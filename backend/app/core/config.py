from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
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
    autonomous_trading_enabled: bool = False
    autonomous_trading_start_at: datetime | None = None
    autonomous_trading_end_at: datetime | None = None
    autonomous_symbol_allowlist: list[str] = [
        "NVDA",
        "TSLA",
        "AAPL",
        "MSFT",
        "AMD",
        "GOOGL",
        "AMZN",
    ]
    autonomous_scan_interval_seconds: int = Field(default=900, gt=0, le=3600)
    autonomous_max_open_positions: int = Field(default=6, gt=0, le=6)
    account_state_max_age_seconds: int = Field(default=30, gt=0, le=300)
    # Optional server-side historical IV provider.  Alpaca's chain supplies
    # current IV/Greeks but not an IV-rank time series; when this URL is not
    # configured PRISM uses only its own durable observations and fails closed
    # until enough timestamped history exists.
    iv_rank_history_url: str | None = None
    iv_rank_history_api_key: str | None = None
    iv_rank_lookback_days: int = Field(default=252, ge=30, le=1825)
    iv_rank_min_observations: int = Field(default=20, ge=2, le=5000)
    cors_allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:3005"]

    # AI / LLM Configuration (providers implemented by LLMGateway)
    llm_provider: str = "featherless"
    llm_model: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    deepseek_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    featherless_api_key: str | None = None
    featherless_base_url: str = "https://api.featherless.ai/v1"
    sec_user_agent: str = "PRISM autonomous research contact: operator@prism.local"

    # Seeded Authentication
    auth_email: str = "operator@prism.local"
    auth_password: str = "prism-development-only"
    auth_secret_key: str = "prism-development-only-session-secret-rotate"
    auth_session_expire_hours: int = Field(default=24, gt=0, le=720)

    @field_validator("autonomous_trading_start_at", "autonomous_trading_end_at")
    @classmethod
    def require_utc_autonomous_window_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("autonomous trading window timestamps must be timezone-aware UTC")
        return value.astimezone(UTC)

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
        window_is_partial = (self.autonomous_trading_start_at is None) != (
            self.autonomous_trading_end_at is None
        )
        if window_is_partial:
            raise ValueError(
                "AUTONOMOUS_TRADING_START_AT and AUTONOMOUS_TRADING_END_AT "
                "must be configured together"
            )
        if (
            self.autonomous_trading_start_at is not None
            and self.autonomous_trading_end_at is not None
            and self.autonomous_trading_start_at >= self.autonomous_trading_end_at
        ):
            raise ValueError("AUTONOMOUS_TRADING_START_AT must precede AUTONOMOUS_TRADING_END_AT")
        if self.autonomous_trading_enabled:
            if not self.execution_enabled:
                raise ValueError("AUTONOMOUS_TRADING_ENABLED requires EXECUTION_ENABLED")
            if not self.credentials_present:
                raise ValueError("AUTONOMOUS_TRADING_ENABLED requires Alpaca paper credentials")
            if self.autonomous_trading_start_at is None or self.autonomous_trading_end_at is None:
                raise ValueError("AUTONOMOUS_TRADING_ENABLED requires a UTC start and end time")
            # Import lazily to keep settings independent from the rules module at import time.
            from app.rules.registry import get_authorized_ruleset

            if self.environment == "production":
                hackathon_window = get_authorized_ruleset().parameters.hackathon_window
                if (
                    self.autonomous_trading_start_at < hackathon_window.trading_start_at
                    or self.autonomous_trading_end_at > hackathon_window.force_flatten_by
                ):
                    raise ValueError(
                        "Production autonomous trading window must remain within the "
                        "BA-authorized hackathon window"
                    )
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
        normalized_symbols = [symbol.strip().upper() for symbol in self.autonomous_symbol_allowlist]
        if not normalized_symbols or any(not symbol for symbol in normalized_symbols):
            raise ValueError("AUTONOMOUS_SYMBOL_ALLOWLIST must contain at least one symbol")
        if len(set(normalized_symbols)) != len(normalized_symbols):
            raise ValueError("AUTONOMOUS_SYMBOL_ALLOWLIST must not contain duplicates")
        self.autonomous_symbol_allowlist = normalized_symbols
        return self

    def autonomous_trading_window_active(self, now: datetime | None = None) -> bool:
        """Return whether the explicitly enabled autonomous window is currently open."""
        if not self.autonomous_trading_enabled:
            return False
        if self.autonomous_trading_start_at is None or self.autonomous_trading_end_at is None:
            return False
        current_time = now or datetime.now(UTC)
        if current_time.tzinfo is None or current_time.utcoffset() is None:
            return False
        current_time = current_time.astimezone(UTC)
        return self.autonomous_trading_start_at <= current_time < self.autonomous_trading_end_at

    @property
    def credentials_present(self) -> bool:
        return bool(self.alpaca_api_key and self.alpaca_secret_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
