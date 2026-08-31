"""Authenticated, database-backed read models for autonomous paper trading.

This module deliberately reads immutable audit roots only.  It never imports the
worker, Alpaca clients, or execution gateway, so an operator dashboard cannot
trigger provider reads or order submission while it refreshes.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models import (
    AutonomousCycleCollection,
    AutonomousCycleRead,
    AutonomousDecisionCollection,
    AutonomousDecisionRead,
    AutonomousExecutionCollection,
    AutonomousExecutionRead,
    AutonomousPortfolioLatest,
    AutonomousPortfolioSnapshot,
    AutonomousPositionRead,
    AutonomousRuleTraceSummary,
)
from app.autonomous.models import (
    AuthorizationModel,
    AutonomousCycleModel,
    PortfolioSnapshotModel,
    RiskAssessmentModel,
    TradeProposalModel,
)
from app.execution.models import ExecutionReceiptModel

AuthorizationOutcomeValue = Literal["APPROVE", "REJECT", "MODIFIED_PENDING_ACCEPTANCE"]
ExecutionReceiptStatus = Literal[
    "pending", "submitted", "reconciling", "rejected", "filled", "failed"
]


def _uuid(value: str) -> UUID:
    return UUID(str(value))


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _parsed_json(value: str) -> dict[str, Any]:
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


def cycle_read(row: AutonomousCycleModel) -> AutonomousCycleRead:
    try:
        decoded_symbols = json.loads(row.symbols_json)
    except (TypeError, json.JSONDecodeError):
        decoded_symbols = []
    symbols = [str(symbol).upper() for symbol in decoded_symbols if isinstance(symbol, str)]
    return AutonomousCycleRead(
        id=_uuid(row.id),
        started_at=_utc(row.started_at),
        completed_at=_utc(row.completed_at) if row.completed_at is not None else None,
        outcome=row.outcome,
        symbols=symbols,
        reason=row.reason,
        worker_version=row.worker_version,
    )


def _rule_trace(value: str) -> list[AutonomousRuleTraceSummary]:
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(decoded, list):
        return []
    summaries: list[AutonomousRuleTraceSummary] = []
    for item in decoded:
        if not isinstance(item, dict):
            continue
        priority = item.get("priority")
        outcome = item.get("outcome")
        if priority not in {"P0", "P1", "P2", "P3", "P4", "P5"}:
            continue
        if outcome not in {"PASS", "MODIFY", "FAIL"}:
            continue
        reason_codes = item.get("reason_codes")
        summaries.append(
            AutonomousRuleTraceSummary(
                rule_id=str(item.get("rule_id", "unknown")),
                priority=priority,
                outcome=outcome,
                reason_codes=[str(code) for code in reason_codes]
                if isinstance(reason_codes, list)
                else [],
                explanation=str(item.get("explanation", "")),
            )
        )
    return summaries


def decision_read(
    authorization: AuthorizationModel,
    proposal: TradeProposalModel | None,
    risk: RiskAssessmentModel | None,
) -> AutonomousDecisionRead:
    return AutonomousDecisionRead(
        proposal_id=_uuid(authorization.proposal_id),
        trace_id=_uuid(authorization.trace_id),
        symbol=proposal.symbol if proposal is not None else "UNKNOWN",
        created_at=_utc(authorization.created_at),
        risk_verdict=risk.verdict if risk is not None else None,
        authorization_outcome=cast(AuthorizationOutcomeValue, authorization.outcome),
        ruleset_version=authorization.ruleset_version,
        profile_version=authorization.profile_version,
        decision_at=_utc(authorization.decision_at),
        expires_at=_utc(authorization.expires_at),
        rule_trace=_rule_trace(authorization.rule_trace_json),
    )


def execution_read(row: ExecutionReceiptModel) -> AutonomousExecutionRead:
    return AutonomousExecutionRead(
        id=_uuid(row.id),
        trace_id=_uuid(row.trace_id),
        proposal_id=_uuid(row.proposal_id),
        status=cast(ExecutionReceiptStatus, row.status),
        filled_quantity=row.filled_quantity,
        filled_average_price=row.filled_average_price,
        error_code=row.error_code,
        created_at=_utc(row.created_at),
        submitted_at=_utc(row.submitted_at) if row.submitted_at is not None else None,
        reconciled_at=_utc(row.reconciled_at) if row.reconciled_at is not None else None,
    )


def portfolio_read(row: PortfolioSnapshotModel) -> AutonomousPortfolioSnapshot:
    payload = _parsed_json(row.payload_json)
    positions: list[AutonomousPositionRead] = []
    raw_positions = payload.get("positions")
    if isinstance(raw_positions, list):
        for raw_position in raw_positions:
            if not isinstance(raw_position, dict):
                continue
            positions.append(
                AutonomousPositionRead(
                    symbol=str(raw_position.get("symbol", "UNKNOWN")),
                    underlying=str(raw_position.get("underlying", "UNKNOWN")),
                    asset_class=str(raw_position.get("asset_class", "unknown")),
                    quantity=_decimal_or_none(raw_position.get("qty")),
                    market_value=_decimal_or_none(raw_position.get("market_value")),
                    average_entry_price=_decimal_or_none(raw_position.get("avg_entry_price")),
                    unrealized_pl=_decimal_or_none(raw_position.get("unrealized_pl")),
                    unrealized_plpc=_decimal_or_none(raw_position.get("unrealized_plpc")),
                    expiration=(
                        str(raw_position["expiration"])
                        if raw_position.get("expiration") is not None
                        else None
                    ),
                    sector=(str(raw_position["sector"]) if raw_position.get("sector") else None),
                    correlated_cluster=(
                        str(raw_position["correlated_cluster"])
                        if raw_position.get("correlated_cluster")
                        else None
                    ),
                    delta=_decimal_or_none(raw_position.get("delta")),
                    vega=_decimal_or_none(raw_position.get("vega")),
                    metadata_complete=bool(raw_position.get("metadata_complete", False)),
                    quote_age_seconds=_decimal_or_none(raw_position.get("quote_age_seconds")),
                )
            )
    observed_at = payload.get("observed_at")
    if isinstance(observed_at, str):
        try:
            parsed_observed_at = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        except ValueError:
            parsed_observed_at = row.observed_at
        if parsed_observed_at.tzinfo is None or parsed_observed_at.utcoffset() is None:
            parsed_observed_at = row.observed_at
    else:
        parsed_observed_at = row.observed_at
    return AutonomousPortfolioSnapshot(
        observed_at=_utc(parsed_observed_at),
        account_verified=bool(payload.get("account_verified", row.account_verified)),
        supported_options_level=payload.get("supported_options_level", row.supported_options_level),
        account_values_complete=bool(payload.get("account_values_complete", False)),
        cash=_decimal_or_none(payload.get("cash")),
        buying_power=_decimal_or_none(payload.get("buying_power")),
        portfolio_value=_decimal_or_none(payload.get("portfolio_value")),
        start_of_day_equity=_decimal_or_none(payload.get("start_of_day_equity")),
        positions=positions,
    )


class AutonomousReadService:
    """Read-only queries for bounded operator polling endpoints."""

    async def list_cycles(
        self, session: AsyncSession, *, start: datetime, end: datetime, limit: int
    ) -> AutonomousCycleCollection:
        rows = list(
            (
                await session.scalars(
                    select(AutonomousCycleModel)
                    .where(
                        AutonomousCycleModel.started_at >= start,
                        AutonomousCycleModel.started_at <= end,
                    )
                    .order_by(AutonomousCycleModel.started_at.desc())
                    .limit(limit)
                )
            ).all()
        )
        return AutonomousCycleCollection(
            items=[cycle_read(row) for row in rows],
            empty_message="No autonomous cycles fall inside this UTC range." if not rows else None,
        )

    async def list_decisions(
        self,
        session: AsyncSession,
        *,
        start: datetime,
        end: datetime,
        limit: int,
        symbol: str | None,
        outcome: str | None,
    ) -> AutonomousDecisionCollection:
        statement = (
            select(AuthorizationModel)
            .where(
                AuthorizationModel.created_at >= start,
                AuthorizationModel.created_at <= end,
            )
            .order_by(AuthorizationModel.created_at.desc())
            .limit(limit)
        )
        if outcome:
            statement = statement.where(AuthorizationModel.outcome == outcome.upper())
        if symbol:
            statement = statement.join(
                TradeProposalModel, TradeProposalModel.id == AuthorizationModel.proposal_id
            ).where(TradeProposalModel.symbol == symbol.upper())
        authorizations = list((await session.scalars(statement)).all())
        proposal_ids = [row.proposal_id for row in authorizations]
        proposals: dict[str, TradeProposalModel] = {}
        risks: dict[str, RiskAssessmentModel] = {}
        if proposal_ids:
            proposal_rows = list(
                (
                    await session.scalars(
                        select(TradeProposalModel).where(TradeProposalModel.id.in_(proposal_ids))
                    )
                ).all()
            )
            proposals = {row.id: row for row in proposal_rows}
            risk_rows = list(
                (
                    await session.scalars(
                        select(RiskAssessmentModel).where(
                            RiskAssessmentModel.proposal_id.in_(proposal_ids)
                        )
                    )
                ).all()
            )
            risks = {row.proposal_id: row for row in risk_rows}
        items = [
            decision_read(row, proposals.get(row.proposal_id), risks.get(row.proposal_id))
            for row in authorizations
        ]
        return AutonomousDecisionCollection(
            items=items,
            empty_message=(
                "No autonomous decisions fall inside this UTC range." if not items else None
            ),
        )

    async def list_executions(
        self,
        session: AsyncSession,
        *,
        start: datetime,
        end: datetime,
        limit: int,
        status: str | None,
    ) -> AutonomousExecutionCollection:
        statement = (
            select(ExecutionReceiptModel)
            .where(
                ExecutionReceiptModel.created_at >= start,
                ExecutionReceiptModel.created_at <= end,
            )
            .order_by(ExecutionReceiptModel.created_at.desc())
            .limit(limit)
        )
        if status:
            statement = statement.where(ExecutionReceiptModel.status == status.lower())
        rows = list((await session.scalars(statement)).all())
        return AutonomousExecutionCollection(
            items=[execution_read(row) for row in rows],
            empty_message="No autonomous execution receipts fall inside this UTC range."
            if not rows
            else None,
        )

    async def latest_portfolio(self, session: AsyncSession) -> AutonomousPortfolioLatest:
        row = await session.scalar(
            select(PortfolioSnapshotModel)
            .order_by(PortfolioSnapshotModel.observed_at.desc())
            .limit(1)
        )
        if row is None:
            return AutonomousPortfolioLatest(
                empty_message="No autonomous portfolio snapshot has been recorded yet."
            )
        return AutonomousPortfolioLatest(snapshot=portfolio_read(row))
