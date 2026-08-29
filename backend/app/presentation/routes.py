from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth.dependencies import get_current_user
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
from app.presentation.service import (
    get_agent,
    get_agents,
    get_alternative,
    get_alternatives,
    get_decision,
    get_decisions,
    get_governance,
    get_news,
    get_overview,
    get_portfolio,
    get_weekly_summary,
)

router = APIRouter(
    prefix="/presentation",
    tags=["presentation"],
    dependencies=[Depends(get_current_user)],
)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Presentation ranges require timezone-aware UTC timestamps",
        )
    return value.astimezone(UTC)


def _validated_range(from_time: datetime, to_time: datetime) -> tuple[datetime, datetime]:
    start = _utc(from_time)
    end = _utc(to_time)
    if start > end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Range start must be on or before range end",
        )
    return start, end


FromQuery = Annotated[datetime, Query(alias="from")]
ToQuery = Annotated[datetime, Query(alias="to")]


@router.get("/overview", response_model=PresentationEnvelope[Overview])
def overview(from_time: FromQuery, to_time: ToQuery) -> PresentationEnvelope[Overview]:
    start, end = _validated_range(from_time, to_time)
    return get_overview(start, end)


@router.get("/decisions", response_model=PresentationEnvelope[DecisionCollection])
def decisions(
    from_time: FromQuery,
    to_time: ToQuery,
    outcome: str | None = None,
    symbol: str | None = None,
) -> PresentationEnvelope[DecisionCollection]:
    start, end = _validated_range(from_time, to_time)
    return get_decisions(start, end, outcome=outcome, symbol=symbol)


@router.get("/decisions/{decision_id}", response_model=PresentationEnvelope[StoryDetail])
def decision(decision_id: str) -> PresentationEnvelope[StoryDetail]:
    result = get_decision(decision_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    return result


@router.get("/portfolio", response_model=PresentationEnvelope[Portfolio])
def portfolio(from_time: FromQuery, to_time: ToQuery) -> PresentationEnvelope[Portfolio]:
    start, end = _validated_range(from_time, to_time)
    return get_portfolio(start, end)


@router.get("/alternatives", response_model=PresentationEnvelope[AlternativeCollection])
def alternatives(
    from_time: FromQuery, to_time: ToQuery
) -> PresentationEnvelope[AlternativeCollection]:
    start, end = _validated_range(from_time, to_time)
    return get_alternatives(start, end)


@router.get("/alternatives/{session_id}", response_model=PresentationEnvelope[AlternativeSession])
def alternative(session_id: str) -> PresentationEnvelope[AlternativeSession]:
    result = get_alternative(session_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return result


@router.get("/news", response_model=PresentationEnvelope[NewsCollection])
def news(
    from_time: FromQuery,
    to_time: ToQuery,
    symbol: str | None = None,
    significance: str | None = None,
) -> PresentationEnvelope[NewsCollection]:
    start, end = _validated_range(from_time, to_time)
    return get_news(start, end, symbol=symbol, significance=significance)


@router.get("/agents", response_model=PresentationEnvelope[AgentObservability])
def agents(from_time: FromQuery, to_time: ToQuery) -> PresentationEnvelope[AgentObservability]:
    start, end = _validated_range(from_time, to_time)
    return get_agents(start, end)


@router.get("/agents/{agent_id}", response_model=PresentationEnvelope[AgentRecord])
def agent(agent_id: str) -> PresentationEnvelope[AgentRecord]:
    result = get_agent(agent_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return result


@router.get("/governance", response_model=PresentationEnvelope[Governance])
def governance() -> PresentationEnvelope[Governance]:
    return get_governance()


@router.get("/weekly-summary", response_model=PresentationEnvelope[WeeklySummary])
def weekly_summary() -> PresentationEnvelope[WeeklySummary]:
    return get_weekly_summary()
