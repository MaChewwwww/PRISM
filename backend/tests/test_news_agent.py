from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.contracts.models import (
    CatalystMateriality,
    GuidanceChange,
    LLMEventAnalysis,
    NewsEventCategory,
)
from app.core.config import Settings
from app.core.llm_gateway import LLMCompletionResult, LLMGateway
from app.market.alpaca_gateway import AlpacaPyGateway
from app.research.decision_agent import calculate_news_sentiment_score
from app.research.models import LLMEventAnalysisModel
from app.research.news_agent import (
    NewsAnalysisLLMOutput,
    NewsIntelligenceAgent,
    clean_html_and_truncate,
    compute_event_age_seconds,
    compute_source_confidence,
)


def test_clean_html_and_truncate() -> None:
    # Test stripping tags
    html_text = "<p>Hello <b>World</b></p>"
    assert clean_html_and_truncate(html_text) == "Hello World"

    # Test whitespaces
    dirty_whitespace = "\nHello \t  World\n"
    assert clean_html_and_truncate(dirty_whitespace) == "Hello World"

    # Test truncation
    long_text = "A" * 2100
    truncated = clean_html_and_truncate(long_text, max_chars=10)
    assert len(truncated) == 13  # 10 'A's + "..."
    assert truncated.endswith("...")


def test_compute_source_confidence() -> None:
    assert compute_source_confidence("sec") == Decimal("100.0")
    assert compute_source_confidence("Reuters Wire") == Decimal("95.0")
    assert compute_source_confidence("Bloomberg") == Decimal("95.0")
    assert compute_source_confidence("PR Newswire") == Decimal("95.0")
    assert compute_source_confidence("Benzinga News") == Decimal("80.0")
    assert compute_source_confidence("SeekingAlpha") == Decimal("65.0")
    assert compute_source_confidence("Random Blog") == Decimal("50.0")
    assert compute_source_confidence(None) == Decimal("50.0")


def test_compute_event_age_seconds() -> None:
    now = datetime(2026, 8, 30, 12, 0, 0, tzinfo=UTC)
    published_1h_ago = now - timedelta(hours=1)
    assert compute_event_age_seconds(published_1h_ago, now=now) == 3600

    iso_str = "2026-08-30T11:30:00Z"
    assert compute_event_age_seconds(iso_str, now=now) == 1800

    assert compute_event_age_seconds(None, now=now) == 0
    assert compute_event_age_seconds("invalid-date", now=now) == 0


@pytest.mark.asyncio
async def test_alpaca_gateway_get_news_success() -> None:
    settings = Settings(
        _env_file=None,
        alpaca_api_key="key",
        alpaca_secret_key="secret",
    )

    mock_news_client = MagicMock()
    mock_article = MagicMock()
    mock_article.id = 12345
    mock_article.headline = "Earnings Beat"
    mock_article.source = "benzinga"
    mock_article.url = "http://example.com"
    mock_article.summary = "Beat expectations"
    mock_article.content = "<p>Full details</p>"
    mock_article.symbols = ["AAPL"]
    mock_article.created_at = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)

    mock_response = MagicMock()
    mock_response.data = {"AAPL": [mock_article]}
    mock_news_client.get_news.return_value = mock_response

    with patch("app.market.alpaca_gateway.NewsClient", return_value=mock_news_client):
        gateway = AlpacaPyGateway(settings)
        news = gateway.get_news("AAPL", limit=1)

        assert len(news) == 1
        assert news[0]["id"] == "12345"
        assert news[0]["headline"] == "Earnings Beat"
        assert news[0]["summary"] == "Beat expectations"
        assert news[0]["content"] == "<p>Full details</p>"
        assert news[0]["symbols"] == ["AAPL"]
        mock_news_client.get_news.assert_called_once()


@pytest.mark.asyncio
async def test_alpaca_gateway_get_news_retry_exponential() -> None:
    settings = Settings(
        _env_file=None,
        alpaca_api_key="key",
        alpaca_secret_key="secret",
    )

    mock_news_client = MagicMock()
    mock_article = MagicMock()
    mock_article.id = 123
    mock_article.headline = "Retry Success"
    mock_article.source = "benzinga"
    mock_article.url = None
    mock_article.summary = ""
    mock_article.content = ""
    mock_article.symbols = ["TSLA"]
    mock_article.created_at = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)

    mock_response = MagicMock()
    mock_response.data = {"TSLA": [mock_article]}

    mock_news_client.get_news.side_effect = [
        TimeoutError("provider timeout"),
        ConnectionError("provider connection reset"),
        mock_response,
    ]

    with (
        patch("app.market.alpaca_gateway.NewsClient", return_value=mock_news_client),
        patch("time.sleep") as mock_sleep,
    ):
        gateway = AlpacaPyGateway(settings)
        news = gateway.get_news("TSLA", limit=1)

        assert len(news) == 1
        assert news[0]["id"] == "123"
        assert mock_news_client.get_news.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)


@pytest.mark.asyncio
async def test_news_intelligence_agent_analysis_and_caching() -> None:
    mock_llm_gateway = AsyncMock(spec=LLMGateway)
    mock_settings = Settings(
        _env_file=None,
        llm_provider="featherless",
        llm_model="DeepSeek-V4-Flash-0731",
    )
    mock_llm_gateway._settings = mock_settings

    parsed_output = NewsAnalysisLLMOutput(
        event_category=NewsEventCategory.EARNINGS,
        catalyst_materiality=CatalystMateriality.HIGH,
        sentiment="bullish",
        significance_score=Decimal("85.0"),
        expected_reaction_pct=Decimal("2.5"),
        guidance_change=GuidanceChange.RAISED,
        eps_surprise_pct=Decimal("4.2"),
        revenue_surprise_pct=Decimal("2.1"),
        quarter="Q3 2026",
        has_contradictory_signals=False,
        contradiction_notes=None,
        rationale="Strong Q3 earnings report beating consensus with raised guidance.",
    )
    mock_completion = LLMCompletionResult(
        raw_content=json.dumps(
            {
                "event_category": "earnings",
                "catalyst_materiality": "high",
                "sentiment": "bullish",
                "significance_score": 85.0,
                "expected_reaction_pct": 2.5,
                "guidance_change": "raised",
                "eps_surprise_pct": 4.2,
                "revenue_surprise_pct": 2.1,
                "quarter": "Q3 2026",
                "has_contradictory_signals": False,
                "contradiction_notes": None,
                "rationale": "Strong Q3 earnings report beating consensus with raised guidance.",
            }
        ),
        parsed=parsed_output,
        raw_digest="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        model="DeepSeek-V4-Flash-0731",
        provider="featherless",
        prompt_tokens=100,
        completion_tokens=40,
        total_tokens=140,
        latency_ms=120,
        trace_id=uuid4(),
    )
    mock_llm_gateway.complete_structured.return_value = mock_completion

    agent = NewsIntelligenceAgent(mock_llm_gateway)

    article = {
        "id": "benzinga-9999",
        "headline": "Apple Beats Q3 Expectations with Raised Guidance",
        "source": "benzinga",
        "created_at": datetime.now(UTC) - timedelta(minutes=30),
        "summary": "Apple posted record earnings today.",
        "content": "<p>Apple Inc beats revenue estimates and raised full year guidance...</p>",
    }
    trace_id = uuid4()

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_scalar

    analysis = await agent.analyze_article(
        article=article,
        symbol="AAPL",
        trace_id=trace_id,
        db_session=mock_session,
    )

    assert analysis.article_id == "benzinga-9999"
    assert analysis.event_category == NewsEventCategory.EARNINGS
    assert analysis.event_type == "earnings"
    assert analysis.catalyst_materiality == CatalystMateriality.HIGH
    assert analysis.guidance_change == GuidanceChange.RAISED
    assert analysis.earnings_surprise is not None
    assert analysis.earnings_surprise.eps_surprise_pct == Decimal("4.2")
    assert analysis.earnings_surprise.revenue_surprise_pct == Decimal("2.1")
    assert analysis.earnings_surprise.quarter == "Q3 2026"
    assert analysis.source == "benzinga"
    assert analysis.source_confidence == Decimal("80.0")
    assert analysis.event_age_seconds >= 1700
    assert analysis.sentiment == "bullish"
    assert analysis.significance_score == Decimal("85.0")
    assert analysis.expected_reaction_pct == Decimal("2.5")
    mock_llm_gateway.complete_structured.assert_called_once()
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()

    mock_llm_gateway.complete_structured.reset_mock()
    mock_session.add.reset_mock()
    mock_session.commit.reset_mock()

    cached_db_model = LLMEventAnalysisModel(
        id=str(analysis.id),
        trace_id=str(analysis.trace_id),
        created_at=analysis.created_at,
        schema_version=analysis.schema_version,
        article_id=analysis.article_id,
        symbol=analysis.symbol,
        headline=analysis.headline,
        source=analysis.source,
        source_confidence=Decimal(str(analysis.source_confidence)),
        event_age_seconds=analysis.event_age_seconds,
        event_category=analysis.event_category.value,
        event_type=analysis.event_type,
        catalyst_materiality=analysis.catalyst_materiality.value,
        sentiment=analysis.sentiment,
        significance_score=Decimal(str(analysis.significance_score)),
        expected_reaction_pct=Decimal(str(analysis.expected_reaction_pct)),
        guidance_change=analysis.guidance_change.value,
        earnings_surprise_json=json.dumps(
            {
                "eps_surprise_pct": "4.2",
                "revenue_surprise_pct": "2.1",
                "quarter": "Q3 2026",
            }
        ),
        has_contradictory_signals=False,
        contradiction_notes=None,
        rationale=analysis.rationale,
        model_name=analysis.model_name,
        prompt_version=analysis.prompt_version,
        raw_digest=analysis.raw_digest,
    )
    mock_scalar.scalar_one_or_none.return_value = cached_db_model

    cached_analysis = await agent.analyze_article(
        article=article,
        symbol="AAPL",
        trace_id=trace_id,
        db_session=mock_session,
    )

    assert cached_analysis.article_id == "benzinga-9999"
    assert cached_analysis.event_category == NewsEventCategory.EARNINGS
    assert cached_analysis.catalyst_materiality == CatalystMateriality.HIGH
    assert cached_analysis.guidance_change == GuidanceChange.RAISED
    assert cached_analysis.earnings_surprise is not None
    assert cached_analysis.earnings_surprise.eps_surprise_pct == Decimal("4.2")
    assert (
        cached_analysis.raw_digest
        == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    )
    mock_llm_gateway.complete_structured.assert_not_called()
    mock_session.add.assert_not_called()


def test_calculate_news_sentiment_score_weighting() -> None:
    trace_id = uuid4()
    raw_digest = "a" * 64

    # High materiality, high confidence bullish event
    ev1 = LLMEventAnalysis(
        trace_id=trace_id,
        article_id="art1",
        symbol="NVDA",
        headline="NVDA Record Earnings",
        source="reuters",
        source_confidence=Decimal("95.0"),
        event_category=NewsEventCategory.EARNINGS,
        catalyst_materiality=CatalystMateriality.HIGH,
        sentiment="bullish",
        significance_score=Decimal("90.0"),
        guidance_change=GuidanceChange.RAISED,
        rationale="Record earnings",
        model_name="test-model",
        prompt_version="2.0",
        raw_digest=raw_digest,
    )

    # Noise materiality, low confidence bearish blog
    ev2 = LLMEventAnalysis(
        trace_id=trace_id,
        article_id="art2",
        symbol="NVDA",
        headline="Minor opinion blog doubt",
        source="unknown_blog",
        source_confidence=Decimal("30.0"),
        event_category=NewsEventCategory.ROUTINE_PR,
        catalyst_materiality=CatalystMateriality.NOISE,
        sentiment="bearish",
        significance_score=Decimal("20.0"),
        rationale="Speculative doubt",
        model_name="test-model",
        prompt_version="2.0",
        raw_digest=raw_digest,
    )

    score = calculate_news_sentiment_score([ev1, ev2])
    # The high-materiality, high-confidence bullish event should dominate over noise
    assert score > Decimal("75.0")
