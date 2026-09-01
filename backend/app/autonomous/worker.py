from __future__ import annotations

import asyncio
import hashlib
import json
import logging
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
    TradeProposalModel,
)
from app.contracts.models import (
    AuthorizationOutcome,
    ExitPolicy,
    MarketRegime,
    OptionPayoffEconomics,
    PortfolioRiskState,
    ShadowCandidate,
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
from app.research.post_analysis import (
    POST_ANALYSIS_AGENT_VERSION,
    PostAnalysisAgent,
    get_trading_week_bounds,
    is_friday_post_close,
)
from app.research.risk_agent import RiskManagementAgent
from app.research.sec_fundamentals import SecFundamentalsUnavailable, fetch_sec_company_financials
from app.rules.evaluator import authorize_proposal, input_digest
from app.rules.registry import get_authorized_ruleset
from app.shadowfund.models import ShadowPostAnalysisBatchModel, ShadowSessionModel
from app.shadowfund.service import ShadowFundService

logger = logging.getLogger(__name__)

AUTONOMOUS_SYMBOLS = ("NVDA", "TSLA", "AAPL", "MSFT", "AMD", "GOOGL", "AMZN")
WORKER_VERSION = "production-parity-v3"


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

    async def run_forever(self, stop_event: asyncio.Event) -> None:
        flatten_attempted = False
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
                    await self._wait(
                        stop_event, min(self.settings.autonomous_scan_interval_seconds, 60)
                    )
                    continue
                try:
                    outcome = await self.run_cycle(now=now)
                except Exception:
                    logger.exception("Autonomous cycle failed closed")
                    outcome = "FAILED"
                if flatten_due and outcome == "FLATTENED":
                    flatten_attempted = True
                await self._wait(stop_event, self.settings.autonomous_scan_interval_seconds)
            else:
                try:
                    async for session in get_db_session():
                        if await self._acquire_cycle_lock(session):
                            await self._run_weekly_post_analysis_if_due(session, now)
                            await session.commit()
                except Exception:
                    logger.exception("Weekly post-analysis check failed closed")
                await self._wait(
                    stop_event, min(self.settings.autonomous_scan_interval_seconds, 60)
                )

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
            if kill_switch_active:
                await self._record(session, now, "NO_TRADE", "Kill switch active")
                await session.commit()
                return "NO_TRADE"
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
                    if not await self._force_flatten(session, positions):
                        await self._record(session, now, "FAILED", "Force-flatten command failed")
                        await session.commit()
                        return "FAILED"
                    await self._record(session, now, "NO_TRADE", "Hackathon force-flatten executed")
                    await session.commit()
                    return "FLATTENED"
                await self._reconcile_exit_receipts(session, positions, now)
                exits_ok, exited_symbols, exit_checks = await self._manage_exits(
                    session, positions, now
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
                candidates.sort(
                    key=lambda item: _decimal(item[2].get("opportunity_score")), reverse=True
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

                open_positions = len(positions)
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
            # AI proposes an exit policy, but profile-owned take-profit and
            # fixed stop values are bound deterministically before a proposal
            # can be persisted or authorized.
            exit_policy = ExitPolicy(
                take_profit_pct=active_profile.parameters.take_profit_pct,
                stop_loss_pct=active_profile.parameters.stop_loss_pct,
                dte_threshold=report.exit_policy.dte_threshold,
                max_hold_days=report.exit_policy.max_hold_days,
            )
            direction: Literal["bullish", "bearish"] = (
                "bullish" if report.direction.value == "bullish" else "bearish"
            )
            analog = compute_historical_analogs(bars, direction=direction, now=now)
            structure: Literal["long", "debit_spread"] = (
                "long"
                if report.recommended_structure.value in {"long_call", "long_put"}
                else "debit_spread"
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

            candidate_strategies = select_candidate_option_strategies(
                contracts,
                quotes,
                underlying_price=report.current_price,
                direction=direction,
                structure=structure,
                now=now,
                exit_dte_threshold=exit_policy.dte_threshold,
                force_flatten_at=get_authorized_ruleset().parameters.hackathon_window.force_flatten_by,
                max_candidates=5,
            )
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

            # Sort candidate strategies by:
            # 1. Meets authorized Net EV floor of 0.15R (True before False)
            # 2. Net EV (descending)
            # 3. Reward-to-Risk ratio (descending)
            evaluated.sort(
                key=lambda item: (
                    item[1].net_ev_r >= Decimal("0.15"),
                    item[1].net_ev_r,
                    item[1].reward_risk_ratio or Decimal("0"),
                ),
                reverse=True,
            )
            strategy, option_economics = evaluated[0]
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
                "quantity": 1,
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
            proposal_digest = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            proposal = TradeProposal(
                trace_id=trace_id,
                research_report_id=report.id,
                symbol=symbol,
                strategy=strategy,
                quantity=1,
                rationale=report.synthesis_rationale,
                exit_policy=exit_policy,
                shadow_candidates=shadow_candidates,
                option_economics=proposal_economics,
                research_bundle_digest=bundle_digest,
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
                position["delta"] = str(_decimal(quote.get("delta")) * qty)
                position["vega"] = str(_decimal(quote.get("vega")) * qty)
                position["iv"] = str(quote.get("iv"))
                position["quote_timestamp"] = _timestamp_iso(quote.get("quote_timestamp"))
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
                payload_json=json.dumps(portfolio, sort_keys=True),
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
        order_cost = strategy.limit_price * Decimal("100")
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
        planned_risk = analog.max_loss_per_contract or order_cost
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
                * Decimal("0.01")
                for leg in strategy.legs
            ),
            Decimal("0"),
        )
        greek_budget = equity * _decimal(rules.aggregate_hard_stop_risk_pct) / Decimal("100")
        greeks_risk_ok = bool(
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

    async def _force_flatten(self, session: AsyncSession, positions: list[Any]) -> bool:
        runner = SubprocessRunner()
        gateway = AlpacaCliExecutionGateway(self.settings, runner, None)  # type: ignore[arg-type]
        repository = SqlAlchemyReceiptRepository(session)
        success = True
        for position in positions:
            symbol = str(_field(position, "symbol", default=""))
            if symbol:
                receipt = await gateway.close_position_async(
                    symbol,
                    trace_id=uuid4(),
                    exit_reason="hackathon_force_flatten",
                    requested_quantity=self._position_quantity(position),
                    repository=repository,
                )
                success = success and receipt.status.value in {"submitted", "filled"}
        return success

    async def _manage_exits(
        self, session: AsyncSession, positions: list[Any], now: datetime
    ) -> tuple[bool, set[str], list[dict[str, str]]]:
        """Apply mandatory paper exits before evaluating any new entry.

        Alpaca positions expose unrealized P/L as a decimal fraction.  OCC
        symbols expose expiration in YYMMDD; positions that do not contain
        either field are left untouched and are handled by force-flatten.
        Unknown values never trigger a speculative close.
        """
        symbols: set[str] = set()
        checks: list[dict[str, str]] = []
        max_hold_days = get_authorized_ruleset().parameters.hackathon_max_hold_trading_days
        for position in positions:
            symbol = str(_field(position, "symbol", default=""))
            plpc_raw = _field(position, "unrealized_plpc", default=None)
            plpc = _decimal(plpc_raw, Decimal("NaN")) if plpc_raw is not None else Decimal("NaN")
            if plpc.is_finite() and (plpc >= Decimal("0.75") or plpc <= Decimal("-0.50")):
                symbols.add(symbol)
                checks.append({"symbol": symbol, "result": "exit", "reason": "pnl_threshold"})
                continue
            opened_at = _field(position, "opened_at", "created_at", default=None)
            if (
                isinstance(opened_at, datetime)
                and opened_at.tzinfo is not None
                and (now - opened_at.astimezone(UTC)).days >= max_hold_days
            ):
                symbols.add(symbol)
                checks.append({"symbol": symbol, "result": "exit", "reason": "max_hold_days"})
                continue
            match = re.search(r"(\d{6})[CP]", symbol)
            if match:
                try:
                    expiry = datetime.strptime(match.group(1), "%y%m%d").date()
                except ValueError:
                    expiry = None
                if expiry is not None and (expiry - now.date()).days <= 7:
                    symbols.add(symbol)
                    checks.append({"symbol": symbol, "result": "exit", "reason": "dte_threshold"})
                    continue
            checks.append({"symbol": symbol, "result": "hold", "reason": "no_exit_condition"})
        if not symbols:
            return True, set(), checks
        gateway = AlpacaCliExecutionGateway(self.settings, SubprocessRunner(), None)  # type: ignore[arg-type]
        repository = SqlAlchemyReceiptRepository(session)
        active_result = await session.execute(
            select(ExecutionReceiptModel).where(
                ExecutionReceiptModel.operation == "exit",
                ExecutionReceiptModel.symbol.in_(symbols),
                ExecutionReceiptModel.status.in_(["pending", "submitted", "reconciling"]),
            )
        )
        active_exit_symbols = {
            str(row.symbol) for row in active_result.scalars() if row.symbol is not None
        }
        for symbol in sorted(symbols):
            check = next(check for check in checks if check["symbol"] == symbol)
            if symbol in active_exit_symbols:
                check["result"] = "exit_pending"
                continue
            receipt = await gateway.close_position_async(
                symbol,
                trace_id=uuid4(),
                exit_reason=check["reason"],
                requested_quantity=self._position_quantity(
                    next(
                        position
                        for position in positions
                        if str(_field(position, "symbol", default="")) == symbol
                    )
                ),
                repository=repository,
            )
            if receipt.status.value == "filled":
                continue
            if receipt.status.value in {"pending", "submitted", "reconciling"}:
                check["result"] = "exit_pending"
                continue
            check["result"] = "exit_failed"
            return False, symbols, checks
        confirmed_symbols = {check["symbol"] for check in checks if check["result"] == "exit"}
        return True, confirmed_symbols, checks

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
            if not row.symbol or row.symbol.upper() in current_symbols:
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
                    receipt_id=str(row.id),
                    transition=f"{previous_status}->filled",
                    observed_at=now,
                    payload_json=json.dumps(
                        {
                            "operation": "exit",
                            "symbol": row.symbol,
                            "exit_reason": row.exit_reason,
                            "confirmation": "position_absent",
                        },
                        sort_keys=True,
                    ),
                )
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
            if receipt.status.value != previous_status or receipt.error_code:
                session.add(
                    ReconciliationEventModel(
                        id=str(uuid4()),
                        receipt_id=str(row.id),
                        transition=f"{previous_status}->{receipt.status.value}",
                        observed_at=datetime.now(UTC),
                        payload_json=json.dumps(
                            {
                                "client_order_id": receipt.client_order_id,
                                "broker_order_id": receipt.broker_order_id,
                                "error_code": receipt.error_code,
                            },
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
                exit_checks_json=json.dumps(safe_exit_checks, sort_keys=True),
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
