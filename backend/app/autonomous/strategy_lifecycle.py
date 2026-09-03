"""Deterministic strategy marking and adaptive exit policy evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from app.contracts.models import ExitPolicy, ExitReason, OptionStrategy

NEW_YORK = ZoneInfo("America/New_York")
REGULAR_OPEN = time(9, 30)
REGULAR_CLOSE = time(16, 0)


class StrategyMarkUnavailable(ValueError):
    """Fresh executable quotes cannot establish a strategy mark."""


@dataclass(frozen=True)
class AdaptiveExitEvaluation:
    current_return_pct: Decimal
    mfe_pct: Decimal
    profit_armed: bool
    score_failure_count: int
    exit_reason: ExitReason | None


def executable_liquidation_value(
    strategy: OptionStrategy,
    quotes: dict[str, dict[str, Any]],
    *,
    now: datetime,
    max_quote_age_seconds: int,
) -> Decimal:
    """Return the executable closing value: bid for longs, ask for shorts."""

    if now.tzinfo is None:
        raise StrategyMarkUnavailable("Strategy mark timestamp must be timezone-aware")
    total = Decimal("0")
    for leg in strategy.legs:
        quote = quotes.get(leg.symbol)
        if not isinstance(quote, dict):
            raise StrategyMarkUnavailable("Strategy leg quote is unavailable")
        timestamp = quote.get("quote_timestamp")
        if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
            raise StrategyMarkUnavailable("Strategy leg quote timestamp is unavailable")
        age = Decimal(str((now - timestamp.astimezone(UTC)).total_seconds()))
        if age < Decimal("-300") or age > Decimal(str(max_quote_age_seconds)):
            raise StrategyMarkUnavailable("Strategy leg quote is stale")
        try:
            bid = Decimal(str(quote["bid"]))
            ask = Decimal(str(quote["ask"]))
        except (KeyError, InvalidOperation, TypeError, ValueError) as exc:
            raise StrategyMarkUnavailable("Strategy leg quote is incomplete") from exc
        if bid <= 0 or ask < bid:
            raise StrategyMarkUnavailable("Strategy leg quote is invalid")
        price = bid if leg.side.value == "buy" else ask
        sign = Decimal("1") if leg.side.value == "buy" else Decimal("-1")
        total += sign * price * Decimal(leg.ratio_qty)
    if total <= 0:
        raise StrategyMarkUnavailable("Strategy has no positive executable liquidation value")
    return total


def strategy_return_pct(entry_debit: Decimal, liquidation_value: Decimal) -> Decimal:
    if entry_debit <= 0 or liquidation_value < 0:
        raise StrategyMarkUnavailable("Strategy return inputs are invalid")
    return ((liquidation_value - entry_debit) / entry_debit * Decimal("100")).quantize(
        Decimal("0.0001")
    )


def regular_session_minutes_elapsed(opened_at: datetime, now: datetime) -> int:
    """Count elapsed US regular-session minutes, excluding nights and weekends."""

    if opened_at.tzinfo is None or now.tzinfo is None or now <= opened_at:
        return 0
    start = opened_at.astimezone(NEW_YORK)
    end = now.astimezone(NEW_YORK)
    cursor: date = start.date()
    minutes = 0
    while cursor <= end.date():
        if cursor.weekday() < 5:
            session_open = datetime.combine(cursor, REGULAR_OPEN, tzinfo=NEW_YORK)
            session_close = datetime.combine(cursor, REGULAR_CLOSE, tzinfo=NEW_YORK)
            interval_start = max(start, session_open)
            interval_end = min(end, session_close)
            if interval_end > interval_start:
                minutes += int((interval_end - interval_start).total_seconds() // 60)
        cursor += timedelta(days=1)
    return minutes


def evaluate_adaptive_exit(
    policy: ExitPolicy,
    *,
    current_return_pct: Decimal,
    prior_mfe_pct: Decimal,
    profit_armed: bool,
    prior_score_failure_count: int,
    original_direction_score: Decimal | None,
    opposite_direction_score: Decimal | None,
    score_floor: Decimal,
    fresh_direction_evidence: bool,
    trading_minutes_elapsed: int,
    dte_days: int | None,
    force_flatten_due: bool,
) -> AdaptiveExitEvaluation:
    """Apply the authorized exit priority and return the next durable state."""

    mfe = max(prior_mfe_pct, current_return_pct)
    armed = profit_armed or current_return_pct >= policy.profit_arm_pct
    failures = prior_score_failure_count
    if fresh_direction_evidence and original_direction_score is not None:
        failures = 0 if original_direction_score >= score_floor else failures + 1

    reason: ExitReason | None = None
    if force_flatten_due:
        reason = ExitReason.HACKATHON_FORCE_FLATTEN
    elif dte_days is not None and dte_days <= policy.dte_threshold:
        reason = ExitReason.DTE_THRESHOLD
    elif current_return_pct <= -policy.hard_stop_loss_pct:
        reason = ExitReason.HARD_STOP_LOSS
    elif (
        fresh_direction_evidence
        and original_direction_score is not None
        and opposite_direction_score is not None
        and opposite_direction_score >= score_floor
        and opposite_direction_score > original_direction_score
    ):
        reason = ExitReason.OPPOSITE_DIRECTION
    elif failures >= policy.thesis_failure_cycles:
        reason = ExitReason.THESIS_INVALIDATED
    elif armed and current_return_pct <= mfe - policy.profit_trailing_giveback_points:
        reason = ExitReason.TRAILING_PROFIT
    elif current_return_pct >= policy.hard_take_profit_pct:
        reason = ExitReason.HARD_TAKE_PROFIT
    elif (
        trading_minutes_elapsed >= policy.time_stop_trading_minutes and mfe < policy.minimum_mfe_pct
    ):
        reason = ExitReason.STAGNATION_TIME_STOP
    elif trading_minutes_elapsed >= policy.max_hold_days * 390:
        reason = ExitReason.MAX_HOLD_DAYS

    return AdaptiveExitEvaluation(
        current_return_pct=current_return_pct,
        mfe_pct=mfe,
        profit_armed=armed,
        score_failure_count=failures,
        exit_reason=reason,
    )
