"""Run the bounded staging historical simulation without an execution adapter."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.backtest.models import BacktestAuditEventModel, BacktestRunModel
from app.core.config import get_settings
from app.core.database import close_database, get_db_session, init_db

START = "2026-08-24"
END = "2026-08-28"
SYMBOLS = ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "GOOGL", "META"]
DISCLOSURE = (
    "Important disclosure: This backtest is a hypothetical historical simulation and does not "
    "represent actual trading performance. It does not place paper or live orders."
)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


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
    summary = {
        **manifest,
        "outcome": "DATA_UNAVAILABLE",
        "reason": "Historical data acquisition is required before a virtual trade can be recorded.",
        "disclosure": DISCLOSURE,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    init_db(settings.database_url)
    async for session in get_db_session():
        session.add(
            BacktestRunModel(
                id=run_id,
                started_at=created_at,
                completed_at=datetime.now(UTC),
                status="DATA_UNAVAILABLE",
                start_date=START,
                end_date=END,
                symbols_json=json.dumps(SYMBOLS),
                artifact_dir=str(output),
                summary_json=json.dumps(summary),
                # A placeholder/data-refusal result must never replace a
                # previously completed staging presentation dataset.
                is_active_presentation=False,
            )
        )
        session.add(
            BacktestAuditEventModel(
                id=str(uuid4()),
                run_id=run_id,
                created_at=datetime.now(UTC),
                event_type="SIMULATION_DATA_UNAVAILABLE",
                payload_digest=_digest(summary),
                payload_json=json.dumps(summary),
            )
        )
        await session.commit()
    await close_database()
    print(
        json.dumps({"run_id": run_id, "artifact_dir": str(output), "outcome": summary["outcome"]})
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=START)
    parser.add_argument("--end", default=END)
    parser.parse_args()
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
