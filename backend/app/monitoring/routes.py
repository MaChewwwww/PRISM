"""Authenticated monitoring API routes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.monitoring.service import MonitoringReadService
from app.presentation.models import (
    AgentObservability,
    AgentRecord,
    AlternativeCollection,
    AlternativeSession,
    DecisionCollection,
    Governance,
    NewsCollection,
    Overview,
    Portfolio,
    PresentationEnvelope,
    StoryDetail,
    WeeklySummary,
)
from app.presentation.shadow_repository import BacktestPresentationRepository

router = APIRouter(
    prefix="/monitoring", tags=["monitoring"], dependencies=[Depends(get_current_user)]
)
FromQuery = Annotated[datetime, Query(alias="from")]
ToQuery = Annotated[datetime, Query(alias="to")]


def _range(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    if start.tzinfo is None or end.tzinfo is None or start > end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Timezone-aware UTC range required",
        )
    return start.astimezone(UTC), end.astimezone(UTC)


@router.get("/overview", response_model=PresentationEnvelope[Overview])
async def overview(
    start: FromQuery, end: ToQuery, session: Annotated[AsyncSession, Depends(get_db_session)]
):
    first, last = _range(start, end)
    return await MonitoringReadService().overview(session, first, last)


@router.get("/decisions", response_model=PresentationEnvelope[DecisionCollection])
async def decisions(
    start: FromQuery,
    end: ToQuery,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    outcome: str | None = None,
    symbol: str | None = None,
):
    first, last = _range(start, end)
    return await MonitoringReadService().decisions(
        session, first, last, outcome=outcome, symbol=symbol
    )


@router.get("/decisions/{proposal_id}", response_model=PresentationEnvelope[StoryDetail])
async def decision(proposal_id: str, session: Annotated[AsyncSession, Depends(get_db_session)]):
    result = await MonitoringReadService().decision(session, proposal_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recorded decision not found"
        )
    return result


@router.get("/portfolio", response_model=PresentationEnvelope[Portfolio])
async def portfolio(
    start: FromQuery, end: ToQuery, session: Annotated[AsyncSession, Depends(get_db_session)]
):
    first, last = _range(start, end)
    return await MonitoringReadService().portfolio(session, first, last)


@router.get("/alternatives", response_model=PresentationEnvelope[AlternativeCollection])
async def alternatives(
    start: FromQuery,
    end: ToQuery,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    first, last = _range(start, end)
    return await BacktestPresentationRepository(session, settings).list_sessions(
        start=first, end=last
    )


@router.get("/alternatives/{session_id}", response_model=PresentationEnvelope[AlternativeSession])
async def alternative(
    session_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    result = await BacktestPresentationRepository(session, settings).get(session_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recorded session not found"
        )
    return result


@router.get("/news", response_model=PresentationEnvelope[NewsCollection])
async def news(
    start: FromQuery,
    end: ToQuery,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    symbol: str | None = None,
    significance: str | None = None,
):
    first, last = _range(start, end)
    return await MonitoringReadService().news(
        session, first, last, symbol=symbol, significance=significance
    )


@router.get("/agents", response_model=PresentationEnvelope[AgentObservability])
async def agents(
    start: FromQuery, end: ToQuery, session: Annotated[AsyncSession, Depends(get_db_session)]
):
    first, last = _range(start, end)
    return await MonitoringReadService().agents(session, first, last)


@router.get("/agents/{agent_id}", response_model=PresentationEnvelope[AgentRecord])
async def agent(
    agent_id: str,
    start: FromQuery,
    end: ToQuery,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    first, last = _range(start, end)
    observed = await MonitoringReadService().agents(session, first, last)
    record = next((item for item in observed.data.agents if item.id == agent_id), None)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recorded agent not found"
        )
    return PresentationEnvelope(meta=observed.meta, data=record)


@router.get("/governance", response_model=PresentationEnvelope[Governance])
async def governance(session: Annotated[AsyncSession, Depends(get_db_session)]):
    return await MonitoringReadService().governance(session)


@router.get("/weekly-summary", response_model=PresentationEnvelope[WeeklySummary])
async def weekly_summary(session: Annotated[AsyncSession, Depends(get_db_session)]):
    return await MonitoringReadService().weekly_summary(session)
