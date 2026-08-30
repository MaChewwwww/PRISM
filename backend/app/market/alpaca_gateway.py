from __future__ import annotations

import json
import logging
import time
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from alpaca.data.enums import DataFeed
from alpaca.data.historical.news import NewsClient
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import (
    NewsRequest,
    OptionBarsRequest,
    OptionChainRequest,
    StockBarsRequest,
)
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOptionContractsRequest

from app.core.config import Settings

logger = logging.getLogger(__name__)


def _is_transient_provider_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code in {408, 409, 425, 429, 500, 502, 503, 504}:
        return True
    return isinstance(exc, (ConnectionError, TimeoutError))


class AlpacaPyGateway:
    """Typed, read-only Alpaca clients. Domain mapping belongs above this adapter."""

    def __init__(self, settings: Settings):
        if not settings.credentials_present:
            raise ValueError("Alpaca credentials are required for provider reads")
        self.settings = settings
        key = settings.alpaca_api_key or ""
        secret = settings.alpaca_secret_key or ""
        self.trading = TradingClient(key, secret, paper=True)
        self.stocks = StockHistoricalDataClient(key, secret)
        self.options = OptionHistoricalDataClient(key, secret)
        self.news = NewsClient(key, secret)

    def get_account(self) -> Any:
        return self.trading.get_account()

    def get_positions(self) -> list[Any]:
        """Read the complete paper portfolio from the Trading API."""
        positions = self.trading.get_all_positions()
        return list(positions or [])

    def get_clock(self) -> Any:
        """Read the broker market clock used for entry/exit timing."""
        return self.trading.get_clock()

    def get_asset(self, symbol: str) -> Any:
        return self.trading.get_asset(symbol)

    def get_option_contracts(
        self,
        underlying: str,
        *,
        expiration_date_gte: date | None = None,
        expiration_date_lte: date | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Return active option contracts with only server-provided fields."""
        request = GetOptionContractsRequest(
            underlying_symbols=[underlying],
            expiration_date_gte=expiration_date_gte,
            expiration_date_lte=expiration_date_lte,
            limit=limit,
        )
        response = self.trading.get_option_contracts(request)
        contracts = getattr(response, "option_contracts", response)
        if isinstance(contracts, dict):
            contracts = contracts.get("option_contracts", [])
        if not isinstance(contracts, (list, tuple)):
            return []

        def field(contract: Any, name: str, default: Any = None) -> Any:
            if isinstance(contract, dict):
                return contract.get(name, default)
            return getattr(contract, name, default)

        return [
            {
                "symbol": str(field(contract, "symbol", "")),
                "underlying": str(field(contract, "underlying_symbol", underlying)),
                "expiration": field(contract, "expiration_date"),
                "strike": Decimal(str(field(contract, "strike_price"))),
                "option_type": str(field(contract, "type", "")).lower(),
                "active": str(field(contract, "status", "active")).lower().endswith("active"),
                "tradable": bool(field(contract, "tradable", False)),
                "price_increment": field(contract, "price_increment", "0.01"),
            }
            for contract in contracts
        ]

    def get_option_chain(
        self,
        underlying: str,
        *,
        expiration_date_gte: date | None = None,
        expiration_date_lte: date | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Return latest option quotes/Greeks from Alpaca's option-chain endpoint."""
        request = OptionChainRequest(
            underlying_symbol=underlying,
            expiration_date_gte=expiration_date_gte,
            expiration_date_lte=expiration_date_lte,
        )
        response = self.options.get_option_chain(request)
        if not isinstance(response, dict):
            return {}

        def field(value: Any, name: str, default: Any = None) -> Any:
            if isinstance(value, dict):
                return value.get(name, default)
            return getattr(value, name, default)

        normalized: dict[str, dict[str, Any]] = {}
        for symbol, snapshot in response.items():
            quote = field(snapshot, "latest_quote")
            greeks = field(snapshot, "greeks")
            bid = field(quote, "bid_price") if quote is not None else None
            ask = field(quote, "ask_price") if quote is not None else None
            quote_time = field(quote, "timestamp") if quote is not None else None
            # A quote without a timestamp or a complete Greek snapshot is not
            # executable evidence.  Do not turn missing provider fields into
            # zeroes: zero IV/delta can look valid to downstream rules while
            # actually representing an unavailable feed.
            greek_values = (
                field(greeks, "delta") if greeks is not None else None,
                field(greeks, "gamma") if greeks is not None else None,
                field(greeks, "theta") if greeks is not None else None,
                field(greeks, "vega") if greeks is not None else None,
                field(greeks, "implied_volatility") if greeks is not None else None,
            )
            if (
                bid is None
                or ask is None
                or quote_time is None
                or any(value is None for value in greek_values)
            ):
                continue
            normalized[str(symbol)] = {
                "bid": Decimal(str(bid)),
                "ask": Decimal(str(ask)),
                "quote_timestamp": quote_time,
                "delta": Decimal(str(greek_values[0])),
                "gamma": Decimal(str(greek_values[1])),
                "theta": Decimal(str(greek_values[2])),
                "vega": Decimal(str(greek_values[3])),
                "iv": Decimal(str(greek_values[4])),
                # IV rank is not part of every Alpaca snapshot, but preserve
                # it when an entitled provider/feed supplies the field. The
                # The worker computes a historical rank when this optional
                # provider field is absent.
                "iv_rank": (
                    Decimal(str(field(snapshot, "iv_rank")))
                    if field(snapshot, "iv_rank") is not None
                    else None
                ),
            }
        return normalized

    def get_option_bars(
        self,
        option_symbol: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 2000,
    ) -> list[dict[str, Any]]:
        """Retrieve historical option bars for model-derived IV observations."""

        request = OptionBarsRequest(
            symbol_or_symbols=option_symbol,
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
            limit=limit,
        )
        response = self.options.get_option_bars(request)
        data_map = getattr(response, "data", response)
        values: Any = data_map.get(option_symbol, []) if isinstance(data_map, dict) else data_map
        if not isinstance(values, (list, tuple)):
            return []
        bars: list[dict[str, Any]] = []
        for bar in values:
            timestamp = getattr(bar, "timestamp", None)
            close = getattr(bar, "close", None)
            if timestamp is None or close is None:
                continue
            bars.append({"timestamp": timestamp, "close": Decimal(str(close))})
        return bars

    def get_iv_rank_history(
        self,
        underlying: str,
        *,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """Read a declared server-side IV history provider.

        Alpaca's option-chain endpoint is still the source of current quotes
        and Greeks, but it does not expose historical IV rank.  Deployments
        may configure an internal/entitled provider through
        ``IV_RANK_HISTORY_URL``.  The adapter accepts only timestamped IV
        observations and tags every row with that configured source; malformed
        or unavailable provider responses are surfaced as an unavailable read
        so the autonomous worker records ``NO_TRADE``.
        """

        url = self.settings.iv_rank_history_url
        if not url:
            return []
        if start.tzinfo is None or end.tzinfo is None or start >= end:
            raise ValueError("IV history range is invalid")
        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query))
        query.update(
            {
                "symbol": underlying.upper(),
                "start": start.astimezone(UTC).isoformat(),
                "end": end.astimezone(UTC).isoformat(),
            }
        )
        request_url = urlunparse(parsed._replace(query=urlencode(query)))
        headers = {"Accept": "application/json"}
        if self.settings.iv_rank_history_api_key:
            headers["Authorization"] = f"Bearer {self.settings.iv_rank_history_api_key}"
        try:
            with urlopen(
                Request(request_url, headers=headers),
                timeout=self.settings.alpaca_request_timeout_seconds,
            ) as response:
                raw = response.read(2_000_000)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise ValueError("IV history provider unavailable") from exc
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("IV history provider returned invalid JSON") from exc
        rows = payload.get("data") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ValueError("IV history provider returned an invalid payload")
        # Keep credentials/userinfo out of persisted provenance labels when an
        # operator uses a URL with embedded authentication.
        source = "iv_history_provider:" + (parsed.hostname or "configured")
        normalized: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            timestamp = row.get("observed_at", row.get("timestamp"))
            iv = row.get("implied_volatility", row.get("iv"))
            option_symbol = row.get("option_symbol", row.get("symbol", underlying))
            if not isinstance(timestamp, datetime):
                try:
                    timestamp = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
                except (TypeError, ValueError):
                    continue
            if timestamp.tzinfo is None:
                continue
            try:
                iv_decimal = Decimal(str(iv))
            except (TypeError, ValueError):
                continue
            if not iv_decimal.is_finite() or iv_decimal <= 0 or iv_decimal >= 10:
                continue
            normalized.append(
                {
                    "observed_at": timestamp.astimezone(UTC),
                    "implied_volatility": iv_decimal,
                    "source": source,
                    "option_symbol": str(option_symbol),
                }
            )
        return normalized

    def get_news(
        self,
        symbol: str,
        limit: int = 10,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve news articles from Alpaca News API for a ticker symbol, with retries."""
        request_params = NewsRequest(
            symbols=symbol,
            limit=limit,
            start=start,
            end=end,
        )

        retries = 3
        delay = 1.0
        for attempt in range(retries):
            try:
                news_response = self.news.get_news(request_params)
                # Flatten the data dict mapping symbols to lists of News articles
                articles: list[Any] = []
                data_map = getattr(news_response, "data", news_response)
                if isinstance(data_map, dict):
                    for symbol_news in data_map.values():
                        if isinstance(symbol_news, list):
                            articles.extend(symbol_news)
                return [
                    {
                        "id": str(article.id),
                        "headline": article.headline,
                        "source": article.source,
                        "url": article.url,
                        "summary": article.summary or "",
                        "content": article.content or "",
                        "symbols": article.symbols,
                        "created_at": article.created_at,
                    }
                    for article in articles
                ]
            except Exception as exc:
                logger.warning(
                    "Alpaca news fetch failed for %s (attempt %d/%d)",
                    symbol,
                    attempt + 1,
                    retries,
                )
                if attempt == retries - 1 or not _is_transient_provider_error(exc):
                    raise
                time.sleep(delay)
                delay *= 2.0
        return []

    def get_stock_bars(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.Day,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve historical stock bars (OHLCV) from Alpaca Market API for a symbol."""
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            limit=limit,
            # Paper-only accounts are entitled to IEX equities data.  Leaving
            # the feed unset makes alpaca-py request SIP by default, which
            # correctly returns 403 for a Basic/paper account.
            feed=DataFeed.IEX,
        )

        retries = 3
        delay = 1.0
        for attempt in range(retries):
            try:
                bar_response = self.stocks.get_stock_bars(request_params)
                bars: list[Any] = []
                data_map = getattr(bar_response, "data", bar_response)
                if isinstance(data_map, dict):
                    symbol_bars = data_map.get(symbol, [])
                    if isinstance(symbol_bars, list):
                        bars.extend(symbol_bars)
                elif hasattr(bar_response, "__iter__"):
                    bars.extend(bar_response)

                return [
                    {
                        "timestamp": bar.timestamp,
                        "open": Decimal(str(bar.open)),
                        "high": Decimal(str(bar.high)),
                        "low": Decimal(str(bar.low)),
                        "close": Decimal(str(bar.close)),
                        "volume": bar.volume,
                        "trade_count": getattr(bar, "trade_count", None),
                        "vwap": (
                            Decimal(str(bar.vwap))
                            if getattr(bar, "vwap", None) is not None
                            else None
                        ),
                    }
                    for bar in bars
                ]
            except Exception as exc:
                logger.warning(
                    "Alpaca stock bars fetch failed for %s (attempt %d/%d): %s",
                    symbol,
                    attempt + 1,
                    retries,
                    type(exc).__name__,
                )
                if attempt == retries - 1 or not _is_transient_provider_error(exc):
                    raise
                time.sleep(delay)
                delay *= 2.0
        return []
