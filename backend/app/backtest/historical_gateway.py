"""Point-in-time, read-only inputs for the staging AI replay."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.market.alpaca_gateway import AlpacaPyGateway


class HistoricalResearchGateway:
    """Expose only market/news observations available at one replay checkpoint."""

    def __init__(self, gateway: AlpacaPyGateway, *, checkpoint: datetime) -> None:
        self._gateway = gateway
        self._checkpoint = checkpoint.astimezone(UTC)
        self._bars_cache: dict[str, list[dict[str, Any]]] = {}
        self._news_cache: dict[str, list[dict[str, Any]]] = {}
        self.inputs: dict[str, Any] = {
            "checkpoint": self._checkpoint.isoformat(),
            "bars": {},
            "news": {},
            "fundamentals": {},
        }

    def get_stock_bars(self, symbol: str, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        normalized_symbol = symbol.strip().upper()
        requested_limit = kwargs.get("limit")
        cached = self._bars_cache.get(normalized_symbol)
        if cached is not None and (requested_limit is None or len(cached) >= int(requested_limit)):
            self.inputs["bars"][normalized_symbol] = cached
            return cached
        requested_start = kwargs.pop("start", self._checkpoint - timedelta(days=730))
        requested_end = kwargs.pop("end", self._checkpoint)
        kwargs["start"] = requested_start
        kwargs["end"] = min(requested_end, self._checkpoint)
        rows = self._gateway.get_stock_bars(normalized_symbol, *args, **kwargs)
        filtered = [
            row
            for row in rows
            if isinstance(row.get("timestamp"), datetime)
            and row["timestamp"].tzinfo is not None
            and row["timestamp"].astimezone(UTC) <= self._checkpoint
        ]
        filtered.sort(key=lambda row: row["timestamp"].astimezone(UTC))
        self._bars_cache[normalized_symbol] = filtered
        self.inputs["bars"][normalized_symbol] = filtered
        return filtered

    def get_news(self, symbol: str, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        normalized_symbol = symbol.strip().upper()
        requested_limit = kwargs.get("limit")
        cached = self._news_cache.get(normalized_symbol)
        if cached is not None and (requested_limit is None or len(cached) >= int(requested_limit)):
            self.inputs["news"][normalized_symbol] = cached
            return cached
        requested_start = kwargs.pop("start", self._checkpoint - timedelta(days=30))
        kwargs["start"] = requested_start
        kwargs["end"] = self._checkpoint
        rows = self._gateway.get_news(normalized_symbol, *args, **kwargs)
        filtered = [
            row
            for row in rows
            if isinstance(row.get("created_at"), datetime)
            and row["created_at"].tzinfo is not None
            and row["created_at"].astimezone(UTC) <= self._checkpoint
        ]
        filtered.sort(key=lambda row: row["created_at"].astimezone(UTC), reverse=True)
        self._news_cache[normalized_symbol] = filtered
        self.inputs["news"][normalized_symbol] = filtered
        return filtered
