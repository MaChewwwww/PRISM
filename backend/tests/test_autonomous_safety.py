from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.autonomous.audit import build_evaluation_root
from app.autonomous.models import AutonomousCycleModel
from app.autonomous.worker import AutonomousWorker, CandidateResearchOutcome
from app.contracts.models import (
    OptionLeg,
    OptionSide,
    OptionStrategy,
    OptionType,
    RiskAssessment,
    StrategyKind,
    TradeProposal,
    TradeVerdict,
)
from app.core.config import Settings
from app.market.option_selection import select_option_strategy
from app.rules.evaluator import authorize_proposal
from app.rules.registry import ProfileParameters


def _proposal() -> TradeProposal:
    return TradeProposal(
        trace_id=uuid4(),
        research_report_id=uuid4(),
        symbol="NVDA",
        strategy=OptionStrategy(
            kind="long_call",
            legs=[
                OptionLeg(
                    symbol="NVDA270101C00100000",
                    underlying="NVDA",
                    expiration="2027-01-01",
                    option_type=OptionType.CALL,
                    side=OptionSide.BUY,
                    strike_price=Decimal("100"),
                    position_intent="buy_to_open",
                )
            ],
            limit_price=Decimal("1.00"),
        ),
        quantity=1,
        rationale="test",
        proposal_digest="a" * 64,
    )


def test_option_selection_rejects_stale_quotes() -> None:
    now = datetime(2026, 8, 30, 13, 30, tzinfo=UTC)
    contracts = [
        {
            "symbol": "NVDA270910C00100000",
            "underlying": "NVDA",
            "expiration": "2026-09-10",
            "strike": "100",
            "option_type": "call",
            "active": True,
            "tradable": True,
        }
    ]
    quotes = {
        contracts[0]["symbol"]: {
            "bid": "1.00",
            "ask": "1.02",
            "quote_timestamp": now - timedelta(seconds=31),
        }
    }
    try:
        select_option_strategy(
            contracts,
            quotes,
            underlying_price=Decimal("100"),
            direction="bullish",
            structure="long",
            now=now,
        )
    except ValueError as exc:
        assert "No fresh" in str(exc)
        assert "quote_stale=1" in str(exc)
    else:
        raise AssertionError("stale quote must not produce a strategy")


def test_option_selection_accepts_quotes_during_cycle() -> None:
    now = datetime(2026, 8, 30, 13, 30, tzinfo=UTC)
    contracts = [
        {
            "symbol": "NVDA270910C00100000",
            "underlying": "NVDA",
            "expiration": "2026-09-10",
            "strike": "100",
            "option_type": "call",
            "active": True,
            "tradable": True,
        }
    ]
    quotes = {
        contracts[0]["symbol"]: {
            "bid": "1.00",
            "ask": "1.02",
            "quote_timestamp": now + timedelta(seconds=15),
        }
    }
    strategy = select_option_strategy(
        contracts,
        quotes,
        underlying_price=Decimal("100"),
        direction="bullish",
        structure="long",
        now=now,
    )
    assert strategy.legs[0].symbol == "NVDA270910C00100000"


def test_option_selection_debit_spread_fallback_to_long_leg() -> None:
    now = datetime(2026, 8, 30, 13, 30, tzinfo=UTC)
    contracts = [
        {
            "symbol": "MSFT270910C00500000",
            "underlying": "MSFT",
            "expiration": "2026-09-10",
            "strike": "500",
            "option_type": "call",
            "active": True,
            "tradable": True,
        }
    ]
    quotes = {
        contracts[0]["symbol"]: {
            "bid": "2.00",
            "ask": "2.10",
            "quote_timestamp": now + timedelta(seconds=5),
        }
    }
    # When debit_spread is requested but only 1 strike is available,
    # it gracefully falls back to long single leg.
    strategy = select_option_strategy(
        contracts,
        quotes,
        underlying_price=Decimal("500"),
        direction="bullish",
        structure="debit_spread",
        now=now,
    )
    assert strategy.kind == StrategyKind.LONG_CALL
    assert len(strategy.legs) == 1
    assert strategy.legs[0].symbol == "MSFT270910C00500000"


def test_authorization_rejects_missing_evidence_and_preserves_rule_trace() -> None:
    proposal = _proposal()
    risk = RiskAssessment(
        trace_id=proposal.trace_id,
        proposal_id=proposal.id,
        verdict="acceptable",
        max_loss=Decimal("1"),
        findings=[],
        data_fresh=True,
    )
    settings = Settings(
        _env_file=None,
        execution_enabled=True,
        execution_kill_switch=False,
        active_ruleset_version="1.0.0",
    )
    decision = authorize_proposal(proposal, risk, settings, inputs={})
    assert decision.outcome == "REJECT"
    assert [rule.priority for rule in decision.rule_trace] == ["P0", "P1", "P2", "P3", "P4", "P5"]
    assert decision.allowed_order_payload is None


def test_evaluation_root_is_immutable_and_lineage_bound() -> None:
    trace_id = uuid4()
    first = build_evaluation_root(
        trace_id=trace_id,
        outcome="NO_TRADE",
        evidence={"analog_count": 0},
    )
    second = build_evaluation_root(
        trace_id=trace_id,
        outcome="NO_TRADE",
        evidence={"analog_count": 1},
    )
    assert first.is_immutable is True
    assert first.root_digest != second.root_digest


def test_balanced_profile_threshold_is_78() -> None:
    proposal = _proposal()
    risk = RiskAssessment(
        trace_id=proposal.trace_id,
        proposal_id=proposal.id,
        verdict="acceptable",
        max_loss=Decimal("1"),
        findings=[],
        data_fresh=True,
    )
    settings = Settings(
        _env_file=None,
        execution_enabled=True,
        execution_kill_switch=False,
        active_ruleset_version="1.0.0",
    )
    inputs = {
        "market_fresh": True,
        "analog_count": 30,
        "fundamentals_sourced": True,
        "account_verified": True,
        "open_positions": 0,
        "buying_power_ok": True,
        "cash_buffer_ok": True,
        "concentration_ok": True,
        "position_size_ok": True,
        "aggregate_risk_ok": True,
        "portfolio_controls_complete": True,
        "sector_concentration_ok": True,
        "cluster_concentration_ok": True,
        "greeks_risk_ok": True,
        "expiration_concentration_ok": True,
        "market_open": True,
        "iv_rank_available": True,
        "iv_rank": "25",
        "market_regime": "normal",
        "portfolio_risk_state": "normal",
        "quote_age_seconds": 1,
        "spread_pct": "5",
        "within_entry_window": True,
        "before_force_flatten": True,
        "net_ev_r": "0.15",
        "reward_risk_ratio": "1.50",
        "supported_options_level": 2,
    }
    inputs["opportunity_score"] = "77"
    assert authorize_proposal(proposal, risk, settings, inputs=inputs).outcome == "REJECT"
    inputs["opportunity_score"] = "78"
    assert authorize_proposal(proposal, risk, settings, inputs=inputs).outcome == "APPROVE"


def test_persisted_profile_parameters_remain_bounded_by_the_same_rule_engine() -> None:
    proposal = _proposal()
    risk = RiskAssessment(
        trace_id=proposal.trace_id,
        proposal_id=proposal.id,
        verdict="acceptable",
        max_loss=Decimal("1"),
        findings=[],
        data_fresh=True,
    )
    settings = Settings(
        _env_file=None,
        execution_enabled=True,
        execution_kill_switch=False,
        active_ruleset_version="1.0.0",
    )
    inputs = {
        "market_fresh": True,
        "analog_count": 30,
        "fundamentals_sourced": True,
        "account_verified": True,
        "open_positions": 0,
        "buying_power_ok": True,
        "cash_buffer_ok": True,
        "concentration_ok": True,
        "position_size_ok": True,
        "aggregate_risk_ok": True,
        "portfolio_controls_complete": True,
        "sector_concentration_ok": True,
        "cluster_concentration_ok": True,
        "greeks_risk_ok": True,
        "expiration_concentration_ok": True,
        "market_open": True,
        "iv_rank_available": True,
        "iv_rank": "25",
        "market_regime": "normal",
        "portfolio_risk_state": "normal",
        "quote_age_seconds": 1,
        "spread_pct": "5",
        "within_entry_window": True,
        "before_force_flatten": True,
        "net_ev_r": "0.15",
        "reward_risk_ratio": "1.50",
        "supported_options_level": 2,
        "opportunity_score": "78",
    }
    conservative = ProfileParameters(
        target_position_size_pct=Decimal("1.50"),
        opportunity_score_threshold=Decimal("85"),
        take_profit_pct=Decimal("75"),
        stop_loss_pct=Decimal("50"),
    )
    decision = authorize_proposal(
        proposal,
        risk,
        settings,
        inputs=inputs,
        profile_key="conservative",
        profile_parameters=conservative,
        profile_id=UUID("00000000-0000-0000-0000-000000000001"),
        profile_version=7,
    )
    assert decision.outcome == "REJECT"
    assert decision.profile_id == UUID("00000000-0000-0000-0000-000000000001")
    assert decision.profile_version == 7


def test_missing_operational_controls_fail_closed_even_at_threshold() -> None:
    proposal = _proposal()
    risk = RiskAssessment(
        trace_id=proposal.trace_id,
        proposal_id=proposal.id,
        verdict="acceptable",
        max_loss=Decimal("1"),
        findings=[],
        data_fresh=True,
    )
    settings = Settings(
        _env_file=None,
        execution_enabled=True,
        execution_kill_switch=False,
        active_ruleset_version="1.0.0",
    )
    decision = authorize_proposal(
        proposal,
        risk,
        settings,
        inputs={
            "market_fresh": True,
            "analog_count": 30,
            "fundamentals_sourced": True,
            "account_verified": True,
            "open_positions": 0,
            "buying_power_ok": True,
            "cash_buffer_ok": True,
            "concentration_ok": True,
            "portfolio_controls_complete": True,
            "sector_concentration_ok": True,
            "cluster_concentration_ok": True,
            "greeks_risk_ok": True,
            "expiration_concentration_ok": True,
            "quote_age_seconds": 1,
            "spread_pct": "5",
            "market_open": True,
            "within_entry_window": True,
            "before_force_flatten": True,
            "opportunity_score": "99",
            "net_ev_r": "0.50",
            "reward_risk_ratio": "2.0",
            "market_regime": "normal",
            "portfolio_risk_state": "normal",
            "supported_options_level": 2,
        },
    )
    assert decision.outcome == "REJECT"


def test_high_iv_rank_requires_a_debit_spread() -> None:
    proposal = _proposal()
    risk = RiskAssessment(
        trace_id=proposal.trace_id,
        proposal_id=proposal.id,
        verdict="acceptable",
        max_loss=Decimal("1"),
        findings=[],
        data_fresh=True,
    )
    settings = Settings(
        _env_file=None,
        execution_enabled=True,
        execution_kill_switch=False,
        active_ruleset_version="1.0.0",
    )
    inputs = {
        "market_fresh": True,
        "analog_count": 30,
        "fundamentals_sourced": True,
        "account_verified": True,
        "open_positions": 0,
        "buying_power_ok": True,
        "cash_buffer_ok": True,
        "concentration_ok": True,
        "position_size_ok": True,
        "aggregate_risk_ok": True,
        "market_open": True,
        "iv_rank_available": True,
        "iv_rank": "51",
        "market_regime": "normal",
        "portfolio_risk_state": "normal",
        "quote_age_seconds": 1,
        "spread_pct": "5",
        "within_entry_window": True,
        "before_force_flatten": True,
        "opportunity_score": "99",
        "net_ev_r": "0.50",
        "reward_risk_ratio": "2.0",
        "supported_options_level": 2,
    }
    assert authorize_proposal(proposal, risk, settings, inputs=inputs).outcome == "REJECT"


def test_candidate_research_outcome_structure() -> None:
    outcome = CandidateResearchOutcome(
        rejection_code="OPTION_SELECTION_REJECTED",
        rejection_reason="Option quote spread exceeds 10 percent",
    )
    assert outcome.candidate is None
    assert outcome.rejection_code == "OPTION_SELECTION_REJECTED"
    assert outcome.rejection_reason == "Option quote spread exceeds 10 percent"


@pytest.mark.asyncio
async def test_record_captures_structured_candidate_rejections() -> None:
    settings = Settings(
        _env_file=None,
        execution_enabled=True,
        execution_kill_switch=False,
        active_ruleset_version="1.0.0",
        shadowfund_enabled=False,
    )
    worker = AutonomousWorker(settings)
    now = datetime(2026, 8, 31, 14, 0, tzinfo=UTC)

    added_objects: list[Any] = []
    mock_session = AsyncMock()
    mock_session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
    mock_session.flush = AsyncMock()

    rejections = {
        "NVDA": {
            "code": "OPTION_SELECTION_REJECTED",
            "reason": "Option quote spread exceeds 10 percent",
        },
        "AAPL": {
            "code": "IV_RANK_UNAVAILABLE",
            "reason": "Only 0 IV observations available; 20 required",
        },
    }
    reason_str = (
        "No eligible deterministic proposal - "
        "NVDA: OPTION_SELECTION_REJECTED (Option quote spread exceeds 10 percent); "
        "AAPL: IV_RANK_UNAVAILABLE (Only 0 IV observations available; 20 required)"
    )

    await worker._record(
        mock_session,
        now,
        "NO_TRADE",
        reason_str,
        evidence={"candidate_rejections": rejections},
    )

    cycle_models = [obj for obj in added_objects if isinstance(obj, AutonomousCycleModel)]
    assert len(cycle_models) == 1
    assert cycle_models[0].outcome == "NO_TRADE"
    assert "NVDA: OPTION_SELECTION_REJECTED" in cycle_models[0].reason
    assert "AAPL: IV_RANK_UNAVAILABLE" in cycle_models[0].reason


def test_trade_verdict_affirmative_options_proposal() -> None:
    affirmative = {
        TradeVerdict.PROCEED_TO_OPTIONS_PROPOSAL,
        TradeVerdict.PROPOSE_TRADE,
    }
    assert TradeVerdict.PROCEED_TO_OPTIONS_PROPOSAL in affirmative
    assert TradeVerdict.PROPOSE_TRADE in affirmative
    assert TradeVerdict.NO_TRADE not in affirmative
    assert TradeVerdict.PROCEED_TO_OPTIONS_PROPOSAL.value == "proceed_to_options_proposal"
