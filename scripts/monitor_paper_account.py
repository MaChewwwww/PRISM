#!/usr/bin/env python3
"""Print a read-only, redacted PRISM Alpaca paper-account snapshot.

This operator utility deliberately uses only the typed account and position
reads exposed by ``AlpacaPyGateway``.  It does not import an execution adapter,
submit orders, or change PRISM configuration or autonomous-worker state.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import Settings  # type: ignore[import-untyped]
from app.market.alpaca_gateway import AlpacaPyGateway  # type: ignore[import-untyped]
from dotenv import dotenv_values


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return decimal_value if decimal_value.is_finite() else None


def _text(value: Any) -> str:
    if value is None:
        return "unavailable"
    enum_value = getattr(value, "value", None)
    return str(enum_value if enum_value is not None else value)


def _money(value: Any) -> str:
    decimal_value = _decimal(value)
    return "unavailable" if decimal_value is None else f"${decimal_value:,.2f}"


def _number(value: Any) -> str:
    decimal_value = _decimal(value)
    return (
        "unavailable"
        if decimal_value is None
        else f"{decimal_value:,f}".rstrip("0").rstrip(".")
    )


def _percentage(value: Any) -> str:
    decimal_value = _decimal(value)
    return (
        "unavailable"
        if decimal_value is None
        else f"{decimal_value * Decimal(100):+.2f}%"
    )


def _yes_no(value: Any) -> str:
    return "Yes" if bool(value) else "No"


def load_production_settings(env_file: Path) -> Settings:
    """Load settings from the explicitly selected local environment file.

    Passing parsed values as constructor arguments gives the selected file
    precedence over any unrelated shell environment variables.  ``Settings``
    then enforces PRISM's paper-only validation before a provider client exists.
    """

    if not env_file.is_file():
        raise ValueError(f"Environment file not found: {env_file}")
    raw_values = dotenv_values(env_file)
    values = {
        key.lower(): value for key, value in raw_values.items() if value is not None
    }
    settings = Settings(**values)
    if settings.environment != "production":
        raise ValueError("The account monitor requires ENVIRONMENT=production")
    return settings


def render_report(account: Any, positions: list[Any], *, checked_at: datetime) -> str:
    """Render safe operator output without account IDs, numbers, or secrets."""

    equity = _decimal(_field(account, "equity"))
    last_equity = _decimal(_field(account, "last_equity"))
    daily_pnl = (
        equity - last_equity if equity is not None and last_equity is not None else None
    )
    daily_pnl_percent = (
        daily_pnl / last_equity
        if daily_pnl is not None
        and last_equity is not None
        and last_equity != Decimal(0)
        else None
    )
    divider = "=" * 68
    sub_divider = "-" * 68
    lines = [
        divider,
        "                 PRISM ALPACA PAPER ACCOUNT OVERVIEW",
        divider,
        f"  Account Status      : {_text(_field(account, 'status'))}",
        f"  Currency            : {_text(_field(account, 'currency'))}",
        "  Account Identifier  : [redacted]",
        sub_divider,
        f"  Portfolio Value     : {_money(_field(account, 'portfolio_value'))}",
        f"  Today's P&L         : {_money(daily_pnl)} ({_percentage(daily_pnl_percent)})",
        f"  Cash                : {_money(_field(account, 'cash'))}",
        f"  Buying Power        : {_money(_field(account, 'buying_power'))}",
        f"  Equity              : {_money(equity)}",
        f"  Long Market Value   : {_money(_field(account, 'long_market_value'))}",
        f"  Short Market Value  : {_money(_field(account, 'short_market_value'))}",
        sub_divider,
        f"  Pattern Day Trader  : {_yes_no(_field(account, 'pattern_day_trader'))}",
        f"  Day Trades Used     : {_text(_field(account, 'daytrade_count'))}",
        f"  Margin Multiplier   : {_number(_field(account, 'multiplier'))}x",
        f"  Shorting Allowed    : {_yes_no(_field(account, 'shorting_enabled'))}",
        f"  Trading Blocked     : {_yes_no(_field(account, 'trading_blocked'))}",
        sub_divider,
    ]
    if not positions:
        lines.append("  [i] No open positions currently.")
    else:
        lines.append(f"  Open Positions ({len(positions)}):")
        for position in positions:
            symbol = str(_field(position, "symbol", "unavailable"))
            side = str(_field(position, "side", "unavailable"))
            lines.extend(
                [
                    f"    {symbol} ({side})",
                    f"      Quantity         : {_number(_field(position, 'qty'))}",
                    f"      Market Value     : {_money(_field(position, 'market_value'))}",
                    (
                        f"      Unrealized P&L   : {_money(_field(position, 'unrealized_pl'))} "
                        f"({_percentage(_field(position, 'unrealized_plpc'))})"
                    ),
                ]
            )
    lines.extend(
        [divider, f"  Checked at (UTC): {checked_at.astimezone(UTC).isoformat()}"]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only PRISM Alpaca paper-account monitor"
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=REPOSITORY_ROOT / ".env.production",
        help="Local production environment file (default: repository .env.production)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        settings = load_production_settings(args.env_file.resolve())
        gateway = AlpacaPyGateway(settings)
        account = gateway.get_account()
        positions = gateway.get_positions()
    except Exception as exc:  # noqa: BLE001
        # Provider errors can include sensitive response bodies.
        print(
            f"Paper-account monitor failed safely: {type(exc).__name__}",
            file=sys.stderr,
        )
        return 1

    print(render_report(account, positions, checked_at=datetime.now(UTC)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
