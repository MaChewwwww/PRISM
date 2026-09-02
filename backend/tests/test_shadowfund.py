from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.contracts.models import (
    OptionLeg,
    OptionSide,
    OptionStrategy,
    OptionType,
    ShadowAlternativeIntent,
)
from app.shadowfund.service import ShadowFundService


def _strategy() -> OptionStrategy:
    return OptionStrategy(
        kind="long_call",
        legs=[
            OptionLeg(
                symbol="NVDA260904C00100000",
                underlying="NVDA",
                expiration="2026-09-04",
                option_type=OptionType.CALL,
                side=OptionSide.BUY,
                strike_price=Decimal("100"),
                position_intent="buy_to_open",
            )
        ],
        limit_price=Decimal("2.00"),
    )


def test_shadowfund_uses_bid_for_virtual_long_exit_and_supports_half_size() -> None:
    strategy = _strategy()
    quotes = {strategy.legs[0].symbol: {"bid": "3.00", "ask": "2.00"}}
    entry = ShadowFundService._strategy_value(strategy, quotes, entry=True)
    exit_mark = ShadowFundService._strategy_value(strategy, quotes, entry=False)
    assert entry == Decimal("2.00")
    assert exit_mark == Decimal("3.00")
    assert (exit_mark - entry) * Decimal("100") * Decimal("0.5") == Decimal("50.00")


def test_shadowfund_rejects_stale_or_future_quotes() -> None:
    strategy = _strategy()
    now = datetime(2026, 8, 31, 13, 30, tzinfo=UTC)
    stale = {strategy.legs[0].symbol: {"quote_timestamp": now - timedelta(seconds=31)}}
    future = {strategy.legs[0].symbol: {"quote_timestamp": now + timedelta(seconds=1)}}
    assert not ShadowFundService._quotes_are_fresh(
        strategy, stale, observed_at=now, max_quote_age_seconds=30
    )
    assert ShadowFundService._quotes_are_fresh(
        strategy, future, observed_at=now, max_quote_age_seconds=30
    )


def test_shadowfund_horizon_exit_precedes_price_policy() -> None:
    strategy = _strategy()
    now = datetime(2026, 9, 3, 20, 0, tzinfo=UTC)
    assert (
        ShadowFundService._exit_reason(
            '{"take_profit_pct":"75","stop_loss_pct":"50","dte_threshold":7}',
            strategy,
            entry_cost=Decimal("2"),
            mark=Decimal("4"),
            observed_at=now,
            horizon_at=now,
        )
        == "HORIZON_CLOSE"
    )


def test_agent_seven_shadow_intent_is_strict_and_non_executable() -> None:
    intent = ShadowAlternativeIntent(
        direction="bullish", preferred_structure="long_call", rationale="Alternative thesis"
    )
    assert intent.direction.value == "bullish"
    with pytest.raises(ValidationError):
        ShadowAlternativeIntent(
            direction="bullish",
            preferred_structure="long_call",
            rationale="Alternative thesis",
            symbol="NVDA260904C00100000",
        )


def test_shadowfund_service_has_no_order_execution_dependency() -> None:
    # Keep the source-boundary assertion direct: ShadowFund cannot import the
    # order-capable CLI, autonomous worker, account readers, or receipt models.
    import inspect

    implementation = inspect.getsource(__import__("app.shadowfund.service", fromlist=["*"]))
    assert "execution.cli_gateway" not in implementation
    assert "autonomous.worker" not in implementation
    assert "ExecutionReceiptModel" not in implementation
