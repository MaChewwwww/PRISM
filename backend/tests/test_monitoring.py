from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.autonomous.models import AuthorizationModel
from app.core.config import Settings, get_settings
from app.main import app
from app.monitoring.service import _summary
from app.rules.registry import get_authorized_ruleset

FROM = "2026-07-29T00:00:00Z"
TO = "2026-08-28T23:59:59Z"


def _login(client: TestClient, settings: Settings) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": settings.auth_email, "password": settings.auth_password},
    )
    assert response.status_code == 200


def test_authorized_ruleset_matches_balanced_day_one_baseline() -> None:
    ruleset = get_authorized_ruleset()
    assert ruleset.status == "active"
    assert str(ruleset.profiles["balanced"].target_position_size_pct) == "2.00"
    assert str(ruleset.profiles["balanced"].opportunity_score_threshold) == "78"
    assert str(ruleset.profiles["balanced"].take_profit_pct) == "75.00"
    assert str(ruleset.profiles["balanced"].stop_loss_pct) == "50.00"


def test_authorization_summary_uses_recorded_shadow_symbol_when_proposal_is_missing() -> None:
    row = AuthorizationModel(
        proposal_id="orphan-proposal",
        created_at=datetime(2026, 8, 31, 17, 10, 24, tzinfo=UTC),
        outcome="APPROVE",
    )

    summary = _summary(row, fallback_symbol="NVDA")

    assert summary.symbol == "NVDA"
    assert summary.title == "NVDA Approve"
    assert "proposal payload unavailable" in summary.summary


def test_monitoring_routes_require_authentication_and_presentation_routes_are_absent() -> None:
    settings = Settings(_env_file=None)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        response = client.get("/api/v1/monitoring/overview", params={"from": FROM, "to": TO})
        assert response.status_code == 401
        _login(client, settings)
        removed = client.get("/api/v1/presentation/overview", params={"from": FROM, "to": TO})
        assert removed.status_code == 404
    app.dependency_overrides.clear()


def test_monitoring_range_rejects_naive_or_reversed_timestamps_before_read_model_access() -> None:
    settings = Settings(_env_file=None)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        _login(client, settings)
        naive = client.get(
            "/api/v1/monitoring/overview",
            params={"from": "2026-08-01T00:00:00", "to": TO},
        )
        assert naive.status_code == 422
        reversed_range = client.get(
            "/api/v1/monitoring/overview",
            params={"from": TO, "to": FROM},
        )
        assert reversed_range.status_code == 422
    app.dependency_overrides.clear()
