from __future__ import annotations

import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Any

from alpaca.data.historical.news import NewsClient
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import NewsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient

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
        key = settings.alpaca_api_key or ""
        secret = settings.alpaca_secret_key or ""
        self.trading = TradingClient(key, secret, paper=True)
        self.stocks = StockHistoricalDataClient(key, secret)
        self.options = OptionHistoricalDataClient(key, secret)
        self.news = NewsClient(key, secret)

    def get_account(self) -> Any:
        return self.trading.get_account()

    def get_asset(self, symbol: str) -> Any:
        return self.trading.get_asset(symbol)

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
