from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.contracts.models import (
    AssetMacroImpact,
    EconomicEventProximity,
    MacroRegime,
    MarketStressDirection,
    MarketStressLevel,
    RateEnvironment,
)
from app.core.config import Settings
from app.core.llm_gateway import LLMCompletionResult, LLMGateway
from app.market.alpaca_gateway import AlpacaPyGateway
from app.research.macro_agent import (
    MacroAnalysisLLMOutput,
    MacroeconomicAgent,
    compute_macro_climate_score,
    compute_market_stress_level,
    compute_period_return,
    detect_economic_event_proximity,
)


def test_compute_period_return() -> None:
    # 1. Normal positive return
    bars = [{"close": 100.0}, {"close": 105.0}, {"close": 110.0}]
    ret = compute_period_return(bars, days=2)
    assert ret == Decimal("10.00")

    # 2. Empty bars
    assert compute_period_return([], days=5) == Decimal("0.0")

    # 3. Single bar
    assert compute_period_return([{"close": 100.0}], days=5) == Decimal("0.0")


def test_compute_market_stress_level() -> None:
    # Calm / low volatility mock bars
    calm_bars = [{"close": 100 + (i * 0.1)} for i in range(25)]
    stress, direction, vol, delta = compute_market_stress_level(calm_bars)
    assert stress == MarketStressLevel.LOW
    assert direction in {MarketStressDirection.STABLE, MarketStressDirection.EASING}
    assert vol < Decimal("15.0")
    assert delta <= Decimal("2.0")

    # High volatility mock bars (wild swings)
    volatile_bars = [{"close": 100 if i % 2 == 0 else 115} for i in range(25)]
    stress_hi, dir_hi, vol_hi, delta_hi = compute_market_stress_level(volatile_bars)
    assert stress_hi in {MarketStressLevel.HIGH, MarketStressLevel.EXTREME}
    assert dir_hi in {
        MarketStressDirection.ESCALATING,
        MarketStressDirection.STABLE,
        MarketStressDirection.EASING,
    }
    assert vol_hi > Decimal("20.0")
    assert delta_hi is not None


def test_detect_economic_event_proximity() -> None:
    # 1. FOMC headline
    assert (
        detect_economic_event_proximity(["Powell hints at FOMC rate decision this Wednesday"])
        == EconomicEventProximity.FOMC_DECISION_NEAR
    )

    # 2. CPI headline
    assert (
        detect_economic_event_proximity(["Wall Street awaits key CPI inflation report"])
        == EconomicEventProximity.CPI_INFLATION_NEAR
    )

    # 3. Jobs / Payrolls headline
    assert (
        detect_economic_event_proximity(["Nonfarm payrolls report expected to show job growth"])
        == EconomicEventProximity.JOBS_PAYROLLS_NEAR
    )

    # 4. Standard calendar
    assert (
        detect_economic_event_proximity(["Tech stocks lead broad market gains today"])
        == EconomicEventProximity.STANDARD_CALENDAR
    )


def test_compute_macro_climate_score() -> None:
    # 1. Bullish macro climate (rising equities, stable bonds, low vol)
    bull_score = compute_macro_climate_score(
        spy_20d=Decimal("5.0"),
        qqq_20d=Decimal("8.0"),
        tlt_20d=Decimal("2.0"),
        vol_stress=MarketStressLevel.LOW,
    )
    assert Decimal("60.0") <= bull_score <= Decimal("100.0")

    # 2. Bearish macro climate (falling equities, collapsing bonds, extreme vol)
    bear_score = compute_macro_climate_score(
        spy_20d=Decimal("-12.0"),
        qqq_20d=Decimal("-15.0"),
        tlt_20d=Decimal("-10.0"),
        vol_stress=MarketStressLevel.EXTREME,
    )
    assert Decimal("0.0") <= bear_score <= Decimal("40.0")


@pytest.mark.asyncio
async def test_macro_agent_analyze_mocked() -> None:
    # 1. Mock LLM Gateway
    settings = Settings(
        app_env="development",
        alpaca_api_key="test-key",
        alpaca_secret_key="test-secret",
        llm_api_key="test-llm-key",
        llm_model="test-model",
    )
    llm_gateway = LLMGateway(settings)
    mock_llm_output = MacroAnalysisLLMOutput(
        macro_regime=MacroRegime.RISK_ON,
        rate_environment=RateEnvironment.RATE_CUT_CYCLE,
        asset_macro_impact=AssetMacroImpact.STRONG_TAILWIND,
        macro_tailwinds=["Federal Reserve rate cuts", "Expanding market liquidity"],
        macro_headwinds=["Elevated oil prices"],
        stock_macro_sensitivity="NVDA benefits strongly from lower discount rates on cash flows.",
        thesis="Macro regime is risk-on, supporting capital allocation to AI infrastructure.",
    )
    llm_gateway.complete_structured = AsyncMock(  # type: ignore[method-assign]
        return_value=LLMCompletionResult(
            raw_content="{}",
            parsed=mock_llm_output,
            model="test-model",
            provider="test-provider",
            raw_digest="a" * 64,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            latency_ms=200,
            trace_id=uuid4(),
        )
    )

    # 2. Mock Alpaca Gateway
    alpaca_gateway = MagicMock(spec=AlpacaPyGateway)
    alpaca_gateway.get_stock_bars.return_value = [
        {"close": 500.0 + i, "timestamp": "2026-08-28T00:00:00Z"} for i in range(25)
    ]
    alpaca_gateway.get_news.return_value = [
        {"headline": "Fed signals rate cuts ahead at next FOMC meeting", "source": "Reuters"}
    ]

    agent = MacroeconomicAgent(llm_gateway=llm_gateway, alpaca_gateway=alpaca_gateway)
    trace_id = uuid4()

    report = await agent.analyze_macro(symbol="NVDA", trace_id=trace_id)

    assert report.symbol == "NVDA"
    assert report.macro_regime == MacroRegime.RISK_ON
    assert report.rate_environment == RateEnvironment.RATE_CUT_CYCLE
    assert report.asset_macro_impact == AssetMacroImpact.STRONG_TAILWIND
    assert report.economic_event_proximity == EconomicEventProximity.FOMC_DECISION_NEAR
    assert report.market_stress_direction is not None
    assert len(report.assets) >= 6
    assert len(report.macro_tailwinds) == 2
    assert "NVDA benefits" in report.stock_macro_sensitivity
