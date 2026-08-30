from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.models import (
    CatalystMateriality,
    EarningsSurpriseData,
    GuidanceChange,
    LLMEventAnalysis,
    NewsEventCategory,
)
from app.core.llm_gateway import LLMGateway
from app.research.models import LLMEventAnalysisModel

PROMPT_VERSION = "2.0"

SYSTEM_PROMPT = (
    "You are a News Intelligence Agent for PRISM, a multi-agent trading intelligence system. "
    "Your primary function is to analyze financial news, announcements, earnings releases, and "
    "market events to determine their category, materiality, sentiment, significance, forward "
    "guidance changes, earnings/revenue surprises, and any internal contradictory signals.\n\n"
    "CLASSIFICATION RULES:\n"
    "- event_category: One of 'earnings', 'guidance', 'm_and_a', 'regulatory_legal', "
    "'product_innovation', 'analyst_action', 'management_change', 'macro_geopolitical', "
    "'routine_pr', or 'other'.\n"
    "- catalyst_materiality: 'critical' (transformative, major M&A, existential litigation), "
    "'high' (material earnings beat/miss, major guidance revision, FDA approval), 'medium' "
    "(analyst upgrade/downgrade, product launch), 'low' (minor contract, conference talk), or "
    "'noise' (routine PR, syndication filler).\n"
    "- sentiment: 'bullish', 'bearish', or 'neutral'.\n"
    "- guidance_change: 'raised', 'lowered', 'reaffirmed', 'withdrawn', or 'not_applicable'.\n"
    "- eps_surprise_pct / revenue_surprise_pct: Quantified beat (+) or miss (-) percentage if "
    "explicitly stated in text.\n"
    "- has_contradictory_signals: Set to true if the article contains conflicting narrative "
    "forces (e.g. EPS beat but guidance lowered, or revenue surge with collapsing margins).\n"
    "Output strictly valid JSON matching the schema."
)

SOURCE_CREDIBILITY_MAP: dict[str, Decimal] = {
    "sec": Decimal("100.0"),
    "businesswire": Decimal("95.0"),
    "pr_newswire": Decimal("95.0"),
    "globenewswire": Decimal("95.0"),
    "reuters": Decimal("95.0"),
    "bloomberg": Decimal("95.0"),
    "dow_jones": Decimal("95.0"),
    "wsj": Decimal("95.0"),
    "cnbc": Decimal("85.0"),
    "benzinga": Decimal("80.0"),
    "marketwatch": Decimal("80.0"),
    "investors_business_daily": Decimal("80.0"),
    "seekingalpha": Decimal("65.0"),
    "thefly": Decimal("75.0"),
    "fool": Decimal("60.0"),
}


def compute_source_confidence(source: str | None) -> Decimal:
    """Deterministically score source reliability based on known regulatory and wire tiers."""
    if not source:
        return Decimal("50.0")
    norm_source = source.strip().lower().replace(" ", "_").replace("-", "_")
    for key, score in SOURCE_CREDIBILITY_MAP.items():
        if key in norm_source or norm_source in key:
            return score
    return Decimal("50.0")


def compute_event_age_seconds(created_at: Any, now: datetime | None = None) -> int:
    """Deterministically compute event age / freshness relative to current UTC time."""
    if now is None:
        now = datetime.now(UTC)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    if isinstance(created_at, datetime):
        dt = created_at if created_at.tzinfo else created_at.replace(tzinfo=UTC)
        return max(0, int((now - dt.astimezone(UTC)).total_seconds()))
    if isinstance(created_at, str):
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return max(0, int((now - dt.astimezone(UTC)).total_seconds()))
        except Exception:
            return 0
    return 0


class NewsAnalysisLLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_category: NewsEventCategory = Field(description="Standardized category of the news event")
    catalyst_materiality: CatalystMateriality = Field(
        description="Materiality level: critical, high, medium, low, or noise"
    )
    sentiment: str = Field(
        description=(
            "Sentiment classification for target asset: 'bullish', 'bearish', or 'neutral'"
        )
    )
    significance_score: Decimal = Field(
        ge=0,
        le=100,
        description="Significance impact on asset from 0 (insignificant) to 100 (critical)",
    )
    expected_reaction_pct: Decimal | None = Field(
        default=None,
        description="Estimated asset price reaction pct, or null if unquantifiable",
    )
    guidance_change: GuidanceChange = Field(
        default=GuidanceChange.NOT_APPLICABLE,
        description="Guidance revision: raised, lowered, reaffirmed, withdrawn, not_applicable",
    )
    eps_surprise_pct: Decimal | None = Field(
        default=None,
        description="EPS surprise percentage (e.g. 5.2 for +5.2% beat), or null",
    )
    revenue_surprise_pct: Decimal | None = Field(
        default=None,
        description="Revenue surprise percentage (e.g. -1.8 for -1.8% miss), or null",
    )
    quarter: str | None = Field(
        default=None,
        description="Reporting fiscal quarter if applicable (e.g. 'Q2 2026' or 'Q3')",
    )
    has_contradictory_signals: bool = Field(
        default=False,
        description="True if article contains conflicting signals (e.g. EPS beat vs cut guidance)",
    )

    contradiction_notes: str | None = Field(
        default=None,
        description="Brief analytical explanation of conflicting signals, or null if none",
    )
    rationale: str = Field(
        description="Analytical reasoning justifying sentiment, materiality, and significance"
    )


def clean_html_and_truncate(html_content: str, max_chars: int = 2000) -> str:
    """Strip HTML tags and truncate the content to target character limit."""
    if not html_content:
        return ""
    # Strip HTML tags
    clean_text = re.sub(r"<.*?>", "", html_content)
    # Normalize whitespace
    clean_text = " ".join(clean_text.split())
    # Truncate
    if len(clean_text) > max_chars:
        clean_text = clean_text[:max_chars] + "..."
    return clean_text


class NewsIntelligenceAgent:
    """AI specialist agent that analyzes news and market catalysts to determine sentiment/impact."""

    def __init__(self, llm_gateway: LLMGateway) -> None:
        self.llm_gateway = llm_gateway

    async def analyze_article(
        self,
        article: dict[str, Any],
        symbol: str,
        trace_id: UUID,
        db_session: AsyncSession | None = None,
        *,
        strict: bool = False,
    ) -> LLMEventAnalysis:
        """Analyze a single news article, checking cache first to prevent duplicate LLM cost."""
        article_id = str(article["id"])
        headline = article.get("headline", "")
        source_raw = article.get("source") or "unknown"
        created_at_raw = article.get("created_at")
        summary = article.get("summary", "")
        content_raw = article.get("content", "")
        clean_content = clean_html_and_truncate(content_raw)

        source_confidence = compute_source_confidence(source_raw)
        event_age_seconds = compute_event_age_seconds(created_at_raw)

        # Get LLM configuration to search cache by (article_id, model_name)
        active_model = self.llm_gateway._settings.llm_model or "default"

        # Check DB cache first
        if db_session is not None and not strict:
            try:
                query = select(LLMEventAnalysisModel).where(
                    LLMEventAnalysisModel.article_id == article_id,
                    LLMEventAnalysisModel.model_name == active_model,
                )
                result = await db_session.execute(query)
                cached_model = result.scalar_one_or_none()

                if cached_model:
                    earnings_surprise = None
                    if cached_model.earnings_surprise_json:
                        try:
                            surprise_dict = json.loads(cached_model.earnings_surprise_json)
                            earnings_surprise = EarningsSurpriseData(
                                eps_surprise_pct=(
                                    Decimal(str(surprise_dict["eps_surprise_pct"]))
                                    if surprise_dict.get("eps_surprise_pct") is not None
                                    else None
                                ),
                                revenue_surprise_pct=(
                                    Decimal(str(surprise_dict["revenue_surprise_pct"]))
                                    if surprise_dict.get("revenue_surprise_pct") is not None
                                    else None
                                ),
                                quarter=surprise_dict.get("quarter"),
                            )
                        except Exception:
                            earnings_surprise = None

                    # Cache hit: build LLMEventAnalysis directly from database model fields
                    return LLMEventAnalysis(
                        schema_version=cached_model.schema_version,
                        id=UUID(cached_model.id),
                        trace_id=UUID(cached_model.trace_id),
                        created_at=cached_model.created_at,
                        article_id=cached_model.article_id,
                        symbol=cached_model.symbol,
                        headline=cached_model.headline,
                        source=cached_model.source or source_raw,
                        source_confidence=Decimal(str(cached_model.source_confidence)),
                        event_age_seconds=cached_model.event_age_seconds,
                        event_category=(
                            NewsEventCategory(cached_model.event_category)
                            if cached_model.event_category in NewsEventCategory._value2member_map_
                            else NewsEventCategory.OTHER
                        ),
                        event_type=cached_model.event_type,
                        catalyst_materiality=(
                            CatalystMateriality(cached_model.catalyst_materiality)
                            if cached_model.catalyst_materiality
                            in CatalystMateriality._value2member_map_
                            else CatalystMateriality.MEDIUM
                        ),
                        sentiment=cached_model.sentiment,
                        significance_score=Decimal(str(cached_model.significance_score)),
                        expected_reaction_pct=(
                            Decimal(str(cached_model.expected_reaction_pct))
                            if cached_model.expected_reaction_pct is not None
                            else None
                        ),
                        guidance_change=(
                            GuidanceChange(cached_model.guidance_change)
                            if cached_model.guidance_change in GuidanceChange._value2member_map_
                            else GuidanceChange.NOT_APPLICABLE
                        ),
                        earnings_surprise=earnings_surprise,
                        has_contradictory_signals=cached_model.has_contradictory_signals,
                        contradiction_notes=cached_model.contradiction_notes,
                        rationale=cached_model.rationale,
                        model_name=cached_model.model_name,
                        prompt_version=cached_model.prompt_version,
                        raw_digest=cached_model.raw_digest,
                    )
            except Exception:
                # Database cache read failed (e.g. offline DB); proceed with live LLM analysis
                pass

        # Cache miss: run LLM completion
        prompt = (
            f"Analyze the following financial news article for the target asset: {symbol}\n\n"
            f"Source Wire: {source_raw}\n"
            f"Headline: {headline}\n"
            f"Summary: {summary}\n"
            f"Article Content: {clean_content}\n"
        )

        completion = await self.llm_gateway.complete_structured(
            prompt=prompt,
            response_model=NewsAnalysisLLMOutput,
            system_prompt=SYSTEM_PROMPT,
            trace_id=trace_id,
        )

        parsed_output = completion.parsed
        if not parsed_output:
            raise ValueError("Failed to obtain valid parsed output from LLM completion")

        earnings_surprise = None
        if (
            parsed_output.eps_surprise_pct is not None
            or parsed_output.revenue_surprise_pct is not None
            or parsed_output.quarter is not None
        ):
            earnings_surprise = EarningsSurpriseData(
                eps_surprise_pct=parsed_output.eps_surprise_pct,
                revenue_surprise_pct=parsed_output.revenue_surprise_pct,
                quarter=parsed_output.quarter,
            )

        # Construct contract schema
        analysis_contract = LLMEventAnalysis(
            id=uuid4(),
            trace_id=trace_id,
            created_at=datetime.now(UTC),
            article_id=article_id,
            symbol=symbol,
            headline=headline,
            source=source_raw,
            source_confidence=source_confidence,
            event_age_seconds=event_age_seconds,
            event_category=parsed_output.event_category,
            event_type=parsed_output.event_category.value,
            catalyst_materiality=parsed_output.catalyst_materiality,
            sentiment=parsed_output.sentiment,
            significance_score=parsed_output.significance_score,
            expected_reaction_pct=parsed_output.expected_reaction_pct,
            guidance_change=parsed_output.guidance_change,
            earnings_surprise=earnings_surprise,
            has_contradictory_signals=parsed_output.has_contradictory_signals,
            contradiction_notes=parsed_output.contradiction_notes,
            rationale=parsed_output.rationale,
            model_name=completion.model,
            prompt_version=PROMPT_VERSION,
            raw_digest=completion.raw_digest,
        )

        # Write to SQL Database cache (if available)
        if db_session is not None:
            try:
                earnings_surprise_json = None
                if earnings_surprise is not None:
                    earnings_surprise_json = json.dumps(
                        {
                            "eps_surprise_pct": (
                                str(earnings_surprise.eps_surprise_pct)
                                if earnings_surprise.eps_surprise_pct is not None
                                else None
                            ),
                            "revenue_surprise_pct": (
                                str(earnings_surprise.revenue_surprise_pct)
                                if earnings_surprise.revenue_surprise_pct is not None
                                else None
                            ),
                            "quarter": earnings_surprise.quarter,
                        }
                    )

                db_model = LLMEventAnalysisModel(
                    id=str(analysis_contract.id),
                    trace_id=str(analysis_contract.trace_id),
                    created_at=analysis_contract.created_at,
                    schema_version=analysis_contract.schema_version,
                    article_id=analysis_contract.article_id,
                    symbol=analysis_contract.symbol,
                    headline=analysis_contract.headline,
                    source=analysis_contract.source,
                    source_confidence=Decimal(str(analysis_contract.source_confidence)),
                    event_age_seconds=analysis_contract.event_age_seconds,
                    event_category=analysis_contract.event_category.value,
                    event_type=analysis_contract.event_type,
                    catalyst_materiality=analysis_contract.catalyst_materiality.value,
                    sentiment=analysis_contract.sentiment,
                    significance_score=Decimal(str(analysis_contract.significance_score)),
                    expected_reaction_pct=(
                        Decimal(str(analysis_contract.expected_reaction_pct))
                        if analysis_contract.expected_reaction_pct is not None
                        else None
                    ),
                    guidance_change=analysis_contract.guidance_change.value,
                    earnings_surprise_json=earnings_surprise_json,
                    has_contradictory_signals=analysis_contract.has_contradictory_signals,
                    contradiction_notes=analysis_contract.contradiction_notes,
                    rationale=analysis_contract.rationale,
                    model_name=analysis_contract.model_name,
                    prompt_version=analysis_contract.prompt_version,
                    raw_digest=analysis_contract.raw_digest,
                )
                db_session.add(db_model)
                await db_session.commit()
            except Exception as exc:
                # Database cache write failed; ignore and return result
                if strict:
                    raise RuntimeError("News research persistence failed") from exc

        return analysis_contract
