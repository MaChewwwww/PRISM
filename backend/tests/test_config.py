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


def test_llm_configuration_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.llm_provider == "anthropic"
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
