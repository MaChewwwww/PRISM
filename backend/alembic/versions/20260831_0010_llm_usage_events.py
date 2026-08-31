"""Persist privacy-safe LLM token usage events.

Revision ID: 20260831_0010
Revises: 20260831_0009
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260831_0010"
down_revision: str | None = "20260831_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_usage_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trace_id", sa.String(36), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("model", sa.String(160), nullable=False),
        sa.Column("operation", sa.String(120), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("usage_available", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("raw_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("estimated_cost_usd", sa.Numeric(18, 8), nullable=True),
    )
    op.create_index("ix_llm_usage_events_observed_at", "llm_usage_events", ["observed_at"])
    op.create_index("ix_llm_usage_events_trace_id", "llm_usage_events", ["trace_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_usage_events_trace_id", "llm_usage_events")
    op.drop_index("ix_llm_usage_events_observed_at", "llm_usage_events")
    op.drop_table("llm_usage_events")
