"""Create the initial PRISM news-analysis cache schema.

Revision ID: 20260829_0001
Revises:
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "20260829_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLE_NAME = "llm_event_analyses"
_REQUIRED_COLUMNS = {
    "id",
    "trace_id",
    "created_at",
    "schema_version",
    "article_id",
    "symbol",
    "headline",
    "event_type",
    "sentiment",
    "significance_score",
    "expected_reaction_pct",
    "rationale",
    "model_name",
    "prompt_version",
    "raw_digest",
}


def _adopt_legacy_table_if_compatible() -> bool:
    """Return True when the pre-Alembic table can be adopted safely.

    Earlier staging revisions created this table with ``Base.metadata.create_all``.
    Those databases have the complete schema but no ``alembic_version`` row.  The
    baseline must record its revision without attempting to recreate the table;
    an incompatible table fails closed so a later migration can be authored.
    """

    # Offline SQL generation has no database to inspect; emit the baseline DDL.
    if context.is_offline_mode():
        return False

    bind = op.get_bind()
    inspector = sa.inspect(bind)
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
    if _adopt_legacy_table_if_compatible():
        return

    op.create_table(
        _TABLE_NAME,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("trace_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_version", sa.String(length=10), nullable=False),
        sa.Column("article_id", sa.String(length=100), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("headline", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("sentiment", sa.String(length=20), nullable=False),
        sa.Column("significance_score", sa.Numeric(), nullable=False),
        sa.Column("expected_reaction_pct", sa.Numeric(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=20), nullable=False),
        sa.Column("raw_digest", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("raw_digest"),
    )


def downgrade() -> None:
    op.drop_table(_TABLE_NAME)
