from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LLMEventAnalysisModel(Base):
    __tablename__ = "llm_event_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    schema_version: Mapped[Literal["1.0"]] = mapped_column(
        String(10), nullable=False, default="1.0"
    )

    article_id: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    headline: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")
    source_confidence: Mapped[Decimal] = mapped_column(
        Numeric, nullable=False, default=Decimal("50.0")
    )
    event_age_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    event_category: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    catalyst_materiality: Mapped[str] = mapped_column(String(50), nullable=False, default="medium")
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False)
    significance_score: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    expected_reaction_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    guidance_change: Mapped[str] = mapped_column(
        String(50), nullable=False, default="not_applicable"
    )
    earnings_surprise_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_contradictory_signals: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contradiction_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    raw_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)


class ResearchReportModel(Base):
    __tablename__ = "research_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    schema_version: Mapped[Literal["1.0"]] = mapped_column(
        String(10), nullable=False, default="1.0"
    )

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    article_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    thesis: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    freshness_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    limitations_json: Mapped[str] = mapped_column(Text, nullable=False)

    actual_reaction_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    expected_reaction_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    reaction_gap_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    direction_adjusted_gap_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    volume_ratio: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    classification: Mapped[str | None] = mapped_column(String(50), nullable=True)
    opportunity_score: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    historical_median_reaction_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    historical_dispersion_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    analog_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analog_similarity_score: Mapped[Decimal] = mapped_column(
        Numeric, nullable=False, default=Decimal("50.0")
    )
    historical_volatility_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    implied_volatility_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    iv_hv_ratio: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    options_implied_move_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    event_age_hours: Mapped[Decimal] = mapped_column(
        Numeric, nullable=False, default=Decimal("0.0")
    )
    catalyst_decay_factor: Mapped[Decimal] = mapped_column(
        Numeric, nullable=False, default=Decimal("1.0")
    )
    catalyst_decay_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="fresh_catalyst"
    )

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)


class IndustryAnalysisModel(Base):
    __tablename__ = "industry_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    schema_version: Mapped[Literal["1.0"]] = mapped_column(
        String(10), nullable=False, default="1.0"
    )

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    sector_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sector_etf: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_return_5d_pct: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    stock_return_20d_pct: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    sector_return_5d_pct: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    sector_return_20d_pct: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    spy_return_5d_pct: Mapped[Decimal] = mapped_column(
        Numeric, nullable=False, default=Decimal("0.0")
    )
    spy_return_20d_pct: Mapped[Decimal] = mapped_column(
        Numeric, nullable=False, default=Decimal("0.0")
    )
    relative_alpha_5d_pct: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    relative_alpha_20d_pct: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    stock_vs_spy_alpha_20d_pct: Mapped[Decimal] = mapped_column(
        Numeric, nullable=False, default=Decimal("0.0")
    )
    peer_dispersion_20d_pct: Mapped[Decimal] = mapped_column(
        Numeric, nullable=False, default=Decimal("0.0")
    )
    sector_relative_performance: Mapped[str] = mapped_column(String(50), nullable=False)
    peer_relative_performance: Mapped[str] = mapped_column(String(50), nullable=False)
    sector_regime_confirmation: Mapped[str] = mapped_column(
        String(50), nullable=False, default="broad_beta_convergence"
    )
    peer_reaction_dynamics: Mapped[str] = mapped_column(
        String(50), nullable=False, default="isolated_reaction"
    )
    peers_json: Mapped[str] = mapped_column(Text, nullable=False)
    sector_health_score: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    competitive_moat: Mapped[str] = mapped_column(String(50), nullable=False)
    overall_sentiment: Mapped[str] = mapped_column(String(50), nullable=False)
    tailwinds_json: Mapped[str] = mapped_column(Text, nullable=False)
    headwinds_json: Mapped[str] = mapped_column(Text, nullable=False)
    thesis: Mapped[str] = mapped_column(Text, nullable=False)

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)


class MacroAnalysisModel(Base):
    __tablename__ = "macro_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    schema_version: Mapped[Literal["1.0"]] = mapped_column(
        String(10), nullable=False, default="1.0"
    )

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    macro_regime: Mapped[str] = mapped_column(String(50), nullable=False)
    rate_environment: Mapped[str] = mapped_column(String(50), nullable=False)
    market_stress_level: Mapped[str] = mapped_column(String(50), nullable=False)
    market_stress_direction: Mapped[str] = mapped_column(
        String(50), nullable=False, default="stable"
    )
    realized_volatility_pct: Mapped[Decimal] = mapped_column(
        Numeric, nullable=False, default=Decimal("15.0")
    )
    volatility_change_5d_pct: Mapped[Decimal] = mapped_column(
        Numeric, nullable=False, default=Decimal("0.0")
    )
    macro_climate_score: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    economic_event_proximity: Mapped[str] = mapped_column(
        String(50), nullable=False, default="standard_calendar"
    )
    asset_macro_impact: Mapped[str] = mapped_column(String(50), nullable=False, default="neutral")
    assets_json: Mapped[str] = mapped_column(Text, nullable=False)
    macro_tailwinds_json: Mapped[str] = mapped_column(Text, nullable=False)
    macro_headwinds_json: Mapped[str] = mapped_column(Text, nullable=False)
    stock_macro_sensitivity: Mapped[str] = mapped_column(Text, nullable=False)
    thesis: Mapped[str] = mapped_column(Text, nullable=False)

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)


class TradeDecisionModel(Base):
    __tablename__ = "trade_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    schema_version: Mapped[Literal["1.0"]] = mapped_column(
        String(10), nullable=False, default="1.0"
    )

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    verdict: Mapped[str] = mapped_column(String(50), nullable=False)
    direction: Mapped[str] = mapped_column(String(50), nullable=False)
    recommended_structure: Mapped[str] = mapped_column(String(50), nullable=False)
    composite_opportunity_score: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    net_ev_r: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    reward_risk_ratio: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    target_price: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

    exit_policy_json: Mapped[str] = mapped_column(Text, nullable=False)
    specialist_scores_json: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    contradictions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    contradiction_analysis: Mapped[str] = mapped_column(Text, nullable=False)
    portfolio_fit: Mapped[str] = mapped_column(Text, nullable=False, default="")
    options_only_constraint: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    synthesis_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    key_risks_json: Mapped[str] = mapped_column(Text, nullable=False)

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)


class AgentDecisionRecordModel(Base):
    """Redacted, append-only specialist snapshot for monitoring read models.

    This deliberately stores the decision-facing summary only. Prompts, provider
    payloads, chain-of-thought, credentials, and broker payloads stay outside
    this boundary.
    """

    __tablename__ = "agent_decision_records"
    __table_args__ = (
        UniqueConstraint("trace_id", "agent_key", name="uq_agent_decision_trace_key"),
        CheckConstraint(
            "provenance IN ('live_research', 'retrospective_reconstruction')",
            name="ck_agent_decision_provenance",
        ),
        CheckConstraint(
            "provenance != 'retrospective_reconstruction' OR "
            "(source_title IS NOT NULL AND source_date IS NOT NULL AND source_digest IS NOT NULL "
            "AND reconstruction_label IS NOT NULL)",
            name="ck_agent_decision_reconstruction_source",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    proposal_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    story_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    agent_key: Mapped[str] = mapped_column(String(40), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    limitations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    provenance: Mapped[str] = mapped_column(String(40), nullable=False)
    source_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reconstruction_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    record_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
