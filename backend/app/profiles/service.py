"""Application service for bounded AI Profile lifecycle changes.

No function in this module imports an execution adapter or grants execution
authority.  Profile selection only supplies bounded inputs to the existing
deterministic rules engine.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.profiles.models import (
    AIProfileModel,
    CalibrationPreferenceModel,
    ProfileGovernanceAuditEventModel,
)
from app.rules.registry import ProfileParameters, get_authorized_ruleset
from app.shadowfund.models import ShadowPostAnalysisBatchModel, ShadowProfileRecommendationModel

CalibrationMode = Literal["manual", "automatic"]


class ProfileGovernanceError(ValueError):
    """A request cannot safely produce an active profile."""


@dataclass(frozen=True)
class ActiveProfile:
    id: UUID
    profile_key: Literal["conservative", "balanced", "aggressive"]
    version: int
    parameters: ProfileParameters
    activation_mode: CalibrationMode


def _digest(value: object) -> str:
    encoded = json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _serialize_parameters(parameters: ProfileParameters) -> str:
    return json.dumps(parameters.model_dump(mode="json"), sort_keys=True)


def _parse_parameters(payload: str) -> ProfileParameters:
    return ProfileParameters.model_validate_json(payload)


class ProfileGovernanceService:
    """Persist and resolve operator-approved profile calibrations."""

    async def get_preference(
        self, session: AsyncSession, operator_id: str
    ) -> CalibrationPreferenceModel:
        preference = await session.get(CalibrationPreferenceModel, operator_id)
        if preference is not None:
            return preference
        now = datetime.now(UTC)
        preference = CalibrationPreferenceModel(
            operator_id=operator_id,
            mode="automatic",
            updated_at=now,
            updated_by="registry-seed",
            automatic_opt_in=True,
        )
        session.add(preference)
        await session.flush()
        return preference

    async def set_preference(
        self, session: AsyncSession, *, operator_id: str, mode: CalibrationMode
    ) -> CalibrationPreferenceModel:
        preference = await self.get_preference(session, operator_id)
        now = datetime.now(UTC)
        preference.mode = mode
        preference.automatic_opt_in = mode == "automatic"
        preference.updated_at = now
        preference.updated_by = operator_id
        await self._audit(
            session,
            actor=operator_id,
            event_type="CALIBRATION_PREFERENCE_UPDATED",
            aggregate_id=operator_id,
            payload={"mode": mode, "automatic_opt_in": preference.automatic_opt_in},
        )
        return preference

    async def get_active(self, session: AsyncSession) -> ActiveProfile:
        row = await session.scalar(
            select(AIProfileModel)
            .where(AIProfileModel.status == "active")
            .order_by(AIProfileModel.version.desc())
            .limit(1)
        )
        if row is None:
            row = await self._seed_baseline(session)
        try:
            ruleset = get_authorized_ruleset()
            if row.ruleset_id != ruleset.ruleset_id or row.ruleset_version != ruleset.version:
                raise ProfileGovernanceError(
                    "Active profile is incompatible with the active ruleset"
                )
            key = row.profile_key
            if key not in {"conservative", "balanced", "aggressive"}:
                raise ProfileGovernanceError("Active profile key is not authorized")
            parameters = _parse_parameters(row.parameters_json)
            self._validate_bounds(parameters)
            return ActiveProfile(
                id=UUID(row.id),
                profile_key=key,  # type: ignore[arg-type]
                version=row.version,
                parameters=parameters,
                activation_mode=row.activation_mode,  # type: ignore[arg-type]
            )
        except (ValueError, TypeError) as exc:
            raise ProfileGovernanceError("Active profile is malformed") from exc

    async def activate_post_analysis_batch(
        self,
        session: AsyncSession,
        *,
        batch_id: str,
        actor: str,
        mode: CalibrationMode,
    ) -> ActiveProfile:
        """Atomically supersede the active profile from a validated batch.

        The batch and recommendations remain immutable evidence.  The new
        profile binds their digest and records its own immutable audit event.
        """

        existing = await session.scalar(
            select(AIProfileModel).where(AIProfileModel.source_batch_id == batch_id)
        )
        if existing is not None:
            return ActiveProfile(
                id=UUID(existing.id),
                profile_key=existing.profile_key,  # type: ignore[arg-type]
                version=existing.version,
                parameters=_parse_parameters(existing.parameters_json),
                activation_mode=existing.activation_mode,  # type: ignore[arg-type]
            )

        batch = await session.get(ShadowPostAnalysisBatchModel, batch_id)
        if batch is None or batch.state != "DRAFT":
            raise ProfileGovernanceError("No draft post-analysis recommendation batch is available")
        recommendations = list(
            (
                await session.scalars(
                    select(ShadowProfileRecommendationModel)
                    .where(ShadowProfileRecommendationModel.batch_id == batch_id)
                    .order_by(ShadowProfileRecommendationModel.parameter_id)
                )
            ).all()
        )
        if not recommendations:
            raise ProfileGovernanceError("Post-analysis batch contains no recommendation")

        active = await self.get_active(session)
        values = active.parameters.model_dump(mode="python")
        expected_fields = set(values)
        suggested_fields: set[str] = set()
        for recommendation in recommendations:
            field = recommendation.parameter_id
            if field not in expected_fields or field in suggested_fields:
                raise ProfileGovernanceError("Recommendation fields are incomplete or duplicated")
            if recommendation.validation_state != "WITHIN_AUTHORIZED_BOUNDS":
                raise ProfileGovernanceError("Recommendation is outside authorized profile bounds")
            try:
                values[field] = Decimal(recommendation.suggested_value)
            except (InvalidOperation, ValueError) as exc:
                raise ProfileGovernanceError("Recommendation contains an invalid decimal") from exc
            suggested_fields.add(field)
        if not suggested_fields:
            raise ProfileGovernanceError("Recommendation contains no authorized profile field")

        parameters = ProfileParameters.model_validate(values)
        self._validate_bounds(parameters)
        ruleset = get_authorized_ruleset()
        now = datetime.now(UTC)
        current_rows = list(
            (
                await session.scalars(
                    select(AIProfileModel).where(AIProfileModel.status == "active")
                )
            ).all()
        )
        for row in current_rows:
            row.status = "superseded"
        version = max((row.version for row in current_rows), default=active.version) + 1
        profile_key = active.profile_key
        payload = {
            "batch_id": batch_id,
            "profile_key": profile_key,
            "version": version,
            "ruleset": f"{ruleset.ruleset_id}@{ruleset.version}",
            "parameters": parameters.model_dump(mode="json"),
            "mode": mode,
        }
        row = AIProfileModel(
            id=str(uuid4()),
            profile_key=profile_key,
            version=version,
            status="active",
            ruleset_id=ruleset.ruleset_id,
            ruleset_version=ruleset.version,
            activation_mode=mode,
            created_at=now,
            effective_at=now,
            activated_by=actor,
            source_batch_id=batch_id,
            parameters_json=_serialize_parameters(parameters),
            input_digest=_digest(payload),
        )
        session.add(row)
        await session.flush()
        await self._audit(
            session,
            actor=actor,
            event_type="PROFILE_AUTOMATICALLY_CALIBRATED"
            if mode == "automatic"
            else "PROFILE_MANUALLY_ACTIVATED",
            aggregate_id=row.id,
            payload=payload,
        )
        return ActiveProfile(
            id=UUID(row.id),
            profile_key=profile_key,
            version=version,
            parameters=parameters,
            activation_mode=mode,
        )

    async def apply_automatic_if_enabled(
        self,
        session: AsyncSession,
        *,
        batch_id: str,
        operator_id: str,
    ) -> ActiveProfile | None:
        """Apply only when the authenticated operator selected automatic mode."""
        preference = await self.get_preference(session, operator_id)
        if preference.mode != "automatic" or not preference.automatic_opt_in:
            return None
        batch = await session.get(ShadowPostAnalysisBatchModel, batch_id)
        if batch is None or batch.state != "DRAFT":
            return None
        has_recommendation = await session.scalar(
            select(ShadowProfileRecommendationModel.id)
            .where(ShadowProfileRecommendationModel.batch_id == batch_id)
            .limit(1)
        )
        if has_recommendation is None:
            return None
        return await self.activate_post_analysis_batch(
            session, batch_id=batch_id, actor=operator_id, mode="automatic"
        )

    async def _seed_baseline(self, session: AsyncSession) -> AIProfileModel:
        ruleset = get_authorized_ruleset()
        now = datetime.now(UTC)
        key = ruleset.default_profile
        parameters = ruleset.profiles[key]
        payload = {
            "seed": "authorized_registry",
            "profile_key": key,
            "version": 1,
            "ruleset": f"{ruleset.ruleset_id}@{ruleset.version}",
            "parameters": parameters.model_dump(mode="json"),
        }
        row = AIProfileModel(
            id=str(uuid5(NAMESPACE_URL, f"{ruleset.ruleset_id}:{key}:1")),
            profile_key=key,
            version=1,
            status="active",
            ruleset_id=ruleset.ruleset_id,
            ruleset_version=ruleset.version,
            activation_mode="manual",
            created_at=now,
            effective_at=now,
            activated_by="registry-seed",
            source_batch_id=None,
            parameters_json=_serialize_parameters(parameters),
            input_digest=_digest(payload),
        )
        session.add(row)
        await session.flush()
        await self._audit(
            session,
            actor="registry-seed",
            event_type="BASELINE_PROFILE_SEEDED",
            aggregate_id=row.id,
            payload=payload,
        )
        return row

    @staticmethod
    def _validate_bounds(parameters: ProfileParameters) -> None:
        ruleset = get_authorized_ruleset()
        for field, bound in ruleset.profile_bounds.items():
            value = getattr(parameters, field)
            if value < bound.minimum or value > bound.maximum:
                raise ProfileGovernanceError(f"{field} is outside BA-authorized bounds")

    async def _audit(
        self,
        session: AsyncSession,
        *,
        actor: str,
        event_type: str,
        aggregate_id: str,
        payload: object,
    ) -> None:
        session.add(
            ProfileGovernanceAuditEventModel(
                id=str(uuid4()),
                created_at=datetime.now(UTC),
                actor=actor,
                event_type=event_type,
                aggregate_id=aggregate_id,
                payload_digest=_digest(payload),
                payload_json=json.dumps(payload, default=str, sort_keys=True),
            )
        )
