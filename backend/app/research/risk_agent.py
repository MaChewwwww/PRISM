"""AI-assisted adversarial risk review.

This agent can recommend rejection, but cannot approve or alter an order.  The
deterministic P0-P5 evaluator remains the only authorization authority.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.models import RiskAssessment, RiskVerdict, TradeProposal
from app.core.llm_gateway import LLMGateway


class RiskAssessmentLLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: RiskVerdict
    max_loss: Decimal = Field(ge=0)
    findings: list[str] = Field(default_factory=list)
    data_fresh: bool


class RiskManagementAgent:
    def __init__(self, llm_gateway: LLMGateway) -> None:
        self.llm_gateway = llm_gateway

    async def assess(
        self,
        proposal: TradeProposal,
        *,
        context: dict[str, Any],
    ) -> RiskAssessment:
        prompt = (
            "Act as PRISM's adversarial Risk Management agent. You may reject a proposal but "
            "must not authorize or rewrite it. Evaluate max loss, account buying power, "
            "portfolio concentration, quote freshness, historical analog coverage, and "
            "the paper-only execution boundary. Return only the required JSON schema.\n\n"
            f"PROPOSAL:\n{proposal.model_dump_json()}\n\n"
            f"OBSERVED CONTEXT:\n{context}\n"
        )
        result = await self.llm_gateway.complete_structured(
            prompt=prompt,
            response_model=RiskAssessmentLLMOutput,
            trace_id=proposal.trace_id,
        )
        output = result.parsed
        if output is None:
            raise ValueError("Risk agent returned no structured assessment")
        return RiskAssessment(
            trace_id=proposal.trace_id,
            proposal_id=proposal.id,
            verdict=output.verdict,
            max_loss=Decimal(str(output.max_loss)),
            findings=output.findings,
            data_fresh=output.data_fresh,
        )
