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
    OptionStructure,
    QuantitativeAnalysisReport,
    ResearchReport,
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
    "You are the Chief Investment Officer & Trading Decision Synthesis Agent for PRISM.\n"
    "Your responsibility is to synthesize research from ALL 6 specialist agents:\n"
    "1. News Intelligence (Sentiment & Catalysts)\n"
    "2. Quantitative Analysis (Momentum, RSI, SMAs, Volatility)\n"
    "3. Industry Intelligence (Sector Health, Relative Alpha, Moat)\n"
    "4. Fundamental Analysis (Piotroski F-Score, Altman Z-Score, Margins, Valuation)\n"
    "5. Macroeconomic Analysis (Regime, Rates, Stress Level, Yields)\n"
    "6. Market Reaction & Mispricing (Reaction Gap & Opportunity Score)\n\n"
    "GOVERNANCE & OPTION SELECTION RULES:\n"
    "- If Composite Score < 75.0 or there is fatal fundamental distress (Z-Score < 1.8) or "
    "unfavorable expected value (< +0.15R), output verdict 'no_trade' and structure 'no_trade'.\n"
    "- In VOLATILE or HIGH STRESS regimes, propose defined-risk spreads ('bull_call_spread' or "
    "'bear_put_spread').\n"
    "- In NORMAL/LOW STRESS regimes with high conviction, propose single-leg ('long_call' or "
    "'long_put').\n"
    "- Net EV must be realistic (>= +0.15R) and Reward/Risk ratio must be >= 1.50:1.\n"
    "Output strictly valid JSON matching the schema."
)


class TradeProposalLLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: TradeVerdict = Field(
        ..., description="Proposal verdict: 'propose_trade' or 'no_trade'"
    )
    direction: TradeDirection = Field(
        ..., description="Directional stance: 'bullish', 'bearish', or 'neutral'"
    )
    recommended_structure: OptionStructure = Field(
        ...,
        description="Supported structure: 'long_call', 'long_put', 'bull_call_spread', "
        "'bear_put_spread', or 'no_trade'",
    )
    net_ev_r: Decimal = Field(
        ...,
        description="Net expected value in R-multiples (minimum +0.15R for valid trade)",
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
    synthesis_rationale: str = Field(
        ..., description="Comprehensive multi-agent consensus and trade rationale"
    )
    contradiction_analysis: str = Field(
        ...,
        description="Explicit breakdown of agreeing vs. dissenting specialist agent signals",
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
    """Map news event sentiments to a 0-100 normalized score."""
    if not news_events:
        return Decimal("50.0")
    total_score = Decimal("0.0")
    for event in news_events:
        sentiment = str(event.sentiment).lower()
        if "bullish" in sentiment:
            total_score += Decimal("80.0")
        elif "bearish" in sentiment:
            total_score += Decimal("20.0")
        else:
            total_score += Decimal("50.0")
    return round(total_score / Decimal(str(len(news_events))), 1)


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
                if cached is not None:
                    logger.info("Returning cached TradeDecisionReport for %s", sym)
                    exit_policy = ExitPolicy.model_validate(json.loads(cached.exit_policy_json))
                    spec_scores = SpecialistScores.model_validate(
                        json.loads(cached.specialist_scores_json)
                    )
                    return TradeDecisionReport(
                        id=UUID(cached.id),
                        trace_id=UUID(cached.trace_id),
                        created_at=cached.created_at,
                        symbol=cached.symbol,
                        verdict=TradeVerdict(cached.verdict),
                        direction=TradeDirection(cached.direction),
                        recommended_structure=OptionStructure(cached.recommended_structure),
                        composite_opportunity_score=cached.composite_opportunity_score,
                        net_ev_r=cached.net_ev_r,
                        reward_risk_ratio=cached.reward_risk_ratio,
                        confidence_score=cached.confidence_score,
                        current_price=cached.current_price,
                        target_price=cached.target_price,
                        exit_policy=exit_policy,
                        specialist_scores=spec_scores,
                        synthesis_rationale=cached.synthesis_rationale,
                        contradiction_analysis=cached.contradiction_analysis,
                        key_risks=json.loads(cached.key_risks_json),
                    )
            except Exception as exc:
                logger.warning("Error checking decision cache: %s", exc)

        # 1. Concurrently Fetch Market Bars and News in Worker Threads (Non-blocking I/O)
        bars, news_articles = await asyncio.gather(
            asyncio.to_thread(self.alpaca_gateway.get_stock_bars, sym, limit=250),
            asyncio.to_thread(self.alpaca_gateway.get_news, sym, limit=5),
        )

        if not bars or "close" not in bars[-1]:
            logger.warning(
                "No live bars returned from Alpaca for %s; using baseline market valuation",
                sym,
            )
            bars = [
                {
                    "timestamp": datetime.now(UTC),
                    "open": Decimal("130.00"),
                    "high": Decimal("132.00"),
                    "low": Decimal("128.00"),
                    "close": Decimal("130.50"),
                    "volume": 5000000,
                }
            ]
        current_price = Decimal(str(bars[-1]["close"]))

        # 2. Concurrently Execute All 6 Specialist Research Agents in Parallel
        industry_agent = IndustryIntelligenceAgent(self.llm_gateway, self.alpaca_gateway)
        macro_agent = MacroeconomicAgent(self.llm_gateway, self.alpaca_gateway)
        reaction_agent = MarketReactionAgent(self.llm_gateway)
        news_agent = NewsIntelligenceAgent(self.llm_gateway)

        # Launch News, Industry, and Macro concurrently at the exact same moment
        news_tasks = [
            news_agent.analyze_article(
                article=art,
                symbol=sym,
                trace_id=trace_id,
                db_session=db_session,
            )
            for art in (news_articles or [])
        ]
        news_coro = asyncio.gather(*news_tasks) if news_tasks else asyncio.sleep(0, result=[])
        industry_coro = industry_agent.analyze_industry(
            symbol=sym, trace_id=trace_id, db_session=db_session
        )
        macro_coro = macro_agent.analyze_macro(symbol=sym, trace_id=trace_id, db_session=db_session)

        news_report, industry_report, macro_report = await asyncio.gather(
            news_coro, industry_coro, macro_coro
        )

        # Synchronous deterministic agents
        quant_report: QuantitativeAnalysisReport = compute_quantitative_analysis(
            bars=bars, symbol=sym, trace_id=trace_id
        )
        fundamental_report: FundamentalAnalysisReport = compute_fundamental_analysis(
            symbol=sym, latest_close=current_price, trace_id=trace_id
        )

        # Reaction agent
        catalyst = news_report[0].headline if news_report else f"Market movement in {sym}"
        exp_move = (
            news_report[0].expected_reaction_pct
            if news_report and news_report[0].expected_reaction_pct
            else Decimal("0.0")
        )
        reaction_report: ResearchReport = await reaction_agent.analyze_reaction(
            symbol=sym,
            bars=bars,
            catalyst_summary=catalyst,
            expected_reaction_pct=exp_move,
            trace_id=trace_id,
            db_session=db_session,
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

        # 4. DeepSeek LLM Decision Synthesis
        pe_val = fundamental_report.valuation.pe_ratio_ttm or "N/A"
        z_str = f"Z={fundamental_report.altman_z_score} ({fundamental_report.altman_zone.value})"
        prompt = (
            f"Synthesize multi-agent research package for {sym} at ${current_price}:\n\n"
            f"1. NEWS: Score={news_score}/100 | Top Headline={catalyst}\n\n"
            f"2. QUANT: Trend={quant_report.trend.value.upper()} | "
            f"Momentum={quant_report.momentum_score}/100 | "
            f"RSI={quant_report.rsi_14} ({quant_report.rsi_condition.value.upper()}) | "
            f"Vol={quant_report.volatility_annualized_pct}%\n\n"
            f"3. INDUSTRY: Sector={industry_report.sector_name} ({industry_report.sector_etf}) | "
            f"Health={industry_report.sector_health_score}/100 | "
            f"Moat={industry_report.competitive_moat.value.upper()} | "
            f"Alpha 20d={industry_report.relative_alpha_20d_pct}%\n\n"
            f"4. FUNDAMENTAL: Quality={fundamental_report.composite_quality_score}/100 | "
            f"Health={fundamental_report.fundamental_health.value.upper()} | "
            f"F-Score={fundamental_report.piotroski_f_score}/9 | {z_str} | "
            f"Valuation={fundamental_report.valuation_stance.value.upper()} (P/E: {pe_val}x)\n\n"
            f"5. MACRO: Regime={macro_report.macro_regime.value.upper()} | "
            f"Rates={macro_report.rate_environment.value.upper()} | "
            f"Stress={macro_report.market_stress_level.value.upper()} | "
            f"Climate={macro_report.macro_climate_score}/100\n\n"
            f"6. MARKET REACTION: Thesis={reaction_report.thesis} | "
            f"Confidence={reaction_opp_score}/100\n\n"
            f"DETERMINISTIC COMPOSITE MULTI-AGENT SCORE: {composite_score}/100\n\n"
            "TASK:\n"
            "1. Output Verdict ('propose_trade' or 'no_trade').\n"
            "2. Select Direction ('bullish', 'bearish', or 'neutral').\n"
            "3. Select Structure ('long_call', 'long_put', 'bull_call_spread', "
            "'bear_put_spread', 'no_trade').\n"
            "4. Provide Net EV (R-multiples, >= +0.15R) and Reward/Risk ratio (>= 1.50:1).\n"
            "5. Provide Confidence Score (0-100) and Target Price.\n"
            "6. Detail Synthesis Rationale, Contradiction Analysis, and Key Risks."
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
            synthesis_rationale=output.synthesis_rationale,
            contradiction_analysis=output.contradiction_analysis,
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
                    synthesis_rationale=output.synthesis_rationale,
                    contradiction_analysis=output.contradiction_analysis,
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
