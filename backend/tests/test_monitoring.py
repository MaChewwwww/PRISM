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
    assert str(ruleset.parameters.profit_arm_pct) == "20.00"
    assert str(ruleset.parameters.hard_take_profit_pct) == "40.00"
    assert str(ruleset.parameters.hard_stop_loss_pct) == "50.00"


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


def test_monitoring_and_presentation_alternatives_routes_require_authentication() -> None:
    settings = Settings(_env_file=None)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        response = client.get("/api/v1/monitoring/overview", params={"from": FROM, "to": TO})
        assert response.status_code == 401
        presentation_unauthenticated = client.get(
            "/api/v1/presentation/alternatives", params={"from": FROM, "to": TO}
        )
        assert presentation_unauthenticated.status_code == 401
        _login(client, settings)
        alternatives = client.get("/api/v1/presentation/alternatives")
        assert alternatives.status_code == 422
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


def test_market_bars_route_returns_valid_bars_and_metrics() -> None:
    settings = Settings(_env_file=None)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        _login(client, settings)
        response = client.get(
            "/api/v1/monitoring/market-bars",
            params={"symbol": "NVDA", "timeframe": "1Day", "limit": 30},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["data"]["symbol"] == "NVDA"
        assert payload["data"]["timeframe"] == "1Day"
        assert len(payload["data"]["bars"]) == 30
        assert payload["data"]["latestPrice"].startswith("$")
        assert "changePct" in payload["data"]
        assert payload["data"]["volume"] > 0
    app.dependency_overrides.clear()


def test_governance_route_returns_populated_hard_rules() -> None:
    class EmptySession:
        async def scalar(self, _statement: object) -> None:
            return None

    async def empty_session():
        yield EmptySession()

    from app.core.database import get_db_session

    settings = Settings(_env_file=None)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db_session] = empty_session
    with TestClient(app) as client:
        _login(client, settings)
        response = client.get("/api/v1/monitoring/governance")
        assert response.status_code == 200
        payload = response.json()
        hard_rules = payload["data"]["hardRules"]
        assert len(hard_rules) >= 15
        rule_ids = {r["ruleId"] for r in hard_rules}
        assert "P0-PAPER-ONLY" in rule_ids
        assert "P0-DATA-FRESHNESS" in rule_ids
        assert "P0-DRAWDOWN" in rule_ids
        assert "P0-CASH-BUFFER" in rule_ids
        assert "P1-TICKER-CAP" in rule_ids
        assert "P2-RISK-PER-TRADE" in rule_ids
        assert "P3-EXIT" in rule_ids
    app.dependency_overrides.clear()


def test_agents_route_returns_canonical_roster() -> None:
    class EmptyRows:
        def all(self) -> list[object]:
            return []

    class EmptySession:
        async def scalars(self, _statement: object) -> EmptyRows:
            return EmptyRows()

    async def empty_session():
        yield EmptySession()

    from app.core.database import get_db_session

    settings = Settings(_env_file=None)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db_session] = empty_session
    with TestClient(app) as client:
        _login(client, settings)
        response = client.get("/api/v1/monitoring/agents", params={"from": FROM, "to": TO})
        assert response.status_code == 200
        payload = response.json()
        agents = payload["data"]["agents"]
        agent_ids = [a["id"] for a in agents]
        assert "decision" in agent_ids
        assert "quant" in agent_ids
        assert "news" in agent_ids
        assert "fundamental" in agent_ids
        assert "macro" in agent_ids
        assert "reaction" in agent_ids
        assert "industry" in agent_ids

        single_res = client.get(
            "/api/v1/monitoring/agents/decision", params={"from": FROM, "to": TO}
        )
        assert single_res.status_code == 200
        single_alias = client.get(
            "/api/v1/monitoring/agents/trading-decision", params={"from": FROM, "to": TO}
        )
        assert single_alias.status_code == 200
    app.dependency_overrides.clear()
