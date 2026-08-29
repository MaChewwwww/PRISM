from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.contracts.models import (
    CompetitiveMoat,
    IndustryAnalysisReport,
    IndustrySentiment,
    RelativePerformance,
)
from app.core.llm_gateway import LLMCompletionResult
from app.research.industry_agent import (
    IndustryAnalysisLLMOutput,
    IndustryIntelligenceAgent,
    classify_peer_relative_performance,
    classify_relative_performance,
    compute_period_return,
    compute_sector_health_score,
)
from app.research.models import IndustryAnalysisModel


def test_compute_period_return() -> None:
    # 10 bars from 100 to 110 (+10%)
    bars = [{"close": Decimal(str(100 + i))} for i in range(10)]
    assert compute_period_return(bars, 5) == Decimal("4.81")  # (109 - 104) / 104 * 100 = 4.81%
    assert compute_period_return([], 5) == Decimal("0.0")
    assert compute_period_return([{"close": Decimal("100.0")}], 5) == Decimal("0.0")


def test_compute_sector_health_score_and_classifications() -> None:
    # Bullish sector & positive breadth
    score = compute_sector_health_score(
        sector_5d=Decimal("3.0"),
        sector_20d=Decimal("8.0"),
        peer_returns_20d=[Decimal("5.0"), Decimal("2.0"), Decimal("-1.0")],
    )
    assert score > Decimal("60.0")

    # Classifications
    assert classify_relative_performance(Decimal("3.5")) == RelativePerformance.OUTPERFORMING
    assert classify_relative_performance(Decimal("-3.5")) == RelativePerformance.UNDERPERFORMING
    assert classify_relative_performance(Decimal("0.5")) == RelativePerformance.INLINE

    assert (
        classify_peer_relative_performance(Decimal("10.0"), [Decimal("2.0"), Decimal("3.0")])
        == RelativePerformance.OUTPERFORMING
    )


@pytest.mark.asyncio
async def test_industry_intelligence_agent_analyze() -> None:
    mock_alpaca = MagicMock()
    mock_alpaca.get_stock_bars.side_effect = lambda sym, limit=30: [
        {"close": Decimal("100.0")},
        {"close": Decimal("102.0")},
        {"close": Decimal("105.0")},
        {"close": Decimal("108.0")},
        {"close": Decimal("110.0")},
        {"close": Decimal("110.0")},
    ]
    mock_alpaca.get_news.return_value = []

    mock_llm = MagicMock()
    mock_llm.model_name = "deepseek-ai/DeepSeek-V3"
    llm_output = IndustryAnalysisLLMOutput(
        competitive_moat=CompetitiveMoat.WIDE,
        overall_sentiment=IndustrySentiment.POSITIVE,
        tailwinds=["AI compute demand", "CUDA software lock-in"],
        headwinds=["Packaging bottlenecks at TSMC", "Export restrictions"],
        thesis="Nvidia maintains an industry-leading position with strong relative alpha.",
    )
    mock_llm.complete_structured = AsyncMock(
        return_value=LLMCompletionResult(
            raw_content="{}",
            parsed=llm_output,
            raw_digest="a" * 64,
            model="deepseek-ai/DeepSeek-V3",
            provider="featherless",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            latency_ms=120,
            trace_id=uuid4(),
        )
    )

    agent = IndustryIntelligenceAgent(llm_gateway=mock_llm, alpaca_gateway=mock_alpaca)
    trace_id = uuid4()

    report: IndustryAnalysisReport = await agent.analyze_industry(
        symbol="NVDA",
        trace_id=trace_id,
        db_session=None,
    )

    assert report.symbol == "NVDA"
    assert report.sector_name == "Semiconductors & AI Compute"
    assert report.sector_etf == "SMH"
    assert report.sector_health_score >= Decimal("0.0")
    assert report.competitive_moat == CompetitiveMoat.WIDE
    assert report.overall_sentiment == IndustrySentiment.POSITIVE
    assert len(report.peers) >= 2
    assert len(report.tailwinds) == 2
    assert len(report.headwinds) == 2
    assert "Nvidia" in report.thesis


@pytest.mark.asyncio
async def test_industry_intelligence_agent_db_cache_hit_and_miss() -> None:
    mock_alpaca = MagicMock()
    mock_alpaca.get_stock_bars.return_value = [
        {"close": Decimal("100.0")},
        {"close": Decimal("105.0")},
    ]
    mock_alpaca.get_news.return_value = []

    mock_llm = MagicMock()
    mock_llm.model_name = "deepseek-ai/DeepSeek-V3"
    llm_output = IndustryAnalysisLLMOutput(
        competitive_moat=CompetitiveMoat.WIDE,
        overall_sentiment=IndustrySentiment.MODERATELY_POSITIVE,
        tailwinds=["Enterprise cloud adoption"],
        headwinds=["Regulatory scrutiny"],
        thesis="Strong enterprise software momentum.",
    )
    mock_llm.complete_structured = AsyncMock(
        return_value=LLMCompletionResult(
            raw_content="{}",
            parsed=llm_output,
            raw_digest="b" * 64,
            model="deepseek-ai/DeepSeek-V3",
            provider="featherless",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            latency_ms=120,
            trace_id=uuid4(),
        )
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_scalar

    agent = IndustryIntelligenceAgent(llm_gateway=mock_llm, alpaca_gateway=mock_alpaca)
    trace_id = uuid4()

    # 1. First call: Cache miss -> calls LLM and adds to DB
    report = await agent.analyze_industry(
        symbol="MSFT",
        trace_id=trace_id,
        db_session=mock_session,
    )
    assert report.symbol == "MSFT"
    mock_llm.complete_structured.assert_called_once()
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()

    # 2. Second call: Cache hit -> returns cached without LLM call
    mock_llm.complete_structured.reset_mock()
    sample_peers = [{"symbol": "ORCL", "price_change_5d_pct": "4.0", "price_change_20d_pct": "8.0"}]
    cached_record = IndustryAnalysisModel(
        id=str(report.id),
        trace_id=str(report.trace_id),
        created_at=datetime.now(UTC),
        schema_version="1.0",
        symbol="MSFT",
        sector_name="Enterprise Cloud & Software",
        sector_etf="IGV",
        stock_return_5d_pct=Decimal("5.0"),
        stock_return_20d_pct=Decimal("10.0"),
        sector_return_5d_pct=Decimal("3.0"),
        sector_return_20d_pct=Decimal("7.0"),
        relative_alpha_5d_pct=Decimal("2.0"),
        relative_alpha_20d_pct=Decimal("3.0"),
        sector_relative_performance="outperforming",
        peer_relative_performance="outperforming",
        peers_json=json.dumps(sample_peers),
        sector_health_score=Decimal("90.0"),
        competitive_moat="wide",
        overall_sentiment="moderately_positive",
        tailwinds_json=json.dumps(["Enterprise cloud adoption"]),
        headwinds_json=json.dumps(["Regulatory scrutiny"]),
        thesis="Cached thesis.",
        model_name="deepseek-ai/DeepSeek-V3",
        raw_digest="b" * 64,
    )
    mock_scalar.scalar_one_or_none.return_value = cached_record

    cached_report = await agent.analyze_industry(
        symbol="MSFT",
        trace_id=trace_id,
        db_session=mock_session,
    )
    assert cached_report.symbol == "MSFT"
    assert cached_report.thesis == "Cached thesis."
    mock_llm.complete_structured.assert_not_called()
