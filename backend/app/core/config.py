from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: Literal["development", "test", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "postgresql+asyncpg://shadowfund:shadowfund@localhost:5432/shadowfund"
    redis_url: str | None = None
    alpaca_api_key: str | None = None
    alpaca_secret_key: str | None = None
    alpaca_paper: bool = True
    alpaca_live_trade: bool = False
    alpaca_cli_path: str = "alpaca"
    alpaca_cli_version: str = "0.0.13"
    alpaca_request_timeout_seconds: float = Field(default=30, gt=0, le=120)
    execution_enabled: bool = False
    execution_kill_switch: bool = True
    active_ruleset_version: str | None = None
    account_state_max_age_seconds: int = Field(default=30, gt=0, le=300)
    cors_allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:3005"]

    # AI / LLM Configuration (supports anthropic, gemini, ollama, deepseek, openai, featherless)
    llm_provider: str = "anthropic"
    llm_model: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    deepseek_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    featherless_api_key: str | None = None
    featherless_base_url: str = "https://api.featherless.ai/v1"

    # Seeded Authentication
    auth_email: str = "operator@prism.local"
    auth_password: str = "prism-development-only"
    auth_secret_key: str = "prism-development-only-session-secret-rotate"
    auth_session_expire_hours: int = Field(default=24, gt=0, le=720)

    @model_validator(mode="after")
    def enforce_paper_safety(self) -> Settings:
        if not self.alpaca_paper or self.alpaca_live_trade:
            raise ValueError("Live trading is prohibited; ALPACA_PAPER must remain true")
        key_present = bool(self.alpaca_api_key)
        secret_present = bool(self.alpaca_secret_key)
        if key_present != secret_present:
            raise ValueError("Alpaca credentials must be configured as a complete pair")
        if self.execution_enabled and not self.active_ruleset_version:
            raise ValueError("Execution requires ACTIVE_RULESET_VERSION")
        if self.environment in {"staging", "production"}:
            insecure_passwords = {
                "prism-development-only",
                "shadowfund2026!",
                "shadowfund-staging-2026!",
            }
            if self.auth_password in insecure_passwords or self.auth_password.startswith(
                ("your_", "replace-")
            ):
                raise ValueError("Staging and production require a non-example AUTH_PASSWORD")
            if len(self.auth_password) < 12:
                raise ValueError(
                    "Staging and production AUTH_PASSWORD must be at least 12 characters"
                )
            insecure_secrets = {
                "governed-shadowfund-paper-secret-key-change-in-production",
                "governed-shadowfund-staging-secret-key-change-in-staging",
                "prism-development-only-session-secret-rotate",
            }
            if self.auth_secret_key in insecure_secrets or self.auth_secret_key.startswith(
                ("your_", "replace-")
            ):
                raise ValueError("Staging and production require a non-example AUTH_SECRET_KEY")
            if len(self.auth_secret_key) < 32:
                raise ValueError(
                    "Staging and production AUTH_SECRET_KEY must be at least 32 characters"
                )
        return self

    @property
    def credentials_present(self) -> bool:
        return bool(self.alpaca_api_key and self.alpaca_secret_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
