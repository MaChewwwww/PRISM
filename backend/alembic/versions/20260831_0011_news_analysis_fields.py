"""Add fields used by the persisted News Intelligence analysis model.

Revision ID: 20260831_0011
Revises: 20260831_0010
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

revision: str = "20260831_0011"
down_revision: str | None = "20260831_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLE_NAME = "llm_event_analyses"


def _columns() -> tuple[sa.Column[object], ...]:
    return (
        sa.Column("source", sa.String(length=100), nullable=False, server_default="unknown"),
        sa.Column(
            "source_confidence",
            sa.Numeric(),
            nullable=False,
            server_default=sa.text("50.0"),
        ),
        sa.Column(
            "catalyst_materiality",
            sa.String(length=50),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "guidance_change",
            sa.String(length=50),
            nullable=False,
            server_default="not_applicable",
        ),
        sa.Column("earnings_surprise_json", sa.Text(), nullable=True),
        sa.Column(
            "has_contradictory_signals",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("contradiction_notes", sa.Text(), nullable=True),
    )


def upgrade() -> None:
    """Bring adopted legacy news-analysis tables up to the current model shape."""
    if context.is_offline_mode():
        for column in _columns():
            op.add_column(_TABLE_NAME, column)
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(_TABLE_NAME):
        return

    existing_columns = {column["name"] for column in inspector.get_columns(_TABLE_NAME)}
    for column in _columns():
        if column.name not in existing_columns:
            op.add_column(_TABLE_NAME, column)


def downgrade() -> None:
    if context.is_offline_mode():
        for name in (
            "contradiction_notes",
            "has_contradictory_signals",
            "earnings_surprise_json",
            "guidance_change",
            "catalyst_materiality",
            "source_confidence",
            "source",
        ):
            op.drop_column(_TABLE_NAME, name)
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(_TABLE_NAME):
        return

    existing_columns = {column["name"] for column in inspector.get_columns(_TABLE_NAME)}
    for name in (
        "contradiction_notes",
        "has_contradictory_signals",
        "earnings_surprise_json",
        "guidance_change",
        "catalyst_materiality",
        "source_confidence",
        "source",
    ):
        if name in existing_columns:
            op.drop_column(_TABLE_NAME, name)
