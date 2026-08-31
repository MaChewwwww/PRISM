"""Provider-neutral historical option contract and NBBO replay inputs.

The staging simulator deliberately keeps this boundary independent from the
Alpaca trading gateway.  A provider must return timestamped bid/ask quotes;
daily OHLC bars or latest snapshots cannot satisfy the replay contract.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen


class HistoricalOptionsUnavailable(ValueError):
    """The configured provider cannot satisfy a historical replay request."""


@dataclass(frozen=True, slots=True)
class HistoricalOptionContract:
    symbol: str
    underlying: str
    expiration: date
    strike: Decimal
    option_type: str
    active: bool
    tradable: bool
    price_increment: Decimal = Decimal("0.01")
    # Providers that expose listing/activation history should populate this
    # field.  The replay filters it at the decision checkpoint so a contract
    # first listed later in the window cannot leak into an earlier decision.
    available_at: datetime | None = None
    payload_digest: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "underlying": self.underlying,
            "expiration": self.expiration.isoformat(),
            "strike": str(self.strike),
            "option_type": self.option_type,
            "active": self.active,
            "tradable": self.tradable,
            "price_increment": str(self.price_increment),
            "available_at": (
                self.available_at.astimezone(UTC).isoformat() if self.available_at else None
            ),
            "payload_digest": self.payload_digest,
        }


@dataclass(frozen=True, slots=True)
class HistoricalOptionQuote:
    symbol: str
    quote_timestamp: datetime
    bid: Decimal
    ask: Decimal
    feed: str
    iv_rank: Decimal | None = None
    payload_digest: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "quote_timestamp": self.quote_timestamp.astimezone(UTC).isoformat(),
            "bid": str(self.bid),
            "ask": str(self.ask),
            "feed": self.feed,
            "iv_rank": str(self.iv_rank) if self.iv_rank is not None else None,
            "payload_digest": self.payload_digest,
        }


class HistoricalOptionsProvider(Protocol):
    """Read-only historical options port used by the staging simulator."""

    feed: str

    def list_contracts(
        self,
        underlying: str,
        *,
        start: datetime,
        end: datetime,
        as_of: datetime | None = None,
    ) -> list[HistoricalOptionContract]: ...

    def get_quotes(
        self,
        option_symbols: Iterable[str],
        *,
        start: datetime,
        end: datetime,
    ) -> list[HistoricalOptionQuote]: ...


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise HistoricalOptionsUnavailable("Historical option timestamp is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HistoricalOptionsUnavailable("Historical option timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _decimal(value: Any, *, positive: bool = False) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise HistoricalOptionsUnavailable("Historical option numeric value is invalid") from exc
    if not parsed.is_finite() or (positive and parsed <= 0):
        raise HistoricalOptionsUnavailable("Historical option numeric value is invalid")
    return parsed


def _boolean(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    return bool(value)


def normalize_contract(payload: dict[str, Any]) -> HistoricalOptionContract:
    try:
        expiration_raw = payload.get("expiration", payload.get("expiration_date"))
        expiration_text = str(expiration_raw)
        expiration = date.fromisoformat(expiration_text.split("T", 1)[0])
        symbol = str(payload["symbol"]).strip().upper()
        underlying = (
            str(payload.get("underlying", payload.get("underlying_symbol"))).strip().upper()
        )
        option_type = str(payload.get("option_type", payload.get("type", ""))).lower()
        if option_type in {"c", "call"} or option_type.endswith("call"):
            option_type = "call"
        elif option_type in {"p", "put"} or option_type.endswith("put"):
            option_type = "put"
        if not symbol or not underlying or option_type not in {"call", "put"}:
            raise KeyError("contract identity")
        availability_raw = next(
            (
                payload.get(key)
                for key in ("available_at", "listed_at", "listing_timestamp", "created_at")
                if payload.get(key) is not None
            ),
            None,
        )
        return HistoricalOptionContract(
            symbol=symbol,
            underlying=underlying,
            expiration=expiration,
            strike=_decimal(payload.get("strike", payload.get("strike_price")), positive=True),
            option_type=option_type,
            active=_boolean(payload.get("active"), default=True),
            tradable=_boolean(payload.get("tradable"), default=True),
            price_increment=_decimal(payload.get("price_increment", "0.01"), positive=True),
            available_at=(
                _parse_timestamp(availability_raw) if availability_raw is not None else None
            ),
            payload_digest=payload_digest(payload),
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, HistoricalOptionsUnavailable):
            raise
        raise HistoricalOptionsUnavailable("Historical option contract is incomplete") from exc


def normalize_quote(payload: dict[str, Any], *, feed: str) -> HistoricalOptionQuote:
    try:
        symbol = str(payload.get("symbol", payload.get("option_symbol"))).strip().upper()
        bid = _decimal(payload.get("bid", payload.get("bid_price")), positive=True)
        ask = _decimal(payload.get("ask", payload.get("ask_price")), positive=True)
        if not symbol or ask < bid:
            raise ValueError("quote")
        timestamp = _parse_timestamp(
            payload.get("quote_timestamp", payload.get("timestamp", payload.get("observed_at")))
        )
        expected_feed = str(feed).strip().upper()
        observed_feed = str(payload.get("feed", feed)).strip().upper()
        if not expected_feed or observed_feed != expected_feed:
            raise HistoricalOptionsUnavailable("Historical option quote feed is not entitled")
        return HistoricalOptionQuote(
            symbol=symbol,
            quote_timestamp=timestamp,
            bid=bid,
            ask=ask,
            feed=observed_feed,
            iv_rank=(_decimal(payload["iv_rank"]) if payload.get("iv_rank") is not None else None),
            payload_digest=payload_digest(payload),
        )
    except HistoricalOptionsUnavailable:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise HistoricalOptionsUnavailable("Historical option quote is incomplete") from exc


def payload_digest(value: Any) -> str:
    encoded = json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class HttpHistoricalOptionsProvider:
    """Small JSON adapter for an operator-entitled historical NBBO service.

    The service may return either a list or ``{"data": [...]}``.  Pagination
    is supported through ``next``/``next_url`` links or a cursor value.  The
    adapter intentionally rejects a response that contains no usable rows.
    """

    def __init__(
        self, url: str, *, api_key: str | None = None, feed: str = "OPRA", timeout: float = 30
    ) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("historical options provider URL is invalid")
        self.url = url
        self.api_key = api_key
        self.feed = str(feed).strip().upper()
        if not self.feed:
            raise ValueError("historical options provider feed is required")
        self.timeout = timeout
        self.last_raw_contract_rows: list[dict[str, Any]] = []
        self.last_raw_quote_rows: list[dict[str, Any]] = []

    def list_contracts(
        self,
        underlying: str,
        *,
        start: datetime,
        end: datetime,
        as_of: datetime | None = None,
    ) -> list[HistoricalOptionContract]:
        rows = self._fetch_rows(
            {
                "kind": "contracts",
                "underlying": underlying.upper(),
                "start": _iso(start),
                "end": _iso(end),
                **({"as_of": _iso(as_of)} if as_of is not None else {}),
            }
        )
        self.last_raw_contract_rows = list(rows)
        contracts: list[HistoricalOptionContract] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                contract = normalize_contract(row)
            except HistoricalOptionsUnavailable:
                continue
            if (
                contract.underlying == underlying.upper()
                and contract.expiration >= start.date()
                and (
                    as_of is None
                    or contract.available_at is None
                    or contract.available_at <= as_of.astimezone(UTC)
                )
            ):
                contracts.append(contract)
        if not contracts:
            raise HistoricalOptionsUnavailable(
                f"No historical option contracts for {underlying.upper()}"
            )
        return contracts

    def get_quotes(
        self,
        option_symbols: Iterable[str],
        *,
        start: datetime,
        end: datetime,
    ) -> list[HistoricalOptionQuote]:
        symbols = [str(symbol).upper() for symbol in option_symbols]
        if not symbols:
            return []
        rows = self._fetch_rows(
            {
                "kind": "quotes",
                "symbols": ",".join(symbols),
                "start": _iso(start),
                "end": _iso(end),
                "feed": self.feed,
            }
        )
        self.last_raw_quote_rows = list(rows)
        quotes: list[HistoricalOptionQuote] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                quote = normalize_quote(row, feed=self.feed)
            except HistoricalOptionsUnavailable:
                continue
            if quote.symbol in symbols and start.astimezone(
                UTC
            ) <= quote.quote_timestamp <= end.astimezone(UTC):
                quotes.append(quote)
        if not quotes:
            raise HistoricalOptionsUnavailable("Historical option NBBO quotes are unavailable")
        return sorted(quotes, key=lambda item: (item.quote_timestamp, item.symbol))

    def _fetch_rows(self, params: dict[str, str]) -> list[dict[str, Any]]:
        next_url: str | None = self.url
        cursor: str | None = None
        rows: list[dict[str, Any]] = []
        for _ in range(100):
            if next_url is None:
                break
            parsed = urlparse(next_url)
            query = dict(parse_qsl(parsed.query))
            if next_url == self.url:
                query.update(params)
            if cursor:
                query["cursor"] = cursor
            request_url = urlunparse(parsed._replace(query=urlencode(query)))
            headers = {"Accept": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            try:
                with urlopen(
                    Request(request_url, headers=headers), timeout=self.timeout
                ) as response:
                    raw = response.read(10_000_000)
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                raise HistoricalOptionsUnavailable(
                    "Historical options provider unavailable"
                ) from exc
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise HistoricalOptionsUnavailable(
                    "Historical options provider returned invalid JSON"
                ) from exc
            page_rows = payload.get("data", payload) if isinstance(payload, dict) else payload
            if isinstance(page_rows, list):
                rows.extend(item for item in page_rows if isinstance(item, dict))
            elif isinstance(page_rows, dict):
                rows.append(page_rows)
            else:
                raise HistoricalOptionsUnavailable(
                    "Historical options provider returned invalid rows"
                )
            if not isinstance(payload, dict):
                break
            link = payload.get("next_url", payload.get("next"))
            if isinstance(link, str) and link:
                next_url, cursor = urljoin(request_url, link), None
            else:
                cursor_value = payload.get("next_cursor", payload.get("cursor"))
                next_url = self.url if cursor_value else None
                cursor = str(cursor_value) if cursor_value else None
        return rows


def _iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("historical options range must be timezone-aware")
    return value.astimezone(UTC).isoformat()


class StaticHistoricalOptionsProvider:
    """Deterministic fixture provider used by unit tests and local development."""

    def __init__(
        self,
        contracts: Iterable[HistoricalOptionContract],
        quotes: Iterable[HistoricalOptionQuote],
        *,
        feed: str = "OPRA",
    ) -> None:
        self.feed = str(feed).strip().upper()
        if not self.feed:
            raise ValueError("historical options provider feed is required")
        self._contracts = list(contracts)
        self._quotes = list(quotes)
        self.last_raw_contract_rows = [item.as_dict() for item in self._contracts]
        self.last_raw_quote_rows = [item.as_dict() for item in self._quotes]

    def list_contracts(
        self,
        underlying: str,
        *,
        start: datetime,
        end: datetime,
        as_of: datetime | None = None,
    ) -> list[HistoricalOptionContract]:
        result = [
            item
            for item in self._contracts
            if item.underlying == underlying.upper()
            and item.expiration >= start.date()
            and (
                as_of is None
                or item.available_at is None
                or item.available_at <= as_of.astimezone(UTC)
            )
        ]
        self.last_raw_contract_rows = [item.as_dict() for item in result]
        if not result:
            raise HistoricalOptionsUnavailable("No historical option contracts")
        return result

    def get_quotes(
        self,
        option_symbols: Iterable[str],
        *,
        start: datetime,
        end: datetime,
    ) -> list[HistoricalOptionQuote]:
        symbols = {str(value).upper() for value in option_symbols}
        result = [
            item
            for item in self._quotes
            if item.symbol in symbols
            and start.astimezone(UTC) <= item.quote_timestamp <= end.astimezone(UTC)
        ]
        self.last_raw_quote_rows = [item.as_dict() for item in result]
        if not result:
            raise HistoricalOptionsUnavailable("Historical option NBBO quotes are unavailable")
        return sorted(result, key=lambda item: (item.quote_timestamp, item.symbol))


def quote_map_at(
    quotes: Iterable[HistoricalOptionQuote],
    *,
    observed_at: datetime,
    max_age_seconds: int = 30,
) -> dict[str, dict[str, Any]]:
    """Return the latest quote at or before ``observed_at`` without lookahead."""

    target = observed_at.astimezone(UTC)
    latest: dict[str, HistoricalOptionQuote] = {}
    for quote in quotes:
        timestamp = quote.quote_timestamp.astimezone(UTC)
        if timestamp <= target and (target - timestamp).total_seconds() <= max_age_seconds:
            previous = latest.get(quote.symbol)
            if previous is None or timestamp > previous.quote_timestamp:
                latest[quote.symbol] = quote
    return {
        symbol: {
            "bid": quote.bid,
            "ask": quote.ask,
            "quote_timestamp": quote.quote_timestamp,
            "feed": quote.feed,
            "iv_rank": quote.iv_rank,
        }
        for symbol, quote in latest.items()
    }
