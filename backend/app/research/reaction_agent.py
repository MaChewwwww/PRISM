from __future__ import annotations

import json
import logging
import math
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.models import (
    CatalystDecayStatus,
    EvidenceItem,
    NewsEventCategory,
    ReactionClassification,
    ResearchReport,
)
from app.core.llm_gateway import LLMGateway
from app.research.models import ResearchReportModel

PROMPT_VERSION = "1.0"
logger = logging.getLogger(__name__)

# Event Category benchmark distributions:
# (median_reaction_pct, dispersion_pct, default_analog_count, half_life_hours)
HISTORICAL_ANALOG_BENCHMARKS: dict[NewsEventCategory, tuple[Decimal, Decimal, int, float]] = {
    NewsEventCategory.EARNINGS: (Decimal("4.5"), Decimal("3.2"), 16, 24.0),
    NewsEventCategory.GUIDANCE: (Decimal("5.2"), Decimal("3.8"), 12, 36.0),
    NewsEventCategory.PRODUCT_INNOVATION: (Decimal("3.2"), Decimal("2.4"), 10, 48.0),
    NewsEventCategory.M_AND_A: (Decimal("8.5"), Decimal("5.1"), 6, 72.0),
    NewsEventCategory.REGULATORY_LEGAL: (Decimal("4.0"), Decimal("4.5"), 8, 48.0),
    NewsEventCategory.ANALYST_ACTION: (Decimal("2.1"), Decimal("1.8"), 24, 18.0),
    NewsEventCategory.MANAGEMENT_CHANGE: (Decimal("2.8"), Decimal("2.2"), 8, 24.0),
    NewsEventCategory.MACRO_GEOPOLITICAL: (Decimal("1.9"), Decimal("1.5"), 20, 12.0),
    NewsEventCategory.ROUTINE_PR: (Decimal("0.8"), Decimal("0.9"), 30, 8.0),
    NewsEventCategory.OTHER: (Decimal("1.5"), Decimal("1.5"), 10, 24.0),
}


SYSTEM_PROMPT = (
    "You are a Market Reaction and Mispricing Intelligence Agent for PRISM, a multi-agent trading "
    "intelligence system. Your task is to evaluate whether the market has underreacted, fairly "
    "reacted, or overreacted to a financial catalyst by analyzing computed price movement, "
    "direction-adjusted gap, historical analogs, options implied move, and catalyst decay. "
    "Output strictly valid JSON matching the schema."
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

    @field_validator("limitations", "evidence_summaries", mode="before")
    @classmethod
    def _coerce_list(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [v.strip()]
        if isinstance(v, (list, tuple)):
            return [str(x).strip() for x in v]
        return []


def _freshness_seconds(bars: list[dict[str, Any]], now: datetime) -> int:
    latest_timestamp = bars[-1].get("timestamp") if bars else None
    if not isinstance(latest_timestamp, datetime):
        return 10**9
    if latest_timestamp.tzinfo is None or latest_timestamp.utcoffset() is None:
        return 10**9
    return max(0, int((now - latest_timestamp.astimezone(UTC)).total_seconds()))


def compute_catalyst_decay(
    event_age_seconds: int,
    half_life_hours: float = 24.0,
) -> tuple[Decimal, Decimal, CatalystDecayStatus]:
    """Compute exponential alpha decay factor and classification from event age in seconds."""
    age_hours = max(Decimal("0.0"), round(Decimal(str(event_age_seconds)) / Decimal("3600.0"), 2))
    hours_float = float(age_hours)
    hl = max(1.0, half_life_hours)
    decay_raw = math.pow(2.0, -hours_float / hl)
    decay_factor = Decimal(str(round(max(0.01, min(1.0, decay_raw)), 3)))

    if hours_float < 4.0:
        status = CatalystDecayStatus.FRESH_CATALYST
    elif hours_float < 24.0:
        status = CatalystDecayStatus.ACTIVE_DIGESTION
    elif hours_float < 72.0:
        status = CatalystDecayStatus.AGING_CATALYST
    else:
        status = CatalystDecayStatus.PRICED_IN

    return age_hours, decay_factor, status


def compute_volatility_and_implied_move(
    bars: list[dict[str, Any]],
    expected_reaction_pct: Decimal = Decimal("0.0"),
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Calculate historical realized vol, event-calibrated IV, IV/HV, and options implied move."""
    if len(bars) < 5:
        return Decimal("25.0"), Decimal("30.0"), Decimal("1.20"), Decimal("2.8")

    closes = [float(b["close"]) for b in bars if "close" in b]
    returns = [
        (closes[i] - closes[i - 1]) / closes[i - 1]
        for i in range(1, len(closes))
        if closes[i - 1] > 0
    ]
    if not returns:
        return Decimal("25.0"), Decimal("30.0"), Decimal("1.20"), Decimal("2.8")

    mean_ret = sum(returns) / len(returns)
    variance = sum((r - mean_ret) ** 2 for r in returns) / max(1, len(returns) - 1)
    hv_annualized = math.sqrt(variance) * math.sqrt(252) * 100.0
    hv_dec = max(Decimal("10.0"), round(Decimal(str(hv_annualized)), 1))

    event_vol_premium = max(
        Decimal("1.10"), Decimal("1.0") + (abs(expected_reaction_pct) / Decimal("20.0"))
    )
    iv_dec = round(hv_dec * event_vol_premium, 1)
    iv_hv_ratio = round(iv_dec / hv_dec, 2)

    daily_implied_move = float(iv_dec) * math.sqrt(1.0 / 252.0) * 0.84
    implied_move_dec = max(Decimal("0.5"), round(Decimal(str(daily_implied_move)), 2))

    return hv_dec, iv_dec, iv_hv_ratio, implied_move_dec


def compute_reaction_metrics(
    bars: list[dict[str, Any]],
    expected_reaction_pct: Decimal | float | None = None,
    event_age_seconds: int = 0,
    event_category: NewsEventCategory = NewsEventCategory.OTHER,
) -> dict[str, Any]:
    """Deterministically compute reaction gap, direction-adjusted gap, analogs, and decay."""
    exp_dec = (
        Decimal(str(expected_reaction_pct)) if expected_reaction_pct is not None else Decimal("0.0")
    )

    median_analog, dispersion_analog, analog_count, half_life = HISTORICAL_ANALOG_BENCHMARKS.get(
        event_category,
        (Decimal("2.0"), Decimal("2.0"), 10, 24.0),
    )

    age_hours, decay_factor, decay_status = compute_catalyst_decay(event_age_seconds, half_life)
    hv, iv, iv_hv_ratio, implied_move = compute_volatility_and_implied_move(bars, exp_dec)

    if not bars:
        return {
            "pre_event_price": None,
            "current_price": None,
            "actual_reaction_pct": Decimal("0.0"),
            "expected_reaction_pct": exp_dec,
            "reaction_gap_pct": Decimal("0.0"),
            "direction_adjusted_gap_pct": Decimal("0.0"),
            "volume_ratio": Decimal("1.0"),
            "classification": "FAIR_REACTION",
            "opportunity_score": Decimal("0.0"),
            "historical_median_reaction_pct": median_analog,
            "historical_dispersion_pct": dispersion_analog,
            "analog_count": analog_count,
            "analog_similarity_score": Decimal("50.0"),
            "historical_volatility_pct": hv,
            "implied_volatility_pct": iv,
            "iv_hv_ratio": iv_hv_ratio,
            "options_implied_move_pct": implied_move,
            "event_age_hours": age_hours,
            "catalyst_decay_factor": decay_factor,
            "catalyst_decay_status": decay_status,
        }

    pre_price = Decimal(str(bars[0]["close"]))
    if pre_price <= 0:
        raise ValueError("market bar close must be positive")
    current_price = Decimal(str(bars[-1]["close"]))

    actual_reaction = ((current_price - pre_price) / pre_price) * Decimal("100.0")

    reaction_gap = exp_dec - actual_reaction

    if exp_dec >= Decimal("0.0"):
        direction_adjusted_gap = exp_dec - actual_reaction
    else:
        direction_adjusted_gap = -(exp_dec - actual_reaction)

    lookback_bars = bars[-21:-1] if len(bars) > 20 else bars[:-1]
    if lookback_bars:
        prev_volumes = [Decimal(str(b.get("volume", 0))) for b in lookback_bars]
        avg_vol = sum(prev_volumes) / Decimal(str(len(prev_volumes)))
        latest_vol = Decimal(str(bars[-1].get("volume", 0)))
        vol_ratio = latest_vol / avg_vol if avg_vol > Decimal("0") else Decimal("1.0")
    else:
        vol_ratio = Decimal("1.0")

    if direction_adjusted_gap > Decimal("1.5"):
        classification = "UNDERREACTION"
    elif direction_adjusted_gap < Decimal("-2.0"):
        classification = "OVERREACTION"
    else:
        classification = "FAIR_REACTION"

    diff_from_median = abs(abs(actual_reaction) - median_analog)
    similarity_norm = max(Decimal("0.0"), Decimal("100.0") - (diff_from_median * Decimal("15.0")))
    analog_sim_score = round(similarity_norm, 1)

    gap_magnitude = abs(direction_adjusted_gap)
    vol_multiplier = min(Decimal("2.0"), max(Decimal("0.5"), vol_ratio))
    raw_score = gap_magnitude * Decimal("20.0") * vol_multiplier * decay_factor
    opp_score = min(Decimal("100.0"), max(Decimal("0.0"), raw_score))

    return {
        "pre_event_price": pre_price,
        "current_price": current_price,
        "actual_reaction_pct": round(actual_reaction, 4),
        "expected_reaction_pct": round(exp_dec, 4),
        "reaction_gap_pct": round(reaction_gap, 4),
        "direction_adjusted_gap_pct": round(direction_adjusted_gap, 4),
        "volume_ratio": round(vol_ratio, 2),
        "classification": classification,
        "opportunity_score": round(opp_score, 1),
        "historical_median_reaction_pct": median_analog,
        "historical_dispersion_pct": dispersion_analog,
        "analog_count": analog_count,
        "analog_similarity_score": analog_sim_score,
        "historical_volatility_pct": hv,
        "implied_volatility_pct": iv,
        "iv_hv_ratio": iv_hv_ratio,
        "options_implied_move_pct": implied_move,
        "event_age_hours": age_hours,
        "catalyst_decay_factor": decay_factor,
        "catalyst_decay_status": decay_status,
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
        db_session: AsyncSession | None = None,
        article_id: str | None = None,
        event_age_seconds: int = 0,
        event_category: NewsEventCategory = NewsEventCategory.OTHER,
        *,
        strict: bool = False,
    ) -> ResearchReport:
        """Evaluate the market reaction and produce a formal ResearchReport contract."""
        active_model = self.llm_gateway._settings.llm_model or "default"

        # Check DB cache first
        if article_id and db_session is not None and not strict:
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
                    decay_status_raw = getattr(cached, "catalyst_decay_status", None)
                    decay_status = (
                        CatalystDecayStatus(decay_status_raw)
                        if decay_status_raw
                        else CatalystDecayStatus.FRESH_CATALYST
                    )

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
                        direction_adjusted_gap_pct=getattr(
                            cached, "direction_adjusted_gap_pct", None
                        ),
                        volume_ratio=cached.volume_ratio,
                        classification=(
                            ReactionClassification(cached.classification)
                            if cached.classification
                            else None
                        ),
                        opportunity_score=cached.opportunity_score,
                        historical_median_reaction_pct=getattr(
                            cached, "historical_median_reaction_pct", None
                        ),
                        historical_dispersion_pct=getattr(
                            cached, "historical_dispersion_pct", None
                        ),
                        analog_count=getattr(cached, "analog_count", 0) or 0,
                        analog_similarity_score=getattr(cached, "analog_similarity_score", None)
                        or Decimal("50.0"),
                        historical_volatility_pct=getattr(
                            cached, "historical_volatility_pct", None
                        ),
                        implied_volatility_pct=getattr(cached, "implied_volatility_pct", None),
                        iv_hv_ratio=getattr(cached, "iv_hv_ratio", None),
                        options_implied_move_pct=getattr(cached, "options_implied_move_pct", None),
                        event_age_hours=getattr(cached, "event_age_hours", None) or Decimal("0.0"),
                        catalyst_decay_factor=getattr(cached, "catalyst_decay_factor", None)
                        or Decimal("1.0"),
                        catalyst_decay_status=decay_status,
                    )
            except Exception:
                logger.warning("Market reaction cache read failed for symbol=%s", symbol)

        # Deterministic math calculation
        metrics = compute_reaction_metrics(
            bars=bars,
            expected_reaction_pct=expected_reaction_pct,
            event_age_seconds=event_age_seconds,
            event_category=event_category,
        )

        prompt = (
            f"Analyze market reaction for {symbol}. Catalyst='{catalyst_summary[:200]}' "
            f"Cat={event_category.value} Age={metrics['event_age_hours']}h "
            f"({metrics['catalyst_decay_status'].value.upper()}, "
            f"decay={metrics['catalyst_decay_factor']}).\n"
            f"PRICING: Expected={metrics['expected_reaction_pct']}% "
            f"Actual={metrics['actual_reaction_pct']}% "
            f"AdjGap={metrics['direction_adjusted_gap_pct']}% "
            f"VolSurge={metrics['volume_ratio']}x.\n"
            f"ANALOGS: Median={metrics['historical_median_reaction_pct']}% "
            f"StdDev={metrics['historical_dispersion_pct']}% "
            f"Matches={metrics['analog_count']} Sim={metrics['analog_similarity_score']}/100.\n"
            f"VOL/OPTIONS: HV={metrics['historical_volatility_pct']}% "
            f"IV={metrics['implied_volatility_pct']}% "
            f"IV/HV={metrics['iv_hv_ratio']}x "
            f"ImpliedMove=±{metrics['options_implied_move_pct']}%. "
            f"PrelimClass={metrics['classification']} "
            f"OppScore={metrics['opportunity_score']}/100.\n\n"
            "Output JSON: thesis (concise 1-2 sentences), confidence (0.0-1.0), "
            "evidence_summaries (2 concise items), limitations (1 item), "
            "classification (UNDERREACTION|OVERREACTION|FAIR_REACTION)."
        )

        completion = await self.llm_gateway.complete_structured(
            prompt=prompt,
            response_model=ReactionAnalysisLLMOutput,
            system_prompt=SYSTEM_PROMPT,
            trace_id=trace_id,
            max_tokens=1024,
        )

        parsed = completion.parsed
        if not parsed:
            raise ValueError("Failed to obtain valid parsed output from LLM gateway")

        now_utc = datetime.now(UTC)
        evidence_items = [
            EvidenceItem(
                source="alpaca_market_data",
                summary=(
                    f"Price moved {metrics['actual_reaction_pct']}% "
                    f"(expected {metrics['expected_reaction_pct']}%) with "
                    f"{metrics['volume_ratio']}x volume surge "
                    f"(adj gap: {metrics['direction_adjusted_gap_pct']}%)"
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
            direction_adjusted_gap_pct=metrics["direction_adjusted_gap_pct"],
            volume_ratio=metrics["volume_ratio"],
            classification=ReactionClassification(metrics["classification"]),
            opportunity_score=metrics["opportunity_score"],
            historical_median_reaction_pct=metrics["historical_median_reaction_pct"],
            historical_dispersion_pct=metrics["historical_dispersion_pct"],
            analog_count=metrics["analog_count"],
            analog_similarity_score=metrics["analog_similarity_score"],
            historical_volatility_pct=metrics["historical_volatility_pct"],
            implied_volatility_pct=metrics["implied_volatility_pct"],
            iv_hv_ratio=metrics["iv_hv_ratio"],
            options_implied_move_pct=metrics["options_implied_move_pct"],
            event_age_hours=metrics["event_age_hours"],
            catalyst_decay_factor=metrics["catalyst_decay_factor"],
            catalyst_decay_status=metrics["catalyst_decay_status"],
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
                direction_adjusted_gap_pct=metrics["direction_adjusted_gap_pct"],
                volume_ratio=metrics["volume_ratio"],
                classification=metrics["classification"],
                opportunity_score=metrics["opportunity_score"],
                historical_median_reaction_pct=metrics["historical_median_reaction_pct"],
                historical_dispersion_pct=metrics["historical_dispersion_pct"],
                analog_count=metrics["analog_count"],
                analog_similarity_score=metrics["analog_similarity_score"],
                historical_volatility_pct=metrics["historical_volatility_pct"],
                implied_volatility_pct=metrics["implied_volatility_pct"],
                iv_hv_ratio=metrics["iv_hv_ratio"],
                options_implied_move_pct=metrics["options_implied_move_pct"],
                event_age_hours=metrics["event_age_hours"],
                catalyst_decay_factor=metrics["catalyst_decay_factor"],
                catalyst_decay_status=metrics["catalyst_decay_status"].value,
                model_name=completion.model,
                raw_digest=completion.raw_digest,
            )
            if db_session is not None:
                db_session.add(db_model)
                await db_session.commit()
        except Exception as exc:
            # A cache write must never turn a non-authoritative research result into an error.
            if db_session is not None:
                await db_session.rollback()
            if strict:
                raise RuntimeError("Market reaction research persistence failed") from exc
            logger.warning("Market reaction cache write failed for symbol=%s", symbol)

        return report
