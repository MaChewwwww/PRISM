from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
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
    SpecialistScores,
    TradeDecisionReport,
    TradeDirection,
    TradeVerdict,
)
from app.core.llm_gateway import LLMGateway
from app.market.alpaca_gateway import AlpacaPyGateway
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
    "Output strictly valid JSON matching the schema."
)


class TradeProposalLLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
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
        ...,
        description="Narrative breakdown reconciling agreeing vs. dissenting specialist signals",
    )

    portfolio_fit: str = Field(
        ...,
        description="Assessment of portfolio risk, sector concentration, and volatility fit",
    )
    options_only_constraint_acknowledged: bool = Field(
        default=True,
        description="Acknowledgment that trade must strictly execute as a defined paper option",
    )
    synthesis_rationale: str = Field(
        ..., description="Comprehensive multi-agent consensus and trade rationale"
    )
    key_risks: list[str] = Field(
        default_factory=list, description="Top 2-4 primary risks identified across agents"
    )


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
    ) -> TradeDecisionReport:
        sym = symbol.strip().upper()
        active_model = self.llm_gateway._settings.llm_model or "default"

        # Check DB Cache
        if db_session is not None:
            try:
                stmt = (
                    select(TradeDecisionModel)
                    .where(
                        TradeDecisionModel.symbol == sym,
                        TradeDecisionModel.model_name == active_model,
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
                        trace_id=UUID(cached.trace_id),
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
                    )

            except Exception as exc:
                logger.warning(
                    "TradeDecision DB cache read failed for %s: %s",
                    sym,
                    type(exc).__name__,
                )

        # 1. Fetch Market Data for Underlying (Bars)
        bars = self.alpaca_gateway.get_stock_bars(symbol=sym, limit=250)
        if not bars:
            raise ValueError(f"Insufficient market price bars available for symbol {sym}")
        current_price = Decimal(str(bars[-1]["close"]))

        # 2. Concurrently Execute Specialist Agents
        reaction_agent = MarketReactionAgent(self.llm_gateway)
        industry_agent = IndustryIntelligenceAgent(self.llm_gateway, self.alpaca_gateway)
        macro_agent = MacroeconomicAgent(self.llm_gateway, self.alpaca_gateway)
        news_agent = NewsIntelligenceAgent(self.llm_gateway)

        news_articles = self.alpaca_gateway.get_news(symbol=sym, limit=3)

        # Top catalyst metadata for concurrent reaction analysis
        top_art = news_articles[0] if news_articles else {}
        catalyst = top_art.get("headline") or f"Market movement in {sym}"
        art_id = top_art.get("id")

        # Coroutines for all async specialist agents running in parallel
        news_tasks = [
            news_agent.analyze_article(
                article=art,
                symbol=sym,
                trace_id=trace_id,
                db_session=db_session,
            )
            for art in news_articles[:2]
        ]
        news_coro = asyncio.gather(*news_tasks) if news_tasks else asyncio.sleep(0, result=[])

        news_report, industry_report, macro_report, reaction_report = await asyncio.gather(
            news_coro,
            industry_agent.analyze_industry(
                symbol=sym,
                trace_id=trace_id,
                db_session=db_session,
            ),
            macro_agent.analyze_macro(
                symbol=sym,
                trace_id=trace_id,
                db_session=db_session,
            ),
            reaction_agent.analyze_reaction(
                symbol=sym,
                bars=bars,
                catalyst_summary=catalyst,
                expected_reaction_pct=Decimal("0.0"),
                trace_id=trace_id,
                db_session=db_session,
                article_id=art_id,
                event_age_seconds=0,
                event_category=NewsEventCategory.OTHER,
            ),
        )

        # Synchronous deterministic agents
        quant_report: QuantitativeAnalysisReport = compute_quantitative_analysis(
            bars=bars, symbol=sym, trace_id=trace_id
        )
        fundamental_report: FundamentalAnalysisReport = compute_fundamental_analysis(
            symbol=sym, latest_close=current_price, trace_id=trace_id
        )

        # 3. Deterministic Composite Scoring & Alignment
        news_score = calculate_news_sentiment_score(news_report)
        reaction_opp_score = (
            reaction_report.confidence * Decimal("100.0")
            if reaction_report.confidence is not None
            else Decimal("75.0")
        )

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

        # 4. LLM Decision Synthesis
        pe_val = fundamental_report.valuation.pe_ratio_ttm or "N/A"
        z_str = f"Z={fundamental_report.altman_z_score} ({fundamental_report.altman_zone.value})"

        top_event = news_report[0] if news_report else None
        news_details = []
        if top_event:
            cat_val = (
                top_event.event_category.value
                if hasattr(top_event.event_category, "value")
                else str(top_event.event_category)
            )
            mat_val = (
                top_event.catalyst_materiality.value
                if hasattr(top_event.catalyst_materiality, "value")
                else str(top_event.catalyst_materiality)
            )
            guid_val = (
                top_event.guidance_change.value
                if hasattr(top_event.guidance_change, "value")
                else str(top_event.guidance_change)
            )
            news_details.append(f"Category={cat_val}")
            news_details.append(f"Materiality={mat_val}")
            news_details.append(f"Guidance={guid_val}")
            if top_event.earnings_surprise:
                if top_event.earnings_surprise.eps_surprise_pct:
                    news_details.append(
                        f"EPS Surprise={top_event.earnings_surprise.eps_surprise_pct}%"
                    )
                if top_event.earnings_surprise.revenue_surprise_pct:
                    news_details.append(
                        f"Rev Surprise={top_event.earnings_surprise.revenue_surprise_pct}%"
                    )
            if any(getattr(e, "has_contradictory_signals", False) for e in news_report):
                news_details.append("FLAGS=CONTRADICTORY_SIGNALS_PRESENT")
        news_extra_str = f" | {', '.join(news_details)}" if news_details else ""

        fund_event_str = ""
        if fundamental_report.earnings_event:
            ee = fundamental_report.earnings_event
            fund_event_str = (
                f" | Earnings Event: EPS Surp={ee.eps_surprise_pct or 'N/A'}%, "
                f"Rev Surp={ee.revenue_surprise_pct or 'N/A'}%, "
                f"Guidance={ee.guidance_change.value.upper()}, "
                f"Revisions={ee.estimate_revision_trend.value.upper()}"
            )

        red_flags_str = ""
        if fundamental_report.red_flags:
            flags_list = ", ".join(rf.value for rf in fundamental_report.red_flags)
            red_flags_str = f" | RED FLAGS: [{flags_list}]"

        react_class_str = (
            reaction_report.classification.value
            if reaction_report.classification
            else "FAIR_REACTION"
        )
        prompt = (
            "You are the Chief Investment Officer (CIO) for PRISM.\n"
            f"Synthesize specialist research into an actionable trade proposal for: {sym}.\n\n"
            f"CURRENT MARKET PRICE: ${current_price}\n\n"
            f"SPECIALIST AGENT SYNTHESIS INPUTS:\n"
            f"1. NEWS: {len(news_report)} catalysts analyzed | Score={news_score}/100 | "
            f"Top Headline: '{catalyst}'{news_extra_str}\n\n"
            f"2. QUANT: Trend={quant_report.trend.value.upper()} | "
            f"Momentum={quant_report.momentum_score}/100 | "
            f"Confirmation={quant_report.trend_confirmation.value.replace('_', ' ').upper()} | "
            f"Gap={quant_report.price_displacement.gap_size_pct}% | "
            f"RSI={quant_report.rsi_14} ({quant_report.rsi_condition.value.upper()}) | "
            f"Vol={quant_report.volatility_annualized_pct}%\n\n"
            f"3. INDUSTRY: Sector={industry_report.sector_name} ({industry_report.sector_etf}) | "
            f"Health={industry_report.sector_health_score}/100 | "
            f"Regime={industry_report.sector_regime_confirmation.value} | "
            f"Moat={industry_report.competitive_moat.value.upper()} | "
            f"Alpha Sector 20d={industry_report.relative_alpha_20d_pct}% | "
            f"Alpha SPY 20d={industry_report.stock_vs_spy_alpha_20d_pct}% | "
            f"Peer Dispersion={industry_report.peer_dispersion_20d_pct}% | "
            f"Peer Dynamics={industry_report.peer_reaction_dynamics.value}\n\n"
            f"4. FUNDAMENTAL: Quality={fundamental_report.composite_quality_score}/100 | "
            f"Health={fundamental_report.fundamental_health.value.upper()} | "
            f"F-Score={fundamental_report.piotroski_f_score}/9 | {z_str} | "
            f"Valuation={fundamental_report.valuation_stance.value.upper()} (P/E: {pe_val}x)"
            f"{fund_event_str}{red_flags_str}\n\n"
            f"5. MACRO: Regime={macro_report.macro_regime.value.upper()} | "
            f"Rates={macro_report.rate_environment.value.upper()} | "
            f"Stress={macro_report.market_stress_level.value.upper()} "
            f"({macro_report.market_stress_direction.value.upper()}, "
            f"Vol={macro_report.realized_volatility_pct}%) | "
            f"Event Proximity={macro_report.economic_event_proximity.value} | "
            f"Asset Impact={macro_report.asset_macro_impact.value.upper()} | "
            f"Climate={macro_report.macro_climate_score}/100\n\n"
            f"6. MARKET REACTION: Class={react_class_str} | "
            f"Gap={reaction_report.reaction_gap_pct}% "
            f"(Adj Gap={reaction_report.direction_adjusted_gap_pct}%) | "
            f"IV/HV={reaction_report.iv_hv_ratio}x "
            f"(Implied Move=±{reaction_report.options_implied_move_pct}%, "
            f"Actual={reaction_report.actual_reaction_pct}%) | "
            f"Decay={reaction_report.catalyst_decay_status.value.upper()} "
            f"(Factor={reaction_report.catalyst_decay_factor}, "
            f"Age={reaction_report.event_age_hours}h) | "
            f"Analogs={reaction_report.analog_count} "
            f"(Median={reaction_report.historical_median_reaction_pct}%, "
            f"Sim={reaction_report.analog_similarity_score}/100) | "
            f"Opportunity={reaction_opp_score}/100 | "
            f"Thesis={reaction_report.thesis}\n\n"
            f"DETERMINISTIC COMPOSITE MULTI-AGENT SCORE: {composite_score}/100\n\n"
            "TASK:\n"
            "1. Output Verdict ('proceed_to_options_proposal' or 'no_trade').\n"
            "2. Select Direction ('bullish', 'bearish', or 'neutral').\n"
            "3. Select Structure ('long_call', 'long_put', 'bull_call_spread', "
            "'bear_put_spread', 'no_trade').\n"
            "4. Provide Net EV (R-multiples, >= +0.15R) and Reward/Risk ratio (>= 1.50:1).\n"
            "5. Provide Confidence Score (0-100) and Target Price.\n"
            "6. Provide Evidence Summary (3-5 bullets) and Contradictions List.\n"
            "7. Assess Portfolio Fit and confirm Options-Only Constraint.\n"
            "8. Detail Synthesis Rationale, Contradiction Analysis, and Key Risks."
        )

        llm_response = await self.llm_gateway.complete_structured(
            prompt=prompt,
            response_model=TradeProposalLLMOutput,
            system_prompt=SYSTEM_PROMPT,
            trace_id=trace_id,
        )

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
            max_hold_days=14,
        )

        now_utc = datetime.now(UTC)
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
                logger.warning("Failed to cache TradeDecisionReport to database: %s", exc)
                await db_session.rollback()

        return decision
