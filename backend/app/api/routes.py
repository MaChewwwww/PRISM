from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import router as auth_router
from app.api.models import AutonomousStatus, HealthResponse, KillSwitchRequest, SystemStatus
from app.autonomous.control import control_payload, get_or_create_control, set_kill_switch
from app.core.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.core.database import check_database, get_db_session
from app.execution.cli_gateway import verify_cli_capabilities
from app.presentation.routes import router as presentation_router
from app.research.routes import router as research_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(research_router)
router.include_router(presentation_router)


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


async def get_database_readiness() -> bool:
    return await check_database()


@router.get("/health/ready", response_model=HealthResponse)
async def ready(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    database_ready: Annotated[bool, Depends(get_database_readiness)],
) -> HealthResponse:
    configured = settings.alpaca_paper and not settings.alpaca_live_trade and database_ready
    if settings.autonomous_trading_enabled:
        cli_available, _ = cli_status(settings)
        account_verified, options_level = paper_account_status(settings)
        configured = (
            configured
            and settings.execution_enabled
            and bool(settings.active_ruleset_version)
            and settings.credentials_present
            and cli_available
            and account_verified
            and (options_level is not None and options_level >= 3)
            and verify_cli_capabilities(settings)
        )
    if not configured:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="not_ready")
    return HealthResponse(status="ready")


def paper_account_status(settings: Settings) -> tuple[bool, int | None]:
    """Verify the paper account through the pinned CLI without exposing output."""
    executable = shutil.which(settings.alpaca_cli_path)
    if executable is None or not settings.credentials_present:
        return False, None
    env = {
        **os.environ,
        "ALPACA_API_KEY": settings.alpaca_api_key or "",
        "ALPACA_SECRET_KEY": settings.alpaca_secret_key or "",
        "ALPACA_LIVE_TRADE": "false",
        "ALPACA_OUTPUT": "json",
    }
    try:
        result = subprocess.run(
            [executable, "account", "get", "--quiet"],
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
            shell=False,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, None
    if result.returncode != 0:
        return False, None
    try:
        payload = json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError):
        return False, None
    if not isinstance(payload, dict) or str(payload.get("status", "")).lower() != "active":
        return False, None
    level = payload.get("options_trading_level", payload.get("options_level"))
    if level is None:
        return True, None
    digits = "".join(character for character in str(level) if character.isdigit())
    return True, int(digits) if digits else None


@router.get("/autonomous/status", response_model=AutonomousStatus)
async def autonomous_status(
    settings: Annotated[Settings, Depends(get_settings)],
    current_user: Annotated[str, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AutonomousStatus:
    try:
        control = await get_or_create_control(session, settings)
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Autonomous control state is unavailable",
        ) from exc
    return AutonomousStatus.model_validate(control_payload(control, settings))


@router.post("/autonomous/kill-switch", response_model=AutonomousStatus)
async def autonomous_kill_switch(
    request: KillSwitchRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    current_user: Annotated[str, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AutonomousStatus:
    if not request.reason.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Reason required"
        )
    try:
        control = await set_kill_switch(
            session,
            settings,
            active=request.active,
            actor=current_user,
            reason=request.reason,
        )
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Autonomous control state is unavailable",
        ) from exc
    return AutonomousStatus.model_validate(control_payload(control, settings))


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
