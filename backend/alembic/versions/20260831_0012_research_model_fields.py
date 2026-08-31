"""Reconcile fields added to persisted research models after the legacy baseline.

Revision ID: 20260831_0012
Revises: 20260831_0011
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

revision: str = "20260831_0012"
down_revision: str | None = "20260831_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLE_COLUMNS: dict[str, tuple[sa.Column[object], ...]] = {
    "industry_analyses": (
        sa.Column("spy_return_5d_pct", sa.Numeric(), nullable=False, server_default=sa.text("0.0")),
        sa.Column(
            "spy_return_20d_pct", sa.Numeric(), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column(
            "stock_vs_spy_alpha_20d_pct",
            sa.Numeric(),
            nullable=False,
            server_default=sa.text("0.0"),
        ),
        sa.Column(
            "peer_dispersion_20d_pct",
            sa.Numeric(),
            nullable=False,
            server_default=sa.text("0.0"),
        ),
        sa.Column(
            "sector_regime_confirmation",
            sa.String(length=50),
            nullable=False,
            server_default="broad_beta_convergence",
        ),
        sa.Column(
            "peer_reaction_dynamics",
            sa.String(length=50),
            nullable=False,
            server_default="isolated_reaction",
        ),
    ),
    "macro_analyses": (
        sa.Column(
            "market_stress_direction",
            sa.String(length=50),
            nullable=False,
            server_default="stable",
        ),
        sa.Column(
            "realized_volatility_pct",
            sa.Numeric(),
            nullable=False,
            server_default=sa.text("15.0"),
        ),
        sa.Column(
            "volatility_change_5d_pct",
            sa.Numeric(),
            nullable=False,
            server_default=sa.text("0.0"),
        ),
        sa.Column(
            "economic_event_proximity",
            sa.String(length=50),
            nullable=False,
            server_default="standard_calendar",
        ),
        sa.Column(
            "asset_macro_impact",
            sa.String(length=50),
            nullable=False,
            server_default="neutral",
        ),
    ),
    "research_reports": (
        sa.Column("direction_adjusted_gap_pct", sa.Numeric(), nullable=True),
        sa.Column("historical_median_reaction_pct", sa.Numeric(), nullable=True),
        sa.Column("historical_dispersion_pct", sa.Numeric(), nullable=True),
        sa.Column("analog_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "analog_similarity_score",
            sa.Numeric(),
            nullable=False,
            server_default=sa.text("50.0"),
        ),
        sa.Column("historical_volatility_pct", sa.Numeric(), nullable=True),
        sa.Column("implied_volatility_pct", sa.Numeric(), nullable=True),
        sa.Column("iv_hv_ratio", sa.Numeric(), nullable=True),
        sa.Column("options_implied_move_pct", sa.Numeric(), nullable=True),
        sa.Column(
            "event_age_hours",
            sa.Numeric(),
            nullable=False,
            server_default=sa.text("0.0"),
        ),
        sa.Column(
            "catalyst_decay_factor",
            sa.Numeric(),
            nullable=False,
            server_default=sa.text("1.0"),
        ),
        sa.Column(
            "catalyst_decay_status",
            sa.String(length=50),
            nullable=False,
            server_default="fresh_catalyst",
        ),
    ),
    "trade_decisions": (
        sa.Column(
            "evidence_summary_json",
            sa.Text(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "contradictions_json",
            sa.Text(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("portfolio_fit", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "options_only_constraint",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    ),
}


def upgrade() -> None:
    if context.is_offline_mode():
        for table_name, columns in _TABLE_COLUMNS.items():
            for column in columns:
                op.add_column(table_name, column)
        return

    inspector = sa.inspect(op.get_bind())
    for table_name, columns in _TABLE_COLUMNS.items():
        if not inspector.has_table(table_name):
            continue
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        for column in columns:
            if column.name not in existing_columns:
                op.add_column(table_name, column)


def downgrade() -> None:
    if context.is_offline_mode():
        for table_name, columns in reversed(tuple(_TABLE_COLUMNS.items())):
            for column in reversed(columns):
                op.drop_column(table_name, column.name)
        return

    inspector = sa.inspect(op.get_bind())
    for table_name, columns in reversed(tuple(_TABLE_COLUMNS.items())):
        if not inspector.has_table(table_name):
            continue
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        for column in reversed(columns):
            if column.name in existing_columns:
                op.drop_column(table_name, column.name)
