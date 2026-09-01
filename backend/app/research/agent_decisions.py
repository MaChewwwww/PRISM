"""Redacted, durable monitoring snapshots for the seven research specialists."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.research.models import AgentDecisionRecordModel

AGENT_ROSTER = (
    ("news", "News Agent"),
    ("quantitative", "Quantitative Agent"),
    ("industry", "Industry Agent"),
    ("fundamental", "Fundamental Agent"),
    ("macroeconomic", "Macroeconomic Agent"),
    ("market_reaction", "Market Reaction/Mispricing Agent"),
    ("trading_decision", "Trading Decision Agent"),
)


def _text(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    return str(getattr(value, "value", value))


def _items(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, (str, int, float))][:8]


def _snapshot(agent_key: str, report: Any) -> tuple[str, str, list[str], list[str]]:
    if agent_key == "news":
        reports = report if isinstance(report, list) else []
        headline = _text(
            getattr(reports[0], "headline", None) if reports else None, "No news catalyst recorded"
        )
        return (
            headline,
            _text(
                getattr(reports[0], "rationale", None) if reports else None,
                "No durable news analysis was available.",
            ),
            [headline] if reports else [],
            _items(getattr(reports[0], "limitations", []) if reports else []),
        )
    if agent_key == "trading_decision":
        return (
            _text(getattr(report, "verdict", None), "Recorded trading decision"),
            _text(
                getattr(report, "synthesis_rationale", None),
                "No durable synthesis rationale was available.",
            ),
            _items(getattr(report, "evidence_summary", [])),
            _items(getattr(report, "key_risks", [])),
        )
    return (
        _text(
            getattr(report, "summary", None) or getattr(report, "thesis", None),
            "Recorded specialist research",
        ),
        _text(
            getattr(report, "summary", None) or getattr(report, "thesis", None),
            "No durable specialist summary was available.",
        ),
        _items(getattr(report, "evidence", []))
        or _items(getattr(report, "tailwinds", []))
        or _items(getattr(report, "macro_tailwinds", [])),
        _items(getattr(report, "limitations", []))
        or _items(getattr(report, "headwinds", []))
        or _items(getattr(report, "macro_headwinds", [])),
    )


async def persist_agent_decision_snapshots(
    session: AsyncSession,
    *,
    trace_id: UUID,
    symbol: str,
    created_at: datetime,
    reports: dict[str, Any],
    model_name: str | None,
) -> None:
    """Add each snapshot once per trace; callers commit with their decision transaction."""
    existing = set(
        (
            await session.scalars(
                select(AgentDecisionRecordModel.agent_key).where(
                    AgentDecisionRecordModel.trace_id == str(trace_id)
                )
            )
        ).all()
    )
    for key, name in AGENT_ROSTER:
        if key in existing:
            continue
        headline, summary, evidence, limitations = _snapshot(key, reports.get(key))
        digest_input = json.dumps(
            [str(trace_id), key, headline, summary, evidence, limitations], sort_keys=True
        )
        session.add(
            AgentDecisionRecordModel(
                id=str(uuid4()),
                trace_id=str(trace_id),
                proposal_id=None,
                story_id=None,
                created_at=created_at,
                symbol=symbol,
                agent_key=key,
                agent_name=name,
                headline=headline,
                summary=summary,
                evidence_json=json.dumps(evidence),
                limitations_json=json.dumps(limitations),
                model_name=model_name
                if key
                in {"news", "industry", "macroeconomic", "market_reaction", "trading_decision"}
                else None,
                prompt_version=None,
                provenance="live_research",
                source_title=None,
                source_date=None,
                source_digest=None,
                reconstruction_label=None,
                record_digest=hashlib.sha256(digest_input.encode()).hexdigest(),
            )
        )
