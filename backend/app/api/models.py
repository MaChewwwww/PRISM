from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


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
