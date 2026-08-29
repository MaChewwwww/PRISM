from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.models import AuthMeResponse, LoginRequest, LoginResponse, LogoutResponse
from app.core.auth.dependencies import get_current_user
from app.core.auth.token import create_access_token
from app.core.config import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    email_matches = secrets.compare_digest(
        request.email.strip().lower(), settings.auth_email.strip().lower()
    )
    password_matches = secrets.compare_digest(request.password, settings.auth_password)

    if not (email_matches and password_matches):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(
        email=settings.auth_email,
        secret_key=settings.auth_secret_key,
        expires_in_hours=settings.auth_session_expire_hours,
    )
    expires_at = datetime.now(UTC) + timedelta(hours=settings.auth_session_expire_hours)
    expires_at_str = expires_at.isoformat()

    response.set_cookie(
        key="prism_session",
        value=token,
        max_age=settings.auth_session_expire_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        path="/",
    )

    return LoginResponse(
        email=settings.auth_email,
        expires_at=expires_at_str,
    )


@router.get("/me", response_model=AuthMeResponse)
def me(current_user: Annotated[str, Depends(get_current_user)]) -> AuthMeResponse:
    return AuthMeResponse(email=current_user, authenticated=True)


@router.post("/logout", response_model=LogoutResponse)
def logout(response: Response) -> LogoutResponse:
    response.delete_cookie(
        key="prism_session",
        path="/",
        httponly=True,
        samesite="lax",
    )
    return LogoutResponse(status="logged_out")
