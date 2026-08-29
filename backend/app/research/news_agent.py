from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.models import LLMEventAnalysis
from app.core.llm_gateway import LLMGateway
from app.research.models import LLMEventAnalysisModel

PROMPT_VERSION = "1.0"

SYSTEM_PROMPT = (
    "You are a News Intelligence Agent for PRISM, a multi-agent trading intelligence system. "
    "Your primary function is to analyze financial news, announcements, earnings releases, and "
    "market events to determine their relevance, sentiment, significance, and potential impact "
    "on an asset. Output strictly valid JSON matching the schema."
)


class NewsAnalysisLLMOutput(BaseModel):
    event_type: str = Field(
        description=(
            "Category of the event (e.g., earnings, product_launch, m_a, legal, "
            "macro, corporate_governance, regulatory, other)"
        )
    )
    sentiment: str = Field(
        description=(
            "Sentiment classification of the news article for the target asset. "
            "Must be 'bullish', 'bearish', or 'neutral'"
        )
    )
    significance_score: Decimal = Field(
        ge=0,
        le=100,
        description=(
            "Significance and potential impact on the asset, "
            "from 0 (insignificant) to 100 (critical)"
        ),
    )
    expected_reaction_pct: Decimal | None = Field(
        default=None,
        description=(
            "Estimated or expected asset price reaction percentage (positive/negative), "
            "or null if not quantifiable"
        ),
    )
    rationale: str = Field(
        description=(
            "Concise analytical reasoning justifying the sentiment, significance, "
            "and event classification based strictly on the article text"
        )
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
        db_session: AsyncSession,
    ) -> LLMEventAnalysis:
        """Analyze a single news article, checking cache first to prevent duplicate LLM cost."""
        article_id = str(article["id"])
        headline = article.get("headline", "")
        summary = article.get("summary", "")
        content_raw = article.get("content", "")
        clean_content = clean_html_and_truncate(content_raw)

        # Get LLM configuration to search cache by (article_id, model_name)
        active_model = self.llm_gateway._settings.llm_model or "default"

        # Check DB cache first
        try:
            query = select(LLMEventAnalysisModel).where(
                LLMEventAnalysisModel.article_id == article_id,
                LLMEventAnalysisModel.model_name == active_model,
            )
            result = await db_session.execute(query)
            cached_model = result.scalar_one_or_none()

            if cached_model:
                # Cache hit: build LLMEventAnalysis directly from database model fields
                return LLMEventAnalysis(
                    schema_version=cached_model.schema_version,
                    id=UUID(cached_model.id),
                    trace_id=UUID(cached_model.trace_id),
                    created_at=cached_model.created_at,
                    article_id=cached_model.article_id,
                    symbol=cached_model.symbol,
                    headline=cached_model.headline,
                    event_type=cached_model.event_type,
                    sentiment=cached_model.sentiment,
                    significance_score=Decimal(str(cached_model.significance_score)),
                    expected_reaction_pct=(
                        Decimal(str(cached_model.expected_reaction_pct))
                        if cached_model.expected_reaction_pct is not None
                        else None
                    ),
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

        # Construct contract schema
        analysis_contract = LLMEventAnalysis(
            id=uuid4(),
            trace_id=trace_id,
            created_at=datetime.now(UTC),
            article_id=article_id,
            symbol=symbol,
            headline=headline,
            event_type=parsed_output.event_type,
            sentiment=parsed_output.sentiment,
            significance_score=parsed_output.significance_score,
            expected_reaction_pct=parsed_output.expected_reaction_pct,
            rationale=parsed_output.rationale,
            model_name=completion.model,
            prompt_version=PROMPT_VERSION,
            raw_digest=completion.raw_digest,
        )

        # Write to SQL Database cache (if available)
        try:
            db_model = LLMEventAnalysisModel(
                id=str(analysis_contract.id),
                trace_id=str(analysis_contract.trace_id),
                created_at=analysis_contract.created_at,
                schema_version=analysis_contract.schema_version,
                article_id=analysis_contract.article_id,
                symbol=analysis_contract.symbol,
                headline=analysis_contract.headline,
                event_type=analysis_contract.event_type,
                sentiment=analysis_contract.sentiment,
                significance_score=analysis_contract.significance_score,
                expected_reaction_pct=analysis_contract.expected_reaction_pct,
                rationale=analysis_contract.rationale,
                model_name=analysis_contract.model_name,
                prompt_version=analysis_contract.prompt_version,
                raw_digest=analysis_contract.raw_digest,
            )
            db_session.add(db_model)
            await db_session.commit()
        except Exception:
            # Database cache write failed; ignore and return result
            pass

        return analysis_contract
