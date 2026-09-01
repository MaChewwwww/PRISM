from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.contracts.models import DecimalString
from app.rules.registry import ProfileParameters


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ok", "ready", "not_ready"]


class SystemStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["ready", "degraded", "unavailable", "misconfigured"]
    paper_mode: bool
    execution_enabled: bool
    kill_switch_active: bool
    cli_available: bool
    cli_version: str | None
    credentials_present: bool
    account_verified: bool
    supported_options_level: int | None


class AutonomousStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    autonomous_enabled: bool
    execution_enabled: bool
    kill_switch_active: bool
    updated_at: datetime
    updated_by: str
    reason: str


class AutonomousCycleRead(BaseModel):
    """Redacted immutable outcome from one autonomous worker cycle."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    started_at: datetime
    completed_at: datetime | None
    outcome: Literal["NO_TRADE", "SUBMITTED", "FAILED"]
    symbols: list[str]
    reason: str
    exit_checks: list["AutonomousExitCheck"]
    worker_version: str


class AutonomousExitCheck(BaseModel):
    """Safe evidence for a mandatory position-exit decision."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    result: Literal["exit", "hold", "exit_failed", "exit_pending"]
    reason: Literal[
        "pnl_threshold",
        "max_hold_days",
        "dte_threshold",
        "no_exit_condition",
    ]


class AutonomousCycleCollection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AutonomousCycleRead]
    empty_message: str | None = None


class AutonomousRuleTraceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    priority: Literal["P0", "P1", "P2", "P3", "P4", "P5"]
    outcome: Literal["PASS", "MODIFY", "FAIL"]
    reason_codes: list[str]
    explanation: str


class AutonomousDecisionRead(BaseModel):
    """Joined proposal, risk, and deterministic-authorization read model."""

    model_config = ConfigDict(extra="forbid")

    proposal_id: UUID
    trace_id: UUID
    symbol: str
    created_at: datetime
    risk_verdict: str | None = None
    authorization_outcome: Literal["APPROVE", "REJECT", "MODIFIED_PENDING_ACCEPTANCE"]
    ruleset_version: str
    profile_version: int
    decision_at: datetime
    expires_at: datetime
    rule_trace: list[AutonomousRuleTraceSummary]


class AutonomousDecisionCollection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AutonomousDecisionRead]
    empty_message: str | None = None


class AutonomousExecutionRead(BaseModel):
    """Sanitized paper-order receipt; broker and client identifiers stay server-side."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    trace_id: UUID
    proposal_id: UUID | None = None
    operation: Literal["entry", "exit"]
    symbol: str | None = None
    exit_reason: (
        Literal[
            "pnl_threshold",
            "max_hold_days",
            "dte_threshold",
            "hackathon_force_flatten",
        ]
        | None
    ) = None
    requested_quantity: DecimalString | None = None
    status: Literal["pending", "submitted", "reconciling", "rejected", "filled", "failed"]
    filled_quantity: DecimalString
    filled_average_price: DecimalString | None = None
    error_code: str | None = None
    created_at: datetime
    submitted_at: datetime | None = None
    reconciled_at: datetime | None = None


class AutonomousExecutionCollection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AutonomousExecutionRead]
    empty_message: str | None = None


class AutonomousPositionRead(BaseModel):
    """Normalized position fields safe for the authenticated operator surface."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    underlying: str
    asset_class: str
    quantity: DecimalString | None = None
    market_value: DecimalString | None = None
    average_entry_price: DecimalString | None = None
    unrealized_pl: DecimalString | None = None
    unrealized_plpc: DecimalString | None = None
    expiration: str | None = None
    sector: str | None = None
    correlated_cluster: str | None = None
    delta: DecimalString | None = None
    vega: DecimalString | None = None
    metadata_complete: bool
    quote_age_seconds: DecimalString | None = None


class AutonomousPortfolioSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observed_at: datetime
    account_verified: bool
    supported_options_level: int | None = None
    account_values_complete: bool
    cash: DecimalString | None = None
    buying_power: DecimalString | None = None
    portfolio_value: DecimalString | None = None
    start_of_day_equity: DecimalString | None = None
    positions: list[AutonomousPositionRead]


class AutonomousPortfolioLatest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot: AutonomousPortfolioSnapshot | None = None
    empty_message: str | None = None


class KillSwitchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active: bool
    reason: str


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    password: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    expires_at: str


class AuthMeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    authenticated: bool


class LogoutResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["logged_out"]


class CalibrationPreferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["manual", "automatic"]


class CalibrationPreferenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator_id: str
    mode: Literal["manual", "automatic"]
    automatic_opt_in: bool
    updated_at: datetime


class ActiveProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    profile_key: Literal["conservative", "balanced", "aggressive"]
    version: int
    parameters: ProfileParameters
    activation_mode: Literal["manual", "automatic"]


class ProfileGovernanceStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_profile: ActiveProfileResponse
    preference: CalibrationPreferenceResponse


class ProfileActivationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: UUID


class ProfileActivationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_profile: ActiveProfileResponse
    activated_from_batch_id: UUID


class LLMUsageSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_count: int
    usage_available_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: DecimalString | None = None
