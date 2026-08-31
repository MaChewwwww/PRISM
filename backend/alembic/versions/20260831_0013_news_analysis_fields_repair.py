"""Repair News fields added after the legacy schema migration was applied.

Revision ID: 20260831_0013
Revises: 20260831_0012
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

revision: str = "20260831_0013"
down_revision: str | None = "20260831_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLE_NAME = "llm_event_analyses"
_COLUMNS: tuple[sa.Column[object], ...] = (
    sa.Column("event_age_seconds", sa.Integer(), nullable=False, server_default="0"),
    sa.Column(
        "event_category",
        sa.String(length=50),
        nullable=False,
        server_default="other",
    ),
)


def upgrade() -> None:
    """Add fields whose original migration revision was already applied."""
    if context.is_offline_mode():
        for column in _COLUMNS:
            op.add_column(_TABLE_NAME, column)
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(_TABLE_NAME):
        return

    existing_columns = {column["name"] for column in inspector.get_columns(_TABLE_NAME)}
    for column in _COLUMNS:
        if column.name not in existing_columns:
            op.add_column(_TABLE_NAME, column)


def downgrade() -> None:
    if context.is_offline_mode():
        for column in reversed(_COLUMNS):
            op.drop_column(_TABLE_NAME, column.name)
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(_TABLE_NAME):
        return

    existing_columns = {column["name"] for column in inspector.get_columns(_TABLE_NAME)}
    for column in reversed(_COLUMNS):
        if column.name in existing_columns:
            op.drop_column(_TABLE_NAME, column.name)
