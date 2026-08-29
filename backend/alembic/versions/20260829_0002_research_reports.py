"""Add persisted market-reaction research reports.

Revision ID: 20260829_0002
Revises: 20260829_0001
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "20260829_0002"
down_revision: str | None = "20260829_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE_NAME = "research_reports"
_REQUIRED_COLUMNS = {
    "id",
    "trace_id",
    "created_at",
    "schema_version",
    "symbol",
    "article_id",
    "thesis",
    "confidence",
    "freshness_seconds",
    "evidence_json",
    "limitations_json",
    "actual_reaction_pct",
    "expected_reaction_pct",
    "reaction_gap_pct",
    "volume_ratio",
    "classification",
    "opportunity_score",
    "model_name",
    "raw_digest",
}


def _adopt_existing_table_if_compatible() -> bool:
    """Adopt a pre-created report table without dropping or rewriting data."""

    if context.is_offline_mode():
        return False

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(_TABLE_NAME):
        return False

    existing_columns = {column["name"] for column in inspector.get_columns(_TABLE_NAME)}
    missing_columns = sorted(_REQUIRED_COLUMNS - existing_columns)
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise RuntimeError(
            f"Existing {_TABLE_NAME} table is incompatible with migration "
            f"{revision}; missing columns: {missing}"
        )
    return True


def upgrade() -> None:
    if _adopt_existing_table_if_compatible():
        return

    op.create_table(
        _TABLE_NAME,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("trace_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_version", sa.String(length=10), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("article_id", sa.String(length=100), nullable=True),
        sa.Column("thesis", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(), nullable=False),
        sa.Column("freshness_seconds", sa.Integer(), nullable=False),
        sa.Column("evidence_json", sa.Text(), nullable=False),
        sa.Column("limitations_json", sa.Text(), nullable=False),
        sa.Column("actual_reaction_pct", sa.Numeric(), nullable=True),
        sa.Column("expected_reaction_pct", sa.Numeric(), nullable=True),
        sa.Column("reaction_gap_pct", sa.Numeric(), nullable=True),
        sa.Column("volume_ratio", sa.Numeric(), nullable=True),
        sa.Column("classification", sa.String(length=50), nullable=True),
        sa.Column("opportunity_score", sa.Numeric(), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("raw_digest", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("raw_digest"),
    )


def downgrade() -> None:
    op.drop_table(_TABLE_NAME)
