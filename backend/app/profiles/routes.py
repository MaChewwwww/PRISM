"""Authenticated backend control plane for AI Profile calibration."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models import (
    ActiveProfileResponse,
    CalibrationPreferenceRequest,
    CalibrationPreferenceResponse,
    ProfileActivationRequest,
    ProfileActivationResponse,
    ProfileGovernanceStatusResponse,
)
from app.core.auth.dependencies import get_current_user
from app.core.database import get_db_session
from app.profiles.service import ActiveProfile, ProfileGovernanceError, ProfileGovernanceService

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _profile_response(profile: ActiveProfile) -> ActiveProfileResponse:
    """Keep conversion at the API boundary; the service owns the domain type."""
    return ActiveProfileResponse.model_validate(
        {
            "id": profile.id,
            "profile_key": profile.profile_key,
            "version": profile.version,
            "parameters": profile.parameters,
            "activation_mode": profile.activation_mode,
        }
    )


@router.get("/governance", response_model=ProfileGovernanceStatusResponse)
async def profile_governance_status(
    current_user: Annotated[str, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProfileGovernanceStatusResponse:
    service = ProfileGovernanceService()
    try:
        preference = await service.get_preference(session, current_user)
        active = await service.get_active(session)
        await session.commit()
    except ProfileGovernanceError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profile governance state is unavailable",
        ) from exc
    return ProfileGovernanceStatusResponse(
        active_profile=_profile_response(active),
        preference=CalibrationPreferenceResponse(
            operator_id=preference.operator_id,
            mode=preference.mode,  # type: ignore[arg-type]
            automatic_opt_in=preference.automatic_opt_in,
            updated_at=preference.updated_at,
        ),
    )


@router.put("/calibration-preference", response_model=CalibrationPreferenceResponse)
async def update_calibration_preference(
    request: CalibrationPreferenceRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CalibrationPreferenceResponse:
    service = ProfileGovernanceService()
    try:
        preference = await service.set_preference(
            session, operator_id=current_user, mode=request.mode
        )
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profile calibration preference could not be saved",
        ) from exc
    return CalibrationPreferenceResponse(
        operator_id=preference.operator_id,
        mode=preference.mode,  # type: ignore[arg-type]
        automatic_opt_in=preference.automatic_opt_in,
        updated_at=preference.updated_at,
    )


@router.post("/activate-post-analysis", response_model=ProfileActivationResponse)
async def activate_post_analysis_profile(
    request: ProfileActivationRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProfileActivationResponse:
    service = ProfileGovernanceService()
    try:
        active = await service.activate_post_analysis_batch(
            session,
            batch_id=str(request.batch_id),
            actor=current_user,
            mode="manual",
        )
        await session.commit()
    except ProfileGovernanceError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profile activation could not be completed",
        ) from exc
    return ProfileActivationResponse(
        active_profile=_profile_response(active), activated_from_batch_id=request.batch_id
    )
