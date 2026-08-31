from __future__ import annotations

import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.monitor_paper_account import render_report  # noqa: E402


def test_render_report_redacts_account_identifiers_and_formats_decimal_values() -> None:
    account = SimpleNamespace(
        id="should-not-be-visible",
        account_number="should-not-be-visible",
        status="ACTIVE",
        currency="USD",
        portfolio_value="100000.00",
        equity="100250.25",
        last_equity="100000.00",
        cash="95000.00",
        buying_power="400000.00",
        long_market_value="5250.25",
        short_market_value="0",
        pattern_day_trader=False,
        daytrade_count=0,
        multiplier="4",
        shorting_enabled=True,
        trading_blocked=False,
    )
    position = SimpleNamespace(
        symbol="AAPL",
        side="long",
        qty="2",
        market_value="5250.25",
        unrealized_pl="250.25",
        unrealized_plpc=Decimal("0.05"),
    )

    report = render_report(account, [position], checked_at=datetime(2026, 8, 31, tzinfo=UTC))

    assert "should-not-be-visible" not in report
    assert "Account Identifier  : [redacted]" in report
    assert "Account Status      : ACTIVE" in report
    assert "Portfolio Value     : $100,000.00" in report
    assert "Today's P&L         : $250.25 (+0.25%)" in report
    assert "AAPL (long)" in report
    assert "Unrealized P&L   : $250.25 (+5.00%)" in report


def test_render_report_handles_no_positions_and_missing_optional_fields() -> None:
    account = {"status": "ACTIVE", "currency": "USD", "multiplier": None}

    report = render_report(account, [], checked_at=datetime(2026, 8, 31, tzinfo=UTC))

    assert "[i] No open positions currently." in report
    assert "Margin Multiplier   : unavailablex" in report
