from __future__ import annotations

import hashlib
import json
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
from app.rules.registry import get_authorized_ruleset


class ExecutionRejected(ValueError):
    """A fail-closed rejection before any broker invocation."""


def _allowed_payload_digest(payload: object) -> str:
    if hasattr(payload, "model_dump"):
        encoded = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    else:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


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
        if (
            leg.side != OptionSide.BUY
            or leg.ratio_qty != 1
            or strategy.kind != expected_kind
            or leg.position_intent != "buy_to_open"
        ):
            raise ExecutionRejected("Single-leg options must be one long call or long put")
        return
    if len(legs) != 2 or any(leg.ratio_qty != 1 for leg in legs):
        raise ExecutionRejected("Spreads must contain exactly two 1:1 option legs")
    buy_legs = [leg for leg in legs if leg.side == OptionSide.BUY]
    sell_legs = [leg for leg in legs if leg.side == OptionSide.SELL]
    if len(buy_legs) != 1 or len(sell_legs) != 1:
        raise ExecutionRejected("Debit spreads require exactly one long and one short leg")
    long_leg, short_leg = buy_legs[0], sell_legs[0]
    if long_leg.position_intent != "buy_to_open" or short_leg.position_intent != "sell_to_open":
        raise ExecutionRejected("Debit spread legs must explicitly open long and short positions")
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
    kill_switch_active: bool | None = None,
) -> None:
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ExecutionRejected("Execution timestamp must be timezone-aware")
    current_time = current_time.astimezone(UTC)
    if not settings.alpaca_paper or settings.alpaca_live_trade:
        raise ExecutionRejected("Live trading is prohibited")
    effective_kill_switch = (
        settings.execution_kill_switch if kill_switch_active is None else kill_switch_active
    )
    if not settings.execution_enabled or effective_kill_switch:
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
    if settings.autonomous_trading_enabled and not proposal.research_bundle_digest:
        raise ExecutionRejected("Autonomous proposal is missing its research bundle binding")
    payload = decision.allowed_order_payload
    if payload is None:
        raise ExecutionRejected("Authorized payload is missing")
    if (
        payload.symbol != proposal.symbol
        or payload.quantity != proposal.quantity
        or payload.strategy != proposal.strategy
    ):
        raise ExecutionRejected("Authorized payload does not match the proposal")
    computed_payload_digest = _allowed_payload_digest(payload)
    if settings.autonomous_trading_enabled:
        if decision.allowed_order_payload_digest != computed_payload_digest:
            raise ExecutionRejected("Authorized payload digest is not recomputed")
    elif decision.allowed_order_payload_digest not in {
        proposal.proposal_digest,
        computed_payload_digest,
    }:
        raise ExecutionRejected("Authorized payload does not match the proposal digest")
    if decision.trace_id != proposal.trace_id:
        raise ExecutionRejected("Authorization trace does not match the proposal")
    if decision.proposal_version != proposal.proposal_version:
        raise ExecutionRejected("Authorization proposal version does not match the proposal")
    if decision.ruleset_version != settings.active_ruleset_version:
        raise ExecutionRejected("Authorization ruleset is not active")
    if decision.ruleset_id != get_authorized_ruleset().ruleset_id:
        raise ExecutionRejected("Authorization ruleset identity is not authorized")
    if decision.expires_at <= current_time:
        raise ExecutionRejected("Authorization has expired")
    if decision.expires_at <= decision.decision_at:
        raise ExecutionRejected("Authorization expiration is invalid")
    if decision.decision_at > current_time or decision.account_observed_at > current_time:
        raise ExecutionRejected("Authorization timestamps are in the future")
    account_age = (current_time - decision.account_observed_at).total_seconds()
    if account_age < 0 or account_age > settings.account_state_max_age_seconds:
        raise ExecutionRejected("Account state is not fresh")
    if not decision.account_verified:
        raise ExecutionRejected("Paper account is not verified")
    if not decision.rule_trace:
        raise ExecutionRejected("Authorization is missing a deterministic rule trace")
    validate_strategy(proposal.strategy)
    if decision.supported_options_level < required_options_level(proposal.strategy):
        raise ExecutionRejected("Account options level is insufficient")
