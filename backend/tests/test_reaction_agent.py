from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.llm_gateway import LLMCompletionResult, LLMGateway
from app.market.alpaca_gateway import AlpacaPyGateway
from app.research.models import ResearchReportModel
from app.research.reaction_agent import (
    MarketReactionAgent,
    ReactionAnalysisLLMOutput,
    compute_reaction_metrics,
)


def test_compute_reaction_metrics_underreaction() -> None:
    # Pre-price: 100.0, Current-price: 101.0 -> actual: +1.0%
    # Expected: +4.0% -> gap: +3.0% (Underreaction)
    bars = [
        {"close": Decimal("100.0"), "volume": 1000},
        {"close": Decimal("100.5"), "volume": 1200},
        {"close": Decimal("101.0"), "volume": 2500},
    ]
    metrics = compute_reaction_metrics(bars, expected_reaction_pct=Decimal("4.0"))

    assert metrics["actual_reaction_pct"] == Decimal("1.0")
    assert metrics["expected_reaction_pct"] == Decimal("4.0")
    assert metrics["reaction_gap_pct"] == Decimal("3.0")
    assert metrics["classification"] == "UNDERREACTION"
    assert metrics["volume_ratio"] > Decimal("1.5")
    assert metrics["opportunity_score"] > Decimal("50.0")


def test_compute_reaction_metrics_overreaction() -> None:
    # Pre-price: 100.0, Current-price: 94.0 -> actual: -6.0%
    # Expected: -1.0% -> gap: -1 - (-6) = +5.0 or gap: -1 - (-6) = +5
    # When expected is -1 and actual is -6, gap = -1 - (-6) = +5.0
    # Wait, in the formula: gap = expected - actual = -1 - (-6) = +5.0
    # If expected is 1.0 and actual is 6.0 (bullish overreaction):
    # gap = 1.0 - 6.0 = -5.0
    bars = [
        {"close": Decimal("100.0"), "volume": 1000},
        {"close": Decimal("106.0"), "volume": 2000},
    ]
    metrics = compute_reaction_metrics(bars, expected_reaction_pct=Decimal("1.0"))

    assert metrics["actual_reaction_pct"] == Decimal("6.0")
    assert metrics["reaction_gap_pct"] == Decimal("-5.0")
    assert metrics["classification"] == "OVERREACTION"


def test_compute_reaction_metrics_fair_reaction() -> None:
    bars = [
        {"close": Decimal("100.0"), "volume": 1000},
        {"close": Decimal("102.0"), "volume": 1000},
    ]
    metrics = compute_reaction_metrics(bars, expected_reaction_pct=Decimal("2.2"))

    assert metrics["actual_reaction_pct"] == Decimal("2.0")
    assert metrics["reaction_gap_pct"] == Decimal("0.2")
    assert metrics["classification"] == "FAIR_REACTION"


def test_compute_reaction_metrics_empty_bars() -> None:
    metrics = compute_reaction_metrics([], expected_reaction_pct=Decimal("2.0"))
    assert metrics["actual_reaction_pct"] == Decimal("0.0")
    assert metrics["reaction_gap_pct"] == Decimal("0.0")
    assert metrics["classification"] == "FAIR_REACTION"


@pytest.mark.asyncio
async def test_alpaca_gateway_get_stock_bars_success() -> None:
    settings = Settings(
        _env_file=None,
        alpaca_api_key="key",
        alpaca_secret_key="secret",
    )

    mock_stock_client = MagicMock()
    mock_bar = MagicMock()
    mock_bar.timestamp = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    mock_bar.open = 200.0
    mock_bar.high = 205.0
    mock_bar.low = 199.0
    mock_bar.close = 204.0
    mock_bar.volume = 50000
    mock_bar.trade_count = 1200
    mock_bar.vwap = 203.5

    mock_response = MagicMock()
    mock_response.data = {"AAPL": [mock_bar]}
    mock_stock_client.get_stock_bars.return_value = mock_response

    with patch(
        "app.market.alpaca_gateway.StockHistoricalDataClient",
        return_value=mock_stock_client,
    ):
        gateway = AlpacaPyGateway(settings)
        bars = gateway.get_stock_bars("AAPL", limit=1)

        assert len(bars) == 1
        assert bars[0]["open"] == Decimal("200.0")
        assert bars[0]["close"] == Decimal("204.0")
        assert isinstance(bars[0]["open"], Decimal)
        assert bars[0]["volume"] == 50000
        mock_stock_client.get_stock_bars.assert_called_once()


@pytest.mark.asyncio
async def test_market_reaction_agent_analysis_and_caching() -> None:
    mock_llm_gateway = AsyncMock(spec=LLMGateway)
    mock_settings = Settings(
        _env_file=None,
        llm_provider="featherless",
        llm_model="DeepSeek-V4-Flash-0731",
    )
    mock_llm_gateway._settings = mock_settings

    parsed_output = ReactionAnalysisLLMOutput(
        thesis="Market has underreacted to Apple Q3 earnings beat with a 3% gap.",
        confidence=Decimal("0.85"),
        evidence_summaries=["Price rose only 1% despite 4% earnings catalyst value."],
        limitations=["Upcoming FOMC meeting could introduce broad market volatility."],
        classification="UNDERREACTION",
    )

    mock_completion = LLMCompletionResult(
        raw_content=json.dumps(
            {
                "thesis": "Market has underreacted to Apple Q3 earnings beat with a 3% gap.",
                "confidence": 0.85,
                "evidence_summaries": ["Price rose only 1% despite 4% earnings catalyst value."],
                "limitations": ["Upcoming FOMC meeting could introduce broad market volatility."],
                "classification": "UNDERREACTION",
            }
        ),
        parsed=parsed_output,
        raw_digest="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        model="DeepSeek-V4-Flash-0731",
        provider="featherless",
        prompt_tokens=150,
        completion_tokens=60,
        total_tokens=210,
        latency_ms=180,
        trace_id=uuid4(),
    )
    mock_llm_gateway.complete_structured.return_value = mock_completion

    agent = MarketReactionAgent(mock_llm_gateway)

    bars = [
        {"close": Decimal("100.0"), "volume": 1000},
        {"close": Decimal("101.0"), "volume": 2000},
    ]
    trace_id = uuid4()

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_scalar

    # First call: Cache miss -> calls LLM gateway
    report = await agent.analyze_reaction(
        symbol="AAPL",
        bars=bars,
        catalyst_summary="Apple beats Q3 EPS and revenue estimates.",
        expected_reaction_pct=Decimal("4.0"),
        trace_id=trace_id,
        db_session=mock_session,
        article_id="art-123",
    )

    assert report.symbol == "AAPL"
    assert report.confidence == Decimal("0.85")
    assert "underreacted" in report.thesis.lower()
    assert len(report.evidence) >= 2
    assert len(report.limitations) == 1
    mock_llm_gateway.complete_structured.assert_called_once()
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()

    # Reset mocks for cache hit test
    mock_llm_gateway.complete_structured.reset_mock()
    mock_session.add.reset_mock()
    mock_session.commit.reset_mock()

    cached_db_model = ResearchReportModel(
        id=str(report.id),
        trace_id=str(report.trace_id),
        created_at=report.created_at,
        schema_version=report.schema_version,
        symbol=report.symbol,
        article_id="art-123",
        thesis=report.thesis,
        confidence=report.confidence,
        freshness_seconds=report.freshness_seconds,
        evidence_json=json.dumps(
            [
                {
                    "source": e.source,
                    "summary": e.summary,
                    "observed_at": e.observed_at.isoformat(),
                    "received_at": e.received_at.isoformat(),
                }
                for e in report.evidence
            ]
        ),
        limitations_json=json.dumps(report.limitations),
        actual_reaction_pct=Decimal("1.0"),
        expected_reaction_pct=Decimal("4.0"),
        reaction_gap_pct=Decimal("3.0"),
        classification="UNDERREACTION",
        opportunity_score=Decimal("80.0"),
        model_name=mock_completion.model,
        raw_digest=mock_completion.raw_digest,
    )
    mock_scalar.scalar_one_or_none.return_value = cached_db_model

    # Second call: Cache hit -> bypasses LLM gateway
    cached_report = await agent.analyze_reaction(
        symbol="AAPL",
        bars=bars,
        catalyst_summary="Apple beats Q3 EPS and revenue estimates.",
        expected_reaction_pct=Decimal("4.0"),
        trace_id=trace_id,
        db_session=mock_session,
        article_id="art-123",
    )

    assert cached_report.symbol == "AAPL"
    assert cached_report.thesis == report.thesis
    mock_llm_gateway.complete_structured.assert_not_called()
    mock_session.add.assert_not_called()
