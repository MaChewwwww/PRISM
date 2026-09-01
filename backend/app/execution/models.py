from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ExecutionReceiptModel(Base):
    """Durable broker-submission receipt keyed by persisted client order ID."""

    __tablename__ = "execution_receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    proposal_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    client_order_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    broker_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    operation: Mapped[str] = mapped_column(String(16), nullable=False, default="entry")
    symbol: Mapped[str | None] = mapped_column(String(64), nullable=True)
    exit_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requested_quantity: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    filled_quantity: Mapped[Decimal] = mapped_column(Numeric, nullable=False, default=0)
    filled_average_price: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
