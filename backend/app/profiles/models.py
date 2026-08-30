"""Durable, audited AI Profile governance records.

These records tune only the BA-authorized profile fields.  They are not an
authorization record and cannot relax the deterministic ruleset.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AIProfileModel(Base):
    __tablename__ = "ai_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile_key: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    ruleset_id: Mapped[str] = mapped_column(String(100), nullable=False)
    ruleset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    activation_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activated_by: Mapped[str] = mapped_column(String(255), nullable=False)
    source_batch_id: Mapped[str | None] = mapped_column(String(36), nullable=True, unique=True)
    parameters_json: Mapped[str] = mapped_column(Text, nullable=False)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)


class CalibrationPreferenceModel(Base):
    __tablename__ = "profile_calibration_preferences"

    operator_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)
    automatic_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ProfileGovernanceAuditEventModel(Base):
    __tablename__ = "profile_governance_audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(36), nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
