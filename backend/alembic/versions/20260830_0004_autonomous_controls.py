"""Persist autonomous operator controls and cycle audit anchors.

Revision ID: 20260830_0004
Revises: 20260830_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_0004"
down_revision: str | None = "20260830_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "autonomous_controls",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("kill_switch_active", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
    )
    op.create_table(
        "autonomous_cycles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("symbols_json", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("worker_version", sa.String(32), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("autonomous_cycles")
    op.drop_table("autonomous_controls")
