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
        self.inputs: dict[str, Any] = {
            "checkpoint": self._checkpoint.isoformat(),
            "bars": {},
            "news": {},
        }

    def get_stock_bars(self, symbol: str, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        requested_start = kwargs.pop("start", self._checkpoint - timedelta(days=730))
        requested_end = kwargs.pop("end", self._checkpoint)
        kwargs["start"] = requested_start
        kwargs["end"] = min(requested_end, self._checkpoint)
        rows = self._gateway.get_stock_bars(symbol, *args, **kwargs)
        filtered = [
            row
            for row in rows
            if isinstance(row.get("timestamp"), datetime)
            and row["timestamp"].tzinfo is not None
            and row["timestamp"].astimezone(UTC) <= self._checkpoint
        ]
        self.inputs["bars"][symbol] = filtered
        return filtered

    def get_news(self, symbol: str, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        requested_start = kwargs.pop("start", self._checkpoint - timedelta(days=30))
        kwargs["start"] = requested_start
        kwargs["end"] = self._checkpoint
        rows = self._gateway.get_news(symbol, *args, **kwargs)
        filtered = [
            row
            for row in rows
            if isinstance(row.get("created_at"), datetime)
            and row["created_at"].tzinfo is not None
            and row["created_at"].astimezone(UTC) <= self._checkpoint
        ]
        self.inputs["news"][symbol] = filtered
        return filtered
