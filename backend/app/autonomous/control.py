from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.autonomous.models import AutonomousControlModel
from app.core.config import Settings

CONTROL_ID = "default"


async def get_or_create_control(
    session: AsyncSession, settings: Settings
) -> AutonomousControlModel:
    result = await session.execute(
        select(AutonomousControlModel).where(AutonomousControlModel.id == CONTROL_ID)
    )
    control = result.scalar_one_or_none()
    if control is None:
        control = AutonomousControlModel(
            id=CONTROL_ID,
            kill_switch_active=settings.execution_kill_switch,
            updated_at=datetime.now(UTC),
            updated_by="system",
            reason="Initialized fail-closed from configuration",
        )
        session.add(control)
        await session.flush()
    return control


async def set_kill_switch(
    session: AsyncSession, settings: Settings, *, active: bool, actor: str, reason: str
) -> AutonomousControlModel:
    if not active and settings.execution_kill_switch:
        raise ValueError("Static EXECUTION_KILL_SWITCH remains active")
    control = await get_or_create_control(session, settings)
    control.kill_switch_active = active
    control.updated_at = datetime.now(UTC)
    control.updated_by = actor[:255]
    control.reason = reason[:2000]
    await session.commit()
    return control


def control_payload(control: AutonomousControlModel, settings: Settings) -> dict[str, object]:
    return {
        "autonomous_enabled": settings.autonomous_trading_enabled,
        "execution_enabled": settings.execution_enabled,
        "kill_switch_active": settings.execution_kill_switch or control.kill_switch_active,
        "updated_at": control.updated_at,
        "updated_by": control.updated_by,
        "reason": control.reason,
    }
