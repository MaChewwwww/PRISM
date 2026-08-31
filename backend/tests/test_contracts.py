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
    assert analysis.event_category.value == "other"
    assert analysis.source_confidence == Decimal("50.0")

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


def test_news_event_analysis_enriched_fields() -> None:
    from app.contracts import (
        CatalystMateriality,
        EarningsSurpriseData,
        GuidanceChange,
        NewsEventCategory,
    )

    trace_id = uuid4()
    raw_digest = "b" * 64

    analysis = LLMEventAnalysis(
        trace_id=trace_id,
        article_id="news_enriched_1",
        symbol="MSFT",
        headline="Microsoft Q4 Cloud Revenue Surges, Guidance Raised",
        source="reuters",
        source_confidence=Decimal("95.0"),
        event_age_seconds=120,
        event_category=NewsEventCategory.EARNINGS,
        catalyst_materiality=CatalystMateriality.HIGH,
        sentiment="bullish",
        significance_score=Decimal("92.0"),
        expected_reaction_pct=Decimal("3.5"),
        guidance_change=GuidanceChange.RAISED,
        earnings_surprise=EarningsSurpriseData(
            eps_surprise_pct=Decimal("5.0"),
            revenue_surprise_pct=Decimal("2.5"),
            quarter="Q4 2026",
        ),
        has_contradictory_signals=False,
        rationale="Strong cloud growth and guidance beat.",
        model_name="claude-3-5-sonnet",
        prompt_version="2.0",
        raw_digest=raw_digest,
    )

    assert analysis.event_category == NewsEventCategory.EARNINGS
    assert analysis.catalyst_materiality == CatalystMateriality.HIGH
    assert analysis.guidance_change == GuidanceChange.RAISED
    assert analysis.earnings_surprise is not None
    assert analysis.earnings_surprise.eps_surprise_pct == Decimal("5.0")
    assert analysis.source_confidence == Decimal("95.0")
    assert analysis.event_age_seconds == 120


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


def test_quantitative_analysis_report_enriched_fields() -> None:
    from app.contracts.models import (
        BollingerBands,
        MACDCrossover,
        MACDSignal,
        MovingAverages,
        PriceDisplacement,
        QuantitativeAnalysisReport,
        RSICondition,
        TrendConfirmation,
        TrendDirection,
    )

    report = QuantitativeAnalysisReport(
        trace_id=uuid4(),
        symbol="TSLA",
        current_price=Decimal("250.00"),
        trend=TrendDirection.BULLISH,
        trend_confirmation=TrendConfirmation.STRONG_UPTREND_CONFIRMED,
        momentum_score=Decimal("82.5"),
        rsi_14=Decimal("65.2"),
        rsi_condition=RSICondition.NEUTRAL,
        macd=MACDSignal(
            macd=Decimal("3.5"),
            signal=Decimal("2.8"),
            histogram=Decimal("0.7"),
            crossover=MACDCrossover.NONE,
        ),
        moving_averages=MovingAverages(
            sma_20=Decimal("240.0"),
            sma_50=Decimal("230.0"),
            sma_200=Decimal("210.0"),
        ),
        bollinger_bands=BollingerBands(
            upper=Decimal("260.0"),
            middle=Decimal("245.0"),
            lower=Decimal("230.0"),
            bandwidth_pct=Decimal("12.24"),
            percent_b=Decimal("0.67"),
        ),
        atr_14=Decimal("8.50"),
        volatility_annualized_pct=Decimal("35.20"),
        volume_surge_ratio=Decimal("1.85"),
        price_displacement=PriceDisplacement(
            gap_size_pct=Decimal("3.20"),
            displacement_1d_pct=Decimal("4.50"),
            displacement_3d_pct=Decimal("8.10"),
            displacement_5d_pct=Decimal("12.40"),
            displacement_20d_pct=Decimal("22.50"),
        ),
        summary="Strong uptrend confirmed with 3.2% gap and +12.4% 5d displacement.",
    )

    payload = report.model_dump(mode="json")
    assert payload["trend_confirmation"] == "strong_uptrend_confirmed"
    assert payload["price_displacement"]["gap_size_pct"] == "3.20"
    assert payload["price_displacement"]["displacement_5d_pct"] == "12.40"


def test_fundamental_analysis_report_enriched_fields() -> None:
    from app.contracts.models import (
        AltmanZone,
        BalanceSheetRedFlag,
        EarningsSurpriseEvent,
        EstimateRevisionTrend,
        FundamentalAnalysisReport,
        FundamentalHealth,
        GuidanceChange,
        ProfitabilityMetrics,
        SolvencyMetrics,
        ValuationMetrics,
        ValuationStance,
    )

    report = FundamentalAnalysisReport(
        trace_id=uuid4(),
        symbol="NVDA",
        current_price=Decimal("125.00"),
        market_cap_millions=Decimal("3000000.0"),
        enterprise_value_millions=Decimal("2980000.0"),
        profitability=ProfitabilityMetrics(
            gross_margin_pct=Decimal("75.0"),
            operating_margin_pct=Decimal("62.0"),
            net_margin_pct=Decimal("55.0"),
            roe_pct=Decimal("85.0"),
            roa_pct=Decimal("45.0"),
        ),
        solvency=SolvencyMetrics(
            current_ratio=Decimal("3.5"),
            debt_to_equity=Decimal("0.14"),
            interest_coverage_ratio=Decimal("300.0"),
            net_debt_millions=Decimal("-24000.0"),
        ),
        valuation=ValuationMetrics(
            pe_ratio_ttm=Decimal("42.5"),
            ev_to_ebitda=Decimal("35.0"),
            price_to_book=Decimal("38.0"),
            fcf_yield_pct=Decimal("2.4"),
            free_cash_flow_millions=Decimal("63500.0"),
        ),
        piotroski_f_score=8,
        altman_z_score=Decimal("18.5"),
        altman_zone=AltmanZone.SAFE,
        composite_quality_score=Decimal("94.5"),
        fundamental_health=FundamentalHealth.EXCELLENT,
        valuation_stance=ValuationStance.PREMIUM,
        earnings_event=EarningsSurpriseEvent(
            quarter="Q2 2026",
            eps_actual=Decimal("0.68"),
            eps_consensus=Decimal("0.64"),
            eps_surprise_pct=Decimal("6.25"),
            revenue_actual_millions=Decimal("30040.0"),
            revenue_consensus_millions=Decimal("28700.0"),
            revenue_surprise_pct=Decimal("4.67"),
            guidance_change=GuidanceChange.RAISED,
            gross_margin_surprise_bps=Decimal("120.0"),
            operating_margin_surprise_bps=Decimal("150.0"),
            estimate_revision_trend=EstimateRevisionTrend.UPWARD,
        ),
        red_flags=[BalanceSheetRedFlag.NONE_DETECTED],
        summary="Elite fundamentals with Q2 2026 guidance raise and 6.25% EPS beat.",
    )

    payload = report.model_dump(mode="json")
    assert payload["earnings_event"]["quarter"] == "Q2 2026"
    assert payload["earnings_event"]["guidance_change"] == "raised"
    assert payload["earnings_event"]["eps_surprise_pct"] == "6.25"
    assert payload["red_flags"] == ["none_detected"]


def test_industry_analysis_report_enriched_fields() -> None:
    from app.contracts.models import (
        CompetitiveMoat,
        IndustryAnalysisReport,
        IndustrySentiment,
        PeerPerformance,
        PeerReactionDynamics,
        RelativePerformance,
        SectorRegimeConfirmation,
    )

    report = IndustryAnalysisReport(
        trace_id=uuid4(),
        symbol="NVDA",
        sector_name="Semiconductors & AI Compute",
        sector_etf="SMH",
        sector_health_score=Decimal("88.5"),
        stock_return_5d_pct=Decimal("4.5"),
        stock_return_20d_pct=Decimal("14.2"),
        sector_return_5d_pct=Decimal("2.1"),
        sector_return_20d_pct=Decimal("8.5"),
        spy_return_5d_pct=Decimal("0.8"),
        spy_return_20d_pct=Decimal("3.2"),
        relative_alpha_5d_pct=Decimal("2.4"),
        relative_alpha_20d_pct=Decimal("5.7"),
        stock_vs_spy_alpha_20d_pct=Decimal("11.0"),
        peer_dispersion_20d_pct=Decimal("6.3"),
        sector_relative_performance=RelativePerformance.OUTPERFORMING,
        peer_relative_performance=RelativePerformance.OUTPERFORMING,
        sector_regime_confirmation=SectorRegimeConfirmation.LEADING_SECTOR_OUTPERFORMER,
        peer_reaction_dynamics=PeerReactionDynamics.DIVERGENT_WINNER,
        peers=[
            PeerPerformance(
                symbol="AMD",
                price_change_5d_pct=Decimal("-1.2"),
                price_change_20d_pct=Decimal("3.5"),
            )
        ],
        competitive_moat=CompetitiveMoat.WIDE,
        overall_sentiment=IndustrySentiment.POSITIVE,
        tailwinds=["Accelerating data center Blackwell ramp"],
        headwinds=["CoWoS advanced packaging capacity bottlenecks"],
        thesis="Leading sector outperformer with wide moat and high peer alpha.",
    )

    payload = report.model_dump(mode="json")
    assert payload["sector_regime_confirmation"] == "leading_sector_outperformer"
    assert payload["peer_reaction_dynamics"] == "divergent_winner"
    assert payload["stock_vs_spy_alpha_20d_pct"] == "11.0"
    assert payload["peer_dispersion_20d_pct"] == "6.3"


def test_macro_analysis_report_enriched_fields() -> None:
    from app.contracts.models import (
        AssetMacroImpact,
        EconomicEventProximity,
        MacroAnalysisReport,
        MacroAssetPerformance,
        MacroRegime,
        MarketStressDirection,
        MarketStressLevel,
        RateEnvironment,
    )

    report = MacroAnalysisReport(
        trace_id=uuid4(),
        symbol="NVDA",
        macro_regime=MacroRegime.RISK_ON,
        rate_environment=RateEnvironment.RATE_CUT_CYCLE,
        market_stress_level=MarketStressLevel.LOW,
        market_stress_direction=MarketStressDirection.EASING,
        realized_volatility_pct=Decimal("12.4"),
        volatility_change_5d_pct=Decimal("-2.5"),
        macro_climate_score=Decimal("84.5"),
        economic_event_proximity=EconomicEventProximity.FOMC_DECISION_NEAR,
        asset_macro_impact=AssetMacroImpact.STRONG_TAILWIND,
        assets=[
            MacroAssetPerformance(
                asset_symbol="SPY",
                asset_name="S&P 500 Broad Market Index",
                price_change_5d_pct=Decimal("1.2"),
                price_change_20d_pct=Decimal("4.5"),
            ),
            MacroAssetPerformance(
                asset_symbol="TLT",
                asset_name="20+ Year US Treasury Bond ETF",
                price_change_5d_pct=Decimal("0.8"),
                price_change_20d_pct=Decimal("2.1"),
            ),
        ],
        macro_tailwinds=["Federal Reserve rate cut cycle begins"],
        macro_headwinds=["Tariff uncertainty"],
        stock_macro_sensitivity="Growth duration asset with strong rate sensitivity.",
        thesis="Constructive macro backdrop with easing volatility.",
    )

    payload = report.model_dump(mode="json")
    assert payload["market_stress_direction"] == "easing"
    assert payload["economic_event_proximity"] == "fomc_decision_near"
    assert payload["asset_macro_impact"] == "strong_tailwind"
    assert payload["realized_volatility_pct"] == "12.4"


def test_research_report_enriched_fields() -> None:
    from app.contracts.models import (
        CatalystDecayStatus,
        EvidenceItem,
        ReactionClassification,
        ResearchReport,
    )

    now = datetime.now(UTC)
    report = ResearchReport(
        trace_id=uuid4(),
        symbol="AAPL",
        thesis="Significant underreaction to AI hardware supercycle catalyst.",
        confidence=Decimal("0.88"),
        freshness_seconds=120,
        evidence=[
            EvidenceItem(
                source="alpaca_market_data",
                summary="Price +1.0% vs expected +4.0%",
                observed_at=now,
                received_at=now,
            )
        ],
        actual_reaction_pct=Decimal("1.0"),
        expected_reaction_pct=Decimal("4.0"),
        reaction_gap_pct=Decimal("3.0"),
        direction_adjusted_gap_pct=Decimal("3.0"),
        volume_ratio=Decimal("2.1"),
        classification=ReactionClassification.UNDERREACTION,
        opportunity_score=Decimal("84.5"),
        historical_median_reaction_pct=Decimal("4.5"),
        historical_dispersion_pct=Decimal("3.2"),
        analog_count=16,
        analog_similarity_score=Decimal("80.0"),
        historical_volatility_pct=Decimal("24.0"),
        implied_volatility_pct=Decimal("30.0"),
        iv_hv_ratio=Decimal("1.25"),
        options_implied_move_pct=Decimal("3.2"),
        event_age_hours=Decimal("2.5"),
        catalyst_decay_factor=Decimal("0.93"),
        catalyst_decay_status=CatalystDecayStatus.FRESH_CATALYST,
    )

    payload = report.model_dump(mode="json")
    assert payload["direction_adjusted_gap_pct"] == "3.0"
    assert payload["historical_median_reaction_pct"] == "4.5"
    assert payload["analog_count"] == 16
    assert payload["catalyst_decay_status"] == "fresh_catalyst"
    assert payload["iv_hv_ratio"] == "1.25"


def test_trade_decision_report_enriched_fields() -> None:
    from app.contracts.models import (
        ExitPolicy,
        OptionStructure,
        SpecialistScores,
        TradeDecisionReport,
        TradeDirection,
        TradeVerdict,
    )

    report = TradeDecisionReport(
        trace_id=uuid4(),
        symbol="AAPL",
        verdict=TradeVerdict.PROCEED_TO_OPTIONS_PROPOSAL,
        direction=TradeDirection.BULLISH,
        recommended_structure=OptionStructure.BULL_CALL_SPREAD,
        composite_opportunity_score=Decimal("86.5"),
        net_ev_r=Decimal("0.42"),
        reward_risk_ratio=Decimal("2.10"),
        confidence_score=Decimal("88.0"),
        current_price=Decimal("225.50"),
        target_price=Decimal("240.00"),
        exit_policy=ExitPolicy(
            take_profit_pct=Decimal("75.0"),
            stop_loss_pct=Decimal("50.0"),
            dte_threshold=7,
            max_hold_days=14,
        ),
        specialist_scores=SpecialistScores(
            reaction_opportunity_score=Decimal("85.0"),
            quant_momentum_score=Decimal("88.0"),
            fundamental_quality_score=Decimal("92.0"),
            sector_health_score=Decimal("80.0"),
            macro_climate_score=Decimal("78.0"),
            news_sentiment_score=Decimal("85.0"),
        ),
        evidence_summary=[
            "Quant momentum score is 88/100 with RSI confirming continuation",
            "Market reaction shows underreaction with +3.0% direction-adjusted gap",
            "Macro rate-cut cycle provides duration asset tailwind",
        ],
        contradictions=["Quant 5-day displacement is elevated relative to 20-day baseline"],
        contradiction_analysis=(
            "Short-term quantitative stretch is outweighed by robust fundamentals."
        ),
        portfolio_fit="Consumer Tech sector allocation has capacity; beta is 1.05x.",
        options_only_constraint_acknowledged=True,
        synthesis_rationale=(
            "Multi-agent alignment across fundamental quality, momentum, and reaction gap."
        ),
        key_risks=["Broader tech sector volatility", "Upcoming economic data release"],
    )

    payload = report.model_dump(mode="json")
    assert payload["verdict"] == "proceed_to_options_proposal"
    assert payload["direction"] == "bullish"
    assert payload["recommended_structure"] == "bull_call_spread"
    assert len(payload["evidence_summary"]) == 3
    assert len(payload["contradictions"]) == 1
    assert payload["options_only_constraint_acknowledged"] is True
    assert "Consumer Tech" in payload["portfolio_fit"]
