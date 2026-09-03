"""Deterministic five-minute option replay primitives for staging."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app.backtest.historical_options import HistoricalOptionQuote, quote_map_at
from app.contracts.models import OptionSide, OptionStrategy

EASTERN = ZoneInfo("America/New_York")
UTC_OPEN = time(9, 30)
UTC_CLOSE = time(16, 0)
CADENCE = timedelta(minutes=5)


@dataclass(frozen=True, slots=True)
class ReplayWindow:
    start: date = date(2026, 8, 24)
    end: date = date(2026, 8, 27)
    new_entry_cutoff: datetime = datetime(2026, 8, 26, 20, tzinfo=UTC)
    force_flatten_at: datetime = datetime(2026, 8, 27, 20, tzinfo=UTC)

    def sessions(self) -> list[date]:
        current = self.start
        result: list[date] = []
        while current <= self.end:
            if current.weekday() < 5:
                result.append(current)
            current += timedelta(days=1)
        return result

    def grid(self, *, start_date: date | None = None) -> list[datetime]:
        points: list[datetime] = []
        for session in self.sessions():
            if start_date is not None and session < start_date:
                continue
            local = datetime.combine(session, UTC_OPEN, tzinfo=EASTERN)
            close = datetime.combine(session, UTC_CLOSE, tzinfo=EASTERN)
            while local <= close:
                points.append(local.astimezone(UTC))
                local += CADENCE
        return points

    def is_entry_allowed(self, observed_at: datetime) -> bool:
        return observed_at.astimezone(UTC) < self.new_entry_cutoff


@dataclass(frozen=True, slots=True)
class SimulatedFill:
    status: str
    quantity: int | None = None
    entry_at: datetime | None = None
    entry_price: Decimal | None = None
    exit_at: datetime | None = None
    exit_price: Decimal | None = None
    slippage: Decimal | None = None
    exit_reason: str | None = None
    legs: tuple[dict[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "quantity": self.quantity,
            "entry_at": self.entry_at.astimezone(UTC).isoformat() if self.entry_at else None,
            "entry_price": str(self.entry_price) if self.entry_price is not None else None,
            "exit_at": self.exit_at.astimezone(UTC).isoformat() if self.exit_at else None,
            "exit_price": str(self.exit_price) if self.exit_price is not None else None,
            "slippage": str(self.slippage) if self.slippage is not None else None,
            "exit_reason": self.exit_reason,
            "cost_model": "observed_nbbo_touch",
            "legs": list(self.legs),
        }


@dataclass(frozen=True, slots=True)
class SimulationValuation:
    observed_at: datetime
    mark: Decimal
    gross_pnl: Decimal
    net_pnl: Decimal
    drawdown: Decimal
    mae: Decimal
    mfe: Decimal
    capital_at_risk: Decimal
    coverage_pct: Decimal
    confidence: str
    exit_reason: str | None = None


@dataclass(frozen=True, slots=True)
class SimulationResult:
    fill: SimulatedFill
    valuations: tuple[SimulationValuation, ...] = ()
    state: str = "incomplete"
    reason: str | None = None


class DeterministicOptionSimulator:
    """Replay one option strategy using only timestamped NBBO observations."""

    def __init__(self, *, max_quote_age_seconds: int = 30) -> None:
        self.max_quote_age_seconds = max_quote_age_seconds

    @staticmethod
    def strategy_value(
        strategy: OptionStrategy,
        quotes: dict[str, dict[str, Any]],
        *,
        entry: bool,
    ) -> Decimal | None:
        total = Decimal("0")
        for leg in strategy.legs:
            quote = quotes.get(leg.symbol)
            if quote is None or quote.get("bid") is None or quote.get("ask") is None:
                return None
            key = "ask" if (leg.side is OptionSide.BUY) == entry else "bid"
            try:
                price = Decimal(str(quote[key]))
            except Exception:
                return None
            if price <= 0:
                return None
            sign = Decimal("1") if leg.side is OptionSide.BUY else Decimal("-1")
            total += sign * price * leg.ratio_qty
        return total if total > 0 else None

    @staticmethod
    def midpoint_value(
        strategy: OptionStrategy, quotes: dict[str, dict[str, Any]]
    ) -> Decimal | None:
        total = Decimal("0")
        for leg in strategy.legs:
            quote = quotes.get(leg.symbol)
            if quote is None or quote.get("bid") is None or quote.get("ask") is None:
                return None
            try:
                midpoint = (Decimal(str(quote["bid"])) + Decimal(str(quote["ask"]))) / Decimal("2")
            except Exception:
                return None
            sign = Decimal("1") if leg.side is OptionSide.BUY else Decimal("-1")
            total += sign * midpoint * leg.ratio_qty
        return total if total > 0 else None

    def replay(
        self,
        strategy: OptionStrategy,
        quotes: Iterable[HistoricalOptionQuote],
        *,
        window: ReplayWindow,
        allocation_multiplier: Decimal = Decimal("1"),
        quantity: int = 1,
        entry_allowed: bool = True,
        start_date: date | None = None,
        thesis_invalidated_at: datetime | None = None,
        exit_policy_json: str | None = None,
    ) -> SimulationResult:
        if quantity < 1:
            return SimulationResult(
                fill=SimulatedFill(status="not_filled"),
                state="incomplete",
                reason="INVALID_QUANTITY",
            )
        quote_rows = tuple(quotes)
        entry_at: datetime | None = None
        entry_price: Decimal | None = None
        entry_slippage = Decimal("0")
        valuations: list[SimulationValuation] = []
        max_loss = Decimal("0")
        peak_pnl = Decimal("0")
        worst_pnl = Decimal("0")
        best_pnl = Decimal("0")
        legs: tuple[dict[str, Any], ...] = ()
        for observed_at in window.grid(start_date=start_date):
            mapped = quote_map_at(
                quote_rows,
                observed_at=observed_at,
                max_age_seconds=self.max_quote_age_seconds,
            )
            if entry_at is None:
                if not entry_allowed or not window.is_entry_allowed(observed_at):
                    continue
                candidate = self.strategy_value(strategy, mapped, entry=True)
                if candidate is None:
                    continue
                entry_at = observed_at
                entry_price = candidate
                entry_slippage = self.touch_slippage(
                    strategy, mapped, entry=True, quantity=quantity
                )
                legs = tuple(
                    {
                        "option_symbol": leg.symbol,
                        "side": leg.side.value,
                        "quantity": quantity * leg.ratio_qty,
                        "entry_price": str(
                            mapped[leg.symbol]["ask" if leg.side is OptionSide.BUY else "bid"]
                        ),
                        "exit_price": None,
                    }
                    for leg in strategy.legs
                )
                max_loss = candidate * Decimal("100") * allocation_multiplier * quantity
            if entry_at is None or entry_price is None:
                continue
            mark = self.strategy_value(strategy, mapped, entry=False)
            if mark is None:
                continue
            gross = (mark - entry_price) * Decimal("100") * allocation_multiplier * quantity
            peak_pnl = max(peak_pnl, gross)
            worst_pnl = min(worst_pnl, gross)
            best_pnl = max(best_pnl, gross)
            mae = worst_pnl
            mfe = best_pnl
            exit_reason = self.exit_reason(
                strategy,
                entry_price=entry_price,
                mark=mark,
                observed_at=observed_at,
                entry_at=entry_at,
                horizon_at=window.force_flatten_at,
                exit_policy_json=exit_policy_json,
                thesis_invalidated_at=thesis_invalidated_at,
                prior_mfe_pct=(
                    best_pnl
                    / (entry_price * Decimal("100") * allocation_multiplier * quantity)
                    * Decimal("100")
                    if entry_price > 0 and allocation_multiplier > 0 and quantity > 0
                    else Decimal("0")
                ),
            )
            valuation = SimulationValuation(
                observed_at=observed_at,
                mark=mark,
                gross_pnl=gross,
                net_pnl=gross,
                drawdown=min(Decimal("0"), gross - peak_pnl),
                mae=mae,
                mfe=mfe,
                capital_at_risk=max_loss,
                coverage_pct=Decimal("100"),
                confidence="high",
                exit_reason=exit_reason,
            )
            valuations.append(valuation)
            if exit_reason is not None:
                legs = tuple(
                    {
                        **leg,
                        "exit_price": str(
                            mapped[leg["option_symbol"]]["bid" if leg["side"] == "buy" else "ask"]
                        ),
                    }
                    for leg in legs
                )
                exit_slippage = self.touch_slippage(
                    strategy, mapped, entry=False, quantity=quantity
                )
                return SimulationResult(
                    fill=SimulatedFill(
                        status="filled",
                        quantity=quantity,
                        entry_at=entry_at,
                        entry_price=entry_price,
                        exit_at=observed_at,
                        exit_price=mark,
                        slippage=entry_slippage + exit_slippage,
                        exit_reason=exit_reason,
                        legs=legs,
                    ),
                    valuations=tuple(valuations),
                    state="complete",
                )
        if entry_at is None:
            required_symbols = {leg.symbol for leg in strategy.legs}
            available_symbols = {quote.symbol for quote in quote_rows}
            missing_data = not required_symbols.issubset(available_symbols) or (
                entry_allowed and not valuations
            )
            return SimulationResult(
                fill=SimulatedFill(status="not_filled"),
                valuations=tuple(valuations),
                state="incomplete" if missing_data else "complete",
                reason=(
                    "DATA_UNAVAILABLE: no valid historical quote"
                    if missing_data
                    else "NO_TRADE"
                    if entry_allowed
                    else "ENTRY_WINDOW_CLOSED"
                ),
            )
        return SimulationResult(
            fill=SimulatedFill(
                status="incomplete",
                quantity=quantity,
                entry_at=entry_at,
                entry_price=entry_price,
                slippage=entry_slippage,
                legs=legs,
            ),
            valuations=tuple(valuations),
            state="incomplete",
            reason="DATA_UNAVAILABLE: no valid terminal quote",
        )

    @staticmethod
    def exit_reason(
        strategy: OptionStrategy,
        *,
        entry_price: Decimal,
        mark: Decimal,
        observed_at: datetime,
        horizon_at: datetime | None,
        exit_policy_json: str | None,
        entry_at: datetime | None = None,
        thesis_invalidated_at: datetime | None = None,
        prior_mfe_pct: Decimal = Decimal("0"),
    ) -> str | None:
        if horizon_at is not None and observed_at >= horizon_at:
            return "HORIZON_CLOSE"
        if entry_price <= 0:
            return "DATA_UNAVAILABLE"
        try:
            policy = json.loads(exit_policy_json or "{}")
            pct = (mark - entry_price) / entry_price * Decimal("100")
            if "hard_take_profit_pct" in policy:
                mfe_pct = max(prior_mfe_pct, pct)
                if pct <= -Decimal(str(policy.get("hard_stop_loss_pct", "50"))):
                    return "HARD_STOP_LOSS"
                if thesis_invalidated_at is not None and observed_at >= thesis_invalidated_at:
                    return "THESIS_INVALIDATION"
                if mfe_pct >= Decimal(
                    str(policy.get("profit_arm_pct", "20"))
                ) and pct <= mfe_pct - Decimal(
                    str(policy.get("profit_trailing_giveback_points", "10"))
                ):
                    return "TRAILING_PROFIT"
                if pct >= Decimal(str(policy.get("hard_take_profit_pct", "40"))):
                    return "HARD_TAKE_PROFIT"
            else:
                if pct >= Decimal(str(policy.get("take_profit_pct", "75"))):
                    return "TAKE_PROFIT"
                if pct <= -Decimal(str(policy.get("stop_loss_pct", "50"))):
                    return "STOP_LOSS"
            if thesis_invalidated_at is not None and observed_at >= thesis_invalidated_at:
                return "THESIS_INVALIDATION"
            expiry = min(date.fromisoformat(leg.expiration) for leg in strategy.legs)
            if (expiry - observed_at.astimezone(UTC).date()).days <= int(
                policy.get("dte_threshold", 7)
            ):
                return "DTE_EXIT"
            if entry_at is not None:
                max_hold_days = int(policy.get("max_hold_days", 14))
                trading_days = 0
                current = entry_at.astimezone(EASTERN).date()
                observed_date = observed_at.astimezone(EASTERN).date()
                while current < observed_date:
                    if current.weekday() < 5:
                        trading_days += 1
                    current += timedelta(days=1)
                if trading_days >= max_hold_days:
                    return "MAX_HOLD"
        except (TypeError, ValueError, json.JSONDecodeError):
            return "DATA_UNAVAILABLE"
        return None

    @staticmethod
    def touch_slippage(
        strategy: OptionStrategy,
        quotes: dict[str, dict[str, Any]],
        *,
        entry: bool,
        quantity: int,
    ) -> Decimal:
        """Sum each leg's observed NBBO touch versus midpoint in dollars."""

        total = Decimal("0")
        for leg in strategy.legs:
            quote = quotes.get(leg.symbol)
            if quote is None:
                return Decimal("0")
            try:
                bid = Decimal(str(quote["bid"]))
                ask = Decimal(str(quote["ask"]))
            except (KeyError, TypeError, ValueError):
                return Decimal("0")
            touch = ask if (leg.side is OptionSide.BUY) == entry else bid
            midpoint = (bid + ask) / Decimal("2")
            total += abs(touch - midpoint) * Decimal("100") * quantity * leg.ratio_qty
        return total
