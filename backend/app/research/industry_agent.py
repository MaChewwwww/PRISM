from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.models import (
    CompetitiveMoat,
    IndustryAnalysisReport,
    IndustrySentiment,
    PeerPerformance,
    PeerReactionDynamics,
    RelativePerformance,
    SectorRegimeConfirmation,
)
from app.core.llm_gateway import LLMGateway
from app.market.alpaca_gateway import AlpacaPyGateway
from app.research.models import IndustryAnalysisModel

logger = logging.getLogger(__name__)

# Specialized Sub-Industry ETF and Comprehensive Peer Registry
DEFAULT_SECTOR_REGISTRY: dict[str, tuple[str, str, list[str]]] = {
    # Ticker: (Sub-Industry Name, Specialized ETF, Relevant Direct Competitors)
    "TSLA": (
        "Automotive & Clean Mobility",
        "DRIV",
        ["RIVN", "F", "GM", "TM"],
    ),
    "NVDA": (
        "Semiconductors & AI Compute",
        "SMH",
        ["AMD", "AVGO", "INTC", "TSM"],
    ),
    "AMD": (
        "Semiconductors & Computing",
        "SMH",
        ["NVDA", "INTC", "QCOM"],
    ),
    "AVGO": (
        "Semiconductors & Infrastructure",
        "SMH",
        ["NVDA", "QCOM", "MRVL"],
    ),
    "AAPL": (
        "Consumer Hardware & Platforms",
        "XLK",
        ["MSFT", "GOOGL", "DELL"],
    ),
    "MSFT": (
        "Enterprise Cloud & Software",
        "IGV",
        ["ORCL", "CRM", "NOW", "GOOGL"],
    ),
    "GOOGL": (
        "Digital Advertising & AI Services",
        "XLC",
        ["META", "SNAP", "PINS", "MSFT"],
    ),
    "META": (
        "Social Platforms & Digital Media",
        "XLC",
        ["GOOGL", "SNAP", "PINS"],
    ),
    "AMZN": (
        "E-Commerce & Cloud Infrastructure",
        "XLY",
        ["WMT", "MSFT", "BABA"],
    ),
    "JPM": (
        "Diversified & Commercial Banking",
        "KBWB",
        ["BAC", "WFC", "C", "GS"],
    ),
    "BAC": (
        "Commercial & Retail Banking",
        "KBWB",
        ["JPM", "WFC", "C"],
    ),
    "GS": (
        "Investment Banking & Capital Markets",
        "XLF",
        ["MS", "JPM", "C"],
    ),
    "LLY": (
        "Biopharmaceuticals & Therapeutics",
        "XBI",
        ["NVO", "JNJ", "PFE", "ABBV"],
    ),
    "XOM": (
        "Integrated Oil & Energy Exploration",
        "XLE",
        ["CVX", "COP", "SLB"],
    ),
}
DEFAULT_FALLBACK: tuple[str, str, list[str]] = ("Broad Market Equities", "SPY", ["QQQ", "IWM"])

SYSTEM_PROMPT = (
    "You are an expert equity research sector and industry analyst for PRISM.\n"
    "STRICT AGENT SCOPE BOUNDARIES:\n"
    "1. Focus EXCLUSIVELY on industry dynamics, supply/demand, and competitive share.\n"
    "2. DO NOT include company financial statements, balance sheets, or earnings metrics.\n"
    "3. DO NOT include broad macroeconomic monetary policy or Fed rate commentary.\n"
    "4. Clearly distinguish between sector-wide forces vs. company-specific performance.\n"
    "Output strictly valid JSON matching the schema."
)


class IndustryAnalysisLLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    competitive_moat: CompetitiveMoat = Field(
        ...,
        description="Assessment of competitive moat ('wide', 'narrow', 'none', 'deteriorating')",
    )
    overall_sentiment: IndustrySentiment = Field(
        ...,
        description="Overall industry-level sentiment towards the company",
    )
    tailwinds: list[str] = Field(
        default_factory=list,
        description="Top 2-3 strictly industry-level tailwinds (e.g. EV adoption, infrastructure)",
    )
    headwinds: list[str] = Field(
        default_factory=list,
        description="Top 2-3 strictly industry-level headwinds (e.g. price wars, inventory glut)",
    )
    thesis: str = Field(
        ...,
        description="Synthesis thesis explaining whether industry forces favor the stock vs peers",
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


def compute_sector_health_score(
    sector_5d: Decimal,
    sector_20d: Decimal,
    peer_returns_20d: list[Decimal],
) -> Decimal:
    """Deterministically compute Sector Health Score (0-100) from sector trend and peer breadth."""
    # Factor 1: Sector ETF 20-day return (40 pts max, centered at 20 pts for 0%)
    # -10% -> 0 pts, 0% -> 20 pts, +10% -> 40 pts
    sec_20d_norm = min(
        Decimal("1.0"),
        max(Decimal("0.0"), Decimal("0.5") + (sector_20d / Decimal("20.0"))),
    )
    score_sec_20d = sec_20d_norm * Decimal("40.0")

    # Factor 2: Sector ETF 5-day return (20 pts max, centered at 10 pts for 0%)
    # -5% -> 0 pts, 0% -> 10 pts, +5% -> 20 pts
    sec_5d_norm = min(
        Decimal("1.0"),
        max(Decimal("0.0"), Decimal("0.5") + (sector_5d / Decimal("10.0"))),
    )
    score_sec_5d = sec_5d_norm * Decimal("20.0")

    # Factor 3: Peer Breadth (40 pts max) - percentage of peers with positive 20d return
    if peer_returns_20d:
        pos_peers = sum(1 for r in peer_returns_20d if r > Decimal("0.0"))
        breadth_ratio = Decimal(str(pos_peers)) / Decimal(str(len(peer_returns_20d)))
        score_breadth = breadth_ratio * Decimal("40.0")
    else:
        score_breadth = Decimal("20.0")

    total_score = score_sec_20d + score_sec_5d + score_breadth
    return min(Decimal("100.0"), max(Decimal("0.0"), round(total_score, 1)))


def classify_relative_performance(alpha: Decimal) -> RelativePerformance:
    """Classify relative performance against a benchmark."""
    if alpha >= Decimal("2.0"):
        return RelativePerformance.OUTPERFORMING
    if alpha <= Decimal("-2.0"):
        return RelativePerformance.UNDERPERFORMING
    return RelativePerformance.INLINE


def classify_peer_relative_performance(
    stock_return_20d: Decimal, peer_returns_20d: list[Decimal]
) -> RelativePerformance:
    """Classify performance relative to the peer group."""
    if not peer_returns_20d:
        return RelativePerformance.MIXED
    beats = sum(1 for p in peer_returns_20d if stock_return_20d > p)
    ratio = beats / len(peer_returns_20d)
    if ratio >= 0.7:
        return RelativePerformance.OUTPERFORMING
    if ratio <= 0.3:
        return RelativePerformance.UNDERPERFORMING
    return RelativePerformance.MIXED


def compute_peer_dispersion(peer_returns_20d: list[Decimal]) -> Decimal:
    """Compute sample standard deviation of peer returns to measure cross-sectional dispersion."""
    if len(peer_returns_20d) < 2:
        return Decimal("0.0")

    n = Decimal(str(len(peer_returns_20d)))
    mean_val = sum(peer_returns_20d) / n
    variance = sum((r - mean_val) ** 2 for r in peer_returns_20d) / (n - Decimal("1.0"))
    std_dev = Decimal(str(round(float(variance) ** 0.5, 2)))
    return std_dev


def compute_sector_regime_confirmation(
    stock_20d: Decimal,
    sector_20d: Decimal,
    spy_20d: Decimal,
) -> SectorRegimeConfirmation:
    """Deterministically classify market vs. sector vs. stock multi-tier relative structure."""
    # 1. Leading Sector Outperformer: Stock beating sector, and sector beating broad SPY
    if stock_20d >= sector_20d and sector_20d >= spy_20d and stock_20d > Decimal("0.0"):
        return SectorRegimeConfirmation.LEADING_SECTOR_OUTPERFORMER

    # 2. Idiosyncratic Decoupling: Stock beating SPY while sector is lagging SPY
    if stock_20d > spy_20d and sector_20d < spy_20d:
        return SectorRegimeConfirmation.IDIOSYNCRATIC_DECOUPLING

    # 3. Lagging in Bull Sector: Sector is strong relative to SPY, but stock is trailing its sector
    if sector_20d > (spy_20d + Decimal("2.0")) and stock_20d < (sector_20d - Decimal("2.0")):
        return SectorRegimeConfirmation.LAGGING_IN_BULL_SECTOR

    # 4. Sector Under Pressure: Sector is noticeably underperforming SPY, pulling down stock
    if sector_20d < (spy_20d - Decimal("2.0")) and stock_20d < (spy_20d - Decimal("1.0")):
        return SectorRegimeConfirmation.SECTOR_UNDER_PRESSURE

    # 5. Default Broad Beta Convergence
    return SectorRegimeConfirmation.BROAD_BETA_CONVERGENCE


def compute_peer_reaction_dynamics(
    stock_5d: Decimal,
    peer_returns_5d: list[Decimal],
) -> PeerReactionDynamics:
    """Classify 5-day event reaction dynamics between target stock and its peer group."""
    if not peer_returns_5d:
        return PeerReactionDynamics.ISOLATED_REACTION

    avg_peer_5d = sum(peer_returns_5d) / Decimal(str(len(peer_returns_5d)))

    # Stock positive, peer group average negative -> Divergent winner
    if stock_5d >= Decimal("1.5") and avg_peer_5d <= Decimal("-0.5"):
        return PeerReactionDynamics.DIVERGENT_WINNER

    # Stock positive and peers strongly positive -> Sympathetic sector surge
    if stock_5d >= Decimal("1.5") and avg_peer_5d >= Decimal("1.5"):
        return PeerReactionDynamics.SYMPATHETIC_SECTOR_SURGE

    # Stock negative and peers negative -> Peer dragged down
    if stock_5d <= Decimal("-1.5") and avg_peer_5d <= Decimal("-1.5"):
        return PeerReactionDynamics.PEER_DRAGGED_DOWN

    return PeerReactionDynamics.ISOLATED_REACTION


class IndustryIntelligenceAgent:
    """Agent #3: Evaluates the stock against its specialized sector ETF and direct competitors."""

    def __init__(self, llm_gateway: LLMGateway, alpaca_gateway: AlpacaPyGateway) -> None:
        self.llm_gateway = llm_gateway
        self.alpaca_gateway = alpaca_gateway

    async def analyze_industry(
        self,
        symbol: str,
        trace_id: UUID,
        custom_peers: list[str] | None = None,
        db_session: AsyncSession | None = None,
        *,
        strict: bool = False,
        evaluation_at: datetime | None = None,
    ) -> IndustryAnalysisReport:
        sym = symbol.strip().upper()
        sector_name, sector_etf, default_peers = DEFAULT_SECTOR_REGISTRY.get(sym, DEFAULT_FALLBACK)
        peer_symbols = custom_peers if custom_peers else default_peers
        active_model = self.llm_gateway._settings.llm_model or "default"

        # Check DB cache
        if db_session is not None and not strict:
            try:
                stmt = (
                    select(IndustryAnalysisModel)
                    .where(
                        IndustryAnalysisModel.symbol == sym,
                        IndustryAnalysisModel.sector_etf == sector_etf,
                        IndustryAnalysisModel.model_name == active_model,
                    )
                    .order_by(IndustryAnalysisModel.created_at.desc())
                    .limit(1)
                )
                result = await db_session.execute(stmt)
                cached = result.scalar_one_or_none()
                if cached is not None:
                    logger.info(f"Returning cached Industry Analysis for {sym}")
                    peers_data = [
                        PeerPerformance.model_validate(p) for p in json.loads(cached.peers_json)
                    ]
                    sec_regime_raw = getattr(cached, "sector_regime_confirmation", None)
                    sec_regime_val = sec_regime_raw if sec_regime_raw else "broad_beta_convergence"
                    peer_react_raw = getattr(cached, "peer_reaction_dynamics", None)
                    peer_react_val = peer_react_raw if peer_react_raw else "isolated_reaction"

                    spy_5d_val = getattr(cached, "spy_return_5d_pct", None) or Decimal("0.0")
                    spy_20d_val = getattr(cached, "spy_return_20d_pct", None) or Decimal("0.0")
                    stock_vs_spy_val = getattr(
                        cached, "stock_vs_spy_alpha_20d_pct", None
                    ) or Decimal("0.0")
                    peer_disp_val = getattr(cached, "peer_dispersion_20d_pct", None) or Decimal(
                        "0.0"
                    )

                    return IndustryAnalysisReport(
                        id=UUID(cached.id),
                        trace_id=UUID(cached.trace_id),
                        created_at=cached.created_at,
                        symbol=cached.symbol,
                        sector_name=cached.sector_name,
                        sector_etf=cached.sector_etf,
                        sector_health_score=cached.sector_health_score,
                        stock_return_5d_pct=cached.stock_return_5d_pct,
                        stock_return_20d_pct=cached.stock_return_20d_pct,
                        sector_return_5d_pct=cached.sector_return_5d_pct,
                        sector_return_20d_pct=cached.sector_return_20d_pct,
                        spy_return_5d_pct=spy_5d_val,
                        spy_return_20d_pct=spy_20d_val,
                        relative_alpha_5d_pct=cached.relative_alpha_5d_pct,
                        relative_alpha_20d_pct=cached.relative_alpha_20d_pct,
                        stock_vs_spy_alpha_20d_pct=stock_vs_spy_val,
                        peer_dispersion_20d_pct=peer_disp_val,
                        sector_relative_performance=RelativePerformance(
                            cached.sector_relative_performance
                        ),
                        peer_relative_performance=RelativePerformance(
                            cached.peer_relative_performance
                        ),
                        sector_regime_confirmation=SectorRegimeConfirmation(sec_regime_val),
                        peer_reaction_dynamics=PeerReactionDynamics(peer_react_val),
                        peers=peers_data,
                        competitive_moat=CompetitiveMoat(cached.competitive_moat),
                        overall_sentiment=IndustrySentiment(cached.overall_sentiment),
                        tailwinds=json.loads(cached.tailwinds_json),
                        headwinds=json.loads(cached.headwinds_json),
                        thesis=cached.thesis,
                    )

            except Exception as exc:
                logger.warning("Error checking industry cache: %s", type(exc).__name__)

        # 1. Fetch independent market evidence concurrently. The strict path
        # still rejects missing coverage before the LLM is invoked.
        stock_bars, sector_bars, spy_bars = await asyncio.gather(
            asyncio.to_thread(self.alpaca_gateway.get_stock_bars, sym, limit=30),
            asyncio.to_thread(self.alpaca_gateway.get_stock_bars, sector_etf, limit=30),
            asyncio.to_thread(self.alpaca_gateway.get_stock_bars, "SPY", limit=30),
        )
        if strict and (len(stock_bars) < 20 or len(sector_bars) < 20 or len(spy_bars) < 20):
            raise ValueError("Industry evidence coverage is insufficient")

        stock_5d = compute_period_return(stock_bars, 5)
        stock_20d = compute_period_return(stock_bars, 20)
        sector_5d = compute_period_return(sector_bars, 5)
        sector_20d = compute_period_return(sector_bars, 20)
        spy_5d = compute_period_return(spy_bars, 5)
        spy_20d = compute_period_return(spy_bars, 20)

        rel_alpha_5d = round(stock_5d - sector_5d, 2)
        rel_alpha_20d = round(stock_20d - sector_20d, 2)
        stock_vs_spy_alpha_20d = round(stock_20d - spy_20d, 2)

        # Compute peer returns concurrently, while retaining deterministic
        # strict-mode rejection for every required peer observation.
        async def _fetch_peer_performance(peer: str) -> tuple[PeerPerformance, Decimal, Decimal]:
            p_sym = peer.strip().upper()
            try:
                p_bars = await asyncio.to_thread(
                    self.alpaca_gateway.get_stock_bars, p_sym, limit=30
                )
                if strict and len(p_bars) < 20:
                    raise ValueError("Peer evidence coverage is insufficient")
                p_5d = compute_period_return(p_bars, 5)
                p_20d = compute_period_return(p_bars, 20)
                return (
                    PeerPerformance(
                        symbol=p_sym,
                        price_change_5d_pct=p_5d,
                        price_change_20d_pct=p_20d,
                    ),
                    p_5d,
                    p_20d,
                )
            except Exception as exc:
                if strict:
                    raise ValueError("Peer evidence is unavailable") from exc
                logger.warning("Could not fetch peer bars for %s: %s", p_sym, type(exc).__name__)
                return (
                    PeerPerformance(
                        symbol=p_sym,
                        price_change_5d_pct=Decimal("0.0"),
                        price_change_20d_pct=Decimal("0.0"),
                    ),
                    Decimal("0.0"),
                    Decimal("0.0"),
                )

        peer_results = await asyncio.gather(
            *[_fetch_peer_performance(peer) for peer in peer_symbols]
        )
        peer_performances = [result[0] for result in peer_results]
        peer_5d_list = [result[1] for result in peer_results]
        peer_20d_list = [result[2] for result in peer_results]

        # 2. Deterministic Health Score, Dispersion, & Performance Classifications
        sector_health_score = compute_sector_health_score(sector_5d, sector_20d, peer_20d_list)
        sector_rel_perf = classify_relative_performance(rel_alpha_20d)
        peer_rel_perf = classify_peer_relative_performance(stock_20d, peer_20d_list)
        peer_dispersion_20d = compute_peer_dispersion(peer_20d_list)
        sector_regime = compute_sector_regime_confirmation(stock_20d, sector_20d, spy_20d)
        peer_reaction = compute_peer_reaction_dynamics(stock_5d, peer_5d_list)

        # 3. Fetch Recent Industry News Context
        try:
            news_items = self.alpaca_gateway.get_news(symbol=sym, limit=5)
            news_headlines = [
                f"- {item.get('headline', '')} ({item.get('source', 'Alpaca')})"
                for item in news_items
            ]
            news_context = (
                "\n".join(news_headlines) if news_headlines else "No recent sector news articles."
            )
        except Exception as exc:
            logger.warning("Could not fetch industry news: %s", type(exc).__name__)
            news_context = "Sector news unavailable."

        # 4. LLM DeepSeek Synthesis
        peers_str = ", ".join(
            f"{p.symbol} (5d: {p.price_change_5d_pct}%, 20d: {p.price_change_20d_pct}%)"
            for p in peer_performances
        )

        prompt = (
            "You are the Industry Intelligence Analyst for PRISM institutional research.\n"
            f"Evaluate industry and competitive dynamics for target stock: {sym}.\n\n"
            f"INDUSTRY & BENCHMARK DATA:\n"
            f"- Sub-Industry: {sector_name}\n"
            f"- Benchmark ETF: {sector_etf}\n"
            f"- Grounded Sector Health Score: {sector_health_score}/100\n"
            f"- Stock Return (5d / 20d): {stock_5d}% / {stock_20d}%\n"
            f"- Sector ETF Return (5d / 20d): {sector_5d}% / {sector_20d}%\n"
            f"- Broad Market SPY Return (5d / 20d): {spy_5d}% / {spy_20d}%\n"
            f"- Relative Alpha vs Sector (20d): {rel_alpha_20d}% ({sector_rel_perf.value})\n"
            f"- Stock vs SPY Alpha (20d): {stock_vs_spy_alpha_20d}%\n"
            f"- Sector Regime Confirmation: {sector_regime.value}\n"
            f"- Peer Dispersion (20d std dev): {peer_dispersion_20d}%\n"
            f"- Event Peer Dynamics (5d): {peer_reaction.value}\n"
            f"- Peer Comparison (20d): {peer_rel_perf.value} across peers: {peers_str}\n\n"
            f"RECENT INDUSTRY HEADLINES:\n{news_context}\n\n"
            "TASK:\n"
            "1. Assess Competitive Moat ('wide', 'narrow', 'none', 'deteriorating').\n"
            "2. Set Overall Sentiment ('positive', 'moderately_positive', 'mixed', "
            "'moderately_negative', 'negative').\n"
            "3. List 2-3 strictly industry tailwinds (e.g. adoption, infrastructure).\n"
            "4. List 2-3 strictly industry headwinds (e.g. price wars, inventory).\n"
            "5. Provide thesis distinguishing broad sector health vs company alpha."
        )

        llm_response = await self.llm_gateway.complete_structured(
            prompt=prompt,
            response_model=IndustryAnalysisLLMOutput,
            system_prompt=SYSTEM_PROMPT,
            trace_id=trace_id,
        )

        if not llm_response.parsed:
            raise ValueError("Failed to obtain valid parsed output from LLM gateway")

        analysis_output: IndustryAnalysisLLMOutput = llm_response.parsed
        now_utc = (evaluation_at or datetime.now(UTC)).astimezone(UTC)
        report_id = uuid4()

        report = IndustryAnalysisReport(
            id=report_id,
            trace_id=trace_id,
            created_at=now_utc,
            symbol=sym,
            sector_name=sector_name,
            sector_etf=sector_etf,
            sector_health_score=sector_health_score,
            stock_return_5d_pct=stock_5d,
            stock_return_20d_pct=stock_20d,
            sector_return_5d_pct=sector_5d,
            sector_return_20d_pct=sector_20d,
            spy_return_5d_pct=spy_5d,
            spy_return_20d_pct=spy_20d,
            relative_alpha_5d_pct=rel_alpha_5d,
            relative_alpha_20d_pct=rel_alpha_20d,
            stock_vs_spy_alpha_20d_pct=stock_vs_spy_alpha_20d,
            peer_dispersion_20d_pct=peer_dispersion_20d,
            sector_relative_performance=sector_rel_perf,
            peer_relative_performance=peer_rel_perf,
            sector_regime_confirmation=sector_regime,
            peer_reaction_dynamics=peer_reaction,
            peers=peer_performances,
            competitive_moat=analysis_output.competitive_moat,
            overall_sentiment=analysis_output.overall_sentiment,
            tailwinds=analysis_output.tailwinds,
            headwinds=analysis_output.headwinds,
            thesis=analysis_output.thesis,
        )

        # Cache in PostgreSQL
        if db_session is not None:
            try:
                db_record = IndustryAnalysisModel(
                    id=str(report_id),
                    trace_id=str(trace_id),
                    created_at=now_utc,
                    schema_version="1.0",
                    symbol=sym,
                    sector_name=sector_name,
                    sector_etf=sector_etf,
                    stock_return_5d_pct=stock_5d,
                    stock_return_20d_pct=stock_20d,
                    sector_return_5d_pct=sector_5d,
                    sector_return_20d_pct=sector_20d,
                    spy_return_5d_pct=spy_5d,
                    spy_return_20d_pct=spy_20d,
                    relative_alpha_5d_pct=rel_alpha_5d,
                    relative_alpha_20d_pct=rel_alpha_20d,
                    stock_vs_spy_alpha_20d_pct=stock_vs_spy_alpha_20d,
                    peer_dispersion_20d_pct=peer_dispersion_20d,
                    sector_relative_performance=sector_rel_perf.value,
                    peer_relative_performance=peer_rel_perf.value,
                    sector_regime_confirmation=sector_regime.value,
                    peer_reaction_dynamics=peer_reaction.value,
                    peers_json=json.dumps([p.model_dump(mode="json") for p in peer_performances]),
                    sector_health_score=sector_health_score,
                    competitive_moat=analysis_output.competitive_moat.value,
                    overall_sentiment=analysis_output.overall_sentiment.value,
                    tailwinds_json=json.dumps(analysis_output.tailwinds),
                    headwinds_json=json.dumps(analysis_output.headwinds),
                    thesis=analysis_output.thesis,
                    model_name=active_model,
                    raw_digest=llm_response.raw_digest,
                )
                db_session.add(db_record)
                await db_session.commit()
                logger.info(f"Persisted Industry Analysis for {sym} to database")
            except Exception as exc:
                logger.warning("Failed to cache Industry Analysis: %s", type(exc).__name__)
                await db_session.rollback()
                if strict:
                    raise RuntimeError("Industry research persistence failed") from exc

        return report
