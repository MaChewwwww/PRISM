"""Persist proposal, risk, authorization, portfolio and execution audit roots.

Revision ID: 20260830_0005
Revises: 20260830_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_0005"
down_revision: str | None = "20260830_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_bundles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("bundle_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("is_immutable", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "trade_proposals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("proposal_version", sa.Integer(), nullable=False),
        sa.Column("research_bundle_id", sa.String(36), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("proposal_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "risk_assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("proposal_id", sa.String(36), nullable=False),
        sa.Column("verdict", sa.String(32), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("account_verified", sa.Boolean(), nullable=False),
        sa.Column("supported_options_level", sa.Integer(), nullable=True),
        sa.Column("snapshot_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "authorizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("proposal_id", sa.String(36), nullable=False),
        sa.Column("proposal_version", sa.Integer(), nullable=False),
        sa.Column("proposal_digest", sa.String(64), nullable=False),
        sa.Column("ruleset_id", sa.String(100), nullable=False),
        sa.Column("ruleset_version", sa.String(32), nullable=False),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(40), nullable=False),
        sa.Column("market_snapshot_digest", sa.String(64), nullable=False),
        sa.Column("portfolio_snapshot_digest", sa.String(64), nullable=False),
        sa.Column("decision_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("rule_trace_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "execution_receipts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(36), nullable=False),
        sa.Column("proposal_id", sa.String(36), nullable=False),
        sa.Column("client_order_id", sa.String(128), nullable=False, unique=True),
        sa.Column("broker_order_id", sa.String(128), nullable=True),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("filled_quantity", sa.Numeric(), nullable=False),
        sa.Column("filled_average_price", sa.Numeric(), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_execution_receipts_payload_digest", "execution_receipts", ["payload_digest"]
    )
    op.create_table(
        "reconciliation_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("receipt_id", sa.String(36), nullable=False),
        sa.Column("transition", sa.String(40), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "autonomous_audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("aggregate_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("autonomous_audit_events")
    op.drop_table("reconciliation_events")
    op.drop_index("ix_execution_receipts_payload_digest", table_name="execution_receipts")
    op.drop_table("execution_receipts")
    op.drop_table("authorizations")
    op.drop_table("portfolio_snapshots")
    op.drop_table("risk_assessments")
    op.drop_table("trade_proposals")
    op.drop_table("research_bundles")
