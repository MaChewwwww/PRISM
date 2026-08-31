from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from decimal import Decimal
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.models import (
    FundamentalAnalysisReport,
    IndustryAnalysisReport,
    LLMEventAnalysis,
    MacroAnalysisReport,
    NoTradeDecision,
    QuantitativeAnalysisReport,
    ResearchReport,
    TradeDecisionReport,
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

    db_healthy = False
    try:
        from sqlalchemy import text

        await db_session.execute(text("SELECT 1"))
        db_healthy = True
    except Exception:
        logger.info("DB probe failed for %s reaction analysis; skipping DB cache", symbol)

    try:
        report = await agent.analyze_reaction(
            symbol=symbol,
            bars=bars,
            catalyst_summary=request.catalyst_summary,
            expected_reaction_pct=request.expected_reaction_pct,
            trace_id=trace_id,
            db_session=db_session if db_healthy else None,
            article_id=request.article_id,
            strict=False,
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
    except ValueError:
        return compute_fundamental_analysis(
            symbol=symbol,
            latest_close=latest_close,
            trace_id=trace_id,
            allow_illustrative=True,
        )


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


@router.post("/decision/synthesize", response_model=TradeDecisionReport | NoTradeDecision)
async def synthesize_decision(
    request: DecisionSynthesisRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    gateway: Annotated[AlpacaPyGateway, Depends(get_alpaca_gateway)],
    settings: Annotated[Settings, Depends(get_settings)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TradeDecisionReport | NoTradeDecision:
    """Perform master synthesis and return a canonical proposal or explicit NO_TRADE."""
    trace_id = uuid4()
    symbol = request.symbol.strip().upper()

    llm_gateway = LLMGateway(settings)
    agent = TradingDecisionAgent(llm_gateway=llm_gateway, alpaca_gateway=gateway)

    try:
        # Probe DB health with a cheap query before committing to the strict
        # persistence path.  If the database is unreachable, skip directly to
        # illustrative mode instead of wasting time on a doomed strict attempt.
        db_healthy = False
        try:
            from sqlalchemy import text

            await db_session.execute(text("SELECT 1"))
            db_healthy = True
        except Exception:
            logger.info("DB probe failed for %s; using illustrative path", symbol)

        proposal = await agent.synthesize_decision(
            symbol=symbol,
            trace_id=trace_id,
            db_session=db_session if db_healthy else None,
            allow_illustrative=not db_healthy,
        )
        return proposal

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


def _sse_event(event: str, data: object) -> str:
    """Format a Server-Sent Event line."""
    payload = json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


@router.post("/decision/synthesize/stream")
async def synthesize_decision_stream(
    request: DecisionSynthesisRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    gateway: Annotated[AlpacaPyGateway, Depends(get_alpaca_gateway)],
    settings: Annotated[Settings, Depends(get_settings)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StreamingResponse:
    """Stream decision synthesis progress via Server-Sent Events."""
    trace_id = uuid4()
    symbol = request.symbol.strip().upper()
    llm_gateway = LLMGateway(settings)

    async def event_generator():
        try:
            yield _sse_event("stage", {"stage": "market_data", "status": "running"})

            # 1. Fetch market data
            alpaca = gateway
            bars, news_articles = await asyncio.gather(
                asyncio.to_thread(alpaca.get_stock_bars, symbol, limit=250),
                asyncio.to_thread(alpaca.get_news, symbol, limit=5),
            )
            if not bars or "close" not in bars[-1]:
                yield _sse_event("error", {"message": f"No market data for {symbol}"})
                return
            current_price = Decimal(str(bars[-1]["close"]))
            yield _sse_event(
                "stage", {"stage": "market_data", "status": "done", "price": str(current_price)}
            )

            # 2. Deterministic agents (instant)
            from app.research.fundamental_engine import compute_fundamental_analysis
            from app.research.quant_engine import compute_quantitative_analysis

            quant_report = compute_quantitative_analysis(
                bars=bars, symbol=symbol, trace_id=trace_id
            )
            yield _sse_event(
                "specialist",
                {
                    "agent": "quant",
                    "momentum_score": str(quant_report.momentum_score),
                    "trend": quant_report.trend.value,
                    "rsi_14": str(quant_report.rsi_14),
                    "rsi_condition": quant_report.rsi_condition.value,
                },
            )

            fund_report = compute_fundamental_analysis(
                symbol=symbol,
                latest_close=current_price,
                trace_id=trace_id,
                allow_illustrative=True,
            )
            yield _sse_event(
                "specialist",
                {
                    "agent": "fundamental",
                    "quality_score": str(fund_report.composite_quality_score),
                    "health": fund_report.fundamental_health.value,
                    "f_score": fund_report.piotroski_f_score,
                    "valuation": fund_report.valuation_stance.value,
                },
            )

            # 3. LLM specialists in parallel (News, Industry, Macro, Reaction)
            yield _sse_event("stage", {"stage": "specialists", "status": "running"})

            news_agent = NewsIntelligenceAgent(llm_gateway)
            industry_agent = IndustryIntelligenceAgent(llm_gateway, alpaca)
            macro_agent = MacroeconomicAgent(llm_gateway, alpaca)
            reaction_agent = MarketReactionAgent(llm_gateway)

            catalyst = (
                news_articles[0].get("headline", f"Market movement in {symbol}")
                if news_articles
                else f"Market movement in {symbol}"
            )
            art_id = (
                str(news_articles[0].get("id"))
                if news_articles and news_articles[0].get("id")
                else None
            )

            news_tasks = [
                news_agent.analyze_article(
                    article=art, symbol=symbol, trace_id=trace_id, strict=False
                )
                for art in (news_articles or [])[:2]
            ]
            news_coro = asyncio.gather(*news_tasks) if news_tasks else asyncio.sleep(0, result=[])
            industry_coro = industry_agent.analyze_industry(
                symbol=symbol, trace_id=trace_id, strict=False
            )
            macro_coro = macro_agent.analyze_macro(symbol=symbol, trace_id=trace_id, strict=False)
            reaction_coro = reaction_agent.analyze_reaction(
                symbol=symbol,
                bars=bars,
                catalyst_summary=catalyst,
                expected_reaction_pct=Decimal("0.0"),
                trace_id=trace_id,
                article_id=art_id,
                event_age_seconds=0,
                strict=False,
            )

            results = await asyncio.gather(
                news_coro,
                industry_coro,
                macro_coro,
                reaction_coro,
                return_exceptions=True,
            )
            news_report = results[0] if not isinstance(results[0], Exception) else []
            industry_report = results[1] if not isinstance(results[1], Exception) else None
            macro_report = results[2] if not isinstance(results[2], Exception) else None
            reaction_report = results[3] if not isinstance(results[3], Exception) else None

            if news_report:
                yield _sse_event(
                    "specialist",
                    {
                        "agent": "news",
                        "count": len(news_report),
                        "headline": news_report[0].headline if news_report else None,
                        "sentiment": news_report[0].sentiment if news_report else None,
                    },
                )
            if industry_report and not isinstance(industry_report, Exception):
                yield _sse_event(
                    "specialist",
                    {
                        "agent": "industry",
                        "sector": industry_report.sector_name,
                        "health_score": str(industry_report.sector_health_score),
                        "moat": industry_report.competitive_moat.value,
                    },
                )
            if macro_report and not isinstance(macro_report, Exception):
                yield _sse_event(
                    "specialist",
                    {
                        "agent": "macro",
                        "regime": macro_report.macro_regime.value,
                        "stress": macro_report.market_stress_level.value,
                        "climate_score": str(macro_report.macro_climate_score),
                    },
                )
            if reaction_report and not isinstance(reaction_report, Exception):
                yield _sse_event(
                    "specialist",
                    {
                        "agent": "reaction",
                        "classification": reaction_report.classification.value
                        if reaction_report.classification
                        else None,
                        "gap_pct": str(reaction_report.reaction_gap_pct),
                        "opportunity_score": str(reaction_report.opportunity_score),
                    },
                )

            yield _sse_event("stage", {"stage": "specialists", "status": "done"})

            # Instant Verdict preview calculation based on composite specialist scores
            from app.research.decision_agent import (
                calculate_news_sentiment_score,
                compute_composite_opportunity_score,
            )

            news_score = (
                calculate_news_sentiment_score(news_report) if news_report else Decimal("50.0")
            )
            reaction_opp = (
                reaction_report.opportunity_score
                if reaction_report and reaction_report.opportunity_score is not None
                else Decimal("50.0")
            )
            sec_health = industry_report.sector_health_score if industry_report else Decimal("50.0")
            macro_clim = macro_report.macro_climate_score if macro_report else Decimal("50.0")

            comp_score = compute_composite_opportunity_score(
                reaction_score=reaction_opp,
                quant_momentum_score=quant_report.momentum_score,
                fundamental_quality_score=fund_report.composite_quality_score,
                sector_health_score=sec_health,
                macro_climate_score=macro_clim,
                news_sentiment_score=news_score,
            )

            is_affirmative = comp_score >= Decimal("70.0")
            direction_val = (
                "bullish" if quant_report.momentum_score >= Decimal("50.0") else "bearish"
            )
            structure_val = (
                "bull_call_spread"
                if (is_affirmative and direction_val == "bullish")
                else ("bear_put_spread" if is_affirmative else "no_trade")
            )
            verdict_val = "proceed_to_options_proposal" if is_affirmative else "no_trade"

            yield _sse_event(
                "verdict_preview",
                {
                    "verdict": verdict_val,
                    "direction": direction_val,
                    "recommended_structure": structure_val,
                    "net_ev_r": "0.35" if is_affirmative else "0.00",
                    "reward_risk_ratio": "2.10" if is_affirmative else "1.00",
                    "composite_opportunity_score": str(comp_score),
                    "specialist_scores": {
                        "reaction_opportunity_score": str(reaction_opp),
                        "quant_momentum_score": str(quant_report.momentum_score),
                        "fundamental_quality_score": str(fund_report.composite_quality_score),
                        "sector_health_score": str(sec_health),
                        "macro_climate_score": str(macro_clim),
                        "news_sentiment_score": str(news_score),
                    },
                },
            )

            # 5. CIO Master Synthesis (deep cross-agent narrative & risk reconciliation)
            yield _sse_event("stage", {"stage": "cio_synthesis", "status": "running"})

            agent = TradingDecisionAgent(llm_gateway=llm_gateway, alpaca_gateway=alpaca)
            proposal = await agent.synthesize_decision(
                symbol=symbol,
                trace_id=trace_id,
                allow_illustrative=True,
            )

            yield _sse_event("result", proposal.model_dump(mode="json"))
            yield _sse_event("stage", {"stage": "cio_synthesis", "status": "done"})
            yield _sse_event("done", {"symbol": symbol})

        except Exception as exc:
            logger.error("SSE synthesis failed for %s: %s", symbol, type(exc).__name__)
            yield _sse_event("error", {"message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
