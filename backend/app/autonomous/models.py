from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AutonomousControlModel(Base):
    """The durable operator control plane for autonomous execution.

    The singleton row is deliberately stored in PostgreSQL so a restart or a
    second backend process cannot silently lose the kill-switch state.
    """

    __tablename__ = "autonomous_controls"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    kill_switch_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class AutonomousCycleModel(Base):
    """Immutable cycle outcome/audit anchor; execution is never implied by a row."""

    __tablename__ = "autonomous_cycles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[Literal["NO_TRADE", "SUBMITTED", "FAILED"]] = mapped_column(
        String(20), nullable=False
    )
    symbols_json: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    exit_checks_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    worker_version: Mapped[str] = mapped_column(String(32), nullable=False)


class AutonomousAuditEventModel(Base):
    __tablename__ = "autonomous_audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ResearchBundleModel(Base):
    __tablename__ = "research_bundles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    bundle_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    is_immutable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TradeProposalModel(Base):
    __tablename__ = "trade_proposals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    proposal_version: Mapped[int] = mapped_column(Integer, nullable=False)
    research_bundle_id: Mapped[str] = mapped_column(String(36), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    proposal_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class RiskAssessmentModel(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    proposal_id: Mapped[str] = mapped_column(String(36), nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class PortfolioSnapshotModel(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    account_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    supported_options_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snapshot_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class OptionIvObservationModel(Base):
    """Timestamped IV observations used to derive a reproducible IV rank.

    The row is immutable and keyed by a digest of the provider payload.  It is
    intentionally separate from portfolio snapshots so a quote refresh can
    build a history without mutating an earlier authorization input.
    """

    __tablename__ = "option_iv_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    underlying: Mapped[str] = mapped_column(String(20), nullable=False)
    option_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    implied_volatility: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    observation_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)


class AuthorizationModel(Base):
    __tablename__ = "authorizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    proposal_id: Mapped[str] = mapped_column(String(36), nullable=False)
    proposal_version: Mapped[int] = mapped_column(Integer, nullable=False)
    proposal_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    ruleset_id: Mapped[str] = mapped_column(String(100), nullable=False)
    ruleset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    profile_id: Mapped[str] = mapped_column(String(36), nullable=False)
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    market_snapshot_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    portfolio_snapshot_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    rule_trace_json: Mapped[str] = mapped_column(Text, nullable=False)


class ReconciliationEventModel(Base):
    __tablename__ = "reconciliation_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    receipt_id: Mapped[str] = mapped_column(String(36), nullable=False)
    transition: Mapped[str] = mapped_column(String(40), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class StrategyPositionModel(Base):
    """Durable parent strategy used for marking, deduplication, and atomic exits."""

    __tablename__ = "strategy_positions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    thesis_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    catalyst_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    underlying: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    strategy_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    strategy_json: Mapped[str] = mapped_column(Text, nullable=False)
    exit_policy_json: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_debit: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    last_liquidation_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    current_return_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    mfe_pct: Mapped[Decimal] = mapped_column(Numeric, nullable=False, default=Decimal("0"))
    profit_armed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score_failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_score_evidence_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_score_evidence_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    exit_latched_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    exit_latched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parent_exit_receipt_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    last_marked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StrategyLifecycleEventModel(Base):
    __tablename__ = "strategy_lifecycle_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    strategy_position_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
