from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from app.contracts.models import (
    MACDCrossover,
    MACDSignal,
    RSICondition,
    TrendConfirmation,
    TrendDirection,
)
from app.research.quant_engine import (
    compute_atr_and_volatility,
    compute_bollinger_bands,
    compute_gap_and_displacement,
    compute_macd,
    compute_quantitative_analysis,
    compute_rsi,
    compute_sma,
    compute_trend_confirmation,
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


def test_compute_atr_and_volatility_short_history_does_not_invent_volatility() -> None:
    atr, ann_vol = compute_atr_and_volatility(
        [Decimal("101.0")],
        [Decimal("99.0")],
        [Decimal("100.0")],
    )

    assert atr == Decimal("2.0")
    assert ann_vol == Decimal("0.0")


def test_compute_gap_and_displacement() -> None:
    # 10 daily bars: day 0 to 9
    # Day 8: close=100.0. Day 9: open=105.0 (+5% gap), close=108.0 (+8% 1d return)
    bars = [
        {"open": 90.0 + i, "close": 91.0 + i, "high": 92.0 + i, "low": 89.0 + i} for i in range(8)
    ]
    bars.append({"open": 98.0, "close": 100.0, "high": 101.0, "low": 97.0})  # Day 8 (prior)
    bars.append({"open": 105.0, "close": 108.0, "high": 110.0, "low": 104.0})  # Day 9 (latest)

    disp = compute_gap_and_displacement(bars)

    assert disp.gap_size_pct == Decimal("5.0")  # (105 - 100) / 100 * 100
    assert disp.displacement_1d_pct == Decimal("8.0")  # (108 - 100) / 100 * 100
    assert disp.displacement_3d_pct is not None
    assert disp.displacement_5d_pct is not None
    assert disp.displacement_20d_pct is None  # Only 10 bars available


def test_compute_trend_confirmation_regimes() -> None:
    # 1. Strong uptrend: Price (130) > 20 (120) > 50 (110) > 200 (100)
    conf_up = compute_trend_confirmation(
        current_price=Decimal("130.0"),
        sma_20=Decimal("120.0"),
        sma_50=Decimal("110.0"),
        sma_200=Decimal("100.0"),
        rsi_14=Decimal("60.0"),
        macd=MACDSignal(
            macd=Decimal("2.0"),
            signal=Decimal("1.5"),
            histogram=Decimal("0.5"),
            crossover=MACDCrossover.NONE,
        ),
        percent_b=Decimal("0.8"),
    )
    assert conf_up == TrendConfirmation.STRONG_UPTREND_CONFIRMED

    # 2. Pullback in uptrend: 20 > 50 > 200, Price dipped below 20 (118 < 120)
    conf_pullback = compute_trend_confirmation(
        current_price=Decimal("118.0"),
        sma_20=Decimal("120.0"),
        sma_50=Decimal("110.0"),
        sma_200=Decimal("100.0"),
        rsi_14=Decimal("45.0"),
        macd=MACDSignal(
            macd=Decimal("1.0"),
            signal=Decimal("1.2"),
            histogram=Decimal("-0.2"),
            crossover=MACDCrossover.NONE,
        ),
        percent_b=Decimal("0.4"),
    )
    assert conf_pullback == TrendConfirmation.PULLBACK_IN_UPTREND

    # 3. Breakdown: Price (90) < 20 (95) < 50 (100) < 200 (110)
    conf_break = compute_trend_confirmation(
        current_price=Decimal("90.0"),
        sma_20=Decimal("95.0"),
        sma_50=Decimal("100.0"),
        sma_200=Decimal("110.0"),
        rsi_14=Decimal("38.0"),
        macd=MACDSignal(
            macd=Decimal("-2.0"),
            signal=Decimal("-1.5"),
            histogram=Decimal("-0.5"),
            crossover=MACDCrossover.NONE,
        ),
        percent_b=Decimal("0.1"),
    )
    assert conf_break == TrendConfirmation.BREAKDOWN_CONFIRMED

    # 4. Oversold bounce
    conf_oversold = compute_trend_confirmation(
        current_price=Decimal("50.0"),
        sma_20=Decimal("55.0"),
        sma_50=None,
        sma_200=None,
        rsi_14=Decimal("25.0"),
        macd=MACDSignal(
            macd=Decimal("-3.0"),
            signal=Decimal("-3.2"),
            histogram=Decimal("0.2"),
            crossover=MACDCrossover.BULLISH_CROSS,
        ),
        percent_b=Decimal("0.02"),
    )
    assert conf_oversold == TrendConfirmation.OVERSOLD_BOUNCE


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
    assert report.trend_confirmation in {
        TrendConfirmation.STRONG_UPTREND_CONFIRMED,
        TrendConfirmation.PULLBACK_IN_UPTREND,
        TrendConfirmation.GOLDEN_CROSS,
        TrendConfirmation.RANGE_BOUND,
        TrendConfirmation.OVERSOLD_BOUNCE,
        TrendConfirmation.DEATH_CROSS,
        TrendConfirmation.BREAKDOWN_CONFIRMED,
    }
    assert report.price_displacement.gap_size_pct is not None
    assert report.price_displacement.displacement_1d_pct is not None
    assert report.price_displacement.displacement_5d_pct is not None
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
    assert report.trend_confirmation == TrendConfirmation.RANGE_BOUND
    assert report.price_displacement.gap_size_pct == Decimal("0.0")
    assert report.momentum_score == Decimal("50.0")
