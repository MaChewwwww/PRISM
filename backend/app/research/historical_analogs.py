"""Point-in-time historical analog and conservative option-payoff economics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from app.contracts.models import OptionStrategy, OptionType


class HistoricalAnalogUnavailable(ValueError):
    """Historical coverage or comparable-event count is insufficient."""


@dataclass(frozen=True)
class HistoricalAnalogSummary:
    count: int
    direction: Literal["bullish", "bearish"]
    expected_return_pct: Decimal
    win_rate_pct: Decimal
    net_ev_r: Decimal
    observed_from: datetime
    observed_to: datetime
    outcome_returns_pct: tuple[Decimal, ...] = ()
    ev_method: str = "underlying_return_proxy"
    expected_profit_per_contract: Decimal | None = None
    expected_loss_per_contract: Decimal | None = None
    max_loss_per_contract: Decimal | None = None
    premium_per_contract: Decimal | None = None
    slippage_per_contract: Decimal | None = None
    fill_probability: Decimal | None = None
    reward_risk_ratio: Decimal | None = None
    horizon_bars: int = 5
    methodology_version: str = "nearest_non_overlapping_point_in_time_v2"


def _median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal("2")


def _features(prices: list[Decimal], volumes: list[Decimal], index: int) -> tuple[Decimal, ...]:
    one_day = (prices[index] - prices[index - 1]) / prices[index - 1] * Decimal("100")
    five_day = (prices[index] - prices[index - 5]) / prices[index - 5] * Decimal("100")
    twenty_day = (prices[index] - prices[index - 20]) / prices[index - 20] * Decimal("100")
    daily_returns = [
        (prices[pos] - prices[pos - 1]) / prices[pos - 1] * Decimal("100")
        for pos in range(index - 19, index + 1)
    ]
    mean = sum(daily_returns, Decimal("0")) / Decimal(len(daily_returns))
    variance = sum((value - mean) ** 2 for value in daily_returns) / Decimal(len(daily_returns))
    volatility = variance.sqrt()
    prior_volume = volumes[index - 20 : index]
    average_volume = sum(prior_volume, Decimal("0")) / Decimal(len(prior_volume))
    volume_ratio = volumes[index] / average_volume if average_volume > 0 else Decimal("1")
    return one_day, five_day, twenty_day, volatility, volume_ratio


def compute_historical_analogs(
    bars: list[dict[str, Any]],
    *,
    direction: Literal["bullish", "bearish"],
    now: datetime,
    minimum_events: int = 30,
    horizon_bars: int = 5,
    strategy: OptionStrategy | None = None,
    underlying_price: Decimal | None = None,
    quotes: dict[str, dict[str, Any]] | None = None,
    max_spread_pct: Decimal = Decimal("10"),
    event_category: str = "other",
) -> HistoricalAnalogSummary:
    if now.tzinfo is None or horizon_bars <= 0 or minimum_events <= 0:
        raise HistoricalAnalogUnavailable("Analog inputs are invalid")
    normalized: list[tuple[datetime, Decimal, Decimal]] = []
    for bar in bars:
        try:
            timestamp = bar["timestamp"]
            if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
                continue
            close = Decimal(str(bar["close"]))
            if close <= 0:
                continue
            volume = Decimal(str(bar.get("volume", "0")))
            normalized.append((timestamp.astimezone(UTC), close, max(Decimal("0"), volume)))
        except (KeyError, TypeError, ValueError):
            continue
    normalized.sort(key=lambda item: item[0])
    cutoff = now.astimezone(UTC) - timedelta(days=365 * 5)
    normalized = [
        (timestamp, close, volume)
        for timestamp, close, volume in normalized
        if cutoff <= timestamp <= now.astimezone(UTC)
    ]
    if len(normalized) < 21 + horizon_bars:
        raise HistoricalAnalogUnavailable("Five-year historical coverage is insufficient")

    prices = [item[1] for item in normalized]
    volumes = [item[2] for item in normalized]
    current_features = _features(prices, volumes, len(normalized) - 1)
    candidate_rows: list[tuple[int, tuple[Decimal, ...]]] = []
    for index in range(20, len(normalized) - horizon_bars):
        features = _features(prices, volumes, index)
        setup_move = features[1]
        setup_matches = (direction == "bullish" and setup_move > 0) or (
            direction == "bearish" and setup_move < 0
        )
        if not setup_matches:
            continue
        candidate_rows.append((index, features))
    if len(candidate_rows) < minimum_events:
        raise HistoricalAnalogUnavailable(
            f"Only {len(candidate_rows)} comparable events observed; {minimum_events} required"
        )

    feature_columns = list(zip(*(features for _, features in candidate_rows), strict=True))
    medians = [_median(list(column)) for column in feature_columns]
    scales = []
    for column, median in zip(feature_columns, medians, strict=True):
        mad = _median([abs(value - median) for value in column])
        scales.append(mad if mad > 0 else Decimal("1"))
    ranked = sorted(
        candidate_rows,
        key=lambda row: sum(
            (
                abs(feature - current) / scale
                for feature, current, scale in zip(row[1], current_features, scales, strict=True)
            ),
            Decimal("0"),
        ),
    )
    selected: list[int] = []
    for index, _features_row in ranked:
        candidate_start = index - 20
        candidate_end = index + horizon_bars
        if any(
            not (candidate_end < chosen - 20 or candidate_start > chosen + horizon_bars)
            for chosen in selected
        ):
            continue
        selected.append(index)
        if len(selected) == minimum_events:
            break
    if len(selected) < minimum_events:
        raise HistoricalAnalogUnavailable(
            f"Only {len(selected)} non-overlapping comparable events observed; "
            f"{minimum_events} required"
        )

    realized: list[Decimal] = []
    for index in selected:
        outcome_start = prices[index]
        outcome_end = prices[index + horizon_bars]
        outcome_move = (outcome_end - outcome_start) / outcome_start * Decimal("100")
        # Store the return in the chosen direction so a positive value is
        # always a favorable historical outcome, while retaining losses for a
        # genuine risk/EV calculation.
        realized.append(outcome_move if direction == "bullish" else -outcome_move)

    expected = sum(realized, Decimal("0")) / Decimal(str(len(realized)))
    wins = sum(1 for value in realized if value > 0)
    win_rate = Decimal(str(wins)) / Decimal(str(len(realized))) * Decimal("100")
    # R is defined against the observed adverse move in the same sample.  A
    # zero adverse move cannot establish an EV and therefore fails closed.
    adverse = [value for value in realized if value < 0]
    risk = abs(min(adverse)) if adverse else Decimal("0")
    if risk <= 0:
        raise HistoricalAnalogUnavailable("Comparable events contain no observed adverse move")
    net_ev_r = expected / risk
    summary = HistoricalAnalogSummary(
        count=len(realized),
        direction=direction,
        expected_return_pct=round(expected, 4),
        win_rate_pct=round(win_rate, 4),
        net_ev_r=round(net_ev_r, 4),
        observed_from=min(normalized[index][0] for index in selected),
        observed_to=max(normalized[index + horizon_bars][0] for index in selected),
        outcome_returns_pct=tuple(realized),
        horizon_bars=horizon_bars,
        methodology_version=(
            f"nearest_non_overlapping_point_in_time_v2:event_category={event_category}"
        ),
    )
    if strategy is not None:
        if underlying_price is None or quotes is None:
            raise HistoricalAnalogUnavailable("Option payoff inputs are incomplete")
        return compute_option_payoff_ev(
            summary,
            strategy,
            underlying_price=underlying_price,
            quotes=quotes,
            max_spread_pct=max_spread_pct,
        )
    return summary


def compute_option_payoff_ev(
    summary: HistoricalAnalogSummary,
    strategy: OptionStrategy,
    *,
    underlying_price: Decimal,
    quotes: dict[str, dict[str, Any]],
    contract_multiplier: Decimal = Decimal("100"),
    max_spread_pct: Decimal = Decimal("10"),
) -> HistoricalAnalogSummary:
    """Revalue every analog through the selected option structure.

    The model uses only observed inputs: midpoint premium, adverse NBBO touch
    (the slippage bound), and a fill probability derived from each leg's
    observed spread relative to the authorized maximum.  A non-fill is a zero
    P/L outcome.  Payoff is marked at expiration using intrinsic value, so both
    single-leg and debit-spread premium, slippage, and fill probability are
    represented in the resulting EV. The observed entry slippage is charged a
    second time as a conservative liquidation-cost estimate at the actual
    holding horizon. This remains a model, not historical option-price proof.
    """

    if not summary.outcome_returns_pct or underlying_price <= 0:
        raise HistoricalAnalogUnavailable("Option EV inputs are unavailable")
    if contract_multiplier <= 0 or max_spread_pct <= 0:
        raise HistoricalAnalogUnavailable("Option EV parameters are invalid")

    entry_cashflow = Decimal("0")
    midpoint_debit = Decimal("0")
    slippage = Decimal("0")
    fill_probability = Decimal("1")
    leg_data: list[tuple[Any, Decimal, Decimal, Decimal]] = []
    for leg in strategy.legs:
        quote = quotes.get(leg.symbol)
        if not isinstance(quote, dict):
            raise HistoricalAnalogUnavailable("Option quote is unavailable for EV")
        try:
            bid = Decimal(str(quote["bid"]))
            ask = Decimal(str(quote["ask"]))
        except (KeyError, InvalidOperation, TypeError, ValueError) as exc:
            raise HistoricalAnalogUnavailable("Option quote is incomplete for EV") from exc
        if bid <= 0 or ask < bid:
            raise HistoricalAnalogUnavailable("Option quote is invalid for EV")
        midpoint = (bid + ask) / Decimal("2")
        spread_pct = (ask - bid) / midpoint * Decimal("100")
        if spread_pct < 0 or spread_pct > max_spread_pct:
            raise HistoricalAnalogUnavailable("Option quote spread is unavailable for EV")
        leg_fill = max(Decimal("0"), min(Decimal("1"), Decimal("1") - spread_pct / max_spread_pct))
        fill_probability *= leg_fill
        if leg.side.value == "buy":
            touch = ask
            entry_cashflow -= touch * contract_multiplier
            midpoint_debit += midpoint * contract_multiplier
        else:
            touch = bid
            entry_cashflow += touch * contract_multiplier
            midpoint_debit -= midpoint * contract_multiplier
        slippage += abs(touch - midpoint) * contract_multiplier
        leg_data.append((leg, touch, bid, ask))

    if midpoint_debit <= 0:
        raise HistoricalAnalogUnavailable("Option structure has no positive debit")

    profits: list[Decimal] = []
    for return_pct in summary.outcome_returns_pct:
        # ``outcome_returns_pct`` is stored in the strategy direction so the
        # descriptive EV fields stay intuitive (positive means favorable).
        # Put/short-direction outcomes therefore need to be mapped back to the
        # actual underlying return before applying option intrinsic value.
        actual_return_pct = return_pct if summary.direction == "bullish" else -return_pct
        terminal_price = underlying_price * (Decimal("1") + actual_return_pct / Decimal("100"))
        terminal_price = max(Decimal("0"), terminal_price)
        payoff = entry_cashflow
        for leg, _touch, _bid, _ask in leg_data:
            intrinsic = max(
                Decimal("0"),
                terminal_price - leg.strike_price
                if leg.option_type is OptionType.CALL
                else leg.strike_price - terminal_price,
            )
            signed_payoff = intrinsic * contract_multiplier
            payoff += signed_payoff if leg.side.value == "buy" else -signed_payoff
        profits.append(payoff - slippage)

    if not profits:
        raise HistoricalAnalogUnavailable("Option payoff outcomes are unavailable")
    mean_profit = sum(profits, Decimal("0")) / Decimal(str(len(profits)))
    expected_profit = mean_profit * fill_probability
    losses = [value for value in profits if value < 0]
    expected_loss = (
        abs(sum(losses, Decimal("0")) / Decimal(str(len(losses))) * fill_probability)
        if losses
        else Decimal("0")
    )
    max_loss = abs(min(profits)) if min(profits) < 0 else Decimal("0")
    # A debit structure's paid premium is its hard-loss floor.  If no sampled
    # outcome reaches zero intrinsic value, retain that observable floor.
    max_loss = max(max_loss, abs(entry_cashflow))
    if max_loss <= 0:
        raise HistoricalAnalogUnavailable("Option payoff has no measurable maximum loss")
    positive = [value for value in profits if value > 0]
    expected_gain = (
        sum(positive, Decimal("0")) / Decimal(str(len(positive))) * fill_probability
        if positive
        else Decimal("0")
    )
    reward_risk = expected_gain / expected_loss if expected_loss > 0 else Decimal("0")
    net_ev_r = expected_profit / max_loss
    return HistoricalAnalogSummary(
        count=summary.count,
        direction=summary.direction,
        expected_return_pct=summary.expected_return_pct,
        win_rate_pct=summary.win_rate_pct,
        net_ev_r=round(net_ev_r, 4),
        observed_from=summary.observed_from,
        observed_to=summary.observed_to,
        outcome_returns_pct=summary.outcome_returns_pct,
        ev_method="option_payoff_intrinsic_actual_horizon_round_trip_slippage_v2",
        expected_profit_per_contract=round(expected_profit, 4),
        expected_loss_per_contract=round(expected_loss, 4),
        max_loss_per_contract=round(max_loss, 4),
        premium_per_contract=round(midpoint_debit, 4),
        slippage_per_contract=round(slippage, 4),
        fill_probability=round(fill_probability, 6),
        reward_risk_ratio=round(reward_risk, 4),
        horizon_bars=summary.horizon_bars,
        methodology_version=summary.methodology_version,
    )
