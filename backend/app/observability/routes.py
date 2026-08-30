from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models import LLMUsageSummaryResponse
from app.core.auth.dependencies import get_current_user
from app.core.database import get_db_session
from app.observability.models import LLMUsageEventModel

router = APIRouter(prefix="/llm-usage", tags=["observability"])


@router.get("/summary", response_model=LLMUsageSummaryResponse)
async def llm_usage_summary(
    current_user: Annotated[str, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    from_at: Annotated[datetime, Query(alias="from")],
    to_at: Annotated[datetime, Query(alias="to")],
) -> LLMUsageSummaryResponse:
    if from_at.tzinfo is None or to_at.tzinfo is None or from_at > to_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="UTC range required"
        )
    try:
        row = (
            await session.execute(
                select(
                    func.count(LLMUsageEventModel.id),
                    func.count(LLMUsageEventModel.id).filter(
                        LLMUsageEventModel.usage_available.is_(True)
                    ),
                    func.coalesce(func.sum(LLMUsageEventModel.prompt_tokens), 0),
                    func.coalesce(func.sum(LLMUsageEventModel.completion_tokens), 0),
                    func.coalesce(func.sum(LLMUsageEventModel.total_tokens), 0),
                    func.sum(LLMUsageEventModel.estimated_cost_usd),
                ).where(
                    LLMUsageEventModel.observed_at >= from_at.astimezone(UTC),
                    LLMUsageEventModel.observed_at <= to_at.astimezone(UTC),
                )
            )
        ).one()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM usage is unavailable"
        ) from exc
    return LLMUsageSummaryResponse(
        request_count=int(row[0]),
        usage_available_count=int(row[1]),
        prompt_tokens=int(row[2]),
        completion_tokens=int(row[3]),
        total_tokens=int(row[4]),
        estimated_cost_usd=row[5],
    )
