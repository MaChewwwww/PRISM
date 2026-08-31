from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BacktestRunModel(Base):
    __tablename__ = "backtest_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    start_date: Mapped[str] = mapped_column(String(10), nullable=False)
    end_date: Mapped[str] = mapped_column(String(10), nullable=False)
    symbols_json: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_dir: Mapped[str] = mapped_column(Text, nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    is_active_presentation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class BacktestAuditEventModel(Base):
    __tablename__ = "backtest_audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
