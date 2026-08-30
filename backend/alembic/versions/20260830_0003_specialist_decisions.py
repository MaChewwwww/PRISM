"""Persist industry, macro, and trading-decision research reports.

Revision ID: 20260830_0003
Revises: 20260829_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_0003"
down_revision: str | None = "20260829_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "industry_analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_version", sa.String(10), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("sector_name", sa.String(100), nullable=False),
        sa.Column("sector_etf", sa.String(20), nullable=False),
        sa.Column("stock_return_5d_pct", sa.Numeric(), nullable=False),
        sa.Column("stock_return_20d_pct", sa.Numeric(), nullable=False),
        sa.Column("sector_return_5d_pct", sa.Numeric(), nullable=False),
        sa.Column("sector_return_20d_pct", sa.Numeric(), nullable=False),
        sa.Column("relative_alpha_5d_pct", sa.Numeric(), nullable=False),
        sa.Column("relative_alpha_20d_pct", sa.Numeric(), nullable=False),
        sa.Column("sector_relative_performance", sa.String(50), nullable=False),
        sa.Column("peer_relative_performance", sa.String(50), nullable=False),
        sa.Column("peers_json", sa.Text(), nullable=False),
        sa.Column("sector_health_score", sa.Numeric(), nullable=False),
        sa.Column("competitive_moat", sa.String(50), nullable=False),
        sa.Column("overall_sentiment", sa.String(50), nullable=False),
        sa.Column("tailwinds_json", sa.Text(), nullable=False),
        sa.Column("headwinds_json", sa.Text(), nullable=False),
        sa.Column("thesis", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("raw_digest", sa.String(64), nullable=False, unique=True),
    )
    op.create_table(
        "macro_analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_version", sa.String(10), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("macro_regime", sa.String(50), nullable=False),
        sa.Column("rate_environment", sa.String(50), nullable=False),
        sa.Column("market_stress_level", sa.String(50), nullable=False),
        sa.Column("macro_climate_score", sa.Numeric(), nullable=False),
        sa.Column("assets_json", sa.Text(), nullable=False),
        sa.Column("macro_tailwinds_json", sa.Text(), nullable=False),
        sa.Column("macro_headwinds_json", sa.Text(), nullable=False),
        sa.Column("stock_macro_sensitivity", sa.Text(), nullable=False),
        sa.Column("thesis", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("raw_digest", sa.String(64), nullable=False, unique=True),
    )
    op.create_table(
        "trade_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_version", sa.String(10), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("verdict", sa.String(50), nullable=False),
        sa.Column("direction", sa.String(50), nullable=False),
        sa.Column("recommended_structure", sa.String(50), nullable=False),
        sa.Column("composite_opportunity_score", sa.Numeric(), nullable=False),
        sa.Column("net_ev_r", sa.Numeric(), nullable=False),
        sa.Column("reward_risk_ratio", sa.Numeric(), nullable=False),
        sa.Column("confidence_score", sa.Numeric(), nullable=False),
        sa.Column("current_price", sa.Numeric(), nullable=False),
        sa.Column("target_price", sa.Numeric(), nullable=True),
        sa.Column("exit_policy_json", sa.Text(), nullable=False),
        sa.Column("specialist_scores_json", sa.Text(), nullable=False),
        sa.Column("synthesis_rationale", sa.Text(), nullable=False),
        sa.Column("contradiction_analysis", sa.Text(), nullable=False),
        sa.Column("key_risks_json", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("raw_digest", sa.String(64), nullable=False, unique=True),
    )


def downgrade() -> None:
    op.drop_table("trade_decisions")
    op.drop_table("macro_analyses")
    op.drop_table("industry_analyses")
