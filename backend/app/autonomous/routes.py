"""Authenticated operational read endpoints for the autonomous worker."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models import (
    AutonomousCycleCollection,
    AutonomousDecisionCollection,
    AutonomousExecutionCollection,
    AutonomousPortfolioLatest,
)
from app.autonomous.read_service import AutonomousReadService
from app.core.auth.dependencies import get_current_user
from app.core.database import get_db_session

router = APIRouter(
    prefix="/autonomous",
    tags=["autonomous"],
    dependencies=[Depends(get_current_user)],
)


def _range(from_at: datetime, to_at: datetime) -> tuple[datetime, datetime]:
    if from_at.tzinfo is None or to_at.tzinfo is None or from_at > to_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A timezone-aware UTC range is required",
        )
    return from_at.astimezone(UTC), to_at.astimezone(UTC)


FromQuery = Annotated[datetime, Query(alias="from")]
ToQuery = Annotated[datetime, Query(alias="to")]
LimitQuery = Annotated[int, Query(ge=1, le=200)]


@router.get("/cycles", response_model=AutonomousCycleCollection)
async def cycles(
    from_at: FromQuery,
    to_at: ToQuery,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: LimitQuery = 100,
) -> AutonomousCycleCollection:
    start, end = _range(from_at, to_at)
    try:
        return await AutonomousReadService().list_cycles(session, start=start, end=end, limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Autonomous cycle history is unavailable",
        ) from exc


@router.get("/decisions", response_model=AutonomousDecisionCollection)
async def decisions(
    from_at: FromQuery,
    to_at: ToQuery,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: LimitQuery = 100,
    symbol: str | None = Query(default=None, max_length=20),
    outcome: str | None = Query(default=None, max_length=40),
) -> AutonomousDecisionCollection:
    start, end = _range(from_at, to_at)
    normalized_outcome = outcome.upper() if outcome else None
    if normalized_outcome not in {None, "APPROVE", "REJECT", "MODIFIED_PENDING_ACCEPTANCE"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported autonomous authorization outcome",
        )
    try:
        return await AutonomousReadService().list_decisions(
            session,
            start=start,
            end=end,
            limit=limit,
            symbol=symbol.strip().upper() if symbol else None,
            outcome=normalized_outcome,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Autonomous decision history is unavailable",
        ) from exc


@router.get("/executions", response_model=AutonomousExecutionCollection)
async def executions(
    from_at: FromQuery,
    to_at: ToQuery,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: LimitQuery = 100,
    receipt_status: str | None = Query(default=None, alias="status", max_length=32),
) -> AutonomousExecutionCollection:
    start, end = _range(from_at, to_at)
    normalized_status = receipt_status.lower() if receipt_status else None
    if normalized_status not in {
        None,
        "pending",
        "submitted",
        "reconciling",
        "rejected",
        "filled",
        "failed",
    }:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported autonomous execution status",
        )
    try:
        return await AutonomousReadService().list_executions(
            session,
            start=start,
            end=end,
            limit=limit,
            status=normalized_status,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Autonomous execution history is unavailable",
        ) from exc


@router.get("/portfolio/latest", response_model=AutonomousPortfolioLatest)
async def latest_portfolio(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AutonomousPortfolioLatest:
    try:
        return await AutonomousReadService().latest_portfolio(session)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Autonomous portfolio state is unavailable",
        ) from exc
