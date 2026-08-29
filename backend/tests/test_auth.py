from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.auth.token import create_access_token, verify_access_token
from app.core.config import Settings, get_settings
from app.main import app


def test_token_creation_and_verification() -> None:
    secret = "test-secret-key-12345"
    token = create_access_token("trader@prism.local", secret, expires_in_hours=1)
    payload = verify_access_token(token, secret)
    assert payload is not None
    assert payload["sub"] == "trader@prism.local"

    # Wrong secret fails
    assert verify_access_token(token, "wrong-secret") is None

    # Tampered token fails
    parts = token.split(".")
    tampered = f"{parts[0]}extra.{parts[1]}"
    assert verify_access_token(tampered, secret) is None


def test_token_expiration() -> None:
    secret = "test-secret-key-12345"
    # Create token that expired in the past
    token = create_access_token("trader@prism.local", secret, expires_in_hours=-1)
    assert verify_access_token(token, secret) is None


def test_auth_login_success() -> None:
    settings = Settings(
        _env_file=None,
        auth_email="custom@prism.local",
        auth_password="correct-password-99",
        auth_secret_key="custom-secret",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        res = client.post(
            "/api/v1/auth/login",
            json={"email": " CUSTOM@prism.local ", "password": "correct-password-99"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == "custom@prism.local"
        assert "token" not in data
        assert "expires_at" in data
        assert "prism_session" in res.cookies
    app.dependency_overrides.clear()


def test_auth_login_invalid_credentials() -> None:
    settings = Settings(_env_file=None)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        # Invalid password
        res = client.post(
            "/api/v1/auth/login",
            json={"email": settings.auth_email, "password": "wrong-password"},
        )
        assert res.status_code == 401
        assert res.json()["detail"] == "Invalid email or password"

        # Invalid email
        res = client.post(
            "/api/v1/auth/login",
            json={"email": "intruder@domain.com", "password": settings.auth_password},
        )
        assert res.status_code == 401
    app.dependency_overrides.clear()


def test_auth_me_bearer_and_cookie() -> None:
    settings = Settings(_env_file=None, auth_secret_key="my-key")
    app.dependency_overrides[get_settings] = lambda: settings
    token = create_access_token(
        "operator@prism.local", settings.auth_secret_key, expires_in_hours=1
    )

    with TestClient(app) as client:
        # No auth
        assert client.get("/api/v1/auth/me").status_code == 401

        # Bearer header
        res_bearer = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_bearer.status_code == 200
        assert res_bearer.json() == {"email": "operator@prism.local", "authenticated": True}

        # Cookie
        client.cookies.set("prism_session", token)
        res_cookie = client.get("/api/v1/auth/me")
        assert res_cookie.status_code == 200
        assert res_cookie.json() == {"email": "operator@prism.local", "authenticated": True}
    app.dependency_overrides.clear()


def test_auth_logout() -> None:
    settings = Settings(_env_file=None)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        res = client.post("/api/v1/auth/logout")
        assert res.status_code == 200
        assert res.json() == {"status": "logged_out"}
    app.dependency_overrides.clear()
