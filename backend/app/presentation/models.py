from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, alias_generators, field_validator


class PresentationModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )


class DataMode(StrEnum):
    ILLUSTRATIVE_FIXTURE = "illustrative_fixture"
    RECORDED = "recorded"
    SIMULATED = "simulated"


class Provenance(StrEnum):
    ILLUSTRATIVE_FIXTURE = "illustrative_fixture"
    ALPACA_PAPER = "alpaca_paper"
    SHADOW = "shadow"
    BENCHMARK = "benchmark"
    SIMULATED = "simulated"
    PLANNED_INTEGRATION = "planned_integration"
    RECORDED = "recorded"
    ALPACA_MARKET_DATA = "alpaca_market_data"


class DateRange(PresentationModel):
    preset: Literal["7d", "1m", "3m", "ytd", "custom"]
    from_date: str = Field(serialization_alias="from")
    to_date: str = Field(serialization_alias="to")
    timezone: Literal["UTC"] = "UTC"


class PresentationMeta(PresentationModel):
    generated_at: datetime
    as_of: datetime
    data_mode: DataMode = DataMode.ILLUSTRATIVE_FIXTURE
    fixture_version: str | None = "prism-demo-v1"
    provenance_notice: str | None = None
    range: DateRange | None = None


class PresentationEnvelope[PayloadT](PresentationModel):
    meta: PresentationMeta
    data: PayloadT


class ChartPoint(PresentationModel):
    date: str
    chosen_path: str | None = None
    alternative: str | None = None
    benchmark: str | None = None
    agent_alternative: str | None = None
    reduced_size: str | None = None
    unhedged: str | None = None
    cash_baseline: str | None = None
    pnl: str | None = None
    drawdown: str | None = None


class StoryOutcome(StrEnum):
    PASS = "pass"
    MODIFY = "modify"
    FAIL = "fail"
    NO_TRADE = "no_trade"
    DEGRADED = "degraded"


class StorySummary(PresentationModel):
    id: str
    occurred_at: datetime
    symbol: str
    category: str
    title: str
    summary: str
    outcome: StoryOutcome
    rule_result: Literal["PASS", "MODIFY", "FAIL", "NOT_EVALUATED"]
    chosen_path_impact: str
    best_alternative_impact: str
    lesson: str


class DecisionNode(PresentationModel):
    id: str
    parent_id: str | None
    label: str
    actor: str
    component_kind: Literal["ai_specialist", "risk_ai", "deterministic", "paper", "shadow"]
    status: str
    detail: str


class TranscriptStep(PresentationModel):
    id: str
    occurred_at: datetime
    kind: Literal["agent_summary", "tool_call", "rule_gate"]
    actor: str
    title: str
    summary: str
    model: str | None = None
    prompt_version: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    evidence_refs: list[str]


class RuleCheck(PresentationModel):
    rule_id: str
    priority: Literal["P0", "P1", "P2", "P3", "P4", "P5"]
    name: str
    result: Literal["PASS", "MODIFY", "FAIL", "NOT_EVALUATED"]
    reason_code: str
    explanation: str


class AlternativeBranch(PresentationModel):
    id: str
    branch_key: str
    label: str
    variation: str
    pnl: str
    delta_vs_chosen: str
    drawdown: str
    coverage: str
    status: Literal["open", "complete", "incomplete"]
    gross_pnl: str | None = None
    net_pnl: str | None = None
    mae: str | None = None
    mfe: str | None = None
    duration: str | None = None
    capital_at_risk: str | None = None
    allocation_multiplier: str | None = None
    entry_exit_policy: str | None = None
    valuation_confidence: str | None = None
    refusal_reason: str | None = None
    chosen_path: bool = False
    simulated_fill: AlternativeSimulatedFill | None = None


class AlternativeSimulatedFillLeg(PresentationModel):
    option_symbol: str
    side: Literal["buy", "sell"]
    quantity: int
    entry_price: str | None = None
    exit_price: str | None = None


class AlternativeSimulatedFill(PresentationModel):
    status: Literal["filled", "not_filled", "incomplete"]
    quantity: int | None = None
    entry_at: datetime | None = None
    entry_price: str | None = None
    exit_at: datetime | None = None
    exit_price: str | None = None
    slippage: str | None = None
    exit_reason: str | None = None
    cost_model: Literal["observed_nbbo_touch"]
    legs: list[AlternativeSimulatedFillLeg] = Field(default_factory=list)


class AlternativeSimulationMeta(PresentationModel):
    kind: Literal["historical_options"]
    window_start: datetime
    window_end: datetime
    cadence_seconds: int = Field(gt=0)
    cost_model: Literal["observed_nbbo_touch"]


class Catalyst(PresentationModel):
    headline: str
    source: str
    published_at: datetime
    classification: str
    observed_move: str
    expected_move: str


class IllustrativeOutcome(PresentationModel):
    action: str
    status: str
    rationale: str
    observed_at: datetime


class Evidence(PresentationModel):
    label: str
    source: str
    observed_at: datetime
    provenance: Provenance


class OperationalEvidence(PresentationModel):
    label: str
    value: str
    status: Literal["recorded", "unavailable", "degraded", "simulated"]
    observed_at: datetime | None = None


class StoryDetail(StorySummary):
    catalyst: Catalyst
    market_path: list[ChartPoint]
    decision_tree: list[DecisionNode]
    transcript: list[TranscriptStep]
    rule_checks: list[RuleCheck]
    illustrative_outcome: IllustrativeOutcome
    alternatives: list[AlternativeBranch]
    lessons: list[str]
    evidence: list[Evidence]
    operational_evidence: list[OperationalEvidence] = Field(default_factory=list)


class ExposureItem(PresentationModel):
    label: str
    value: str


class Position(PresentationModel):
    symbol: str
    allocation: str
    value: str
    pnl: str
    provenance: Provenance


class Activity(PresentationModel):
    occurred_at: datetime
    label: str
    detail: str
    amount: str
    provenance: Provenance = Provenance.ILLUSTRATIVE_FIXTURE


class Portfolio(PresentationModel):
    points: list[ChartPoint]
    positions: list[Position]
    activities: list[Activity]
    exposure: list[ExposureItem]
    operational_evidence: list[OperationalEvidence] = Field(default_factory=list)


class OutcomeCount(PresentationModel):
    label: str
    value: str


class Overview(PresentationModel):
    stories: list[StorySummary]
    portfolio: Portfolio
    outcomes: list[OutcomeCount]
    recommendations: list[str]


class DecisionCollection(PresentationModel):
    stories: list[StorySummary]
    symbols: list[str]


class AlternativeSession(PresentationModel):
    id: str
    story_id: str
    occurred_at: datetime
    symbol: str
    title: str
    summary: str
    chosen_path_pnl: str
    best_branch: str
    alternative_label: str | None = None
    best_delta: str
    coverage: str
    branches: list[AlternativeBranch]
    path: list[ChartPoint]
    limitations: list[str]
    state: Literal["open", "complete", "incomplete"] = "incomplete"
    terminal_outcome: str | None = None
    source_mode: Literal["production", "staging"] | None = None
    evaluation_root_digest: str | None = None
    ruleset_version: str | None = None
    profile_version: int | None = None
    valuation_policy_version: str | None = None
    refusal_reasons: list[str] = Field(default_factory=list)
    simulation: AlternativeSimulationMeta | None = None


class AlternativeCollection(PresentationModel):
    sessions: list[AlternativeSession]
    aggregate_path: list[ChartPoint] = Field(default_factory=list)
    completed_sessions: int = Field(default=0, ge=0)
    incomplete_sessions: int = Field(default=0, ge=0)
    empty_message: str | None = None


class AgentRun(PresentationModel):
    id: str
    occurred_at: datetime
    status: Literal["complete", "degraded", "failed"]
    trigger: str
    duration_ms: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_tokens: int = Field(ge=0)
    summary: str


class AgentRecord(PresentationModel):
    id: str
    name: str
    role: str
    cadence: str
    model: str
    prompt_version: str
    description: str
    dependencies: list[str]
    stage: int = Field(ge=1)
    authority: Literal["research", "proposal", "risk", "recommendation"]
    accent: str
    runs: list[AgentRun]


class ToolRecord(PresentationModel):
    id: str
    name: str
    kind: Literal["SDK", "Internal", "MCP", "LLM"]
    state: Literal["used", "planned"]
    calls: int = Field(ge=0)
    success_rate: str
    median_latency: str
    purpose: str


class SystemComponent(PresentationModel):
    id: str
    name: str
    kind: Literal["risk_ai", "deterministic", "paper_execution", "shadowfund", "post_analysis"]
    authority: str
    description: str
    stage: int = Field(ge=1)


class AgentObservability(PresentationModel):
    agents: list[AgentRecord]
    tools: list[ToolRecord]
    components: list[SystemComponent]


class NewsRecord(PresentationModel):
    id: str
    published_at: datetime
    source: str
    provider: Literal["recorded"] = "recorded"
    symbols: list[str]
    headline: str
    summary: str
    category: str
    story_id: str | None
    significance: Literal["high", "medium", "low"]
    provenance: Provenance = Provenance.RECORDED


class NewsCollection(PresentationModel):
    items: list[NewsRecord]
    symbols: list[str]


class HardRule(PresentationModel):
    rule_id: str
    priority: Literal["P0", "P1", "P2", "P3", "P4", "P5"]
    name: str
    active_value: str
    explanation: str


class ProfileParameter(PresentationModel):
    id: str
    name: str
    active_value: str
    minimum: str
    maximum: str
    unit: str
    description: str


class ProfileSummary(PresentationModel):
    key: Literal["conservative", "balanced", "aggressive"]
    status: Literal["active", "available"]
    parameters: dict[str, str]


class GovernanceVersion(PresentationModel):
    version: str
    state: Literal["active", "superseded"]
    summary: str


class HackathonWindow(PresentationModel):
    trading_start_at: datetime
    official_scoring_at: datetime
    window_outer_boundary_at: datetime
    force_flatten_by: datetime
    new_entry_cutoff_at: datetime
    effective_max_hold_trading_days: int = Field(ge=1)
    scoring_basis: Literal["total_account_equity"]


class Governance(PresentationModel):
    ruleset_id: str
    ruleset_version: str
    ruleset_status: Literal["active"]
    active_profile: Literal["balanced"]
    decision_semantics: dict[str, str]
    hard_rules: list[HardRule]
    profile_parameters: list[ProfileParameter]
    profiles: list[ProfileSummary]
    versions: list[GovernanceVersion]
    hackathon_window: HackathonWindow


class ProfileSuggestion(PresentationModel):
    id: str
    parameter_id: str
    parameter_name: str
    current_value: str
    suggested_value: str
    allowed_minimum: str
    allowed_maximum: str
    confidence: Literal["high", "medium", "low"]
    rationale: str
    week_of: str
    validation_state: Literal["within_authorized_bounds"]
    manual_review_required: Literal[True] = True


class WeeklySummary(PresentationModel):
    week_of: str
    stories_analyzed: int
    illustrative_net_pnl: str
    shadow_beat_chosen: int
    key_findings: list[str]
    suggestions: list[ProfileSuggestion]


class RangeParameters(PresentationModel):
    from_date: datetime = Field(serialization_alias="from")
    to_date: datetime = Field(serialization_alias="to")

    @field_validator("from_date", "to_date")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("presentation ranges must be timezone-aware")
        return value
