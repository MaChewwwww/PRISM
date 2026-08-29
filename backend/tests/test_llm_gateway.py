from __future__ import annotations

import hashlib
import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.core.llm_gateway import (
    LLMConfigurationError,
    LLMError,
    LLMGateway,
    LLMValidationError,
)


class MockAnalysisResult(BaseModel):
    symbol: str
    sentiment: str
    score: int = Field(ge=0, le=100)
    thesis: str


@pytest.mark.asyncio
async def test_featherless_missing_api_key_raises_config_error() -> None:
    settings = Settings(
        _env_file=None,
        llm_provider="featherless",
        featherless_api_key=None,
    )
    gateway = LLMGateway(settings=settings)
    with pytest.raises(LLMConfigurationError, match="FEATHERLESS_API_KEY is required"):
        await gateway.complete_structured(
            prompt="Analyze NVDA",
            response_model=MockAnalysisResult,
        )


@pytest.mark.asyncio
async def test_featherless_successful_structured_completion() -> None:
    mock_payload = {
        "symbol": "NVDA",
        "sentiment": "bullish",
        "score": 88,
        "thesis": "High demand for Blackwell architecture with positive guidance.",
    }
    raw_content = json.dumps(mock_payload)
    expected_digest = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": raw_content,
                }
            }
        ],
        "usage": {
            "prompt_tokens": 150,
            "completion_tokens": 45,
            "total_tokens": 195,
        },
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_response

    settings = Settings(
        _env_file=None,
        llm_provider="featherless",
        featherless_api_key="test-featherless-key",
        featherless_base_url="https://api.featherless.ai/v1",
        llm_model="DeepSeek-V4-Flash-0731",
    )
    gateway = LLMGateway(settings=settings, client=mock_client)
    trace_id = uuid4()

    result = await gateway.complete_structured(
        prompt="Analyze NVDA earnings catalyst",
        response_model=MockAnalysisResult,
        trace_id=trace_id,
    )

    assert result.parsed is not None
    assert result.parsed.symbol == "NVDA"
    assert result.parsed.score == 88
    assert result.raw_digest == expected_digest
    assert result.model == "DeepSeek-V4-Flash-0731"
    assert result.provider == "featherless"
    assert result.prompt_tokens == 150
    assert result.completion_tokens == 45
    assert result.total_tokens == 195
    assert result.trace_id == trace_id

    # Verify request headers and URL
    call_args = mock_client.post.call_args
    assert call_args[0][0] == "https://api.featherless.ai/v1/chat/completions"
    assert call_args[1]["headers"]["Authorization"] == "Bearer test-featherless-key"
    assert call_args[1]["json"]["model"] == "DeepSeek-V4-Flash-0731"
    assert call_args[1]["json"]["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_featherless_schema_violation_fails_closed() -> None:
    # Score is out of range (> 100) violating schema
    invalid_payload = {
        "symbol": "NVDA",
        "sentiment": "bullish",
        "score": 999,
        "thesis": "Invalid score test",
    }
    raw_content = json.dumps(invalid_payload)

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": raw_content}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 30},
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_response

    settings = Settings(
        _env_file=None,
        llm_provider="featherless",
        featherless_api_key="test-key",
    )
    gateway = LLMGateway(settings=settings, client=mock_client)

    with pytest.raises(LLMValidationError, match="failed Pydantic validation"):
        await gateway.complete_structured(
            prompt="Analyze NVDA",
            response_model=MockAnalysisResult,
        )


@pytest.mark.asyncio
async def test_featherless_http_error_handling() -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.text = "Unauthorized: Invalid API Key"

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_response

    settings = Settings(
        _env_file=None,
        llm_provider="featherless",
        featherless_api_key="invalid-key",
    )
    gateway = LLMGateway(settings=settings, client=mock_client)

    with pytest.raises(LLMError, match="returned HTTP 401"):
        await gateway.complete_structured(
            prompt="Analyze NVDA",
            response_model=MockAnalysisResult,
        )
