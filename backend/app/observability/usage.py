from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.core.config import Settings
from app.core.database import get_db_session
from app.observability.models import LLMUsageEventModel


async def record_llm_usage(
    *,
    settings: Settings,
    trace_id: UUID,
    provider: str,
    model: str,
    operation: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int | None,
    latency_ms: int,
    raw_digest: str,
) -> None:
    """Best-effort observability write; never changes an LLM result or trade path."""
    if not settings.llm_usage_tracking_enabled:
        return
    available = prompt_tokens is not None and completion_tokens is not None
    estimated_cost: Decimal | None = None
    if (
        available
        and settings.llm_input_price_per_million_usd is not None
        and settings.llm_output_price_per_million_usd is not None
    ):
        estimated_cost = (
            Decimal(prompt_tokens or 0) * settings.llm_input_price_per_million_usd
            + Decimal(completion_tokens or 0) * settings.llm_output_price_per_million_usd
        ) / Decimal("1000000")
    try:
        async for session in get_db_session():
            session.add(
                LLMUsageEventModel(
                    id=str(uuid4()),
                    observed_at=datetime.now(UTC),
                    trace_id=str(trace_id),
                    provider=provider,
                    model=model,
                    operation=operation,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    usage_available=available,
                    latency_ms=latency_ms,
                    raw_digest=raw_digest,
                    estimated_cost_usd=estimated_cost,
                )
            )
            await session.commit()
    except Exception:
        # Observability is deliberately isolated from research and execution.
        return
