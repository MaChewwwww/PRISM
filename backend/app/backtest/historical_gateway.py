"""Point-in-time, read-only inputs for the staging AI replay."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.market.alpaca_gateway import AlpacaPyGateway

# Alpaca returns ascending rows.  A small limit over a long lookback therefore
# selects the oldest observations, which can leave strict replay evidence stale
# even though newer bars exist in the requested range.
REPLAY_BAR_LIMIT = 1000


class HistoricalResearchGateway:
    """Expose only market/news observations available at one replay checkpoint."""

    def __init__(
        self,
        gateway: AlpacaPyGateway,
        *,
        checkpoint: datetime,
        require_checkpoint_data: bool = False,
    ) -> None:
        self._gateway = gateway
        self._checkpoint = checkpoint.astimezone(UTC)
        self._require_checkpoint_data = require_checkpoint_data
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
        requested_limit_int = int(requested_limit) if requested_limit is not None else None
        cached = self._bars_cache.get(normalized_symbol)
        if cached is not None and (
            requested_limit_int is None or len(cached) >= requested_limit_int
        ):
            self.inputs["bars"][normalized_symbol] = cached
            self._ensure_checkpoint_coverage(normalized_symbol, cached)
            return (
                cached
                if requested_limit_int is None
                else cached[-requested_limit_int:]
                if requested_limit_int > 0
                else []
            )
        requested_start = kwargs.pop("start", self._checkpoint - timedelta(days=730))
        requested_end = kwargs.pop("end", self._checkpoint)
        kwargs["start"] = requested_start
        kwargs["end"] = min(requested_end, self._checkpoint)
        if self._require_checkpoint_data:
            kwargs["limit"] = max(requested_limit_int or 0, REPLAY_BAR_LIMIT)
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
        self._ensure_checkpoint_coverage(normalized_symbol, filtered)
        return (
            filtered
            if requested_limit_int is None
            else filtered[-requested_limit_int:]
            if requested_limit_int > 0
            else []
        )

    def _ensure_checkpoint_coverage(self, symbol: str, rows: list[dict[str, Any]]) -> None:
        if self._require_checkpoint_data and not any(
            row["timestamp"].astimezone(UTC).date() == self._checkpoint.date() for row in rows
        ):
            raise ValueError(f"Historical bars do not reach checkpoint for {symbol}")

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
