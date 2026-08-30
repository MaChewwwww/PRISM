"""Immutable persistence roots for non-executable ShadowFund evaluation."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ShadowSessionModel(Base):
    __tablename__ = "shadow_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evaluation_root_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    terminal_outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    proposal_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    authorization_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    backtest_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    source_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    source_feed: Mapped[str] = mapped_column(String(40), nullable=False)
    valuation_policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    exit_policy_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ruleset_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    profile_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    refusal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    horizon_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ShadowBranchModel(Base):
    __tablename__ = "shadow_branches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    branch_key: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    variation: Mapped[str] = mapped_column(Text, nullable=False)
    strategy_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    allocation_multiplier: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    entry_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    entry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    chosen_path: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ShadowObservationModel(Base):
    __tablename__ = "shadow_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    feed: Mapped[str] = mapped_column(String(40), nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ShadowValuationModel(Base):
    __tablename__ = "shadow_valuations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    branch_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    gross_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    net_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    drawdown: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    mae: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    mfe: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    capital_at_risk: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    coverage_pct: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    exit_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)


class ShadowPostAnalysisBatchModel(Base):
    __tablename__ = "shadow_post_analysis_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    model_metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)


class ShadowProfileRecommendationModel(Base):
    __tablename__ = "shadow_profile_recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    parameter_id: Mapped[str] = mapped_column(String(80), nullable=False)
    current_value: Mapped[str] = mapped_column(String(40), nullable=False)
    suggested_value: Mapped[str] = mapped_column(String(40), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    validation_state: Mapped[str] = mapped_column(String(40), nullable=False)
    manual_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
