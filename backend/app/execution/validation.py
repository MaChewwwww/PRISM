from __future__ import annotations

from datetime import UTC, datetime

from app.contracts.models import (
    AuthorizationDecision,
    AuthorizationOutcome,
    OptionSide,
    OptionStrategy,
    OptionType,
    StrategyKind,
    TradeProposal,
)
from app.core.config import Settings


class ExecutionRejected(ValueError):
    """A fail-closed rejection before any broker invocation."""


def required_options_level(strategy: OptionStrategy) -> int:
    return 2 if len(strategy.legs) == 1 else 3


def validate_strategy(strategy: OptionStrategy) -> None:
    legs = strategy.legs
    if strategy.time_in_force != "day" or strategy.extended_hours:
        raise ExecutionRejected("Options execution requires day TIF and no extended hours")
    if any(not leg.active or not leg.tradable for leg in legs):
        raise ExecutionRejected("Every option contract must be active and tradable")
    if len(legs) == 1:
        leg = legs[0]
        expected_kind = (
            StrategyKind.LONG_CALL if leg.option_type == OptionType.CALL else StrategyKind.LONG_PUT
        )
        if leg.side != OptionSide.BUY or leg.ratio_qty != 1 or strategy.kind != expected_kind:
            raise ExecutionRejected("Single-leg options must be one long call or long put")
        return
    if len(legs) != 2 or any(leg.ratio_qty != 1 for leg in legs):
        raise ExecutionRejected("Spreads must contain exactly two 1:1 option legs")
    buy_legs = [leg for leg in legs if leg.side == OptionSide.BUY]
    sell_legs = [leg for leg in legs if leg.side == OptionSide.SELL]
    if len(buy_legs) != 1 or len(sell_legs) != 1:
        raise ExecutionRejected("Debit spreads require exactly one long and one short leg")
    long_leg, short_leg = buy_legs[0], sell_legs[0]
    if long_leg.underlying != short_leg.underlying or long_leg.expiration != short_leg.expiration:
        raise ExecutionRejected("Spread legs must share one underlying and expiration")
    if long_leg.option_type != short_leg.option_type:
        raise ExecutionRejected("Spread legs must have the same option type")
    is_call_debit = (
        strategy.kind == StrategyKind.CALL_DEBIT_SPREAD
        and long_leg.option_type == OptionType.CALL
        and long_leg.strike_price < short_leg.strike_price
    )
    is_put_debit = (
        strategy.kind == StrategyKind.PUT_DEBIT_SPREAD
        and long_leg.option_type == OptionType.PUT
        and long_leg.strike_price > short_leg.strike_price
    )
    if not (is_call_debit or is_put_debit):
        raise ExecutionRejected("Only defined-risk call/put debit spreads are supported")


def validate_authorization(
    proposal: TradeProposal,
    decision: AuthorizationDecision,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> None:
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ExecutionRejected("Execution timestamp must be timezone-aware")
    current_time = current_time.astimezone(UTC)
    if not settings.alpaca_paper or settings.alpaca_live_trade:
        raise ExecutionRejected("Live trading is prohibited")
    if not settings.execution_enabled or settings.execution_kill_switch:
        raise ExecutionRejected("Paper execution is disabled or kill-switched")
    if settings.autonomous_trading_enabled and not settings.autonomous_trading_window_active(
        current_time
    ):
        raise ExecutionRejected("Autonomous trading window is not active")
    if not settings.active_ruleset_version:
        raise ExecutionRejected("No active ruleset")
    if decision.outcome != AuthorizationOutcome.APPROVE:
        raise ExecutionRejected("Authorization is not approved")
    if decision.proposal_id != proposal.id or decision.proposal_digest != proposal.proposal_digest:
        raise ExecutionRejected("Authorization does not match the proposal")
    if decision.allowed_order_payload_digest != proposal.proposal_digest:
        raise ExecutionRejected("Authorized payload does not match the proposal digest")
    payload = decision.allowed_order_payload
    if payload is None:
        raise ExecutionRejected("Authorized payload is missing")
    if (
        payload.symbol != proposal.symbol
        or payload.quantity != proposal.quantity
        or payload.strategy != proposal.strategy
    ):
        raise ExecutionRejected("Authorized payload does not match the proposal")
    if decision.trace_id != proposal.trace_id:
        raise ExecutionRejected("Authorization trace does not match the proposal")
    if decision.ruleset_version != settings.active_ruleset_version:
        raise ExecutionRejected("Authorization ruleset is not active")
    if decision.expires_at <= current_time:
        raise ExecutionRejected("Authorization has expired")
    account_age = (current_time - decision.account_observed_at).total_seconds()
    if account_age < 0 or account_age > settings.account_state_max_age_seconds:
        raise ExecutionRejected("Account state is not fresh")
    if not decision.account_verified:
        raise ExecutionRejected("Paper account is not verified")
    validate_strategy(proposal.strategy)
    if decision.supported_options_level < required_options_level(proposal.strategy):
        raise ExecutionRejected("Account options level is insufficient")
