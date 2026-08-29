from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.contracts.models import (
    MACDCrossover,
    RSICondition,
    TrendDirection,
)
from app.research.quant_engine import (
    compute_atr_and_volatility,
    compute_bollinger_bands,
    compute_macd,
    compute_quantitative_analysis,
    compute_rsi,
    compute_sma,
)
from app.research.routes import QuantitativeAnalysisRequest, analyze_quantitative


def test_compute_sma() -> None:
    prices = [Decimal(str(i)) for i in range(1, 11)]  # 1 to 10
    assert compute_sma(prices, 5) == Decimal("8.0")  # (6+7+8+9+10)/5 = 8.0
    assert compute_sma(prices, 20) is None


def test_compute_rsi_overbought_and_oversold() -> None:
    # Monotonically increasing prices -> RSI should be high (> 70)
    rising_prices = [Decimal(str(100 + i * 2)) for i in range(25)]
    rsi_high = compute_rsi(rising_prices, 14)
    assert rsi_high >= Decimal("70.0")

    # Monotonically decreasing prices -> RSI should be low (< 30)
    falling_prices = [Decimal(str(200 - i * 2)) for i in range(25)]
    rsi_low = compute_rsi(falling_prices, 14)
    assert rsi_low <= Decimal("30.0")

    # Short price history fallback
    assert compute_rsi([Decimal("100.0")], 14) == Decimal("50.0")


def test_compute_macd_and_crossover() -> None:
    # Create price series simulating a strong bullish reversal
    prices = [Decimal("100.0")] * 30 + [Decimal(str(100 + i * 3)) for i in range(1, 15)]
    macd_signal = compute_macd(prices)

    assert isinstance(macd_signal.macd, Decimal)
    assert isinstance(macd_signal.signal, Decimal)
    assert isinstance(macd_signal.histogram, Decimal)
    assert macd_signal.crossover in {
        MACDCrossover.BULLISH_CROSS,
        MACDCrossover.BEARISH_CROSS,
        MACDCrossover.NONE,
    }


def test_compute_bollinger_bands() -> None:
    prices = [Decimal(str(100 + (i % 5))) for i in range(25)]
    bb = compute_bollinger_bands(prices, period=20, num_std=2)

    assert bb.upper > bb.middle
    assert bb.middle > bb.lower
    assert bb.bandwidth_pct > Decimal("0.0")
    assert Decimal("0.0") <= bb.percent_b <= Decimal("1.5")


def test_compute_atr_and_volatility() -> None:
    highs = [Decimal("105.0")] * 20
    lows = [Decimal("95.0")] * 20
    closes = [Decimal("100.0")] * 20

    atr, ann_vol = compute_atr_and_volatility(highs, lows, closes, period=14)
    assert atr == Decimal("10.0")
    assert ann_vol >= Decimal("0.0")


def test_compute_atr_and_volatility_short_history_does_not_invent_volatility() -> None:
    atr, ann_vol = compute_atr_and_volatility(
        [Decimal("101.0")],
        [Decimal("99.0")],
        [Decimal("100.0")],
    )

    assert atr == Decimal("2.0")
    assert ann_vol == Decimal("0.0")


def test_compute_quantitative_analysis_full_report() -> None:
    # 60 sample bars
    bars = []
    base_price = 150.0
    for i in range(60):
        price = base_price + (i * 0.5)
        bars.append(
            {
                "timestamp": f"2026-07-{i % 28 + 1:02d}T12:00:00Z",
                "open": price - 0.2,
                "high": price + 1.0,
                "low": price - 1.0,
                "close": price,
                "volume": 100000 + (i * 1000),
            }
        )

    trace_id = uuid4()
    report = compute_quantitative_analysis(bars=bars, symbol="NVDA", trace_id=trace_id)

    assert report.symbol == "NVDA"
    assert report.trace_id == trace_id
    assert report.schema_version == "1.0"
    assert report.current_price > Decimal("0.0")
    assert report.trend in {TrendDirection.BULLISH, TrendDirection.BEARISH, TrendDirection.NEUTRAL}
    assert Decimal("0.0") <= report.momentum_score <= Decimal("100.0")
    assert report.rsi_condition in {
        RSICondition.OVERBOUGHT,
        RSICondition.OVERSOLD,
        RSICondition.NEUTRAL,
    }
    assert report.moving_averages.sma_20 is not None
    assert report.moving_averages.sma_50 is not None
    assert report.bollinger_bands.upper > report.bollinger_bands.lower
    assert len(report.summary) > 10


def test_compute_quantitative_analysis_empty_bars() -> None:
    trace_id = uuid4()
    report = compute_quantitative_analysis(bars=[], symbol="AAPL", trace_id=trace_id)

    assert report.symbol == "AAPL"
    assert report.current_price == Decimal("0.0")
    assert report.trend == TrendDirection.NEUTRAL
    assert report.momentum_score == Decimal("50.0")


@pytest.mark.asyncio
async def test_quantitative_route_normalizes_symbol_and_uses_bounded_bars() -> None:
    class StubGateway:
        def get_stock_bars(self, *, symbol: str, limit: int) -> list[dict[str, object]]:
            assert symbol == "AAPL"
            assert limit == 20
            return [
                {
                    "open": Decimal("100"),
                    "high": Decimal("101"),
                    "low": Decimal("99"),
                    "close": Decimal(str(100 + index)),
                    "volume": 1_000 + index,
                }
                for index in range(20)
            ]

    report = await analyze_quantitative(
        request=QuantitativeAnalysisRequest(symbol=" aapl ", bar_limit=20),
        current_user="operator@prism.local",
        gateway=StubGateway(),  # type: ignore[arg-type]
    )

    assert report.symbol == "AAPL"
    assert report.current_price == Decimal("119.00")


@pytest.mark.asyncio
async def test_quantitative_route_redacts_provider_errors() -> None:
    class FailingGateway:
        def get_stock_bars(self, *, symbol: str, limit: int) -> list[dict[str, object]]:
            raise RuntimeError("secret-provider-token should not be returned")

    with pytest.raises(HTTPException) as raised:
        await analyze_quantitative(
            request=QuantitativeAnalysisRequest(symbol="AAPL", bar_limit=20),
            current_user="operator@prism.local",
            gateway=FailingGateway(),  # type: ignore[arg-type]
        )

    assert raised.value.status_code == 502
    assert raised.value.detail == "Alpaca market data provider is temporarily unavailable"
    assert "secret-provider-token" not in str(raised.value.detail)


def test_quantitative_request_rejects_blank_symbols() -> None:
    with pytest.raises(ValueError, match="symbol must not be blank"):
        QuantitativeAnalysisRequest(symbol="   ")
