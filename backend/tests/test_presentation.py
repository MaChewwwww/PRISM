from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from app.presentation.ports import FixturePresentationRepository
from app.rules.registry import get_authorized_ruleset

FROM = "2026-07-29T00:00:00Z"
TO = "2026-08-28T23:59:59Z"


def _login(client: TestClient, settings: Settings) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": settings.auth_email, "password": settings.auth_password},
    )
    assert response.status_code == 200


def test_authorized_ruleset_matches_ba_baseline() -> None:
    ruleset = get_authorized_ruleset()
    assert ruleset.status == "active"
    assert str(ruleset.parameters.take_profit_default_pct) == "75.00"
    assert str(ruleset.parameters.stop_loss_pct) == "50.00"
    assert ruleset.parameters.data_freshness_seconds == 30
    assert ruleset.parameters.max_hold_default_days == 14
    assert ruleset.parameters.hackathon_max_hold_trading_days == 4
    window = ruleset.parameters.hackathon_window
    assert window.trading_start_at.isoformat() == "2026-08-31T13:30:00+00:00"
    assert window.new_entry_cutoff_at.isoformat() == "2026-09-02T20:00:00+00:00"
    assert window.official_scoring_at == window.force_flatten_by
    assert window.window_outer_boundary_at.isoformat() == "2026-09-04T13:30:00+00:00"
    assert window.scoring_basis == "total_account_equity"
    assert str(ruleset.profiles["balanced"].opportunity_score_threshold) == "78"


def test_fixture_repository_exposes_replaceable_read_boundary() -> None:
    repository = FixturePresentationRepository()
    assert repository.version == "prism-demo-v1"
    assert repository.as_of.tzinfo is not None
    assert repository.snapshot()["stories"]


def test_presentation_endpoints_are_authenticated_and_fixture_labeled() -> None:
    settings = Settings(_env_file=None)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        unauthenticated = client.get(
            "/api/v1/presentation/overview", params={"from": FROM, "to": TO}
        )
        assert unauthenticated.status_code == 401

        _login(client, settings)
        ranged_paths = (
            "/api/v1/presentation/overview",
            "/api/v1/presentation/decisions",
            "/api/v1/presentation/portfolio",
            "/api/v1/presentation/alternatives",
            "/api/v1/presentation/news",
            "/api/v1/presentation/agents",
        )
        detail_paths = (
            "/api/v1/presentation/decisions/acme-earnings-gap",
            "/api/v1/presentation/alternatives/session-acme-earnings",
            "/api/v1/presentation/agents/news-intelligence",
            "/api/v1/presentation/governance",
            "/api/v1/presentation/weekly-summary",
        )
        for path in ranged_paths:
            response = client.get(path, params={"from": FROM, "to": TO})
            assert response.status_code == 200, response.text
            payload = response.json()
            assert payload["meta"]["dataMode"] == "illustrative_fixture"
            assert payload["meta"]["fixtureVersion"] == "prism-demo-v1"
            serialized = response.text.lower()
            assert "alpaca paper trading account" not in serialized
            assert "active portfolio (paper)" not in serialized
        for path in detail_paths:
            response = client.get(path)
            assert response.status_code == 200, response.text
            payload = response.json()
            assert payload["meta"]["dataMode"] == "illustrative_fixture"
            assert payload["meta"]["fixtureVersion"] == "prism-demo-v1"
            serialized = response.text.lower()
            assert "alpaca paper trading account" not in serialized
            assert "active portfolio (paper)" not in serialized
    app.dependency_overrides.clear()


def test_presentation_decision_and_agent_topology() -> None:
    settings = Settings(_env_file=None)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        _login(client, settings)
        decision = client.get("/api/v1/presentation/decisions/acme-earnings-gap")
        assert decision.status_code == 200
        actors = [node["actor"] for node in decision.json()["data"]["decisionTree"]]
        assert actors[:7] == [
            "News Agent",
            "Quantitative Agent",
            "Industry Agent",
            "Fundamental Agent",
            "Macroeconomic Agent",
            "Market Reaction/Mispricing Agent",
            "Trading Decision Agent",
        ]
        assert "Deterministic Rules Engine" not in actors
        assert "Rules Engine" in actors

        agents = client.get("/api/v1/presentation/agents", params={"from": FROM, "to": TO}).json()[
            "data"
        ]
        assert len(agents["agents"]) == 9
        assert len([agent for agent in agents["agents"] if agent["stage"] <= 7]) == 7
        rules = next(item for item in agents["components"] if item["id"] == "rules-engine")
        assert rules["authority"] == "Sole execution authorization"
    app.dependency_overrides.clear()


def test_governance_and_weekly_recommendations_are_bounded_and_manual() -> None:
    settings = Settings(_env_file=None)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        _login(client, settings)
        governance = client.get("/api/v1/presentation/governance").json()["data"]
        assert governance["activeProfile"] == "balanced"
        values = {item["id"]: item["activeValue"] for item in governance["profileParameters"]}
        assert values["take_profit_pct"] == "75.00"
        assert values["stop_loss_pct"] == "50.00"
        window = governance["hackathonWindow"]
        assert window["newEntryCutoffAt"] == "2026-09-02T20:00:00Z"
        assert window["officialScoringAt"] == "2026-09-03T20:00:00Z"
        assert window["forceFlattenBy"] == window["officialScoringAt"]
        assert window["scoringBasis"] == "total_account_equity"

        summary = client.get("/api/v1/presentation/weekly-summary").json()["data"]
        assert summary["suggestions"]
        assert all(item["manualReviewRequired"] for item in summary["suggestions"])
        assert all(
            item["validationState"] == "within_authorized_bounds" for item in summary["suggestions"]
        )
    app.dependency_overrides.clear()


def test_presentation_range_rejects_naive_or_reversed_timestamps() -> None:
    settings = Settings(_env_file=None)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        _login(client, settings)
        naive = client.get(
            "/api/v1/presentation/overview",
            params={"from": "2026-08-01T00:00:00", "to": TO},
        )
        assert naive.status_code == 422
        reversed_range = client.get(
            "/api/v1/presentation/overview",
            params={"from": TO, "to": FROM},
        )
        assert reversed_range.status_code == 422
    app.dependency_overrides.clear()
