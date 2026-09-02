"""Deterministic P0-P5 authorization after AI research and risk assessment."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from app.contracts.models import (
    AllowedOrderPayload,
    AuthorizationDecision,
    AuthorizationOutcome,
    MarketRegime,
    PortfolioRiskState,
    ReasonCode,
    RiskAssessment,
    RiskVerdict,
    RuleEvaluation,
    RuleOutcome,
    RulePriority,
    TradeProposal,
)
from app.core.config import Settings
from app.rules.registry import AuthorizedRuleset, ProfileParameters, get_authorized_ruleset


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def input_digest(inputs: dict[str, Any]) -> str:
    encoded = json.dumps(_json_value(inputs), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def allowed_payload_digest(payload: AllowedOrderPayload) -> str:
    """Digest only the broker-authorized payload, excluding proposal metadata."""
    encoded = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _decimal_input(inputs: dict[str, Any], key: str, default: str) -> Decimal:
    try:
        return Decimal(str(inputs.get(key, default)))
    except (TypeError, ValueError):
        return Decimal(default)


def _rule(
    proposal: TradeProposal,
    ruleset: AuthorizedRuleset,
    priority: RulePriority,
    rule_id: str,
    passed: bool,
    reasons: list[ReasonCode],
    explanation: str,
    snapshot_digest: str,
) -> RuleEvaluation:
    return RuleEvaluation(
        trace_id=proposal.trace_id,
        proposal_id=proposal.id,
        priority=priority,
        rule_id=rule_id,
        ruleset_version=ruleset.version,
        outcome=RuleOutcome.PASS if passed else RuleOutcome.FAIL,
        reason_codes=reasons,
        explanation=explanation,
        input_snapshot_digest=snapshot_digest,
    )


def _p2_reason_codes(
    *,
    risk: RiskAssessment | None,
    strategy_valid: bool,
    regime_ok: bool,
    iv_rank_ok: bool,
    economics_bound: bool,
) -> list[ReasonCode]:
    """Return only predicates that actually failed in the P2 gate."""
    reasons: list[ReasonCode] = []
    if risk is None:
        reasons.append(ReasonCode.RISK_ASSESSMENT_MISSING)
    else:
        if risk.verdict is not RiskVerdict.ACCEPTABLE:
            reasons.append(ReasonCode.RISK_ASSESSMENT_REJECTED)
        if not risk.data_fresh:
            reasons.append(ReasonCode.RISK_DATA_STALE)
    if not strategy_valid:
        reasons.append(ReasonCode.INVALID_STRATEGY)
    if not regime_ok:
        reasons.append(ReasonCode.MARKET_REGIME_BLOCKED)
    if not iv_rank_ok:
        reasons.append(ReasonCode.IV_RANK_LIMIT_BREACH)
    if not economics_bound:
        reasons.append(ReasonCode.ECONOMICS_MISMATCH)
    return reasons


def _p4_reason_codes(
    *,
    opportunity_score: Decimal,
    opportunity_threshold: Decimal,
    net_ev: Decimal,
    minimum_net_ev: Decimal,
    reward_risk_ratio: Decimal,
    minimum_reward_risk: Decimal,
    market_regime: MarketRegime | None,
    strategy_leg_count: int,
    economics_bound: bool,
) -> list[ReasonCode]:
    """Return one reason code for each independently failed P4 predicate."""
    reasons: list[ReasonCode] = []
    if opportunity_score < opportunity_threshold:
        reasons.append(ReasonCode.OPPORTUNITY_SCORE_BELOW_FLOOR)
    if net_ev < minimum_net_ev:
        reasons.append(
            ReasonCode.NEGATIVE_EXPECTED_VALUE
            if net_ev < 0
            else ReasonCode.EXPECTED_VALUE_BELOW_FLOOR
        )
    if reward_risk_ratio < minimum_reward_risk:
        reasons.append(ReasonCode.REWARD_RISK_BELOW_FLOOR)
    if market_regime is MarketRegime.CRISIS or (
        market_regime is MarketRegime.VOLATILE and strategy_leg_count != 2
    ):
        reasons.append(ReasonCode.MARKET_REGIME_BLOCKED)
    if not economics_bound:
        reasons.append(ReasonCode.ECONOMICS_MISMATCH)
    return reasons


def authorize_proposal(
    proposal: TradeProposal,
    risk: RiskAssessment | None,
    settings: Settings,
    *,
    inputs: dict[str, Any],
    now: datetime | None = None,
    profile_key: Literal["conservative", "balanced", "aggressive"] = "balanced",
    profile_parameters: ProfileParameters | None = None,
    profile_id: UUID | None = None,
    profile_version: int = 1,
    kill_switch_active: bool | None = None,
) -> AuthorizationDecision:
    """Evaluate all P0-P5 controls and return a fully bound decision.

    Missing context is a rejection. The function never fills unavailable
    market, account, portfolio, or historical-analog values with defaults.
    """
    now = (now or datetime.now(UTC)).astimezone(UTC)
    ruleset = get_authorized_ruleset()
    snapshot = input_digest(inputs)
    params = ruleset.parameters
    profile = profile_parameters or ruleset.profiles[profile_key]
    effective_kill_switch = (
        settings.execution_kill_switch if kill_switch_active is None else kill_switch_active
    )
    checks: list[RuleEvaluation] = []
    try:
        from app.execution.validation import validate_strategy

        validate_strategy(proposal.strategy)
        strategy_valid = True
    except ValueError:
        strategy_valid = False
    risk_ok = risk is not None and risk.verdict is RiskVerdict.ACCEPTABLE and risk.data_fresh
    try:
        raw_market_regime = inputs.get("market_regime")
        market_regime = (
            MarketRegime(raw_market_regime) if isinstance(raw_market_regime, str) else None
        )
    except ValueError:
        market_regime = None
    regime_ok = (
        market_regime is not None
        and market_regime != MarketRegime.CRISIS
        and (market_regime != MarketRegime.VOLATILE or len(proposal.strategy.legs) == 2)
    )
    iv_rank = _decimal_input(inputs, "iv_rank", "-1")
    iv_rank_ok = (
        inputs.get("iv_rank_available") is True
        and Decimal("0") <= iv_rank <= Decimal("100")
        and (iv_rank <= Decimal("50") or len(proposal.strategy.legs) == 2)
    )
    economics = proposal.option_economics
    economics_bound = not settings.autonomous_trading_enabled or (
        economics is not None
        and economics.net_ev_r == _decimal_input(inputs, "net_ev_r", "-1")
        and economics.reward_risk_ratio == _decimal_input(inputs, "reward_risk_ratio", "0")
    )
    checks.append(
        _rule(
            proposal,
            ruleset,
            RulePriority.P0,
            "P0-SAFETY-EVIDENCE",
            bool(
                settings.alpaca_paper
                and not settings.alpaca_live_trade
                and not effective_kill_switch
                and settings.active_ruleset_version == ruleset.version
                and inputs.get("market_fresh") is True
                and inputs.get("analog_count", 0) >= 30
                and inputs.get("fundamentals_sourced") is True
                and economics_bound
            ),
            []
            if all(
                [
                    settings.alpaca_paper,
                    not settings.alpaca_live_trade,
                    not effective_kill_switch,
                    settings.active_ruleset_version == ruleset.version,
                    inputs.get("market_fresh") is True,
                    inputs.get("analog_count", 0) >= 30,
                    inputs.get("fundamentals_sourced") is True,
                    economics_bound,
                ]
            )
            else [ReasonCode.STALE_DATA],
            "Paper-only execution requires fresh, sourced evidence and at least 30 analog events.",
            snapshot,
        )
    )
    checks.append(
        _rule(
            proposal,
            ruleset,
            RulePriority.P1,
            "P1-PORTFOLIO-CONTROLS",
            bool(
                inputs.get("account_verified") is True
                and inputs.get("open_positions", params.max_open_positions + 1)
                < settings.autonomous_max_open_positions
                and inputs.get("buying_power_ok") is True
                and inputs.get("cash_buffer_ok") is True
                and inputs.get("concentration_ok") is True
                and inputs.get("position_size_ok") is True
                and inputs.get("aggregate_risk_ok") is True
                and inputs.get("portfolio_controls_complete") is True
                and inputs.get("sector_concentration_ok") is True
                and inputs.get("cluster_concentration_ok") is True
                and inputs.get("greeks_risk_ok") is True
                and inputs.get("expiration_concentration_ok") is True
                and inputs.get("portfolio_risk_state") == PortfolioRiskState.NORMAL
                and _decimal_input(inputs, "supported_options_level", "0")
                >= Decimal("3" if len(proposal.strategy.legs) > 1 else "2")
            ),
            []
            if bool(
                inputs.get("account_verified") is True
                and inputs.get("open_positions", params.max_open_positions + 1)
                < settings.autonomous_max_open_positions
                and inputs.get("buying_power_ok") is True
                and inputs.get("cash_buffer_ok") is True
                and inputs.get("concentration_ok") is True
                and inputs.get("position_size_ok") is True
                and inputs.get("aggregate_risk_ok") is True
                and inputs.get("portfolio_controls_complete") is True
                and inputs.get("sector_concentration_ok") is True
                and inputs.get("cluster_concentration_ok") is True
                and inputs.get("greeks_risk_ok") is True
                and inputs.get("expiration_concentration_ok") is True
                and inputs.get("portfolio_risk_state") == PortfolioRiskState.NORMAL
                and _decimal_input(inputs, "supported_options_level", "0")
                >= Decimal("3" if len(proposal.strategy.legs) > 1 else "2")
            )
            else [ReasonCode.RISK_LIMIT_BREACH],
            (
                "Account, drawdown, position, buying-power, cash, concentration, sizing, "
                "and options-level controls."
            ),
            snapshot,
        )
    )
    checks.append(
        _rule(
            proposal,
            ruleset,
            RulePriority.P2,
            "P2-RISK-AND-INSTRUMENT",
            risk_ok and strategy_valid and regime_ok and iv_rank_ok and economics_bound,
            _p2_reason_codes(
                risk=risk,
                strategy_valid=strategy_valid,
                regime_ok=regime_ok,
                iv_rank_ok=iv_rank_ok,
                economics_bound=economics_bound,
            ),
            "Fresh AI risk, supported structures, and non-crisis regimes are required.",
            snapshot,
        )
    )
    checks.append(
        _rule(
            proposal,
            ruleset,
            RulePriority.P3,
            "P3-LIQUIDITY-AND-TIMING",
            bool(
                _decimal_input(inputs, "quote_age_seconds", str(params.data_freshness_seconds + 1))
                <= params.data_freshness_seconds
                and _decimal_input(inputs, "spread_pct", "100") <= params.max_bid_ask_spread_pct
                and inputs.get("market_open") is True
                and inputs.get("iv_rank_available") is True
                and inputs.get("within_entry_window") is True
                and inputs.get("before_force_flatten") is True
            ),
            []
            if bool(
                _decimal_input(inputs, "quote_age_seconds", str(params.data_freshness_seconds + 1))
                <= params.data_freshness_seconds
                and _decimal_input(inputs, "spread_pct", "100") <= params.max_bid_ask_spread_pct
                and inputs.get("market_open") is True
                and inputs.get("iv_rank_available") is True
                and inputs.get("within_entry_window") is True
                and inputs.get("before_force_flatten") is True
            )
            else [ReasonCode.LIQUIDITY_LIMIT_BREACH],
            "Fresh NBBO, spread, entry cutoff, and force-flatten controls.",
            snapshot,
        )
    )
    checks.append(
        _rule(
            proposal,
            ruleset,
            RulePriority.P4,
            "P4-EDGE-THRESHOLDS",
            bool(
                _decimal_input(inputs, "opportunity_score", "0")
                >= profile.opportunity_score_threshold
                and _decimal_input(inputs, "net_ev_r", "-1") >= params.minimum_net_ev_r
                and _decimal_input(inputs, "reward_risk_ratio", "0")
                >= params.minimum_reward_risk_ratio
                and market_regime != MarketRegime.CRISIS
                and (market_regime != MarketRegime.VOLATILE or len(proposal.strategy.legs) == 2)
                and economics_bound
            ),
            _p4_reason_codes(
                opportunity_score=_decimal_input(inputs, "opportunity_score", "0"),
                opportunity_threshold=profile.opportunity_score_threshold,
                net_ev=_decimal_input(inputs, "net_ev_r", "-1"),
                minimum_net_ev=params.minimum_net_ev_r,
                reward_risk_ratio=_decimal_input(inputs, "reward_risk_ratio", "0"),
                minimum_reward_risk=params.minimum_reward_risk_ratio,
                market_regime=market_regime,
                strategy_leg_count=len(proposal.strategy.legs),
                economics_bound=economics_bound,
            ),
            "The active profile opportunity score, EV, and reward/risk thresholds must pass.",
            snapshot,
        )
    )
    exit_policy = proposal.exit_policy
    exit_valid = (
        exit_policy.profit_arm_pct == params.profit_arm_pct
        and exit_policy.profit_trailing_giveback_points == params.profit_trailing_giveback_points
        and exit_policy.hard_take_profit_pct == params.hard_take_profit_pct
        and exit_policy.hard_stop_loss_pct == params.hard_stop_loss_pct
        and exit_policy.thesis_failure_cycles == params.thesis_failure_cycles
        and exit_policy.time_stop_trading_minutes == params.time_stop_trading_minutes
        and exit_policy.minimum_mfe_pct == params.minimum_mfe_pct
        and params.dte_threshold_min_days
        <= exit_policy.dte_threshold
        <= params.dte_threshold_max_days
        and exit_policy.max_hold_days
        <= (
            params.hackathon_max_hold_trading_days
            if settings.autonomous_trading_enabled
            else params.max_hold_max_days
        )
    )
    checks.append(
        _rule(
            proposal,
            ruleset,
            RulePriority.P5,
            "P5-EXIT-AND-PAYLOAD-INTEGRITY",
            strategy_valid and exit_valid and settings.active_ruleset_version == ruleset.version,
            []
            if strategy_valid and exit_valid and settings.active_ruleset_version == ruleset.version
            else [ReasonCode.PAYLOAD_MISMATCH],
            "Ruleset-bound adaptive exit policy and option payload must validate exactly.",
            snapshot,
        )
    )
    approved = all(check.outcome is RuleOutcome.PASS for check in checks)
    expiration = now + timedelta(seconds=params.data_freshness_seconds)
    if settings.autonomous_trading_end_at is not None:
        expiration = min(expiration, settings.autonomous_trading_end_at)
    allowed = AllowedOrderPayload(
        symbol=proposal.symbol,
        strategy=proposal.strategy,
        quantity=proposal.quantity,
    )
    return AuthorizationDecision(
        trace_id=proposal.trace_id,
        proposal_id=proposal.id,
        proposal_version=proposal.proposal_version,
        proposal_digest=proposal.proposal_digest,
        ruleset_id=ruleset.ruleset_id,
        ruleset_version=ruleset.version,
        profile_id=profile_id or uuid5(NAMESPACE_URL, f"{ruleset.ruleset_id}:{profile_key}"),
        profile_version=profile_version,
        outcome=AuthorizationOutcome.APPROVE if approved else AuthorizationOutcome.REJECT,
        allowed_order_payload_digest=allowed_payload_digest(allowed) if approved else None,
        allowed_order_payload=allowed if approved else None,
        market_snapshot_digest=str(inputs.get("market_snapshot_digest", snapshot)),
        portfolio_snapshot_digest=str(inputs.get("portfolio_snapshot_digest", snapshot)),
        market_regime=market_regime or MarketRegime.NORMAL,
        portfolio_risk_state=inputs.get("portfolio_risk_state", PortfolioRiskState.NORMAL),
        decision_at=now,
        expires_at=expiration,
        account_observed_at=inputs.get("account_observed_at", now),
        supported_options_level=int(inputs.get("supported_options_level", 0)),
        account_verified=bool(inputs.get("account_verified", False)),
        rule_trace=checks,
    )
