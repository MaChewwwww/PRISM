"""Persist auditable AI Profile calibration and activation records.

Revision ID: 20260831_0009
Revises: 20260831_0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260831_0009"
down_revision: str | None = "20260831_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("profile_key", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("ruleset_id", sa.String(100), nullable=False),
        sa.Column("ruleset_version", sa.String(32), nullable=False),
        sa.Column("activation_mode", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_by", sa.String(255), nullable=False),
        sa.Column("source_batch_id", sa.String(36), nullable=True, unique=True),
        sa.Column("parameters_json", sa.Text(), nullable=False),
        sa.Column("input_digest", sa.String(64), nullable=False, unique=True),
    )
    op.create_index("ix_ai_profiles_active_version", "ai_profiles", ["status", "version"])
    op.create_table(
        "profile_calibration_preferences",
        sa.Column("operator_id", sa.String(255), primary_key=True),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
        sa.Column("automatic_opt_in", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "profile_governance_audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", sa.String(36), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_profile_governance_audit_aggregate",
        "profile_governance_audit_events",
        ["aggregate_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_profile_governance_audit_aggregate", "profile_governance_audit_events")
    op.drop_table("profile_governance_audit_events")
    op.drop_table("profile_calibration_preferences")
    op.drop_index("ix_ai_profiles_active_version", "ai_profiles")
    op.drop_table("ai_profiles")
