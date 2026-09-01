"""Record autonomous position closes and structured cycle exit evidence.

Revision ID: 20260901_0015
Revises: 20260901_0014
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260901_0015"
down_revision: str | None = "20260901_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "execution_receipts",
        "proposal_id",
        existing_type=sa.String(36),
        nullable=True,
    )
    op.add_column(
        "execution_receipts",
        sa.Column("operation", sa.String(16), nullable=False, server_default="entry"),
    )
    op.add_column("execution_receipts", sa.Column("symbol", sa.String(64), nullable=True))
    op.add_column("execution_receipts", sa.Column("exit_reason", sa.String(64), nullable=True))
    op.add_column(
        "execution_receipts", sa.Column("requested_quantity", sa.Numeric(), nullable=True)
    )
    op.alter_column(
        "execution_receipts",
        "operation",
        existing_type=sa.String(16),
        server_default=None,
    )
    op.add_column("autonomous_cycles", sa.Column("exit_checks_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("autonomous_cycles", "exit_checks_json")
    op.drop_column("execution_receipts", "requested_quantity")
    op.drop_column("execution_receipts", "exit_reason")
    op.drop_column("execution_receipts", "symbol")
    op.drop_column("execution_receipts", "operation")
    op.alter_column(
        "execution_receipts",
        "proposal_id",
        existing_type=sa.String(36),
        nullable=False,
    )
