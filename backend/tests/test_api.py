from fastapi.testclient import TestClient

from app.api.routes import get_database_readiness
from app.core.config import Settings, get_settings
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
