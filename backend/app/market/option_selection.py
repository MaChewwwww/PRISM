from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

from app.contracts.models import (
    OptionLeg,
    OptionSide,
    OptionStrategy,
    OptionType,
    StrategyKind,
)


class OptionSelectionError(ValueError):
    """The live contract/quote set cannot produce a safe order."""


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise OptionSelectionError("Option expiration is invalid") from exc


def _quote_price(
    record: dict[str, Any],
    now: datetime,
    *,
    entry_touch: bool = False,
    opening_side: Literal["buy", "sell"] = "buy",
) -> Decimal:
    try:
        bid = Decimal(str(record["bid"]))
        ask = Decimal(str(record["ask"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise OptionSelectionError("Option quote is incomplete") from exc
    if bid <= 0 or ask <= 0 or ask < bid:
        raise OptionSelectionError("Option quote is invalid")
    timestamp = record.get("quote_timestamp")
    if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
        raise OptionSelectionError("Option quote timestamp is missing")
    age = (now - timestamp.astimezone(UTC)).total_seconds()
    if age < -300 or age > 30:
        raise OptionSelectionError("Option quote is stale")
    if (ask - bid) / ((ask + bid) / Decimal("2")) > Decimal("0.10"):
        raise OptionSelectionError("Option quote spread exceeds 10 percent")
    increment = Decimal(str(record.get("price_increment", "0.01")))
    if increment <= 0:
        raise OptionSelectionError("Option price increment is invalid")
    if entry_touch:
        # A buy opens at the ask.  The selector is only used for long/debit
        # strategies, so the net debit is assembled from the long ask and
        # short bid below.  Keep this helper's midpoint behavior as the
        # production default for callers that still use limit economics.
        return ask if opening_side == "buy" else bid
    return ((bid + ask) / Decimal("2") / increment).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    ) * increment


def select_option_strategy(
    contracts: list[dict[str, Any]],
    quotes: dict[str, dict[str, Any]],
    *,
    underlying_price: Decimal,
    direction: Literal["bullish", "bearish"],
    structure: Literal["long", "debit_spread"],
    now: datetime,
    exit_dte_threshold: int = 7,
    force_flatten_at: datetime | None = None,
    pricing: Literal["midpoint", "entry_touch"] = "midpoint",
) -> OptionStrategy:
    """Select a fresh ATM long or adjacent OTM debit spread from live inputs."""
    if now.tzinfo is None or underlying_price <= 0:
        raise OptionSelectionError("Selection inputs are invalid")
    min_expiration = now.date() + timedelta(days=exit_dte_threshold)
    if force_flatten_at is not None:
        min_expiration = max(min_expiration, force_flatten_at.astimezone(UTC).date())
    option_type = OptionType.CALL if direction == "bullish" else OptionType.PUT
    candidates = []
    diag: dict[str, int] = {
        "expired_or_before_min_dte": 0,
        "inactive_or_untradable": 0,
        "wrong_type": 0,
        "missing_quotes": 0,
        "invalid_strike": 0,
        "quote_error": 0,
        "quote_stale": 0,
        "quote_spread_exceeded": 0,
    }
    for contract in contracts:
        expiration = _as_date(contract.get("expiration"))
        if expiration <= min_expiration:
            diag["expired_or_before_min_dte"] += 1
            continue
        if not contract.get("active", True) or contract.get("tradable") is False:
            diag["inactive_or_untradable"] += 1
            continue
        if not str(contract.get("option_type", "")).lower().endswith(option_type.value):
            diag["wrong_type"] += 1
            continue
        quotes_for_contract = quotes.get(str(contract.get("symbol")))
        if quotes_for_contract is None:
            diag["missing_quotes"] += 1
            continue
        try:
            strike = Decimal(str(contract["strike"]))
        except (KeyError, TypeError, ValueError):
            diag["invalid_strike"] += 1
            continue
        try:
            price = _quote_price(
                quotes_for_contract,
                now,
                entry_touch=pricing == "entry_touch",
            )
        except OptionSelectionError as exc:
            err_msg = str(exc)
            if "stale" in err_msg:
                diag["quote_stale"] += 1
            elif "spread" in err_msg:
                diag["quote_spread_exceeded"] += 1
            else:
                diag["quote_error"] += 1
            continue
        candidates.append((expiration, strike, contract, price))
    if not candidates:
        breakdown = [f"{k}={v}" for k, v in diag.items() if v > 0]
        breakdown_str = f" ({', '.join(breakdown)})" if breakdown else ""
        msg = (
            f"No fresh active option contract satisfies exit rules; "
            f"examined {len(contracts)} contracts{breakdown_str}"
        )
        raise OptionSelectionError(msg)
    expiration = min(item[0] for item in candidates)
    same_expiration = [item for item in candidates if item[0] == expiration]
    long_item = min(same_expiration, key=lambda item: abs(item[1] - underlying_price))
    long_exp, long_strike, long_contract, long_price = long_item
    long_leg = OptionLeg(
        symbol=str(long_contract["symbol"]),
        underlying=str(long_contract["underlying"]),
        expiration=long_exp.isoformat(),
        option_type=option_type,
        side=OptionSide.BUY,
        strike_price=long_strike,
        position_intent="buy_to_open",
    )
    if structure == "long":
        kind = StrategyKind.LONG_CALL if option_type == OptionType.CALL else StrategyKind.LONG_PUT
        return OptionStrategy(kind=kind, legs=[long_leg], limit_price=long_price)
    if option_type == OptionType.CALL:
        short_pool = [item for item in same_expiration if item[1] > long_strike]
        kind = StrategyKind.CALL_DEBIT_SPREAD
    else:
        short_pool = [item for item in same_expiration if item[1] < long_strike]
        kind = StrategyKind.PUT_DEBIT_SPREAD
    if not short_pool:
        raise OptionSelectionError("No adjacent OTM short strike for debit spread")
    short_item = min(short_pool, key=lambda item: abs(item[1] - long_strike))
    short_exp, short_strike, short_contract, short_price = short_item
    if pricing == "entry_touch":
        # The short leg is sold at its bid when opening a debit spread.
        short_price = _quote_price(
            quotes[str(short_contract["symbol"])],
            now,
            entry_touch=True,
            opening_side="sell",
        )
        debit = long_price - short_price
    else:
        debit = long_price - short_price
    if debit <= 0:
        raise OptionSelectionError("Debit spread must have a positive net debit")
    short_leg = OptionLeg(
        symbol=str(short_contract["symbol"]),
        underlying=str(short_contract["underlying"]),
        expiration=short_exp.isoformat(),
        option_type=option_type,
        side=OptionSide.SELL,
        strike_price=short_strike,
        position_intent="sell_to_open",
    )
    return OptionStrategy(kind=kind, legs=[long_leg, short_leg], limit_price=debit)
