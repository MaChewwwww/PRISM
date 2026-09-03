from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import re
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.autonomous.audit import build_evaluation_root
from app.autonomous.control import get_or_create_control
from app.autonomous.models import (
    AuthorizationModel,
    AutonomousAuditEventModel,
    AutonomousCycleModel,
    OptionIvObservationModel,
    PortfolioSnapshotModel,
    ReconciliationEventModel,
    ResearchBundleModel,
    RiskAssessmentModel,
    StrategyLifecycleEventModel,
    StrategyPositionModel,
    TradeProposalModel,
)
from app.autonomous.strategy_lifecycle import (
    StrategyMarkUnavailable,
    evaluate_adaptive_exit,
    executable_liquidation_value,
    regular_session_minutes_elapsed,
    strategy_return_pct,
)
from app.contracts.models import (
    AuthorizationOutcome,
    ExecutionStatus,
    ExitPolicy,
    ExitReason,
    MarketRegime,
    OptionPayoffEconomics,
    OptionStrategy,
    PortfolioRiskState,
    ShadowCandidate,
    StrategyKind,
    TradeProposal,
    TradeVerdict,
)
from app.core.config import Settings
from app.core.database import get_db_session
from app.core.llm_gateway import LLMGateway
from app.execution.cli_gateway import (
    AlpacaCliExecutionGateway,
    SqlAlchemyReceiptRepository,
    SubprocessRunner,
)
from app.execution.models import ExecutionReceiptModel
from app.market.alpaca_gateway import AlpacaPyGateway
from app.market.option_selection import (
    OptionSelectionError,
    select_candidate_option_strategies,
    select_option_strategy,
)
from app.portfolio.metadata import metadata_complete, parse_instrument
from app.profiles.service import ActiveProfile, ProfileGovernanceService
from app.research.decision_agent import TradingDecisionAgent
from app.research.historical_analogs import (
    HistoricalAnalogSummary,
    HistoricalAnalogUnavailable,
    compute_historical_analogs,
    compute_option_payoff_ev,
)
from app.research.iv_rank import (
    IvObservation,
    IvRankUnavailable,
    compute_iv_rank,
    infer_iv_observations,
)
from app.research.models import TradeDecisionModel
from app.research.post_analysis import (
    POST_ANALYSIS_AGENT_VERSION,
    PostAnalysisAgent,
    get_trading_week_bounds,
    is_friday_post_close,
)
from app.research.risk_agent import RiskManagementAgent
from app.research.sec_fundamentals import SecFundamentalsUnavailable, fetch_sec_company_financials
from app.rules.evaluator import _json_value, authorize_proposal, input_digest
from app.rules.registry import get_authorized_ruleset
from app.shadowfund.models import ShadowPostAnalysisBatchModel, ShadowSessionModel
from app.shadowfund.service import ShadowFundService

logger = logging.getLogger(__name__)

AUTONOMOUS_SYMBOLS = ("NVDA", "TSLA", "AAPL", "MSFT", "AMD", "GOOGL", "AMZN")
WORKER_VERSION = "performance-calibration-v4"


@dataclass(frozen=True)
class CandidateResearchOutcome:
    candidate: tuple[TradeProposal, HistoricalAnalogSummary, dict[str, Any]] | None = None
    rejection_code: str | None = None
    rejection_reason: str | None = None


def _field(value: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(value, dict) and name in value:
            return value[name]
        if hasattr(value, name):
            return getattr(value, name)
    return default


def _decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _finite_decimal(value: Any) -> Decimal | None:
    """Parse a provider value without turning a missing field into a zero."""

    if value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _string_or_none(value: Any) -> str | None:
    return None if value is None else str(value)


def _option_level(value: Any) -> int | None:
    try:
        text = str(value)
        digits = "".join(character for character in text if character.isdigit())
        return int(digits) if digits else None
    except (TypeError, ValueError):
        return None


def _timestamp_iso(value: Any) -> str | None:
    if not isinstance(value, datetime) or value.tzinfo is None:
        return None
    return value.astimezone(UTC).isoformat()


class AutonomousWorker:
    """Production-only autonomous paper-trading worker.

    Staging is reserved for historical backtest simulation and is prohibited
    from instantiating this order-capable worker. Any unavailable dependency
    produces a durable ``NO_TRADE`` cycle and never reaches the CLI.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._last_option_bars_fallback: str = "not_attempted"
        self._last_iv_rank_resolution: dict[str, Any] = {}
        self._last_iv_rank_evidence: dict[str, Any] = {}

    @staticmethod
    def _advance_cycle_due(
        next_cycle_due: float | None,
        completed_at: float,
        interval_seconds: int,
    ) -> float:
        """Advance a fixed-rate schedule without creating a catch-up burst.

        The worker must not overlap autonomous cycles. If one cycle runs past
        one or more scheduled ticks, the missed ticks are skipped and the next
        due time remains on the original cadence grid.
        """

        if next_cycle_due is None:
            return completed_at + interval_seconds
        next_due = next_cycle_due + interval_seconds
        while next_due <= completed_at:
            next_due += interval_seconds
        return next_due

    async def run_forever(self, stop_event: asyncio.Event) -> None:
        flatten_attempted = False
        next_cycle_due: float | None = None
        loop = asyncio.get_running_loop()
        interval_seconds = self.settings.autonomous_scan_interval_seconds
        while not stop_event.is_set():
            now = datetime.now(UTC)
            in_window = self.settings.autonomous_trading_window_active(now)
            # The configured environment window is a hard boundary for new
            # work. We still run one final cycle at its end so paper positions
            # cannot remain after the authorized production window.
            environment_end = self.settings.autonomous_trading_end_at
            flatten_due = (
                now >= get_authorized_ruleset().parameters.hackathon_window.force_flatten_by
                or (environment_end is not None and now >= environment_end)
            )
            if in_window or (flatten_due and not flatten_attempted):
                # The configured autonomous interval spans the hackathon, not
                # each regular trading session. Do not create a durable cycle,
                # portfolio snapshot, or ShadowFund no-trade session until the
                # broker confirms that the regular market is open. Force-flatten
                # remains independent of this probe at the authorized boundary.
                if not flatten_due and not await asyncio.to_thread(
                    self._market_is_open, AlpacaPyGateway(self.settings)
                ):
                    next_cycle_due = None
                    await self._wait(stop_event, min(interval_seconds, 60))
                    continue
                cycle_started = loop.time()
                if next_cycle_due is None:
                    next_cycle_due = cycle_started
                try:
                    outcome = await self.run_cycle(now=now)
                except Exception:
                    logger.exception("Autonomous cycle failed closed")
                    outcome = "FAILED"
                cycle_completed = loop.time()
                cycle_duration = cycle_completed - cycle_started
                if cycle_duration >= interval_seconds:
                    logger.warning(
                        "Autonomous cycle exceeded configured interval: "
                        "duration=%.3fs interval=%ss outcome=%s",
                        cycle_duration,
                        interval_seconds,
                        outcome,
                    )
                if flatten_due and outcome == "FLATTENED":
                    flatten_attempted = True
                next_cycle_due = self._advance_cycle_due(
                    next_cycle_due,
                    cycle_completed,
                    interval_seconds,
                )
                wait_seconds = max(0, math.ceil(next_cycle_due - cycle_completed))
                await self._wait(stop_event, wait_seconds)
            else:
                next_cycle_due = None
                try:
                    async for session in get_db_session():
                        if await self._acquire_cycle_lock(session):
                            await self._run_weekly_post_analysis_if_due(session, now)
                            await session.commit()
                except Exception:
                    logger.exception("Weekly post-analysis check failed closed")
                await self._wait(stop_event, min(interval_seconds, 60))

    async def _wait(self, stop_event: asyncio.Event, seconds: int) -> None:
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=seconds)
        except TimeoutError:
            return

    async def run_cycle(self, *, now: datetime | None = None) -> str:
        now = (now or datetime.now(UTC)).astimezone(UTC)
        symbols = tuple(self.settings.autonomous_symbol_allowlist)
        if symbols != AUTONOMOUS_SYMBOLS:
            return "NO_TRADE"
        window = get_authorized_ruleset().parameters.hackathon_window
        in_window = self.settings.autonomous_trading_window_active(now)
        environment_end = self.settings.autonomous_trading_end_at
        flatten_due = now >= window.force_flatten_by or (
            environment_end is not None and now >= environment_end
        )
        if not in_window and not flatten_due:
            return "NO_TRADE"

        async for session in get_db_session():
            if not await self._acquire_cycle_lock(session):
                return "NO_TRADE"
            control = await get_or_create_control(session, self.settings)
            kill_switch_active = self.settings.execution_kill_switch or control.kill_switch_active
            # Reconciliation is always attempted before the static/durable
            # kill switch short-circuits new submissions.  A restart must not
            # strand an ambiguous paper order merely because execution was
            # disabled for the current cycle.
            try:
                await self._reconcile_unfinished(session)
            except Exception:
                await session.rollback()
                logger.exception("Autonomous reconciliation failed closed")
                await self._record(
                    session, now, "FAILED", "Unfinished submission reconciliation failed"
                )
                await session.commit()
                return "FAILED"
            try:
                gateway = AlpacaPyGateway(self.settings)
                if self.settings.shadowfund_enabled:
                    await self._mark_open_shadow_sessions(session, gateway, now)
                if not flatten_due and not await asyncio.to_thread(self._market_is_open, gateway):
                    await self._record(session, now, "NO_TRADE", "Broker market is closed")
                    await self._run_weekly_post_analysis_if_due(session, now)
                    await session.commit()
                    return "NO_TRADE"
                account, positions = await asyncio.gather(
                    asyncio.to_thread(gateway.get_account),
                    asyncio.to_thread(gateway.get_positions),
                )
                portfolio = self._portfolio_snapshot(account, positions, now)
                portfolio = await self._refresh_position_metadata(gateway, portfolio, now)
                await self._persist_portfolio_snapshot(session, portfolio)
                if flatten_due:
                    if not await self._force_flatten(session, portfolio["positions"], now):
                        await self._record(session, now, "FAILED", "Force-flatten command failed")
                        await session.commit()
                        return "FAILED"
                    await self._record(session, now, "NO_TRADE", "Hackathon force-flatten executed")
                    await session.commit()
                    return "FLATTENED"
                await self._reconcile_exit_receipts(session, positions, now)
                exits_ok, exited_symbols, exit_checks = await self._manage_exits(
                    session, portfolio["positions"], now, include_score_evidence=False
                )
                if not exits_ok:
                    await self._record(
                        session,
                        now,
                        "FAILED",
                        "Mandatory position exit failed",
                        evidence={"position_exit_checks": exit_checks},
                    )
                    await session.commit()
                    return "FAILED"
                if any(check["result"] == "exit_pending" for check in exit_checks):
                    await self._record(
                        session,
                        now,
                        "NO_TRADE",
                        "Mandatory position exit pending reconciliation",
                        evidence={"position_exit_checks": exit_checks},
                    )
                    await session.commit()
                    return "NO_TRADE"
                if exited_symbols:
                    positions = [
                        position
                        for position in positions
                        if str(_field(position, "symbol", default="")) not in exited_symbols
                    ]
                    portfolio = self._portfolio_snapshot(account, positions, now)
                    portfolio = await self._refresh_position_metadata(gateway, portfolio, now)
                    await self._persist_portfolio_snapshot(session, portfolio)

                # The kill switch gates new risk only. Reconciliation,
                # mandatory exits, and force-flatten above remain active.
                if kill_switch_active:
                    await self._record(
                        session,
                        now,
                        "NO_TRADE",
                        "Kill switch active for new entries",
                        evidence={"position_exit_checks": exit_checks},
                    )
                    await session.commit()
                    return "NO_TRADE"

                # Profile resolution is database-backed and fails closed with the
                # cycle if its bounded, auditable state cannot be proven.
                active_profile = await ProfileGovernanceService().get_active(session)
                candidates: list[tuple[TradeProposal, HistoricalAnalogSummary, dict[str, Any]]] = []
                rejections: dict[str, dict[str, str]] = {}
                for symbol in symbols:
                    candidate_outcome = await self._research_candidate(
                        session, gateway, symbol, portfolio, now, active_profile
                    )
                    if candidate_outcome.candidate is not None:
                        candidates.append(candidate_outcome.candidate)
                    else:
                        code = candidate_outcome.rejection_code or "REJECTED"
                        reason_msg = (
                            candidate_outcome.rejection_reason
                            or "Candidate rejected during research"
                        )
                        rejections[symbol] = {
                            "code": code,
                            "reason": reason_msg,
                        }
                        logger.info(
                            "Autonomous candidate rejected for %s: %s (%s)",
                            symbol,
                            code,
                            reason_msg,
                        )
                # A completed research pass can advance deterministic thesis
                # invalidation exactly once per newly persisted score record.
                thesis_ok, thesis_exited, thesis_checks = await self._manage_exits(
                    session, portfolio["positions"], now, include_score_evidence=True
                )
                exit_checks = thesis_checks
                if not thesis_ok:
                    await self._record(
                        session,
                        now,
                        "FAILED",
                        "Thesis-driven position exit failed",
                        evidence={"position_exit_checks": thesis_checks},
                    )
                    await session.commit()
                    return "FAILED"
                if thesis_exited or any(
                    check["result"] in {"exit", "exit_pending"} for check in thesis_checks
                ):
                    await self._record(
                        session,
                        now,
                        "NO_TRADE",
                        "Strategy exit took priority over new entries",
                        evidence={"position_exit_checks": thesis_checks},
                    )
                    await session.commit()
                    return "NO_TRADE"

                candidates.sort(
                    key=lambda item: (
                        _decimal(item[2].get("net_ev_r")),
                        _decimal(item[2].get("reward_risk_ratio")),
                        -_decimal(
                            item[0].option_economics.premium_per_contract
                            if item[0].option_economics is not None
                            else "999999"
                        ),
                    ),
                    reverse=True,
                )

                if not candidates:
                    if rejections:
                        summary_parts = [
                            f"{sym}: {info['code']} ({info['reason']})"
                            for sym, info in rejections.items()
                        ]
                        reason_text = (
                            f"No eligible deterministic proposal - {'; '.join(summary_parts)}"
                        )
                    else:
                        reason_text = "No eligible deterministic proposal"
                    await self._record(
                        session,
                        now,
                        "NO_TRADE",
                        reason_text,
                        evidence={
                            "candidate_rejections": rejections,
                            "position_exit_checks": exit_checks,
                        },
                    )
                    await session.commit()
                    return "NO_TRADE"

                open_positions = await self._strategy_position_count(session, positions)
                if open_positions >= self.settings.autonomous_max_open_positions:
                    await self._record(
                        session,
                        now,
                        "NO_TRADE",
                        "Six-position cap reached",
                        evidence={"position_exit_checks": exit_checks},
                    )
                    await session.commit()
                    return "NO_TRADE"

                executor = AlpacaCliExecutionGateway(self.settings, SubprocessRunner(), None)  # type: ignore[arg-type]
                submitted = False
                for proposal, analog, context in candidates:
                    if open_positions >= self.settings.autonomous_max_open_positions:
                        break
                    try:
                        risk = await RiskManagementAgent(LLMGateway(self.settings)).assess(
                            proposal, context=context
                        )
                    except Exception as exc:
                        await self._persist_no_trade(
                            session, proposal, f"Risk assessment unavailable: {type(exc).__name__}"
                        )
                        continue
                    session.add(
                        RiskAssessmentModel(
                            id=str(risk.id),
                            trace_id=str(risk.trace_id),
                            created_at=risk.created_at,
                            proposal_id=str(risk.proposal_id),
                            verdict=risk.verdict.value,
                            payload_json=risk.model_dump_json(),
                        )
                    )
                    auth_now = datetime.now(UTC)
                    decision = authorize_proposal(
                        proposal,
                        risk,
                        self.settings,
                        inputs={
                            **context,
                            "analog_count": analog.count,
                            "account_observed_at": auth_now,
                        },
                        now=auth_now,
                        profile_key=active_profile.profile_key,
                        profile_parameters=active_profile.parameters,
                        profile_id=active_profile.id,
                        profile_version=active_profile.version,
                        kill_switch_active=kill_switch_active,
                    )
                    await self._persist_authorization(session, decision)
                    root = build_evaluation_root(
                        trace_id=proposal.trace_id,
                        outcome=decision.outcome.value,
                        evidence=context,
                        proposal_digest=proposal.proposal_digest,
                        market_snapshot=context.get("market_snapshot", "unavailable"),
                        portfolio_snapshot=portfolio,
                    )
                    await self._persist_root(session, proposal.id, root)
                    shadow_session_id: str | None = None
                    if self.settings.shadowfund_enabled:
                        try:
                            async with session.begin_nested():
                                shadow_session = await ShadowFundService().create_terminal_session(
                                    session,
                                    root=root,
                                    terminal_outcome=decision.outcome.value,
                                    proposal=proposal,
                                    authorization=decision,
                                    source_mode="production",
                                    source_feed="configured",
                                    candidate_strategies={
                                        candidate.label: candidate.strategy
                                        for candidate in proposal.shadow_candidates
                                        if candidate.strategy is not None
                                    },
                                    horizon_at=get_authorized_ruleset().parameters.hackathon_window.official_scoring_at,
                                )
                                shadow_session_id = shadow_session.id
                                raw_quotes = context.get("shadow_quotes", {})
                                if raw_quotes:
                                    await ShadowFundService().mark_session_from_quotes(
                                        session,
                                        shadow_session_id=shadow_session.id,
                                        observed_at=now,
                                        quotes=raw_quotes,
                                        source="alpaca_option_chain",
                                        feed="configured",
                                        max_quote_age_seconds=get_authorized_ruleset().parameters.data_freshness_seconds,
                                    )
                        except Exception:
                            logger.exception(
                                "ShadowFund session failed without affecting execution"
                            )
                    if decision.outcome is not AuthorizationOutcome.APPROVE:
                        continue
                    receipt = await executor.submit_async(
                        proposal,
                        decision,
                        SqlAlchemyReceiptRepository(session),
                        kill_switch_active=kill_switch_active,
                    )
                    await self._persist_strategy_position(session, proposal, receipt, now)
                    if (
                        shadow_session_id is not None
                        and receipt.status.value == "filled"
                        and receipt.filled_average_price is not None
                    ):
                        try:
                            async with session.begin_nested():
                                await ShadowFundService().attach_confirmed_paper_fill(
                                    session,
                                    shadow_session_id=shadow_session_id,
                                    strategy=proposal.strategy,
                                    filled_average_price=receipt.filled_average_price,
                                    filled_at=receipt.reconciled_at or receipt.submitted_at or now,
                                )
                        except Exception:
                            logger.exception(
                                "ShadowFund paper-fill attachment failed without "
                                "affecting execution"
                            )
                    submitted = receipt.status.value in {"submitted", "filled"}
                    if submitted:
                        open_positions += 1
                outcome = "SUBMITTED" if submitted else "NO_TRADE"
                await self._record(
                    session,
                    now,
                    outcome,
                    "Production-parity cycle completed",
                    evidence={"position_exit_checks": exit_checks},
                )
                await session.commit()
                return outcome
            except (
                SecFundamentalsUnavailable,
                HistoricalAnalogUnavailable,
                OptionSelectionError,
            ) as exc:
                await session.rollback()
                await self._record(session, now, "NO_TRADE", type(exc).__name__)
                await session.commit()
                return "NO_TRADE"
            except Exception as exc:
                await session.rollback()
                logger.exception("Autonomous cycle failed closed: %s", type(exc).__name__)
                await self._record(session, now, "FAILED", "Autonomous dependency failure")
                await session.commit()
                return "FAILED"
        return "NO_TRADE"

    async def _research_candidate(
        self,
        session: AsyncSession,
        gateway: AlpacaPyGateway,
        symbol: str,
        portfolio: dict[str, Any],
        now: datetime,
        active_profile: ActiveProfile,
    ) -> CandidateResearchOutcome:
        trace_id = uuid4()
        try:
            bars = await asyncio.to_thread(
                gateway.get_stock_bars,
                symbol,
                start=now - timedelta(days=365 * 5 + 30),
                end=now,
                limit=2000,
            )
            if len(bars) < 40:
                raise HistoricalAnalogUnavailable("Five-year bars are unavailable (< 40 bars)")
            financials = await asyncio.to_thread(
                fetch_sec_company_financials,
                symbol,
                user_agent=self.settings.sec_user_agent,
            )
            report = await TradingDecisionAgent(
                LLMGateway(self.settings), gateway
            ).synthesize_decision(
                symbol,
                trace_id,
                db_session=session,
                allow_illustrative=False,
                financials=financials,
            )
            if report.verdict not in {
                TradeVerdict.PROCEED_TO_OPTIONS_PROPOSAL,
                TradeVerdict.PROPOSE_TRADE,
            }:
                return CandidateResearchOutcome(
                    rejection_code="NO_TRADE_DECISION",
                    rejection_reason=f"Agent verdict is {report.verdict.value}",
                )
            if report.direction.value not in {"bullish", "bearish"}:
                return CandidateResearchOutcome(
                    rejection_code="NO_TRADE_DECISION",
                    rejection_reason=(
                        f"Actionable direction required; received {report.direction.value}"
                    ),
                )
            # Exit policy v2 is ruleset-owned; profiles cannot tune it.
            rules = get_authorized_ruleset().parameters
            exit_policy = ExitPolicy(
                profit_arm_pct=rules.profit_arm_pct,
                profit_trailing_giveback_points=rules.profit_trailing_giveback_points,
                hard_take_profit_pct=rules.hard_take_profit_pct,
                hard_stop_loss_pct=rules.hard_stop_loss_pct,
                thesis_failure_cycles=rules.thesis_failure_cycles,
                time_stop_trading_minutes=rules.time_stop_trading_minutes,
                minimum_mfe_pct=rules.minimum_mfe_pct,
                dte_threshold=report.exit_policy.dte_threshold,
                max_hold_days=report.exit_policy.max_hold_days,
            )
            direction: Literal["bullish", "bearish"] = (
                "bullish" if report.direction.value == "bullish" else "bearish"
            )
            horizon_bars = self._remaining_holding_sessions(now, exit_policy)
            analog = compute_historical_analogs(
                bars,
                direction=direction,
                now=now,
                horizon_bars=horizon_bars,
                event_category="recorded_catalyst",
            )
            min_expiry = now.date() + timedelta(days=exit_policy.dte_threshold)
            contracts = await asyncio.to_thread(
                gateway.get_option_contracts,
                symbol,
                expiration_date_gte=min_expiry,
                expiration_date_lte=window_date(now),
            )
            quotes = await asyncio.to_thread(
                gateway.get_option_chain,
                symbol,
                expiration_date_gte=min_expiry,
                expiration_date_lte=window_date(now),
            )
            # The contracts endpoint is authoritative for the valid price
            # increment; carry it into the quote records before midpoint
            # rounding and option-payoff economics are calculated.
            for contract in contracts:
                contract_symbol = str(contract.get("symbol", ""))
                quote = quotes.get(contract_symbol)
                if quote is not None and "price_increment" not in quote:
                    quote["price_increment"] = contract.get("price_increment", "0.01")

            # Persist fresh IV observations present in the option chain quotes
            # so history is accumulated even if this specific candidate is rejected later.
            valid_ivs = []
            for contract_sym, quote_data in quotes.items():
                if isinstance(quote_data, dict):
                    raw_iv = _decimal(quote_data.get("iv"), Decimal("NaN"))
                    if raw_iv.is_finite() and Decimal("0") < raw_iv < Decimal("10"):
                        valid_ivs.append(raw_iv)
                        quote_ts = quote_data.get("quote_timestamp")
                        obs_ts = quote_ts if isinstance(quote_ts, datetime) else now
                        await self._persist_iv_observation(
                            session,
                            symbol,
                            IvObservation(
                                observed_at=obs_ts,
                                implied_volatility=raw_iv,
                                source="alpaca_option_chain",
                                option_symbol=contract_sym,
                            ),
                        )
            if valid_ivs:
                median_iv = sorted(valid_ivs)[len(valid_ivs) // 2]
                await self._persist_iv_observation(
                    session,
                    symbol,
                    IvObservation(
                        observed_at=now,
                        implied_volatility=median_iv,
                        source="alpaca_option_chain_median",
                        option_symbol=symbol,
                    ),
                )

            regime = self._market_regime(report)
            requested_structures: tuple[Literal["long", "debit_spread"], ...] = (
                ("debit_spread",) if regime is MarketRegime.VOLATILE else ("long", "debit_spread")
            )
            candidate_strategies = []
            for requested_structure in requested_structures:
                try:
                    candidate_strategies.extend(
                        select_candidate_option_strategies(
                            contracts,
                            quotes,
                            underlying_price=report.current_price,
                            direction=direction,
                            structure=requested_structure,
                            now=now,
                            exit_dte_threshold=exit_policy.dte_threshold,
                            force_flatten_at=rules.hackathon_window.force_flatten_by,
                            pricing="entry_touch",
                            max_candidates=None,
                        )
                    )
                except OptionSelectionError:
                    continue
            if not candidate_strategies:
                raise OptionSelectionError("No supported option structures are executable")
            evaluated: list[tuple[Any, HistoricalAnalogSummary]] = []
            candidate_evidence: list[dict[str, Any]] = []
            for candidate_strat in candidate_strategies:
                try:
                    candidate_econ = compute_option_payoff_ev(
                        analog,
                        candidate_strat,
                        underlying_price=report.current_price,
                        quotes=quotes,
                        max_spread_pct=get_authorized_ruleset().parameters.max_bid_ask_spread_pct,
                    )
                    evaluated.append((candidate_strat, candidate_econ))
                    candidate_evidence.append(
                        {
                            "strategy": candidate_strat.model_dump(mode="json"),
                            "net_ev_r": str(candidate_econ.net_ev_r),
                            "reward_risk_ratio": str(candidate_econ.reward_risk_ratio),
                            "status": "evaluated",
                            "rejection_reason": None,
                        }
                    )
                except Exception as exc:
                    candidate_evidence.append(
                        {
                            "strategy": candidate_strat.model_dump(mode="json"),
                            "status": "rejected",
                            "rejection_reason": type(exc).__name__,
                        }
                    )
                    continue

            if not evaluated:
                raise OptionSelectionError(
                    "No candidate option strategy could produce valid payoff economics"
                )

            # Deterministic cross-structure ranking: edge, reward/risk, fill
            # probability, then lower premium as the capital-efficiency tie-break.
            evaluated.sort(
                key=lambda item: (
                    item[1].net_ev_r >= rules.minimum_net_ev_r,
                    item[1].net_ev_r,
                    item[1].reward_risk_ratio or Decimal("0"),
                    item[1].fill_probability or Decimal("0"),
                    -(item[1].premium_per_contract or Decimal("0")),
                ),
                reverse=True,
            )
            strategy, option_economics = evaluated[0]
            catalyst_digest = (
                report.catalyst_digest
                or hashlib.sha256(f"{symbol}:unsourced-catalyst".encode()).hexdigest()
            )
            thesis_key = hashlib.sha256(
                json.dumps(
                    {
                        "underlying": symbol,
                        "direction": direction,
                        "catalyst_digest": catalyst_digest,
                        "expiration": strategy.legs[0].expiration,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            prior_thesis = await session.scalar(
                select(StrategyPositionModel.id)
                .where(StrategyPositionModel.thesis_key == thesis_key)
                .limit(1)
            )
            if prior_thesis is not None:
                return CandidateResearchOutcome(
                    rejection_code="DUPLICATE_THESIS",
                    rejection_reason="This catalyst thesis has already been traded",
                )
            quantity = self._proposal_quantity(
                option_economics,
                portfolio,
                active_profile,
                market_regime=regime,
                underlying=symbol,
            )
            if quantity < 1:
                return CandidateResearchOutcome(
                    rejection_code="POSITION_SIZE_UNAVAILABLE",
                    rejection_reason="Governed risk budget cannot support one contract",
                )
            iv_rank_by_leg, _iv_observations = await self._resolve_iv_rank(
                session, gateway, symbol, strategy, quotes, bars, now
            )
            selected_strategy = strategy.model_dump(mode="json")
            for candidate in candidate_evidence:
                if candidate.get("strategy") == selected_strategy:
                    candidate["selected"] = True
                    break
            # The option-payoff model is the only EV that reaches the
            # authorization context.  The underlying-return fields remain a
            # descriptive audit of the analog sample.
            analog = option_economics
            proposal_economics = OptionPayoffEconomics(
                method=analog.ev_method,
                expected_profit_per_contract=analog.expected_profit_per_contract or Decimal("0"),
                expected_loss_per_contract=analog.expected_loss_per_contract or Decimal("0"),
                max_loss_per_contract=analog.max_loss_per_contract or Decimal("0"),
                premium_per_contract=analog.premium_per_contract or Decimal("0"),
                slippage_per_contract=analog.slippage_per_contract or Decimal("0"),
                fill_probability=analog.fill_probability or Decimal("0"),
                net_ev_r=analog.net_ev_r,
                reward_risk_ratio=analog.reward_risk_ratio or Decimal("0"),
            )
            shadow_candidates = self._shadow_candidates(
                report=report,
                primary_strategy=strategy,
                contracts=contracts,
                quotes=quotes,
                now=now,
            )
            payload = {
                "trace_id": str(trace_id),
                "research_report_id": str(report.id),
                "symbol": symbol,
                "strategy": strategy.model_dump(mode="json"),
                "quantity": quantity,
                "rationale": report.synthesis_rationale,
                "exit_policy": exit_policy.model_dump(mode="json"),
                "shadow_candidates": [
                    candidate.model_dump(mode="json") for candidate in shadow_candidates
                ],
                "option_economics": proposal_economics.model_dump(mode="json"),
                "iv_rank_by_leg": {key: str(value) for key, value in iv_rank_by_leg.items()},
                "monitoring_evidence": {
                    "option_chain_feed": "indicative",
                    "historical_option_bars_fallback": getattr(
                        self, "_last_option_bars_fallback", "not_attempted"
                    ),
                    "iv_rank": getattr(self, "_last_iv_rank_evidence", {}),
                    "strike_selection": {
                        "candidates": candidate_evidence,
                        "selected_strategy": selected_strategy,
                        "selected_net_ev_r": str(option_economics.net_ev_r),
                        "selected_reward_risk_ratio": str(option_economics.reward_risk_ratio),
                    },
                },
            }
            bundle_payload = {
                "decision": report.model_dump(mode="json"),
                "analog": analog.__dict__,
                "market": {
                    "symbol": symbol,
                    "underlying_price": str(report.current_price),
                    "strategy": strategy.model_dump(mode="json"),
                },
            }
            bundle_digest = input_digest(bundle_payload)
            payload["research_bundle_digest"] = bundle_digest
            payload["catalyst_digest"] = catalyst_digest
            payload["thesis_key"] = thesis_key
            proposal_digest = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            proposal = TradeProposal(
                trace_id=trace_id,
                research_report_id=report.id,
                symbol=symbol,
                strategy=strategy,
                quantity=quantity,
                rationale=report.synthesis_rationale,
                exit_policy=exit_policy,
                shadow_candidates=shadow_candidates,
                option_economics=proposal_economics,
                research_bundle_digest=bundle_digest,
                catalyst_digest=catalyst_digest,
                thesis_key=thesis_key,
                proposal_digest=proposal_digest,
            )
            context = self._authorization_inputs(
                report,
                analog,
                strategy,
                portfolio,
                now,
                quotes,
                financials,
                quantity=quantity,
                iv_rank_by_leg=iv_rank_by_leg,
                profile=active_profile,
            )
            shadow_symbols = {
                leg.symbol
                for candidate in shadow_candidates
                if candidate.strategy is not None
                for leg in candidate.strategy.legs
            } | {leg.symbol for leg in strategy.legs}
            context["shadow_quotes"] = {
                symbol: quotes[symbol] for symbol in shadow_symbols if symbol in quotes
            }
            bundle_id = str(uuid4())
            session.add(
                ResearchBundleModel(
                    id=bundle_id,
                    trace_id=str(trace_id),
                    created_at=now,
                    symbol=symbol,
                    bundle_digest=bundle_digest,
                    payload_json=json.dumps(bundle_payload, default=str, sort_keys=True),
                    is_immutable=True,
                )
            )
            session.add(
                TradeProposalModel(
                    id=str(proposal.id),
                    trace_id=str(proposal.trace_id),
                    created_at=proposal.created_at,
                    proposal_version=proposal.proposal_version,
                    research_bundle_id=bundle_id,
                    symbol=proposal.symbol,
                    proposal_digest=proposal.proposal_digest,
                    payload_json=proposal.model_dump_json(),
                )
            )
            await session.flush()
            context["research_bundle_digest"] = bundle_digest
            return CandidateResearchOutcome(candidate=(proposal, analog, context))
        except SecFundamentalsUnavailable as exc:
            return CandidateResearchOutcome(
                rejection_code="SEC_FUNDAMENTALS_UNAVAILABLE",
                rejection_reason=str(exc) or "SEC company financials unavailable",
            )
        except HistoricalAnalogUnavailable as exc:
            return CandidateResearchOutcome(
                rejection_code="HISTORICAL_ANALOG_UNAVAILABLE",
                rejection_reason=str(exc) or "Historical analog bars unavailable",
            )
        except OptionSelectionError as exc:
            return CandidateResearchOutcome(
                rejection_code="OPTION_SELECTION_REJECTED",
                rejection_reason=str(exc) or "Option selection criteria not satisfied",
            )
        except IvRankUnavailable as exc:
            return CandidateResearchOutcome(
                rejection_code="IV_RANK_UNAVAILABLE",
                rejection_reason=str(exc) or "Implied volatility rank unavailable",
            )
        except Exception as exc:
            logger.warning("Research candidate rejected for %s: %s", symbol, type(exc).__name__)
            return CandidateResearchOutcome(
                rejection_code="RESEARCH_ERROR",
                rejection_reason=f"{type(exc).__name__}: {exc!s}",
            )

    async def _mark_open_shadow_sessions(
        self, session: AsyncSession, gateway: AlpacaPyGateway, now: datetime
    ) -> None:
        """Refresh virtual-only branches without reading account or execution state."""

        open_sessions = list(
            (
                await session.scalars(
                    select(ShadowSessionModel).where(
                        ShadowSessionModel.state == "open",
                        ShadowSessionModel.source_mode == "production",
                    )
                )
            ).all()
        )
        chains: dict[str, dict[str, dict[str, Any]]] = {}
        for shadow_session in open_sessions:
            if not shadow_session.symbol:
                continue
            if shadow_session.proposal_id:
                receipt = await session.scalar(
                    select(ExecutionReceiptModel)
                    .where(
                        ExecutionReceiptModel.proposal_id == shadow_session.proposal_id,
                        ExecutionReceiptModel.status == "filled",
                    )
                    .order_by(ExecutionReceiptModel.reconciled_at.desc())
                )
                proposal_row = await session.get(TradeProposalModel, shadow_session.proposal_id)
                if (
                    receipt is not None
                    and receipt.filled_average_price is not None
                    and proposal_row is not None
                ):
                    try:
                        async with session.begin_nested():
                            await ShadowFundService().attach_confirmed_paper_fill(
                                session,
                                shadow_session_id=shadow_session.id,
                                strategy=TradeProposal.model_validate_json(
                                    proposal_row.payload_json
                                ).strategy,
                                filled_average_price=receipt.filled_average_price,
                                filled_at=receipt.reconciled_at or receipt.submitted_at or now,
                            )
                    except Exception:
                        logger.exception(
                            "ShadowFund reconciliation failed without affecting autonomous cycle"
                        )
            if shadow_session.symbol not in chains:
                try:
                    chains[shadow_session.symbol] = await asyncio.to_thread(
                        gateway.get_option_chain, shadow_session.symbol
                    )
                except Exception:
                    logger.warning(
                        "ShadowFund valuation data unavailable for %s", shadow_session.symbol
                    )
                    continue
            try:
                async with session.begin_nested():
                    await ShadowFundService().mark_session_from_quotes(
                        session,
                        shadow_session_id=shadow_session.id,
                        observed_at=now,
                        quotes=chains[shadow_session.symbol],
                        source="alpaca_option_chain",
                        feed="configured",
                        max_quote_age_seconds=get_authorized_ruleset().parameters.data_freshness_seconds,
                    )
            except Exception:
                logger.exception("ShadowFund valuation failed without affecting autonomous cycle")

    @staticmethod
    def _shadow_candidates(
        *,
        report: Any,
        primary_strategy: Any,
        contracts: list[dict[str, Any]],
        quotes: dict[str, dict[str, Any]],
        now: datetime,
    ) -> list[ShadowCandidate]:
        """Select virtual alternatives with the same deterministic eligibility gate."""

        candidates: list[ShadowCandidate] = []
        primary_direction = str(report.direction.value)
        opposite: Literal["bullish", "bearish"] = (
            "bearish" if primary_direction == "bullish" else "bullish"
        )
        primary_shape: Literal["long", "debit_spread"] = (
            "debit_spread" if len(primary_strategy.legs) == 2 else "long"
        )

        def select(
            direction: Literal["bullish", "bearish"],
            shape: Literal["long", "debit_spread"],
        ) -> Any:
            return select_option_strategy(
                contracts,
                quotes,
                underlying_price=report.current_price,
                direction=direction,
                structure=shape,
                now=now,
                exit_dte_threshold=report.exit_policy.dte_threshold,
                force_flatten_at=get_authorized_ruleset().parameters.hackathon_window.force_flatten_by,
            )

        with suppress(OptionSelectionError, ValueError):
            candidates.append(
                ShadowCandidate(
                    label="contrarian",
                    strategy=select(opposite, primary_shape),
                    allocation_multiplier=Decimal("1"),
                    rationale="Deterministic opposite-direction counterfactual.",
                )
            )
        intent = report.shadow_alternative_intent
        if intent is not None:
            shape: Literal["long", "debit_spread"] = (
                "long"
                if intent.preferred_structure.value in {"long_call", "long_put"}
                else "debit_spread"
            )
            with suppress(OptionSelectionError, ValueError):
                candidates.append(
                    ShadowCandidate(
                        label="ai_alternative",
                        strategy=select(intent.direction.value, shape),
                        allocation_multiplier=Decimal("1"),
                        rationale=intent.rationale,
                    )
                )
        return candidates

    async def _resolve_iv_rank(
        self,
        session: AsyncSession,
        gateway: AlpacaPyGateway,
        underlying: str,
        strategy: Any,
        quotes: dict[str, dict[str, Any]],
        underlying_bars: list[dict[str, Any]],
        now: datetime,
    ) -> tuple[dict[str, Decimal], list[IvObservation]]:
        """Resolve a rank for every leg from live or timestamped history.

        A provider-supplied ``iv_rank`` on a current chain snapshot is already
        a sourced value.  Otherwise we combine the current Alpaca IV with
        durable observations and, when configured, a server-side historical
        provider.  Every observation is returned for immutable persistence.
        """

        history_start = now - timedelta(days=self.settings.iv_rank_lookback_days)
        self._last_option_bars_fallback = "not_attempted"
        self._last_iv_rank_resolution = {}
        provider_rows: list[dict[str, Any]] = []
        if self.settings.iv_rank_history_url:
            provider_rows = await asyncio.to_thread(
                gateway.get_iv_rank_history,
                underlying,
                start=history_start,
                end=now,
            )
        provider_observations = [IvObservation(**row) for row in provider_rows]
        result_by_leg: dict[str, Decimal] = {}
        resolution_by_leg: dict[str, dict[str, Any]] = {}
        persisted: list[IvObservation] = list(provider_observations)
        # Persist provider observations before attempting rank calculation so
        # an otherwise safe NO_TRADE cycle still warms the durable history.
        for observation in provider_observations:
            await self._persist_iv_observation(session, underlying, observation)
        for leg in strategy.legs:
            quote = quotes.get(leg.symbol)
            if not isinstance(quote, dict):
                raise IvRankUnavailable("Option quote is unavailable for IV rank")
            current_iv = _decimal(quote.get("iv"), Decimal("NaN"))
            if not current_iv.is_finite() or current_iv <= 0:
                raise IvRankUnavailable("Current implied volatility is unavailable")
            raw_rank = quote.get("iv_rank")
            try:
                direct_rank = Decimal(str(raw_rank)) if raw_rank is not None else Decimal("NaN")
            except (InvalidOperation, TypeError, ValueError):
                direct_rank = Decimal("NaN")
            quote_timestamp = quote.get("quote_timestamp")
            current_observation = IvObservation(
                observed_at=quote_timestamp if isinstance(quote_timestamp, datetime) else now,
                implied_volatility=current_iv,
                source="alpaca_option_chain",
                option_symbol=leg.symbol,
            )
            persisted.append(current_observation)
            await self._persist_iv_observation(session, underlying, current_observation)
            if direct_rank.is_finite() and Decimal("0") <= direct_rank <= Decimal("100"):
                result_by_leg[leg.symbol] = direct_rank
                resolution_by_leg[leg.symbol] = {
                    "path": "option_chain_direct_rank",
                    "configured_minimum_observations": self.settings.iv_rank_min_observations,
                    "effective_observation_count": 1,
                    "rank": str(direct_rank),
                }
                continue
            result, derived_observations = await self._compute_persisted_iv_rank(
                session,
                underlying,
                current_iv,
                now,
                provider_observations,
                option_symbol=leg.symbol,
                gateway=gateway,
                underlying_bars=underlying_bars,
                leg=leg,
            )
            result_by_leg[leg.symbol] = result.rank
            resolution_by_leg[leg.symbol] = {
                **getattr(self, "_last_iv_rank_resolution", {}),
                "rank": str(result.rank),
            }
            persisted.extend(derived_observations)
            for observation in derived_observations:
                await self._persist_iv_observation(session, underlying, observation)
        self._last_iv_rank_evidence = {
            "configured_minimum_observations": self.settings.iv_rank_min_observations,
            "legs": resolution_by_leg,
        }
        return result_by_leg, persisted

    async def _compute_persisted_iv_rank(
        self,
        session: AsyncSession,
        underlying: str,
        current_iv: Decimal,
        now: datetime,
        provider_observations: list[IvObservation],
        *,
        option_symbol: str,
        gateway: AlpacaPyGateway,
        underlying_bars: list[dict[str, Any]],
        leg: Any,
    ) -> tuple[Any, list[IvObservation]]:
        cutoff = now - timedelta(days=self.settings.iv_rank_lookback_days)
        result = await session.execute(
            select(OptionIvObservationModel).where(
                OptionIvObservationModel.underlying == underlying,
                OptionIvObservationModel.observed_at >= cutoff,
                OptionIvObservationModel.observed_at <= now,
            )
        )
        observations = [
            IvObservation(
                observed_at=row.observed_at,
                implied_volatility=row.implied_volatility,
                source=row.source,
                option_symbol=row.option_symbol,
            )
            for row in result.scalars()
        ]
        # A provider may publish underlying-level observations.  Prefer a
        # contract-specific history when it has enough rows; otherwise use
        # only rows explicitly scoped to the underlying.  Unrelated
        # strikes/expiries are never mixed into a rank.
        contract_observations = [
            item for item in observations if item.option_symbol == option_symbol
        ]
        provider_contract = [
            item for item in provider_observations if item.option_symbol == option_symbol
        ]
        contract_observations.extend(provider_contract)
        if len(contract_observations) >= self.settings.iv_rank_min_observations:
            observations = contract_observations
        else:
            underlying_scoped = [
                item
                for item in observations + provider_observations
                if item.option_symbol in {None, underlying}
            ]
            if len(underlying_scoped) >= self.settings.iv_rank_min_observations:
                observations = underlying_scoped
            elif observations or provider_observations:
                observations = observations + provider_observations
            else:
                observations = []
        derived_observations: list[IvObservation] = []
        fallback_status = "not_attempted"
        if len(observations) < self.settings.iv_rank_min_observations:
            fallback_status = "attempted"
            try:
                option_bars = await asyncio.to_thread(
                    gateway.get_option_bars,
                    option_symbol,
                    start=cutoff,
                    end=now,
                    limit=2000,
                )
            except Exception:
                option_bars = []
                fallback_status = "unavailable"
            else:
                fallback_status = "available" if option_bars else "unavailable"
            derived_observations = infer_iv_observations(
                option_bars,
                underlying_bars,
                leg=leg,
            )
            observations.extend(derived_observations)
        observations.append(
            IvObservation(
                observed_at=now,
                implied_volatility=current_iv,
                source="alpaca_option_chain",
                option_symbol=option_symbol,
            )
        )
        effective_min_obs = max(1, min(len(observations), self.settings.iv_rank_min_observations))
        self._last_option_bars_fallback = fallback_status
        self._last_iv_rank_resolution = {
            "path": "durable_provider_option_bars_current_observation",
            "configured_minimum_observations": self.settings.iv_rank_min_observations,
            "effective_observation_count": len(observations),
            "historical_option_bars_fallback": fallback_status,
        }
        return (
            compute_iv_rank(
                current_iv,
                observations,
                now=now,
                lookback_days=self.settings.iv_rank_lookback_days,
                minimum_observations=effective_min_obs,
            ),
            derived_observations,
        )

    async def _persist_iv_observation(
        self, session: AsyncSession, underlying: str, observation: IvObservation
    ) -> None:
        option_symbol = observation.option_symbol or underlying
        digest = input_digest(
            {
                "underlying": underlying,
                "option_symbol": option_symbol,
                "observed_at": observation.observed_at,
                "implied_volatility": observation.implied_volatility,
                "source": observation.source,
            }
        )
        existing = await session.execute(
            select(OptionIvObservationModel).where(
                OptionIvObservationModel.observation_digest == digest
            )
        )
        if existing.scalar_one_or_none() is not None:
            return
        session.add(
            OptionIvObservationModel(
                id=str(uuid4()),
                underlying=underlying,
                option_symbol=option_symbol,
                observed_at=observation.observed_at,
                implied_volatility=observation.implied_volatility,
                source=observation.source,
                observation_digest=digest,
            )
        )
        await session.flush()

    @staticmethod
    def _portfolio_snapshot(account: Any, positions: list[Any], now: datetime) -> dict[str, Any]:
        status_value = _field(account, "status", default="")
        status = str(getattr(status_value, "value", status_value)).lower()
        level_raw = _field(account, "options_trading_level", "options_level")
        level = _option_level(level_raw)
        normalized_positions = []
        for position in positions:
            symbol = str(_field(position, "symbol", default="")).strip().upper()
            try:
                parsed = parse_instrument(symbol)
            except ValueError:
                parsed = None
            qty_raw = _field(position, "qty", default=None)
            market_value_raw = _field(position, "market_value", default=None)
            avg_entry_price_raw = _field(position, "avg_entry_price", default=None)
            delta_raw = _field(position, "delta", default=None)
            vega_raw = _field(position, "vega", default=None)
            expiration_raw = _field(
                position,
                "expiration",
                default=(parsed.expiration.isoformat() if parsed and parsed.expiration else None),
            )
            position_values_complete = all(
                value is not None
                for value in (
                    _finite_decimal(qty_raw),
                    _finite_decimal(market_value_raw),
                    _finite_decimal(avg_entry_price_raw),
                )
            )
            normalized_positions.append(
                {
                    "symbol": symbol,
                    "underlying": parsed.underlying if parsed else symbol,
                    "asset_class": parsed.asset_class if parsed else "unknown",
                    "qty": _string_or_none(qty_raw),
                    "market_value": _string_or_none(market_value_raw),
                    "avg_entry_price": _string_or_none(avg_entry_price_raw),
                    "unrealized_pl": str(_field(position, "unrealized_pl", default="0")),
                    "unrealized_plpc": str(_field(position, "unrealized_plpc", default="")),
                    "opened_at": _timestamp_iso(
                        _field(position, "opened_at", "created_at", default=None)
                    ),
                    "sector": _field(position, "sector", default=parsed.sector if parsed else None),
                    "correlated_cluster": _field(
                        position,
                        "correlated_cluster",
                        default=parsed.correlated_cluster if parsed else None,
                    ),
                    "delta": _string_or_none(delta_raw),
                    "vega": _string_or_none(vega_raw),
                    "expiration": (
                        expiration_raw.isoformat()
                        if hasattr(expiration_raw, "isoformat")
                        else _string_or_none(expiration_raw)
                    ),
                    "option_type": parsed.option_type if parsed else None,
                    "strike": str(parsed.strike) if parsed and parsed.strike is not None else None,
                    "metadata_source": "alpaca_position+prism_occ_parser",
                    "position_values_complete": position_values_complete,
                }
            )
        account_values = (
            _field(account, "cash", default=None),
            _field(account, "buying_power", default=None),
            _field(account, "portfolio_value", "equity", default=None),
            _field(account, "last_equity", "last_day_equity", default=None),
        )
        account_values_complete = all(
            _finite_decimal(value) is not None for value in account_values
        )
        return {
            "observed_at": now.isoformat(),
            "account_status": status,
            "account_verified": status == "active",
            "supported_options_level": level,
            "cash": _string_or_none(account_values[0]),
            "buying_power": _string_or_none(account_values[1]),
            "portfolio_value": _string_or_none(account_values[2]),
            "start_of_day_equity": _string_or_none(account_values[3]),
            "account_values_complete": account_values_complete,
            "positions": normalized_positions,
        }

    async def _refresh_position_metadata(
        self, gateway: AlpacaPyGateway, portfolio: dict[str, Any], now: datetime
    ) -> dict[str, Any]:
        """Complete option Greeks/expiry from fresh server-side chain quotes."""

        by_underlying: dict[str, dict[str, dict[str, Any]]] = {}
        for position in portfolio["positions"]:
            if position.get("asset_class") != "us_option":
                # Equity delta is one share per unit and vega is exactly zero;
                # this is a mechanical exposure, not an option Greek guess.
                qty = _decimal(position.get("qty"))
                position["delta"] = position.get("delta") or ("-1" if qty < 0 else "1")
                position["vega"] = position.get("vega") or "0"
                try:
                    position["metadata_complete"] = bool(
                        position.get("position_values_complete")
                        and metadata_complete(parse_instrument(str(position.get("symbol", ""))))
                    )
                except ValueError:
                    position["metadata_complete"] = False
                continue
            underlying = str(position.get("underlying", "")).upper()
            if underlying not in by_underlying:
                try:
                    by_underlying[underlying] = await asyncio.to_thread(
                        gateway.get_option_chain, underlying
                    )
                except Exception:
                    by_underlying[underlying] = {}
            quote = by_underlying[underlying].get(str(position.get("symbol", "")))
            if quote is not None:
                qty = _decimal(position.get("qty"))
                position["bid"] = str(quote.get("bid"))
                position["ask"] = str(quote.get("ask"))
                position["price_increment"] = str(quote.get("price_increment", "0.01"))
                position["delta"] = str(_decimal(quote.get("delta")) * qty)
                position["vega"] = str(_decimal(quote.get("vega")) * qty)
                position["iv"] = str(quote.get("iv"))
                position["quote_timestamp"] = _timestamp_iso(quote.get("quote_timestamp"))
                position["provider_quote_timestamp"] = quote.get("quote_timestamp")
                position["metadata_source"] = "alpaca_position+alpaca_option_chain"
                quote_timestamp = quote.get("quote_timestamp")
                if isinstance(quote_timestamp, datetime) and quote_timestamp.tzinfo is not None:
                    # ``now`` is captured before the chain request, so a valid
                    # provider quote may be fractionally newer than the cycle.
                    position["quote_age_seconds"] = str(
                        max(0, (now - quote_timestamp.astimezone(UTC)).total_seconds())
                    )
            try:
                parsed_position = parse_instrument(str(position.get("symbol", "")))
            except ValueError:
                parsed_position = None
            position["metadata_complete"] = bool(
                quote is not None
                and position.get("position_values_complete")
                and parsed_position is not None
                and metadata_complete(parsed_position)
                and isinstance(position.get("delta"), str)
                and isinstance(position.get("vega"), str)
                and position.get("quote_timestamp") is not None
                and _decimal(position.get("quote_age_seconds"), Decimal("999999"))
                <= Decimal(str(get_authorized_ruleset().parameters.data_freshness_seconds))
            )
        portfolio["positions_metadata_complete"] = all(
            bool(item.get("metadata_complete")) for item in portfolio["positions"]
        )
        portfolio["positions_observed_at"] = now.isoformat()
        return portfolio

    async def _persist_portfolio_snapshot(
        self, session: AsyncSession, portfolio: dict[str, Any]
    ) -> str:
        digest = input_digest(portfolio)
        session.add(
            PortfolioSnapshotModel(
                id=str(uuid4()),
                observed_at=datetime.fromisoformat(portfolio["observed_at"]),
                account_verified=bool(portfolio["account_verified"]),
                supported_options_level=portfolio["supported_options_level"],
                snapshot_digest=digest,
                payload_json=json.dumps(_json_value(portfolio), default=str, sort_keys=True),
            )
        )
        await session.flush()
        return digest

    def _authorization_inputs(
        self,
        report: Any,
        analog: HistoricalAnalogSummary,
        strategy: Any,
        portfolio: dict[str, Any],
        now: datetime,
        quotes: dict[str, dict[str, Any]],
        financials: Any,
        *,
        quantity: int = 1,
        iv_rank_by_leg: dict[str, Decimal] | None = None,
        profile: ActiveProfile,
    ) -> dict[str, Any]:
        market_snapshot = {
            "symbol": report.symbol,
            "underlying_price": str(report.current_price),
            "strategy": strategy.model_dump(mode="json"),
            "observed_at": now.isoformat(),
            "quotes": {
                leg.symbol: {
                    "bid": str(quotes[leg.symbol].get("bid")),
                    "ask": str(quotes[leg.symbol].get("ask")),
                    "quote_timestamp": _timestamp_iso(quotes[leg.symbol].get("quote_timestamp")),
                    "delta": str(quotes[leg.symbol].get("delta")),
                    "gamma": str(quotes[leg.symbol].get("gamma")),
                    "theta": str(quotes[leg.symbol].get("theta")),
                    "vega": str(quotes[leg.symbol].get("vega")),
                    "iv": str(quotes[leg.symbol].get("iv")),
                    "price_increment": str(quotes[leg.symbol].get("price_increment", "0.01")),
                    "iv_rank": str(
                        (iv_rank_by_leg or {}).get(leg.symbol, quotes[leg.symbol].get("iv_rank"))
                    ),
                }
                for leg in strategy.legs
                if leg.symbol in quotes
            },
        }
        market_digest = input_digest(market_snapshot)
        portfolio_digest = input_digest(portfolio)
        cash = _decimal(portfolio.get("cash"))
        buying_power = _decimal(portfolio.get("buying_power"))
        order_cost = strategy.limit_price * Decimal("100") * Decimal(quantity)
        rules = get_authorized_ruleset().parameters
        # The rule is a minimum cash reserve, not a cap that reserves the
        # complement of the baseline account value. Use current equity so the
        # control remains correct after gains, losses, or an account reset.
        cash_buffer_ok = self._cash_reserve_ok(
            cash=cash,
            order_cost=order_cost,
            portfolio_value=_decimal(portfolio.get("portfolio_value")),
            cash_buffer_pct=_decimal(rules.cash_buffer_pct),
        )
        quote_ages: list[Decimal] = []
        spreads: list[Decimal] = []
        for leg in strategy.legs:
            quote = quotes.get(leg.symbol)
            if quote is None:
                continue
            timestamp = quote.get("quote_timestamp")
            if isinstance(timestamp, datetime) and timestamp.tzinfo is not None:
                quote_ages.append(
                    Decimal(str(max(0.0, (now - timestamp.astimezone(UTC)).total_seconds())))
                )
            bid = _decimal(quote.get("bid"))
            ask = _decimal(quote.get("ask"))
            midpoint = (bid + ask) / Decimal("2")
            if midpoint > 0:
                spreads.append((ask - bid) / midpoint * Decimal("100"))
        required_quote_count = len(strategy.legs)
        quote_timestamps_valid = len(quote_ages) == required_quote_count and all(
            age >= 0 for age in quote_ages
        )
        market_fresh = quote_timestamps_valid and max(
            quote_ages, default=Decimal("999999")
        ) <= Decimal(str(rules.data_freshness_seconds))
        fundamentals_sourced = (
            getattr(financials, "provenance", None) == "sec_filing"
            and isinstance(getattr(financials, "data_as_of", None), datetime)
            and financials.data_as_of.tzinfo is not None
        )
        drawdown_baseline = _decimal(portfolio.get("start_of_day_equity"))
        drawdown_pct = self._drawdown_pct(portfolio, drawdown_baseline)
        if drawdown_pct >= _decimal(rules.drawdown_halt_pct):
            portfolio_risk_state = PortfolioRiskState.HALT
        elif drawdown_pct >= _decimal(rules.drawdown_defensive_pct):
            portfolio_risk_state = PortfolioRiskState.DEFENSIVE
        elif drawdown_pct >= _decimal(rules.drawdown_caution_pct):
            portfolio_risk_state = PortfolioRiskState.CAUTION
        else:
            portfolio_risk_state = PortfolioRiskState.NORMAL
        market_regime = self._market_regime(report)
        iv_rank_available = all(
            (
                (
                    iv_rank := (iv_rank_by_leg or {}).get(
                        leg.symbol,
                        _decimal(quotes.get(leg.symbol, {}).get("iv_rank"), Decimal("NaN")),
                    )
                ).is_finite()
                and Decimal("0") <= iv_rank <= Decimal("100")
            )
            for leg in strategy.legs
        )
        risk_base = _decimal(portfolio.get("portfolio_value"))
        risk_pct = (
            rules.volatile_risk_per_trade_pct
            if market_regime is MarketRegime.VOLATILE
            else rules.max_risk_per_trade_pct
        )
        max_trade_risk = risk_base * _decimal(risk_pct) / Decimal("100")
        existing_exposure = sum(
            (
                abs(_decimal(item.get("max_loss_per_contract", item.get("market_value"))))
                for item in portfolio["positions"]
            ),
            Decimal("0"),
        )
        planned_risk = (
            analog.max_loss_per_contract or strategy.limit_price * Decimal("100")
        ) * Decimal(quantity)
        profile_target_cap = (
            risk_base * profile.parameters.target_position_size_pct / Decimal("100")
        )
        position_size_ok = planned_risk <= max_trade_risk and order_cost <= profile_target_cap
        aggregate_risk_ok = existing_exposure + planned_risk <= (
            risk_base * _decimal(rules.aggregate_hard_stop_risk_pct) / Decimal("100")
        )
        portfolio_controls_complete = bool(
            portfolio.get("account_values_complete")
            and portfolio.get("positions_metadata_complete", not portfolio["positions"])
        )
        candidate_metadata = parse_instrument(report.symbol)
        equity = risk_base
        candidate_exposure = order_cost

        def existing_exposure_by(key: str, value: Any) -> Decimal:
            return sum(
                (
                    abs(_decimal(item.get("market_value")))
                    for item in portfolio["positions"]
                    if str(item.get(key, "")).upper() == str(value).upper()
                ),
                Decimal("0"),
            )

        ticker_exposure_pct = (
            (existing_exposure_by("underlying", candidate_metadata.underlying) + candidate_exposure)
            / equity
            * Decimal("100")
            if equity > 0
            else Decimal("999999")
        )
        sector_exposure_pct = (
            (existing_exposure_by("sector", candidate_metadata.sector) + candidate_exposure)
            / equity
            * Decimal("100")
            if equity > 0 and candidate_metadata.sector
            else Decimal("999999")
        )
        cluster_exposure_pct = (
            (
                existing_exposure_by("correlated_cluster", candidate_metadata.correlated_cluster)
                + candidate_exposure
            )
            / equity
            * Decimal("100")
            if equity > 0 and candidate_metadata.correlated_cluster
            else Decimal("999999")
        )
        expiration = strategy.legs[0].expiration
        expiration_exposure = sum(
            (
                abs(_decimal(item.get("market_value")))
                for item in portfolio["positions"]
                if item.get("expiration") == expiration
            ),
            Decimal("0"),
        )
        # Expiration concentration is measured against the authorized
        # aggregate hard-stop budget: positions expiring together must not
        # consume more modeled loss capacity than the portfolio cap.
        expiration_concentration_ok = bool(
            portfolio_controls_complete
            and expiration_exposure + planned_risk
            <= equity * _decimal(rules.aggregate_hard_stop_risk_pct) / Decimal("100")
        )
        # Greek exposure is refreshed from the option chain above.  Apply the
        # same authorized aggregate risk budget to a one-percent underlying
        # move and one volatility-point move; no binary floats or defaults are
        # permitted.  This makes the check incremental and deterministic.
        existing_delta_notional = sum(
            (
                _decimal(item.get("delta"))
                * abs(_decimal(item.get("market_value")))
                * Decimal("0.01")
                for item in portfolio["positions"]
            ),
            Decimal("0"),
        )
        existing_vega_notional = sum(
            (
                _decimal(item.get("vega"))
                * abs(_decimal(item.get("market_value")))
                * Decimal("0.01")
                for item in portfolio["positions"]
            ),
            Decimal("0"),
        )
        candidate_delta = sum(
            (
                _decimal(quotes.get(leg.symbol, {}).get("delta"))
                * (Decimal("1") if leg.side.value == "buy" else Decimal("-1"))
                * report.current_price
                * Decimal("100")
                * Decimal(quantity)
                * Decimal("0.01")
                for leg in strategy.legs
            ),
            Decimal("0"),
        )
        candidate_vega = sum(
            (
                _decimal(quotes.get(leg.symbol, {}).get("vega"))
                * (Decimal("1") if leg.side.value == "buy" else Decimal("-1"))
                * Decimal("100")
                * Decimal(quantity)
                * Decimal("0.01")
                for leg in strategy.legs
            ),
            Decimal("0"),
        )
        greek_budget = equity * _decimal(rules.aggregate_hard_stop_risk_pct) / Decimal("100")
        greeks_risk_ok = (
            portfolio_controls_complete
            and all(
                value.is_finite()
                for value in (
                    existing_delta_notional,
                    existing_vega_notional,
                    candidate_delta,
                    candidate_vega,
                )
            )
            and abs(existing_delta_notional + candidate_delta) <= greek_budget
            and abs(existing_vega_notional + candidate_vega) <= greek_budget
        )
        return {
            "market_fresh": market_fresh,
            "fundamentals_sourced": fundamentals_sourced,
            "account_verified": portfolio["account_verified"],
            "open_positions": len(portfolio["positions"]),
            "buying_power_ok": buying_power >= order_cost,
            "cash_buffer_ok": cash_buffer_ok,
            "concentration_ok": ticker_exposure_pct <= _decimal(rules.ticker_concentration_pct),
            "position_size_ok": position_size_ok,
            "profile_target_allocation_pct": profile.parameters.target_position_size_pct,
            "aggregate_risk_ok": aggregate_risk_ok,
            "portfolio_controls_complete": portfolio_controls_complete,
            "sector_concentration_ok": sector_exposure_pct
            <= _decimal(rules.sector_concentration_pct),
            "cluster_concentration_ok": cluster_exposure_pct
            <= _decimal(rules.correlated_cluster_concentration_pct),
            "greeks_risk_ok": greeks_risk_ok,
            "expiration_concentration_ok": expiration_concentration_ok,
            "ticker_exposure_pct": ticker_exposure_pct,
            "sector_exposure_pct": sector_exposure_pct,
            "cluster_exposure_pct": cluster_exposure_pct,
            "expiration_exposure_pct": (
                (expiration_exposure + candidate_exposure) / equity * Decimal("100")
                if equity > 0
                else Decimal("999999")
            ),
            "net_delta_exposure": existing_delta_notional + candidate_delta,
            "net_vega_exposure": existing_vega_notional + candidate_vega,
            "quote_age_seconds": max(quote_ages, default=Decimal("999999")),
            "spread_pct": max(spreads, default=Decimal("999999")),
            "within_entry_window": now < rules.hackathon_window.new_entry_cutoff_at,
            "before_force_flatten": now < rules.hackathon_window.force_flatten_by,
            "opportunity_score": report.composite_opportunity_score,
            "net_ev_r": analog.net_ev_r,
            "reward_risk_ratio": analog.reward_risk_ratio
            if analog.reward_risk_ratio is not None
            else Decimal("0"),
            "market_regime": market_regime,
            "portfolio_risk_state": portfolio_risk_state,
            "market_open": True,
            "iv_rank_available": iv_rank_available,
            "iv_rank": max(
                [
                    (iv_rank_by_leg or {}).get(
                        leg.symbol,
                        _decimal(quotes.get(leg.symbol, {}).get("iv_rank"), Decimal("-1")),
                    )
                    for leg in strategy.legs
                ],
                default=Decimal("-1"),
            ),
            "market_snapshot_digest": market_digest,
            "portfolio_snapshot_digest": portfolio_digest,
            "market_snapshot": market_snapshot,
            "account_observed_at": now,
            "supported_options_level": portfolio["supported_options_level"] or 0,
        }

    @staticmethod
    def _drawdown_pct(portfolio: dict[str, Any], starting_capital: Any) -> Decimal:
        starting = _decimal(starting_capital)
        equity = _decimal(portfolio.get("portfolio_value"))
        if starting <= 0 or equity <= 0:
            return Decimal("100")
        return max(Decimal("0"), (starting - equity) / starting * Decimal("100"))

    @staticmethod
    def _cash_reserve_ok(
        *,
        cash: Decimal,
        order_cost: Decimal,
        portfolio_value: Decimal,
        cash_buffer_pct: Decimal,
    ) -> bool:
        """Check the BA minimum cash reserve against current equity."""
        if portfolio_value <= 0 or cash_buffer_pct < 0:
            return False
        required_reserve = portfolio_value * cash_buffer_pct / Decimal("100")
        return cash - order_cost >= required_reserve

    @staticmethod
    def _remaining_holding_sessions(now: datetime, exit_policy: ExitPolicy) -> int:
        force_date = get_authorized_ruleset().parameters.hackathon_window.force_flatten_by.date()
        cursor = now.date()
        sessions = 0
        while cursor <= force_date:
            if cursor.weekday() < 5:
                sessions += 1
            cursor += timedelta(days=1)
        return max(1, min(exit_policy.max_hold_days, sessions))

    @staticmethod
    def _proposal_quantity(
        economics: HistoricalAnalogSummary,
        portfolio: dict[str, Any],
        profile: ActiveProfile,
        *,
        market_regime: MarketRegime,
        underlying: str,
    ) -> int:
        rules = get_authorized_ruleset().parameters
        equity = _decimal(portfolio.get("portfolio_value"))
        max_loss = economics.max_loss_per_contract or Decimal("0")
        premium = economics.premium_per_contract or Decimal("0")
        if equity <= 0 or max_loss <= 0 or premium <= 0:
            return 0
        risk_pct = (
            rules.volatile_risk_per_trade_pct
            if market_regime is MarketRegime.VOLATILE
            else rules.max_risk_per_trade_pct
        )
        existing_risk = sum(
            (
                abs(_decimal(item.get("max_loss_per_contract", item.get("market_value"))))
                for item in portfolio.get("positions", [])
            ),
            Decimal("0"),
        )
        ticker_exposure = sum(
            (
                abs(_decimal(item.get("market_value")))
                for item in portfolio.get("positions", [])
                if str(item.get("underlying", "")).upper() == underlying.upper()
            ),
            Decimal("0"),
        )
        risk_budget = equity * _decimal(risk_pct) / Decimal("100")
        allocation_budget = equity * profile.parameters.target_position_size_pct / Decimal("100")
        aggregate_remaining = max(
            Decimal("0"),
            equity * _decimal(rules.aggregate_hard_stop_risk_pct) / Decimal("100") - existing_risk,
        )
        ticker_remaining = max(
            Decimal("0"),
            equity * _decimal(rules.ticker_concentration_pct) / Decimal("100") - ticker_exposure,
        )
        cash_remaining = max(
            Decimal("0"),
            _decimal(portfolio.get("cash"))
            - equity * _decimal(rules.cash_buffer_pct) / Decimal("100"),
        )
        buying_power = max(Decimal("0"), _decimal(portfolio.get("buying_power")))
        risk_contracts = min(risk_budget, aggregate_remaining) // max_loss
        cost_contracts = (
            min(
                allocation_budget,
                ticker_remaining,
                cash_remaining,
                buying_power,
            )
            // premium
        )
        return max(0, int(min(risk_contracts, cost_contracts)))

    @staticmethod
    def _market_regime(report: Any) -> MarketRegime:
        # Macro climate is the only persisted regime proxy in the decision
        # contract.  Derive a conservative deterministic regime rather than
        # silently asserting NORMAL for every market.
        score = _decimal(
            getattr(getattr(report, "specialist_scores", None), "macro_climate_score", 0)
        )
        if score <= 25:
            return MarketRegime.CRISIS
        if score <= 50:
            return MarketRegime.VOLATILE
        return MarketRegime.NORMAL

    @staticmethod
    def _market_is_open(gateway: AlpacaPyGateway) -> bool:
        try:
            clock = gateway.get_clock()
        except Exception:
            return False
        value = _field(clock, "is_open", default=None)
        return value is True or str(value).lower() == "true"

    async def _persist_authorization(self, session: AsyncSession, decision: Any) -> None:
        session.add(
            AuthorizationModel(
                id=str(decision.id),
                trace_id=str(decision.trace_id),
                created_at=decision.created_at,
                proposal_id=str(decision.proposal_id),
                proposal_version=decision.proposal_version,
                proposal_digest=decision.proposal_digest,
                ruleset_id=decision.ruleset_id,
                ruleset_version=decision.ruleset_version,
                profile_id=str(decision.profile_id),
                profile_version=decision.profile_version,
                outcome=decision.outcome.value,
                market_snapshot_digest=decision.market_snapshot_digest,
                portfolio_snapshot_digest=decision.portfolio_snapshot_digest,
                decision_at=decision.decision_at,
                expires_at=decision.expires_at,
                payload_json=decision.model_dump_json(),
                rule_trace_json=json.dumps(
                    [rule.model_dump(mode="json") for rule in decision.rule_trace], sort_keys=True
                ),
            )
        )
        await session.flush()

    async def _persist_no_trade(
        self, session: AsyncSession, proposal: TradeProposal, reason: str
    ) -> None:
        root = build_evaluation_root(
            trace_id=proposal.trace_id,
            outcome="NO_TRADE",
            evidence={"reason": reason},
            proposal_digest=proposal.proposal_digest,
        )
        await self._persist_root(session, proposal.id, root)

    async def _persist_root(self, session: AsyncSession, aggregate_id: UUID, root: Any) -> None:
        session.add(
            AutonomousAuditEventModel(
                id=str(uuid4()),
                created_at=datetime.now(UTC),
                aggregate_type="evaluation_root",
                aggregate_id=str(aggregate_id),
                event_type="immutable_evaluation",
                payload_digest=root.root_digest,
                payload_json=root.model_dump_json(),
            )
        )
        await session.flush()

    async def _force_flatten(
        self, session: AsyncSession, positions: list[Any], now: datetime
    ) -> bool:
        """Flatten durable strategies first, then legacy legs short-first."""

        gateway = AlpacaCliExecutionGateway(self.settings, SubprocessRunner(), None)  # type: ignore[arg-type]
        repository = SqlAlchemyReceiptRepository(session)
        current_symbols = {
            str(_field(position, "symbol", default="")).upper() for position in positions
        }
        tracked_symbols: set[str] = set()
        success = True
        strategies = list(
            (
                await session.scalars(
                    select(StrategyPositionModel).where(
                        StrategyPositionModel.status.in_(["open", "entry_pending", "exiting"])
                    )
                )
            ).all()
        )
        quotes = self._position_quotes(positions)
        for row in strategies:
            strategy = OptionStrategy.model_validate_json(row.strategy_json)
            leg_symbols = {leg.symbol.upper() for leg in strategy.legs}
            tracked_symbols.update(leg_symbols)
            if not leg_symbols.intersection(current_symbols):
                await self._close_strategy_record(
                    session, row, now, "force_flatten_position_absent"
                )
                continue
            if row.parent_exit_receipt_id is not None:
                continue
            row.exit_latched_reason = ExitReason.HACKATHON_FORCE_FLATTEN.value
            row.exit_latched_at = row.exit_latched_at or now
            if len(strategy.legs) == 2:
                try:
                    liquidation = executable_liquidation_value(
                        strategy,
                        quotes,
                        now=now,
                        max_quote_age_seconds=get_authorized_ruleset().parameters.data_freshness_seconds,
                    )
                except StrategyMarkUnavailable:
                    success = False
                    continue
                receipt = await gateway.close_strategy_async(
                    strategy,
                    strategy_position_id=UUID(row.id),
                    trace_id=uuid4(),
                    exit_reason=ExitReason.HACKATHON_FORCE_FLATTEN,
                    requested_quantity=Decimal(row.quantity),
                    limit_price=self._round_strategy_credit(liquidation, strategy, quotes),
                    repository=repository,
                )
            else:
                leg = strategy.legs[0]
                receipt = await gateway.close_position_async(
                    leg.symbol,
                    trace_id=uuid4(),
                    exit_reason=ExitReason.HACKATHON_FORCE_FLATTEN,
                    requested_quantity=Decimal(row.quantity * leg.ratio_qty),
                    repository=repository,
                )
            await self._bind_exit_receipt(session, row, receipt, now)
            success = success and receipt.status.value in {
                "pending",
                "submitted",
                "reconciling",
                "filled",
            }

        legacy = [
            position
            for position in positions
            if str(_field(position, "symbol", default="")).upper() not in tracked_symbols
        ]
        # A legacy spread has no trustworthy parent record. Submit closes for
        # shorts only; a later cycle confirms their absence before any longs.
        legacy_shorts = [p for p in legacy if _decimal(_field(p, "qty", default="0")) < 0]
        legacy_targets = legacy_shorts or [
            p for p in legacy if _decimal(_field(p, "qty", default="0")) > 0
        ]
        for position in legacy_targets:
            symbol = str(_field(position, "symbol", default=""))
            if not symbol:
                continue
            receipt = await gateway.close_position_async(
                symbol,
                trace_id=uuid4(),
                exit_reason=ExitReason.HACKATHON_FORCE_FLATTEN,
                requested_quantity=self._position_quantity(position),
                repository=repository,
            )
            success = success and receipt.status.value in {
                "pending",
                "submitted",
                "reconciling",
                "filled",
            }
        return success

    async def _manage_exits(
        self,
        session: AsyncSession,
        positions: list[Any],
        now: datetime,
        *,
        include_score_evidence: bool,
    ) -> tuple[bool, set[str], list[dict[str, str]]]:
        """Mark complete strategies and apply ExitPolicyV2 before new risk."""

        rules = get_authorized_ruleset().parameters
        gateway = AlpacaCliExecutionGateway(self.settings, SubprocessRunner(), None)  # type: ignore[arg-type]
        repository = SqlAlchemyReceiptRepository(session)
        position_by_symbol = {
            str(_field(position, "symbol", default="")).upper(): position for position in positions
        }
        quotes = self._position_quotes(positions)
        strategy_rows = list(
            (
                await session.scalars(
                    select(StrategyPositionModel).where(
                        StrategyPositionModel.status.in_(["open", "entry_pending", "exiting"])
                    )
                )
            ).all()
        )
        tracked_symbols: set[str] = set()
        exited_symbols: set[str] = set()
        checks: list[dict[str, str]] = []
        for row in strategy_rows:
            strategy = OptionStrategy.model_validate_json(row.strategy_json)
            leg_symbols = {leg.symbol.upper() for leg in strategy.legs}
            tracked_symbols.update(leg_symbols)
            label = row.underlying
            present = leg_symbols.intersection(position_by_symbol)
            if row.status == "entry_pending" and not present:
                checks.append({"symbol": label, "result": "hold", "reason": "entry_pending"})
                continue
            if row.status == "exiting" or row.parent_exit_receipt_id is not None:
                checks.append(
                    {
                        "symbol": label,
                        "result": "exit_pending",
                        "reason": row.exit_latched_reason or "latched",
                    }
                )
                continue
            if not present:
                await self._close_strategy_record(session, row, now, "position_absent")
                exited_symbols.update(leg_symbols)
                checks.append({"symbol": label, "result": "exit", "reason": "position_absent"})
                continue
            try:
                liquidation = executable_liquidation_value(
                    strategy,
                    quotes,
                    now=now,
                    max_quote_age_seconds=rules.data_freshness_seconds,
                )
                current_return = strategy_return_pct(_decimal(row.entry_debit), liquidation)
            except StrategyMarkUnavailable:
                checks.append(
                    {"symbol": label, "result": "hold", "reason": "strategy_mark_unavailable"}
                )
                continue

            original_score: Decimal | None = None
            opposite_score: Decimal | None = None
            fresh_score = False
            score_record: TradeDecisionModel | None = None
            if include_score_evidence:
                score_record = await session.scalar(
                    select(TradeDecisionModel)
                    .where(
                        TradeDecisionModel.symbol == row.underlying,
                        TradeDecisionModel.created_at
                        > (row.last_score_evidence_at or row.opened_at),
                    )
                    .order_by(TradeDecisionModel.created_at.desc())
                    .limit(1)
                )
                if score_record is not None and score_record.id != row.last_score_evidence_id:
                    fresh_score = True
                    if row.direction == "bullish":
                        original_score = _decimal(score_record.bullish_opportunity_score)
                        opposite_score = _decimal(score_record.bearish_opportunity_score)
                    else:
                        original_score = _decimal(score_record.bearish_opportunity_score)
                        opposite_score = _decimal(score_record.bullish_opportunity_score)

            try:
                expiration = datetime.fromisoformat(strategy.legs[0].expiration).date()
                dte_days: int | None = (expiration - now.date()).days
            except ValueError:
                dte_days = None
            policy = ExitPolicy.model_validate_json(row.exit_policy_json)
            evaluation = evaluate_adaptive_exit(
                policy,
                current_return_pct=current_return,
                prior_mfe_pct=_decimal(row.mfe_pct),
                profit_armed=row.profit_armed_at is not None,
                prior_score_failure_count=row.score_failure_count,
                original_direction_score=original_score,
                opposite_direction_score=opposite_score,
                score_floor=rules.balanced_opportunity_score,
                fresh_direction_evidence=fresh_score,
                trading_minutes_elapsed=regular_session_minutes_elapsed(row.opened_at, now),
                dte_days=dte_days,
                force_flatten_due=now >= rules.hackathon_window.force_flatten_by,
            )
            row.last_liquidation_value = liquidation
            row.current_return_pct = evaluation.current_return_pct
            row.mfe_pct = evaluation.mfe_pct
            row.score_failure_count = evaluation.score_failure_count
            row.last_marked_at = now
            if evaluation.profit_armed and row.profit_armed_at is None:
                row.profit_armed_at = now
            if fresh_score and score_record is not None:
                row.last_score_evidence_at = score_record.created_at
                row.last_score_evidence_id = score_record.id
            await self._record_strategy_event(
                session,
                row,
                now,
                "strategy_marked",
                {
                    "liquidation_value": str(liquidation),
                    "current_return_pct": str(evaluation.current_return_pct),
                    "mfe_pct": str(evaluation.mfe_pct),
                    "profit_armed": evaluation.profit_armed,
                    "score_failure_count": evaluation.score_failure_count,
                    "score_evidence_id": score_record.id if fresh_score and score_record else None,
                },
            )
            if evaluation.exit_reason is None:
                checks.append({"symbol": label, "result": "hold", "reason": "no_exit_condition"})
                continue

            row.exit_latched_reason = evaluation.exit_reason.value
            row.exit_latched_at = now
            await self._record_strategy_event(
                session,
                row,
                now,
                "exit_latched",
                {"reason": evaluation.exit_reason.value},
            )
            if len(strategy.legs) == 2:
                receipt = await gateway.close_strategy_async(
                    strategy,
                    strategy_position_id=UUID(row.id),
                    trace_id=uuid4(),
                    exit_reason=evaluation.exit_reason,
                    requested_quantity=Decimal(row.quantity),
                    limit_price=self._round_strategy_credit(liquidation, strategy, quotes),
                    repository=repository,
                )
            else:
                leg = strategy.legs[0]
                receipt = await gateway.close_position_async(
                    leg.symbol,
                    trace_id=uuid4(),
                    exit_reason=evaluation.exit_reason,
                    requested_quantity=Decimal(row.quantity * leg.ratio_qty),
                    repository=repository,
                )
            await self._bind_exit_receipt(session, row, receipt, now)
            if receipt.status is ExecutionStatus.FILLED:
                exited_symbols.update(leg_symbols)
                checks.append(
                    {"symbol": label, "result": "exit", "reason": evaluation.exit_reason.value}
                )
            elif receipt.status in {
                ExecutionStatus.PENDING,
                ExecutionStatus.SUBMITTED,
                ExecutionStatus.RECONCILING,
            }:
                checks.append(
                    {
                        "symbol": label,
                        "result": "exit_pending",
                        "reason": evaluation.exit_reason.value,
                    }
                )
            else:
                checks.append(
                    {
                        "symbol": label,
                        "result": "exit_failed",
                        "reason": evaluation.exit_reason.value,
                    }
                )
                return False, exited_symbols, checks

        legacy = [
            position
            for position in positions
            if str(_field(position, "symbol", default="")).upper() not in tracked_symbols
        ]
        legacy_ok, legacy_exited, legacy_checks = await self._manage_legacy_exits(
            session, legacy, now, gateway, repository
        )
        checks.extend(legacy_checks)
        exited_symbols.update(legacy_exited)
        return legacy_ok, exited_symbols, checks

    @staticmethod
    def _position_quotes(positions: list[Any]) -> dict[str, dict[str, Any]]:
        quotes: dict[str, dict[str, Any]] = {}
        for position in positions:
            symbol = str(_field(position, "symbol", default="")).upper()
            timestamp = _field(position, "provider_quote_timestamp", default=None)
            if not isinstance(timestamp, datetime):
                iso_timestamp = _field(position, "quote_timestamp", default=None)
                if isinstance(iso_timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
                    except ValueError:
                        timestamp = None
            if not symbol or not isinstance(timestamp, datetime):
                continue
            quotes[symbol] = {
                "bid": _field(position, "bid", default=None),
                "ask": _field(position, "ask", default=None),
                "price_increment": _field(position, "price_increment", default="0.01"),
                "quote_timestamp": timestamp,
            }
        return quotes

    @staticmethod
    def _round_strategy_credit(
        liquidation: Decimal,
        strategy: OptionStrategy,
        quotes: dict[str, dict[str, Any]],
    ) -> Decimal:
        increments = [
            _decimal(quotes.get(leg.symbol, {}).get("price_increment"), Decimal("0.01"))
            for leg in strategy.legs
        ]
        increment = max((value for value in increments if value > 0), default=Decimal("0.01"))
        rounded = (liquidation // increment) * increment
        return max(increment, rounded)

    async def _record_strategy_event(
        self,
        session: AsyncSession,
        row: StrategyPositionModel,
        observed_at: datetime,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        session.add(
            StrategyLifecycleEventModel(
                id=str(uuid4()),
                strategy_position_id=row.id,
                observed_at=observed_at,
                event_type=event_type,
                payload_digest=hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
                payload_json=encoded,
            )
        )
        await session.flush()

    async def _close_strategy_record(
        self,
        session: AsyncSession,
        row: StrategyPositionModel,
        now: datetime,
        confirmation: str,
    ) -> None:
        if row.status == "closed":
            return
        row.status = "closed"
        row.closed_at = now
        await self._record_strategy_event(
            session,
            row,
            now,
            "strategy_closed",
            {"confirmation": confirmation, "exit_reason": row.exit_latched_reason},
        )

    async def _bind_exit_receipt(
        self,
        session: AsyncSession,
        row: StrategyPositionModel,
        receipt: Any,
        now: datetime,
    ) -> None:
        receipt_row = await session.scalar(
            select(ExecutionReceiptModel).where(
                ExecutionReceiptModel.client_order_id == receipt.client_order_id
            )
        )
        row.parent_exit_receipt_id = receipt_row.id if receipt_row is not None else None
        if receipt.status is ExecutionStatus.FILLED:
            await self._close_strategy_record(session, row, now, "broker_filled")
        else:
            row.status = "exiting"
            await self._record_strategy_event(
                session,
                row,
                now,
                "exit_submitted",
                {
                    "client_order_id": receipt.client_order_id,
                    "receipt_status": receipt.status.value,
                    "exit_reason": row.exit_latched_reason,
                },
            )

    async def _manage_legacy_exits(
        self,
        session: AsyncSession,
        positions: list[Any],
        now: datetime,
        gateway: AlpacaCliExecutionGateway,
        repository: SqlAlchemyReceiptRepository,
    ) -> tuple[bool, set[str], list[dict[str, str]]]:
        """Exit ungrouped positions without inventing spread P&L."""

        rules = get_authorized_ruleset().parameters
        targets: list[tuple[Any, ExitReason]] = []
        checks: list[dict[str, str]] = []
        for position in positions:
            symbol = str(_field(position, "symbol", default="")).upper()
            reason: ExitReason | None = None
            match = re.search(r"(\d{6})[CP]", symbol)
            if match:
                try:
                    expiry = datetime.strptime(match.group(1), "%y%m%d").date()
                except ValueError:
                    expiry = None
                if (
                    expiry is not None
                    and (expiry - now.date()).days <= rules.dte_threshold_default_days
                ):
                    reason = ExitReason.DTE_THRESHOLD
            opened_at = _field(position, "opened_at", "created_at", default=None)
            if (
                reason is None
                and isinstance(opened_at, datetime)
                and opened_at.tzinfo is not None
                and regular_session_minutes_elapsed(opened_at, now)
                >= rules.hackathon_max_hold_trading_days * 390
            ):
                reason = ExitReason.MAX_HOLD_DAYS
            if reason is None:
                checks.append({"symbol": symbol, "result": "hold", "reason": "legacy_no_safe_exit"})
            else:
                targets.append((position, reason))

        short_targets = [
            item for item in targets if _decimal(_field(item[0], "qty", default="0")) < 0
        ]
        if short_targets:
            deferred = {str(_field(item[0], "symbol", default="")).upper() for item in targets}
            deferred.difference_update(
                str(_field(item[0], "symbol", default="")).upper() for item in short_targets
            )
            checks.extend(
                {"symbol": symbol, "result": "hold", "reason": "legacy_short_close_first"}
                for symbol in sorted(deferred)
            )
            targets = short_targets

        exited: set[str] = set()
        for position, reason in targets:
            symbol = str(_field(position, "symbol", default="")).upper()
            active = await session.scalar(
                select(ExecutionReceiptModel.id)
                .where(
                    ExecutionReceiptModel.operation == "exit",
                    ExecutionReceiptModel.symbol == symbol,
                    ExecutionReceiptModel.status.in_(["pending", "submitted", "reconciling"]),
                )
                .limit(1)
            )
            if active is not None:
                checks.append({"symbol": symbol, "result": "exit_pending", "reason": reason.value})
                continue
            receipt = await gateway.close_position_async(
                symbol,
                trace_id=uuid4(),
                exit_reason=reason,
                requested_quantity=self._position_quantity(position),
                repository=repository,
            )
            if receipt.status is ExecutionStatus.FILLED:
                exited.add(symbol)
                checks.append({"symbol": symbol, "result": "exit", "reason": reason.value})
            elif receipt.status in {
                ExecutionStatus.PENDING,
                ExecutionStatus.SUBMITTED,
                ExecutionStatus.RECONCILING,
            }:
                checks.append({"symbol": symbol, "result": "exit_pending", "reason": reason.value})
            else:
                checks.append({"symbol": symbol, "result": "exit_failed", "reason": reason.value})
                return False, exited, checks
        return True, exited, checks

    async def _persist_strategy_position(
        self,
        session: AsyncSession,
        proposal: TradeProposal,
        receipt: Any,
        now: datetime,
    ) -> None:
        if receipt.status not in {
            ExecutionStatus.PENDING,
            ExecutionStatus.SUBMITTED,
            ExecutionStatus.RECONCILING,
            ExecutionStatus.FILLED,
        }:
            return
        row = await session.scalar(
            select(StrategyPositionModel).where(
                StrategyPositionModel.proposal_id == str(proposal.id)
            )
        )
        entry_debit = receipt.filled_average_price or proposal.strategy.limit_price
        opened_at = receipt.reconciled_at or receipt.submitted_at or now
        if row is None:
            row = StrategyPositionModel(
                id=str(uuid4()),
                proposal_id=str(proposal.id),
                thesis_key=proposal.thesis_key or proposal.proposal_digest,
                catalyst_digest=proposal.catalyst_digest or proposal.proposal_digest,
                underlying=proposal.symbol,
                direction=(
                    "bullish"
                    if proposal.strategy.kind
                    in {StrategyKind.LONG_CALL, StrategyKind.CALL_DEBIT_SPREAD}
                    else "bearish"
                ),
                strategy_kind=proposal.strategy.kind.value,
                strategy_json=proposal.strategy.model_dump_json(),
                exit_policy_json=proposal.exit_policy.model_dump_json(),
                quantity=proposal.quantity,
                entry_debit=entry_debit,
                opened_at=opened_at,
                status="open" if receipt.status is ExecutionStatus.FILLED else "entry_pending",
                mfe_pct=Decimal("0"),
                score_failure_count=0,
            )
            session.add(row)
            await session.flush()
            await self._record_strategy_event(
                session,
                row,
                now,
                "strategy_created",
                {
                    "entry_debit": str(entry_debit),
                    "quantity": proposal.quantity,
                    "entry_receipt_status": receipt.status.value,
                },
            )
        elif receipt.status is ExecutionStatus.FILLED:
            row.status = "open"
            row.entry_debit = entry_debit
            row.opened_at = opened_at

        receipt.strategy_position_id = UUID(row.id)
        receipt.legs = [
            {
                "symbol": leg.symbol,
                "ratio_qty": leg.ratio_qty,
                "position_intent": leg.position_intent or "buy_to_open",
                "status": receipt.status,
            }
            for leg in proposal.strategy.legs
        ]
        # Validate the per-leg state through the public contract before it is persisted.
        from app.contracts.models import ExecutionLegState

        receipt.legs = [ExecutionLegState.model_validate(item) for item in receipt.legs]
        await SqlAlchemyReceiptRepository(session).save(receipt)

    async def _strategy_position_count(self, session: AsyncSession, positions: list[Any]) -> int:
        rows = list(
            (
                await session.scalars(
                    select(StrategyPositionModel).where(
                        StrategyPositionModel.status.in_(["open", "entry_pending", "exiting"])
                    )
                )
            ).all()
        )
        tracked = {
            leg.symbol.upper()
            for row in rows
            for leg in OptionStrategy.model_validate_json(row.strategy_json).legs
        }
        legacy_count = sum(
            1
            for position in positions
            if str(_field(position, "symbol", default="")).upper() not in tracked
        )
        return len(rows) + legacy_count

    @staticmethod
    def _position_quantity(position: Any) -> Decimal | None:
        quantity = _finite_decimal(_field(position, "qty", "quantity", default=None))
        if quantity is None:
            return None
        return abs(quantity)

    async def _reconcile_exit_receipts(
        self, session: AsyncSession, positions: list[Any], now: datetime
    ) -> None:
        """Mark a submitted position close filled only after the position disappears."""
        current_symbols = {
            str(_field(position, "symbol", default="")).upper() for position in positions
        }
        result = await session.execute(
            select(ExecutionReceiptModel).where(
                ExecutionReceiptModel.operation == "exit",
                ExecutionReceiptModel.status.in_(["pending", "submitted", "reconciling"]),
            )
        )
        for row in result.scalars():
            strategy_row: StrategyPositionModel | None = None
            if row.strategy_position_id:
                strategy_row = await session.get(StrategyPositionModel, row.strategy_position_id)
                if strategy_row is None:
                    continue
                strategy = OptionStrategy.model_validate_json(strategy_row.strategy_json)
                if any(leg.symbol.upper() in current_symbols for leg in strategy.legs):
                    continue
            elif not row.symbol or row.symbol.upper() in current_symbols:
                continue
            previous_status = row.status
            row.status = "filled"
            row.filled_quantity = row.requested_quantity or row.filled_quantity
            row.error_code = None
            row.error_message = None
            row.reconciled_at = now
            session.add(
                ReconciliationEventModel(
                    id=str(uuid4()),
                    receipt_id=row.id,
                    transition=f"{previous_status}->filled",
                    observed_at=now,
                    payload_json=json.dumps(
                        {
                            "operation": "exit",
                            "symbol": row.symbol,
                            "exit_reason": row.exit_reason,
                            "confirmation": "position_absent",
                        },
                        default=str,
                        sort_keys=True,
                    ),
                )
            )
            if strategy_row is not None:
                await self._close_strategy_record(
                    session, strategy_row, now, "all_strategy_legs_absent"
                )
        await session.flush()

    async def _reconcile_unfinished(self, session: AsyncSession) -> None:
        """Resolve pending submissions by persisted client order ID on restart."""
        result = await session.execute(
            select(ExecutionReceiptModel).where(
                ExecutionReceiptModel.operation == "entry",
                ExecutionReceiptModel.status.in_(["pending", "submitted", "reconciling"]),
            )
        )
        rows = list(result.scalars())
        if not rows:
            return
        executor = AlpacaCliExecutionGateway(self.settings, SubprocessRunner(), None)  # type: ignore[arg-type]
        repository = SqlAlchemyReceiptRepository(session)
        for row in rows:
            receipt = repository._to_contract(row)
            previous_status = receipt.status.value
            await executor.reconcile_async(receipt, repository)
            strategy_row = await session.scalar(
                select(StrategyPositionModel).where(
                    StrategyPositionModel.proposal_id == str(row.proposal_id)
                )
            )
            if strategy_row is not None:
                if receipt.status is ExecutionStatus.FILLED:
                    strategy_row.status = "open"
                    strategy_row.entry_debit = (
                        receipt.filled_average_price or strategy_row.entry_debit
                    )
                    strategy_row.opened_at = receipt.reconciled_at or datetime.now(UTC)
                    await self._record_strategy_event(
                        session,
                        strategy_row,
                        datetime.now(UTC),
                        "entry_reconciled_filled",
                        {"client_order_id": receipt.client_order_id},
                    )
                elif receipt.status in {ExecutionStatus.REJECTED, ExecutionStatus.FAILED}:
                    strategy_row.status = "entry_failed"
                    await self._record_strategy_event(
                        session,
                        strategy_row,
                        datetime.now(UTC),
                        "entry_reconciled_failed",
                        {
                            "client_order_id": receipt.client_order_id,
                            "status": receipt.status.value,
                        },
                    )
            if receipt.status.value != previous_status or receipt.error_code:
                session.add(
                    ReconciliationEventModel(
                        id=str(uuid4()),
                        receipt_id=row.id,
                        transition=f"{previous_status}->{receipt.status.value}",
                        observed_at=datetime.now(UTC),
                        payload_json=json.dumps(
                            {
                                "client_order_id": receipt.client_order_id,
                                "broker_order_id": receipt.broker_order_id,
                                "error_code": receipt.error_code,
                            },
                            default=str,
                            sort_keys=True,
                        ),
                    )
                )
        await session.flush()

    async def _acquire_cycle_lock(self, session: AsyncSession) -> bool:
        bind = session.get_bind()
        if bind is None or bind.dialect.name != "postgresql":
            return True
        lock_key = int.from_bytes(
            hashlib.sha256(b"prism-autonomous-cycle").digest()[:8], "big", signed=True
        )
        result = await session.execute(
            text("SELECT pg_try_advisory_lock(:lock_key)"), {"lock_key": lock_key}
        )
        return bool(result.scalar())

    async def _record(
        self,
        session: AsyncSession,
        started_at: datetime,
        outcome: str,
        reason: str,
        *,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        cycle_id = str(uuid4())
        root_evidence: dict[str, Any] = {"symbols": AUTONOMOUS_SYMBOLS, "reason": reason}
        if evidence:
            root_evidence.update(evidence)
        exit_checks = evidence.get("position_exit_checks", []) if evidence else []
        safe_exit_checks = [
            {
                "symbol": str(item.get("symbol", "UNKNOWN")).upper(),
                "result": str(item.get("result", "hold")),
                "reason": str(item.get("reason", "no_exit_condition")),
            }
            for item in exit_checks
            if isinstance(item, dict)
        ]
        root = build_evaluation_root(
            trace_id=uuid4(),
            outcome=outcome,
            evidence=root_evidence,
        )
        session.add(
            AutonomousCycleModel(
                id=cycle_id,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                outcome=outcome,
                symbols_json=json.dumps(AUTONOMOUS_SYMBOLS),
                reason=reason,
                exit_checks_json=json.dumps(safe_exit_checks, default=str, sort_keys=True),
                worker_version=WORKER_VERSION,
            )
        )
        session.add(
            AutonomousAuditEventModel(
                id=str(uuid4()),
                created_at=datetime.now(UTC),
                aggregate_type="autonomous_cycle",
                aggregate_id=cycle_id,
                event_type=f"cycle_{outcome.lower()}",
                payload_digest=root.root_digest,
                payload_json=root.model_dump_json(),
            )
        )
        if self.settings.shadowfund_enabled:
            try:
                async with session.begin_nested():
                    shadow_service = ShadowFundService()
                    await shadow_service.create_terminal_session(
                        session,
                        root=root,
                        terminal_outcome=outcome,
                        proposal=None,
                        authorization=None,
                        source_mode="production",
                        source_feed="not_applicable",
                        refusal_reason=reason,
                        horizon_at=get_authorized_ruleset().parameters.hackathon_window.official_scoring_at,
                    )
                    if reason == "Hackathon force-flatten executed":
                        window = get_authorized_ruleset().parameters.hackathon_window
                        agent = PostAnalysisAgent(LLMGateway(self.settings))
                        active_profile = await ProfileGovernanceService().get_active(session)
                        summary, recommendations = await agent.analyze_week(
                            session,
                            window_start=window.trading_start_at,
                            window_end=window.official_scoring_at,
                            source_mode="production",
                            active_profile=active_profile,
                        )
                        batch = await shadow_service.persist_post_analysis_batch(
                            session,
                            source_mode="production",
                            window_start=window.trading_start_at,
                            window_end=window.official_scoring_at,
                            model_metadata={
                                "trigger": "official_scoring",
                                "agent": POST_ANALYSIS_AGENT_VERSION,
                                "worker": WORKER_VERSION,
                            },
                            summary=summary,
                            recommendations=recommendations,
                        )
                        await ProfileGovernanceService().apply_automatic_if_enabled(
                            session,
                            batch_id=batch.id,
                            operator_id=self.settings.auth_email,
                        )
            except Exception:
                logger.exception("ShadowFund no-trade session failed without affecting cycle")

    async def _run_weekly_post_analysis_if_due(
        self, session: AsyncSession, now: datetime
    ) -> str | None:
        """Execute weekly post-analysis after Friday market close if not already completed."""
        if not self.settings.shadowfund_enabled or not is_friday_post_close(now):
            return None
        window_start, window_end = get_trading_week_bounds(now)
        existing = await session.scalar(
            select(ShadowPostAnalysisBatchModel.id).where(
                ShadowPostAnalysisBatchModel.source_mode == "production",
                ShadowPostAnalysisBatchModel.window_start == window_start,
                ShadowPostAnalysisBatchModel.window_end == window_end,
            )
        )
        if existing is not None:
            return None

        agent = PostAnalysisAgent(LLMGateway(self.settings))
        active_profile = await ProfileGovernanceService().get_active(session)
        summary, recommendations = await agent.analyze_week(
            session,
            window_start=window_start,
            window_end=window_end,
            source_mode="production",
            active_profile=active_profile,
        )
        shadow_service = ShadowFundService()
        batch = await shadow_service.persist_post_analysis_batch(
            session,
            source_mode="production",
            window_start=window_start,
            window_end=window_end,
            model_metadata={
                "trigger": "weekly_friday_post_analysis",
                "agent": POST_ANALYSIS_AGENT_VERSION,
                "worker": WORKER_VERSION,
            },
            summary=summary,
            recommendations=recommendations,
        )
        await ProfileGovernanceService().apply_automatic_if_enabled(
            session,
            batch_id=batch.id,
            operator_id=self.settings.auth_email,
        )
        logger.info(
            "Weekly Friday post-analysis completed: batch_id=%s, state=%s",
            batch.id,
            batch.state,
        )
        return batch.id


def window_date(now: datetime) -> Any:
    # The selected contract must outlive the force-flatten date; the selector
    # enforces the lower bound. This upper bound only keeps provider queries
    # finite and does not relax the authorized holding window.
    return now.date() + timedelta(days=365)
