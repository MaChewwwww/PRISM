"""Persist immutable ShadowFund sessions, observations, and valuations.

Revision ID: 20260831_0008
Revises: 20260830_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260831_0008"
down_revision: str | None = "20260830_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shadow_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluation_root_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("terminal_outcome", sa.String(40), nullable=False),
        sa.Column("proposal_id", sa.String(36), nullable=True, index=True),
        sa.Column("authorization_id", sa.String(36), nullable=True),
        sa.Column("backtest_run_id", sa.String(36), nullable=True, index=True),
        sa.Column("symbol", sa.String(20), nullable=True, index=True),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("source_mode", sa.String(20), nullable=False),
        sa.Column("source_feed", sa.String(40), nullable=False),
        sa.Column("valuation_policy_version", sa.String(32), nullable=False),
        sa.Column("exit_policy_json", sa.Text(), nullable=True),
        sa.Column("ruleset_version", sa.String(32), nullable=True),
        sa.Column("profile_version", sa.Integer(), nullable=True),
        sa.Column("input_digest", sa.String(64), nullable=False),
        sa.Column("refusal_reason", sa.Text(), nullable=True),
        sa.Column("horizon_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "shadow_branches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False, index=True),
        sa.Column("branch_key", sa.String(40), nullable=False),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("variation", sa.Text(), nullable=False),
        sa.Column("strategy_json", sa.Text(), nullable=True),
        sa.Column("allocation_multiplier", sa.Numeric(18, 6), nullable=False),
        sa.Column("entry_cost", sa.Numeric(18, 6), nullable=True),
        sa.Column("entry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("chosen_path", sa.Boolean(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
    )
    op.create_table(
        "shadow_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False, index=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("feed", sa.String(40), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "shadow_valuations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("branch_id", sa.String(36), nullable=False, index=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("gross_pnl", sa.Numeric(18, 6), nullable=False),
        sa.Column("net_pnl", sa.Numeric(18, 6), nullable=False),
        sa.Column("drawdown", sa.Numeric(18, 6), nullable=False),
        sa.Column("mae", sa.Numeric(18, 6), nullable=False),
        sa.Column("mfe", sa.Numeric(18, 6), nullable=False),
        sa.Column("capital_at_risk", sa.Numeric(18, 6), nullable=False),
        sa.Column("coverage_pct", sa.Numeric(9, 4), nullable=False),
        sa.Column("confidence", sa.String(20), nullable=False),
        sa.Column("exit_reason", sa.String(40), nullable=True),
    )
    op.create_table(
        "shadow_post_analysis_batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_mode", sa.String(20), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("input_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("model_metadata_json", sa.Text(), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "shadow_profile_recommendations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("batch_id", sa.String(36), nullable=False, index=True),
        sa.Column("parameter_id", sa.String(80), nullable=False),
        sa.Column("current_value", sa.String(40), nullable=False),
        sa.Column("suggested_value", sa.String(40), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("confidence", sa.String(20), nullable=False),
        sa.Column("validation_state", sa.String(40), nullable=False),
        sa.Column("manual_review_required", sa.Boolean(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("shadow_profile_recommendations")
    op.drop_table("shadow_post_analysis_batches")
    op.drop_table("shadow_valuations")
    op.drop_table("shadow_observations")
    op.drop_table("shadow_branches")
    op.drop_table("shadow_sessions")
