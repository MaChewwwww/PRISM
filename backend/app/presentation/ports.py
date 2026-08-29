from __future__ import annotations

import json
from datetime import UTC, datetime
from importlib.resources import files
from typing import Any, Protocol


class PresentationRepository(Protocol):
    """Replaceable read-model boundary for fixture, persisted, or provider adapters."""

    version: str
    as_of: datetime

    def snapshot(self) -> dict[str, Any]: ...


class FixturePresentationRepository:
    """Versioned local source used until persisted/provider repositories are authorized."""

    version = "prism-demo-v1"
    as_of = datetime(2026, 8, 28, 23, 59, 59, tzinfo=UTC)

    def snapshot(self) -> dict[str, Any]:
        resource = files("app.presentation.fixtures").joinpath("prism_demo_v1.json")
        value = json.loads(resource.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("presentation fixture must be an object")
        return value
