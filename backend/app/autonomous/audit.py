from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from app.contracts.models import EvaluationRoot


def build_evaluation_root(
    *,
    trace_id: UUID,
    outcome: str,
    evidence: Any,
    proposal_digest: str | None = None,
    market_snapshot: Any = "unavailable",
    portfolio_snapshot: Any = "unavailable",
) -> EvaluationRoot:
    """Hash the complete lineage so later ShadowFund valuation uses same inputs."""

    def digest(value: Any) -> str:
        encoded = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    evidence_digest = digest(evidence)
    market_digest = digest(market_snapshot)
    portfolio_digest = digest(portfolio_snapshot)
    lineage = {
        "trace_id": str(trace_id),
        "outcome": outcome,
        "evidence_digest": evidence_digest,
        "proposal_digest": proposal_digest,
        "market_snapshot_digest": market_digest,
        "portfolio_snapshot_digest": portfolio_digest,
    }
    return EvaluationRoot(
        trace_id=trace_id,
        root_digest=digest(lineage),
        outcome=outcome,
        evidence_digest=evidence_digest,
        proposal_digest=proposal_digest,
        market_snapshot_digest=market_digest,
        portfolio_snapshot_digest=portfolio_digest,
    )
