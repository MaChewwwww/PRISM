from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.contracts.models import (
    BollingerBands,
    MACDCrossover,
    MACDSignal,
    MovingAverages,
    QuantitativeAnalysisReport,
    RSICondition,
    TrendDirection,
)


def _to_decimal(val: Any) -> Decimal:
    return Decimal(str(val))


def compute_sma(prices: list[Decimal], window: int) -> Decimal | None:
    """Compute Simple Moving Average over the trailing window."""
    if len(prices) < window or window <= 0:
        return None
    sample = prices[-window:]
    return sum(sample) / Decimal(str(window))


def compute_ema_series(prices: list[Decimal], period: int) -> list[Decimal]:
    """Compute Exponential Moving Average series over prices."""
    if not prices or period <= 0:
        return []
    if len(prices) < period:
        # Fallback to SMA if fewer than period
        avg = sum(prices) / Decimal(str(len(prices)))
        return [avg] * len(prices)

    multiplier = Decimal("2.0") / Decimal(str(period + 1))
    # Initial EMA is the SMA of first `period` elements
    initial_sma = sum(prices[:period]) / Decimal(str(period))
    ema_series = [initial_sma]

    for price in prices[period:]:
        prev_ema = ema_series[-1]
        current_ema = (price - prev_ema) * multiplier + prev_ema
        ema_series.append(current_ema)

    # Pad the beginning so length matches prices
    padding = [initial_sma] * (period - 1)
    return padding + ema_series


def compute_rsi(prices: list[Decimal], period: int = 14) -> Decimal:
    """Compute Relative Strength Index (RSI 14) bounded between 0 and 100."""
    if len(prices) < period + 1:
        return Decimal("50.0")

    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    recent_changes = changes[-period:]

    gains = [c for c in recent_changes if c > Decimal("0")]
    losses = [abs(c) for c in recent_changes if c < Decimal("0")]

    avg_gain = sum(gains) / Decimal(str(period)) if gains else Decimal("0")
    avg_loss = sum(losses) / Decimal(str(period)) if losses else Decimal("0")

    if avg_loss == Decimal("0"):
        return Decimal("100.0") if avg_gain > Decimal("0") else Decimal("50.0")

    rs = avg_gain / avg_loss
    rsi = Decimal("100.0") - (Decimal("100.0") / (Decimal("1.0") + rs))
    return min(Decimal("100.0"), max(Decimal("0.0"), round(rsi, 2)))


def compute_macd(
    prices: list[Decimal],
    fast: int = 12,
    slow: int = 26,
    signal_span: int = 9,
) -> MACDSignal:
    """Compute MACD Line, Signal Line, Histogram, and Crossover state."""
    if len(prices) < slow:
        return MACDSignal(
            macd=Decimal("0.0"),
            signal=Decimal("0.0"),
            histogram=Decimal("0.0"),
            crossover=MACDCrossover.NONE,
        )

    ema_fast = compute_ema_series(prices, fast)
    ema_slow = compute_ema_series(prices, slow)

    macd_series = [f - s for f, s in zip(ema_fast, ema_slow, strict=False)]
    signal_series = compute_ema_series(macd_series, signal_span)

    latest_macd = macd_series[-1]
    latest_signal = signal_series[-1]
    latest_hist = latest_macd - latest_signal

    # Determine crossover by comparing against prior bar
    crossover = MACDCrossover.NONE
    if len(macd_series) >= 2 and len(signal_series) >= 2:
        prev_macd = macd_series[-2]
        prev_signal = signal_series[-2]
        prev_hist = prev_macd - prev_signal

        if prev_hist <= Decimal("0") and latest_hist > Decimal("0"):
            crossover = MACDCrossover.BULLISH_CROSS
        elif prev_hist >= Decimal("0") and latest_hist < Decimal("0"):
            crossover = MACDCrossover.BEARISH_CROSS

    return MACDSignal(
        macd=round(latest_macd, 4),
        signal=round(latest_signal, 4),
        histogram=round(latest_hist, 4),
        crossover=crossover,
    )


def compute_bollinger_bands(
    prices: list[Decimal],
    period: int = 20,
    num_std: int = 2,
) -> BollingerBands:
    """Compute 20-period Bollinger Bands (Upper, Middle, Lower, Bandwidth, %B)."""
    if len(prices) < period:
        current = prices[-1] if prices else Decimal("100.0")
        return BollingerBands(
            upper=current,
            middle=current,
            lower=current,
            bandwidth_pct=Decimal("0.0"),
            percent_b=Decimal("0.5"),
        )

    sample = prices[-period:]
    middle = sum(sample) / Decimal(str(period))

    variance = sum((p - middle) ** 2 for p in sample) / Decimal(str(period))
    std_dev = Decimal(str(math.sqrt(float(variance))))

    std_offset = Decimal(str(num_std)) * std_dev
    upper = middle + std_offset
    lower = middle - std_offset

    bandwidth = (
        ((upper - lower) / middle) * Decimal("100.0") if middle > Decimal("0") else Decimal("0.0")
    )

    current_price = prices[-1]
    denom = upper - lower
    percent_b = (current_price - lower) / denom if denom > Decimal("0") else Decimal("0.5")

    return BollingerBands(
        upper=round(upper, 2),
        middle=round(middle, 2),
        lower=round(lower, 2),
        bandwidth_pct=round(bandwidth, 2),
        percent_b=round(percent_b, 4),
    )


def compute_atr_and_volatility(
    highs: list[Decimal],
    lows: list[Decimal],
    closes: list[Decimal],
    period: int = 14,
) -> tuple[Decimal, Decimal]:
    """Compute Average True Range (14) and 20-day Annualized Volatility (%)."""
    if len(closes) < 2:
        return Decimal("1.0"), Decimal("20.0")

    true_ranges: list[Decimal] = []
    for i in range(1, len(closes)):
        high_val = highs[i]
        low_val = lows[i]
        prev_c = closes[i - 1]
        tr = max(high_val - low_val, abs(high_val - prev_c), abs(low_val - prev_c))
        true_ranges.append(tr)

    atr_sample = true_ranges[-period:] if len(true_ranges) >= period else true_ranges
    atr = sum(atr_sample) / Decimal(str(len(atr_sample))) if atr_sample else Decimal("1.0")

    # Annualized volatility from returns: std_dev(daily returns) * sqrt(252) * 100
    if len(closes) >= 20:
        vol_sample = closes[-20:]
        returns = [
            float((vol_sample[j] - vol_sample[j - 1]) / vol_sample[j - 1])
            for j in range(1, len(vol_sample))
        ]
        mean_ret = sum(returns) / len(returns)
        var_ret = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
        daily_std = math.sqrt(var_ret)
        ann_vol = Decimal(str(daily_std * math.sqrt(252) * 100.0))
    else:
        ann_vol = Decimal("20.0")

    return round(atr, 2), round(ann_vol, 2)


def compute_quantitative_analysis(
    bars: list[dict[str, Any]],
    symbol: str,
    trace_id: UUID,
) -> QuantitativeAnalysisReport:
    """Deterministically analyze market bars to compute all technical indicators and momentum."""
    if not bars:
        now_utc = datetime.now(UTC)
        return QuantitativeAnalysisReport(
            id=uuid4(),
            trace_id=trace_id,
            created_at=now_utc,
            symbol=symbol,
            current_price=Decimal("0.0"),
            trend=TrendDirection.NEUTRAL,
            momentum_score=Decimal("50.0"),
            rsi_14=Decimal("50.0"),
            rsi_condition=RSICondition.NEUTRAL,
            macd=MACDSignal(
                macd=Decimal("0.0"),
                signal=Decimal("0.0"),
                histogram=Decimal("0.0"),
                crossover=MACDCrossover.NONE,
            ),
            moving_averages=MovingAverages(),
            bollinger_bands=BollingerBands(
                upper=Decimal("0.0"),
                middle=Decimal("0.0"),
                lower=Decimal("0.0"),
                bandwidth_pct=Decimal("0.0"),
                percent_b=Decimal("0.5"),
            ),
            atr_14=Decimal("0.0"),
            volatility_annualized_pct=Decimal("0.0"),
            volume_surge_ratio=Decimal("1.0"),
            summary="No bar data available for quantitative analysis.",
        )

    closes = [_to_decimal(b["close"]) for b in bars]
    highs = [_to_decimal(b.get("high", b["close"])) for b in bars]
    lows = [_to_decimal(b.get("low", b["close"])) for b in bars]
    volumes = [_to_decimal(b.get("volume", 0)) for b in bars]

    current_price = closes[-1]

    # 1. Moving Averages
    sma_20 = compute_sma(closes, 20)
    sma_50 = compute_sma(closes, 50)
    sma_200 = compute_sma(closes, 200)

    p_vs_sma20 = (
        round(((current_price - sma_20) / sma_20) * Decimal("100.0"), 2) if sma_20 else None
    )
    p_vs_sma50 = (
        round(((current_price - sma_50) / sma_50) * Decimal("100.0"), 2) if sma_50 else None
    )
    p_vs_sma200 = (
        round(((current_price - sma_200) / sma_200) * Decimal("100.0"), 2) if sma_200 else None
    )

    moving_averages = MovingAverages(
        sma_20=round(sma_20, 2) if sma_20 else None,
        sma_50=round(sma_50, 2) if sma_50 else None,
        sma_200=round(sma_200, 2) if sma_200 else None,
        price_vs_sma20_pct=p_vs_sma20,
        price_vs_sma50_pct=p_vs_sma50,
        price_vs_sma200_pct=p_vs_sma200,
    )

    # 2. RSI (14)
    rsi_14 = compute_rsi(closes, 14)
    if rsi_14 >= Decimal("70.0"):
        rsi_condition = RSICondition.OVERBOUGHT
    elif rsi_14 <= Decimal("30.0"):
        rsi_condition = RSICondition.OVERSOLD
    else:
        rsi_condition = RSICondition.NEUTRAL

    # 3. MACD
    macd = compute_macd(closes)

    # 4. Bollinger Bands
    bollinger = compute_bollinger_bands(closes, 20, 2)

    # 5. ATR & Volatility
    atr_14, vol_ann = compute_atr_and_volatility(highs, lows, closes, 14)

    # 6. Volume Surge Ratio
    if len(volumes) > 1:
        prev_vols = volumes[:-1]
        avg_vol = sum(prev_vols[-20:]) / Decimal(str(min(20, len(prev_vols))))
        latest_vol = volumes[-1]
        vol_surge = latest_vol / avg_vol if avg_vol > Decimal("0") else Decimal("1.0")
    else:
        vol_surge = Decimal("1.0")

    # 7. Trend & Composite Momentum Score (0 to 100)
    # Component 1: Moving Averages Gradient (40 max points, centered at 20 neutral)
    sma_components: list[tuple[Decimal, Decimal]] = []
    if p_vs_sma20 is not None:
        # Scale: -5% is 0.0, 0% is 0.5, +5% is 1.0
        factor_20 = min(
            Decimal("1.0"),
            max(Decimal("0.0"), Decimal("0.5") + (p_vs_sma20 / Decimal("10.0"))),
        )
        sma_components.append((factor_20, Decimal("0.5")))
    if p_vs_sma50 is not None:
        factor_50 = min(
            Decimal("1.0"),
            max(Decimal("0.0"), Decimal("0.5") + (p_vs_sma50 / Decimal("10.0"))),
        )
        sma_components.append((factor_50, Decimal("0.3")))
    if p_vs_sma200 is not None:
        factor_200 = min(
            Decimal("1.0"),
            max(Decimal("0.0"), Decimal("0.5") + (p_vs_sma200 / Decimal("10.0"))),
        )
        sma_components.append((factor_200, Decimal("0.2")))

    if sma_components:
        total_w = sum((w for _, w in sma_components), Decimal("0"))
        weighted_factor = sum((f * w for f, w in sma_components), Decimal("0")) / total_w
        sma_points = weighted_factor * Decimal("40.0")
    else:
        sma_points = Decimal("20.0")

    # Component 2: RSI 14 (30 max points, centered at 15 neutral)
    rsi_points = (rsi_14 / Decimal("100.0")) * Decimal("30.0")

    # Component 3: MACD (30 max points, centered at 15 neutral)
    norm_divisor = (
        atr_14 if atr_14 > Decimal("0") else (_to_decimal(current_price) * Decimal("0.02"))
    )
    hist_ratio = macd.histogram / norm_divisor if norm_divisor > Decimal("0") else Decimal("0.0")
    hist_adjustment = min(Decimal("10.0"), max(Decimal("-10.0"), hist_ratio * Decimal("10.0")))
    macd_base = Decimal("15.0") + hist_adjustment

    crossover_adjustment = Decimal("0.0")
    if macd.crossover == MACDCrossover.BULLISH_CROSS:
        crossover_adjustment = Decimal("5.0")
    elif macd.crossover == MACDCrossover.BEARISH_CROSS:
        crossover_adjustment = Decimal("-5.0")

    macd_points = min(Decimal("30.0"), max(Decimal("0.0"), macd_base + crossover_adjustment))

    total_momentum = sma_points + rsi_points + macd_points
    momentum_score = min(Decimal("100.0"), max(Decimal("0.0"), round(total_momentum, 1)))

    if momentum_score >= Decimal("60.0"):
        trend = TrendDirection.BULLISH
    elif momentum_score <= Decimal("40.0"):
        trend = TrendDirection.BEARISH
    else:
        trend = TrendDirection.NEUTRAL

    # Build deterministic rule-based summary string
    sma_desc = (
        f"above 50d SMA (+{p_vs_sma50}%)"
        if p_vs_sma50 and p_vs_sma50 > Decimal("0")
        else (f"below 50d SMA ({p_vs_sma50}%)" if p_vs_sma50 else "near moving averages")
    )
    summary = (
        f"{trend.value.upper()} trend ({momentum_score}/100 momentum). "
        f"Price is {sma_desc} with RSI at {rsi_14} ({rsi_condition.value}), "
        f"MACD hist at {macd.histogram}, and {round(vol_surge, 2)}x volume surge."
    )

    now_utc = datetime.now(UTC)
    return QuantitativeAnalysisReport(
        id=uuid4(),
        trace_id=trace_id,
        created_at=now_utc,
        symbol=symbol,
        current_price=round(current_price, 2),
        trend=trend,
        momentum_score=momentum_score,
        rsi_14=rsi_14,
        rsi_condition=rsi_condition,
        macd=macd,
        moving_averages=moving_averages,
        bollinger_bands=bollinger,
        atr_14=atr_14,
        volatility_annualized_pct=vol_ann,
        volume_surge_ratio=round(vol_surge, 2),
        summary=summary,
    )
