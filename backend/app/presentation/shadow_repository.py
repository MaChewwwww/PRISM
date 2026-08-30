"""Recorded ShadowFund projection for the existing presentation routes.

This boundary reads only ShadowFund persistence roots.  It intentionally has no
dependency on the autonomous worker, account state, or paper-order adapters.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.backtest.models import BacktestRunModel
from app.core.config import Settings
from app.presentation.models import (
    AlternativeBranch,
    AlternativeCollection,
    AlternativeSession,
    ChartPoint,
    DataMode,
    DateRange,
    PresentationEnvelope,
    PresentationMeta,
)
from app.shadowfund.models import (
    ShadowBranchModel,
    ShadowSessionModel,
    ShadowValuationModel,
)


def _money(value: Decimal | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}${value:,.2f}"


def _number(value: Decimal | None) -> str:
    return "—" if value is None else f"{value:,.2f}"


def _date_range(start: datetime | None = None, end: datetime | None = None) -> DateRange | None:
    if start is None or end is None:
        return None
    return DateRange(
        preset="custom",
        from_date=start.astimezone(UTC).date().isoformat(),
        to_date=end.astimezone(UTC).date().isoformat(),
    )


class BacktestPresentationRepository:
    """Project completed staging ShadowFund runs into unchanged UI models."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    @property
    def _mode(self) -> DataMode:
        return DataMode.SIMULATED if self._settings.environment == "staging" else DataMode.RECORDED

    def _meta(
        self, *, start: datetime | None = None, end: datetime | None = None
    ) -> PresentationMeta:
        simulated = self._mode is DataMode.SIMULATED
        return PresentationMeta(
            generated_at=datetime.now(UTC),
            as_of=datetime.now(UTC),
            data_mode=self._mode,
            fixture_version=None,
            range=_date_range(start, end),
            provenance_notice=(
                "Historical simulation. Virtual ShadowFund valuations are not Alpaca paper "
                "fills and never alter the Active Portfolio."
                if simulated
                else "Recorded ShadowFund counterfactuals. Virtual valuations never alter the "
                "Active Portfolio or submit an order."
            ),
        )

    async def list_sessions(
        self, *, start: datetime, end: datetime
    ) -> PresentationEnvelope[AlternativeCollection]:
        statement = (
            select(ShadowSessionModel)
            .where(
                ShadowSessionModel.created_at >= start,
                ShadowSessionModel.created_at <= end,
            )
            .order_by(ShadowSessionModel.created_at.desc())
        )
        if self._settings.environment == "staging":
            active_run_id = await self._session.scalar(
                select(BacktestRunModel.id).where(
                    BacktestRunModel.status == "COMPLETED",
                    BacktestRunModel.is_active_presentation.is_(True),
                )
            )
            if active_run_id is None:
                return PresentationEnvelope(
                    meta=self._meta(start=start, end=end),
                    data=AlternativeCollection(
                        sessions=[],
                        empty_message=(
                            "No completed staging backtest ShadowFund sessions are available."
                        ),
                    ),
                )
            statement = statement.where(ShadowSessionModel.backtest_run_id == active_run_id)
        rows = list((await self._session.scalars(statement)).all())
        sessions = [await self._session_projection(row) for row in rows]
        aggregate = await self._aggregate_path(rows)
        completed = sum(item.state == "complete" for item in sessions)
        incomplete = sum(item.state == "incomplete" for item in sessions)
        empty_message = None
        if not sessions:
            empty_message = (
                "No completed staging backtest ShadowFund sessions are available."
                if self._settings.environment == "staging"
                else "No recorded ShadowFund sessions fall inside this date range."
            )
        return PresentationEnvelope(
            meta=self._meta(start=start, end=end),
            data=AlternativeCollection(
                sessions=sessions,
                aggregate_path=aggregate,
                completed_sessions=completed,
                incomplete_sessions=incomplete,
                empty_message=empty_message,
            ),
        )

    async def get(self, session_id: str) -> PresentationEnvelope[AlternativeSession] | None:
        row = await self._session.get(ShadowSessionModel, session_id)
        if row is None:
            return None
        if self._settings.environment == "staging":
            active_run_id = await self._session.scalar(
                select(BacktestRunModel.id).where(
                    BacktestRunModel.status == "COMPLETED",
                    BacktestRunModel.is_active_presentation.is_(True),
                )
            )
            if active_run_id is None or row.backtest_run_id != active_run_id:
                return None
        return PresentationEnvelope(meta=self._meta(), data=await self._session_projection(row))

    async def _session_projection(self, row: ShadowSessionModel) -> AlternativeSession:
        branches = list(
            (
                await self._session.scalars(
                    select(ShadowBranchModel)
                    .where(ShadowBranchModel.session_id == row.id)
                    .order_by(ShadowBranchModel.branch_key)
                )
            ).all()
        )
        values_by_branch: dict[str, list[ShadowValuationModel]] = {}
        for branch in branches:
            values_by_branch[branch.id] = list(
                (
                    await self._session.scalars(
                        select(ShadowValuationModel)
                        .where(ShadowValuationModel.branch_id == branch.id)
                        .order_by(ShadowValuationModel.observed_at)
                    )
                ).all()
            )
        chosen = next((branch for branch in branches if branch.chosen_path), None)
        chosen_value = self._latest(values_by_branch.get(chosen.id, [])) if chosen else None
        projected = [
            self._branch_projection(branch, values_by_branch[branch.id], chosen_value)
            for branch in branches
        ]
        comparable = [
            (branch, self._latest(values_by_branch[branch.id]))
            for branch in branches
            if not branch.chosen_path and branch.state != "incomplete"
        ]
        best_branch, best_value = max(
            comparable,
            key=lambda item: item[1].net_pnl if item[1] is not None else Decimal("-999999"),
            default=(chosen, chosen_value),
        )
        chosen_pnl = chosen_value.net_pnl if chosen_value is not None else Decimal("0")
        best_pnl = best_value.net_pnl if best_value is not None else Decimal("0")
        limitations = [
            "Counterfactual capability evidence only; it is not strategy-performance evidence.",
            "No ShadowFund branch can create, authorize, amend, cancel, or submit an order.",
        ]
        if row.refusal_reason:
            limitations.append(row.refusal_reason)
        limitations.extend(
            branch.reason
            for branch in branches
            if branch.reason and branch.reason not in limitations
        )
        return AlternativeSession(
            id=row.id,
            story_id=row.proposal_id or row.id,
            occurred_at=row.created_at,
            symbol=row.symbol or "CASH",
            title=f"ShadowFund counterfactual — {row.symbol or 'no viable proposal'}",
            summary=(
                "Historical simulation projected from point-in-time replay evidence."
                if row.source_mode == "staging"
                else "Recorded counterfactual branches from the terminal autonomous decision."
            ),
            chosen_path_pnl=_money(chosen_pnl),
            best_branch=best_branch.label if best_branch else "Cash / no action",
            alternative_label=(
                best_branch.label if best_branch and not best_branch.chosen_path else None
            ),
            best_delta=_money(best_pnl - chosen_pnl),
            coverage=(
                _number(best_value.coverage_pct) + "%" if best_value is not None else "0.00%"
            ),
            branches=projected,
            path=self._path(branches, values_by_branch),
            limitations=limitations,
            state=cast(Literal["open", "complete", "incomplete"], row.state),
            terminal_outcome=row.terminal_outcome,
            source_mode="staging" if row.source_mode == "staging" else "production",
            evaluation_root_digest=row.evaluation_root_digest,
            ruleset_version=row.ruleset_version,
            profile_version=row.profile_version,
            valuation_policy_version=row.valuation_policy_version,
            refusal_reasons=[branch.reason for branch in branches if branch.reason],
        )

    @staticmethod
    def _latest(values: list[ShadowValuationModel]) -> ShadowValuationModel | None:
        return values[-1] if values else None

    def _branch_projection(
        self,
        branch: ShadowBranchModel,
        values: list[ShadowValuationModel],
        chosen_latest: ShadowValuationModel | None,
    ) -> AlternativeBranch:
        latest = self._latest(values)
        return AlternativeBranch(
            id=branch.id,
            label=branch.label,
            variation=branch.variation,
            pnl=_money(latest.net_pnl if latest else None),
            delta_vs_chosen=(
                "—"
                if latest is None or chosen_latest is None
                else _money(latest.net_pnl - chosen_latest.net_pnl)
            ),
            drawdown=_money(latest.drawdown if latest else None),
            coverage=_number(latest.coverage_pct) + "%" if latest else "0.00%",
            status=cast(Literal["open", "complete", "incomplete"], branch.state),
            gross_pnl=_money(latest.gross_pnl if latest else None),
            net_pnl=_money(latest.net_pnl if latest else None),
            mae=_money(latest.mae if latest else None),
            mfe=_money(latest.mfe if latest else None),
            duration=(
                str((latest.observed_at - branch.entry_at).total_seconds() // 60) + "m"
                if latest is not None and branch.entry_at is not None
                else None
            ),
            capital_at_risk=_money(latest.capital_at_risk if latest else None),
            allocation_multiplier=f"{branch.allocation_multiplier}x",
            entry_exit_policy="Bid/ask marks with authorized freshness, spread, and exit gates.",
            valuation_confidence=latest.confidence if latest else None,
            refusal_reason=branch.reason,
            chosen_path=branch.chosen_path,
        )

    def _path(
        self,
        branches: list[ShadowBranchModel],
        values_by_branch: dict[str, list[ShadowValuationModel]],
    ) -> list[ChartPoint]:
        labels = {branch.branch_key: branch.id for branch in branches}
        values: dict[datetime, dict[str, Decimal]] = defaultdict(dict)
        for branch_id, branch_values in values_by_branch.items():
            key = next((name for name, value in labels.items() if value == branch_id), None)
            if key is None:
                continue
            for valuation in branch_values:
                values[valuation.observed_at][key] = valuation.net_pnl
        return [
            ChartPoint(
                date=at.astimezone(UTC).isoformat(),
                chosen_path=str(series.get("chosen")) if "chosen" in series else None,
                cash_baseline=str(series.get("cash")) if "cash" in series else None,
                reduced_size=str(series.get("half_size")) if "half_size" in series else None,
                unhedged=str(series.get("contrarian")) if "contrarian" in series else None,
                agent_alternative=(
                    str(series.get("ai_alternative")) if "ai_alternative" in series else None
                ),
            )
            for at, series in sorted(values.items())
        ]

    async def _aggregate_path(self, rows: list[ShadowSessionModel]) -> list[ChartPoint]:
        if not rows:
            return []
        branch_rows = list(
            (
                await self._session.scalars(
                    select(ShadowBranchModel).where(
                        ShadowBranchModel.session_id.in_([row.id for row in rows])
                    )
                )
            ).all()
        )
        keys = {branch.id: branch.branch_key for branch in branch_rows}
        valuations = list(
            (
                await self._session.scalars(
                    select(ShadowValuationModel)
                    .where(ShadowValuationModel.branch_id.in_(list(keys)))
                    .order_by(ShadowValuationModel.observed_at)
                )
            ).all()
        )
        totals: dict[datetime, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
        for valuation in valuations:
            totals[valuation.observed_at][keys[valuation.branch_id]] += valuation.net_pnl
        return [
            ChartPoint(
                date=at.astimezone(UTC).isoformat(),
                chosen_path=str(series.get("chosen")) if "chosen" in series else None,
                cash_baseline=str(series.get("cash")) if "cash" in series else None,
                reduced_size=str(series.get("half_size")) if "half_size" in series else None,
                unhedged=str(series.get("contrarian")) if "contrarian" in series else None,
                agent_alternative=(
                    str(series.get("ai_alternative")) if "ai_alternative" in series else None
                ),
            )
            for at, series in sorted(totals.items())
        ]
