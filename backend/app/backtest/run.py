"""Run the bounded staging historical simulation without an execution adapter."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

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
# Alpaca returns stock bars in ascending order.  The replay gateway requests a
# 730-day lookback, so a 250-row limit only returns the oldest part of that
# range and can stop well before the historical checkpoint.  Keep enough
# headroom for the full daily-bar window plus non-trading days.
HISTORICAL_BAR_LIMIT = 1000
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
        f"# PRISM staging historical simulation\n\n{DISCLOSURE}\n\n{PAPER_DISCLOSURE}\n\n"
        "Execution is disabled; this run uses a cash-only ShadowFund counterfactual.\n",
        encoding="utf-8",
    )
    summary: dict[str, Any] = {
        **manifest,
        "outcome": "RUNNING",
        "disclosure": DISCLOSURE,
    }
    init_db(settings.database_url)
    async for session in get_db_session():
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
                    created_at=report["checkpoint"],
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
        running_record.completed_at = datetime.now(UTC)
        running_record.status = summary["outcome"]
        running_record.summary_json = json.dumps(summary, default=str)
        running_record.is_active_presentation = bool(reports)
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


def _write_historical_artifacts(
    output: Path,
    input_manifests: list[dict[str, Any]],
    reports: list[dict[str, Any]],
    warnings: list[str],
) -> None:
    """Persist provider-shaped and normalized point-in-time replay inputs."""
    raw_dir = output / "raw"
    normalized_dir = output / "normalized"
    raw_dir.mkdir(exist_ok=True)
    normalized_dir.mkdir(exist_ok=True)

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

    fingerprint_payload = [
        {"checkpoint": item["checkpoint"], "input_digest": item["input_digest"]}
        for item in input_manifests
    ]
    (output / "data_fingerprint.json").write_text(
        json.dumps(
            {
                "algorithm": "sha256",
                "digest": _digest(fingerprint_payload),
                "source": "alpaca_market_data_and_sec_companyfacts",
                "checkpoints": fingerprint_payload,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (output / "warnings.json").write_text(json.dumps(warnings, indent=2), encoding="utf-8")
    portfolio_results = [
        {
            "checkpoint": report["checkpoint"],
            "symbol": report["symbol"],
            "decision_digest": report["digest"],
            "terminal_outcome": "NO_TRADE",
            "virtual_position": "cash_only",
            "active_portfolio_impact": "none",
            "reason": report["reason"],
        }
        for report in reports
    ]
    (output / "portfolio-results.json").write_text(
        json.dumps(
            {
                "mode": "shadowfund_counterfactual",
                "execution": "disabled",
                "results": portfolio_results,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


async def _replay_agents(
    settings: Any, output: Path, db_session: AsyncSession | None = None
) -> tuple[list[dict[str, Any]], list[str]]:
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
                warnings.append(_safe_warning(checkpoint, symbol, exc))
            except Exception as exc:
                warnings.append(_safe_warning(checkpoint, symbol, exc))
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
        checkpoint += timedelta(days=1)
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
