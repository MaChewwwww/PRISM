from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status

from app.core.auth.token import verify_access_token
from app.core.config import Settings, get_settings


async def get_current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
    shadowfund_session: Annotated[str | None, Cookie()] = None,
) -> str:
    token: str | None = None

    if authorization is not None and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    elif shadowfund_session is not None and shadowfund_session.strip():
        token = shadowfund_session.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_access_token(token, settings.auth_secret_key)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = str(payload["sub"])
    return email
