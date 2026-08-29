from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from alpaca.data.historical.news import NewsClient
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import NewsRequest
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
