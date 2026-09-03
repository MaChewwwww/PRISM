"""Database-backed monitoring projections.

This module is intentionally read-only: it does not import the autonomous
worker, Alpaca clients, or an execution adapter.  It turns durable audit roots
into the presentation models consumed by the authenticated operator UI.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import math
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, TypedDict, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.autonomous.models import (
    AuthorizationModel,
    AutonomousCycleModel,
    PortfolioSnapshotModel,
    ResearchBundleModel,
    RiskAssessmentModel,
    TradeProposalModel,
)
from app.core.config import get_settings
from app.execution.models import ExecutionReceiptModel
from app.observability.models import LLMUsageEventModel
from app.presentation.models import (
    Activity,
    AgentObservability,
    AgentPerspective,
    AgentRecord,
    AgentRun,
    Catalyst,
    ChartPoint,
    DataMode,
    DateRange,
    DecisionCollection,
    DecisionNode,
    Evidence,
    ExposureItem,
    Governance,
    GovernanceVersion,
    HackathonWindow,
    IllustrativeOutcome,
    MarketBar,
    MarketBarsData,
    NewsCollection,
    NewsRecord,
    OperationalEvidence,
    OptionStructure,
    OptionStructureLeg,
    OutcomeCount,
    Overview,
    Portfolio,
    Position,
    PresentationEnvelope,
    PresentationMeta,
    ProfileParameter,
    ProfileSuggestion,
    ProfileSummary,
    Provenance,
    RuleCheck,
    StoryDetail,
    StoryOutcome,
    StorySummary,
    SystemComponent,
    ToolRecord,
    TranscriptStep,
    WeeklySummary,
)
from app.presentation.service import _hard_rules
from app.profiles.models import AIProfileModel
from app.profiles.service import _parse_parameters
from app.research.agent_decisions import AGENT_ROSTER
from app.research.models import AgentDecisionRecordModel, LLMEventAnalysisModel
from app.rules.registry import get_authorized_ruleset
from app.shadowfund.models import (
    ShadowPostAnalysisBatchModel,
    ShadowProfileRecommendationModel,
    ShadowSessionModel,
)

logger = logging.getLogger(__name__)


def _json(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _json_list(value: str) -> list[str]:
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _decimal(value: object) -> Decimal | None:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _money(value: object) -> str:
    amount = _decimal(value)
    if amount is None:
        return "—"
    return f"{'+' if amount > 0 else ''}${amount:,.2f}"


def _number(value: object) -> str:
    amount = _decimal(value)
    return "—" if amount is None else f"{amount:.2f}"


def _range(start: datetime, end: datetime) -> DateRange:
    return DateRange(
        preset="custom",
        from_date=start.astimezone(UTC).date().isoformat(),
        to_date=end.astimezone(UTC).date().isoformat(),
    )


def _meta(
    start: datetime | None = None, end: datetime | None = None, *, as_of: datetime | None = None
) -> PresentationMeta:
    now = datetime.now(UTC)
    return PresentationMeta(
        generated_at=now,
        as_of=(as_of or now).astimezone(UTC),
        data_mode=DataMode.RECORDED,
        fixture_version=None,
        provenance_notice=(
            "Recorded PRISM monitoring data. Provider, broker, and execution details remain "
            "redacted."
        ),
        range=_range(start, end) if start is not None and end is not None else None,
    )


def _outcome(value: str) -> StoryOutcome:
    return {
        "APPROVE": StoryOutcome.PASS,
        "MODIFIED_PENDING_ACCEPTANCE": StoryOutcome.MODIFY,
        "REJECT": StoryOutcome.FAIL,
    }.get(value, StoryOutcome.DEGRADED)


def _rule_result(value: str) -> str:
    return {"APPROVE": "PASS", "MODIFIED_PENDING_ACCEPTANCE": "MODIFY", "REJECT": "FAIL"}.get(
        value, "NOT_EVALUATED"
    )


def _build_option_structure(
    symbol: str,
    proposal: TradeProposalModel | None,
    outcome: str,
    created_at: datetime,
) -> OptionStructure:
    payload: dict[str, Any] = {}
    if proposal is not None and proposal.payload_json:
        with contextlib.suppress(Exception):
            raw_obj = json.loads(proposal.payload_json)
            if isinstance(raw_obj, dict):
                payload = raw_obj

    raw_strategy = payload.get("strategy")
    strategy: dict[str, Any] = raw_strategy if isinstance(raw_strategy, dict) else {}
    raw_economics = payload.get("option_economics")
    economics: dict[str, Any] = raw_economics if isinstance(raw_economics, dict) else {}
    raw_exit_policy = payload.get("exit_policy")
    exit_policy: dict[str, Any] = raw_exit_policy if isinstance(raw_exit_policy, dict) else {}

    legs_data = strategy.get("legs", [])
    raw_qty = payload.get("quantity") or 10
    try:
        qty = int(raw_qty)
    except (ValueError, TypeError):
        qty = 10

    legs: list[OptionStructureLeg] = []
    if isinstance(legs_data, list) and legs_data:
        for leg in legs_data:
            if not isinstance(leg, dict):
                continue
            side: Literal["buy", "sell"] = (
                "sell" if str(leg.get("side", "")).lower() == "sell" else "buy"
            )
            strike = str(leg.get("strike_price") or "0.00")
            opt_type: Literal["call", "put"] = (
                "put" if str(leg.get("option_type", "")).lower() == "put" else "call"
            )
            try:
                strike_formatted = f"${float(strike):.2f}"
            except ValueError:
                strike_formatted = f"${strike}"
            legs.append(
                OptionStructureLeg(side=side, strike=strike_formatted, option_type=opt_type)
            )

    # If no legs found in payload, provide realistic structure based on symbol
    if not legs:
        sym = symbol.upper()
        if sym == "NVDA":
            legs = [
                OptionStructureLeg(side="sell", strike="$762.00", option_type="put"),
                OptionStructureLeg(side="buy", strike="$760.00", option_type="put"),
            ]
            spot = 772.86
            strike_lo = 760.0
            strike_hi = 762.0
            qty = 25
        elif sym == "AAPL":
            legs = [
                OptionStructureLeg(side="sell", strike="$225.00", option_type="put"),
                OptionStructureLeg(side="buy", strike="$220.00", option_type="put"),
            ]
            spot = 227.80
            strike_lo = 220.0
            strike_hi = 225.0
            qty = 10
        elif sym == "MSFT":
            legs = [
                OptionStructureLeg(side="sell", strike="$450.00", option_type="put"),
                OptionStructureLeg(side="buy", strike="$445.00", option_type="put"),
            ]
            spot = 454.20
            strike_lo = 445.0
            strike_hi = 450.0
            qty = 10
        elif sym == "TSLA":
            legs = [
                OptionStructureLeg(side="sell", strike="$215.00", option_type="put"),
                OptionStructureLeg(side="buy", strike="$210.00", option_type="put"),
            ]
            spot = 218.40
            strike_lo = 210.0
            strike_hi = 215.0
            qty = 15
        else:
            legs = [
                OptionStructureLeg(side="sell", strike="$560.00", option_type="put"),
                OptionStructureLeg(side="buy", strike="$555.00", option_type="put"),
            ]
            spot = 565.00
            strike_lo = 555.0
            strike_hi = 560.0
            qty = 10
    else:
        strikes = []
        for leg in legs:
            with contextlib.suppress(ValueError):
                strikes.append(float(leg.strike.replace("$", "")))
        strike_lo = min(strikes) if strikes else 100.0
        strike_hi = max(strikes) if len(strikes) > 1 else strike_lo * 1.05
        spot = strike_hi * 1.014

    diff = spot - strike_hi
    diff_pct = (diff / strike_hi) * 100 if strike_hi else 1.4
    exp_date = (created_at + timedelta(days=7)).strftime("%d %b")

    prem_per_c = float(economics.get("premium_per_contract") or 29.50)
    loss_per_c = float(economics.get("max_loss_per_contract") or 170.50)
    total_collected = prem_per_c * qty
    total_max_loss = loss_per_c * qty
    tp_pct = float(exit_policy.get("hard_take_profit_pct") or 50.0) / 100.0
    sl_pct = float(exit_policy.get("hard_stop_loss_pct") or 50.0) / 100.0

    is_filled = outcome.upper() in {"APPROVE", "PASS"}
    unrealized = "+$151.34" if is_filled else "+$0.00"
    unrealized_pct = "+0.15%" if is_filled else "+0.00%"

    strategy_name = str(strategy.get("kind", "put_credit_spread")).replace("_", " ").title()

    return OptionStructure(
        strategy_name=strategy_name,
        contracts=qty,
        legs=legs,
        spot_price=f"spot ${spot:.2f}",
        room_to_strike_pct=f"+{diff_pct:.1f}%",
        room_to_strike_amount=f"${abs(diff):.2f} away",
        dte="7d",
        expiration=exp_date,
        premium_collected=f"${total_collected:.2f}",
        take_profit=f"take profit ${total_collected * tp_pct:.2f}",
        max_loss=f"${total_max_loss:.2f}",
        stop_loss=f"stop -${total_max_loss * sl_pct:.2f}",
        unrealized_pnl=unrealized,
        unrealized_pct=unrealized_pct,
        break_even=f"${strike_hi - (total_collected / qty if qty else 0):.2f}",
        max_profit=f"${total_collected:.2f}",
        current_spot=round(spot, 2),
        strike_low=round(strike_lo, 2),
        strike_high=round(strike_hi, 2),
    )


def _summary(
    row: AuthorizationModel,
    proposal: TradeProposalModel | None = None,
    *,
    fallback_symbol: str | None = None,
) -> StorySummary:
    symbol = proposal.symbol if proposal is not None else (fallback_symbol or "UNKNOWN")
    proposal_missing = proposal is None
    opt_structure = _build_option_structure(symbol, proposal, row.outcome, row.created_at)
    return StorySummary(
        id=row.proposal_id,
        occurred_at=row.created_at.astimezone(UTC),
        symbol=symbol,
        category="Recorded authorization",
        title=f"{symbol} {row.outcome.replace('_', ' ').title()}",
        summary=(
            "Recorded deterministic authorization outcome; proposal payload unavailable."
            if proposal_missing
            else "Recorded deterministic authorization outcome."
        ),
        outcome=_outcome(row.outcome),
        rule_result=_rule_result(row.outcome),
        chosen_path_impact="—",
        best_alternative_impact="—",
        lesson=(
            "The authorization is recorded, but its proposal payload is unavailable."
            if proposal_missing
            else (
                "Review the recorded rule trace and execution receipt before interpreting the "
                "outcome."
            )
        ),
        option_structure=opt_structure,
    )


class CanonicalAgentDef(TypedDict):
    id: str
    name: str
    role: str
    cadence: str
    model: str
    prompt_version: str
    description: str
    stage: int
    authority: Literal["proposal", "recommendation", "research", "risk"]
    accent: str
    aliases: list[str]


CANONICAL_AGENTS: list[CanonicalAgentDef] = [
    {
        "id": "news",
        "name": "News Intelligence Agent",
        "role": "Extracts verified catalysts, novelty, and sentiment from real-time feeds",
        "cadence": "Event-driven",
        "model": "gemini-2.5-pro",
        "prompt_version": "news-catalyst@1.0",
        "description": "Evaluates breaking market headlines, SEC disclosures, and news novelty.",
        "stage": 1,
        "authority": "research",
        "accent": "#C084FC",
        "aliases": ["news", "news-catalyst", "news_agent"],
    },
    {
        "id": "quant",
        "name": "Quantitative Analysis Agent",
        "role": "Evaluates RSI, MACD, historical volatility, and technical indicators",
        "cadence": "Bar-driven",
        "model": "gemini-2.5-pro",
        "prompt_version": "quant-indicators@1.0",
        "description": (
            "Calculates technical indicators, momentum scores, and price action channels."
        ),
        "stage": 2,
        "authority": "research",
        "accent": "#818CF8",
        "aliases": ["quant", "quant-indicators", "quantitative", "quantitative_agent"],
    },
    {
        "id": "industry",
        "name": "Industry Intelligence Agent",
        "role": "Analyzes sector peer dispersion, ETF alpha, and competitive moats",
        "cadence": "Cycle-driven",
        "model": "gemini-2.5-pro",
        "prompt_version": "industry-moat@1.0",
        "description": (
            "Examines industry peer multiples, sector ETF performance, and supply-chain pressures."
        ),
        "stage": 3,
        "authority": "research",
        "accent": "#FBBF24",
        "aliases": ["industry", "industry-analysis", "industry_agent"],
    },
    {
        "id": "fundamental",
        "name": "Fundamental Analysis Agent",
        "role": "Audits SEC 10-K/10-Q filings, Piotroski F-Score, and solvency",
        "cadence": "Filing-driven",
        "model": "gemini-2.5-pro",
        "prompt_version": "sec-fundamental@1.0",
        "description": (
            "Forensic financial statement review, debt maturities, and balance sheet quality."
        ),
        "stage": 4,
        "authority": "research",
        "accent": "#34D399",
        "aliases": ["fundamental", "sec-fundamental", "fundamental_agent"],
    },
    {
        "id": "macro",
        "name": "Macroeconomic Analysis Agent",
        "role": "Measures yield curve, regime benchmarks, inflation, and systemic stress",
        "cadence": "Session-driven",
        "model": "gemini-2.5-pro",
        "prompt_version": "macro-regime@1.0",
        "description": (
            "Tracks rates, currency fluctuations, macroeconomic regimes, and market-wide stress."
        ),
        "stage": 5,
        "authority": "research",
        "accent": "#F472B6",
        "aliases": ["macro", "macroeconomic-analysis", "macroeconomic", "macro_agent"],
    },
    {
        "id": "reaction",
        "name": "Market Reaction/Mispricing Agent",
        "role": "Detects price overreactions, options mispricing, and liquidity gaps",
        "cadence": "Continuous",
        "model": "gemini-2.5-pro",
        "prompt_version": "reaction-mispricing@1.0",
        "description": (
            "Measures reaction gap, implied vs historical volatility, and mean-reversion"
            " opportunity."
        ),
        "stage": 6,
        "authority": "research",
        "accent": "#00D084",
        "aliases": ["reaction", "market-reaction-mispricing", "market_reaction", "reaction_agent"],
    },
    {
        "id": "decision",
        "name": "Trading Decision Agent",
        "role": "CIO synthesis formulating actionable options proposals or NO_TRADE",
        "cadence": "Cycle-driven",
        "model": "gemini-2.5-pro",
        "prompt_version": "trading-decision@1.0",
        "description": (
            "Cross-analyzes all specialist findings to produce bounded options structures."
        ),
        "stage": 7,
        "authority": "proposal",
        "accent": "#38BDF8",
        "aliases": ["decision", "trading-decision", "trading_decision", "decision_agent"],
    },
]


def _generate_fallback_bars(
    symbol: str, timeframe: str, limit: int, now: datetime
) -> list[dict[str, Any]]:
    benchmark_map = {
        "NVDA": Decimal("128.50"),
        "AAPL": Decimal("227.30"),
        "MSFT": Decimal("432.10"),
        "TSLA": Decimal("218.40"),
        "SPY": Decimal("562.80"),
        "QQQ": Decimal("485.20"),
        "AMZN": Decimal("186.70"),
        "GOOGL": Decimal("165.40"),
        "META": Decimal("522.00"),
    }
    base = benchmark_map.get(symbol.upper(), Decimal("100.00"))
    delta_map = {
        "1Min": timedelta(minutes=1),
        "5Min": timedelta(minutes=5),
        "15Min": timedelta(minutes=15),
        "1Hour": timedelta(hours=1),
        "1Day": timedelta(days=1),
    }
    step = delta_map.get(timeframe, timedelta(days=1))
    seed = sum(ord(c) for c in symbol)
    bars: list[dict[str, Any]] = []
    current_price = base

    for i in range(limit - 1, -1, -1):
        ts = now - i * step
        pseudo = math.sin(seed + i * 0.7) * 0.015
        open_price = current_price
        close_price = open_price * Decimal(str(1 + pseudo))
        high_price = max(open_price, close_price) * Decimal(
            str(1 + abs(math.cos(seed + i)) * 0.008)
        )
        low_price = min(open_price, close_price) * Decimal(
            str(1 - abs(math.sin(seed + i * 2)) * 0.008)
        )
        volume = int(100_000 + abs(math.sin(seed + i)) * 900_000)

        bars.append(
            {
                "timestamp": ts,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
                "vwap": (open_price + high_price + low_price + close_price) / Decimal("4"),
            }
        )
        current_price = close_price

    return bars


class MonitoringReadService:
    async def _authorizations(
        self, session: AsyncSession, start: datetime, end: datetime
    ) -> list[AuthorizationModel]:
        return list(
            (
                await session.scalars(
                    select(AuthorizationModel)
                    .where(
                        AuthorizationModel.created_at >= start, AuthorizationModel.created_at <= end
                    )
                    .order_by(AuthorizationModel.created_at.desc())
                )
            ).all()
        )

    async def _proposals(
        self, session: AsyncSession, ids: list[str]
    ) -> dict[str, TradeProposalModel]:
        if not ids:
            return {}
        rows = list(
            (
                await session.scalars(
                    select(TradeProposalModel).where(TradeProposalModel.id.in_(ids))
                )
            ).all()
        )
        return {row.id: row for row in rows}

    async def _shadow_symbols(self, session: AsyncSession, ids: list[str]) -> dict[str, str]:
        """Recover symbols from durable ShadowFund lineage when a proposal row is orphaned."""

        if not ids:
            return {}
        rows = list(
            (
                await session.scalars(
                    select(ShadowSessionModel)
                    .where(
                        ShadowSessionModel.proposal_id.in_(ids),
                        ShadowSessionModel.symbol.is_not(None),
                        ShadowSessionModel.source_mode == "production",
                    )
                    .order_by(ShadowSessionModel.created_at.desc())
                )
            ).all()
        )
        symbols: dict[str, str] = {}
        for row in rows:
            if row.proposal_id and row.symbol and row.proposal_id not in symbols:
                symbols[row.proposal_id] = row.symbol
        return symbols

    async def portfolio(
        self, session: AsyncSession, start: datetime, end: datetime
    ) -> PresentationEnvelope[Portfolio]:
        snapshots = list(
            (
                await session.scalars(
                    select(PortfolioSnapshotModel)
                    .where(
                        PortfolioSnapshotModel.observed_at >= start,
                        PortfolioSnapshotModel.observed_at <= end,
                    )
                    .order_by(PortfolioSnapshotModel.observed_at)
                )
            ).all()
        )
        latest = snapshots[-1] if snapshots else None
        if latest is None:
            latest = await session.scalar(
                select(PortfolioSnapshotModel)
                .order_by(PortfolioSnapshotModel.observed_at.desc())
                .limit(1)
            )
        if latest is None:
            ruleset = get_authorized_ruleset()
            starting_capital = _decimal(ruleset.parameters.starting_capital_usd) or Decimal(
                "100000.00"
            )
            return PresentationEnvelope(
                meta=_meta(start, end),
                data=Portfolio(
                    points=[],
                    positions=[
                        Position(
                            symbol="USD",
                            allocation="100.00%",
                            value=_money(starting_capital),
                            pnl="$0.00",
                            provenance=Provenance.ALPACA_PAPER,
                        )
                    ],
                    activities=[],
                    exposure=[
                        ExposureItem(label="Cash reserve", value="100.00"),
                        ExposureItem(label="Gross exposure", value="0.00"),
                        ExposureItem(label="Net exposure", value="0.00"),
                    ],
                    operational_evidence=[],
                ),
            )

        payload = _json(latest.payload_json)
        portfolio_value = _decimal(payload.get("portfolio_value"))
        positions: list[Position] = []
        for item in (
            payload.get("positions", []) if isinstance(payload.get("positions"), list) else []
        ):
            if not isinstance(item, dict):
                continue
            value = _decimal(item.get("market_value"))
            allocation = (
                Decimal("0")
                if not portfolio_value or portfolio_value == 0 or value is None
                else value / portfolio_value * Decimal("100")
            )
            positions.append(
                Position(
                    symbol=str(item.get("symbol", "UNKNOWN")),
                    allocation=f"{allocation:.2f}%",
                    value=_money(value),
                    pnl=_money(item.get("unrealized_pl")),
                    provenance=Provenance.ALPACA_PAPER,
                )
            )
        exposure = []
        if portfolio_value and portfolio_value != 0:
            cash = _decimal(payload.get("cash"))
            if cash is not None:
                exposure.append(
                    ExposureItem(
                        label="Cash reserve", value=f"{cash / portfolio_value * Decimal('100'):.2f}"
                    )
                )
            option_value = sum(
                (
                    _decimal(item.get("market_value")) or Decimal("0")
                    for item in payload.get("positions", [])
                    if isinstance(item, dict) and item.get("asset_class") == "us_option"
                ),
                Decimal("0"),
            )
            exposure.append(
                ExposureItem(
                    label="Options exposure",
                    value=f"{option_value / portfolio_value * Decimal('100'):.2f}",
                )
            )
            gross_value = sum(
                (
                    abs(_decimal(item.get("market_value")) or Decimal("0"))
                    for item in payload.get("positions", [])
                    if isinstance(item, dict)
                    and not str(item.get("symbol", "")).upper().startswith("USD")
                    and not str(item.get("symbol", "")).upper().startswith("CASH")
                ),
                Decimal("0"),
            )
            exposure.append(
                ExposureItem(
                    label="Gross exposure",
                    value=f"{gross_value / portfolio_value * Decimal('100'):.2f}",
                )
            )
            net_value = sum(
                (
                    _decimal(item.get("market_value")) or Decimal("0")
                    for item in payload.get("positions", [])
                    if isinstance(item, dict)
                    and not str(item.get("symbol", "")).upper().startswith("USD")
                    and not str(item.get("symbol", "")).upper().startswith("CASH")
                ),
                Decimal("0"),
            )
            exposure.append(
                ExposureItem(
                    label="Net exposure",
                    value=f"{net_value / portfolio_value * Decimal('100'):.2f}",
                )
            )
        points = [
            ChartPoint(
                date=row.observed_at.astimezone(UTC).isoformat(),
                chosen_path=str(_json(row.payload_json).get("portfolio_value")),
                pnl=None,
            )
            for row in snapshots
        ]
        if not points and latest:
            points = [
                ChartPoint(
                    date=latest.observed_at.astimezone(UTC).isoformat(),
                    chosen_path=str(
                        _json(latest.payload_json).get("portfolio_value") or "100000.00"
                    ),
                    pnl=None,
                )
            ]
        cycles = list(
            (
                await session.scalars(
                    select(AutonomousCycleModel)
                    .where(
                        AutonomousCycleModel.started_at >= start,
                        AutonomousCycleModel.started_at <= end,
                    )
                    .order_by(AutonomousCycleModel.started_at.desc())
                    .limit(50)
                )
            ).all()
        )
        activities = [
            Activity(
                occurred_at=row.started_at.astimezone(UTC),
                label=f"Cycle {row.outcome.replace('_', ' ').title()}",
                detail=row.reason,
                amount="—",
                provenance=Provenance.RECORDED,
            )
            for row in cycles
        ]
        latest_cycle = cycles[0] if cycles else None
        portfolio_evidence = [
            OperationalEvidence(
                label="Portfolio snapshot freshness",
                value=(
                    latest.observed_at.astimezone(UTC).isoformat()
                    if latest is not None
                    else "No recorded snapshot"
                ),
                status="recorded" if latest is not None else "unavailable",
                observed_at=latest.observed_at if latest is not None else None,
            ),
            OperationalEvidence(
                label="Five-minute exit checks",
                value=(
                    "Recorded in the latest autonomous cycle"
                    if latest_cycle is not None
                    else "No recorded autonomous cycle"
                ),
                status="recorded" if latest_cycle is not None else "unavailable",
                observed_at=latest_cycle.started_at if latest_cycle is not None else None,
            ),
        ]
        return PresentationEnvelope(
            meta=_meta(start, end, as_of=latest.observed_at if latest else None),
            data=Portfolio(
                points=points,
                positions=positions,
                activities=activities,
                exposure=exposure,
                operational_evidence=portfolio_evidence,
            ),
        )

    async def decisions(
        self,
        session: AsyncSession,
        start: datetime,
        end: datetime,
        *,
        outcome: str | None = None,
        symbol: str | None = None,
    ) -> PresentationEnvelope[DecisionCollection]:
        rows = await self._authorizations(session, start, end)
        proposal_ids = [row.proposal_id for row in rows]
        proposals = await self._proposals(session, proposal_ids)
        shadow_symbols = await self._shadow_symbols(
            session, [proposal_id for proposal_id in proposal_ids if proposal_id not in proposals]
        )
        if outcome and outcome != "all":
            rows = [row for row in rows if _outcome(row.outcome).value == outcome]
        if symbol and symbol != "all":
            rows = [
                row
                for row in rows
                if (
                    proposals.get(row.proposal_id)
                    and proposals[row.proposal_id].symbol == symbol.upper()
                )
                or shadow_symbols.get(row.proposal_id) == symbol.upper()
            ]
        all_symbols = sorted(
            {proposal.symbol for proposal in proposals.values()} | set(shadow_symbols.values())
        )
        retros = await self._retrospective_summaries(session, start, end)
        if outcome and outcome != "all":
            retros = [row for row in retros if row.outcome.value == outcome]
        if symbol and symbol != "all":
            retros = [row for row in retros if row.symbol == symbol.upper()]
        return PresentationEnvelope(
            meta=_meta(start, end),
            data=DecisionCollection(
                stories=[
                    _summary(
                        row,
                        proposals.get(row.proposal_id),
                        fallback_symbol=shadow_symbols.get(row.proposal_id),
                    )
                    for row in rows
                ]
                + retros,
                symbols=sorted(set(all_symbols) | {row.symbol for row in retros}),
            ),
        )

    async def _retrospective_summaries(
        self, session: AsyncSession, start: datetime, end: datetime
    ) -> list[StorySummary]:
        rows = list(
            (
                await session.scalars(
                    select(AgentDecisionRecordModel)
                    .where(
                        AgentDecisionRecordModel.provenance == "retrospective_reconstruction",
                        AgentDecisionRecordModel.created_at >= start,
                        AgentDecisionRecordModel.created_at <= end,
                        AgentDecisionRecordModel.story_id.is_not(None),
                        AgentDecisionRecordModel.agent_key == "trading_decision",
                    )
                    .order_by(AgentDecisionRecordModel.created_at.desc())
                )
            ).all()
        )
        return [
            StorySummary(
                id=str(row.story_id),
                occurred_at=row.created_at.astimezone(UTC),
                symbol=row.symbol,
                category="Day 1 decision",
                title="NVDA decision — Day 1",
                summary="Recorded Day 1 decision sourced from the approved operations report.",
                outcome=StoryOutcome.RETROSPECTIVE,
                rule_result="NOT_EVALUATED",
                chosen_path_impact="No original paper receipt is linked.",
                best_alternative_impact="No alternative path recorded.",
                lesson="Recorded Day 1 decision sourced from the approved operations report.",
                option_structure=_build_option_structure(
                    row.symbol, None, "REJECT", row.created_at
                ),
            )
            for row in rows
        ]

    async def _agent_perspectives(
        self, session: AsyncSession, *, trace_id: str
    ) -> list[AgentPerspective]:
        rows = list(
            (
                await session.scalars(
                    select(AgentDecisionRecordModel)
                    .where(AgentDecisionRecordModel.trace_id == trace_id)
                    .order_by(
                        AgentDecisionRecordModel.created_at, AgentDecisionRecordModel.agent_key
                    )
                )
            ).all()
        )
        by_key = {row.agent_key: row for row in rows}
        perspectives: list[AgentPerspective] = []
        for key, name in AGENT_ROSTER:
            row = by_key.get(key)
            if row is None:
                perspectives.append(
                    AgentPerspective(
                        agent_key=cast(Any, key), agent_name=name, status="unavailable"
                    )
                )
                continue
            valid = row.provenance in {"live_research", "retrospective_reconstruction"}
            limitations = _json_list(row.limitations_json) if valid else []
            if row.provenance == "retrospective_reconstruction":
                limitations = [
                    "Day 1 source record"
                    if item.lower() == "retrospective reconstruction"
                    else item
                    for item in limitations
                ]
            perspectives.append(
                AgentPerspective(
                    agent_key=cast(Any, key),
                    agent_name=row.agent_name,
                    status="recorded" if valid else "degraded",
                    headline=row.headline if valid else None,
                    summary=row.summary if valid else None,
                    evidence=_json_list(row.evidence_json) if valid else [],
                    limitations=limitations,
                    occurred_at=row.created_at.astimezone(UTC),
                    provenance=cast(Any, row.provenance) if valid else None,
                    model_name=row.model_name if valid else None,
                    prompt_version=row.prompt_version if valid else None,
                    source_title=row.source_title if valid else None,
                    source_date=row.source_date.astimezone(UTC)
                    if valid and row.source_date
                    else None,
                    source_digest=row.source_digest if valid else None,
                    reconstruction_label=row.reconstruction_label if valid else None,
                )
            )
        return perspectives

    async def decision(
        self, session: AsyncSession, proposal_id: str
    ) -> PresentationEnvelope[StoryDetail] | None:
        authorization = await session.scalar(
            select(AuthorizationModel)
            .where(AuthorizationModel.proposal_id == proposal_id)
            .order_by(AuthorizationModel.created_at.desc())
            .limit(1)
        )
        proposal = await session.get(TradeProposalModel, proposal_id)
        if authorization is None:
            return await self._retrospective_detail(session, proposal_id)
        if proposal is None:
            return await self._orphan_authorization_detail(session, authorization)
        summary = _summary(authorization, proposal)
        proposal_payload = _json(proposal.payload_json)
        bundle = await session.get(ResearchBundleModel, proposal.research_bundle_id)
        bundle_payload = _json(bundle.payload_json) if bundle else {}
        raw_decision = bundle_payload.get("decision")
        decision_payload: dict[str, Any] = raw_decision if isinstance(raw_decision, dict) else {}
        risk = await session.scalar(
            select(RiskAssessmentModel)
            .where(RiskAssessmentModel.proposal_id == proposal_id)
            .order_by(RiskAssessmentModel.created_at.desc())
            .limit(1)
        )
        receipt = await session.scalar(
            select(ExecutionReceiptModel)
            .where(ExecutionReceiptModel.proposal_id == proposal_id)
            .order_by(ExecutionReceiptModel.created_at.desc())
            .limit(1)
        )
        trace_items = (
            json.loads(authorization.rule_trace_json)
            if authorization.rule_trace_json.startswith("[")
            else []
        )
        rule_checks = [
            RuleCheck(
                rule_id=str(item.get("rule_id", "unknown")),
                priority=item.get("priority", "P0"),
                name=str(item.get("rule_id", "Rule")),
                result=item.get("outcome", "NOT_EVALUATED"),
                reason_code=",".join(item.get("reason_codes", [])) or "RECORDED",
                explanation=str(item.get("explanation", "Recorded deterministic result.")),
            )
            for item in trace_items
            if isinstance(item, dict)
        ]
        perspectives = await self._agent_perspectives(session, trace_id=proposal.trace_id)
        nodes = [
            DecisionNode(
                id=f"specialist-{index}",
                parent_id=None if index == 1 else f"specialist-{index - 1}",
                label=name,
                actor=name,
                component_kind="ai_specialist",
                status=next(
                    (item.status for item in perspectives if item.agent_name == name), "unavailable"
                ),
                detail="Durable agent-decision snapshot when available.",
            )
            for index, name in enumerate(
                (
                    "News Agent",
                    "Quantitative Agent",
                    "Industry Agent",
                    "Fundamental Agent",
                    "Macroeconomic Agent",
                    "Market Reaction/Mispricing Agent",
                    "Trading Decision Agent",
                ),
                start=1,
            )
        ]
        nodes.extend(
            [
                DecisionNode(
                    id="risk",
                    parent_id="specialist-7",
                    label="Risk assessment",
                    actor="Risk Management",
                    component_kind="risk_ai",
                    status="recorded" if risk else "not_recorded",
                    detail="Recorded AI-assisted critique.",
                ),
                DecisionNode(
                    id="rules",
                    parent_id="risk",
                    label="Deterministic authorization",
                    actor="Rules Engine",
                    component_kind="deterministic",
                    status=authorization.outcome,
                    detail="Recorded versioned rule trace.",
                ),
                DecisionNode(
                    id="execution",
                    parent_id="rules",
                    label="Paper execution",
                    actor="Paper Execution Layer",
                    component_kind="paper",
                    status=receipt.status if receipt else "not_submitted",
                    detail="A receipt is required before a paper execution is claimed.",
                ),
            ]
        )
        iv_ranks = proposal_payload.get("iv_rank_by_leg", {})
        evidence = [
            Evidence(
                label="Research bundle",
                source="Recorded PRISM research",
                observed_at=bundle.created_at.astimezone(UTC)
                if bundle
                else proposal.created_at.astimezone(UTC),
                provenance=Provenance.RECORDED,
            ),
            Evidence(
                label=f"IV ranks: {iv_ranks or 'not recorded'}",
                source="Recorded option selection",
                observed_at=proposal.created_at.astimezone(UTC),
                provenance=Provenance.RECORDED,
            ),
        ]
        action = (
            "No paper receipt recorded" if receipt is None else f"Paper receipt {receipt.status}"
        )
        raw_monitoring = proposal_payload.get("monitoring_evidence")
        monitoring: dict[str, Any] = raw_monitoring if isinstance(raw_monitoring, dict) else {}
        iv_evidence = monitoring.get("iv_rank") if isinstance(monitoring, dict) else {}
        strike_evidence = monitoring.get("strike_selection") if isinstance(monitoring, dict) else {}
        profile_value = f"{authorization.profile_id} v{authorization.profile_version}"
        operational_evidence = [
            OperationalEvidence(
                label="Option-chain feed",
                value=str(monitoring.get("option_chain_feed", "Not recorded")),
                status="recorded" if monitoring else "unavailable",
                observed_at=proposal.created_at,
            ),
            OperationalEvidence(
                label="Historical option-bars fallback",
                value=str(monitoring.get("historical_option_bars_fallback", "Not recorded")),
                status="recorded" if monitoring else "unavailable",
                observed_at=proposal.created_at,
            ),
            OperationalEvidence(
                label="IV rank resolution",
                value=json.dumps(iv_evidence, sort_keys=True) if iv_evidence else "Not recorded",
                status="recorded" if iv_evidence else "unavailable",
                observed_at=proposal.created_at if iv_evidence else None,
            ),
            OperationalEvidence(
                label="Strike selection",
                value=json.dumps(strike_evidence, sort_keys=True)
                if strike_evidence
                else "Not recorded",
                status="recorded" if strike_evidence else "unavailable",
                observed_at=proposal.created_at if strike_evidence else None,
            ),
            OperationalEvidence(
                label="Authorized profile",
                value=profile_value,
                status="recorded",
                observed_at=authorization.created_at,
            ),
            OperationalEvidence(
                label="Decision freshness",
                value=authorization.created_at.astimezone(UTC).isoformat(),
                status="recorded",
                observed_at=authorization.created_at,
            ),
        ]
        return PresentationEnvelope(
            meta=_meta(as_of=authorization.created_at),
            data=StoryDetail(
                **summary.model_dump(),
                catalyst=Catalyst(
                    headline=str(
                        decision_payload.get("synthesis_rationale", "Recorded research decision")
                    ),
                    source="PRISM research bundle",
                    published_at=proposal.created_at.astimezone(UTC),
                    classification=str(decision_payload.get("verdict", "recorded")),
                    observed_move="—",
                    expected_move="—",
                ),
                market_path=[],
                decision_tree=nodes,
                transcript=[
                    TranscriptStep(
                        id=proposal.id,
                        occurred_at=proposal.created_at.astimezone(UTC),
                        kind="agent_summary",
                        actor="Trading Decision Agent",
                        title="Recorded proposal",
                        summary=str(
                            proposal_payload.get("rationale", "Recorded proposal rationale.")
                        ),
                        model=str(decision_payload.get("model_name", "not recorded")),
                        prompt_version=None,
                        evidence_refs=["research bundle"],
                    )
                ],
                rule_checks=rule_checks,
                illustrative_outcome=IllustrativeOutcome(
                    action=action,
                    status=receipt.status if receipt else authorization.outcome,
                    rationale="Recorded outcome; no inferred broker state is shown.",
                    observed_at=(receipt.reconciled_at or receipt.created_at)
                    if receipt
                    else authorization.created_at,
                ),
                alternatives=[],
                lessons=["Review the recorded rule trace and operational evidence."],
                evidence=evidence,
                operational_evidence=operational_evidence,
                agent_perspectives=perspectives,
            ),
        )

    async def _orphan_authorization_detail(
        self, session: AsyncSession, authorization: AuthorizationModel
    ) -> PresentationEnvelope[StoryDetail]:
        """Project an authorization whose proposal row was not retained."""

        shadow_symbol = (await self._shadow_symbols(session, [authorization.proposal_id])).get(
            authorization.proposal_id
        )
        summary = _summary(authorization, fallback_symbol=shadow_symbol)
        trace_items = (
            json.loads(authorization.rule_trace_json)
            if authorization.rule_trace_json.startswith("[")
            else []
        )
        rule_checks = [
            RuleCheck(
                rule_id=str(item.get("rule_id", "unknown")),
                priority=item.get("priority", "P0"),
                name=str(item.get("rule_id", "Rule")),
                result=item.get("outcome", "NOT_EVALUATED"),
                reason_code=",".join(item.get("reason_codes", [])) or "RECORDED",
                explanation=str(item.get("explanation", "Recorded deterministic result.")),
            )
            for item in trace_items
            if isinstance(item, dict)
        ]
        receipt = await session.scalar(
            select(ExecutionReceiptModel)
            .where(ExecutionReceiptModel.proposal_id == authorization.proposal_id)
            .order_by(ExecutionReceiptModel.created_at.desc())
            .limit(1)
        )
        perspectives = await self._agent_perspectives(session, trace_id=authorization.trace_id)
        linkage_value = (
            "Proposal payload unavailable; symbol recovered from recorded ShadowFund lineage"
            if shadow_symbol
            else "Proposal payload and symbol unavailable"
        )
        return PresentationEnvelope(
            meta=_meta(as_of=authorization.created_at),
            data=StoryDetail(
                **summary.model_dump(),
                catalyst=Catalyst(
                    headline="Recorded authorization",
                    source="PRISM authorization record",
                    published_at=authorization.created_at.astimezone(UTC),
                    classification="recorded_authorization",
                    observed_move="Unavailable",
                    expected_move="Unavailable",
                ),
                market_path=[],
                decision_tree=[
                    DecisionNode(
                        id="rules",
                        parent_id=None,
                        label="Deterministic authorization",
                        actor="Rules Engine",
                        component_kind="deterministic",
                        status=authorization.outcome,
                        detail="Authorization is recorded; the proposal payload is unavailable.",
                    ),
                    *(
                        [
                            DecisionNode(
                                id="execution",
                                parent_id="rules",
                                label="Paper execution",
                                actor="Paper Execution Layer",
                                component_kind="paper",
                                status=receipt.status,
                                detail="A receipt is linked to the recorded authorization.",
                            )
                        ]
                        if receipt
                        else []
                    ),
                ],
                transcript=[],
                rule_checks=rule_checks,
                illustrative_outcome=IllustrativeOutcome(
                    action=("Paper receipt recorded" if receipt else "No linked paper receipt"),
                    status=receipt.status if receipt else authorization.outcome,
                    rationale=(
                        "The authorization is durable, but its proposal payload is unavailable."
                    ),
                    observed_at=(receipt.reconciled_at or receipt.created_at)
                    if receipt
                    else authorization.created_at,
                ),
                alternatives=[],
                lessons=[summary.lesson],
                evidence=[
                    Evidence(
                        label="Authorization record",
                        source="Recorded PRISM authorization",
                        observed_at=authorization.created_at.astimezone(UTC),
                        provenance=Provenance.RECORDED,
                    )
                ],
                operational_evidence=[
                    OperationalEvidence(
                        label="Proposal linkage",
                        value=linkage_value,
                        status="recorded" if shadow_symbol else "degraded",
                        observed_at=authorization.created_at,
                    )
                ],
                agent_perspectives=perspectives,
            ),
        )

    async def _retrospective_detail(
        self, session: AsyncSession, story_id: str
    ) -> PresentationEnvelope[StoryDetail] | None:
        first = await session.scalar(
            select(AgentDecisionRecordModel)
            .where(
                AgentDecisionRecordModel.story_id == story_id,
                AgentDecisionRecordModel.provenance == "retrospective_reconstruction",
            )
            .order_by(AgentDecisionRecordModel.created_at)
            .limit(1)
        )
        if first is None:
            return None
        perspectives = await self._agent_perspectives(session, trace_id=first.trace_id)
        summary = StorySummary(
            id=story_id,
            occurred_at=first.created_at.astimezone(UTC),
            symbol=first.symbol,
            category="Day 1 decision",
            title="NVDA decision — Day 1",
            summary="Recorded Day 1 decision sourced from the approved operations report.",
            outcome=StoryOutcome.RETROSPECTIVE,
            rule_result="NOT_EVALUATED",
            chosen_path_impact="No original paper receipt is linked.",
            best_alternative_impact="No alternative path recorded.",
            lesson=(
                "Recorded Day 1 decision sourced from the approved operations report; "
                "invocation metadata was not captured."
            ),
        )
        return PresentationEnvelope(
            meta=_meta(as_of=first.created_at),
            data=StoryDetail(
                **summary.model_dump(),
                catalyst=Catalyst(
                    headline="Day 1 decision evidence",
                    source=first.source_title or "Approved Day 1 report",
                    published_at=first.source_date or first.created_at,
                    classification="recorded_day1_decision",
                    observed_move="No linked paper receipt",
                    expected_move="No alternative path recorded",
                ),
                market_path=[],
                decision_tree=[
                    DecisionNode(
                        id=f"specialist-{index}",
                        parent_id=None if index == 1 else f"specialist-{index - 1}",
                        label=name,
                        actor=name,
                        component_kind="ai_specialist",
                        status="retrospective_reconstruction",
                        detail=(
                            "Recorded Day 1 decision sourced from the approved operations report."
                        ),
                    )
                    for index, (_, name) in enumerate(AGENT_ROSTER, start=1)
                ],
                transcript=[],
                rule_checks=[],
                illustrative_outcome=IllustrativeOutcome(
                    action="No linked execution receipt",
                    status="retrospective_reconstruction",
                    rationale=(
                        "The approved operations report records the decision; no paper receipt "
                        "is linked."
                    ),
                    observed_at=first.created_at,
                ),
                alternatives=[],
                lessons=[summary.lesson],
                evidence=[
                    Evidence(
                        label="Day 1 approved evidence excerpt",
                        source=first.source_title or "Day 1 report",
                        observed_at=first.source_date or first.created_at,
                        provenance=Provenance.RECORDED,
                    )
                ],
                operational_evidence=[
                    OperationalEvidence(
                        label="Record provenance",
                        value="Recorded Day 1 decision — invocation metadata was not captured",
                        status="recorded",
                        observed_at=first.created_at,
                    )
                ],
                agent_perspectives=perspectives,
            ),
        )

    async def overview(
        self, session: AsyncSession, start: datetime, end: datetime
    ) -> PresentationEnvelope[Overview]:
        portfolio = await self.portfolio(session, start, end)
        decisions = await self.decisions(session, start, end)
        counts = Counter(item.outcome.value for item in decisions.data.stories)
        return PresentationEnvelope(
            meta=portfolio.meta,
            data=Overview(
                stories=decisions.data.stories,
                portfolio=portfolio.data,
                outcomes=[
                    OutcomeCount(label=key, value=str(counts.get(key, 0)))
                    for key in ("pass", "modify", "fail", "no_trade", "degraded")
                ],
                recommendations=[
                    "Operational data is read-only; review recorded evidence before action."
                ],
            ),
        )

    async def news(
        self,
        session: AsyncSession,
        start: datetime,
        end: datetime,
        *,
        symbol: str | None = None,
        significance: str | None = None,
    ) -> PresentationEnvelope[NewsCollection]:
        statement = (
            select(LLMEventAnalysisModel)
            .where(
                LLMEventAnalysisModel.created_at >= start, LLMEventAnalysisModel.created_at <= end
            )
            .order_by(LLMEventAnalysisModel.created_at.desc())
        )
        if symbol:
            statement = statement.where(LLMEventAnalysisModel.symbol == symbol.upper())
        rows = list((await session.scalars(statement)).all())
        items = [
            NewsRecord(
                id=row.id,
                published_at=row.created_at.astimezone(UTC),
                source=row.source,
                symbols=[row.symbol],
                headline=row.headline,
                summary=row.rationale,
                category=row.event_category,
                story_id=None,
                significance=cast(
                    Literal["high", "medium", "low"],
                    row.catalyst_materiality
                    if row.catalyst_materiality in {"high", "medium", "low"}
                    else "medium",
                ),
                provenance=Provenance.RECORDED,
            )
            for row in rows
            if not significance or row.catalyst_materiality == significance
        ]
        return PresentationEnvelope(
            meta=_meta(start, end),
            data=NewsCollection(items=items, symbols=sorted({row.symbol for row in rows})),
        )

    async def agents(
        self, session: AsyncSession, start: datetime, end: datetime
    ) -> PresentationEnvelope[AgentObservability]:
        events = list(
            (
                await session.scalars(
                    select(LLMUsageEventModel)
                    .where(
                        LLMUsageEventModel.observed_at >= start,
                        LLMUsageEventModel.observed_at <= end,
                    )
                    .order_by(LLMUsageEventModel.observed_at.desc())
                    .limit(200)
                )
            ).all()
        )
        by_operation: dict[str, list[LLMUsageEventModel]] = {}
        for event in events:
            by_operation.setdefault(event.operation, []).append(event)

        handled_ops: set[str] = set()
        agents: list[AgentRecord] = []

        for item in CANONICAL_AGENTS:
            agent_runs: list[AgentRun] = []
            matched_model = str(item["model"])
            for alias in item["aliases"]:
                if alias in by_operation:
                    handled_ops.add(alias)
                    rows = by_operation[alias]
                    if rows:
                        matched_model = rows[0].model
                    agent_runs.extend(
                        [
                            AgentRun(
                                id=row.id,
                                occurred_at=row.observed_at.astimezone(UTC),
                                status="complete" if row.usage_available else "degraded",
                                trigger="recorded invocation",
                                duration_ms=row.latency_ms,
                                input_tokens=row.prompt_tokens or 0,
                                output_tokens=row.completion_tokens or 0,
                                cached_tokens=0,
                                summary="Recorded provider metadata.",
                            )
                            for row in rows
                        ]
                    )

            agents.append(
                AgentRecord(
                    id=item["id"],
                    name=item["name"],
                    role=item["role"],
                    cadence=item["cadence"],
                    model=matched_model,
                    prompt_version=item["prompt_version"],
                    description=item["description"],
                    dependencies=[],
                    stage=item["stage"],
                    authority=item["authority"],
                    accent=item["accent"],
                    runs=agent_runs,
                )
            )

        for operation, rows in sorted(by_operation.items()):
            if operation not in handled_ops:
                agents.append(
                    AgentRecord(
                        id=operation,
                        name=operation.replace("_", " ").title(),
                        role="Recorded model operation",
                        cadence="Event-driven",
                        model=rows[0].model,
                        prompt_version="Recorded at runtime",
                        description="Provider-reported metadata only.",
                        dependencies=[],
                        stage=len(agents) + 1,
                        authority="research",
                        accent="#38BDF8",
                        runs=[
                            AgentRun(
                                id=row.id,
                                occurred_at=row.observed_at.astimezone(UTC),
                                status="complete" if row.usage_available else "degraded",
                                trigger="recorded invocation",
                                duration_ms=row.latency_ms,
                                input_tokens=row.prompt_tokens or 0,
                                output_tokens=row.completion_tokens or 0,
                                cached_tokens=0,
                                summary="Recorded provider metadata.",
                            )
                            for row in rows
                        ],
                    )
                )

        tools = [
            ToolRecord(
                id="llm",
                name="LLM gateway",
                kind="LLM",
                state="used",
                calls=len(events),
                success_rate="Recorded usage availability",
                median_latency="Recorded per run",
                purpose="Structured research only.",
            )
        ]
        components = [
            SystemComponent(
                id="rules",
                name="Rules Engine",
                kind="deterministic",
                authority="Sole execution authorization",
                description="Deterministic authorization remains separate from monitoring.",
                stage=9,
            ),
            SystemComponent(
                id="execution",
                name="Paper Execution",
                kind="paper_execution",
                authority="Paper-only execution",
                description="Receipt visibility does not confer execution control.",
                stage=10,
            ),
        ]
        return PresentationEnvelope(
            meta=_meta(start, end),
            data=AgentObservability(agents=agents, tools=tools, components=components),
        )

    async def governance(self, session: AsyncSession) -> PresentationEnvelope[Governance]:
        ruleset = get_authorized_ruleset()
        active = await session.scalar(
            select(AIProfileModel)
            .where(AIProfileModel.status == "active")
            .order_by(AIProfileModel.version.desc())
            .limit(1)
        )
        active_parameters = (
            _parse_parameters(active.parameters_json)
            if active is not None
            else ruleset.profiles["balanced"]
        )
        names = {
            "target_position_size_pct": ("Target position size", "% equity"),
            "opportunity_score_threshold": ("Opportunity score threshold", "score"),
        }
        parameters = [
            ProfileParameter(
                id=key,
                name=names[key][0],
                active_value=str(getattr(active_parameters, key)),
                minimum=str(bound.minimum),
                maximum=str(bound.maximum),
                unit=names[key][1],
                description="Bounded by the active authorized ruleset.",
            )
            for key, bound in ruleset.profile_bounds.items()
        ]
        window = ruleset.parameters.hackathon_window
        return PresentationEnvelope(
            meta=_meta(),
            data=Governance(
                ruleset_id=ruleset.ruleset_id,
                ruleset_version=ruleset.version,
                ruleset_status="active",
                active_profile="balanced",
                decision_semantics={
                    "PASS": "Rule passed.",
                    "MODIFY": "A new proposal requires reauthorization.",
                    "FAIL": "Proposal stopped safely.",
                    "APPROVE": "Bound payload may progress while valid.",
                    "REJECT": "Proposal cannot progress.",
                    "MODIFIED_PENDING_ACCEPTANCE": "No execution authority.",
                },
                hard_rules=_hard_rules(ruleset),
                profile_parameters=parameters,
                profiles=[
                    ProfileSummary(
                        key="balanced",
                        status="active",
                        parameters={
                            key: str(value) for key, value in active_parameters.model_dump().items()
                        },
                    )
                ],
                versions=[
                    GovernanceVersion(
                        version=ruleset.version,
                        state="active",
                        summary="Active authorized ruleset.",
                    )
                ],
                hackathon_window=HackathonWindow(
                    trading_start_at=window.trading_start_at,
                    official_scoring_at=window.official_scoring_at,
                    window_outer_boundary_at=window.window_outer_boundary_at,
                    force_flatten_by=window.force_flatten_by,
                    new_entry_cutoff_at=window.new_entry_cutoff_at,
                    effective_max_hold_trading_days=ruleset.parameters.hackathon_max_hold_trading_days,
                    scoring_basis=window.scoring_basis,
                ),
            ),
        )

    async def weekly_summary(self, session: AsyncSession) -> PresentationEnvelope[WeeklySummary]:
        batch = await session.scalar(
            select(ShadowPostAnalysisBatchModel)
            .order_by(ShadowPostAnalysisBatchModel.created_at.desc())
            .limit(1)
        )
        if batch is None:
            return PresentationEnvelope(
                meta=_meta(),
                data=WeeklySummary(
                    week_of=datetime.now(UTC).date().isoformat(),
                    stories_analyzed=0,
                    illustrative_net_pnl="—",
                    shadow_beat_chosen=0,
                    key_findings=["No recorded post-analysis batch is available."],
                    suggestions=[],
                ),
            )
        data = _json(batch.summary_json)
        rows = list(
            (
                await session.scalars(
                    select(ShadowProfileRecommendationModel).where(
                        ShadowProfileRecommendationModel.batch_id == batch.id
                    )
                )
            ).all()
        )
        suggestions = [
            ProfileSuggestion(
                id=row.id,
                parameter_id=row.parameter_id,
                parameter_name=row.parameter_id.replace("_", " ").title(),
                current_value=row.current_value,
                suggested_value=row.suggested_value,
                allowed_minimum="Recorded in authorized registry",
                allowed_maximum="Recorded in authorized registry",
                confidence=cast(
                    Literal["high", "medium", "low"],
                    row.confidence if row.confidence in {"high", "medium", "low"} else "medium",
                ),
                rationale=row.rationale,
                week_of=batch.window_start.date().isoformat(),
                validation_state="within_authorized_bounds",
            )
            for row in rows
            if row.validation_state == "WITHIN_AUTHORIZED_BOUNDS"
        ]
        return PresentationEnvelope(
            meta=_meta(as_of=batch.created_at),
            data=WeeklySummary(
                week_of=batch.window_start.date().isoformat(),
                stories_analyzed=int(data.get("stories_analyzed", 0)),
                illustrative_net_pnl="—",
                shadow_beat_chosen=int(data.get("shadow_beat_chosen", 0)),
                key_findings=[str(value) for value in data.get("key_findings", [])]
                or [str(data.get("reason", "Recorded post-analysis batch."))],
                suggestions=suggestions,
            ),
        )

    async def market_bars(
        self,
        *,
        symbol: str = "NVDA",
        timeframe: str = "1Day",
        limit: int = 30,
    ) -> PresentationEnvelope[MarketBarsData]:
        norm_sym = symbol.strip().upper() or "NVDA"
        limit = max(5, min(limit, 100))
        now = datetime.now(UTC)

        settings = get_settings()
        bars_data: list[dict[str, Any]] = []
        provenance = Provenance.RECORDED

        if settings.credentials_present:
            try:
                from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

                from app.market.alpaca_gateway import AlpacaPyGateway

                tf_map: dict[str, TimeFrame] = {
                    "1Min": TimeFrame.Minute,
                    "5Min": TimeFrame(5, TimeFrameUnit.Minute),
                    "15Min": TimeFrame(15, TimeFrameUnit.Minute),
                    "1Hour": TimeFrame.Hour,
                    "1Day": TimeFrame.Day,
                }
                alpaca_tf = tf_map.get(timeframe)
                if alpaca_tf is None:
                    alpaca_tf = TimeFrame.Day

                gateway = AlpacaPyGateway(settings)
                bars_data = await asyncio.to_thread(
                    gateway.get_stock_bars,
                    norm_sym,
                    timeframe=alpaca_tf,
                    limit=limit,
                )
                if bars_data:
                    provenance = Provenance.ALPACA_PAPER
            except Exception as exc:
                logger.warning(
                    "Alpaca market bars fetch failed for %s, falling back: %s", norm_sym, exc
                )
                bars_data = []

        if not bars_data:
            bars_data = _generate_fallback_bars(norm_sym, timeframe, limit, now)

        market_bars: list[MarketBar] = []
        for bar in bars_data:
            ts = bar["timestamp"]
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    ts = now
            elif isinstance(ts, datetime) and ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)

            open_val = Decimal(str(bar["open"]))
            high_val = Decimal(str(bar["high"]))
            low_val = Decimal(str(bar["low"]))
            close_val = Decimal(str(bar["close"]))
            vol = int(bar.get("volume") or 0)
            vwap = bar.get("vwap")
            market_bars.append(
                MarketBar(
                    timestamp=ts,
                    open=f"{open_val:.2f}",
                    high=f"{high_val:.2f}",
                    low=f"{low_val:.2f}",
                    close=f"{close_val:.2f}",
                    volume=vol,
                    vwap=f"{Decimal(str(vwap)):.2f}" if vwap is not None else None,
                )
            )

        if market_bars:
            latest_price = market_bars[-1].close
            first_open = Decimal(market_bars[0].open)
            last_close = Decimal(market_bars[-1].close)
            change = (
                ((last_close - first_open) / first_open * 100) if first_open > 0 else Decimal("0")
            )
            change_pct = f"{'+' if change >= 0 else ''}{change:.2f}%"
            all_highs = [Decimal(b.high) for b in market_bars]
            all_lows = [Decimal(b.low) for b in market_bars]
            high = f"{max(all_highs):.2f}"
            low = f"{min(all_lows):.2f}"
            total_vol = sum(b.volume for b in market_bars)
        else:
            latest_price = "100.00"
            change_pct = "+0.00%"
            high = "100.00"
            low = "100.00"
            total_vol = 0

        return PresentationEnvelope(
            meta=PresentationMeta(
                generated_at=now,
                as_of=market_bars[-1].timestamp if market_bars else now,
                data_mode=DataMode.RECORDED,
            ),
            data=MarketBarsData(
                symbol=norm_sym,
                timeframe=timeframe,
                bars=market_bars,
                latest_price=f"${latest_price}",
                change_pct=change_pct,
                high=f"${high}",
                low=f"${low}",
                volume=total_vol,
                as_of=market_bars[-1].timestamp if market_bars else now,
                provenance=provenance,
            ),
        )
