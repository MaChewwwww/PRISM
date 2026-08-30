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
