from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings
from app.observability.usage import record_llm_usage


class LLMError(Exception):
    """Base exception for LLM provider errors."""


class LLMConfigurationError(LLMError):
    """Raised when provider configuration or API keys are missing."""


class LLMValidationError(LLMError):
    """Raised when model response fails strict Pydantic contract validation."""


class LLMNetworkError(LLMError):
    """Raised on connection timeout or network failure."""


@dataclass(frozen=True)
class LLMCompletionResult[T: BaseModel]:
    raw_content: str
    parsed: T | None
    raw_digest: str
    model: str
    provider: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    latency_ms: int
    trace_id: UUID


DEFAULT_SYSTEM_PROMPT = (
    "You are a specialized financial analysis and structured reasoning agent for PRISM. "
    "Output strictly valid JSON matching the schema."
)


_shared_client: httpx.AsyncClient | None = None


def _get_shared_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )
    return _shared_client


class LLMGateway:
    """Provider-neutral gateway for LLM completions with structured contract validation.

    Supported providers: featherless, openai, deepseek, ollama.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client

    def _resolve_provider_endpoint(self, provider: str) -> tuple[str, str | None, str]:
        """Resolve base URL, API key, and default model for the active provider."""
        prov = provider.lower()
        if prov == "featherless":
            if not self._settings.featherless_api_key:
                raise LLMConfigurationError(
                    "FEATHERLESS_API_KEY is required when LLM_PROVIDER=featherless"
                )
            base_url = self._settings.featherless_base_url.rstrip("/")
            default_model = "deepseek-ai/DeepSeek-V4-Flash-0731"
            return f"{base_url}/chat/completions", self._settings.featherless_api_key, default_model
        elif prov == "openai":
            if not self._settings.openai_api_key:
                raise LLMConfigurationError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
            return (
                "https://api.openai.com/v1/chat/completions",
                self._settings.openai_api_key,
                "gpt-4o",
            )
        elif prov == "deepseek":
            if not self._settings.deepseek_api_key:
                raise LLMConfigurationError(
                    "DEEPSEEK_API_KEY is required when LLM_PROVIDER=deepseek"
                )
            return (
                "https://api.deepseek.com/v1/chat/completions",
                self._settings.deepseek_api_key,
                "deepseek-chat",
            )
        elif prov == "ollama":
            base_url = self._settings.ollama_base_url.rstrip("/")
            return f"{base_url}/v1/chat/completions", None, "llama3.1"
        else:
            raise LLMConfigurationError(f"Unsupported or unimplemented LLM provider: '{provider}'")

    async def complete_structured[T: BaseModel](
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        model: str | None = None,
        temperature: float = 0.0,
        trace_id: UUID | None = None,
        timeout_seconds: float = 30.0,
        max_tokens: int | None = None,
    ) -> LLMCompletionResult[T]:
        """Execute a completion with strict Pydantic response validation and SHA256 audit digest."""
        resolved_trace_id = trace_id or uuid4()
        provider = self._settings.llm_provider
        endpoint, api_key, default_model = self._resolve_provider_endpoint(provider)
        target_model = model or self._settings.llm_model or default_model

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "PRISM-AgenticMonolith/1.0",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        schema_json = json.dumps(response_model.model_json_schema())
        augmented_system_prompt = (
            f"{system_prompt}\n\n"
            f"You MUST respond ONLY with a valid JSON object conforming to this schema:\n"
            f"{schema_json}\n"
            f"Do NOT include markdown fences, backticks, reasoning tokens, or extra text."
        )

        payload: dict[str, Any] = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": augmented_system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        start_time = time.perf_counter()
        try:
            client = self._client or _get_shared_client()
            response = await client.post(
                endpoint, json=payload, headers=headers, timeout=timeout_seconds
            )
        except httpx.TimeoutException as exc:
            raise LLMNetworkError(f"LLM request timed out after {timeout_seconds}s") from exc
        except httpx.RequestError as exc:
            raise LLMNetworkError("LLM network communication failed") from exc

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        if response.status_code != 200:
            raise LLMError(f"LLM provider '{provider}' returned HTTP {response.status_code}")

        resp_json = response.json()
        try:
            choice_msg = resp_json["choices"][0]["message"]
            raw_content = choice_msg.get("content") or choice_msg.get("reasoning_content") or ""
        except (KeyError, IndexError) as exc:
            raise LLMValidationError("Malformed LLM response structure") from exc

        # Calculate immutable SHA256 digest of raw output
        raw_digest = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()

        usage = resp_json.get("usage", {})
        usage_available = "prompt_tokens" in usage and "completion_tokens" in usage
        prompt_tokens = int(usage["prompt_tokens"]) if usage_available else None
        completion_tokens = int(usage["completion_tokens"]) if usage_available else None
        total_tokens = (
            int(usage.get("total_tokens", (prompt_tokens or 0) + (completion_tokens or 0)))
            if usage_available
            else None
        )
        await record_llm_usage(
            settings=self._settings,
            trace_id=resolved_trace_id,
            provider=provider,
            model=target_model,
            operation=response_model.__name__,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            raw_digest=raw_digest,
        )

        # Parse and validate with Pydantic
        clean_text = raw_content.strip()
        if clean_text.startswith("```"):
            clean_text = clean_text.strip("`")
            if clean_text.startswith("json"):
                clean_text = clean_text[4:].strip()

        try:
            parsed_instance = response_model.model_validate_json(clean_text)
        except ValidationError as exc:
            raise LLMValidationError(
                f"LLM response failed Pydantic validation for {response_model.__name__}: {exc}"
            ) from exc

        return LLMCompletionResult(
            raw_content=raw_content,
            parsed=parsed_instance,
            raw_digest=raw_digest,
            model=target_model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            trace_id=resolved_trace_id,
        )
