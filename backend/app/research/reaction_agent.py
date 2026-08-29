from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.models import EvidenceItem, ReactionClassification, ResearchReport
from app.core.llm_gateway import LLMGateway
from app.research.models import ResearchReportModel

PROMPT_VERSION = "1.0"
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a Market Reaction and Mispricing Intelligence Agent for PRISM, a multi-agent trading "
    "intelligence system. Your task is to evaluate whether the market has underreacted, fairly "
    "reacted, or overreacted to a financial catalyst by analyzing computed price movement, volume "
    "surges, and the reaction gap. Output strictly valid JSON matching the schema."
)


class ReactionAnalysisLLMOutput(BaseModel):
    thesis: str = Field(
        description="Comprehensive analytical thesis assessing whether the market is mispriced."
    )
    confidence: Decimal = Field(
        ge=0,
        le=1,
        description="Confidence in the mispricing assessment and thesis, from 0.0 to 1.0.",
    )
    evidence_summaries: list[str] = Field(
        description="Key factual evidence points supporting the reaction gap analysis."
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Key risks, uncertainties, or data limitations in the reaction analysis.",
    )
    classification: Literal["UNDERREACTION", "OVERREACTION", "FAIR_REACTION"] = Field(
        description="Classification: 'UNDERREACTION', 'OVERREACTION', or 'FAIR_REACTION'."
    )


def _freshness_seconds(bars: list[dict[str, Any]], now: datetime) -> int:
    latest_timestamp = bars[-1].get("timestamp") if bars else None
    if not isinstance(latest_timestamp, datetime):
        return 0
    if latest_timestamp.tzinfo is None or latest_timestamp.utcoffset() is None:
        return 0
    return max(0, int((now - latest_timestamp.astimezone(UTC)).total_seconds()))


def compute_reaction_metrics(
    bars: list[dict[str, Any]],
    expected_reaction_pct: Decimal | float | None = None,
) -> dict[str, Any]:
    """Deterministically compute actual price reaction, volume surge, and reaction gap."""
    if not bars:
        return {
            "pre_event_price": None,
            "current_price": None,
            "actual_reaction_pct": Decimal("0.0"),
            "expected_reaction_pct": (
                Decimal(str(expected_reaction_pct))
                if expected_reaction_pct is not None
                else Decimal("0.0")
            ),
            "reaction_gap_pct": Decimal("0.0"),
            "volume_ratio": Decimal("1.0"),
            "classification": "FAIR_REACTION",
            "opportunity_score": Decimal("0.0"),
        }

    # Reference pre-event price is the earliest bar in sample (e.g. 1-day/hour prior)
    pre_price = Decimal(str(bars[0]["close"]))
    if pre_price <= 0:
        raise ValueError("market bar close must be positive")
    # Current price is latest bar close
    current_price = Decimal(str(bars[-1]["close"]))

    actual_reaction = ((current_price - pre_price) / pre_price) * Decimal("100.0")

    expected_reaction = (
        Decimal(str(expected_reaction_pct)) if expected_reaction_pct is not None else Decimal("0.0")
    )

    reaction_gap = expected_reaction - actual_reaction

    # Volume surge ratio: latest bar volume vs average volume of previous bars
    if len(bars) > 1:
        prev_volumes = [Decimal(str(b.get("volume", 0))) for b in bars[:-1]]
        avg_vol = (
            sum(prev_volumes) / Decimal(str(len(prev_volumes))) if prev_volumes else Decimal("1")
        )
        latest_vol = Decimal(str(bars[-1].get("volume", 0)))
        vol_ratio = latest_vol / avg_vol if avg_vol > 0 else Decimal("1.0")
    else:
        vol_ratio = Decimal("1.0")

    # Classification
    if reaction_gap > Decimal("1.5"):
        classification = "UNDERREACTION"
    elif reaction_gap < Decimal("-2.0"):
        classification = "OVERREACTION"
    else:
        classification = "FAIR_REACTION"

    # Opportunity score: 0 to 100
    gap_magnitude = abs(reaction_gap)
    vol_multiplier = min(Decimal("2.0"), max(Decimal("0.5"), vol_ratio))
    raw_score = gap_magnitude * Decimal("20.0") * vol_multiplier
    opp_score = min(Decimal("100.0"), max(Decimal("0.0"), raw_score))

    return {
        "pre_event_price": pre_price,
        "current_price": current_price,
        "actual_reaction_pct": round(actual_reaction, 4),
        "expected_reaction_pct": round(expected_reaction, 4),
        "reaction_gap_pct": round(reaction_gap, 4),
        "volume_ratio": round(vol_ratio, 2),
        "classification": classification,
        "opportunity_score": round(opp_score, 1),
    }


class MarketReactionAgent:
    """Specialist AI agent that evaluates actual market reaction against expected news impact."""

    def __init__(self, llm_gateway: LLMGateway) -> None:
        self.llm_gateway = llm_gateway

    async def analyze_reaction(
        self,
        symbol: str,
        bars: list[dict[str, Any]],
        catalyst_summary: str,
        expected_reaction_pct: Decimal | float | None,
        trace_id: UUID,
        db_session: AsyncSession,
        article_id: str | None = None,
    ) -> ResearchReport:
        """Evaluate the market reaction and produce a formal ResearchReport contract."""
        active_model = self.llm_gateway._settings.llm_model or "default"

        # Check DB cache first
        if article_id:
            try:
                query = select(ResearchReportModel).where(
                    ResearchReportModel.symbol == symbol,
                    ResearchReportModel.article_id == article_id,
                    ResearchReportModel.model_name == active_model,
                )
                result = await db_session.execute(query)
                cached = result.scalar_one_or_none()

                if cached:
                    evidence_raw = json.loads(cached.evidence_json)
                    limitations_raw = json.loads(cached.limitations_json)
                    evidence_items = [
                        EvidenceItem(
                            source=item["source"],
                            summary=item["summary"],
                            observed_at=datetime.fromisoformat(item["observed_at"]),
                            received_at=datetime.fromisoformat(item["received_at"]),
                        )
                        for item in evidence_raw
                    ]
                    return ResearchReport(
                        schema_version=cached.schema_version,
                        id=UUID(cached.id),
                        trace_id=UUID(cached.trace_id),
                        created_at=cached.created_at,
                        symbol=cached.symbol,
                        thesis=cached.thesis,
                        confidence=Decimal(str(cached.confidence)),
                        freshness_seconds=cached.freshness_seconds,
                        evidence=evidence_items,
                        limitations=limitations_raw,
                        actual_reaction_pct=cached.actual_reaction_pct,
                        expected_reaction_pct=cached.expected_reaction_pct,
                        reaction_gap_pct=cached.reaction_gap_pct,
                        volume_ratio=cached.volume_ratio,
                        classification=(
                            ReactionClassification(cached.classification)
                            if cached.classification
                            else None
                        ),
                        opportunity_score=cached.opportunity_score,
                    )
            except Exception:
                # Research caching is best-effort; provider analysis remains usable.
                logger.warning("Market reaction cache read failed for symbol=%s", symbol)

        # Deterministic math calculation
        metrics = compute_reaction_metrics(bars, expected_reaction_pct)

        prompt = (
            f"Analyze the market reaction for ticker: {symbol}\n\n"
            f"Catalyst Event Summary: {catalyst_summary}\n"
            f"Expected Catalyst Price Impact: {metrics['expected_reaction_pct']}%\n"
            f"Actual Measured Price Move: {metrics['actual_reaction_pct']}%\n"
            f"Reaction Gap (Expected - Actual): {metrics['reaction_gap_pct']}%\n"
            f"Volume Surge Ratio: {metrics['volume_ratio']}x normal volume\n"
            f"Preliminary Classification: {metrics['classification']}\n"
            f"Opportunity Score: {metrics['opportunity_score']}/100\n\n"
            f"Evaluate whether this represents an actionable underreaction, panic overreaction, "
            f"or fair pricing, providing an analytical thesis and key limitations."
        )

        completion = await self.llm_gateway.complete_structured(
            prompt=prompt,
            response_model=ReactionAnalysisLLMOutput,
            system_prompt=SYSTEM_PROMPT,
            trace_id=trace_id,
        )

        parsed = completion.parsed
        if not parsed:
            raise ValueError("Failed to obtain valid parsed output from LLM gateway")

        now_utc = datetime.now(UTC)
        evidence_items = [
            EvidenceItem(
                source="alpaca_market_data",
                summary=(
                    f"Price moved {metrics['actual_reaction_pct']}% with "
                    f"{metrics['volume_ratio']}x volume surge"
                ),
                observed_at=now_utc,
                received_at=now_utc,
            ),
            EvidenceItem(
                source="news_catalyst",
                summary=catalyst_summary[:200],
                observed_at=now_utc,
                received_at=now_utc,
            ),
        ]
        for summary_text in parsed.evidence_summaries:
            evidence_items.append(
                EvidenceItem(
                    source="reaction_analyst",
                    summary=summary_text,
                    observed_at=now_utc,
                    received_at=now_utc,
                )
            )

        report = ResearchReport(
            id=uuid4(),
            trace_id=trace_id,
            created_at=now_utc,
            symbol=symbol,
            thesis=parsed.thesis,
            confidence=Decimal(str(round(parsed.confidence, 4))),
            freshness_seconds=_freshness_seconds(bars, now_utc),
            evidence=evidence_items,
            limitations=parsed.limitations,
            actual_reaction_pct=metrics["actual_reaction_pct"],
            expected_reaction_pct=metrics["expected_reaction_pct"],
            reaction_gap_pct=metrics["reaction_gap_pct"],
            volume_ratio=metrics["volume_ratio"],
            classification=ReactionClassification(metrics["classification"]),
            opportunity_score=metrics["opportunity_score"],
        )

        # Write to PostgreSQL DB cache
        try:
            db_model = ResearchReportModel(
                id=str(report.id),
                trace_id=str(report.trace_id),
                created_at=report.created_at,
                schema_version=report.schema_version,
                symbol=symbol,
                article_id=article_id,
                thesis=report.thesis,
                confidence=report.confidence,
                freshness_seconds=report.freshness_seconds,
                evidence_json=json.dumps(
                    [
                        {
                            "source": e.source,
                            "summary": e.summary,
                            "observed_at": e.observed_at.isoformat(),
                            "received_at": e.received_at.isoformat(),
                        }
                        for e in report.evidence
                    ]
                ),
                limitations_json=json.dumps(report.limitations),
                actual_reaction_pct=metrics["actual_reaction_pct"],
                expected_reaction_pct=metrics["expected_reaction_pct"],
                reaction_gap_pct=metrics["reaction_gap_pct"],
                volume_ratio=metrics["volume_ratio"],
                classification=metrics["classification"],
                opportunity_score=metrics["opportunity_score"],
                model_name=completion.model,
                raw_digest=completion.raw_digest,
            )
            db_session.add(db_model)
            await db_session.commit()
        except Exception:
            # A cache write must never turn a non-authoritative research result into an error.
            await db_session.rollback()
            logger.warning("Market reaction cache write failed for symbol=%s", symbol)

        return report
