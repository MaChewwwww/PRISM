from __future__ import annotations

import json
import logging
import math
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.models import (
    MacroAnalysisReport,
    MacroAssetPerformance,
    MacroRegime,
    MarketStressLevel,
    RateEnvironment,
)
from app.core.llm_gateway import LLMGateway
from app.market.alpaca_gateway import AlpacaPyGateway
from app.research.models import MacroAnalysisModel

logger = logging.getLogger(__name__)

# Key macro asset benchmarks across Equities, Rates, FX, and Commodities
MACRO_BENCHMARK_REGISTRY: list[tuple[str, str]] = [
    ("SPY", "S&P 500 Broad Market Index"),
    ("QQQ", "Nasdaq 100 Tech & Growth Index"),
    ("IWM", "Russell 2000 Small-Cap / Credit"),
    ("TLT", "20+ Year US Treasury Bond (Yield Proxy)"),
    ("GLD", "Gold / Safe Haven & Inflation Hedge"),
    ("UUP", "US Dollar Index / Global Liquidity"),
]

SYSTEM_PROMPT = (
    "You are an expert macroeconomic strategist and cross-asset analyst for PRISM.\n"
    "STRICT AGENT SCOPE BOUNDARIES:\n"
    "1. Focus EXCLUSIVELY on broad macroeconomic regimes, interest rate trends, inflation, "
    "market volatility, and fiscal/monetary policy.\n"
    "2. DO NOT include company financial statements, balance sheets, or earnings metrics "
    "(reserved for Fundamental Agent).\n"
    "3. DO NOT calculate technical chart patterns or RSI (reserved for Quantitative Agent).\n"
    "4. Explain clearly how the overall macro climate impacts the target stock.\n"
    "Output strictly valid JSON matching the schema."
)


class MacroAnalysisLLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    macro_regime: MacroRegime = Field(
        ...,
        description="Overall macroeconomic regime ('risk_on', 'risk_off', 'expansionary', "
        "'contractionary', 'stagflationary', 'transitional')",
    )
    rate_environment: RateEnvironment = Field(
        ...,
        description="Prevailing monetary policy and interest rate environment "
        "('rate_cut_cycle', 'pause_elevated', 'rising_rates', 'neutral')",
    )
    macro_tailwinds: list[str] = Field(
        default_factory=list,
        description="Top 2-3 strictly macro-level tailwinds (e.g. rate cuts, easing liquidity)",
    )
    macro_headwinds: list[str] = Field(
        default_factory=list,
        description="Top 2-3 strictly macro-level headwinds (e.g. sticky CPI, elevated yields)",
    )
    stock_macro_sensitivity: str = Field(
        ...,
        description="Analysis of how target stock responds to prevailing macro regime",
    )
    thesis: str = Field(
        ...,
        description="Synthesis thesis detailing net macroeconomic stance towards equities",
    )


def compute_period_return(bars: list[dict[str, Any]], days: int) -> Decimal:
    """Compute percentage return over the last `days` bars."""
    if not bars:
        return Decimal("0.0")
    closes = [Decimal(str(b["close"])) for b in bars]
    if len(closes) < 2:
        return Decimal("0.0")
    lookback = min(days, len(closes) - 1)
    start_price = closes[-lookback - 1]
    end_price = closes[-1]
    if start_price == Decimal("0"):
        return Decimal("0.0")
    ret = ((end_price - start_price) / start_price) * Decimal("100.0")
    return round(ret, 2)


def compute_market_stress_level(
    spy_bars: list[dict[str, Any]],
) -> tuple[MarketStressLevel, Decimal]:
    """Compute annualized realized volatility of SPY to quantify market stress."""
    if len(spy_bars) < 5:
        return MarketStressLevel.LOW, Decimal("15.0")

    closes = [float(b["close"]) for b in spy_bars if "close" in b]
    returns = [
        (closes[i] - closes[i - 1]) / closes[i - 1]
        for i in range(1, len(closes))
        if closes[i - 1] > 0
    ]
    if not returns:
        return MarketStressLevel.LOW, Decimal("15.0")

    mean_ret = sum(returns) / len(returns)
    variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
    std_dev = math.sqrt(variance)
    annualized_vol = std_dev * math.sqrt(252) * 100.0
    vol_dec = round(Decimal(str(annualized_vol)), 1)

    if vol_dec >= Decimal("30.0"):
        stress = MarketStressLevel.EXTREME
    elif vol_dec >= Decimal("22.0"):
        stress = MarketStressLevel.HIGH
    elif vol_dec >= Decimal("15.0"):
        stress = MarketStressLevel.MODERATE
    else:
        stress = MarketStressLevel.LOW

    return stress, vol_dec


def compute_macro_climate_score(
    spy_20d: Decimal,
    qqq_20d: Decimal,
    tlt_20d: Decimal,
    vol_stress: MarketStressLevel,
) -> Decimal:
    """Deterministically compute Macro Climate Score (0-100) from equities and rates."""
    # Factor 1: SPY 20d return (35 pts max, centered at 17.5 pts for 0%)
    spy_norm = min(
        Decimal("1.0"),
        max(Decimal("0.0"), Decimal("0.5") + (spy_20d / Decimal("20.0"))),
    )
    score_spy = spy_norm * Decimal("35.0")

    # Factor 2: QQQ 20d return (25 pts max, centered at 12.5 pts for 0%)
    qqq_norm = min(
        Decimal("1.0"),
        max(Decimal("0.0"), Decimal("0.5") + (qqq_20d / Decimal("20.0"))),
    )
    score_qqq = qqq_norm * Decimal("25.0")

    # Factor 3: Treasury Stability (20 pts max) - moderate positive TLT return is favorable
    tlt_norm = min(
        Decimal("1.0"),
        max(Decimal("0.0"), Decimal("0.5") + (tlt_20d / Decimal("20.0"))),
    )
    score_tlt = tlt_norm * Decimal("20.0")

    # Factor 4: Volatility Stress Bonus (20 pts max)
    if vol_stress == MarketStressLevel.LOW:
        score_vol = Decimal("20.0")
    elif vol_stress == MarketStressLevel.MODERATE:
        score_vol = Decimal("14.0")
    elif vol_stress == MarketStressLevel.HIGH:
        score_vol = Decimal("7.0")
    else:
        score_vol = Decimal("2.0")

    total = score_spy + score_qqq + score_tlt + score_vol
    return min(Decimal("100.0"), max(Decimal("0.0"), round(total, 1)))


class MacroeconomicAgent:
    """Agent #5: Assesses macroeconomic regimes, rates, indexes, and volatility context."""

    def __init__(self, llm_gateway: LLMGateway, alpaca_gateway: AlpacaPyGateway) -> None:
        self.llm_gateway = llm_gateway
        self.alpaca_gateway = alpaca_gateway

    async def analyze_macro(
        self,
        symbol: str,
        trace_id: UUID,
        db_session: AsyncSession | None = None,
    ) -> MacroAnalysisReport:
        sym = symbol.strip().upper()
        active_model = self.llm_gateway._settings.llm_model or "default"

        # Check DB Cache
        if db_session is not None:
            try:
                stmt = (
                    select(MacroAnalysisModel)
                    .where(
                        MacroAnalysisModel.symbol == sym,
                        MacroAnalysisModel.model_name == active_model,
                    )
                    .order_by(MacroAnalysisModel.created_at.desc())
                    .limit(1)
                )
                result = await db_session.execute(stmt)
                cached = result.scalar_one_or_none()
                if cached is not None:
                    logger.info(f"Returning cached Macro Analysis for {sym}")
                    assets_data = [
                        MacroAssetPerformance.model_validate(a)
                        for a in json.loads(cached.assets_json)
                    ]
                    return MacroAnalysisReport(
                        id=UUID(cached.id),
                        trace_id=UUID(cached.trace_id),
                        created_at=cached.created_at,
                        symbol=cached.symbol,
                        macro_regime=MacroRegime(cached.macro_regime),
                        rate_environment=RateEnvironment(cached.rate_environment),
                        market_stress_level=MarketStressLevel(cached.market_stress_level),
                        macro_climate_score=cached.macro_climate_score,
                        assets=assets_data,
                        macro_tailwinds=json.loads(cached.macro_tailwinds_json),
                        macro_headwinds=json.loads(cached.macro_headwinds_json),
                        stock_macro_sensitivity=cached.stock_macro_sensitivity,
                        thesis=cached.thesis,
                    )
            except Exception as exc:
                logger.warning(f"Error checking macro cache: {exc}")

        # 1. Fetch Market Bars for Macro Asset Basket
        asset_performances: list[MacroAssetPerformance] = []
        asset_returns_map: dict[str, tuple[Decimal, Decimal]] = {}

        for ticker, name in MACRO_BENCHMARK_REGISTRY:
            try:
                bars = self.alpaca_gateway.get_stock_bars(ticker, limit=30)
                r_5d = compute_period_return(bars, 5)
                r_20d = compute_period_return(bars, 20)
                asset_performances.append(
                    MacroAssetPerformance(
                        asset_symbol=ticker,
                        asset_name=name,
                        price_change_5d_pct=r_5d,
                        price_change_20d_pct=r_20d,
                    )
                )
                asset_returns_map[ticker] = (r_5d, r_20d)
            except Exception as exc:
                logger.warning(f"Could not fetch macro bars for {ticker}: {exc}")
                asset_performances.append(
                    MacroAssetPerformance(
                        asset_symbol=ticker,
                        asset_name=name,
                        price_change_5d_pct=Decimal("0.0"),
                        price_change_20d_pct=Decimal("0.0"),
                    )
                )
                asset_returns_map[ticker] = (Decimal("0.0"), Decimal("0.0"))

        # 2. Compute Volatility Stress and Climate Score
        spy_bars = self.alpaca_gateway.get_stock_bars("SPY", limit=30)
        stress_level, vol_pct = compute_market_stress_level(spy_bars)

        _, spy_20d = asset_returns_map.get("SPY", (Decimal("0.0"), Decimal("0.0")))
        _, qqq_20d = asset_returns_map.get("QQQ", (Decimal("0.0"), Decimal("0.0")))
        _, tlt_20d = asset_returns_map.get("TLT", (Decimal("0.0"), Decimal("0.0")))

        climate_score = compute_macro_climate_score(spy_20d, qqq_20d, tlt_20d, stress_level)

        # 3. Fetch Macro / Fed News Context
        try:
            news_items = self.alpaca_gateway.get_news(symbol="SPY", limit=5)
            news_headlines = [
                f"- {item.get('headline', '')} ({item.get('source', 'Alpaca')})"
                for item in news_items
            ]
            news_context = (
                "\n".join(news_headlines) if news_headlines else "No recent macro headlines."
            )
        except Exception as exc:
            logger.warning(f"Could not fetch macro news: {exc}")
            news_context = "Macro news unavailable."

        # 4. DeepSeek LLM Synthesis
        assets_str = "\n".join(
            f"- {a.asset_symbol} ({a.asset_name}): 5d={a.price_change_5d_pct}%, "
            f"20d={a.price_change_20d_pct}%"
            for a in asset_performances
        )

        prompt = (
            "You are the Macroeconomic Intelligence Analyst for PRISM research.\n"
            f"Evaluate the broader macroeconomic environment and impact on: {sym}.\n\n"
            f"CROSS-ASSET BENCHMARK METRICS:\n{assets_str}\n\n"
            f"MACRO METRICS:\n"
            f"- Realized Volatility: {vol_pct}%\n"
            f"- Market Stress Level: {stress_level.value.upper()}\n"
            f"- Deterministic Macro Climate Score: {climate_score}/100\n\n"
            f"RECENT MACRO HEADLINES:\n{news_context}\n\n"
            "TASK:\n"
            "1. Select Macro Regime ('risk_on', 'risk_off', 'expansionary', 'contractionary', "
            "'stagflationary', 'transitional').\n"
            "2. Select Rate Environment ('rate_cut_cycle', 'pause_elevated', 'rising_rates').\n"
            "3. Provide 2-3 strictly macro-level tailwinds.\n"
            "4. Provide 2-3 strictly macro-level headwinds.\n"
            f"5. Analyze how {sym} specifically responds to this macro/rate environment.\n"
            "6. Provide a synthesis thesis."
        )

        llm_response = await self.llm_gateway.complete_structured(
            prompt=prompt,
            response_model=MacroAnalysisLLMOutput,
            system_prompt=SYSTEM_PROMPT,
            trace_id=trace_id,
        )

        if not llm_response.parsed:
            raise ValueError(
                "Failed to obtain valid parsed output from LLM gateway for macro analysis"
            )

        output: MacroAnalysisLLMOutput = llm_response.parsed
        now_utc = datetime.now(UTC)
        report_id = uuid4()

        report = MacroAnalysisReport(
            id=report_id,
            trace_id=trace_id,
            created_at=now_utc,
            symbol=sym,
            macro_regime=output.macro_regime,
            rate_environment=output.rate_environment,
            market_stress_level=stress_level,
            macro_climate_score=climate_score,
            assets=asset_performances,
            macro_tailwinds=output.macro_tailwinds,
            macro_headwinds=output.macro_headwinds,
            stock_macro_sensitivity=output.stock_macro_sensitivity,
            thesis=output.thesis,
        )

        # Cache in PostgreSQL
        if db_session is not None:
            try:
                db_record = MacroAnalysisModel(
                    id=str(report_id),
                    trace_id=str(trace_id),
                    created_at=now_utc,
                    schema_version="1.0",
                    symbol=sym,
                    macro_regime=output.macro_regime.value,
                    rate_environment=output.rate_environment.value,
                    market_stress_level=stress_level.value,
                    macro_climate_score=climate_score,
                    assets_json=json.dumps([a.model_dump(mode="json") for a in asset_performances]),
                    macro_tailwinds_json=json.dumps(output.macro_tailwinds),
                    macro_headwinds_json=json.dumps(output.macro_headwinds),
                    stock_macro_sensitivity=output.stock_macro_sensitivity,
                    thesis=output.thesis,
                    model_name=active_model,
                    raw_digest=llm_response.raw_digest,
                )
                db_session.add(db_record)
                await db_session.commit()
                logger.info(f"Persisted Macro Analysis for {sym} to database")
            except Exception as exc:
                logger.warning(f"Failed to cache Macro Analysis to database: {exc}")
                await db_session.rollback()

        return report
