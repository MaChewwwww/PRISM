from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.autonomous.worker import AutonomousWorker
from app.core.config import Settings
from app.core.llm_gateway import LLMCompletionResult, LLMGateway
from app.profiles.service import ActiveProfile, ProfileGovernanceService
from app.research.post_analysis import (
    PostAnalysisAgent,
    PostAnalysisLLMOutput,
    ProfileRecommendationLLMItem,
    get_trading_week_bounds,
    is_friday_post_close,
)
from app.rules.registry import ProfileParameters
from app.shadowfund.models import (
    ShadowBranchModel,
    ShadowPostAnalysisBatchModel,
    ShadowProfileRecommendationModel,
    ShadowSessionModel,
    ShadowValuationModel,
)
from app.shadowfund.service import ShadowFundService


def test_trading_week_bounds_and_friday_post_close() -> None:
    # Friday 20:30 UTC (after market close)
    fri_night = datetime(2026, 8, 28, 20, 30, tzinfo=UTC)
    assert is_friday_post_close(fri_night) is True
    start, end = get_trading_week_bounds(fri_night)
    assert start == datetime(2026, 8, 24, 0, 0, tzinfo=UTC)
    assert end == datetime(2026, 8, 28, 20, 0, tzinfo=UTC)

    # Friday 18:00 UTC (market still open)
    fri_open = datetime(2026, 8, 28, 18, 0, tzinfo=UTC)
    assert is_friday_post_close(fri_open) is False

    # Saturday
    sat = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    assert is_friday_post_close(sat) is True
    sat_start, sat_end = get_trading_week_bounds(sat)
    assert sat_start == datetime(2026, 8, 24, 0, 0, tzinfo=UTC)
    assert sat_end == datetime(2026, 8, 28, 20, 0, tzinfo=UTC)

    # Sunday
    sun = datetime(2026, 8, 30, 18, 0, tzinfo=UTC)
    assert is_friday_post_close(sun) is True
    sun_start, sun_end = get_trading_week_bounds(sun)
    assert sun_start == datetime(2026, 8, 24, 0, 0, tzinfo=UTC)
    assert sun_end == datetime(2026, 8, 28, 20, 0, tzinfo=UTC)

    # Wednesday (midweek)
    wed = datetime(2026, 9, 2, 15, 0, tzinfo=UTC)
    assert is_friday_post_close(wed) is False


@pytest.mark.asyncio
async def test_post_analysis_empty_evidence_fails_closed_to_no_recommendation() -> None:
    mock_gateway = MagicMock(spec=LLMGateway)
    agent = PostAnalysisAgent(mock_gateway)
    window_start = datetime(2026, 8, 24, 0, 0, tzinfo=UTC)
    window_end = datetime(2026, 8, 28, 20, 0, tzinfo=UTC)

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_session.scalars.return_value = mock_scalars

    summary, recommendations = await agent.analyze_week(
        mock_session,
        window_start=window_start,
        window_end=window_end,
        source_mode="production",
    )

    assert summary["outcome"] == "NO_RECOMMENDATION"
    assert recommendations == []
    mock_gateway.complete_structured.assert_not_called()


@pytest.mark.asyncio
async def test_post_analysis_with_evidence_and_mock_llm() -> None:
    window_start = datetime(2026, 8, 24, 0, 0, tzinfo=UTC)
    window_end = datetime(2026, 8, 28, 20, 0, tzinfo=UTC)

    session_row = ShadowSessionModel(
        id="session-1",
        trace_id=str(uuid4()),
        created_at=datetime(2026, 8, 26, 14, 0, tzinfo=UTC),
        evaluation_root_digest="root-digest-1",
        terminal_outcome="APPROVE",
        symbol="NVDA",
        state="closed",
        source_mode="production",
        source_feed="configured",
        valuation_policy_version="v1",
        input_digest="input-digest-1",
    )

    branch_chosen = ShadowBranchModel(
        id="branch-chosen",
        session_id="session-1",
        branch_key="chosen_path",
        label="Chosen Path",
        variation="baseline",
        allocation_multiplier=Decimal("1"),
        chosen_path=True,
        state="closed",
    )
    branch_contra = ShadowBranchModel(
        id="branch-contra",
        session_id="session-1",
        branch_key="contrarian",
        label="Contrarian",
        variation="opposite",
        allocation_multiplier=Decimal("1"),
        chosen_path=False,
        state="closed",
    )

    val_contra = ShadowValuationModel(
        id="val-2",
        branch_id="branch-contra",
        observed_at=datetime(2026, 8, 27, 20, 0, tzinfo=UTC),
        gross_pnl=Decimal("20.00"),
        net_pnl=Decimal("18.00"),
        drawdown=Decimal("0.00"),
        mae=Decimal("0.00"),
        mfe=Decimal("22.00"),
        capital_at_risk=Decimal("100.00"),
        coverage_pct=Decimal("100"),
        confidence="confident",
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    def mock_scalars_impl(stmt):
        scalars_obj = MagicMock()
        stmt_str = str(stmt)
        if (
            "trade_proposals" in stmt_str
            or "authorizations" in stmt_str
            or "execution_receipts" in stmt_str
        ):
            scalars_obj.all.return_value = []
        elif "shadow_sessions" in stmt_str:
            scalars_obj.all.return_value = [session_row]
        elif "shadow_branches" in stmt_str:
            scalars_obj.all.return_value = [branch_chosen, branch_contra]
        else:
            scalars_obj.all.return_value = []
        return scalars_obj

    mock_session.scalars.side_effect = mock_scalars_impl

    def mock_scalar_impl(stmt):
        stmt_str = str(stmt)
        if "branch_id" in stmt_str:
            return val_contra
        return None

    mock_session.scalar.side_effect = mock_scalar_impl

    llm_output = PostAnalysisLLMOutput(
        key_findings=[
            "Contrarian branches outperformed chosen paths on NVDA.",
            "Selective opportunity score threshold improved quality.",
        ],
        recommendations=[
            ProfileRecommendationLLMItem(
                parameter_id="opportunity_score_threshold",
                suggested_value="88",
                rationale="Filters marginal setups based on weekly execution observations.",
                confidence="high",
            ),
            ProfileRecommendationLLMItem(
                parameter_id="take_profit_pct",
                suggested_value="85.00",
                rationale="Wider profit target captured upside continuation.",
                confidence="medium",
            ),
        ],
    )

    mock_gateway = MagicMock(spec=LLMGateway)
    mock_gateway.complete_structured = AsyncMock(
        return_value=LLMCompletionResult(
            raw_content="{}",
            parsed=llm_output,
            raw_digest="digest-123",
            model="mock-model",
            provider="mock-provider",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            latency_ms=120,
            trace_id=uuid4(),
        )
    )

    agent = PostAnalysisAgent(mock_gateway)
    summary, recommendations = await agent.analyze_week(
        mock_session,
        window_start=window_start,
        window_end=window_end,
        source_mode="production",
    )

    assert summary["outcome"] == "RECOMMENDED"
    assert len(recommendations) == 2
    assert recommendations[0]["parameter_id"] == "opportunity_score_threshold"
    assert recommendations[0]["suggested_value"] == "88"
    assert recommendations[1]["parameter_id"] == "take_profit_pct"
    assert recommendations[1]["suggested_value"] == "85.00"
    assert len(summary["key_findings"]) == 2


@pytest.mark.asyncio
async def test_shadowfund_service_persist_post_analysis_batch_bounds_validation() -> None:
    mock_session = AsyncMock()
    mock_session.scalar.return_value = None  # No existing batch
    added_objects = []
    mock_session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

    window_start = datetime(2026, 8, 24, 0, 0, tzinfo=UTC)
    window_end = datetime(2026, 8, 28, 20, 0, tzinfo=UTC)

    shadow_service = ShadowFundService()
    batch = await shadow_service.persist_post_analysis_batch(
        mock_session,
        source_mode="production",
        window_start=window_start,
        window_end=window_end,
        model_metadata={"trigger": "weekly_friday_post_analysis"},
        summary={"outcome": "RECOMMENDED"},
        recommendations=[
            {
                "parameter_id": "opportunity_score_threshold",
                "suggested_value": "88",
                "rationale": "Valid score",
                "confidence": "high",
            },
            {
                "parameter_id": "take_profit_pct",
                "suggested_value": "120.00",  # Outside max 100.00%
                "rationale": "Too high",
                "confidence": "low",
            },
        ],
    )

    assert batch.state == "DRAFT"
    recs = [obj for obj in added_objects if isinstance(obj, ShadowProfileRecommendationModel)]
    assert len(recs) == 2
    assert recs[0].validation_state == "WITHIN_AUTHORIZED_BOUNDS"
    assert recs[1].validation_state == "REJECTED_OUTSIDE_AUTHORIZED_BOUNDS"


@pytest.mark.asyncio
async def test_weekly_post_analysis_trigger_and_idempotency() -> None:
    settings = Settings(
        auth_email="operator@prism.test",
        auth_password="password-12345",
        jwt_secret_key="01234567890123456789012345678901",
        shadowfund_enabled=True,
    )
    worker = AutonomousWorker(settings)

    # 1. Non-Friday timestamp -> returns None
    wednesday = datetime(2026, 9, 2, 14, 0, tzinfo=UTC)
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    result = await worker._run_weekly_post_analysis_if_due(mock_session, wednesday)
    assert result is None

    # 2. Friday post-close timestamp when batch already exists -> returns None (idempotent)
    friday_post_close = datetime(2026, 8, 28, 21, 0, tzinfo=UTC)
    mock_session.scalar.return_value = "batch-existing-id"
    result = await worker._run_weekly_post_analysis_if_due(mock_session, friday_post_close)
    assert result is None

    # 3. Friday post-close timestamp when batch does not exist -> runs post-analysis
    mock_session.scalar.return_value = None  # No existing batch
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_session.scalars.return_value = mock_scalars

    added_objects = []
    mock_session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

    active_profile = ActiveProfile(
        id=uuid4(),
        profile_key="balanced",
        version=1,
        parameters=ProfileParameters(
            target_position_size_pct=Decimal("2.00"),
            opportunity_score_threshold=Decimal("78"),
            take_profit_pct=Decimal("75.00"),
            stop_loss_pct=Decimal("50.00"),
        ),
        activation_mode="manual",
    )

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(ProfileGovernanceService, "get_active", AsyncMock(return_value=active_profile))
        mp.setattr(
            ProfileGovernanceService,
            "apply_automatic_if_enabled",
            AsyncMock(return_value=None),
        )

        batch_id = await worker._run_weekly_post_analysis_if_due(mock_session, friday_post_close)
        assert batch_id is not None
        batch_obj = next(
            (o for o in added_objects if isinstance(o, ShadowPostAnalysisBatchModel)),
            None,
        )
        assert batch_obj is not None
        assert batch_obj.state == "NO_RECOMMENDATION"
