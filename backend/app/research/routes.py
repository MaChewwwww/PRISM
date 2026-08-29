from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.models import (
    IndustryAnalysisReport,
    LLMEventAnalysis,
    QuantitativeAnalysisReport,
    ResearchReport,
)
from app.core.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.llm_gateway import LLMGateway
from app.market.alpaca_gateway import AlpacaPyGateway
from app.research.industry_agent import IndustryIntelligenceAgent
from app.research.news_agent import NewsIntelligenceAgent
from app.research.quant_engine import compute_quantitative_analysis
from app.research.reaction_agent import MarketReactionAgent

router = APIRouter(prefix="/research", tags=["research"])


class NewsAnalysisRequest(BaseModel):
    symbol: str = Field(..., description="Ticker symbol to query news for, e.g. AAPL")
    limit: int = Field(
        5, ge=1, le=20, description="Number of news articles to retrieve and analyze"
    )


class MarketReactionRequest(BaseModel):
    symbol: str = Field(..., description="Ticker symbol, e.g. AAPL")
    catalyst_summary: str = Field(
        ...,
        description="Summary of the catalyst or news event to compare market reaction against",
    )
    expected_reaction_pct: Decimal | None = Field(
        default=None,
        description="Expected price reaction percentage (e.g. 3.5 for +3.5%), or null if unknown",
    )
    article_id: str | None = Field(
        default=None,
        description="Optional article ID for caching linkage with News Agent",
    )
    bar_limit: int = Field(
        default=30,
        ge=2,
        le=100,
        description="Number of recent price bars to retrieve for baseline calculation",
    )


class QuantitativeAnalysisRequest(BaseModel):
    symbol: str = Field(..., description="Ticker symbol to quantitatively analyze, e.g. AAPL")
    bar_limit: int = Field(
        default=250,
        ge=20,
        le=500,
        description="Number of historical bars to retrieve (default 250 for 200-day SMA)",
    )


class IndustryAnalysisRequest(BaseModel):
    symbol: str = Field(..., description="Ticker symbol to analyze industry for, e.g. NVDA")
    custom_peers: list[str] | None = Field(
        default=None,
        description="Optional custom peer tickers to compare against",
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
            import logging

            logger = logging.getLogger(__name__)
            logger.warning("Failed to analyze article %s: %s", article.get("id"), exc)

    return analyses


@router.post("/reaction/analyze", response_model=ResearchReport)
async def analyze_reaction(
    request: MarketReactionRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    gateway: Annotated[AlpacaPyGateway, Depends(get_alpaca_gateway)],
) -> ResearchReport:
    """Retrieve market bars for a symbol and run Market Reaction / Mispricing analysis."""
    trace_id = uuid4()
    symbol = request.symbol.strip().upper()

    try:
        bars = gateway.get_stock_bars(symbol=symbol, limit=request.bar_limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch market bars from Alpaca: {exc!s}",
        ) from exc

    if not bars:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No market data bars available for symbol {symbol}",
        )

    llm_gateway = LLMGateway(settings)
    agent = MarketReactionAgent(llm_gateway)

    try:
        report = await agent.analyze_reaction(
            symbol=symbol,
            bars=bars,
            catalyst_summary=request.catalyst_summary,
            expected_reaction_pct=request.expected_reaction_pct,
            trace_id=trace_id,
            db_session=db_session,
            article_id=request.article_id,
        )
        return report
    except Exception as exc:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Market reaction analysis failed for {symbol}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Market reaction analysis failed: {exc!s}",
        ) from exc


@router.post("/quant/analyze", response_model=QuantitativeAnalysisReport)
async def analyze_quantitative(
    request: QuantitativeAnalysisRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    gateway: Annotated[AlpacaPyGateway, Depends(get_alpaca_gateway)],
) -> QuantitativeAnalysisReport:
    """Perform 100% deterministic quantitative and technical momentum analysis."""
    trace_id = uuid4()
    symbol = request.symbol.strip().upper()

    try:
        bars = gateway.get_stock_bars(symbol=symbol, limit=request.bar_limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch market bars from Alpaca: {exc!s}",
        ) from exc

    if not bars:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No market data bars available for symbol {symbol}",
        )

    return compute_quantitative_analysis(bars=bars, symbol=symbol, trace_id=trace_id)


@router.post("/industry/analyze", response_model=IndustryAnalysisReport)
async def analyze_industry(
    request: IndustryAnalysisRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    gateway: Annotated[AlpacaPyGateway, Depends(get_alpaca_gateway)],
    settings: Annotated[Settings, Depends(get_settings)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IndustryAnalysisReport:
    """Perform industry, competitive landscape, and relative alpha intelligence analysis."""
    trace_id = uuid4()
    symbol = request.symbol.strip().upper()

    llm_gateway = LLMGateway(settings)
    agent = IndustryIntelligenceAgent(llm_gateway=llm_gateway, alpaca_gateway=gateway)

    try:
        report = await agent.analyze_industry(
            symbol=symbol,
            trace_id=trace_id,
            custom_peers=request.custom_peers,
            db_session=db_session,
        )
        return report
    except Exception as exc:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Industry analysis failed for {symbol}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Industry analysis failed: {exc!s}",
        ) from exc
