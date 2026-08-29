from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import DateTime, Integer, Numeric, String, Text
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
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False)
    significance_score: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    expected_reaction_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
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
    volume_ratio: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    classification: Mapped[str | None] = mapped_column(String(50), nullable=True)
    opportunity_score: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

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
    relative_alpha_5d_pct: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    relative_alpha_20d_pct: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    sector_relative_performance: Mapped[str] = mapped_column(String(50), nullable=False)
    peer_relative_performance: Mapped[str] = mapped_column(String(50), nullable=False)
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
    macro_climate_score: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    assets_json: Mapped[str] = mapped_column(Text, nullable=False)
    macro_tailwinds_json: Mapped[str] = mapped_column(Text, nullable=False)
    macro_headwinds_json: Mapped[str] = mapped_column(Text, nullable=False)
    stock_macro_sensitivity: Mapped[str] = mapped_column(Text, nullable=False)
    thesis: Mapped[str] = mapped_column(Text, nullable=False)

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
