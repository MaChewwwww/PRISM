from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.backtest import run as backtest_run
from app.backtest.historical_gateway import HistoricalResearchGateway
from app.backtest.models import BacktestAuditEventModel, BacktestRunModel
from app.research.sec_fundamentals import SEC_CIK_BY_SYMBOL


@pytest.mark.asyncio
async def test_data_unavailable_run_does_not_replace_active_presentation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = SimpleNamespace(
        environment="staging",
        backtest_simulation_enabled=True,
        shadowfund_enabled=True,
        alpaca_paper=True,
        alpaca_live_trade=False,
        alpaca_cli_path="alpaca",
        backtest_output_dir=str(tmp_path),
        database_url="postgresql+asyncpg://unused",
    )

    class Session:
        def __init__(self) -> None:
            self.added: list[object] = []
            self.committed = False

        def add(self, value: object) -> None:
            self.added.append(value)

        async def scalars(self, _statement: object) -> object:
            class Result:
                def all(self) -> list[object]:
                    return []

            return Result()

        async def commit(self) -> None:
            self.committed = True

    session = Session()

    async def sessions() -> AsyncIterator[Session]:
        yield session

    monkeypatch.setattr(backtest_run, "get_settings", lambda: settings)
    monkeypatch.setattr(backtest_run, "_preflight", lambda _path: "alpaca 0.0.13")
    monkeypatch.setattr(backtest_run, "init_db", lambda _url: None)
    monkeypatch.setattr(backtest_run, "close_database", lambda: _no_op())
    monkeypatch.setattr(backtest_run, "get_db_session", sessions)

    assert await backtest_run.run() == 0

    run_model = next(
        value
        for value in session.added
        if isinstance(value, BacktestRunModel) and value.status != "RUNNING"
    )
    audit_model = next(
        value for value in session.added if isinstance(value, BacktestAuditEventModel)
    )
    assert run_model.status == "DATA_UNAVAILABLE"
    assert run_model.is_active_presentation is False
    assert audit_model.event_type == "SIMULATION_DATA_UNAVAILABLE"
    assert session.committed is True


@pytest.mark.asyncio
async def test_recover_interrupted_backtest_runs_fail_closed() -> None:
    recovered_at = datetime(2026, 8, 31, 5, tzinfo=UTC)
    stale = BacktestRunModel(
        id="stale-run",
        started_at=datetime(2026, 8, 31, 3, tzinfo=UTC),
        completed_at=None,
        status="RUNNING",
        start_date="2026-08-24",
        end_date="2026-08-28",
        symbols_json="[]",
        artifact_dir="/tmp/stale-run",
        summary_json=json.dumps({"outcome": "RUNNING"}),
        is_active_presentation=False,
    )

    class Session:
        def __init__(self) -> None:
            self.added: list[object] = []

        async def scalars(self, _statement: object) -> object:
            class Result:
                def all(self) -> list[object]:
                    return [stale]

            return Result()

        def add(self, value: object) -> None:
            self.added.append(value)

    session = Session()
    assert await backtest_run._recover_interrupted_runs(session, recovered_at=recovered_at) == 1
    assert stale.status == "DATA_UNAVAILABLE"
    assert stale.completed_at == recovered_at
    assert stale.is_active_presentation is False
    summary = json.loads(stale.summary_json)
    assert summary["outcome"] == "DATA_UNAVAILABLE"
    assert summary["recovered_at"] == recovered_at.isoformat()
    audit = next(value for value in session.added if isinstance(value, BacktestAuditEventModel))
    assert audit.event_type == "SIMULATION_INTERRUPTED"


@pytest.mark.asyncio
async def test_backtest_requires_explicit_shadowfund_feature_flag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = SimpleNamespace(
        environment="staging",
        backtest_simulation_enabled=True,
        shadowfund_enabled=False,
        alpaca_paper=True,
        alpaca_live_trade=False,
        backtest_output_dir=str(tmp_path),
    )
    monkeypatch.setattr(backtest_run, "get_settings", lambda: settings)

    with pytest.raises(RuntimeError, match="SHADOWFUND_ENABLED=true"):
        await backtest_run.run()


@pytest.mark.asyncio
async def test_completed_backtest_persists_one_no_recommendation_batch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = SimpleNamespace(
        environment="staging",
        backtest_simulation_enabled=True,
        shadowfund_enabled=True,
        alpaca_paper=True,
        alpaca_live_trade=False,
        alpaca_cli_path="alpaca",
        backtest_output_dir=str(tmp_path),
        database_url="postgresql+asyncpg://unused",
        auth_email="operator@prism.local",
    )
    calls: list[str] = []

    class Session:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, value: object) -> None:
            self.added.append(value)

        async def scalars(self, _statement: object) -> object:
            class Result:
                def all(self) -> list[object]:
                    return []

            return Result()

        async def execute(self, _statement: object) -> None:
            return None

        async def commit(self) -> None:
            return None

    async def sessions() -> AsyncIterator[Session]:
        yield Session()

    class ShadowService:
        async def create_terminal_session(self, *_args: object, **_kwargs: object) -> None:
            calls.append("session")

        async def persist_post_analysis_batch(
            self, *_args: object, **_kwargs: object
        ) -> SimpleNamespace:
            calls.append("post_analysis")
            return SimpleNamespace(id="batch-1", state="NO_RECOMMENDATION")

    class ProfileService:
        async def apply_automatic_if_enabled(self, *_args: object, **_kwargs: object) -> None:
            calls.append("automatic")

    monkeypatch.setattr(backtest_run, "get_settings", lambda: settings)
    monkeypatch.setattr(backtest_run, "_preflight", lambda _path: "alpaca 0.0.13")
    monkeypatch.setattr(backtest_run, "init_db", lambda _url: None)
    monkeypatch.setattr(backtest_run, "close_database", lambda: _no_op())
    monkeypatch.setattr(backtest_run, "get_db_session", sessions)
    monkeypatch.setattr(backtest_run, "ShadowFundService", ShadowService)
    monkeypatch.setattr(backtest_run, "ProfileGovernanceService", ProfileService)
    monkeypatch.setattr(backtest_run, "_expected_report_count", lambda: 1)
    monkeypatch.setattr(
        backtest_run,
        "_replay_agents",
        lambda _settings, _output, _session=None: _completed_replay(),
    )

    assert await backtest_run.run() == 0
    summary = next(tmp_path.glob("*/summary.json")).read_text(encoding="utf-8")
    assert '"post_analysis_batch_id": "batch-1"' in summary
    assert '"expected_agent_reports": 1' in summary
    assert calls == ["session", "post_analysis", "automatic"]


def test_expected_report_count_matches_the_fixed_four_session_window() -> None:
    assert backtest_run._expected_report_count() == 28


async def _no_op() -> None:
    return None


async def _completed_replay() -> tuple[list[dict[str, object]], list[str]]:
    return (
        [
            {
                "trace_id": "00000000-0000-0000-0000-000000000001",
                "checkpoint": datetime(2026, 8, 24, 20, tzinfo=UTC),
                "digest": "a" * 64,
                "reason": "DATA_UNAVAILABLE: historical option contract/quote replay pending",
            }
        ],
        [],
    )


def test_historical_research_gateway_enforces_point_in_time_cutoff() -> None:
    checkpoint = datetime(2026, 8, 24, 20, tzinfo=UTC)

    class Gateway:
        def get_stock_bars(self, _symbol: str, **_kwargs: object) -> list[dict[str, object]]:
            return [
                {"timestamp": checkpoint - timedelta(minutes=1), "close": "100"},
                {"timestamp": checkpoint + timedelta(minutes=1), "close": "101"},
            ]

        def get_news(self, _symbol: str, **_kwargs: object) -> list[dict[str, object]]:
            return [
                {"created_at": checkpoint - timedelta(minutes=1), "headline": "known"},
                {"created_at": checkpoint + timedelta(minutes=1), "headline": "future"},
            ]

    historical = HistoricalResearchGateway(Gateway(), checkpoint=checkpoint)  # type: ignore[arg-type]
    assert len(historical.get_stock_bars("NVDA")) == 1
    assert len(historical.get_news("NVDA")) == 1


def test_historical_research_gateway_caches_normalized_provider_reads() -> None:
    checkpoint = datetime(2026, 8, 24, 20, tzinfo=UTC)
    calls = {"bars": 0, "news": 0}

    class Gateway:
        def get_stock_bars(self, _symbol: str, **_kwargs: object) -> list[dict[str, object]]:
            calls["bars"] += 1
            return [{"timestamp": checkpoint - timedelta(minutes=1), "close": "100"}]

        def get_news(self, _symbol: str, **_kwargs: object) -> list[dict[str, object]]:
            calls["news"] += 1
            return [{"created_at": checkpoint - timedelta(minutes=1), "headline": "known"}]

    historical = HistoricalResearchGateway(Gateway(), checkpoint=checkpoint)  # type: ignore[arg-type]
    historical.get_stock_bars("nvda", limit=1)
    historical.get_stock_bars("NVDA", limit=1)
    historical.get_news("nvda", limit=1)
    historical.get_news("NVDA", limit=1)
    assert calls == {"bars": 1, "news": 1}


def test_historical_research_gateway_rejects_stale_checkpoint_window() -> None:
    checkpoint = datetime(2026, 8, 24, 20, tzinfo=UTC)

    class Gateway:
        def get_stock_bars(self, _symbol: str, **_kwargs: object) -> list[dict[str, object]]:
            return [{"timestamp": checkpoint - timedelta(days=1), "close": "100"}]

    historical = HistoricalResearchGateway(
        Gateway(),
        checkpoint=checkpoint,
        require_checkpoint_data=True,  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="do not reach checkpoint"):
        historical.get_stock_bars("NVDA", limit=1)
    assert historical.inputs["bars"]["NVDA"]


def test_historical_research_gateway_fetches_latest_rows_for_strict_replay() -> None:
    checkpoint = datetime(2026, 8, 24, 20, tzinfo=UTC)
    calls: list[dict[str, object]] = []
    all_rows = [
        {"timestamp": checkpoint - timedelta(days=offset), "close": str(offset)}
        for offset in range(40, -1, -1)
    ]

    class Gateway:
        def get_stock_bars(self, _symbol: str, **kwargs: object) -> list[dict[str, object]]:
            calls.append(kwargs)
            limit = int(kwargs["limit"])
            return all_rows[:limit]

    historical = HistoricalResearchGateway(
        Gateway(),
        checkpoint=checkpoint,
        require_checkpoint_data=True,  # type: ignore[arg-type]
    )
    latest_rows = historical.get_stock_bars("SPY", limit=3)

    assert calls[0]["limit"] >= 1000
    assert len(latest_rows) == 3
    assert latest_rows[-1]["timestamp"] == checkpoint
    assert len(historical.inputs["bars"]["SPY"]) == len(all_rows)


def test_historical_artifacts_include_fingerprint_and_portfolio_projection(tmp_path: Path) -> None:
    checkpoint = "2026-08-24T20:00:00+00:00"
    manifests = [
        {
            "checkpoint": checkpoint,
            "input_digest": "a" * 64,
            "inputs": {
                "bars": {"NVDA": [{"timestamp": checkpoint, "close": "100"}]},
                "news": {"NVDA": []},
                "fundamentals": {"NVDA": {"provenance": "sec_filing"}},
            },
        }
    ]
    reports = [
        {
            "checkpoint": checkpoint,
            "symbol": "NVDA",
            "digest": "b" * 64,
            "reason": "DATA_UNAVAILABLE: historical option contract/quote replay pending",
        }
    ]
    backtest_run._write_historical_artifacts(tmp_path, manifests, reports, [])
    assert (tmp_path / "raw" / "checkpoint_20260824T200000Z_inputs.json").exists()
    assert (tmp_path / "normalized" / "checkpoint_20260824T200000Z_NVDA_bars.csv").exists()
    assert (tmp_path / "normalized" / "checkpoint_20260824T200000Z_NVDA_fundamentals.json").exists()
    fingerprint = json.loads((tmp_path / "data_fingerprint.json").read_text(encoding="utf-8"))
    portfolio = json.loads((tmp_path / "portfolio-results.json").read_text(encoding="utf-8"))
    assert fingerprint["algorithm"] == "sha256"
    assert portfolio["results"][0]["terminal_outcome"] == "NO_TRADE"


def test_backtest_core_universe_has_a_sec_companyfacts_mapping() -> None:
    assert all(symbol in SEC_CIK_BY_SYMBOL for symbol in backtest_run.SYMBOLS)


def test_backtest_bar_limit_covers_the_full_historical_lookback() -> None:
    # HistoricalResearchGateway asks Alpaca for 730 calendar days.  The API
    # returns ascending rows, so the replay limit must not truncate that
    # window before its checkpoint.
    assert backtest_run.HISTORICAL_BAR_LIMIT >= 730


def test_backtest_digest_handles_timestamped_provider_inputs() -> None:
    assert backtest_run._digest({"observed_at": datetime(2026, 8, 24, 20, tzinfo=UTC)})
