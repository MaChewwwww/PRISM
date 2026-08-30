"""Post-Analysis reflection agent and weekly evidence aggregation.

Aggregates weekly trading execution and ShadowFund counterfactual evidence,
reflects upon strategy behavior, and produces bounded AI Profile recommendations.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.autonomous.models import (
    AuthorizationModel,
    TradeProposalModel,
)
from app.core.llm_gateway import LLMGateway
from app.execution.models import ExecutionReceiptModel
from app.profiles.service import ActiveProfile
from app.rules.registry import ProfileField, get_authorized_ruleset
from app.shadowfund.models import (
    ShadowBranchModel,
    ShadowSessionModel,
    ShadowValuationModel,
)

logger = logging.getLogger(__name__)

POST_ANALYSIS_AGENT_VERSION = "weekly-reflection-v1"


class ProfileRecommendationLLMItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameter_id: ProfileField = Field(
        description=(
            "The BA-authorized profile parameter to adjust. Must be one of: "
            "'target_position_size_pct', 'opportunity_score_threshold', "
            "'take_profit_pct', 'stop_loss_pct'."
        )
    )
    suggested_value: str = Field(description="Decimal value as string within authorized bounds.")
    rationale: str = Field(
        description=(
            "Grounded explanation referencing observed weekly outcomes, "
            "win rate, or counterfactual branch performance."
        )
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description="Confidence level in the calibration adjustment."
    )


class PostAnalysisLLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_findings: list[str] = Field(
        default_factory=list,
        description="Key analytical findings and takeaways from the trading week.",
    )
    recommendations: list[ProfileRecommendationLLMItem] = Field(
        default_factory=list,
        description="List of proposed parameter calibrations strictly within authorized ranges.",
    )


def get_trading_week_bounds(now: datetime) -> tuple[datetime, datetime]:
    """Return Monday 00:00 UTC to Friday 20:00 UTC bounds for the concluding week."""
    now_utc = now.astimezone(UTC)
    weekday = now_utc.weekday()  # Monday = 0, Friday = 4, Saturday = 5, Sunday = 6
    if weekday >= 4:
        # Friday, Saturday, Sunday -> current week Monday to Friday
        monday = (now_utc - timedelta(days=weekday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        friday = (now_utc - timedelta(days=weekday - 4)).replace(
            hour=20, minute=0, second=0, microsecond=0
        )
    else:
        # Monday - Thursday -> preceding week Monday to Friday
        monday = (now_utc - timedelta(days=weekday + 7)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        friday = (now_utc - timedelta(days=weekday + 3)).replace(
            hour=20, minute=0, second=0, microsecond=0
        )
    return monday, friday


def is_friday_post_close(now: datetime) -> bool:
    """Check if timestamp is after Friday market close (20:00 UTC) or weekend."""
    now_utc = now.astimezone(UTC)
    return (now_utc.weekday() == 4 and now_utc.hour >= 20) or (now_utc.weekday() in (5, 6))


class PostAnalysisAgent:
    """Evidence-qualified Post-Analysis agent synthesizing weekly performance."""

    def __init__(self, llm_gateway: LLMGateway) -> None:
        self.llm_gateway = llm_gateway

    async def gather_weekly_evidence(
        self,
        session: AsyncSession,
        *,
        window_start: datetime,
        window_end: datetime,
        source_mode: str = "production",
    ) -> dict[str, Any]:
        """Aggregate proposals, authorizations, receipts, and shadow branches."""
        window_start_utc = window_start.astimezone(UTC)
        window_end_utc = window_end.astimezone(UTC)

        proposals = list(
            (
                await session.scalars(
                    select(TradeProposalModel).where(
                        TradeProposalModel.created_at >= window_start_utc,
                        TradeProposalModel.created_at <= window_end_utc,
                    )
                )
            ).all()
        )

        authorizations = list(
            (
                await session.scalars(
                    select(AuthorizationModel).where(
                        AuthorizationModel.created_at >= window_start_utc,
                        AuthorizationModel.created_at <= window_end_utc,
                    )
                )
            ).all()
        )

        receipts = list(
            (
                await session.scalars(
                    select(ExecutionReceiptModel).where(
                        ExecutionReceiptModel.created_at >= window_start_utc,
                        ExecutionReceiptModel.created_at <= window_end_utc,
                    )
                )
            ).all()
        )

        shadow_sessions = list(
            (
                await session.scalars(
                    select(ShadowSessionModel).where(
                        ShadowSessionModel.source_mode == source_mode,
                        ShadowSessionModel.created_at >= window_start_utc,
                        ShadowSessionModel.created_at <= window_end_utc,
                    )
                )
            ).all()
        )

        shadow_beat_chosen = 0
        branch_stats: dict[str, dict[str, Any]] = {}

        for s_session in shadow_sessions:
            branches = list(
                (
                    await session.scalars(
                        select(ShadowBranchModel).where(
                            ShadowBranchModel.session_id == s_session.id
                        )
                    )
                ).all()
            )
            chosen_branch = next((b for b in branches if b.chosen_path), None)
            chosen_pnl = Decimal("0")
            if chosen_branch:
                last_val = await session.scalar(
                    select(ShadowValuationModel)
                    .where(ShadowValuationModel.branch_id == chosen_branch.id)
                    .order_by(ShadowValuationModel.observed_at.desc())
                    .limit(1)
                )
                if last_val is not None:
                    chosen_pnl = last_val.net_pnl

            beat_chosen_for_session = False
            for branch in branches:
                if branch.chosen_path:
                    continue
                branch_val = await session.scalar(
                    select(ShadowValuationModel)
                    .where(ShadowValuationModel.branch_id == branch.id)
                    .order_by(ShadowValuationModel.observed_at.desc())
                    .limit(1)
                )
                if branch_val is not None:
                    if branch.branch_key not in branch_stats:
                        branch_stats[branch.branch_key] = {
                            "label": branch.label,
                            "count": 0,
                            "positive_pnl_count": 0,
                        }
                    branch_stats[branch.branch_key]["count"] += 1
                    if branch_val.net_pnl > 0:
                        branch_stats[branch.branch_key]["positive_pnl_count"] += 1
                    if branch_val.net_pnl > chosen_pnl:
                        beat_chosen_for_session = True

            if beat_chosen_for_session:
                shadow_beat_chosen += 1

        approvals_count = sum(1 for a in authorizations if a.outcome == "APPROVE")
        rejections_count = sum(1 for a in authorizations if a.outcome == "REJECT")
        submitted_count = sum(1 for r in receipts if r.status in {"submitted", "filled"})
        filled_count = sum(1 for r in receipts if r.status == "filled")

        return {
            "window_start": window_start_utc.isoformat(),
            "window_end": window_end_utc.isoformat(),
            "stories_analyzed": len(proposals),
            "proposals_approved": approvals_count,
            "proposals_rejected": rejections_count,
            "trades_submitted": submitted_count,
            "trades_filled": filled_count,
            "shadow_sessions_count": len(shadow_sessions),
            "shadow_beat_chosen": shadow_beat_chosen,
            "branch_performance": branch_stats,
            "symbols_evaluated": sorted(list({p.symbol for p in proposals})),
        }

    async def analyze_week(
        self,
        session: AsyncSession,
        *,
        window_start: datetime,
        window_end: datetime,
        source_mode: str = "production",
        active_profile: ActiveProfile | None = None,
    ) -> tuple[dict[str, Any], list[dict[str, str]]]:
        """Synthesize weekly performance and produce validated recommendation dicts."""
        evidence = await self.gather_weekly_evidence(
            session,
            window_start=window_start,
            window_end=window_end,
            source_mode=source_mode,
        )

        stories_analyzed = evidence.get("stories_analyzed", 0)
        shadow_sessions_count = evidence.get("shadow_sessions_count", 0)

        # Fail closed safely if no evidence exists for this week
        if stories_analyzed == 0 and shadow_sessions_count == 0:
            summary = {
                "outcome": "NO_RECOMMENDATION",
                "reason": "Insufficient eligible evidence in the weekly window.",
                "stories_analyzed": 0,
                "trades_submitted": 0,
                "trades_filled": 0,
                "shadow_beat_chosen": 0,
                "key_findings": [
                    "No trading proposals or shadow sessions were recorded for this weekly window."
                ],
            }
            return summary, []

        ruleset = get_authorized_ruleset()
        bounds_info = {
            k: {"min": str(v.minimum), "max": str(v.maximum)}
            for k, v in ruleset.profile_bounds.items()
        }
        active_params = (
            active_profile.parameters.model_dump(mode="json")
            if active_profile is not None
            else ruleset.profiles[ruleset.default_profile].model_dump(mode="json")
        )

        prompt = (
            "Act as PRISM's Weekly Post-Analysis and Strategy Reflection Specialist. "
            "Analyze the past trading week's paper execution outcomes, risk evaluations, "
            "and ShadowFund counterfactuals.\n\n"
            "AUTHORIZED AI PROFILE PARAMETERS AND HARD BOUNDS:\n"
            f"{json.dumps(bounds_info, indent=2)}\n\n"
            "CURRENT ACTIVE PROFILE PARAMETERS:\n"
            f"{json.dumps(active_params, indent=2)}\n\n"
            "WEEKLY EVIDENCE AGGREGATE:\n"
            f"{json.dumps(evidence, default=str, indent=2)}\n\n"
            "Guidelines:\n"
            "1. Provide key analytical findings explaining what happened, "
            "strategy performance, and how counterfactual branches compared.\n"
            "2. Suggest parameter adjustments ONLY if justified by evidence, "
            "strictly within authorized min/max bounds.\n"
            "3. Note that 'stop_loss_pct' is fixed at 50.00% and cannot be tuned.\n"
            "4. Return strictly valid JSON matching the requested schema."
        )

        try:
            trace_id = uuid4()
            result = await self.llm_gateway.complete_structured(
                prompt=prompt,
                response_model=PostAnalysisLLMOutput,
                trace_id=trace_id,
            )
            output = result.parsed
            if output is None:
                raise ValueError("Post-Analysis agent returned no structured output")

            formatted_recommendations: list[dict[str, str]] = []
            for rec in output.recommendations:
                if rec.parameter_id not in ruleset.profile_bounds:
                    continue
                formatted_recommendations.append(
                    {
                        "parameter_id": rec.parameter_id,
                        "suggested_value": str(rec.suggested_value),
                        "rationale": rec.rationale,
                        "confidence": rec.confidence,
                    }
                )

            summary = {
                "outcome": "RECOMMENDED" if formatted_recommendations else "NO_RECOMMENDATION",
                "reason": (
                    "Weekly reflection generated profile calibration recommendations."
                    if formatted_recommendations
                    else "Weekly review concluded no parameter adjustments are warranted."
                ),
                "stories_analyzed": stories_analyzed,
                "trades_submitted": evidence.get("trades_submitted", 0),
                "trades_filled": evidence.get("trades_filled", 0),
                "shadow_beat_chosen": evidence.get("shadow_beat_chosen", 0),
                "key_findings": output.key_findings
                or ["Weekly strategy reflection completed without exceptions."],
            }
            return summary, formatted_recommendations
        except Exception as exc:
            logger.warning("Post-Analysis LLM completion failed closed: %s", exc)
            summary = {
                "outcome": "NO_RECOMMENDATION",
                "reason": f"Post-Analysis LLM reflection unavailable: {type(exc).__name__}",
                "stories_analyzed": stories_analyzed,
                "trades_submitted": evidence.get("trades_submitted", 0),
                "trades_filled": evidence.get("trades_filled", 0),
                "shadow_beat_chosen": evidence.get("shadow_beat_chosen", 0),
                "key_findings": ["LLM reflection unavailable; preserving active baseline."],
            }
            return summary, []
