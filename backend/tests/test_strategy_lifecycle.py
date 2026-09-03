from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.autonomous.strategy_lifecycle import (
    evaluate_adaptive_exit,
    executable_liquidation_value,
    strategy_return_pct,
)
from app.contracts.models import ExitPolicy, OptionLeg, OptionSide, OptionStrategy, OptionType


def _strategy() -> OptionStrategy:
    return OptionStrategy(
        kind="call_debit_spread",
        legs=[
            OptionLeg(
                symbol="NVDA260918C00100000",
                underlying="NVDA",
                expiration="2026-09-18",
                option_type=OptionType.CALL,
                side=OptionSide.BUY,
                strike_price=Decimal("100"),
            ),
            OptionLeg(
                symbol="NVDA260918C00110000",
                underlying="NVDA",
                expiration="2026-09-18",
                option_type=OptionType.CALL,
                side=OptionSide.SELL,
                strike_price=Decimal("110"),
            ),
        ],
        limit_price=Decimal("2"),
    )


def test_strategy_mark_uses_long_bid_minus_short_ask() -> None:
    now = datetime(2026, 9, 2, 15, tzinfo=UTC)
    mark = executable_liquidation_value(
        _strategy(),
        {
            "NVDA260918C00100000": {"bid": "3.00", "ask": "3.10", "quote_timestamp": now},
            "NVDA260918C00110000": {"bid": "0.40", "ask": "0.50", "quote_timestamp": now},
        },
        now=now,
        max_quote_age_seconds=30,
    )
    assert mark == Decimal("2.50")
    assert strategy_return_pct(Decimal("2"), mark) == Decimal("25.0000")


def test_adaptive_profit_boundaries_and_loss_stop() -> None:
    policy = ExitPolicy()
    armed = evaluate_adaptive_exit(
        policy,
        current_return_pct=Decimal("20"),
        prior_mfe_pct=Decimal("0"),
        profit_armed=False,
        prior_score_failure_count=0,
        original_direction_score=None,
        opposite_direction_score=None,
        score_floor=Decimal("78"),
        fresh_direction_evidence=False,
        trading_minutes_elapsed=0,
        dte_days=10,
        force_flatten_due=False,
    )
    assert armed.profit_armed and armed.exit_reason is None
    trailing = evaluate_adaptive_exit(
        policy,
        current_return_pct=Decimal("17"),
        prior_mfe_pct=Decimal("27"),
        profit_armed=True,
        prior_score_failure_count=0,
        original_direction_score=None,
        opposite_direction_score=None,
        score_floor=Decimal("78"),
        fresh_direction_evidence=False,
        trading_minutes_elapsed=0,
        dte_days=10,
        force_flatten_due=False,
    )
    assert trailing.exit_reason.value == "trailing_profit"
    hard_profit = evaluate_adaptive_exit(
        policy,
        current_return_pct=Decimal("40"),
        prior_mfe_pct=Decimal("20"),
        profit_armed=True,
        prior_score_failure_count=0,
        original_direction_score=None,
        opposite_direction_score=None,
        score_floor=Decimal("78"),
        fresh_direction_evidence=False,
        trading_minutes_elapsed=0,
        dte_days=10,
        force_flatten_due=False,
    )
    assert hard_profit.exit_reason.value == "hard_take_profit"
    hard_stop = evaluate_adaptive_exit(
        policy,
        current_return_pct=Decimal("-50"),
        prior_mfe_pct=Decimal("0"),
        profit_armed=False,
        prior_score_failure_count=0,
        original_direction_score=None,
        opposite_direction_score=None,
        score_floor=Decimal("78"),
        fresh_direction_evidence=False,
        trading_minutes_elapsed=0,
        dte_days=10,
        force_flatten_due=False,
    )
    assert hard_stop.exit_reason.value == "hard_stop_loss"


def test_thesis_and_stagnation_exit_boundaries() -> None:
    policy = ExitPolicy()
    first_failure = evaluate_adaptive_exit(
        policy,
        current_return_pct=Decimal("0"),
        prior_mfe_pct=Decimal("0"),
        profit_armed=False,
        prior_score_failure_count=0,
        original_direction_score=Decimal("77"),
        opposite_direction_score=Decimal("20"),
        score_floor=Decimal("78"),
        fresh_direction_evidence=True,
        trading_minutes_elapsed=0,
        dte_days=10,
        force_flatten_due=False,
    )
    assert first_failure.exit_reason is None and first_failure.score_failure_count == 1
    second_failure = evaluate_adaptive_exit(
        policy,
        current_return_pct=Decimal("0"),
        prior_mfe_pct=Decimal("0"),
        profit_armed=False,
        prior_score_failure_count=1,
        original_direction_score=Decimal("77"),
        opposite_direction_score=Decimal("20"),
        score_floor=Decimal("78"),
        fresh_direction_evidence=True,
        trading_minutes_elapsed=0,
        dte_days=10,
        force_flatten_due=False,
    )
    assert second_failure.exit_reason.value == "thesis_invalidated"
    stagnation = evaluate_adaptive_exit(
        policy,
        current_return_pct=Decimal("5"),
        prior_mfe_pct=Decimal("9"),
        profit_armed=False,
        prior_score_failure_count=0,
        original_direction_score=None,
        opposite_direction_score=None,
        score_floor=Decimal("78"),
        fresh_direction_evidence=False,
        trading_minutes_elapsed=390,
        dte_days=10,
        force_flatten_due=False,
    )
    assert stagnation.exit_reason.value == "stagnation_time_stop"
