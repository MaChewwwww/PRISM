from __future__ import annotations

import hashlib
import logging
from decimal import Decimal
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.models import (
    DecisionSynthesisResult,
    FundamentalAnalysisReport,
    IndustryAnalysisReport,
    LLMEventAnalysis,
    MacroAnalysisReport,
    NoTradeDecision,
    QuantitativeAnalysisReport,
    ResearchReport,
)
from app.core.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.llm_gateway import LLMGateway
from app.market.alpaca_gateway import AlpacaPyGateway
from app.research.decision_agent import TradingDecisionAgent
from app.research.fundamental_engine import compute_fundamental_analysis
from app.research.industry_agent import IndustryIntelligenceAgent
from app.research.macro_agent import MacroeconomicAgent
from app.research.news_agent import NewsIntelligenceAgent
from app.research.quant_engine import compute_quantitative_analysis
from app.research.reaction_agent import MarketReactionAgent

router = APIRouter(prefix="/research", tags=["research"])
logger = logging.getLogger(__name__)


class NewsAnalysisRequest(BaseModel):
    symbol: str = Field(..., description="Ticker symbol to query news for, e.g. AAPL")
    limit: int = Field(
        5, ge=1, le=20, description="Number of news articles to retrieve and analyze"
    )


class MarketReactionRequest(BaseModel):
    symbol: str = Field(..., min_length=1, description="Ticker symbol, e.g. AAPL")
    catalyst_summary: str = Field(
        ...,
        min_length=1,
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
    symbol: str = Field(
        ...,
        min_length=1,
        description="Ticker symbol to quantitatively analyze, e.g. AAPL",
    )
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

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("symbol must not be blank")
        return normalized


class FundamentalAnalysisRequest(BaseModel):
    symbol: str = Field(
        ...,
        min_length=1,
        description="Ticker symbol to analyze fundamentals for, e.g. NVDA",
    )
    bar_limit: int = Field(
        default=5,
        ge=1,
        le=30,
        description="Number of recent price bars to retrieve for live valuation calculation",
    )

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("symbol must not be blank")
        return normalized


class MacroAnalysisRequest(BaseModel):
    symbol: str = Field(
        ...,
        min_length=1,
        description="Target ticker symbol to assess macroeconomic impact for, e.g. NVDA",
    )

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("symbol must not be blank")
        return normalized


class DecisionSynthesisRequest(BaseModel):
    symbol: str = Field(
        ...,
        min_length=1,
        description="Target ticker symbol to run master 7-agent synthesis on, e.g. NVDA",
    )

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("symbol must not be blank")
        return normalized


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
            detail="Alpaca research provider is unavailable",
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
        articles = await run_in_threadpool(
            gateway.get_news,
            symbol=request.symbol.strip().upper(),
            limit=request.limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Alpaca news provider is temporarily unavailable",
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
        except Exception:
            # Continue analyzing other articles, logging the error
            logger.warning(
                "News analysis failed for article_id=%s",
                article.get("id"),
            )

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
        bars = await run_in_threadpool(
            gateway.get_stock_bars,
            symbol=symbol,
            limit=request.bar_limit,
        )
    except Exception as exc:
        logger.warning(
            "Alpaca market-bar provider failed for symbol=%s: %s",
            symbol,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Alpaca market data provider is temporarily unavailable",
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
        logger.error(
            "Market reaction analysis failed for symbol=%s: %s",
            symbol,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Market reaction analysis is temporarily unavailable",
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
        bars = await run_in_threadpool(
            gateway.get_stock_bars,
            symbol=symbol,
            limit=request.bar_limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Market data is temporarily unavailable"
        ) from exc

    if not bars:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fresh market data is unavailable",
        )

    return compute_quantitative_analysis(bars=bars, symbol=symbol, trace_id=trace_id)


@router.post("/fundamental/analyze", response_model=FundamentalAnalysisReport)
async def analyze_fundamental(
    request: FundamentalAnalysisRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    gateway: Annotated[AlpacaPyGateway, Depends(get_alpaca_gateway)],
) -> FundamentalAnalysisReport:
    """Perform 100% deterministic fundamental financial statement and valuation analysis."""
    trace_id = uuid4()
    symbol = request.symbol.strip().upper()

    latest_close: Decimal | None = None
    try:
        bars = await run_in_threadpool(
            gateway.get_stock_bars,
            symbol=symbol,
            limit=request.bar_limit,
        )
        if bars and len(bars) > 0 and "close" in bars[-1]:
            latest_close = Decimal(str(bars[-1]["close"]))
    except Exception as exc:
        logger.warning(
            "Alpaca price-bar provider failed for symbol=%s: %s",
            symbol,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Market data is temporarily unavailable"
        ) from exc

    if latest_close is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fresh market data is unavailable",
        )

    try:
        return compute_fundamental_analysis(
            symbol=symbol,
            latest_close=latest_close,
            trace_id=trace_id,
            allow_illustrative=False,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sourced fundamental data is unavailable",
        ) from exc


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
        logger.error(
            "Industry analysis failed for %s: %s",
            symbol,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Industry analysis is temporarily unavailable",
        ) from exc


@router.post("/macro/analyze", response_model=MacroAnalysisReport)
async def analyze_macro(
    request: MacroAnalysisRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    gateway: Annotated[AlpacaPyGateway, Depends(get_alpaca_gateway)],
    settings: Annotated[Settings, Depends(get_settings)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MacroAnalysisReport:
    """Perform macroeconomic regime, interest rate, and cross-asset intelligence analysis."""
    trace_id = uuid4()
    symbol = request.symbol.strip().upper()

    llm_gateway = LLMGateway(settings)
    agent = MacroeconomicAgent(llm_gateway=llm_gateway, alpaca_gateway=gateway)

    try:
        report = await agent.analyze_macro(
            symbol=symbol,
            trace_id=trace_id,
            db_session=db_session,
        )
        return report
    except Exception as exc:
        logger.error(
            "Macroeconomic analysis failed for %s: %s",
            symbol,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Macroeconomic analysis is temporarily unavailable",
        ) from exc


@router.post("/decision/synthesize", response_model=DecisionSynthesisResult)
async def synthesize_decision(
    request: DecisionSynthesisRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    gateway: Annotated[AlpacaPyGateway, Depends(get_alpaca_gateway)],
    settings: Annotated[Settings, Depends(get_settings)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DecisionSynthesisResult:
    """Perform master synthesis and return a canonical proposal or explicit NO_TRADE."""
    trace_id = uuid4()
    symbol = request.symbol.strip().upper()

    llm_gateway = LLMGateway(settings)
    agent = TradingDecisionAgent(llm_gateway=llm_gateway, alpaca_gateway=gateway)

    try:
        proposal = await agent.synthesize_decision(
            symbol=symbol,
            trace_id=trace_id,
            db_session=db_session,
            allow_illustrative=False,
        )
        bundle_digest = hashlib.sha256(proposal.model_dump_json().encode("utf-8")).hexdigest()
        # The current specialist report has no live option contract selection or
        # persisted proposal binding. Never promote it to executable authority.
        return NoTradeDecision(
            trace_id=trace_id,
            symbol=symbol,
            research_bundle_digest=bundle_digest,
            reason=(
                proposal.synthesis_rationale
                if proposal.verdict.value == "no_trade"
                else "Canonical TradeProposal binding and live option selection are unavailable"
            ),
        )
    except ValueError:
        bundle_digest = hashlib.sha256(f"no-evidence:{symbol}:{trace_id}".encode()).hexdigest()
        return NoTradeDecision(
            trace_id=trace_id,
            symbol=symbol,
            research_bundle_digest=bundle_digest,
            reason="Required live research evidence is unavailable",
        )
    except Exception as exc:
        logger.error(
            "Decision synthesis failed for %s: %s",
            symbol,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trading decision synthesis is temporarily unavailable",
        ) from exc
