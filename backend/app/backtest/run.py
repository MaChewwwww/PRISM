"""Run the bounded staging historical simulation without an execution adapter."""

from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.autonomous.audit import build_evaluation_root
from app.backtest.historical_gateway import HistoricalResearchGateway
from app.backtest.models import BacktestAuditEventModel, BacktestRunModel
from app.core.config import get_settings
from app.core.database import close_database, get_db_session, init_db
from app.core.llm_gateway import LLMGateway
from app.market.alpaca_gateway import AlpacaPyGateway
from app.profiles.service import ProfileGovernanceService
from app.research.decision_agent import TradingDecisionAgent
from app.research.sec_fundamentals import SecFundamentalsUnavailable, fetch_sec_company_financials
from app.shadowfund.service import ShadowFundService

START = "2026-08-24"
END = "2026-08-28"
SYMBOLS = ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "GOOGL", "META"]
DISCLOSURE = (
    "Important disclosure: This backtest is a hypothetical historical simulation and does not "
    "represent actual trading performance. It does not place paper or live orders."
)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, default=str, sort_keys=True).encode()).hexdigest()


def _preflight(cli_path: str) -> str:
    result = subprocess.run(
        [cli_path, "version"], capture_output=True, text=True, timeout=10, check=False
    )
    if result.returncode != 0:
        raise RuntimeError("Alpaca CLI preflight failed")
    return result.stdout.strip().splitlines()[0][:64]


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
        "mode": "historical_live_model",
        "execution": "disabled",
    }
    (output / "config.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output / "notes.md").write_text(
        f"# PRISM staging historical simulation\n\n{DISCLOSURE}\n", encoding="utf-8"
    )
    summary: dict[str, Any] = {
        **manifest,
        "outcome": "RUNNING",
        "disclosure": DISCLOSURE,
    }
    init_db(settings.database_url)
    async for session in get_db_session():
        try:
            reports, warnings = await _replay_agents(settings, output)
        except Exception as exc:
            reports, warnings = [], [f"AI replay unavailable: {type(exc).__name__}"]
        summary.update(
            {
                "outcome": "COMPLETED" if reports else "DATA_UNAVAILABLE",
                "agent_reports": len(reports),
                "warnings": warnings,
                "reason": (
                    "Agent replay completed. Virtual options remain NO_TRADE when historical "
                    "contracts or quotes are unavailable."
                    if reports
                    else "No point-in-time AI research report could be completed."
                ),
            }
        )
        (output / "summary.json").write_text(
            json.dumps(summary, indent=2, default=str), encoding="utf-8"
        )
        if reports:
            for report in reports:
                root = build_evaluation_root(
                    trace_id=report["trace_id"],
                    outcome="NO_TRADE",
                    evidence={
                        "backtest_report_digest": report["digest"],
                        "reason": report["reason"],
                    },
                )
                await ShadowFundService().create_terminal_session(
                    session,
                    root=root,
                    terminal_outcome="NO_TRADE",
                    proposal=None,
                    authorization=None,
                    source_mode="staging",
                    source_feed="historical_configured",
                    backtest_run_id=run_id,
                    refusal_reason=report["reason"],
                    horizon_at=report["checkpoint"],
                )
            post_analysis = await ShadowFundService().persist_post_analysis_batch(
                session,
                source_mode="staging",
                window_start=datetime.fromisoformat(f"{START}T00:00:00+00:00"),
                window_end=datetime.fromisoformat(f"{END}T20:00:00+00:00"),
                model_metadata={
                    "trigger": "completed_historical_backtest",
                    "mode": "historical_live_model",
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

            await session.execute(update(BacktestRunModel).values(is_active_presentation=False))
        session.add(
            BacktestRunModel(
                id=run_id,
                started_at=created_at,
                completed_at=datetime.now(UTC),
                status=summary["outcome"],
                start_date=START,
                end_date=END,
                symbols_json=json.dumps(SYMBOLS),
                artifact_dir=str(output),
                summary_json=json.dumps(summary, default=str),
                is_active_presentation=bool(reports),
            )
        )
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


async def _replay_agents(settings: Any, output: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Run Agents 1-7 over point-in-time historical evidence; never execute."""

    reports: list[dict[str, Any]] = []
    warnings: list[str] = []
    input_manifests: list[dict[str, Any]] = []
    gateway = AlpacaPyGateway(settings)
    checkpoint = datetime.fromisoformat(f"{START}T20:00:00+00:00")
    end = datetime.fromisoformat(f"{END}T20:00:00+00:00")
    while checkpoint <= end:
        if checkpoint.weekday() >= 5:
            checkpoint += timedelta(days=1)
            continue
        historical = HistoricalResearchGateway(gateway, checkpoint=checkpoint)
        for symbol in SYMBOLS:
            trace_id = uuid4()
            try:
                financials = await asyncio.to_thread(
                    fetch_sec_company_financials,
                    symbol,
                    user_agent=settings.sec_user_agent,
                    as_of=checkpoint,
                )
                decision = await TradingDecisionAgent(
                    LLMGateway(settings),
                    historical,  # type: ignore[arg-type]
                ).synthesize_decision(
                    symbol,
                    trace_id,
                    allow_illustrative=True,
                    financials=financials,
                    as_of=checkpoint,
                    provenance="historical_simulation",
                )
                digest = _digest(decision.model_dump(mode="json"))
                reports.append(
                    {
                        "trace_id": trace_id,
                        "checkpoint": checkpoint,
                        "symbol": symbol,
                        "digest": digest,
                        "decision": decision.model_dump(mode="json"),
                        "reason": (
                            "DATA_UNAVAILABLE: historical option contract/quote replay pending"
                        ),
                        "input_digest": _digest(historical.inputs),
                    }
                )
            except (SecFundamentalsUnavailable, ValueError) as exc:
                warnings.append(f"{checkpoint.date()} {symbol}: {type(exc).__name__}")
            except Exception as exc:
                warnings.append(f"{checkpoint.date()} {symbol}: {type(exc).__name__}")
        input_manifests.append(
            {
                "checkpoint": checkpoint.isoformat(),
                "input_digest": _digest(historical.inputs),
                "inputs": historical.inputs,
            }
        )
        checkpoint += timedelta(days=1)
    (output / "agent-replay.json").write_text(
        json.dumps(
            {"reports": reports, "input_manifests": input_manifests},
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    return reports, warnings


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
