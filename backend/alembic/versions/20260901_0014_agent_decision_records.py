"""Persist redacted agent decision snapshots and Day 1 reconstructions.

Revision ID: 20260901_0014
Revises: 20260831_0013
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from alembic import context, op

revision: str = "20260901_0014"
down_revision: str | None = "20260831_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "agent_decision_records"
_SOURCE_TITLE = "PRISM Day 1 Operations and Performance Report — approved evidence excerpt"
_SOURCE_DATE = datetime(2026, 8, 31, tzinfo=UTC)
_SOURCE_DIGEST = sha256(_SOURCE_TITLE.encode()).hexdigest()
_ROSTER = (
    ("news", "News Agent", "AI infrastructure and data-center demand evidence", "The approved Day 1 report records AI-infrastructure demand and Blackwell backlog as the relevant catalyst context."),
    ("quantitative", "Quantitative Agent", "Momentum with an overbought-RSI caveat", "The report documents positive momentum while noting RSI above 72 as a limitation."),
    ("industry", "Industry Agent", "Blackwell backlog supports sector demand context", "The report identifies Blackwell backlog and data-center demand as sector context."),
    ("fundamental", "Fundamental Agent", "AI capex context supported the review", "The report identifies AI capex as factual context; no original fundamental agent output survives."),
    ("macroeconomic", "Macroeconomic Agent", "Institutional call-flow context was noted", "The report records institutional call-flow and macro context without an original macro transcript."),
    ("market_reaction", "Market Reaction/Mispricing Agent", "Momentum context was reviewed with an overbought caveat", "The report records momentum and the RSI caveat; it does not preserve a reaction-agent invocation."),
    ("trading_decision", "Trading Decision Agent", "Documented NVDA long-call decision", "The approved report documents deterministic EV, spread, and exit gates for the selected long call."),
)
_DECISIONS = (
    ("retrospective-day1-nvda-220", "9c74b0c0-cfa6-5abe-a0a4-478f0f5d5c01", datetime(2026, 8, 31, 17, 10, 25, tzinfo=UTC), "$220 call: entry $4.10, report context $4.15 / +$5"),
    ("retrospective-day1-nvda-225", "f5746126-57f1-5879-bac4-0c72e8dfd3c9", datetime(2026, 8, 31, 18, 10, 39, tzinfo=UTC), "$225 call: entry $1.89, report context $2.11 / +$22"),
)


def _table() -> sa.Table:
    return sa.table(
        _TABLE,
        sa.column("id", sa.String), sa.column("trace_id", sa.String), sa.column("proposal_id", sa.String),
        sa.column("story_id", sa.String), sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("symbol", sa.String), sa.column("agent_key", sa.String), sa.column("agent_name", sa.String),
        sa.column("headline", sa.Text), sa.column("summary", sa.Text), sa.column("evidence_json", sa.Text),
        sa.column("limitations_json", sa.Text), sa.column("model_name", sa.String), sa.column("prompt_version", sa.String),
        sa.column("provenance", sa.String), sa.column("source_title", sa.Text), sa.column("source_date", sa.DateTime(timezone=True)),
        sa.column("source_digest", sa.String), sa.column("reconstruction_label", sa.String), sa.column("record_digest", sa.String),
    )


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("trace_id", sa.String(36), nullable=False),
        sa.Column("proposal_id", sa.String(36)), sa.Column("story_id", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("agent_key", sa.String(40), nullable=False), sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("headline", sa.Text, nullable=False), sa.Column("summary", sa.Text, nullable=False),
        sa.Column("evidence_json", sa.Text, nullable=False), sa.Column("limitations_json", sa.Text, nullable=False),
        sa.Column("model_name", sa.String(100)), sa.Column("prompt_version", sa.String(40)), sa.Column("provenance", sa.String(40), nullable=False),
        sa.Column("source_title", sa.Text), sa.Column("source_date", sa.DateTime(timezone=True)), sa.Column("source_digest", sa.String(64)),
        sa.Column("reconstruction_label", sa.String(80)), sa.Column("record_digest", sa.String(64), nullable=False, unique=True),
        sa.UniqueConstraint("trace_id", "agent_key", name="uq_agent_decision_trace_key"),
        sa.CheckConstraint("provenance IN ('live_research', 'retrospective_reconstruction')", name="ck_agent_decision_provenance"),
        sa.CheckConstraint("provenance != 'retrospective_reconstruction' OR (source_title IS NOT NULL AND source_date IS NOT NULL AND source_digest IS NOT NULL AND reconstruction_label IS NOT NULL)", name="ck_agent_decision_reconstruction_source"),
    )
    op.create_index("ix_agent_decision_records_trace_id", _TABLE, ["trace_id"])
    op.create_index("ix_agent_decision_records_story_id", _TABLE, ["story_id"])
    op.create_index("ix_agent_decision_records_created_at", _TABLE, ["created_at"])
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    records = _table()
    for story_id, trace_id, occurred_at, contract_context in _DECISIONS:
        for key, name, headline, summary in _ROSTER:
            digest = sha256(f"{story_id}:{key}:{_SOURCE_DIGEST}".encode()).hexdigest()
            exists = bind.execute(sa.select(records.c.id).where(records.c.record_digest == digest)).scalar()
            if exists is not None:
                continue
            bind.execute(records.insert().values(
                id=str(uuid5(NAMESPACE_URL, digest)), trace_id=trace_id, proposal_id=None, story_id=story_id,
                created_at=occurred_at, symbol="NVDA", agent_key=key, agent_name=name, headline=headline,
                summary=(summary + " " + contract_context + " was factual context only, not an agent prediction.") if key == "trading_decision" else summary,
                evidence_json='["AI infrastructure/data-center demand", "Blackwell backlog", "AI capex", "institutional call-flow context", "deterministic EV/spread/exit gates"]',
                limitations_json='["Retrospective reconstruction", "Overbought RSI caveat", "No original model invocation or prompt was retained"]',
                model_name=None, prompt_version=None, provenance="retrospective_reconstruction", source_title=_SOURCE_TITLE,
                source_date=_SOURCE_DATE, source_digest=_SOURCE_DIGEST, reconstruction_label="Retrospective reconstruction",
                record_digest=digest,
            ))


def downgrade() -> None:
    op.drop_table(_TABLE)
