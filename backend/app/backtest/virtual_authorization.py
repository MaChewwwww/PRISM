"""Backtest-only mirror of the deterministic authorization rule trace.

This module intentionally does not import the execution package or persist an
``AuthorizationModel``.  It produces an auditable virtual result for a
staging ledger while keeping the order-capable production evaluator isolated.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

from app.contracts.models import OptionSide, RiskAssessment, RiskVerdict, TradeProposal
from app.rules.registry import AuthorizedRuleset, get_authorized_ruleset


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


def virtual_input_digest(inputs: dict[str, Any]) -> str:
    encoded = json.dumps(_json_value(inputs), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class VirtualRuleCheck:
    priority: str
    rule_id: str
    outcome: Literal["PASS", "FAIL"]
    reason_code: str
    explanation: str

    def as_dict(self) -> dict[str, str]:
        return {
            "priority": self.priority,
            "rule_id": self.rule_id,
            "outcome": self.outcome,
            "reason_code": self.reason_code,
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class VirtualAuthorizationResult:
    outcome: Literal["APPROVE", "REJECT"]
    input_digest: str
    ruleset_version: str
    profile_key: str
    rule_trace: tuple[VirtualRuleCheck, ...]

    @property
    def approved(self) -> bool:
        return self.outcome == "APPROVE"

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return tuple(check.reason_code for check in self.rule_trace if check.outcome == "FAIL")

    def as_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "input_digest": self.input_digest,
            "ruleset_version": self.ruleset_version,
            "profile_key": self.profile_key,
            "rule_trace": [check.as_dict() for check in self.rule_trace],
        }


def _check(
    priority: str,
    rule_id: str,
    passed: bool,
    reason_code: str,
    explanation: str,
) -> VirtualRuleCheck:
    return VirtualRuleCheck(
        priority=priority,
        rule_id=rule_id,
        outcome="PASS" if passed else "FAIL",
        reason_code="PASS" if passed else reason_code,
        explanation=explanation,
    )


def _valid_strategy(proposal: TradeProposal) -> bool:
    strategy = proposal.strategy
    legs = strategy.legs
    if len(legs) not in {1, 2} or proposal.quantity < 1:
        return False
    if any(not leg.active or not leg.tradable or leg.ratio_qty != 1 for leg in legs):
        return False
    if len(legs) == 1:
        return legs[0].side is OptionSide.BUY and strategy.kind.value in {
            "long_call",
            "long_put",
        }
    return (
        strategy.kind.value in {"call_debit_spread", "put_debit_spread"}
        and len({leg.underlying for leg in legs}) == 1
        and len({leg.expiration for leg in legs}) == 1
        and sum(1 for leg in legs if leg.side is OptionSide.BUY) == 1
        and sum(1 for leg in legs if leg.side is OptionSide.SELL) == 1
        and legs[0].option_type is legs[1].option_type
        and strategy.limit_price > 0
    )


def evaluate_virtual_authorization(
    proposal: TradeProposal,
    risk: RiskAssessment | None,
    *,
    inputs: dict[str, Any],
    profile_key: Literal["conservative", "balanced", "aggressive"] = "balanced",
    ruleset: AuthorizedRuleset | None = None,
    now: datetime | None = None,
) -> VirtualAuthorizationResult:
    """Evaluate P0-P5 without execution imports or shared authorization rows.

    Execution kill switches and order-capable settings are intentionally not
    consulted: this evaluator can only approve a virtual ShadowFund branch.
    The active ruleset identity is still bound into the P0 trace.
    """

    del now  # The replay window and quote timestamps are already in ``inputs``.
    active_rules = ruleset or get_authorized_ruleset()
    params = active_rules.parameters
    profile = active_rules.profiles[profile_key]
    digest = virtual_input_digest(inputs)
    strategy_valid = _valid_strategy(proposal)
    risk_ok = risk is not None and risk.verdict is RiskVerdict.ACCEPTABLE and risk.data_fresh
    market_regime = str(inputs.get("market_regime", ""))
    legs = len(proposal.strategy.legs)
    iv_rank = _decimal(inputs.get("iv_rank"), Decimal("-1"))
    iv_rank_ok = bool(inputs.get("iv_rank_available") is True and 0 <= iv_rank <= 100)
    if iv_rank > 50 and legs != 2:
        iv_rank_ok = False
    checks = [
        _check(
            "P0",
            "P0-SAFETY-EVIDENCE",
            bool(
                inputs.get("paper_only") is True
                and inputs.get("active_ruleset_version") == active_rules.version
                and inputs.get("market_fresh") is True
                and int(inputs.get("analog_count", 0)) >= 30
                and inputs.get("fundamentals_sourced") is True
            ),
            "STALE_DATA",
            "Virtual replay requires paper-only mode and fresh sourced evidence.",
        ),
        _check(
            "P1",
            "P1-PORTFOLIO-CONTROLS",
            bool(
                inputs.get("account_verified") is True
                and int(inputs.get("open_positions", params.max_open_positions + 1))
                < int(inputs.get("max_open_positions", params.max_open_positions))
                and inputs.get("buying_power_ok") is True
                and inputs.get("cash_buffer_ok") is True
                and inputs.get("concentration_ok") is True
                and inputs.get("position_size_ok") is True
                and inputs.get("aggregate_risk_ok") is True
                and inputs.get("portfolio_controls_complete") is True
                and inputs.get("sector_concentration_ok") is True
                and inputs.get("cluster_concentration_ok") is True
                and inputs.get("expiration_concentration_ok") is True
                and inputs.get("greeks_risk_ok") is True
                and str(inputs.get("portfolio_risk_state", "")) == "normal"
                and _decimal(inputs.get("supported_options_level"), Decimal("0"))
                >= Decimal("3" if legs > 1 else "2")
            ),
            "RISK_LIMIT_BREACH",
            "Virtual account, cash, sizing, concentration, and drawdown controls.",
        ),
        _check(
            "P2",
            "P2-RISK-AND-INSTRUMENT",
            risk_ok
            and strategy_valid
            and market_regime not in {"", "crisis"}
            and (market_regime != "volatile" or legs == 2)
            and iv_rank_ok,
            "UNSUPPORTED_INSTRUMENT",
            "Fresh AI risk, supported structures, regime, and IV evidence are required.",
        ),
        _check(
            "P3",
            "P3-LIQUIDITY-AND-TIMING",
            bool(
                _decimal(inputs.get("quote_age_seconds"), Decimal("999"))
                <= params.data_freshness_seconds
                and _decimal(inputs.get("spread_pct"), Decimal("999"))
                <= params.max_bid_ask_spread_pct
                and inputs.get("market_open") is True
                and inputs.get("within_entry_window") is True
                and inputs.get("before_force_flatten") is True
            ),
            "LIQUIDITY_LIMIT_BREACH",
            "Fresh NBBO, spread, entry-cutoff, and force-flatten controls.",
        ),
        _check(
            "P4",
            "P4-EDGE-THRESHOLDS",
            bool(
                _decimal(inputs.get("opportunity_score"), Decimal("0"))
                >= profile.opportunity_score_threshold
                and _decimal(inputs.get("net_ev_r"), Decimal("-1")) >= params.minimum_net_ev_r
                and _decimal(inputs.get("reward_risk_ratio"), Decimal("0"))
                >= params.minimum_reward_risk_ratio
            ),
            "NEGATIVE_EXPECTED_VALUE",
            "Profile opportunity, expected-value, and reward/risk floors.",
        ),
        _check(
            "P5",
            "P5-EXIT-AND-PAYLOAD-INTEGRITY",
            bool(
                strategy_valid
                and proposal.exit_policy.take_profit_pct == profile.take_profit_pct
                and proposal.exit_policy.stop_loss_pct == profile.stop_loss_pct
                and proposal.exit_policy.max_hold_days <= params.hackathon_max_hold_trading_days
                and params.dte_threshold_min_days
                <= proposal.exit_policy.dte_threshold
                <= params.dte_threshold_max_days
            ),
            "PAYLOAD_MISMATCH",
            "Profile-bound exit policy and supported virtual payload.",
        ),
    ]
    return VirtualAuthorizationResult(
        outcome="APPROVE" if all(item.outcome == "PASS" for item in checks) else "REJECT",
        input_digest=digest,
        ruleset_version=active_rules.version,
        profile_key=profile_key,
        rule_trace=tuple(checks),
    )


def _decimal(value: Any, default: Decimal) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except Exception:
        return default
    return parsed if parsed.is_finite() else default
