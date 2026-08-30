"""Persist isolated staging historical-simulation records.

Revision ID: 20260830_0007
Revises: 20260830_0006
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260830_0007"
down_revision: str | None = "20260830_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("start_date", sa.String(10), nullable=False),
        sa.Column("end_date", sa.String(10), nullable=False),
        sa.Column("symbols_json", sa.Text(), nullable=False),
        sa.Column("artifact_dir", sa.Text(), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=False),
        sa.Column("is_active_presentation", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "backtest_audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("backtest_audit_events")
    op.drop_table("backtest_runs")
