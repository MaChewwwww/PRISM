"""Persist sourced option IV observations for deterministic IV rank.

Revision ID: 20260830_0006
Revises: 20260830_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260830_0006"
down_revision: str | None = "20260830_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "option_iv_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("underlying", sa.String(20), nullable=False),
        sa.Column("option_symbol", sa.String(64), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("implied_volatility", sa.Numeric(), nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("observation_digest", sa.String(64), nullable=False, unique=True),
    )
    op.create_index(
        "ix_option_iv_observations_underlying_observed_at",
        "option_iv_observations",
        ["underlying", "observed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_option_iv_observations_underlying_observed_at",
        table_name="option_iv_observations",
    )
    op.drop_table("option_iv_observations")
