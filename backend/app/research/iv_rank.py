"""Deterministic implied-volatility rank calculations.

Alpaca's option-chain response contains a point-in-time implied volatility, not
an historical IV-rank series.  This module deliberately keeps the two concepts
separate: an IV rank can only be produced from timestamped observations from a
declared provider (or from observations that PRISM has durably recorded from
that provider).  Missing or malformed history is an explicit unavailable
state, never a fabricated zero or percentile.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from app.contracts.models import OptionLeg, OptionType


class IvRankUnavailable(ValueError):
    """The current IV or its timestamped history cannot support an IV rank."""


@dataclass(frozen=True)
class IvObservation:
    observed_at: datetime
    implied_volatility: Decimal
    source: str
    option_symbol: str | None = None


@dataclass(frozen=True)
class IvRankResult:
    rank: Decimal
    observation_count: int
    observed_from: datetime
    observed_to: datetime
    source: str


def _normal_cdf(value: Decimal) -> Decimal:
    """Decimal-only Abramowitz-Stegun normal CDF approximation."""

    sign = Decimal("1") if value >= 0 else Decimal("-1")
    x = abs(value)
    t = Decimal("1") / (Decimal("1") + Decimal("0.2316419") * x)
    polynomial = t * (
        Decimal("0.319381530")
        + t
        * (
            Decimal("-0.356563782")
            + t
            * (Decimal("1.781477937") + t * (Decimal("-1.821255978") + t * Decimal("1.330274429")))
        )
    )
    tail = Decimal("0.3989422804014327") * (-(x * x) / Decimal("2")).exp() * polynomial
    return (Decimal("0.5") + sign * (Decimal("0.5") - tail)).quantize(Decimal("0.00000001"))


def _black_scholes_price(
    underlying: Decimal,
    strike: Decimal,
    years: Decimal,
    volatility: Decimal,
    option_type: OptionType,
) -> Decimal:
    if underlying <= 0 or strike <= 0 or years <= 0 or volatility <= 0:
        return Decimal("0")
    sqrt_years = years.sqrt()
    d1 = (underlying / strike).ln() / (volatility * sqrt_years) + volatility * sqrt_years / Decimal(
        "2"
    )
    d2 = d1 - volatility * sqrt_years
    if option_type is OptionType.CALL:
        return underlying * _normal_cdf(d1) - strike * _normal_cdf(d2)
    return strike * _normal_cdf(-d2) - underlying * _normal_cdf(-d1)


def infer_iv_observations(
    option_bars: Sequence[dict[str, Any]],
    underlying_bars: Sequence[dict[str, Any]],
    *,
    leg: OptionLeg,
    source: str = "alpaca_option_bars:black_scholes_r0_v1",
) -> list[IvObservation]:
    """Infer historical IV from observed Alpaca option/underlying bars.

    Alpaca option bars expose observed premiums rather than historical Greeks.
    For each bar we solve the Black-Scholes premium (zero risk-free-rate
    assumption is explicit in the source tag) with Decimal arithmetic.  Bars
    lacking an underlying close, valid time-to-expiry, or a solvable premium
    are discarded rather than backfilled.
    """

    underlying_prices: list[tuple[datetime, Decimal]] = []
    for row in underlying_bars:
        timestamp = row.get("timestamp") if isinstance(row, dict) else None
        if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
            continue
        try:
            close = Decimal(str(row["close"]))
        except (KeyError, InvalidOperation, TypeError, ValueError):
            continue
        if close > 0:
            underlying_prices.append((timestamp.astimezone(UTC), close))
    underlying_prices.sort(key=lambda item: item[0])
    if not underlying_prices:
        return []
    try:
        expiration = date.fromisoformat(leg.expiration)
    except ValueError:
        return []
    observations: list[IvObservation] = []
    for row in option_bars:
        timestamp = row.get("timestamp") if isinstance(row, dict) else None
        if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
            continue
        timestamp = timestamp.astimezone(UTC)
        try:
            premium = Decimal(str(row["close"]))
        except (KeyError, InvalidOperation, TypeError, ValueError):
            continue
        if premium <= 0:
            continue
        prior = [item for item in underlying_prices if item[0].date() <= timestamp.date()]
        if not prior:
            continue
        underlying = prior[-1][1]
        days = (expiration - timestamp.date()).days
        if days <= 0:
            continue
        years = Decimal(str(days)) / Decimal("365")
        intrinsic = max(
            Decimal("0"),
            underlying - leg.strike_price
            if leg.option_type is OptionType.CALL
            else leg.strike_price - underlying,
        )
        upper_bound = underlying if leg.option_type is OptionType.CALL else leg.strike_price
        if premium <= intrinsic or premium >= upper_bound:
            continue
        low, high = Decimal("0.0001"), Decimal("8")
        if (
            _black_scholes_price(underlying, leg.strike_price, years, high, leg.option_type)
            < premium
        ):
            continue
        for _ in range(48):
            midpoint = (low + high) / Decimal("2")
            model_price = _black_scholes_price(
                underlying, leg.strike_price, years, midpoint, leg.option_type
            )
            if model_price < premium:
                low = midpoint
            else:
                high = midpoint
        iv = (low + high) / Decimal("2")
        if iv > 0 and iv < 10:
            observations.append(
                IvObservation(
                    observed_at=timestamp,
                    implied_volatility=iv,
                    source=source,
                    option_symbol=leg.symbol,
                )
            )
    return observations


def _normalize_observation(value: Any) -> IvObservation | None:
    if isinstance(value, IvObservation):
        observation = value
    elif isinstance(value, dict):
        timestamp = value.get("observed_at", value.get("timestamp"))
        raw_iv = value.get("implied_volatility", value.get("iv"))
        source = value.get("source")
        try:
            iv = Decimal(str(raw_iv))
        except (InvalidOperation, TypeError, ValueError):
            return None
        if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
            return None
        if not isinstance(source, str) or not source.strip():
            return None
        observation = IvObservation(
            observed_at=timestamp,
            implied_volatility=iv,
            source=source.strip(),
            option_symbol=(str(value["option_symbol"]) if value.get("option_symbol") else None),
        )
    else:
        return None

    source_key = observation.source.strip().lower().replace("-", "_").replace(" ", "_")
    if (
        observation.observed_at.tzinfo is None
        or not observation.source.strip()
        or source_key in {"unknown", "fixture", "illustrative_fixture", "synthetic", "fallback"}
        or not observation.implied_volatility.is_finite()
        or observation.implied_volatility <= 0
        or observation.implied_volatility >= 10
    ):
        return None
    return IvObservation(
        observed_at=observation.observed_at.astimezone(UTC),
        implied_volatility=observation.implied_volatility,
        source=observation.source.strip(),
        option_symbol=observation.option_symbol,
    )


def compute_iv_rank(
    current_iv: Decimal,
    observations: Sequence[IvObservation | dict[str, Any]],
    *,
    now: datetime,
    lookback_days: int = 252,
    minimum_observations: int = 20,
) -> IvRankResult:
    """Return the percentile rank of current IV over valid observed history.

    The rank is ``100 * count(history_iv <= current_iv) / count(history)``.
    Current IV is included as a timestamped observation by the caller when it
    was obtained from a live quote.  A provider must supply at least the
    configured number of observations inside the lookback window.  No
    interpolation, forward filling, or synthetic history is performed.
    """

    if now.tzinfo is None or lookback_days <= 0 or minimum_observations <= 0:
        raise IvRankUnavailable("IV-rank inputs are invalid")
    try:
        current = Decimal(str(current_iv))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise IvRankUnavailable("Current implied volatility is invalid") from exc
    if not current.is_finite() or current <= 0 or current >= 10:
        raise IvRankUnavailable("Current implied volatility is unavailable")

    now_utc = now.astimezone(UTC)
    cutoff = now_utc - timedelta(days=lookback_days)
    deduplicated: dict[tuple[datetime, Decimal, str, str | None], IvObservation] = {}
    for raw in observations:
        item = _normalize_observation(raw)
        if item is None or not (cutoff <= item.observed_at <= now_utc):
            continue
        deduplicated[
            (item.observed_at, item.implied_volatility, item.source, item.option_symbol)
        ] = item
    normalized = list(deduplicated.values())
    if len(normalized) < minimum_observations:
        raise IvRankUnavailable(
            f"Only {len(normalized)} IV observations available; {minimum_observations} required"
        )
    normalized.sort(key=lambda item: item.observed_at)
    rank = (
        Decimal(str(sum(1 for item in normalized if item.implied_volatility <= current)))
        / Decimal(str(len(normalized)))
        * Decimal("100")
    )
    sources = sorted({item.source for item in normalized})
    return IvRankResult(
        rank=round(min(Decimal("100"), max(Decimal("0"), rank)), 4),
        observation_count=len(normalized),
        observed_from=normalized[0].observed_at,
        observed_to=normalized[-1].observed_at,
        source=",".join(sources),
    )
