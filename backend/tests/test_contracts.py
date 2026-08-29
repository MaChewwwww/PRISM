from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.contracts import (
    HistoricalBar,
    HistoricalMarketDataRecord,
    LLMEventAnalysis,
    MarketDataType,
    ReactionClassification,
    ResearchReport,
    TimeFrameKind,
)


def test_frs_025_nfrs_019_historical_bar_validation() -> None:
    now = datetime.now(UTC)
    bar = HistoricalBar(
        timestamp=now,
        open=Decimal("150.25"),
        high=Decimal("152.00"),
        low=Decimal("149.80"),
        close=Decimal("151.50"),
        volume=125000,
        trade_count=3200,
        vwap=Decimal("151.10"),
    )
    assert bar.volume == 125000
    assert bar.open == Decimal("150.25")
    assert bar.close == Decimal("151.50")

    # Reject naive timestamps
    with pytest.raises(ValidationError):
        HistoricalBar(
            timestamp=datetime(2024, 1, 1, 10, 0, 0),
            open=Decimal("100"),
            high=Decimal("105"),
            low=Decimal("99"),
            close=Decimal("102"),
            volume=1000,
        )


def test_frs_025_nfrs_019_historical_market_data_record() -> None:
    trace_id = uuid4()
    start_time = datetime(2024, 1, 1, 9, 30, 0, tzinfo=UTC)
    end_time = datetime(2024, 1, 1, 16, 0, 0, tzinfo=UTC)
    raw_query = "AAPL:bars:1Min:2024-01-01T09:30:00Z:2024-01-01T16:00:00Z"
    query_digest = hashlib.sha256(raw_query.encode("utf-8")).hexdigest()

    record = HistoricalMarketDataRecord(
        trace_id=trace_id,
        symbol="AAPL",
        data_type=MarketDataType.BARS,
        timeframe=TimeFrameKind.MIN_1,
        start_time=start_time,
        end_time=end_time,
        query_digest=query_digest,
        source="alpaca_sip",
        item_count=390,
        payload={"bars": []},
        is_immutable=True,
    )
    assert record.symbol == "AAPL"
    assert record.is_immutable is True
    assert record.data_type == MarketDataType.BARS
    assert len(record.query_digest) == 64

    # Invalid digest format fails closed
    with pytest.raises(ValidationError):
        HistoricalMarketDataRecord(
            trace_id=trace_id,
            symbol="AAPL",
            data_type=MarketDataType.BARS,
            timeframe=TimeFrameKind.MIN_1,
            start_time=start_time,
            end_time=end_time,
            query_digest="invalid-digest",
            source="alpaca_sip",
            item_count=390,
            payload={},
        )


def test_frs_025_nfrs_019_llm_event_analysis() -> None:
    trace_id = uuid4()
    raw_text = "NVDA reports Q4 revenue beating expectations by 15%."
    raw_digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    analysis = LLMEventAnalysis(
        trace_id=trace_id,
        article_id="news_article_998811",
        symbol="NVDA",
        headline="NVDA Q4 Earnings Blowout",
        event_type="earnings",
        sentiment="bullish",
        significance_score=Decimal("94.5"),
        expected_reaction_pct=Decimal("0.0525"),
        rationale="Strong data center demand and forward guidance increase.",
        model_name="claude-3-5-sonnet",
        prompt_version="1.2.0",
        raw_digest=raw_digest,
    )
    assert analysis.significance_score == Decimal("94.5")
    assert analysis.sentiment == "bullish"
    assert analysis.event_type == "earnings"

    # Out of range significance score fails
    with pytest.raises(ValidationError):
        LLMEventAnalysis(
            trace_id=trace_id,
            article_id="news_1",
            symbol="NVDA",
            headline="Headline",
            event_type="earnings",
            sentiment="bullish",
            significance_score=Decimal("150.0"),  # max is 100
            rationale="Rationale",
            model_name="claude",
            prompt_version="1.0",
            raw_digest=raw_digest,
        )


def test_frg_02_market_reaction_research_report_metrics_are_decimal_safe() -> None:
    report = ResearchReport(
        trace_id=uuid4(),
        symbol="AAPL",
        thesis="Observed reaction is below the catalyst expectation.",
        confidence=Decimal("0.85"),
        freshness_seconds=12,
        evidence=[],
        actual_reaction_pct=Decimal("1.25"),
        expected_reaction_pct=Decimal("4.00"),
        reaction_gap_pct=Decimal("2.75"),
        volume_ratio=Decimal("1.80"),
        classification=ReactionClassification.UNDERREACTION,
        opportunity_score=Decimal("82.5"),
    )

    payload = report.model_dump(mode="json")
    assert payload["actual_reaction_pct"] == "1.25"
    assert payload["reaction_gap_pct"] == "2.75"
    assert payload["volume_ratio"] == "1.80"
    assert payload["opportunity_score"] == "82.5"
    assert payload["classification"] == "UNDERREACTION"

    with pytest.raises(ValidationError):
        ResearchReport(
            trace_id=uuid4(),
            symbol="AAPL",
            thesis="Invalid score",
            confidence=Decimal("0.5"),
            freshness_seconds=0,
            evidence=[],
            opportunity_score=Decimal("100.1"),
        )


def test_frs_027_exit_policy_validation() -> None:
    from app.contracts import ExitPolicy

    policy = ExitPolicy()
    assert policy.take_profit_pct == Decimal("75.0")
    assert policy.stop_loss_pct == Decimal("50.0")
    assert policy.dte_threshold == 7
    assert policy.max_hold_days == 14

    custom_policy = ExitPolicy(
        take_profit_pct=Decimal("85.0"),
        stop_loss_pct=Decimal("50.0"),
        dte_threshold=5,
        max_hold_days=10,
    )
    assert custom_policy.take_profit_pct == Decimal("85.0")
    assert custom_policy.stop_loss_pct == Decimal("50.0")
    assert custom_policy.dte_threshold == 5
    assert custom_policy.max_hold_days == 10

    # Values outside the BA-authorized bounds fail.
    with pytest.raises(ValidationError):
        ExitPolicy(take_profit_pct=Decimal("74.9"))
    with pytest.raises(ValidationError):
        ExitPolicy(stop_loss_pct=Decimal("49.9"))

    # DTE threshold below the authorized two-day floor fails.
    with pytest.raises(ValidationError):
        ExitPolicy(dte_threshold=1)


def test_frs_028_shadow_candidate_validation() -> None:
    from app.contracts import (
        OptionLeg,
        OptionSide,
        OptionStrategy,
        OptionType,
        ShadowCandidate,
        StrategyKind,
    )

    # Test cash baseline candidate (strategy is None)
    cash_candidate = ShadowCandidate(
        label="no_action_cash",
        strategy=None,
        allocation_multiplier=Decimal("1.0"),
        rationale="Hold 100% cash baseline",
    )
    assert cash_candidate.label == "no_action_cash"
    assert cash_candidate.strategy is None
    assert cash_candidate.allocation_multiplier == Decimal("1.0")

    # Test conservative half-size candidate
    half_candidate = ShadowCandidate(
        label="conservative_half_size",
        strategy=OptionStrategy(
            kind=StrategyKind.LONG_CALL,
            legs=[
                OptionLeg(
                    underlying="NVDA",
                    symbol="NVDA241115C00130000",
                    side=OptionSide.BUY,
                    ratio_qty=1,
                    strike_price=Decimal("130.0"),
                    expiration="2024-11-15",
                    option_type=OptionType.CALL,
                )
            ],
            limit_price=Decimal("4.50"),
        ),
        allocation_multiplier=Decimal("0.5"),
        rationale="Take half size to reduce risk",
    )
    assert half_candidate.label == "conservative_half_size"
    assert half_candidate.allocation_multiplier == Decimal("0.5")
    assert half_candidate.strategy is not None

    # Invalid non-positive multiplier fails
    with pytest.raises(ValidationError):
        ShadowCandidate(
            label="invalid",
            allocation_multiplier=Decimal("0.0"),
        )
