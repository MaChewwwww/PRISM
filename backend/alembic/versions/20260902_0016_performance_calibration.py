"""Add adaptive strategy lifecycle and activate ruleset v2.

Revision ID: 20260902_0016
Revises: 20260901_0015
"""

from collections.abc import Sequence
from datetime import UTC, datetime
import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa

from alembic import op

revision: str = "20260902_0016"
down_revision: str | None = "20260901_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def upgrade() -> None:
    op.add_column(
        "llm_event_analyses",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "llm_event_analyses",
        sa.Column("provider_observed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "research_reports",
        sa.Column("event_published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "research_reports",
        sa.Column("provider_observed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "research_reports",
        sa.Column("calculation_window_start", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "research_reports",
        sa.Column("calculation_window_end", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "research_reports",
        sa.Column(
            "methodology_version",
            sa.String(64),
            nullable=False,
            server_default="reaction_event_aligned_v2",
        ),
    )
    op.add_column(
        "trade_decisions",
        sa.Column(
            "bullish_opportunity_score", sa.Numeric(), nullable=False, server_default=sa.text("0")
        ),
    )
    op.add_column(
        "trade_decisions",
        sa.Column(
            "bearish_opportunity_score", sa.Numeric(), nullable=False, server_default=sa.text("0")
        ),
    )
    op.add_column("trade_decisions", sa.Column("catalyst_digest", sa.String(64), nullable=True))
    op.add_column(
        "trade_decisions",
        sa.Column(
            "scoring_methodology_version",
            sa.String(64),
            nullable=False,
            server_default="directional_composite_v2",
        ),
    )
    op.add_column(
        "execution_receipts", sa.Column("strategy_position_id", sa.String(36), nullable=True)
    )
    op.add_column("execution_receipts", sa.Column("legs_json", sa.Text(), nullable=True))
    op.create_index(
        "ix_execution_receipts_strategy_position_id",
        "execution_receipts",
        ["strategy_position_id"],
    )
    op.create_table(
        "strategy_positions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("proposal_id", sa.String(36), nullable=False, unique=True),
        sa.Column("thesis_key", sa.String(64), nullable=False, unique=True),
        sa.Column("catalyst_digest", sa.String(64), nullable=False),
        sa.Column("underlying", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("strategy_kind", sa.String(32), nullable=False),
        sa.Column("strategy_json", sa.Text(), nullable=False),
        sa.Column("exit_policy_json", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("entry_debit", sa.Numeric(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("last_liquidation_value", sa.Numeric(), nullable=True),
        sa.Column("current_return_pct", sa.Numeric(), nullable=True),
        sa.Column("mfe_pct", sa.Numeric(), nullable=False, server_default=sa.text("0")),
        sa.Column("profit_armed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score_failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_score_evidence_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_score_evidence_id", sa.String(36), nullable=True),
        sa.Column("exit_latched_reason", sa.String(64), nullable=True),
        sa.Column("exit_latched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parent_exit_receipt_id", sa.String(36), nullable=True),
        sa.Column("last_marked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_strategy_positions_underlying_status",
        "strategy_positions",
        ["underlying", "status"],
    )
    op.create_table(
        "strategy_lifecycle_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("strategy_position_id", sa.String(36), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_strategy_lifecycle_events_strategy_observed",
        "strategy_lifecycle_events",
        ["strategy_position_id", "observed_at"],
    )

    # Ruleset v2 deliberately returns profile calibration to manual and removes
    # exit thresholds from profile-tunable parameters. Prior rows remain audit
    # evidence and are superseded rather than rewritten.
    op.execute(sa.text("UPDATE ai_profiles SET status = 'superseded' WHERE status = 'active'"))
    op.execute(
        sa.text(
            "UPDATE profile_calibration_preferences "
            "SET mode = 'manual', automatic_opt_in = false, updated_by = 'ruleset-v2-migration'"
        )
    )
    payload = {
        "seed": "authorized_registry",
        "profile_key": "balanced",
        "version": 2,
        "ruleset": "prism-authorized-baseline@2.0.0",
        "parameters": {
            "target_position_size_pct": "2.00",
            "opportunity_score_threshold": "78",
        },
    }
    ai_profiles = sa.table(
        "ai_profiles",
        sa.column("id", sa.String),
        sa.column("profile_key", sa.String),
        sa.column("version", sa.Integer),
        sa.column("status", sa.String),
        sa.column("ruleset_id", sa.String),
        sa.column("ruleset_version", sa.String),
        sa.column("activation_mode", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("effective_at", sa.DateTime(timezone=True)),
        sa.column("activated_by", sa.String),
        sa.column("source_batch_id", sa.String),
        sa.column("parameters_json", sa.Text),
        sa.column("input_digest", sa.String),
    )
    activated_at = datetime(2026, 9, 2, tzinfo=UTC)
    op.bulk_insert(
        ai_profiles,
        [
            {
                "id": str(uuid5(NAMESPACE_URL, "prism-authorized-baseline:balanced:2")),
                "profile_key": "balanced",
                "version": 2,
                "status": "active",
                "ruleset_id": "prism-authorized-baseline",
                "ruleset_version": "2.0.0",
                "activation_mode": "manual",
                "created_at": activated_at,
                "effective_at": activated_at,
                "activated_by": "ruleset-v2-migration",
                "source_batch_id": None,
                "parameters_json": json.dumps(payload["parameters"], sort_keys=True),
                "input_digest": _digest(payload),
            }
        ],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_strategy_lifecycle_events_strategy_observed",
        table_name="strategy_lifecycle_events",
    )
    op.drop_table("strategy_lifecycle_events")
    op.drop_index("ix_strategy_positions_underlying_status", table_name="strategy_positions")
    op.drop_table("strategy_positions")
    op.drop_index(
        "ix_execution_receipts_strategy_position_id", table_name="execution_receipts"
    )
    op.drop_column("execution_receipts", "legs_json")
    op.drop_column("execution_receipts", "strategy_position_id")
    op.drop_column("trade_decisions", "scoring_methodology_version")
    op.drop_column("trade_decisions", "catalyst_digest")
    op.drop_column("trade_decisions", "bearish_opportunity_score")
    op.drop_column("trade_decisions", "bullish_opportunity_score")
    op.drop_column("research_reports", "methodology_version")
    op.drop_column("research_reports", "calculation_window_end")
    op.drop_column("research_reports", "calculation_window_start")
    op.drop_column("research_reports", "provider_observed_at")
    op.drop_column("research_reports", "event_published_at")
    op.drop_column("llm_event_analyses", "provider_observed_at")
    op.drop_column("llm_event_analyses", "published_at")
