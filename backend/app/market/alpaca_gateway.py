from __future__ import annotations

from typing import Any

from alpaca.data.historical.news import NewsClient
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.trading.client import TradingClient

from app.core.config import Settings


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
