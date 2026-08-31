from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_frs_006_rejects_live_mode() -> None:
    with pytest.raises(ValidationError, match="Live trading is prohibited"):
        Settings(_env_file=None, alpaca_paper=False)


def test_frs_006_rejects_partial_credentials() -> None:
    with pytest.raises(ValidationError, match="complete pair"):
        Settings(_env_file=None, alpaca_api_key="key")


def test_frs_010_execution_requires_active_ruleset() -> None:
    with pytest.raises(ValidationError, match="ACTIVE_RULESET_VERSION"):
        Settings(_env_file=None, execution_enabled=True, execution_kill_switch=False)


def test_autonomous_trading_defaults_to_disabled_without_a_schedule() -> None:
    settings = Settings(_env_file=None)

    assert settings.autonomous_trading_enabled is False
    assert settings.autonomous_trading_start_at is None
    assert settings.autonomous_trading_end_at is None
    assert settings.autonomous_trading_window_active(datetime.now(UTC)) is False


def test_autonomous_trading_requires_explicit_execution_and_schedule() -> None:
    with pytest.raises(ValidationError, match="requires EXECUTION_ENABLED"):
        Settings(
            _env_file=None,
            autonomous_trading_enabled=True,
            alpaca_api_key="paper-key",
            alpaca_secret_key="paper-secret",
        )

    with pytest.raises(ValidationError, match="requires a UTC start and end time"):
        Settings(
            _env_file=None,
            autonomous_trading_enabled=True,
            execution_enabled=True,
            active_ruleset_version="1.0.0",
            alpaca_api_key="paper-key",
            alpaca_secret_key="paper-secret",
        )


def test_staging_rejects_autonomous_trading() -> None:
    common = {
        "_env_file": None,
        "environment": "staging",
        "auth_password": "staging-password-123",
        "auth_secret_key": "s" * 32,
        "autonomous_trading_enabled": True,
        "execution_enabled": True,
        "active_ruleset_version": "1.0.0",
        "alpaca_api_key": "paper-key",
        "alpaca_secret_key": "paper-secret",
        "autonomous_trading_start_at": "2026-08-29T00:00:00Z",
        "autonomous_trading_end_at": "2026-08-30T00:00:00Z",
    }
    with pytest.raises(ValidationError, match="Staging autonomous trading is prohibited"):
        Settings(**common)


def test_production_autonomous_trading_window_is_bounded_by_authorized_hackathon_window() -> None:
    production = {
        "_env_file": None,
        "environment": "production",
        "auth_password": "production-password-123",
        "auth_secret_key": "p" * 32,
        "autonomous_trading_enabled": True,
        "execution_enabled": True,
        "active_ruleset_version": "1.0.0",
        "alpaca_api_key": "paper-key",
        "alpaca_secret_key": "paper-secret",
        "autonomous_trading_start_at": "2026-08-30T13:30:00Z",
        "autonomous_trading_end_at": "2026-09-03T20:00:00Z",
    }
    with pytest.raises(ValidationError, match="within the BA-authorized hackathon window"):
        Settings(**production)

    production["autonomous_trading_start_at"] = "2026-08-31T13:30:00Z"
    settings = Settings(**production)
    assert settings.autonomous_trading_window_active(datetime(2026, 9, 1, tzinfo=UTC)) is True
    assert settings.autonomous_trading_window_active(datetime(2026, 9, 3, 20, tzinfo=UTC)) is False


def test_llm_configuration_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.llm_provider == "featherless"
    assert settings.llm_model is None
    assert settings.anthropic_api_key is None
    assert settings.gemini_api_key is None
    assert settings.openai_api_key is None
    assert settings.deepseek_api_key is None
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.featherless_api_key is None
    assert settings.featherless_base_url == "https://api.featherless.ai/v1"
    assert settings.auth_email == "operator@prism.local"
    assert settings.auth_password == "prism-development-only"
    assert settings.auth_session_expire_hours == 24


def test_staging_rejects_example_authentication_secrets() -> None:
    with pytest.raises(ValidationError, match="non-example AUTH_PASSWORD"):
        Settings(_env_file=None, environment="staging")


def test_staging_shadowfund_requires_explicit_backtest_boundary() -> None:
    with pytest.raises(ValidationError, match="Staging ShadowFund requires"):
        Settings(
            _env_file=None,
            environment="staging",
            auth_password="staging-password-123",
            auth_secret_key="s" * 32,
            shadowfund_enabled=True,
        )

    settings = Settings(
        _env_file=None,
        environment="staging",
        auth_password="staging-password-123",
        auth_secret_key="s" * 32,
        shadowfund_enabled=True,
        backtest_simulation_enabled=True,
    )
    assert settings.shadowfund_enabled is True
