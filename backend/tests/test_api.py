from fastapi.testclient import TestClient

from app.api import routes as api_routes
from app.api.routes import get_database_readiness
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.main import app


def test_frs_015_public_endpoints_and_redacted_status() -> None:
    settings = Settings(_env_file=None, alpaca_cli_path="definitely-not-installed")
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_database_readiness] = lambda: True
    with TestClient(app) as client:
        assert client.get("/api/v1/health/live").json() == {"status": "ok"}
        assert client.get("/api/v1/health/ready").json() == {"status": "ready"}
        assert client.get("/openapi.json").status_code == 200

        # Unauthenticated request to /system/status fails closed with 401
        unauth_response = client.get("/api/v1/system/status")
        assert unauth_response.status_code == 401
        assert client.get("/api/v1/autonomous/status").status_code == 401
        assert (
            client.post(
                "/api/v1/autonomous/kill-switch", json={"active": True, "reason": "test"}
            ).status_code
            == 401
        )

        # Login to obtain session cookie
        login_res = client.post(
            "/api/v1/auth/login",
            json={"email": settings.auth_email, "password": settings.auth_password},
        )
        assert login_res.status_code == 200
        data = login_res.json()
        assert data["email"] == settings.auth_email
        assert "token" not in data

        # Authenticated request to /system/status succeeds
        payload = client.get("/api/v1/system/status").json()
        assert payload["state"] == "degraded"
        assert payload["paper_mode"] is True
        serialized = str(payload).lower()
        assert "api_key" not in serialized
        assert "secret" not in serialized
    app.dependency_overrides.clear()


def test_autonomous_read_endpoints_require_authentication_and_return_empty_read_models() -> None:
    class EmptyRows:
        def all(self) -> list[object]:
            return []

    class EmptySession:
        async def scalars(self, _statement: object) -> EmptyRows:
            return EmptyRows()

        async def scalar(self, _statement: object) -> None:
            return None

    async def empty_session() -> EmptySession:
        yield EmptySession()

    settings = Settings(_env_file=None, alpaca_cli_path="definitely-not-installed")
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_database_readiness] = lambda: True
    app.dependency_overrides[get_db_session] = empty_session
    range_params = {"from": "2026-08-31T00:00:00Z", "to": "2026-08-31T23:59:59Z"}
    with TestClient(app) as client:
        for path in (
            "/api/v1/autonomous/cycles",
            "/api/v1/autonomous/decisions",
            "/api/v1/autonomous/executions",
            "/api/v1/autonomous/portfolio/latest",
        ):
            response = client.get(path, params=range_params)
            assert response.status_code == 401

        login_res = client.post(
            "/api/v1/auth/login",
            json={"email": settings.auth_email, "password": settings.auth_password},
        )
        assert login_res.status_code == 200

        for path in (
            "/api/v1/autonomous/cycles",
            "/api/v1/autonomous/decisions",
            "/api/v1/autonomous/executions",
        ):
            response = client.get(path, params=range_params)
            assert response.status_code == 200, response.text
            assert response.json()["items"] == []
            assert response.json()["empty_message"]

        portfolio = client.get("/api/v1/autonomous/portfolio/latest")
        assert portfolio.status_code == 200
        assert portfolio.json()["snapshot"] is None
        assert portfolio.json()["empty_message"]

        reversed_range = client.get(
            "/api/v1/autonomous/cycles",
            params={"from": range_params["to"], "to": range_params["from"]},
        )
        assert reversed_range.status_code == 422
        assert (
            client.get(
                "/api/v1/autonomous/executions", params={**range_params, "status": "raw"}
            ).status_code
            == 422
        )
    app.dependency_overrides.clear()


def test_system_status_reports_redacted_paper_account_capability(monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        execution_enabled=True,
        active_ruleset_version="1.0.0",
        alpaca_api_key="test-key",
        alpaca_secret_key="test-secret",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(api_routes, "cli_status", lambda _settings: (True, "0.0.13"))
    monkeypatch.setattr(api_routes, "paper_account_status", lambda _settings: (True, 3))

    with TestClient(app) as client:
        login_res = client.post(
            "/api/v1/auth/login",
            json={"email": settings.auth_email, "password": settings.auth_password},
        )
        assert login_res.status_code == 200
        payload = client.get("/api/v1/system/status").json()

    assert payload["state"] == "ready"
    assert payload["account_verified"] is True
    assert payload["supported_options_level"] == 3
    assert "account_number" not in str(payload).lower()
    app.dependency_overrides.clear()
