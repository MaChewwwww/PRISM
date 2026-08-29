from __future__ import annotations

import json
from datetime import UTC, datetime
from functools import lru_cache
from importlib.resources import files
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.contracts.models import DecimalString


class RuleParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_capital_usd: DecimalString
    max_risk_per_trade_pct: DecimalString
    volatile_risk_per_trade_pct: DecimalString
    normal_target_allocation_pct: DecimalString
    volatile_target_allocation_pct: DecimalString
    drawdown_caution_pct: DecimalString
    drawdown_defensive_pct: DecimalString
    drawdown_halt_pct: DecimalString
    cash_buffer_pct: DecimalString
    ticker_concentration_pct: DecimalString
    sector_concentration_pct: DecimalString
    correlated_cluster_concentration_pct: DecimalString
    aggregate_hard_stop_risk_pct: DecimalString
    max_open_positions: int = Field(ge=1)
    max_bid_ask_spread_pct: DecimalString
    data_freshness_seconds: int = Field(ge=1)
    opportunity_score_floor: DecimalString
    balanced_opportunity_score: DecimalString
    minimum_net_ev_r: DecimalString
    minimum_reward_risk_ratio: DecimalString
    take_profit_default_pct: DecimalString
    take_profit_min_pct: DecimalString
    take_profit_max_pct: DecimalString
    stop_loss_pct: DecimalString
    dte_threshold_default_days: int
    dte_threshold_min_days: int
    dte_threshold_max_days: int
    max_hold_default_days: int
    max_hold_min_days: int
    max_hold_max_days: int
    hackathon_max_hold_trading_days: int
    hackathon_window: HackathonWindow


class HackathonWindow(BaseModel):
    """BA-authorized, fixed-date operating bounds for the hackathon."""

    model_config = ConfigDict(extra="forbid")

    trading_start_at: datetime
    official_scoring_at: datetime
    window_outer_boundary_at: datetime
    force_flatten_by: datetime
    new_entry_cutoff_at: datetime
    scoring_basis: Literal["total_account_equity"]

    @field_validator(
        "trading_start_at",
        "official_scoring_at",
        "window_outer_boundary_at",
        "force_flatten_by",
        "new_entry_cutoff_at",
    )
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("hackathon window timestamps must be timezone-aware UTC")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_order(self) -> HackathonWindow:
        if self.trading_start_at >= self.new_entry_cutoff_at:
            raise ValueError("hackathon trading start must precede the new-entry cutoff")
        if self.new_entry_cutoff_at >= self.official_scoring_at:
            raise ValueError("new-entry cutoff must precede the official scoring point")
        if self.force_flatten_by != self.official_scoring_at:
            raise ValueError("force-flatten deadline must equal the official scoring point")
        if self.official_scoring_at >= self.window_outer_boundary_at:
            raise ValueError("outer boundary must follow the official scoring point")
        return self


class ProfileParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_position_size_pct: DecimalString
    opportunity_score_threshold: DecimalString
    take_profit_pct: DecimalString
    stop_loss_pct: DecimalString


ProfileField = Literal[
    "target_position_size_pct",
    "opportunity_score_threshold",
    "take_profit_pct",
    "stop_loss_pct",
]


class ParameterBound(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum: DecimalString
    maximum: DecimalString


class AuthorizedRuleset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ruleset_id: str
    version: str
    status: Literal["active", "retired"]
    effective_from: datetime | None
    effective_to: datetime | None
    default_profile: Literal["conservative", "balanced", "aggressive"]
    parameters: RuleParameters
    profiles: dict[Literal["conservative", "balanced", "aggressive"], ProfileParameters]
    profile_bounds: dict[ProfileField, ParameterBound]


@lru_cache
def get_authorized_ruleset() -> AuthorizedRuleset:
    resource = files("app.rules").joinpath("authorized_baseline.v1.json")
    return AuthorizedRuleset.model_validate(json.loads(resource.read_text(encoding="utf-8")))
