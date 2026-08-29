from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

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
