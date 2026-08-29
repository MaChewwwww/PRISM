from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.models import LLMEventAnalysis
from app.core.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.llm_gateway import LLMGateway
from app.market.alpaca_gateway import AlpacaPyGateway
from app.research.news_agent import NewsIntelligenceAgent

router = APIRouter(prefix="/research", tags=["research"])


class NewsAnalysisRequest(BaseModel):
    symbol: str = Field(..., description="Ticker symbol to query news for, e.g. AAPL")
    limit: int = Field(
        5, ge=1, le=20, description="Number of news articles to retrieve and analyze"
    )


def get_alpaca_gateway(settings: Annotated[Settings, Depends(get_settings)]) -> AlpacaPyGateway:
    if not settings.credentials_present:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alpaca API credentials are not configured",
        )
    try:
        return AlpacaPyGateway(settings)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/news/analyze", response_model=list[LLMEventAnalysis])
async def analyze_news(
    request: NewsAnalysisRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    gateway: Annotated[AlpacaPyGateway, Depends(get_alpaca_gateway)],
) -> list[LLMEventAnalysis]:
    """Retrieve news articles for a symbol and run LLM sentiment and significance analysis."""
    trace_id = uuid4()

    try:
        articles = gateway.get_news(symbol=request.symbol.strip().upper(), limit=request.limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch news from Alpaca: {exc!s}",
        ) from exc

    if not articles:
        return []

    llm_gateway = LLMGateway(settings)
    agent = NewsIntelligenceAgent(llm_gateway)

    analyses = []
    for article in articles:
        try:
            analysis = await agent.analyze_article(
                article=article,
                symbol=request.symbol.strip().upper(),
                trace_id=trace_id,
                db_session=db_session,
            )
            analyses.append(analysis)
        except Exception as exc:
            # Continue analyzing other articles, logging the error
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to analyze article {article.get('id')}: {exc}", exc_info=True)

    return analyses
