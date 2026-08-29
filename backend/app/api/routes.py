from __future__ import annotations

import shutil
import subprocess
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status

from app.api.auth import router as auth_router
from app.api.models import HealthResponse, SystemStatus
from app.core.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)


def cli_status(settings: Settings) -> tuple[bool, str | None]:
    executable = shutil.which(settings.alpaca_cli_path)
    if executable is None:
        return False, None
    try:
        result = subprocess.run(
            [executable, "version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, None
    if result.returncode != 0:
        return False, None
    output = result.stdout.strip().splitlines()
    return True, output[0][:64] if output else settings.alpaca_cli_version


@router.get("/health/live", response_model=HealthResponse)
def live() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/ready", response_model=HealthResponse)
def ready(
    response: Response, settings: Annotated[Settings, Depends(get_settings)]
) -> HealthResponse:
    configured = settings.alpaca_paper and not settings.alpaca_live_trade
    if not configured:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="not_ready")
    return HealthResponse(status="ready")


@router.get("/system/status", response_model=SystemStatus)
def system_status(
    settings: Annotated[Settings, Depends(get_settings)],
    current_user: Annotated[str, Depends(get_current_user)],
) -> SystemStatus:
    cli_available, cli_version = cli_status(settings)
    if settings.execution_enabled and not cli_available:
        state: Literal["ready", "degraded", "unavailable", "misconfigured"] = "misconfigured"
    elif not settings.credentials_present or not cli_available:
        state = "degraded"
    else:
        state = "ready"
    return SystemStatus(
        state=state,
        paper_mode=True,
        execution_enabled=settings.execution_enabled,
        kill_switch_active=settings.execution_kill_switch,
        cli_available=cli_available,
        cli_version=cli_version,
        credentials_present=settings.credentials_present,
        account_verified=False,
        supported_options_level=None,
    )
