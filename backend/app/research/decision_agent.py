from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.models import (
    ExitPolicy,
    FundamentalAnalysisReport,
    FundamentalHealth,
    LLMEventAnalysis,
    NewsEventCategory,
    OptionStructure,
    QuantitativeAnalysisReport,
    ResearchReport,
    ShadowAlternativeIntent,
    SpecialistScores,
    TradeDecisionReport,
    TradeDirection,
    TradeVerdict,
)
from app.core.llm_gateway import LLMError, LLMGateway
from app.market.alpaca_gateway import AlpacaPyGateway
from app.research.fundamental_data import CompanyFinancials
from app.research.fundamental_engine import compute_fundamental_analysis
from app.research.industry_agent import IndustryIntelligenceAgent
from app.research.macro_agent import MacroeconomicAgent
from app.research.models import TradeDecisionModel
from app.research.news_agent import NewsIntelligenceAgent
from app.research.quant_engine import compute_quantitative_analysis
from app.research.reaction_agent import MarketReactionAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are the Chief Investment Officer (CIO) & Master Strategy Synthesis Agent for PRISM.\n"
    "Your responsibility is to synthesize research from ALL 6 specialist agents:\n"
    "1. News Intelligence (Sentiment, Materiality, Catalysts)\n"
    "2. Quantitative Analysis (Momentum, RSI, Moving Averages, Realized Volatility)\n"
    "3. Industry Intelligence (Sector Health, Relative Alpha, Peer Dynamics, Moat)\n"
    "4. Fundamental Analysis (Piotroski F-Score, Altman Z-Score, Margins, Valuation, Red Flags)\n"
    "5. Macroeconomic Analysis (Regime, Rates, Stress Direction, Event Proximity, Macro Climate)\n"
    "6. Market Reaction & Mispricing (Reaction Gap, IV/HV, Implied Move, Decay, Analogs)\n\n"
    "MANDATORY GOVERNANCE & OPTIONS-ONLY INVARIANTS:\n"
    "- PRISM is strictly a paper options trading system (no spot equity purchase).\n"
    "- If Composite Score < 75.0, Altman Z-Score < 1.8 (distressed), Net EV < +0.15R, or "
    "Reward/Risk < 1.50:1, output verdict 'no_trade' and recommended_structure 'no_trade'.\n"
    "- If research indicates strong multi-agent alignment and positive expectation, output verdict "
    "'proceed_to_options_proposal'.\n"
    "- In HIGH STRESS or high volatility regimes, select defined-risk spreads "
    "('bull_call_spread' or 'bear_put_spread').\n"
    "- In LOW STRESS / NORMAL regimes with strong directional momentum, select single-leg "
    "('long_call' or 'long_put').\n"
    "- Explicitly state 3-5 concise evidence summary points, list cross-agent contradictions, "
    "and evaluate portfolio fit.\n"
    "- Optionally provide one non-executable ShadowFund alternative intent with only a direction, "
    "supported structure, and rationale. Never provide option symbols, strikes, prices, "
    "or orders.\n"
    "Output strictly valid JSON matching the schema."
)


class TradeProposalLLMOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    verdict: TradeVerdict = Field(
        ...,
        description="Proposal verdict: 'proceed_to_options_proposal' or 'no_trade'",
    )
    direction: TradeDirection = Field(
        ..., description="Directional stance: 'bullish', 'bearish', or 'neutral'"
    )
    recommended_structure: OptionStructure = Field(
        ...,
        description="Supported option structure: 'long_call', 'long_put', 'bull_call_spread', "
        "'bear_put_spread', or 'no_trade'",
    )
    net_ev_r: Decimal = Field(
        ...,
        description="Net expected value in R-multiples (minimum +0.15R for affirmative proposal)",
    )
    reward_risk_ratio: Decimal = Field(
        ..., description="Realistic reward-to-risk ratio (minimum 1.50:1)"
    )
    confidence_score: Decimal = Field(
        ..., ge=0, le=100, description="Overall synthesis confidence score (0-100)"
    )
    target_price: Decimal | None = Field(
        default=None, description="Projected price target for target stock"
    )
    evidence_summary: list[str] = Field(
        default_factory=list,
        description="Top 3-5 concise evidence bullet points synthesized across specialists",
    )
    contradictions: list[str] = Field(
        default_factory=list,
        description="Specific cross-agent dissenting signals or conflicting data points",
    )
    contradiction_analysis: str = Field(
        default="No material contradictions identified across specialist consensus.",
        description="Narrative breakdown reconciling agreeing vs. dissenting specialist signals",
    )

    portfolio_fit: str = Field(
        default="Standard risk parameters met.",
        description="Assessment of portfolio risk, sector concentration, and volatility fit",
    )
    options_only_constraint_acknowledged: bool = Field(
        default=True,
        description="Acknowledgment that trade must strictly execute as a defined paper option",
    )
    synthesis_rationale: str = Field(
        default="Consensus proposal aligned with multi-agent scores.",
        description="Comprehensive multi-agent consensus and trade rationale",
    )
    key_risks: list[str] = Field(
        default_factory=list, description="Top 2-4 primary risks identified across agents"
    )
    shadow_alternative_intent: ShadowAlternativeIntent | None = Field(
        default=None,
        description=(
            "Optional non-executable ShadowFund alternative. Provide only direction, "
            "supported structure, and rationale; never contract symbols, strikes, prices, "
            "or orders."
        ),
    )

    @field_validator("evidence_summary", "contradictions", "key_risks", mode="before")
    @classmethod
    def _coerce_list(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [v.strip()]
        if isinstance(v, (list, tuple)):
            return [str(x).strip() for x in v]
        return []


def compute_composite_opportunity_score(
    reaction_score: Decimal,
    quant_momentum_score: Decimal,
    fundamental_quality_score: Decimal,
    sector_health_score: Decimal,
    macro_climate_score: Decimal,
    news_sentiment_score: Decimal,
) -> Decimal:
    """Deterministically compute 0-100 multi-agent weighted opportunity score."""
    score = (
        (reaction_score * Decimal("0.25"))
        + (quant_momentum_score * Decimal("0.20"))
        + (fundamental_quality_score * Decimal("0.20"))
        + (sector_health_score * Decimal("0.15"))
        + (macro_climate_score * Decimal("0.10"))
        + (news_sentiment_score * Decimal("0.10"))
    )
    return min(Decimal("100.0"), max(Decimal("0.0"), round(score, 1)))


def calculate_news_sentiment_score(news_events: list[LLMEventAnalysis]) -> Decimal:
    """Deterministically map news events to a 0-100 normalized score weighted
    by materiality and source confidence."""
    if not news_events:
        return Decimal("50.0")

    materiality_weights = {
        "critical": Decimal("1.50"),
        "high": Decimal("1.25"),
        "medium": Decimal("1.00"),
        "low": Decimal("0.60"),
        "noise": Decimal("0.20"),
    }

    weighted_total = Decimal("0.0")
    total_weight = Decimal("0.0")

    for event in news_events:
        sentiment = str(event.sentiment).lower()
        if "bullish" in sentiment:
            base_score = Decimal("80.0")
        elif "bearish" in sentiment:
            base_score = Decimal("20.0")
        else:
            base_score = Decimal("50.0")

        mat_key = str(getattr(event, "catalyst_materiality", "medium")).lower()
        mat_weight = materiality_weights.get(mat_key, Decimal("1.00"))

        src_conf = Decimal(str(getattr(event, "source_confidence", Decimal("50.0"))))
        conf_factor = max(Decimal("0.2"), min(Decimal("1.0"), src_conf / Decimal("100.0")))

        weight = mat_weight * conf_factor
        weighted_total += base_score * weight
        total_weight += weight

    if total_weight <= Decimal("0"):
        return Decimal("50.0")

    return min(Decimal("100.0"), max(Decimal("0.0"), round(weighted_total / total_weight, 1)))


class TradingDecisionAgent:
    """Agent #7: Master synthesis agent evaluating all 6 specialists to emit TradeProposal."""

    def __init__(self, llm_gateway: LLMGateway, alpaca_gateway: AlpacaPyGateway) -> None:
        self.llm_gateway = llm_gateway
        self.alpaca_gateway = alpaca_gateway

    async def synthesize_decision(
        self,
        symbol: str,
        trace_id: UUID,
        db_session: AsyncSession | None = None,
        *,
        allow_illustrative: bool = True,
        financials: CompanyFinancials | None = None,
        as_of: datetime | None = None,
        provenance: (
            Literal["live_research", "historical_simulation", "illustrative_fixture"] | None
        ) = None,
    ) -> TradeDecisionReport:
        sym = symbol.strip().upper()
        settings = self.llm_gateway._settings
        active_model = f"{settings.llm_provider}:{settings.llm_model or 'default'}"
        now_utc = (as_of or datetime.now(UTC)).astimezone(UTC)
        freshness_cutoff = now_utc.timestamp() - 30

        # Check DB Cache
        if db_session is not None and allow_illustrative:
            try:
                stmt = (
                    select(TradeDecisionModel)
                    .where(
                        TradeDecisionModel.symbol == sym,
                        TradeDecisionModel.model_name == active_model,
                        TradeDecisionModel.created_at
                        >= datetime.fromtimestamp(freshness_cutoff, tz=UTC),
                    )
                    .order_by(TradeDecisionModel.created_at.desc())
                    .limit(1)
                )
                result = await db_session.execute(stmt)
                cached = result.scalar_one_or_none()
                if cached:
                    evidence_summary_raw = (
                        json.loads(getattr(cached, "evidence_summary_json", "[]"))
                        if getattr(cached, "evidence_summary_json", None)
                        else []
                    )
                    contradictions_raw = (
                        json.loads(getattr(cached, "contradictions_json", "[]"))
                        if getattr(cached, "contradictions_json", None)
                        else []
                    )
                    portfolio_fit_val = getattr(cached, "portfolio_fit", "") or ""
                    options_only_val = getattr(cached, "options_only_constraint", True)
                    if options_only_val is None:
                        options_only_val = True

                    return TradeDecisionReport(
                        id=UUID(cached.id),
                        trace_id=trace_id,
                        created_at=cached.created_at,
                        schema_version=cached.schema_version,
                        symbol=cached.symbol,
                        verdict=TradeVerdict(cached.verdict),
                        direction=TradeDirection(cached.direction),
                        recommended_structure=OptionStructure(cached.recommended_structure),
                        composite_opportunity_score=Decimal(
                            str(cached.composite_opportunity_score)
                        ),
                        net_ev_r=Decimal(str(cached.net_ev_r)),
                        reward_risk_ratio=Decimal(str(cached.reward_risk_ratio)),
                        confidence_score=Decimal(str(cached.confidence_score)),
                        current_price=Decimal(str(cached.current_price)),
                        target_price=(
                            Decimal(str(cached.target_price))
                            if cached.target_price is not None
                            else None
                        ),
                        exit_policy=ExitPolicy.model_validate_json(cached.exit_policy_json),
                        specialist_scores=SpecialistScores.model_validate_json(
                            cached.specialist_scores_json
                        ),
                        evidence_summary=evidence_summary_raw,
                        contradictions=contradictions_raw,
                        contradiction_analysis=cached.contradiction_analysis,
                        portfolio_fit=portfolio_fit_val,
                        options_only_constraint_acknowledged=options_only_val,
                        synthesis_rationale=cached.synthesis_rationale,
                        key_risks=json.loads(cached.key_risks_json),
                        provenance="illustrative_fixture"
                        if allow_illustrative
                        else "live_research",
                    )

            except Exception as exc:
                logger.warning("Error checking decision cache: %s", type(exc).__name__)

        # 1. Concurrently Fetch Market Bars and News in Worker Threads (Non-blocking I/O)
        bars, news_articles = await asyncio.gather(
            asyncio.to_thread(self.alpaca_gateway.get_stock_bars, sym, limit=250),
            asyncio.to_thread(self.alpaca_gateway.get_news, sym, limit=5),
        )

        if not bars or "close" not in bars[-1]:
            raise ValueError(f"No fresh market bars available for {sym}")
        if not allow_illustrative and not news_articles:
            raise ValueError(f"No current sourced news evidence available for {sym}")
        current_price = Decimal(str(bars[-1]["close"]))

        # 2. Concurrently Execute Specialist Agents
        reaction_agent = MarketReactionAgent(self.llm_gateway)
        industry_agent = IndustryIntelligenceAgent(self.llm_gateway, self.alpaca_gateway)
        macro_agent = MacroeconomicAgent(self.llm_gateway, self.alpaca_gateway)
        news_agent = NewsIntelligenceAgent(self.llm_gateway)

        # AsyncSession is not safe for concurrent commits. The illustrative
        # presentation path keeps its parallel behavior, while the executable
        # path serializes persistence-bound specialists so every report is
        # durably committed without transaction races.
        if db_session is not None and not allow_illustrative:
            news_report = []
            for article in news_articles or []:
                news_report.append(
                    await news_agent.analyze_article(
                        article=article,
                        symbol=sym,
                        trace_id=trace_id,
                        db_session=db_session,
                        strict=True,
                        evaluation_at=now_utc,
                    )
                )
            industry_report = await industry_agent.analyze_industry(
                symbol=sym,
                trace_id=trace_id,
                db_session=db_session,
                strict=True,
                evaluation_at=now_utc,
            )
            macro_report = await macro_agent.analyze_macro(
                symbol=sym,
                trace_id=trace_id,
                db_session=db_session,
                strict=True,
                evaluation_at=now_utc,
            )

            catalyst = news_report[0].headline if news_report else f"Market movement in {sym}"
            exp_move = (
                news_report[0].expected_reaction_pct
                if news_report and news_report[0].expected_reaction_pct
                else Decimal("0.0")
            )
            evt_cat = news_report[0].event_category if news_report else NewsEventCategory.OTHER
            evt_age = news_report[0].event_age_seconds if news_report else 0
            art_id = news_report[0].article_id if news_report else None

            reaction_report: ResearchReport = await reaction_agent.analyze_reaction(
                symbol=sym,
                bars=bars,
                catalyst_summary=catalyst,
                expected_reaction_pct=exp_move,
                trace_id=trace_id,
                db_session=db_session,
                article_id=art_id,
                event_age_seconds=evt_age,
                event_category=evt_cat,
                strict=True,
                evaluation_at=now_utc,
            )
        else:
            catalyst = (
                news_articles[0].get("headline", f"Market movement in {sym}")
                if news_articles
                else f"Market movement in {sym}"
            )
            art_id = (
                str(news_articles[0].get("id"))
                if news_articles and news_articles[0].get("id")
                else None
            )

            news_tasks = [
                news_agent.analyze_article(
                    article=art,
                    symbol=sym,
                    trace_id=trace_id,
                    db_session=db_session,
                    strict=False,
                )
                for art in (news_articles or [])[:2]
            ]
            news_coro = asyncio.gather(*news_tasks) if news_tasks else asyncio.sleep(0, result=[])
            industry_coro = industry_agent.analyze_industry(
                symbol=sym, trace_id=trace_id, db_session=db_session, strict=False
            )
            macro_coro = macro_agent.analyze_macro(
                symbol=sym, trace_id=trace_id, db_session=db_session, strict=False
            )
            reaction_coro = reaction_agent.analyze_reaction(
                symbol=sym,
                bars=bars,
                catalyst_summary=catalyst,
                expected_reaction_pct=Decimal("0.0"),
                trace_id=trace_id,
                db_session=db_session,
                article_id=art_id,
                event_age_seconds=0,
                event_category=NewsEventCategory.OTHER,
                strict=False,
            )
            news_report, industry_report, macro_report, reaction_report = await asyncio.gather(
                news_coro, industry_coro, macro_coro, reaction_coro
            )

        # Synchronous deterministic agents
        quant_report: QuantitativeAnalysisReport = compute_quantitative_analysis(
            bars=bars, symbol=sym, trace_id=trace_id
        )
        fundamental_report: FundamentalAnalysisReport = compute_fundamental_analysis(
            symbol=sym,
            latest_close=current_price,
            trace_id=trace_id,
            allow_illustrative=allow_illustrative,
            financials=financials,
        )

        # Historical replay evaluates evidence at the requested checkpoint.
        # A daily bar can be many hours old at the checkpoint while still being
        # the latest point-in-time observation; the live path retains the
        # strict 30-second freshness gate.
        if (
            not allow_illustrative
            and provenance != "historical_simulation"
            and reaction_report.freshness_seconds > 30
        ):
            raise ValueError(f"Market reaction evidence is stale for {sym}")

        # 3. Deterministic Composite Scoring & Alignment
        news_score = calculate_news_sentiment_score(news_report)
        # The reaction agent owns the deterministic opportunity score.  Do not
        # substitute confidence (or a made-up 75) because the two measures
        # have different meanings and would diverge from the BA weighting.
        reaction_opp_score = reaction_report.opportunity_score
        if reaction_opp_score is None:
            if not allow_illustrative:
                raise ValueError(f"Market reaction opportunity score is unavailable for {sym}")
            reaction_opp_score = Decimal("0.0")

        composite_score = compute_composite_opportunity_score(
            reaction_score=reaction_opp_score,
            quant_momentum_score=quant_report.momentum_score,
            fundamental_quality_score=fundamental_report.composite_quality_score,
            sector_health_score=industry_report.sector_health_score,
            macro_climate_score=macro_report.macro_climate_score,
            news_sentiment_score=news_score,
        )

        specialist_scores = SpecialistScores(
            reaction_opportunity_score=reaction_opp_score,
            quant_momentum_score=quant_report.momentum_score,
            fundamental_quality_score=fundamental_report.composite_quality_score,
            sector_health_score=industry_report.sector_health_score,
            macro_climate_score=macro_report.macro_climate_score,
            news_sentiment_score=news_score,
        )

        # 4. LLM Decision Synthesis — compact key-value prompt for speed
        pe_val = fundamental_report.valuation.pe_ratio_ttm or "N/A"

        top_event = news_report[0] if news_report else None
        news_meta = ""
        if top_event:
            cat = getattr(top_event.event_category, "value", str(top_event.event_category))
            mat = getattr(
                top_event.catalyst_materiality, "value", str(top_event.catalyst_materiality)
            )
            news_meta = f" Cat={cat} Mat={mat}"
            if any(getattr(e, "has_contradictory_signals", False) for e in news_report):
                news_meta += " CONTRADICTORY"

        react_cls = (
            reaction_report.classification.value
            if reaction_report.classification
            else "FAIR_REACTION"
        )
        prompt = (
            f"CIO synthesis for {sym}. Price=${current_price}. Composite={composite_score}/100.\n"
            f"NEWS: n={len(news_report)} score={news_score}/100 headline='{catalyst}'{news_meta}\n"
            f"QUANT: trend={quant_report.trend.value} mom={quant_report.momentum_score}/100 "
            f"rsi={quant_report.rsi_14}({quant_report.rsi_condition.value}) "
            f"gap={quant_report.price_displacement.gap_size_pct}% "
            f"vol={quant_report.volatility_annualized_pct}%\n"
            f"INDUSTRY: sector={industry_report.sector_name} "
            f"health={industry_report.sector_health_score}/100 "
            f"moat={industry_report.competitive_moat.value} "
            f"alpha_spy={industry_report.stock_vs_spy_alpha_20d_pct}%\n"
            f"FUNDAMENTAL: quality={fundamental_report.composite_quality_score}/100 "
            f"health={fundamental_report.fundamental_health.value} "
            f"f_score={fundamental_report.piotroski_f_score}/9 "
            f"z={fundamental_report.altman_z_score}({fundamental_report.altman_zone.value}) "
            f"valuation={fundamental_report.valuation_stance.value}(PE:{pe_val}x)\n"
            f"MACRO: regime={macro_report.macro_regime.value} "
            f"rates={macro_report.rate_environment.value} "
            f"stress={macro_report.market_stress_level.value} "
            f"impact={macro_report.asset_macro_impact.value} "
            f"climate={macro_report.macro_climate_score}/100\n"
            f"REACTION: class={react_cls} gap={reaction_report.reaction_gap_pct}% "
            f"adj_gap={reaction_report.direction_adjusted_gap_pct}% "
            f"iv_hv={reaction_report.iv_hv_ratio}x opp={reaction_opp_score}/100\n\n"
            "Output JSON: verdict(proceed_to_options_proposal|no_trade), "
            "direction(bullish|bearish|neutral), "
            "structure(long_call|long_put|bull_call_spread|bear_put_spread|no_trade), "
            "net_ev_r(>=0.15), reward_risk_ratio(>=1.5), confidence_score(0-100), "
            "target_price, evidence_summary(3-5 items), contradictions, "
            "contradiction_analysis, portfolio_fit, "
            "options_only_constraint_acknowledged(true), synthesis_rationale, key_risks."
        )

        llm_response = None
        last_llm_exc: Exception | None = None
        for _attempt in range(2):
            try:
                llm_response = await self.llm_gateway.complete_structured(
                    prompt=prompt,
                    response_model=TradeProposalLLMOutput,
                    system_prompt=SYSTEM_PROMPT,
                    trace_id=trace_id,
                    timeout_seconds=120.0,
                    max_tokens=4096,
                )
                break
            except LLMError as exc:
                last_llm_exc = exc
                logger.warning(
                    "CIO LLM attempt %d failed for %s: %s",
                    _attempt + 1,
                    sym,
                    type(exc).__name__,
                )
                if _attempt == 0:
                    await asyncio.sleep(2)
        if llm_response is None:
            raise ValueError(f"CIO LLM synthesis failed after retries for {sym}: {last_llm_exc}")

        if not llm_response.parsed:
            raise ValueError(
                "Failed to obtain valid parsed output from LLM gateway for trading decision"
            )

        output: TradeProposalLLMOutput = llm_response.parsed

        # Enforce Hard Governance Gates
        verdict = output.verdict
        structure = output.recommended_structure
        net_ev = output.net_ev_r
        rr_ratio = output.reward_risk_ratio

        if (
            composite_score < Decimal("75.0")
            or fundamental_report.fundamental_health == FundamentalHealth.DISTRESSED
        ):
            verdict = TradeVerdict.NO_TRADE
            structure = OptionStructure.NO_TRADE

        if net_ev < Decimal("0.15") or rr_ratio < Decimal("1.50"):
            verdict = TradeVerdict.NO_TRADE
            structure = OptionStructure.NO_TRADE

        # BA-Authorized Exit Policy
        exit_policy = ExitPolicy(
            take_profit_pct=Decimal("75.0"),
            stop_loss_pct=Decimal("50.0"),
            dte_threshold=7,
            # Autonomous/hackathon execution uses the BA four-trading-day
            # override; the longer reusable baseline remains presentation-only.
            max_hold_days=(4 if not allow_illustrative else 14),
        )

        decision_id = uuid4()

        decision = TradeDecisionReport(
            id=decision_id,
            trace_id=trace_id,
            created_at=now_utc,
            symbol=sym,
            verdict=verdict,
            direction=output.direction,
            recommended_structure=structure,
            composite_opportunity_score=composite_score,
            net_ev_r=net_ev,
            reward_risk_ratio=rr_ratio,
            confidence_score=output.confidence_score,
            current_price=current_price,
            target_price=output.target_price,
            exit_policy=exit_policy,
            specialist_scores=specialist_scores,
            evidence_summary=output.evidence_summary,
            contradictions=output.contradictions,
            contradiction_analysis=output.contradiction_analysis,
            portfolio_fit=output.portfolio_fit,
            options_only_constraint_acknowledged=output.options_only_constraint_acknowledged,
            synthesis_rationale=output.synthesis_rationale,
            key_risks=output.key_risks,
            shadow_alternative_intent=output.shadow_alternative_intent,
            provenance=(
                provenance or ("illustrative_fixture" if allow_illustrative else "live_research")
            ),
            evidence_freshness_seconds=30,
            analog_count=reaction_report.analog_count,
        )

        # Cache in PostgreSQL
        if db_session is not None:
            try:
                db_record = TradeDecisionModel(
                    id=str(decision_id),
                    trace_id=str(trace_id),
                    created_at=now_utc,
                    schema_version="1.0",
                    symbol=sym,
                    verdict=verdict.value,
                    direction=output.direction.value,
                    recommended_structure=structure.value,
                    composite_opportunity_score=composite_score,
                    net_ev_r=net_ev,
                    reward_risk_ratio=rr_ratio,
                    confidence_score=output.confidence_score,
                    current_price=current_price,
                    target_price=output.target_price,
                    exit_policy_json=json.dumps(exit_policy.model_dump(mode="json")),
                    specialist_scores_json=json.dumps(specialist_scores.model_dump(mode="json")),
                    evidence_summary_json=json.dumps(output.evidence_summary),
                    contradictions_json=json.dumps(output.contradictions),
                    contradiction_analysis=output.contradiction_analysis,
                    portfolio_fit=output.portfolio_fit,
                    options_only_constraint=output.options_only_constraint_acknowledged,
                    synthesis_rationale=output.synthesis_rationale,
                    key_risks_json=json.dumps(output.key_risks),
                    model_name=active_model,
                    raw_digest=llm_response.raw_digest,
                )
                db_session.add(db_record)
                await db_session.commit()
                logger.info("Persisted TradeDecisionReport for %s to database", sym)
            except Exception as exc:
                logger.warning("Failed to cache TradeDecisionReport: %s", type(exc).__name__)
                await db_session.rollback()
                if not allow_illustrative:
                    raise RuntimeError("Durable decision persistence is unavailable") from exc

        return decision
