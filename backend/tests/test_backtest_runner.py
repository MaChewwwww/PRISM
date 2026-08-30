from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.backtest import run as backtest_run
from app.backtest.historical_gateway import HistoricalResearchGateway
from app.backtest.models import BacktestAuditEventModel, BacktestRunModel


@pytest.mark.asyncio
async def test_data_unavailable_run_does_not_replace_active_presentation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = SimpleNamespace(
        environment="staging",
        backtest_simulation_enabled=True,
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

    run_model = next(value for value in session.added if isinstance(value, BacktestRunModel))
    audit_model = next(
        value for value in session.added if isinstance(value, BacktestAuditEventModel)
    )
    assert run_model.status == "DATA_UNAVAILABLE"
    assert run_model.is_active_presentation is False
    assert audit_model.event_type == "SIMULATION_DATA_UNAVAILABLE"
    assert session.committed is True


async def _no_op() -> None:
    return None


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
