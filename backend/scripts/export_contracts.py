from __future__ import annotations

import json
from pathlib import Path

from pydantic.json_schema import models_json_schema

from app.api.models import (
    AuthMeResponse,
    HealthResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    SystemStatus,
)
from app.contracts import (
    AIProfile,
    AIProfileRecommendation,
    AuditEvent,
    AuthorizationDecision,
    ExecutionReceipt,
    ExitPolicy,
    HistoricalBar,
    HistoricalMarketDataRecord,
    LLMEventAnalysis,
    OptionLeg,
    OptionStrategy,
    ResearchReport,
    RiskAssessment,
    RuleEvaluation,
    ShadowCandidate,
    ShadowSession,
    TradeProposal,
)

MODELS = (
    HealthResponse,
    SystemStatus,
    LoginRequest,
    LoginResponse,
    AuthMeResponse,
    LogoutResponse,
    ResearchReport,
    TradeProposal,
    ShadowCandidate,
    ExitPolicy,
    OptionLeg,
    OptionStrategy,
    RiskAssessment,
    RuleEvaluation,
    AuthorizationDecision,
    ExecutionReceipt,
    ShadowSession,
    AuditEvent,
    AIProfile,
    AIProfileRecommendation,
    HistoricalBar,
    HistoricalMarketDataRecord,
    LLMEventAnalysis,
)


def main() -> None:
    _, definitions = models_json_schema(
        [(model, "validation") for model in MODELS], ref_template="#/components/schemas/{model}"
    )
    schemas = definitions.get("$defs", {})
    document = {
        "openapi": "3.1.0",
        "info": {"title": "PRISM Governed Market-Reaction Contracts", "version": "0.1.0"},
        "paths": {},
        "components": {"schemas": schemas},
    }
    target = Path(__file__).resolve().parents[1] / "build" / "contracts.openapi.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
