"""Read-only compatibility routes for documented presentation projections."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.presentation.models import AlternativeCollection, PresentationEnvelope
from app.presentation.shadow_repository import BacktestPresentationRepository

router = APIRouter(
    prefix="/presentation", tags=["presentation"], dependencies=[Depends(get_current_user)]
)

FromQuery = Annotated[datetime, Query(alias="from")]
ToQuery = Annotated[datetime, Query(alias="to")]


def _validated_range(from_time: datetime, to_time: datetime) -> tuple[datetime, datetime]:
    if (
        from_time.tzinfo is None
        or to_time.tzinfo is None
        or from_time.utcoffset() is None
        or to_time.utcoffset() is None
        or from_time > to_time
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Presentation ranges require timezone-aware UTC timestamps",
        )
    return from_time.astimezone(UTC), to_time.astimezone(UTC)


@router.get("/alternatives", response_model=PresentationEnvelope[AlternativeCollection])
async def alternatives(
    from_time: FromQuery,
    to_time: ToQuery,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PresentationEnvelope[AlternativeCollection]:
    """Project recorded ShadowFund sessions through the documented read model."""
    start, end = _validated_range(from_time, to_time)
    return await BacktestPresentationRepository(session, settings).list_sessions(
        start=start, end=end
    )
