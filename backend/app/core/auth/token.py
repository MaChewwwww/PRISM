from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def create_access_token(email: str, secret_key: str, expires_in_hours: int = 24) -> str:
    now = datetime.now(UTC)
    exp = now + timedelta(hours=expires_in_hours)
    payload = {
        "sub": email,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = _base64url_encode(payload_json)

    signature = hmac.new(
        secret_key.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sig_b64 = _base64url_encode(signature)

    return f"{payload_b64}.{sig_b64}"


def verify_access_token(token: str, secret_key: str) -> dict[str, Any] | None:
    parts = token.strip().split(".")
    if len(parts) != 2:
        return None

    payload_b64, sig_b64 = parts
    expected_sig = hmac.new(
        secret_key.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected_sig_b64 = _base64url_encode(expected_sig)

    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        return None

    try:
        payload_bytes = _base64url_decode(payload_b64)
        payload: dict[str, Any] = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None

    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        return None

    current_ts = datetime.now(UTC).timestamp()
    if current_ts > exp:
        return None

    return payload
