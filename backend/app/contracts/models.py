from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator

DecimalString = Annotated[
    Decimal,
    Field(json_schema_extra={"format": "decimal-string"}),
    PlainSerializer(str, return_type=str, when_used="json"),
]


class ContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)

    schema_version: Literal["1.0"] = "1.0"
    id: UUID = Field(default_factory=uuid4)
    trace_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("created_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(UTC)


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    summary: str
    observed_at: datetime
    received_at: datetime


class ResearchReport(ContractBase):
    symbol: str
    thesis: str
    confidence: DecimalString = Field(ge=0, le=1)
    freshness_seconds: int = Field(ge=0)
    evidence: list[EvidenceItem]
    limitations: list[str] = Field(default_factory=list)


class OptionSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OptionType(StrEnum):
    CALL = "call"
    PUT = "put"


class OptionLeg(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str
    underlying: str
    expiration: str
    option_type: OptionType
    side: OptionSide
    ratio_qty: int = Field(default=1, ge=1)
    strike_price: DecimalString = Field(gt=0)
    active: bool = True
    tradable: bool = True


class StrategyKind(StrEnum):
    LONG_CALL = "long_call"
    LONG_PUT = "long_put"
    CALL_DEBIT_SPREAD = "call_debit_spread"
    PUT_DEBIT_SPREAD = "put_debit_spread"


class OptionStrategy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: StrategyKind
    legs: list[OptionLeg] = Field(min_length=1, max_length=2)
    limit_price: DecimalString = Field(gt=0)
    time_in_force: Literal["day"] = "day"
    extended_hours: Literal[False] = False


class ExitPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    take_profit_pct: DecimalString = Field(default=Decimal("50.0"), gt=0)
    stop_loss_pct: DecimalString = Field(default=Decimal("50.0"), gt=0)
    dte_threshold: int = Field(default=7, ge=1)
    max_hold_days: int = Field(default=14, ge=1)


class ShadowCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    strategy: OptionStrategy | None = None
    allocation_multiplier: DecimalString = Field(default=Decimal("1.0"), gt=0)
    rationale: str = ""


class TradeProposal(ContractBase):
    research_report_id: UUID
    symbol: str
    strategy: OptionStrategy
    quantity: int = Field(ge=1)
    rationale: str
    exit_policy: ExitPolicy = Field(default_factory=ExitPolicy)
    shadow_candidates: list[ShadowCandidate] = Field(default_factory=list)
    proposal_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class RiskVerdict(StrEnum):
    ACCEPTABLE = "acceptable"
    CONCERNS = "concerns"
    REJECT = "reject"


class RiskAssessment(ContractBase):
    proposal_id: UUID
    verdict: RiskVerdict
    max_loss: DecimalString = Field(ge=0)
    findings: list[str]
    data_fresh: bool


class RuleOutcome(StrEnum):
    PASS = "pass"
    MODIFY = "modify"
    FAIL = "fail"


class RuleEvaluation(ContractBase):
    proposal_id: UUID
    ruleset_version: str
    outcome: RuleOutcome
    reasons: list[str]
    modified_proposal_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class AuthorizationState(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED_PENDING_ACCEPTANCE = "modified_pending_acceptance"


class AuthorizationDecision(ContractBase):
    proposal_id: UUID
    proposal_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    ruleset_version: str
    state: AuthorizationState
    expires_at: datetime
    account_observed_at: datetime
    supported_options_level: int = Field(ge=0)
    account_verified: bool

    @field_validator("expires_at", "account_observed_at")
    @classmethod
    def require_aware_decision_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(UTC)


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    RECONCILING = "reconciling"
    REJECTED = "rejected"
    FILLED = "filled"
    FAILED = "failed"


class ExecutionReceipt(ContractBase):
    proposal_id: UUID
    client_order_id: str
    broker_order_id: str | None = None
    payload_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: ExecutionStatus
    filled_quantity: DecimalString = Decimal("0")
    filled_average_price: DecimalString | None = None
    error_code: str | None = None
    error_message: str | None = None
    submitted_at: datetime | None = None
    reconciled_at: datetime | None = None


class ShadowState(StrEnum):
    OPEN = "open"
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class ShadowSession(ContractBase):
    proposal_id: UUID
    parent_session_id: UUID | None = None
    variation: dict[str, Any]
    evaluation_policy_version: str
    state: ShadowState
    metrics: dict[str, DecimalString] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class AuditEvent(ContractBase):
    aggregate_type: str
    aggregate_id: UUID
    event_type: str
    actor_type: str
    payload_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    payload: dict[str, Any]


class AIProfile(ContractBase):
    profile_key: str
    version: int = Field(ge=1)
    parameters: dict[str, DecimalString | str | int | bool]
    active: bool = False


class RecommendationState(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class AIProfileRecommendation(ContractBase):
    profile_id: UUID
    recommended_parameters: dict[str, DecimalString | str | int | bool]
    evidence_session_ids: list[UUID]
    rationale: str
    state: RecommendationState = RecommendationState.PROPOSED


class MarketDataType(StrEnum):
    BARS = "bars"
    QUOTES = "quotes"
    TRADES = "trades"
    NEWS = "news"


class TimeFrameKind(StrEnum):
    MIN_1 = "1Min"
    MIN_5 = "5Min"
    MIN_15 = "15Min"
    HOUR_1 = "1Hour"
    DAY_1 = "1Day"


class HistoricalBar(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timestamp: datetime
    open: DecimalString = Field(gt=0)
    high: DecimalString = Field(gt=0)
    low: DecimalString = Field(gt=0)
    close: DecimalString = Field(gt=0)
    volume: int = Field(ge=0)
    trade_count: int | None = Field(default=None, ge=0)
    vwap: DecimalString | None = Field(default=None, gt=0)

    @field_validator("timestamp")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(UTC)


class HistoricalMarketDataRecord(ContractBase):
    symbol: str
    data_type: MarketDataType
    timeframe: TimeFrameKind | None = None
    start_time: datetime
    end_time: datetime
    query_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    source: str
    item_count: int = Field(ge=0)
    payload: dict[str, Any]
    is_immutable: bool = False

    @field_validator("start_time", "end_time")
    @classmethod
    def require_aware_range_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(UTC)


class LLMEventAnalysis(ContractBase):
    article_id: str
    symbol: str
    headline: str
    event_type: str
    sentiment: str
    significance_score: DecimalString = Field(ge=0, le=100)
    expected_reaction_pct: DecimalString | None = None
    rationale: str
    model_name: str
    prompt_version: str
    raw_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class TrendDirection(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class RSICondition(StrEnum):
    OVERSOLD = "oversold"
    OVERBOUGHT = "overbought"
    NEUTRAL = "neutral"


class MACDCrossover(StrEnum):
    BULLISH_CROSS = "bullish_cross"
    BEARISH_CROSS = "bearish_cross"
    NONE = "none"


class MACDSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    macd: DecimalString
    signal: DecimalString
    histogram: DecimalString
    crossover: MACDCrossover


class MovingAverages(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sma_20: DecimalString | None = None
    sma_50: DecimalString | None = None
    sma_200: DecimalString | None = None
    price_vs_sma20_pct: DecimalString | None = None
    price_vs_sma50_pct: DecimalString | None = None
    price_vs_sma200_pct: DecimalString | None = None


class BollingerBands(BaseModel):
    model_config = ConfigDict(extra="forbid")
    upper: DecimalString
    middle: DecimalString
    lower: DecimalString
    bandwidth_pct: DecimalString
    percent_b: DecimalString


class QuantitativeAnalysisReport(ContractBase):
    symbol: str
    current_price: DecimalString
    trend: TrendDirection
    momentum_score: DecimalString = Field(ge=0, le=100)
    rsi_14: DecimalString = Field(ge=0, le=100)
    rsi_condition: RSICondition
    macd: MACDSignal
    moving_averages: MovingAverages
    bollinger_bands: BollingerBands
    atr_14: DecimalString
    volatility_annualized_pct: DecimalString
    volume_surge_ratio: DecimalString
    summary: str
