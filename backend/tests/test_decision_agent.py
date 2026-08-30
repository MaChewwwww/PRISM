from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.contracts.models import (
    AssetMacroImpact,
    CatalystMateriality,
    CompetitiveMoat,
    GuidanceChange,
    IndustrySentiment,
    MacroRegime,
    NewsEventCategory,
    OptionStructure,
    RateEnvironment,
    TradeDirection,
    TradeVerdict,
)
from app.core.config import Settings
from app.core.llm_gateway import LLMCompletionResult, LLMGateway
from app.market.alpaca_gateway import AlpacaPyGateway
from app.research.decision_agent import (
    TradeProposalLLMOutput,
    TradingDecisionAgent,
    calculate_news_sentiment_score,
    compute_composite_opportunity_score,
)
from app.research.industry_agent import IndustryAnalysisLLMOutput
from app.research.macro_agent import MacroAnalysisLLMOutput
from app.research.news_agent import NewsAnalysisLLMOutput
from app.research.reaction_agent import ReactionAnalysisLLMOutput


def test_compute_composite_opportunity_score() -> None:
    # High score across all specialists
    score = compute_composite_opportunity_score(
        reaction_score=Decimal("85.0"),
        quant_momentum_score=Decimal("80.0"),
        fundamental_quality_score=Decimal("90.0"),
        sector_health_score=Decimal("75.0"),
        macro_climate_score=Decimal("70.0"),
        news_sentiment_score=Decimal("80.0"),
    )
    assert Decimal("80.0") <= score <= Decimal("85.0")

    # Low score across all specialists
    low_score = compute_composite_opportunity_score(
        reaction_score=Decimal("50.0"),
        quant_momentum_score=Decimal("40.0"),
        fundamental_quality_score=Decimal("45.0"),
        sector_health_score=Decimal("40.0"),
        macro_climate_score=Decimal("30.0"),
        news_sentiment_score=Decimal("20.0"),
    )
    assert Decimal("35.0") <= low_score <= Decimal("45.0")


def test_calculate_news_sentiment_score() -> None:
    assert calculate_news_sentiment_score([]) == Decimal("50.0")


@pytest.mark.asyncio
async def test_decision_agent_synthesize_mocked() -> None:
    settings = Settings(
        app_env="development",
        alpaca_api_key="test-key",
        alpaca_secret_key="test-secret",
        llm_api_key="test-llm-key",
        llm_model="test-model",
    )
    llm_gateway = LLMGateway(settings)

    mock_trade_output = TradeProposalLLMOutput(
        verdict=TradeVerdict.PROCEED_TO_OPTIONS_PROPOSAL,
        direction=TradeDirection.BULLISH,
        recommended_structure=OptionStructure.BULL_CALL_SPREAD,
        net_ev_r=Decimal("0.45"),
        reward_risk_ratio=Decimal("2.20"),
        confidence_score=Decimal("88.0"),
        target_price=Decimal("135.00"),
        evidence_summary=[
            "Quant momentum score is 84/100 with RSI confirming continuation",
            "Market reaction shows underreaction with +3.0% direction-adjusted gap",
            "Macro rate-cut cycle provides strong duration asset tailwind",
        ],
        contradictions=["Quant 5-day displacement is stretched vs 20-day historical mean"],
        contradiction_analysis=(
            "Short-term quantitative stretch is outweighed by robust fundamentals."
        ),
        portfolio_fit="Semiconductor beta is 1.15x with available delta/vega capacity.",
        options_only_constraint_acknowledged=True,
        synthesis_rationale="Multi-agent consensus across Quant, News, and Fundamental.",
        key_risks=["Potential rate hike headline risk", "Short-term profit taking"],
    )

    mock_news_output = NewsAnalysisLLMOutput(
        event_category=NewsEventCategory.PRODUCT_INNOVATION,
        catalyst_materiality=CatalystMateriality.MEDIUM,
        sentiment="bullish",
        significance_score=Decimal("85.0"),
        expected_reaction_pct=Decimal("3.5"),
        guidance_change=GuidanceChange.NOT_APPLICABLE,
        eps_surprise_pct=None,
        revenue_surprise_pct=None,
        quarter=None,
        has_contradictory_signals=False,
        contradiction_notes=None,
        rationale="Strong demand reported",
    )

    mock_industry_output = IndustryAnalysisLLMOutput(
        competitive_moat=CompetitiveMoat.WIDE,
        overall_sentiment=IndustrySentiment.POSITIVE,
        tailwinds=["AI compute growth"],
        headwinds=["Supply constraints"],
        thesis="Dominant market share",
    )

    mock_macro_output = MacroAnalysisLLMOutput(
        macro_regime=MacroRegime.RISK_ON,
        rate_environment=RateEnvironment.RATE_CUT_CYCLE,
        asset_macro_impact=AssetMacroImpact.STRONG_TAILWIND,
        macro_tailwinds=["Lower rates"],
        macro_headwinds=["Inflation stickiness"],
        stock_macro_sensitivity="High sensitivity",
        thesis="Macro regime favors tech",
    )

    mock_reaction_output = ReactionAnalysisLLMOutput(
        thesis="Market is underreacting to AI demand",
        confidence=Decimal("0.85"),
        evidence_summaries=["Volume surge confirms move"],
        classification="UNDERREACTION",
    )

    async def mock_complete_structured(
        prompt: str,
        response_model: type,
        system_prompt: str | None = None,
        trace_id: str | None = None,
    ) -> LLMCompletionResult:
        if response_model is NewsAnalysisLLMOutput:
            parsed_data = mock_news_output
        elif response_model is IndustryAnalysisLLMOutput:
            parsed_data = mock_industry_output
        elif response_model is MacroAnalysisLLMOutput:
            parsed_data = mock_macro_output
        elif response_model is ReactionAnalysisLLMOutput:
            parsed_data = mock_reaction_output
        else:
            parsed_data = mock_trade_output

        return LLMCompletionResult(
            raw_content="{}",
            parsed=parsed_data,
            model="test-model",
            provider="test-provider",
            raw_digest="a" * 64,
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            latency_ms=350,
            trace_id=uuid4(),
        )

    llm_gateway.complete_structured = AsyncMock(side_effect=mock_complete_structured)  # type: ignore[method-assign]

    alpaca_gateway = MagicMock(spec=AlpacaPyGateway)
    alpaca_gateway.get_stock_bars.return_value = [
        {"close": 120.0 + i, "timestamp": "2026-08-28T00:00:00Z"} for i in range(25)
    ]
    alpaca_gateway.get_news.return_value = [
        {
            "id": 101,
            "headline": "Nvidia announces next-gen AI chip demand",
            "summary": "Record demand for GPUs",
            "content": "<p>Strong enterprise demand</p>",
            "source": "Bloomberg",
        }
    ]

    agent = TradingDecisionAgent(llm_gateway=llm_gateway, alpaca_gateway=alpaca_gateway)
    trace_id = uuid4()

    proposal = await agent.synthesize_decision(symbol="NVDA", trace_id=trace_id)

    assert proposal.symbol == "NVDA"
    assert proposal.verdict in {
        TradeVerdict.PROCEED_TO_OPTIONS_PROPOSAL,
        TradeVerdict.PROPOSE_TRADE,
        TradeVerdict.NO_TRADE,
    }
    assert len(proposal.evidence_summary) == 3
    assert len(proposal.contradictions) == 1
    assert proposal.options_only_constraint_acknowledged is True
    assert "Semiconductor" in proposal.portfolio_fit
    assert proposal.exit_policy.take_profit_pct == Decimal("75.0")
    assert proposal.exit_policy.stop_loss_pct == Decimal("50.0")
    assert proposal.exit_policy.dte_threshold == 7
    assert proposal.exit_policy.max_hold_days == 14
