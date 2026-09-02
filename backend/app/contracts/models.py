from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    field_validator,
    model_validator,
)

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


class ReactionClassification(StrEnum):
    UNDERREACTION = "UNDERREACTION"
    OVERREACTION = "OVERREACTION"
    FAIR_REACTION = "FAIR_REACTION"


class CatalystDecayStatus(StrEnum):
    FRESH_CATALYST = "fresh_catalyst"
    ACTIVE_DIGESTION = "active_digestion"
    AGING_CATALYST = "aging_catalyst"
    PRICED_IN = "priced_in"


class ResearchReport(ContractBase):
    symbol: str
    thesis: str
    confidence: DecimalString = Field(ge=0, le=1)
    freshness_seconds: int = Field(ge=0)
    evidence: list[EvidenceItem]
    limitations: list[str] = Field(default_factory=list)
    actual_reaction_pct: DecimalString | None = None
    expected_reaction_pct: DecimalString | None = None
    reaction_gap_pct: DecimalString | None = None
    direction_adjusted_gap_pct: DecimalString | None = None
    volume_ratio: DecimalString | None = Field(default=None, ge=0)
    classification: ReactionClassification | None = None
    opportunity_score: DecimalString | None = Field(default=None, ge=0, le=100)
    historical_median_reaction_pct: DecimalString | None = None
    historical_dispersion_pct: DecimalString | None = None
    analog_count: int = 0
    analog_similarity_score: DecimalString = Field(default=Decimal("50.0"), ge=0, le=100)
    historical_volatility_pct: DecimalString | None = None
    implied_volatility_pct: DecimalString | None = None
    iv_hv_ratio: DecimalString | None = None
    options_implied_move_pct: DecimalString | None = None
    event_age_hours: DecimalString = Decimal("0.0")
    catalyst_decay_factor: DecimalString = Decimal("1.0")
    catalyst_decay_status: CatalystDecayStatus = CatalystDecayStatus.FRESH_CATALYST
    event_published_at: datetime | None = None
    provider_observed_at: datetime | None = None
    calculation_window_start: datetime | None = None
    calculation_window_end: datetime | None = None
    methodology_version: str = "reaction_event_aligned_v2"


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
    # Alpaca requires an explicit position intent for every multi-leg option leg.
    # Keep it optional at the research boundary, but execution rejects missing intents.
    position_intent: (
        Literal["buy_to_open", "buy_to_close", "sell_to_open", "sell_to_close"] | None
    ) = None


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
    profit_arm_pct: DecimalString = Field(default=Decimal("20.0"), ge=0)
    profit_trailing_giveback_points: DecimalString = Field(default=Decimal("10.0"), gt=0)
    hard_take_profit_pct: DecimalString = Field(default=Decimal("40.0"), gt=0)
    hard_stop_loss_pct: DecimalString = Field(default=Decimal("50.0"), ge=50, le=50)
    thesis_failure_cycles: int = Field(default=2, ge=1)
    time_stop_trading_minutes: int = Field(default=390, ge=1)
    minimum_mfe_pct: DecimalString = Field(default=Decimal("10.0"), ge=0)
    dte_threshold: int = Field(default=7, ge=2, le=14)
    max_hold_days: int = Field(default=14, ge=3, le=45)

    @model_validator(mode="after")
    def validate_adaptive_profit_policy(self) -> ExitPolicy:
        if self.profit_arm_pct >= self.hard_take_profit_pct:
            raise ValueError("profit arm must be below hard take-profit")
        if self.profit_trailing_giveback_points >= self.profit_arm_pct:
            raise ValueError("trailing giveback must be below profit arm")
        return self


class ShadowCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    strategy: OptionStrategy | None = None
    allocation_multiplier: DecimalString = Field(default=Decimal("1.0"), gt=0)
    rationale: str = ""


class OptionPayoffEconomics(BaseModel):
    """Deterministic option economics bound into an executable proposal."""

    model_config = ConfigDict(extra="forbid")

    method: str = Field(min_length=1)
    expected_profit_per_contract: DecimalString
    expected_loss_per_contract: DecimalString = Field(ge=0)
    max_loss_per_contract: DecimalString = Field(gt=0)
    premium_per_contract: DecimalString = Field(gt=0)
    slippage_per_contract: DecimalString = Field(ge=0)
    fill_probability: DecimalString = Field(ge=0, le=1)
    net_ev_r: DecimalString
    reward_risk_ratio: DecimalString = Field(ge=0)


class TradeProposal(ContractBase):
    proposal_version: int = Field(default=1, ge=1)
    research_report_id: UUID
    symbol: str
    strategy: OptionStrategy
    quantity: int = Field(ge=1)
    rationale: str
    exit_policy: ExitPolicy = Field(default_factory=ExitPolicy)
    shadow_candidates: list[ShadowCandidate] = Field(default_factory=list)
    option_economics: OptionPayoffEconomics | None = None
    research_bundle_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    catalyst_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    thesis_key: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
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
    PASS = "PASS"
    MODIFY = "MODIFY"
    FAIL = "FAIL"


class RulePriority(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"
    P5 = "P5"


class ReasonCode(StrEnum):
    RULESET_NOT_CONFIGURED = "RULESET_NOT_CONFIGURED"
    STALE_DATA = "STALE_DATA"
    OUTSIDE_TRADING_WINDOW = "OUTSIDE_TRADING_WINDOW"
    HACKATHON_ENTRY_CUTOFF = "HACKATHON_ENTRY_CUTOFF"
    HACKATHON_FORCE_FLATTEN = "HACKATHON_FORCE_FLATTEN"
    HACKATHON_SCORING_WINDOW = "HACKATHON_SCORING_WINDOW"
    EXPIRY_ASSIGNMENT_RISK = "EXPIRY_ASSIGNMENT_RISK"
    DRAWDOWN_CAUTION = "DRAWDOWN_CAUTION"
    DRAWDOWN_DEFENSIVE = "DRAWDOWN_DEFENSIVE"
    DRAWDOWN_HALT = "DRAWDOWN_HALT"
    CASH_BUFFER_BREACH = "CASH_BUFFER_BREACH"
    TICKER_CONCENTRATION_BREACH = "TICKER_CONCENTRATION_BREACH"
    HIGH_IV_SINGLE_LEG_PROHIBITED = "HIGH_IV_SINGLE_LEG_PROHIBITED"
    RISK_LIMIT_BREACH = "RISK_LIMIT_BREACH"
    RISK_ASSESSMENT_MISSING = "RISK_ASSESSMENT_MISSING"
    RISK_ASSESSMENT_REJECTED = "RISK_ASSESSMENT_REJECTED"
    RISK_DATA_STALE = "RISK_DATA_STALE"
    LIQUIDITY_LIMIT_BREACH = "LIQUIDITY_LIMIT_BREACH"
    MARKET_REGIME_BLOCKED = "MARKET_REGIME_BLOCKED"
    IV_RANK_LIMIT_BREACH = "IV_RANK_LIMIT_BREACH"
    INVALID_STRATEGY = "INVALID_STRATEGY"
    ECONOMICS_MISMATCH = "ECONOMICS_MISMATCH"
    OPPORTUNITY_SCORE_BELOW_FLOOR = "OPPORTUNITY_SCORE_BELOW_FLOOR"
    EXPECTED_VALUE_BELOW_FLOOR = "EXPECTED_VALUE_BELOW_FLOOR"
    NEGATIVE_EXPECTED_VALUE = "NEGATIVE_EXPECTED_VALUE"
    REWARD_RISK_BELOW_FLOOR = "REWARD_RISK_BELOW_FLOOR"
    PAYLOAD_MISMATCH = "PAYLOAD_MISMATCH"
    PROFILE_OUT_OF_BOUNDS = "PROFILE_OUT_OF_BOUNDS"
    UNSUPPORTED_INSTRUMENT = "UNSUPPORTED_INSTRUMENT"


class MarketRegime(StrEnum):
    NORMAL = "normal"
    VOLATILE = "volatile"
    EVENT = "event"
    CRISIS = "crisis"


class PortfolioRiskState(StrEnum):
    NORMAL = "normal"
    CAUTION = "caution"
    DEFENSIVE = "defensive"
    HALT = "halt"


class RuleEvaluation(ContractBase):
    rule_id: str
    proposal_id: UUID
    priority: RulePriority
    ruleset_version: str
    outcome: RuleOutcome
    reason_codes: list[ReasonCode]
    explanation: str
    input_snapshot_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    modified_proposal_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class AllowedOrderPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    strategy: OptionStrategy
    quantity: int = Field(ge=1)


class AuthorizationOutcome(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MODIFIED_PENDING_ACCEPTANCE = "MODIFIED_PENDING_ACCEPTANCE"


class AuthorizationDecision(ContractBase):
    proposal_id: UUID
    proposal_version: int = Field(ge=1)
    proposal_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    ruleset_id: str
    ruleset_version: str
    profile_id: UUID
    profile_version: int = Field(ge=1)
    outcome: AuthorizationOutcome
    allowed_order_payload_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    allowed_order_payload: AllowedOrderPayload | None = None
    market_snapshot_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    portfolio_snapshot_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    market_regime: MarketRegime
    portfolio_risk_state: PortfolioRiskState
    decision_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime
    account_observed_at: datetime
    supported_options_level: int = Field(ge=0)
    account_verified: bool
    rule_trace: list[RuleEvaluation] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_authorization_binding(self) -> AuthorizationDecision:
        if (self.allowed_order_payload_digest is None) != (self.allowed_order_payload is None):
            raise ValueError("allowed order payload digest and payload must be provided together")
        if self.outcome is AuthorizationOutcome.APPROVE and (
            self.allowed_order_payload_digest is None or self.allowed_order_payload is None
        ):
            raise ValueError("approved authorization requires an allowed order payload binding")
        return self

    @field_validator("decision_at", "expires_at", "account_observed_at")
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


class ExecutionOperation(StrEnum):
    ENTRY = "entry"
    EXIT = "exit"


class ExitReason(StrEnum):
    PNL_THRESHOLD = "pnl_threshold"
    HARD_STOP_LOSS = "hard_stop_loss"
    OPPOSITE_DIRECTION = "opposite_direction"
    THESIS_INVALIDATED = "thesis_invalidated"
    TRAILING_PROFIT = "trailing_profit"
    HARD_TAKE_PROFIT = "hard_take_profit"
    STAGNATION_TIME_STOP = "stagnation_time_stop"
    MAX_HOLD_DAYS = "max_hold_days"
    DTE_THRESHOLD = "dte_threshold"
    HACKATHON_FORCE_FLATTEN = "hackathon_force_flatten"


class ExecutionLegState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    ratio_qty: int = Field(ge=1)
    position_intent: Literal["buy_to_open", "buy_to_close", "sell_to_open", "sell_to_close"]
    status: ExecutionStatus


class ExecutionReceipt(ContractBase):
    # Mandatory exits are position-level actions and therefore have no
    # proposal/authorization binding. Entry receipts retain their proposal ID.
    proposal_id: UUID | None = None
    client_order_id: str
    broker_order_id: str | None = None
    payload_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: ExecutionStatus
    operation: ExecutionOperation = ExecutionOperation.ENTRY
    symbol: str | None = None
    exit_reason: ExitReason | None = None
    requested_quantity: DecimalString | None = None
    strategy_position_id: UUID | None = None
    legs: list[ExecutionLegState] = Field(default_factory=list)
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


class EvaluationRoot(ContractBase):
    """Immutable lineage anchor shared by authorization and ShadowFund evaluation."""

    root_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    outcome: str = Field(min_length=1)
    evidence_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    proposal_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    market_snapshot_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    portfolio_snapshot_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    is_immutable: Literal[True] = True


class AIProfileKind(StrEnum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class AIProfileStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class ActivationMode(StrEnum):
    MANUAL = "manual"


class AIProfileParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_position_size_pct: DecimalString = Field(ge=Decimal("1.5"), le=Decimal("2.5"))
    opportunity_score_threshold: DecimalString = Field(ge=75, le=95)


class AIProfile(ContractBase):
    profile_key: AIProfileKind
    version: int = Field(ge=1)
    status: AIProfileStatus
    ruleset_id: str
    ruleset_version: str
    activation_mode: ActivationMode = ActivationMode.MANUAL
    effective_at: datetime | None = None
    expires_at: datetime | None = None
    parameters: AIProfileParameters


class RecommendationState(StrEnum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    APPLIED = "applied"
    REJECTED = "rejected"


class AIProfileRecommendation(ContractBase):
    profile_id: UUID
    ruleset_id: str
    ruleset_version: str
    recommended_parameters: AIProfileParameters
    evidence_session_ids: list[UUID]
    rationale: str
    state: RecommendationState = RecommendationState.PROPOSED
    manual_review_required: Literal[True] = True
    validation_reason_codes: list[ReasonCode] = Field(default_factory=list)


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


class NewsEventCategory(StrEnum):
    EARNINGS = "earnings"
    GUIDANCE = "guidance"
    M_AND_A = "m_and_a"
    REGULATORY_LEGAL = "regulatory_legal"
    PRODUCT_INNOVATION = "product_innovation"
    ANALYST_ACTION = "analyst_action"
    MANAGEMENT_CHANGE = "management_change"
    MACRO_GEOPOLITICAL = "macro_geopolitical"
    ROUTINE_PR = "routine_pr"
    OTHER = "other"


class CatalystMateriality(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NOISE = "noise"


class GuidanceChange(StrEnum):
    RAISED = "raised"
    LOWERED = "lowered"
    REAFFIRMED = "reaffirmed"
    WITHDRAWN = "withdrawn"
    NOT_APPLICABLE = "not_applicable"


class EarningsSurpriseData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    eps_surprise_pct: DecimalString | None = None
    revenue_surprise_pct: DecimalString | None = None
    quarter: str | None = None


class LLMEventAnalysis(ContractBase):
    article_id: str
    symbol: str
    headline: str
    source: str = "unknown"
    source_confidence: DecimalString = Field(default=Decimal("50.0"), ge=0, le=100)
    event_age_seconds: int = Field(default=0, ge=0)
    published_at: datetime | None = None
    provider_observed_at: datetime | None = None
    event_category: NewsEventCategory = NewsEventCategory.OTHER
    event_type: str = "other"
    catalyst_materiality: CatalystMateriality = CatalystMateriality.MEDIUM
    sentiment: str
    significance_score: DecimalString = Field(ge=0, le=100)
    expected_reaction_pct: DecimalString | None = None
    guidance_change: GuidanceChange = GuidanceChange.NOT_APPLICABLE
    earnings_surprise: EarningsSurpriseData | None = None
    has_contradictory_signals: bool = False
    contradiction_notes: str | None = None
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


class TrendConfirmation(StrEnum):
    STRONG_UPTREND_CONFIRMED = "strong_uptrend_confirmed"
    PULLBACK_IN_UPTREND = "pullback_in_uptrend"
    GOLDEN_CROSS = "golden_cross"
    RANGE_BOUND = "range_bound"
    OVERSOLD_BOUNCE = "oversold_bounce"
    DEATH_CROSS = "death_cross"
    BREAKDOWN_CONFIRMED = "breakdown_confirmed"


class PriceDisplacement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gap_size_pct: DecimalString = Decimal("0.0")
    displacement_1d_pct: DecimalString = Decimal("0.0")
    displacement_3d_pct: DecimalString | None = None
    displacement_5d_pct: DecimalString | None = None
    displacement_20d_pct: DecimalString | None = None


class QuantitativeAnalysisReport(ContractBase):
    symbol: str = Field(min_length=1)
    current_price: DecimalString = Field(ge=0)
    trend: TrendDirection
    trend_confirmation: TrendConfirmation = TrendConfirmation.RANGE_BOUND
    momentum_score: DecimalString = Field(ge=0, le=100)
    rsi_14: DecimalString = Field(ge=0, le=100)
    rsi_condition: RSICondition
    macd: MACDSignal
    moving_averages: MovingAverages
    bollinger_bands: BollingerBands
    atr_14: DecimalString
    volatility_annualized_pct: DecimalString
    volume_surge_ratio: DecimalString
    price_displacement: PriceDisplacement = Field(default_factory=PriceDisplacement)
    summary: str


class CompetitiveMoat(StrEnum):
    WIDE = "wide"
    NARROW = "narrow"
    NONE = "none"
    DETERIORATING = "deteriorating"


class RelativePerformance(StrEnum):
    OUTPERFORMING = "outperforming"
    UNDERPERFORMING = "underperforming"
    MIXED = "mixed"
    INLINE = "inline"


class IndustrySentiment(StrEnum):
    POSITIVE = "positive"
    MODERATELY_POSITIVE = "moderately_positive"
    MIXED = "mixed"
    MODERATELY_NEGATIVE = "moderately_negative"
    NEGATIVE = "negative"


class PeerPerformance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str
    price_change_5d_pct: DecimalString
    price_change_20d_pct: DecimalString


class SectorRegimeConfirmation(StrEnum):
    LEADING_SECTOR_OUTPERFORMER = "leading_sector_outperformer"
    IDIOSYNCRATIC_DECOUPLING = "idiosyncratic_decoupling"
    BROAD_BETA_CONVERGENCE = "broad_beta_convergence"
    SECTOR_UNDER_PRESSURE = "sector_under_pressure"
    LAGGING_IN_BULL_SECTOR = "lagging_in_bull_sector"


class PeerReactionDynamics(StrEnum):
    DIVERGENT_WINNER = "divergent_winner"
    SYMPATHETIC_SECTOR_SURGE = "sympathetic_sector_surge"
    ISOLATED_REACTION = "isolated_reaction"
    PEER_DRAGGED_DOWN = "peer_dragged_down"


class IndustryAnalysisReport(ContractBase):
    symbol: str
    sector_name: str
    sector_etf: str
    sector_health_score: DecimalString = Field(ge=0, le=100)
    stock_return_5d_pct: DecimalString
    stock_return_20d_pct: DecimalString
    sector_return_5d_pct: DecimalString
    sector_return_20d_pct: DecimalString
    spy_return_5d_pct: DecimalString = Decimal("0.0")
    spy_return_20d_pct: DecimalString = Decimal("0.0")
    relative_alpha_5d_pct: DecimalString
    relative_alpha_20d_pct: DecimalString
    stock_vs_spy_alpha_20d_pct: DecimalString = Decimal("0.0")
    peer_dispersion_20d_pct: DecimalString = Decimal("0.0")
    sector_relative_performance: RelativePerformance
    peer_relative_performance: RelativePerformance
    sector_regime_confirmation: SectorRegimeConfirmation = (
        SectorRegimeConfirmation.BROAD_BETA_CONVERGENCE
    )
    peer_reaction_dynamics: PeerReactionDynamics = PeerReactionDynamics.ISOLATED_REACTION
    peers: list[PeerPerformance]
    competitive_moat: CompetitiveMoat
    overall_sentiment: IndustrySentiment
    tailwinds: list[str] = Field(default_factory=list)
    headwinds: list[str] = Field(default_factory=list)
    thesis: str


class FundamentalHealth(StrEnum):
    EXCELLENT = "excellent"
    HEALTHY = "healthy"
    MODERATE = "moderate"
    VULNERABLE = "vulnerable"
    DISTRESSED = "distressed"


class ValuationStance(StrEnum):
    UNDERVALUED = "undervalued"
    FAIRLY_VALUED = "fairly_valued"
    PREMIUM = "premium"
    OVERVALUED = "overvalued"


class AltmanZone(StrEnum):
    SAFE = "safe"
    GREY = "grey"
    DISTRESS = "distress"


class ProfitabilityMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gross_margin_pct: DecimalString
    operating_margin_pct: DecimalString
    net_margin_pct: DecimalString
    roe_pct: DecimalString
    roa_pct: DecimalString


class SolvencyMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_ratio: DecimalString
    debt_to_equity: DecimalString
    interest_coverage_ratio: DecimalString
    net_debt_millions: DecimalString


class ValuationMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pe_ratio_ttm: DecimalString | None = None
    ev_to_ebitda: DecimalString | None = None
    price_to_book: DecimalString | None = None
    fcf_yield_pct: DecimalString | None = None
    free_cash_flow_millions: DecimalString


class EstimateRevisionTrend(StrEnum):
    UPWARD = "upward"
    DOWNWARD = "downward"
    MIXED = "mixed"
    NEUTRAL = "neutral"


class BalanceSheetRedFlag(StrEnum):
    ACCRUAL_EARNINGS_DIVERGENCE = "accrual_earnings_divergence"
    WORKING_CAPITAL_DEFICIT = "working_capital_deficit"
    HIGH_LEVERAGE_BURDEN = "high_leverage_burden"
    INTEREST_COVERAGE_STRAIN = "interest_coverage_strain"
    ALTMAN_DISTRESS_RISK = "altman_distress_risk"
    NONE_DETECTED = "none_detected"


class EarningsSurpriseEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quarter: str | None = None
    eps_actual: DecimalString | None = None
    eps_consensus: DecimalString | None = None
    eps_surprise_pct: DecimalString | None = None
    revenue_actual_millions: DecimalString | None = None
    revenue_consensus_millions: DecimalString | None = None
    revenue_surprise_pct: DecimalString | None = None
    guidance_change: GuidanceChange = GuidanceChange.NOT_APPLICABLE
    gross_margin_surprise_bps: DecimalString | None = None
    operating_margin_surprise_bps: DecimalString | None = None
    estimate_revision_trend: EstimateRevisionTrend = EstimateRevisionTrend.NEUTRAL


class FundamentalAnalysisReport(ContractBase):
    symbol: str = Field(min_length=1)
    current_price: DecimalString = Field(ge=0)
    market_cap_millions: DecimalString = Field(ge=0)
    enterprise_value_millions: DecimalString = Field(ge=0)
    profitability: ProfitabilityMetrics
    solvency: SolvencyMetrics
    valuation: ValuationMetrics
    piotroski_f_score: int = Field(ge=0, le=9)
    altman_z_score: DecimalString
    altman_zone: AltmanZone
    composite_quality_score: DecimalString = Field(ge=0, le=100)
    fundamental_health: FundamentalHealth
    valuation_stance: ValuationStance
    earnings_event: EarningsSurpriseEvent | None = None
    red_flags: list[BalanceSheetRedFlag] = Field(default_factory=list)
    summary: str
    provenance: Literal["illustrative_fixture", "sec_filing"] = "illustrative_fixture"
    data_as_of: datetime | None = None


class MacroRegime(StrEnum):
    RISK_ON = "risk_on"
    RISK_OFF = "risk_off"
    EXPANSIONARY = "expansionary"
    CONTRACTIONARY = "contractionary"
    STAGFLATIONARY = "stagflationary"
    TRANSITIONAL = "transitional"


class RateEnvironment(StrEnum):
    RATE_CUT_CYCLE = "rate_cut_cycle"
    PAUSE_ELEVATED = "pause_elevated"
    RISING_RATES = "rising_rates"
    NEUTRAL = "neutral"


class MarketStressLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class MarketStressDirection(StrEnum):
    ESCALATING = "escalating"
    STABLE = "stable"
    EASING = "easing"


class EconomicEventProximity(StrEnum):
    FOMC_DECISION_NEAR = "fomc_decision_near"
    CPI_INFLATION_NEAR = "cpi_inflation_near"
    JOBS_PAYROLLS_NEAR = "jobs_payrolls_near"
    HIGH_IMPACT_EVENT_AHEAD = "high_impact_event_ahead"
    STANDARD_CALENDAR = "standard_calendar"


class AssetMacroImpact(StrEnum):
    STRONG_TAILWIND = "strong_tailwind"
    MODERATE_TAILWIND = "moderate_tailwind"
    NEUTRAL = "neutral"
    MODERATE_HEADWIND = "moderate_headwind"
    SEVERE_HEADWIND = "severe_headwind"


class MacroAssetPerformance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_symbol: str
    asset_name: str
    price_change_5d_pct: DecimalString
    price_change_20d_pct: DecimalString


class MacroAnalysisReport(ContractBase):
    symbol: str = Field(min_length=1)
    macro_regime: MacroRegime
    rate_environment: RateEnvironment
    market_stress_level: MarketStressLevel
    market_stress_direction: MarketStressDirection = MarketStressDirection.STABLE
    realized_volatility_pct: DecimalString = Decimal("15.0")
    volatility_change_5d_pct: DecimalString = Decimal("0.0")
    macro_climate_score: DecimalString = Field(ge=0, le=100)
    economic_event_proximity: EconomicEventProximity = EconomicEventProximity.STANDARD_CALENDAR
    asset_macro_impact: AssetMacroImpact = AssetMacroImpact.NEUTRAL
    assets: list[MacroAssetPerformance]
    macro_tailwinds: list[str] = Field(default_factory=list)
    macro_headwinds: list[str] = Field(default_factory=list)
    stock_macro_sensitivity: str
    thesis: str


class TradeDirection(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class TradeVerdict(StrEnum):
    PROCEED_TO_OPTIONS_PROPOSAL = "proceed_to_options_proposal"
    NO_TRADE = "no_trade"
    PROPOSE_TRADE = "propose_trade"


class OptionStructure(StrEnum):
    LONG_CALL = "long_call"
    LONG_PUT = "long_put"
    BULL_CALL_SPREAD = "bull_call_spread"
    BEAR_PUT_SPREAD = "bear_put_spread"
    NO_TRADE = "no_trade"


class ShadowAlternativeIntent(BaseModel):
    """AI research intent for a non-executable ShadowFund branch.

    Contract symbols and prices are deliberately absent. Deterministic code
    selects them from the same eligible option universe as the primary
    proposal, and this model can never become an order payload.
    """

    model_config = ConfigDict(extra="forbid")

    direction: Literal[TradeDirection.BULLISH, TradeDirection.BEARISH]
    preferred_structure: Literal[
        OptionStructure.LONG_CALL,
        OptionStructure.LONG_PUT,
        OptionStructure.BULL_CALL_SPREAD,
        OptionStructure.BEAR_PUT_SPREAD,
    ]
    rationale: str = Field(min_length=1, max_length=500)


class SpecialistScores(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reaction_opportunity_score: DecimalString
    quant_momentum_score: DecimalString
    fundamental_quality_score: DecimalString
    sector_health_score: DecimalString
    macro_climate_score: DecimalString
    news_sentiment_score: DecimalString


class TradeDecisionReport(ContractBase):
    symbol: str = Field(min_length=1)
    verdict: TradeVerdict
    direction: TradeDirection
    recommended_structure: OptionStructure
    composite_opportunity_score: DecimalString = Field(ge=0, le=100)
    bullish_opportunity_score: DecimalString = Field(ge=0, le=100)
    bearish_opportunity_score: DecimalString = Field(ge=0, le=100)
    confidence_score: DecimalString = Field(ge=0, le=100)
    current_price: DecimalString = Field(ge=0)
    target_price: DecimalString | None = None
    exit_policy: ExitPolicy
    specialist_scores: SpecialistScores
    evidence_summary: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    contradiction_analysis: str
    portfolio_fit: str = ""
    options_only_constraint_acknowledged: bool = True
    synthesis_rationale: str
    key_risks: list[str] = Field(default_factory=list)
    shadow_alternative_intent: ShadowAlternativeIntent | None = None
    provenance: Literal["live_research", "historical_simulation", "illustrative_fixture"] = (
        "live_research"
    )
    evidence_freshness_seconds: int | None = Field(default=None, ge=0)
    analog_count: int = Field(default=0, ge=0)
    catalyst_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    scoring_methodology_version: str = "directional_composite_v2"


class NoTradeDecision(ContractBase):
    """Explicit synthesis outcome when evidence cannot support a proposal."""

    kind: Literal["no_trade"] = "no_trade"
    symbol: str = Field(min_length=1)
    research_bundle_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    reason: str = Field(min_length=1)


class ProposalDecision(ContractBase):
    """Canonical proposal result, bound to the immutable research bundle."""

    kind: Literal["proposal"] = "proposal"
    research_bundle_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    proposal: TradeProposal


DecisionSynthesisResult = Annotated[ProposalDecision | NoTradeDecision, Field(discriminator="kind")]
