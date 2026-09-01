"""Run the bounded staging historical simulation without an execution adapter."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import subprocess
from contextlib import suppress
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.autonomous.audit import build_evaluation_root
from app.backtest.historical_gateway import HistoricalResearchGateway
from app.backtest.historical_options import (
    HistoricalOptionsProvider,
    HistoricalOptionsUnavailable,
    HttpHistoricalOptionsProvider,
    normalize_quote,
    quote_map_at,
)
from app.backtest.models import BacktestAuditEventModel, BacktestRunModel
from app.backtest.simulator import EASTERN, DeterministicOptionSimulator, ReplayWindow
from app.backtest.virtual_authorization import evaluate_virtual_authorization
from app.contracts.models import OptionStrategy, OptionStructure, TradeProposal
from app.core.config import get_settings
from app.core.database import close_database, get_db_session, init_db
from app.core.llm_gateway import LLMGateway
from app.market.alpaca_gateway import AlpacaPyGateway
from app.market.option_selection import OptionSelectionError, select_option_strategy
from app.profiles.service import ProfileGovernanceService
from app.research.decision_agent import TradingDecisionAgent
from app.research.risk_agent import RiskManagementAgent
from app.research.sec_fundamentals import SecFundamentalsUnavailable, fetch_sec_company_financials
from app.rules.registry import get_authorized_ruleset
from app.shadowfund.models import ShadowBranchModel
from app.shadowfund.service import ShadowFundService

START = "2026-08-24"
END = "2026-08-27"
SYMBOLS = ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "GOOGL", "META"]
# Alpaca returns stock bars in ascending order.  The replay gateway requests a
# 730-day lookback, so a 250-row limit only returns the oldest part of that
# range and can stop well before the historical checkpoint.  Keep enough
# headroom for the full daily-bar window plus non-trading days.
HISTORICAL_BAR_LIMIT = 1000
REPLAY_WINDOW = ReplayWindow()
REPLAY_CADENCE_SECONDS = 300
DISCLOSURE = (
    "Important disclosure: This backtest is a hypothetical historical simulation and does not "
    "represent actual trading performance. Backtested results do not guarantee future results. "
    "Results depend on market-data quality, data feed selection, corporate-action handling, "
    "fees, slippage, liquidity, taxes, execution assumptions, and implementation details. "
    "This material is for research and educational purposes only and is not investment advice, "
    "a recommendation, an offer, or a solicitation to buy or sell securities, options, "
    "cryptocurrencies, or any other financial product. All investments involve risk and may "
    "lose value. Review Alpaca's disclosures and agreements at "
    "https://alpaca.markets/disclosures."
)
PAPER_DISCLOSURE = (
    "Paper trading is a simulated environment. It does not involve real money or actual "
    "securities transactions. Paper results may differ from live trading because of fill "
    "assumptions, market impact, liquidity, latency, data differences, order handling, fees, "
    "and other market conditions."
)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, default=str, sort_keys=True).encode()).hexdigest()


def _preflight(cli_path: str) -> str:
    version = subprocess.run(
        [cli_path, "version"], capture_output=True, text=True, timeout=10, check=False
    )
    if version.returncode != 0:
        raise RuntimeError("Alpaca CLI version preflight failed")
    doctor = subprocess.run(
        [cli_path, "doctor"], capture_output=True, text=True, timeout=30, check=False
    )
    if doctor.returncode != 0:
        raise RuntimeError("Alpaca CLI doctor preflight failed")
    return version.stdout.strip().splitlines()[0][:64]


def _options_provider(settings: Any) -> HistoricalOptionsProvider | None:
    """Build the explicitly configured staging-only historical NBBO adapter."""

    injected = getattr(settings, "historical_options_provider", None)
    if injected is not None:
        if not str(getattr(injected, "feed", "")).strip():
            raise ValueError("historical options provider feed is required")
        return injected
    url = getattr(settings, "historical_options_url", None)
    if not url:
        return None
    return HttpHistoricalOptionsProvider(
        url,
        api_key=getattr(settings, "historical_options_api_key", None),
        feed=str(getattr(settings, "historical_options_feed", "OPRA")),
        timeout=float(getattr(settings, "alpaca_request_timeout_seconds", 30)),
    )


def _proposal_from_decision(decision: Any, strategy: Any) -> TradeProposal:
    """Bind a strict historical decision to a local, non-persisted proposal."""

    payload = {
        "research_report_id": str(decision.id),
        "symbol": decision.symbol,
        "strategy": strategy.model_dump(mode="json"),
        "quantity": 1,
        "exit_policy": decision.exit_policy.model_dump(mode="json"),
    }
    return TradeProposal(
        trace_id=decision.trace_id,
        research_report_id=decision.id,
        symbol=decision.symbol,
        strategy=strategy,
        quantity=1,
        rationale=decision.synthesis_rationale,
        exit_policy=decision.exit_policy,
        proposal_digest=_digest(payload),
    )


def _selection_inputs(decision: Any) -> tuple[str, str] | None:
    if decision.direction.value not in {"bullish", "bearish"}:
        return None
    structure = decision.recommended_structure
    if structure in {OptionStructure.LONG_CALL, OptionStructure.LONG_PUT}:
        return decision.direction.value, "long"
    if structure in {OptionStructure.BULL_CALL_SPREAD, OptionStructure.BEAR_PUT_SPREAD}:
        return decision.direction.value, "debit_spread"
    return None


INTERRUPTED_RUN_REASON = (
    "Backtest process ended before completion; this record was recovered when a subsequent "
    "staging simulation started."
)


async def _recover_interrupted_runs(session: AsyncSession, *, recovered_at: datetime) -> int:
    """Close abandoned runs before starting a new staging simulation.

    A container restart can terminate the detached backtest process before its
    final transaction runs.  Leaving those rows in ``RUNNING`` makes the audit
    history claim that work is still active and can confuse operators.  A new
    manually-triggered simulation is the explicit recovery boundary, so prior
    running rows are finalized as fail-closed ``DATA_UNAVAILABLE`` records.
    """

    rows = list(
        (
            await session.scalars(
                select(BacktestRunModel).where(BacktestRunModel.status == "RUNNING")
            )
        ).all()
    )
    for record in rows:
        try:
            summary = json.loads(record.summary_json)
        except (TypeError, ValueError):
            summary = {}
        if not isinstance(summary, dict):
            summary = {}
        summary.update(
            {
                "outcome": "DATA_UNAVAILABLE",
                "reason": INTERRUPTED_RUN_REASON,
                "recovered_at": recovered_at.isoformat(),
            }
        )
        record.completed_at = recovered_at
        record.status = "DATA_UNAVAILABLE"
        record.summary_json = json.dumps(summary, default=str)
        record.is_active_presentation = False
        session.add(record)
        session.add(
            BacktestAuditEventModel(
                id=str(uuid4()),
                run_id=record.id,
                created_at=recovered_at,
                event_type="SIMULATION_INTERRUPTED",
                payload_digest=_digest(summary),
                payload_json=json.dumps(summary, default=str),
            )
        )
    return len(rows)


def _expected_report_count() -> int:
    """Return the exact number of weekday/symbol replay decisions required."""

    checkpoint = datetime.fromisoformat(f"{START}T00:00:00+00:00")
    end = datetime.fromisoformat(f"{END}T00:00:00+00:00")
    trading_days = 0
    while checkpoint <= end:
        if checkpoint.weekday() < 5:
            trading_days += 1
        checkpoint += timedelta(days=1)
    return trading_days * len(SYMBOLS)


async def run() -> int:
    settings = get_settings()
    if settings.environment != "staging" or not settings.backtest_simulation_enabled:
        raise RuntimeError(
            "Historical simulation is enabled only in staging with BACKTEST_SIMULATION_ENABLED=true"
        )
    if not settings.alpaca_paper or settings.alpaca_live_trade:
        raise RuntimeError("Historical simulation requires paper-only configuration")
    if not settings.shadowfund_enabled:
        raise RuntimeError(
            "Historical simulation requires SHADOWFUND_ENABLED=true for its isolated "
            "counterfactual evaluation"
        )
    cli_version = _preflight(settings.alpaca_cli_path)
    run_id = str(uuid4())
    created_at = datetime.now(UTC)
    output = Path(settings.backtest_output_dir) / f"{created_at:%Y%m%dT%H%M%SZ}_{run_id}"
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "run_id": run_id,
        "start": START,
        "end": END,
        "symbols": SYMBOLS,
        "cli_version": cli_version,
        "mode": "historical_options_simulation",
        "timezone": "America/New_York",
        "cadence_seconds": REPLAY_CADENCE_SECONDS,
        "entry_cutoff": REPLAY_WINDOW.new_entry_cutoff.isoformat(),
        "force_flatten_at": REPLAY_WINDOW.force_flatten_at.isoformat(),
        "options_feed": getattr(settings, "historical_options_feed", "OPRA"),
        "options_provider_configured": bool(
            getattr(settings, "historical_options_url", None)
            or getattr(settings, "historical_options_provider", None)
        ),
        "execution": "disabled",
    }
    (output / "config.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output / "notes.md").write_text(
        f"# PRISM staging historical simulation\n\n{DISCLOSURE}\n\n{PAPER_DISCLOSURE}\n\n"
        "Execution is disabled; this run uses only historical, non-executable ShadowFund "
        "counterfactuals and observed NBBO touches.\n",
        encoding="utf-8",
    )
    summary: dict[str, Any] = {
        **manifest,
        "outcome": "RUNNING",
        "disclosure": DISCLOSURE,
    }
    init_db(settings.database_url)
    async for session in get_db_session():
        await _recover_interrupted_runs(session, recovered_at=created_at)
        await session.commit()
        running_record = BacktestRunModel(
            id=run_id,
            started_at=created_at,
            completed_at=None,
            status="RUNNING",
            start_date=START,
            end_date=END,
            symbols_json=json.dumps(SYMBOLS),
            artifact_dir=str(output),
            summary_json=json.dumps(summary, default=str),
            is_active_presentation=False,
        )
        session.add(running_record)
        await session.commit()
        try:
            reports, warnings = await _replay_agents(settings, output, session)
        except Exception as exc:
            reports, warnings = [], [f"AI replay unavailable: {type(exc).__name__}"]
            (output / "agent-replay.json").write_text(
                json.dumps({"reports": [], "input_manifests": []}, indent=2), encoding="utf-8"
            )
            _write_historical_artifacts(output, [], [], warnings)
        expected_report_count = _expected_report_count()
        replay_complete = len(reports) == expected_report_count
        simulation_stats: dict[str, int] = {}
        simulation_error: str | None = None
        try:
            simulation_stats = await _persist_simulation(
                session,
                reports,
                run_id=run_id,
                settings=settings,
            )
        except Exception as exc:
            simulation_error = f"Simulation persistence unavailable: {type(exc).__name__}"
            warnings.append(simulation_error)
        try:
            replay_payload = json.loads((output / "agent-replay.json").read_text(encoding="utf-8"))
            manifests = replay_payload.get("input_manifests", [])
            manifests = manifests if isinstance(manifests, list) else []
        except (OSError, ValueError):
            manifests = []
        _write_historical_artifacts(output, manifests, reports, warnings)
        provider_configured = bool(
            getattr(settings, "historical_options_url", None)
            or getattr(settings, "historical_options_provider", None)
        )
        simulation_complete = (
            replay_complete
            and provider_configured
            and simulation_error is None
            and simulation_stats.get("incomplete", 0) == 0
        )
        summary.update(
            {
                "outcome": "COMPLETED" if simulation_complete else "DATA_UNAVAILABLE",
                "agent_reports": len(reports),
                "expected_agent_reports": expected_report_count,
                "warnings": warnings,
                "simulation": simulation_stats,
                "reason": (
                    "Historical option replay completed with deterministic ShadowFund valuations."
                    if simulation_complete
                    else (
                        (
                            simulation_error
                            or (
                                "Historical option provider is not configured or required data is "
                                "unavailable; the run remains inactive."
                            )
                        )
                        if replay_complete
                        else (
                            f"Agent replay produced {len(reports)} of {expected_report_count} "
                            "expected point-in-time research reports; the run remains inactive."
                        )
                    )
                ),
            }
        )
        (output / "summary.json").write_text(
            json.dumps(summary, indent=2, default=str), encoding="utf-8"
        )
        if reports:
            post_analysis = await ShadowFundService().persist_post_analysis_batch(
                session,
                source_mode="staging",
                window_start=datetime.fromisoformat(f"{START}T00:00:00+00:00"),
                window_end=datetime.fromisoformat(f"{END}T20:00:00+00:00"),
                model_metadata={
                    "trigger": "completed_historical_backtest",
                    "mode": "historical_options_simulation",
                    "worker": "staging-backtest-v1",
                },
                summary={
                    "outcome": "NO_RECOMMENDATION",
                    "reason": (
                        "Automated profile recommendations require completed eligible "
                        "ShadowFund valuation evidence."
                    ),
                    "backtest_run_id": run_id,
                },
                recommendations=[],
            )
            # The persisted operator preference is the sole automatic-calibration control.
            # A no-recommendation batch cannot activate a profile.
            await ProfileGovernanceService().apply_automatic_if_enabled(
                session,
                batch_id=post_analysis.id,
                operator_id=settings.auth_email,
            )
            summary["post_analysis_batch_id"] = post_analysis.id
            summary["post_analysis_state"] = post_analysis.state
            from sqlalchemy import update

            if simulation_complete:
                await session.execute(update(BacktestRunModel).values(is_active_presentation=False))
        running_record.completed_at = datetime.now(UTC)
        running_record.status = summary["outcome"]
        running_record.summary_json = json.dumps(summary, default=str)
        running_record.is_active_presentation = simulation_complete
        session.add(
            BacktestAuditEventModel(
                id=str(uuid4()),
                run_id=run_id,
                created_at=datetime.now(UTC),
                event_type=(
                    "SIMULATION_COMPLETED_RESEARCH_REPLAY"
                    if reports
                    else "SIMULATION_DATA_UNAVAILABLE"
                ),
                payload_digest=_digest(summary),
                payload_json=json.dumps(summary, default=str),
            )
        )
        await session.commit()
        (output / "summary.json").write_text(
            json.dumps(summary, indent=2, default=str), encoding="utf-8"
        )
    await close_database()
    print(
        json.dumps({"run_id": run_id, "artifact_dir": str(output), "outcome": summary["outcome"]})
    )
    return 0


def _safe_warning(checkpoint: datetime, symbol: str, exc: Exception) -> str:
    detail = " ".join(str(exc).split())[:180]
    suffix = f": {detail}" if detail else ""
    return f"{checkpoint.date()} {symbol}: {type(exc).__name__}{suffix}"


def _fallback_no_trade_report(
    *,
    checkpoint: datetime,
    symbol: str,
    trace_id: object,
    inputs: dict[str, Any],
    exc: Exception,
) -> dict[str, Any]:
    """Return a deterministic report when one symbol's replay cannot finish.

    A strict specialist failure must not erase the symbol/checkpoint from the
    four-session schedule.  Recording an explicit data-unavailable ``NO_TRADE``
    keeps report counts complete while preserving the fail-closed outcome.
    """

    reason = f"DATA_UNAVAILABLE: {type(exc).__name__}"
    payload = {
        "trace_id": str(trace_id),
        "checkpoint": checkpoint.isoformat(),
        "symbol": symbol,
        "reason": reason,
        "input_digest": _digest(inputs),
    }
    return {
        "trace_id": trace_id,
        "checkpoint": checkpoint,
        "symbol": symbol,
        "digest": _digest(payload),
        "decision": {"symbol": symbol, "verdict": "no_trade", "direction": None},
        "reason": reason,
        "input_digest": _digest(inputs),
        "option_contracts": [],
        "option_quotes": [],
        "option_contracts_raw": [],
        "option_quotes_raw": [],
        "candidate_strategies": {},
        "virtual_authorization": {},
    }


def _write_historical_artifacts(
    output: Path,
    input_manifests: list[dict[str, Any]],
    reports: list[dict[str, Any]],
    warnings: list[str],
) -> None:
    """Persist provider-shaped and normalized point-in-time replay inputs."""
    raw_dir = output / "raw"
    normalized_dir = output / "normalized"
    options_raw_dir = raw_dir / "options"
    options_normalized_dir = normalized_dir / "options"
    raw_dir.mkdir(exist_ok=True)
    normalized_dir.mkdir(exist_ok=True)
    options_raw_dir.mkdir(exist_ok=True)
    options_normalized_dir.mkdir(exist_ok=True)

    for manifest in input_manifests:
        checkpoint = str(manifest["checkpoint"])
        slug = checkpoint.replace("+00:00", "Z").replace(":", "").replace("-", "")
        inputs = manifest["inputs"]
        (raw_dir / f"checkpoint_{slug}_inputs.json").write_text(
            json.dumps(inputs, indent=2, default=str), encoding="utf-8"
        )
        for data_type in ("bars", "news"):
            for symbol, rows in sorted(inputs.get(data_type, {}).items()):
                normalized_path = normalized_dir / f"checkpoint_{slug}_{symbol}_{data_type}.csv"
                rows = rows if isinstance(rows, list) else []
                fields = sorted({key for row in rows if isinstance(row, dict) for key in row})
                with normalized_path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader()
                    for row in rows:
                        writer.writerow({key: row.get(key) for key in fields})
        for symbol, financials in sorted(inputs.get("fundamentals", {}).items()):
            (normalized_dir / f"checkpoint_{slug}_{symbol}_fundamentals.json").write_text(
                json.dumps(financials, indent=2, default=str), encoding="utf-8"
            )

    for report in reports:
        checkpoint = str(report.get("checkpoint", "unknown"))
        slug = checkpoint.replace("+00:00", "Z").replace(":", "").replace("-", "")
        symbol = str(report.get("symbol", "unknown"))
        options_raw = {
            "contracts": report.get("option_contracts_raw", report.get("option_contracts", [])),
            "quotes": report.get("option_quotes_raw", report.get("option_quotes", [])),
        }
        (options_raw_dir / f"checkpoint_{slug}_{symbol}.json").write_text(
            json.dumps(options_raw, indent=2, default=str), encoding="utf-8"
        )
        quote_rows = report.get("option_quotes", [])
        if isinstance(quote_rows, list):
            fields = sorted({key for row in quote_rows if isinstance(row, dict) for key in row})
            with (options_normalized_dir / f"checkpoint_{slug}_{symbol}_quotes.csv").open(
                "w", newline="", encoding="utf-8"
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for row in quote_rows:
                    if isinstance(row, dict):
                        writer.writerow({key: row.get(key) for key in fields})
        contract_rows = report.get("option_contracts", [])
        if isinstance(contract_rows, list):
            fields = sorted({key for row in contract_rows if isinstance(row, dict) for key in row})
            with (options_normalized_dir / f"checkpoint_{slug}_{symbol}_contracts.csv").open(
                "w", newline="", encoding="utf-8"
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for row in contract_rows:
                    if isinstance(row, dict):
                        writer.writerow({key: row.get(key) for key in fields})

    fingerprint_payload = [
        {"checkpoint": item["checkpoint"], "input_digest": item["input_digest"]}
        for item in input_manifests
    ]
    (output / "data_fingerprint.json").write_text(
        json.dumps(
            {
                "algorithm": "sha256",
                "digest": _digest(fingerprint_payload),
                "source": "alpaca_market_data_sec_companyfacts_and_historical_options_provider",
                "checkpoints": fingerprint_payload,
                "options": [
                    {
                        "checkpoint": report.get("checkpoint"),
                        "symbol": report.get("symbol"),
                        "digest": _digest(
                            {
                                "contracts": report.get("option_contracts", []),
                                "quotes": report.get("option_quotes", []),
                                "raw_contracts": report.get("option_contracts_raw", []),
                                "raw_quotes": report.get("option_quotes_raw", []),
                            }
                        ),
                    }
                    for report in reports
                ],
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    (output / "warnings.json").write_text(json.dumps(warnings, indent=2), encoding="utf-8")
    portfolio_results = [
        {
            "checkpoint": report.get("checkpoint"),
            "symbol": report.get("symbol", "unknown"),
            "decision_digest": report.get("digest"),
            "terminal_outcome": (
                "APPROVE"
                if (report.get("virtual_authorization") or {}).get("outcome") == "APPROVE"
                else "NO_TRADE"
            ),
            "virtual_position": (
                "filled"
                if (report.get("simulated_fill") or {}).get("status") == "filled"
                else "cash_only"
            ),
            "active_portfolio_impact": "none",
            "reason": report.get("reason"),
            "simulated_fill": report.get("simulated_fill"),
            "valuations": report.get("valuations", []),
        }
        for report in reports
    ]
    aggregate: dict[str, Decimal] = {}
    for report in reports:
        for valuation in report.get("valuations", []) or []:
            if not isinstance(valuation, dict):
                continue
            observed_at = str(valuation.get("observed_at", ""))
            try:
                pnl = Decimal(str(valuation.get("net_pnl", "0")))
            except Exception:
                continue
            aggregate[observed_at] = aggregate.get(observed_at, Decimal("0")) + pnl
    (output / "portfolio-results.json").write_text(
        json.dumps(
            {
                "mode": "shadowfund_counterfactual",
                "execution": "disabled",
                "results": portfolio_results,
                "aggregate_path": [
                    {"observed_at": at, "net_pnl": str(value)}
                    for at, value in sorted(aggregate.items())
                ],
                "starting_capital": "100000.00",
                "cost_model": "observed_nbbo_touch",
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    (output / "decision-proposals.json").write_text(
        json.dumps(
            [
                {
                    "checkpoint": report.get("checkpoint"),
                    "symbol": report.get("symbol"),
                    "decision_digest": report.get("digest"),
                    "proposal": report.get("proposal"),
                    "virtual_authorization": report.get("virtual_authorization"),
                }
                for report in reports
            ],
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    (output / "virtual-rule-traces.json").write_text(
        json.dumps(
            [
                {
                    "checkpoint": report.get("checkpoint"),
                    "symbol": report.get("symbol"),
                    "trace": (report.get("virtual_authorization") or {}).get("rule_trace", []),
                }
                for report in reports
            ],
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    (output / "simulation-ledger.json").write_text(
        json.dumps(
            {
                "starting_capital": "100000.00",
                "cost_model": "observed_nbbo_touch",
                "events": [
                    {
                        "checkpoint": report.get("checkpoint"),
                        "symbol": report.get("symbol"),
                        "fill": report.get("simulated_fill"),
                    }
                    for report in reports
                    if report.get("simulated_fill")
                ],
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


async def _persist_simulation(
    session: AsyncSession,
    reports: list[dict[str, Any]],
    *,
    run_id: str,
    settings: Any,
) -> dict[str, int]:
    """Persist virtual branches, observations, and valuations for one run."""

    service = ShadowFundService()
    simulator = DeterministicOptionSimulator(
        max_quote_age_seconds=30,
    )
    stats = {"sessions": 0, "filled": 0, "valuations": 0, "incomplete": 0}
    thesis_invalidations: dict[str, datetime] = {}
    reports_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for candidate in reports:
        symbol = str(candidate.get("symbol", ""))
        if symbol and isinstance(candidate.get("checkpoint"), datetime):
            reports_by_symbol.setdefault(symbol, []).append(candidate)
    for symbol_reports in reports_by_symbol.values():
        symbol_reports.sort(key=lambda item: item["checkpoint"])
        for current, following in pairwise(symbol_reports):
            if (current.get("virtual_authorization") or {}).get("outcome") != "APPROVE":
                continue
            current_direction = (current.get("decision") or {}).get("direction")
            following_decision = following.get("decision") or {}
            if following_decision.get("verdict") == "no_trade" or (
                current_direction
                and following_decision.get("direction")
                and following_decision.get("direction") != current_direction
            ):
                thesis_invalidations[str(current.get("trace_id"))] = following["checkpoint"]
    for report in reports:
        checkpoint = report.get("checkpoint")
        if not isinstance(checkpoint, datetime):
            continue
        proposal_payload = report.get("proposal")
        virtual_auth = report.get("virtual_authorization") or {}
        approved = virtual_auth.get("outcome") == "APPROVE"
        proposal = (
            TradeProposal.model_validate(proposal_payload)
            if approved and proposal_payload
            else None
        )
        candidate_strategies = {
            key: OptionStrategy.model_validate(value)
            for key, value in (report.get("candidate_strategies") or {}).items()
            if isinstance(value, dict)
        }
        outcome = "APPROVE" if proposal is not None else "NO_TRADE"
        reason = report.get("reason")
        if not approved and virtual_auth.get("reason_codes"):
            reason = "VIRTUAL_AUTHORIZATION_REJECTED: " + ",".join(
                str(code) for code in virtual_auth["reason_codes"]
            )
        root = build_evaluation_root(
            trace_id=report["trace_id"],
            outcome=outcome,
            evidence={
                "backtest_report_digest": report.get("digest"),
                "virtual_authorization": virtual_auth,
                "reason": reason,
            },
        )
        shadow_session = await service.create_terminal_session(
            session,
            root=root,
            terminal_outcome=outcome,
            proposal=proposal,
            authorization=None,
            source_mode="staging",
            source_feed=str(getattr(settings, "historical_options_feed", "OPRA")),
            candidate_strategies=candidate_strategies,
            chosen_strategy=proposal.strategy if proposal is not None else None,
            backtest_run_id=run_id,
            refusal_reason=reason,
            horizon_at=REPLAY_WINDOW.force_flatten_at,
            created_at=checkpoint,
        )
        ruleset = get_authorized_ruleset()
        shadow_session.ruleset_version = ruleset.version
        shadow_session.profile_version = 1
        stats["sessions"] += 1
        quote_rows = []
        for payload in report.get("option_quotes", []):
            if isinstance(payload, dict):
                try:
                    quote_rows.append(
                        normalize_quote(
                            payload,
                            feed=str(getattr(settings, "historical_options_feed", "OPRA")),
                        )
                    )
                except HistoricalOptionsUnavailable:
                    continue
        branches = list(
            (
                await session.scalars(
                    select(ShadowBranchModel).where(
                        ShadowBranchModel.session_id == shadow_session.id
                    )
                )
            ).all()
        )
        results: dict[str, Any] = {}
        inferred_thesis_invalidation = thesis_invalidations.get(str(report.get("trace_id")))
        if inferred_thesis_invalidation is not None:
            report["thesis_invalidated_at"] = inferred_thesis_invalidation.isoformat()
        for branch in branches:
            if branch.strategy_json is None:
                for observed_at in REPLAY_WINDOW.grid(
                    start_date=checkpoint.astimezone(EASTERN).date()
                ):
                    await service.record_valuation(
                        session,
                        branch_id=branch.id,
                        observed_at=observed_at,
                        gross_pnl=Decimal("0"),
                        net_pnl=Decimal("0"),
                        drawdown=Decimal("0"),
                        mae=Decimal("0"),
                        mfe=Decimal("0"),
                        capital_at_risk=Decimal("0"),
                        coverage_pct=Decimal("100"),
                        confidence="high",
                    )
                    stats["valuations"] += 1
                continue
            strategy = OptionStrategy.model_validate_json(branch.strategy_json)
            result = simulator.replay(
                strategy,
                quote_rows,
                window=REPLAY_WINDOW,
                allocation_multiplier=Decimal(str(branch.allocation_multiplier)),
                quantity=1,
                entry_allowed=approved,
                start_date=checkpoint.astimezone(EASTERN).date(),
                exit_policy_json=shadow_session.exit_policy_json,
                thesis_invalidated_at=(
                    thesis_invalidations.get(str(report.get("trace_id")))
                    or (
                        datetime.fromisoformat(str(report["thesis_invalidated_at"]))
                        if report.get("thesis_invalidated_at")
                        else None
                    )
                ),
            )
            results[branch.id] = result
            fill = result.fill.as_dict()
            if branch.chosen_path:
                report["simulated_fill"] = fill
                report["valuations"] = [
                    {
                        "observed_at": item.observed_at.isoformat(),
                        "mark": str(item.mark),
                        "gross_pnl": str(item.gross_pnl),
                        "net_pnl": str(item.net_pnl),
                        "drawdown": str(item.drawdown),
                        "mae": str(item.mae),
                        "mfe": str(item.mfe),
                        "capital_at_risk": str(item.capital_at_risk),
                        "coverage_pct": str(item.coverage_pct),
                        "confidence": item.confidence,
                        "exit_reason": item.exit_reason,
                    }
                    for item in result.valuations
                ]
            if fill["status"] == "filled":
                stats["filled"] += 1
            if result.fill.entry_price is not None:
                branch.entry_cost = result.fill.entry_price
                branch.entry_at = result.fill.entry_at
            branch.state = result.state
            branch.reason = result.fill.exit_reason or result.reason
            for valuation in result.valuations:
                await service.record_valuation(
                    session,
                    branch_id=branch.id,
                    observed_at=valuation.observed_at,
                    gross_pnl=valuation.gross_pnl,
                    net_pnl=valuation.net_pnl,
                    drawdown=valuation.drawdown,
                    mae=valuation.mae,
                    mfe=valuation.mfe,
                    capital_at_risk=valuation.capital_at_risk,
                    coverage_pct=valuation.coverage_pct,
                    confidence=valuation.confidence,
                    exit_reason=valuation.exit_reason,
                )
                stats["valuations"] += 1
        # Persist every five-minute snapshot, including an explicit fill map,
        # so the presentation adapter can show the hypothetical fill details.
        replay_start_date = checkpoint.astimezone(EASTERN).date()
        for observed_at in REPLAY_WINDOW.grid(start_date=replay_start_date):
            mapped = quote_map_at(
                quote_rows,
                observed_at=observed_at,
                max_age_seconds=simulator.max_quote_age_seconds,
            )
            if not mapped and not results:
                continue
            await service.record_observation(
                session,
                shadow_session_id=shadow_session.id,
                observed_at=observed_at,
                source="historical_options_provider",
                feed=str(getattr(settings, "historical_options_feed", "OPRA")),
                payload={
                    "observed_at": observed_at.isoformat(),
                    "quotes": mapped,
                    "fills": {
                        branch_id: result.fill.as_dict() for branch_id, result in results.items()
                    },
                },
            )
        has_open = any(branch.state == "open" for branch in branches)
        has_incomplete = any(branch.state == "incomplete" for branch in branches)
        if has_open or has_incomplete:
            shadow_session.state = "incomplete"
            stats["incomplete"] += 1
        else:
            shadow_session.state = "complete"
            shadow_session.completed_at = max(
                (
                    valuation.observed_at
                    for result in results.values()
                    for valuation in result.valuations
                ),
                default=checkpoint,
            )
        session.add(shadow_session)
    return stats


async def _replay_agents(
    settings: Any, output: Path, db_session: AsyncSession | None = None
) -> tuple[list[dict[str, Any]], list[str]]:
    """Run Agents 1-7 over point-in-time historical evidence; never execute."""

    reports: list[dict[str, Any]] = []
    warnings: list[str] = []
    input_manifests: list[dict[str, Any]] = []
    gateway = AlpacaPyGateway(settings)
    provider = _options_provider(settings)
    contract_cache: dict[tuple[str, date], list[dict[str, Any]]] = {}
    contract_raw_cache: dict[tuple[str, date], list[dict[str, Any]]] = {}
    quote_cache: dict[str, list[dict[str, Any]]] = {}
    quote_raw_cache: dict[str, list[dict[str, Any]]] = {}
    for session_date in REPLAY_WINDOW.sessions():
        checkpoint = (
            datetime.combine(session_date, datetime.min.time(), tzinfo=EASTERN)
            .replace(hour=9, minute=30)
            .astimezone(UTC)
        )
        historical = HistoricalResearchGateway(
            gateway,
            checkpoint=checkpoint,
            require_checkpoint_data=True,
        )
        for symbol in SYMBOLS:
            trace_id = uuid4()
            try:
                # Persist market/news evidence independently so a single
                # unavailable SEC or LLM dependency cannot erase inputs.
                try:
                    await asyncio.to_thread(
                        historical.get_stock_bars, symbol, limit=HISTORICAL_BAR_LIMIT
                    )
                except Exception as exc:
                    warnings.append(_safe_warning(checkpoint, symbol, exc))
                try:
                    await asyncio.to_thread(historical.get_news, symbol, limit=5)
                except Exception as exc:
                    warnings.append(_safe_warning(checkpoint, symbol, exc))
                financials = await asyncio.to_thread(
                    fetch_sec_company_financials,
                    symbol,
                    user_agent=settings.sec_user_agent,
                    as_of=checkpoint,
                )
                historical.inputs["fundamentals"][symbol] = financials.model_dump(mode="json")
                decision = await TradingDecisionAgent(
                    LLMGateway(settings),
                    historical,  # type: ignore[arg-type]
                ).synthesize_decision(
                    symbol,
                    trace_id,
                    db_session=db_session,
                    allow_illustrative=False,
                    financials=financials,
                    as_of=checkpoint,
                    provenance="historical_simulation",
                )
                report: dict[str, Any] = {
                    "trace_id": trace_id,
                    "checkpoint": checkpoint,
                    "symbol": symbol,
                    "digest": _digest(decision.model_dump(mode="json")),
                    "decision": decision.model_dump(mode="json"),
                    "reason": "NO_TRADE: decision did not produce an eligible option proposal",
                    "input_digest": _digest(historical.inputs),
                }
                selection = _selection_inputs(decision)
                if provider is None:
                    report["reason"] = (
                        "DATA_UNAVAILABLE: historical NBBO provider is not configured"
                    )
                elif selection is not None and decision.verdict.value in {
                    "propose_trade",
                    "proceed_to_options_proposal",
                }:
                    try:
                        contract_key = (symbol, checkpoint.date())
                        if contract_key not in contract_cache:
                            contracts = await asyncio.to_thread(
                                provider.list_contracts,
                                symbol,
                                start=datetime.combine(
                                    REPLAY_WINDOW.start, datetime.min.time(), tzinfo=EASTERN
                                ),
                                end=REPLAY_WINDOW.force_flatten_at,
                                as_of=checkpoint,
                            )
                            contracts = [
                                item
                                for item in contracts
                                if item.available_at is None
                                or item.available_at <= checkpoint.astimezone(UTC)
                            ]
                            if not contracts:
                                raise HistoricalOptionsUnavailable(
                                    "No historical option contracts available at checkpoint"
                                )
                            contract_cache[contract_key] = [item.as_dict() for item in contracts]
                            raw_contracts = getattr(provider, "last_raw_contract_rows", None)
                            contract_raw_cache[contract_key] = (
                                list(raw_contracts)
                                if isinstance(raw_contracts, list)
                                else list(contract_cache[contract_key])
                            )
                        contract_rows = contract_cache[contract_key]
                        option_symbols = [str(item["symbol"]) for item in contract_rows]
                        cached_symbols = {
                            str(item.get("symbol"))
                            for item in quote_cache.get(symbol, [])
                            if isinstance(item, dict)
                        }
                        missing_symbols = [
                            item for item in option_symbols if item not in cached_symbols
                        ]
                        if missing_symbols:
                            quotes = await asyncio.to_thread(
                                provider.get_quotes,
                                missing_symbols,
                                start=datetime.combine(
                                    REPLAY_WINDOW.start, datetime.min.time(), tzinfo=EASTERN
                                ),
                                end=REPLAY_WINDOW.force_flatten_at,
                            )
                            quote_cache.setdefault(symbol, []).extend(
                                item.as_dict() for item in quotes
                            )
                            raw_quotes = getattr(provider, "last_raw_quote_rows", None)
                            quote_raw_cache.setdefault(symbol, []).extend(
                                list(raw_quotes)
                                if isinstance(raw_quotes, list)
                                else [item.as_dict() for item in quotes]
                            )
                        quote_rows = quote_cache.get(symbol, [])
                        quote_map = quote_map_at(
                            [normalize_quote(item, feed=provider.feed) for item in quote_rows],
                            observed_at=checkpoint,
                            max_age_seconds=30,
                        )
                        direction, structure = selection
                        strategy = select_option_strategy(
                            contract_rows,
                            quote_map,
                            underlying_price=decision.current_price,
                            direction=direction,  # type: ignore[arg-type]
                            structure=structure,  # type: ignore[arg-type]
                            now=checkpoint,
                            exit_dte_threshold=decision.exit_policy.dte_threshold,
                            force_flatten_at=REPLAY_WINDOW.force_flatten_at,
                            pricing="entry_touch",
                        )
                        proposal = _proposal_from_decision(decision, strategy)
                        candidate_payload: dict[str, Any] = {}
                        opposite_direction = "bearish" if direction == "bullish" else "bullish"
                        opposite_structure = (
                            "debit_spread" if structure == "debit_spread" else "long"
                        )
                        with suppress(OptionSelectionError):
                            candidate_payload["contrarian"] = select_option_strategy(
                                contract_rows,
                                quote_map,
                                underlying_price=decision.current_price,
                                direction=opposite_direction,  # type: ignore[arg-type]
                                structure=opposite_structure,  # type: ignore[arg-type]
                                now=checkpoint,
                                exit_dte_threshold=decision.exit_policy.dte_threshold,
                                force_flatten_at=REPLAY_WINDOW.force_flatten_at,
                                pricing="entry_touch",
                            ).model_dump(mode="json")
                        intent = decision.shadow_alternative_intent
                        if intent is not None:
                            try:
                                ai_structure = (
                                    "long"
                                    if intent.preferred_structure
                                    in {OptionStructure.LONG_CALL, OptionStructure.LONG_PUT}
                                    else "debit_spread"
                                )
                                candidate_payload["ai_alternative"] = select_option_strategy(
                                    contract_rows,
                                    quote_map,
                                    underlying_price=decision.current_price,
                                    direction=intent.direction.value,  # type: ignore[arg-type]
                                    structure=ai_structure,  # type: ignore[arg-type]
                                    now=checkpoint,
                                    exit_dte_threshold=decision.exit_policy.dte_threshold,
                                    force_flatten_at=REPLAY_WINDOW.force_flatten_at,
                                    pricing="entry_touch",
                                ).model_dump(mode="json")
                            except OptionSelectionError:
                                pass
                        risk = await RiskManagementAgent(LLMGateway(settings)).assess(
                            proposal,
                            context={
                                "market_fresh": True,
                                "historical_options_feed": provider.feed,
                                "quote_count": len(quote_rows),
                            },
                        )
                        iv_values = [
                            item.get("iv_rank")
                            for item in quote_map.values()
                            if item.get("iv_rank") is not None
                        ]
                        ruleset = get_authorized_ruleset()
                        rule_params = ruleset.parameters
                        contract_risk = strategy.limit_price * Decimal("100")
                        starting_capital = rule_params.starting_capital_usd
                        spread_values = []
                        quote_ages = []
                        for leg in strategy.legs:
                            leg_quote = quote_map.get(leg.symbol)
                            if leg_quote is None:
                                continue
                            bid = Decimal(str(leg_quote["bid"]))
                            ask = Decimal(str(leg_quote["ask"]))
                            spread_values.append(
                                (ask - bid) / ((ask + bid) / Decimal("2")) * Decimal("100")
                            )
                            quote_timestamp = leg_quote.get("quote_timestamp")
                            if isinstance(quote_timestamp, datetime):
                                quote_ages.append(
                                    Decimal(
                                        str(
                                            max(
                                                0,
                                                (
                                                    checkpoint.astimezone(UTC)
                                                    - quote_timestamp.astimezone(UTC)
                                                ).total_seconds(),
                                            )
                                        )
                                    )
                                )
                        virtual = evaluate_virtual_authorization(
                            proposal,
                            risk,
                            inputs={
                                "paper_only": True,
                                "active_ruleset_version": ruleset.version,
                                "market_fresh": True,
                                "analog_count": decision.analog_count,
                                "fundamentals_sourced": True,
                                "account_verified": True,
                                "open_positions": 0,
                                "buying_power_ok": True,
                                "cash_buffer_ok": starting_capital - contract_risk
                                >= starting_capital * rule_params.cash_buffer_pct / Decimal("100"),
                                "concentration_ok": contract_risk
                                <= starting_capital
                                * rule_params.ticker_concentration_pct
                                / Decimal("100"),
                                "position_size_ok": contract_risk
                                <= starting_capital
                                * rule_params.max_risk_per_trade_pct
                                / Decimal("100"),
                                "aggregate_risk_ok": contract_risk
                                <= starting_capital
                                * rule_params.aggregate_hard_stop_risk_pct
                                / Decimal("100"),
                                "portfolio_controls_complete": True,
                                "sector_concentration_ok": True,
                                "cluster_concentration_ok": True,
                                "expiration_concentration_ok": True,
                                "greeks_risk_ok": True,
                                "portfolio_risk_state": "normal",
                                "supported_options_level": (
                                    3 if len(proposal.strategy.legs) > 1 else 2
                                ),
                                "market_regime": (
                                    "crisis"
                                    if decision.specialist_scores.macro_climate_score <= 25
                                    else "volatile"
                                    if decision.specialist_scores.macro_climate_score <= 50
                                    else "normal"
                                ),
                                "iv_rank_available": bool(iv_values),
                                "iv_rank": iv_values[0] if iv_values else None,
                                "quote_age_seconds": max(quote_ages, default=Decimal("999")),
                                "spread_pct": max(spread_values, default=Decimal("999")),
                                "market_open": True,
                                "within_entry_window": REPLAY_WINDOW.is_entry_allowed(checkpoint),
                                "before_force_flatten": checkpoint < REPLAY_WINDOW.force_flatten_at,
                                "opportunity_score": decision.composite_opportunity_score,
                                "net_ev_r": decision.net_ev_r,
                                "reward_risk_ratio": decision.reward_risk_ratio,
                            },
                        )
                        report.update(
                            {
                                "proposal": proposal.model_dump(mode="json"),
                                "option_contracts": contract_rows,
                                "option_quotes": quote_rows,
                                "option_contracts_raw": contract_raw_cache.get(contract_key, []),
                                "option_quotes_raw": quote_raw_cache.get(symbol, []),
                                "candidate_strategies": candidate_payload,
                                "virtual_authorization": virtual.as_dict(),
                                "reason": None
                                if virtual.approved
                                else "VIRTUAL_AUTHORIZATION_REJECTED",
                            }
                        )
                    except (HistoricalOptionsUnavailable, OptionSelectionError, ValueError) as exc:
                        report["reason"] = f"DATA_UNAVAILABLE: {type(exc).__name__}"
                reports.append(report)
            except (SecFundamentalsUnavailable, ValueError) as exc:
                warnings.append(_safe_warning(checkpoint, symbol, exc))
                reports.append(
                    _fallback_no_trade_report(
                        checkpoint=checkpoint,
                        symbol=symbol,
                        trace_id=trace_id,
                        inputs=historical.inputs,
                        exc=exc,
                    )
                )
            except Exception as exc:
                warnings.append(_safe_warning(checkpoint, symbol, exc))
                reports.append(
                    _fallback_no_trade_report(
                        checkpoint=checkpoint,
                        symbol=symbol,
                        trace_id=trace_id,
                        inputs=historical.inputs,
                        exc=exc,
                    )
                )
        input_manifests.append(
            {
                "checkpoint": checkpoint.isoformat(),
                "input_digest": _digest(historical.inputs),
                "inputs": historical.inputs,
            }
        )
        # Keep artifacts durable after every checkpoint so operators can
        # inspect progress and a later failure does not discard prior data.
        (output / "agent-replay.json").write_text(
            json.dumps(
                {"reports": reports, "input_manifests": input_manifests},
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        _write_historical_artifacts(output, input_manifests, reports, warnings)
    (output / "agent-replay.json").write_text(
        json.dumps(
            {"reports": reports, "input_manifests": input_manifests},
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    _write_historical_artifacts(output, input_manifests, reports, warnings)
    return reports, warnings


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
