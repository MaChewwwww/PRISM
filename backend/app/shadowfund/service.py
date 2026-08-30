"""Deterministic, non-executable ShadowFund session and valuation service."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.models import (
    AuthorizationDecision,
    EvaluationRoot,
    OptionStrategy,
    TradeProposal,
)
from app.rules.registry import get_authorized_ruleset
from app.shadowfund.models import (
    ShadowBranchModel,
    ShadowObservationModel,
    ShadowPostAnalysisBatchModel,
    ShadowProfileRecommendationModel,
    ShadowSessionModel,
    ShadowValuationModel,
)

VALUATION_POLICY_VERSION = "shadowfund-nbbo-v1"


def _digest(value: Any) -> str:
    encoded = json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class ShadowFundService:
    """Writes only ShadowFund tables; it has no execution or account dependencies."""

    async def create_terminal_session(
        self,
        session: AsyncSession,
        *,
        root: EvaluationRoot,
        terminal_outcome: str,
        proposal: TradeProposal | None,
        authorization: AuthorizationDecision | None,
        source_mode: str,
        source_feed: str,
        candidate_strategies: dict[str, OptionStrategy] | None = None,
        backtest_run_id: str | None = None,
        refusal_reason: str | None = None,
        horizon_at: datetime | None = None,
    ) -> ShadowSessionModel:
        """Create a complete branch set without inferring unavailable market data."""

        existing = await session.scalar(
            select(ShadowSessionModel).where(
                ShadowSessionModel.evaluation_root_digest == root.root_digest
            )
        )
        if existing is not None:
            return existing

        now = datetime.now(UTC)
        has_proposal = proposal is not None
        state = "open" if has_proposal else "incomplete"
        record = ShadowSessionModel(
            id=str(uuid4()),
            trace_id=str(root.trace_id),
            created_at=now,
            evaluation_root_digest=root.root_digest,
            terminal_outcome=terminal_outcome,
            proposal_id=str(proposal.id) if proposal else None,
            authorization_id=str(authorization.id) if authorization else None,
            backtest_run_id=backtest_run_id,
            symbol=proposal.symbol if proposal else None,
            state=state,
            source_mode=source_mode,
            source_feed=source_feed,
            valuation_policy_version=VALUATION_POLICY_VERSION,
            exit_policy_json=proposal.exit_policy.model_dump_json() if proposal else None,
            ruleset_version=authorization.ruleset_version if authorization else None,
            profile_version=authorization.profile_version if authorization else None,
            input_digest=_digest(
                {
                    "root": root.root_digest,
                    "outcome": terminal_outcome,
                    "proposal": proposal.proposal_digest if proposal else None,
                    "source_mode": source_mode,
                }
            ),
            refusal_reason=refusal_reason if not has_proposal else None,
            horizon_at=horizon_at,
        )
        session.add(record)
        await session.flush()

        await self._add_branch(
            session,
            record,
            key="chosen",
            label="Chosen path: Cash",
            variation="No confirmed paper fill; cash is the recorded chosen path.",
            strategy=None,
            multiplier=Decimal("1"),
            chosen_path=True,
            state="complete",
        )
        await self._add_branch(
            session,
            record,
            key="cash",
            label="Cash / no action",
            variation="Remain entirely in cash.",
            strategy=None,
            multiplier=Decimal("1"),
            chosen_path=False,
            state="complete",
        )
        candidates = candidate_strategies or {}
        await self._add_candidate_branch(
            session,
            record,
            key="half_size",
            label="Half-size",
            variation="0.5x fractional virtual option economics.",
            strategy=proposal.strategy if proposal else None,
            multiplier=Decimal("0.5"),
        )
        await self._add_candidate_branch(
            session,
            record,
            key="contrarian",
            label="Contrarian",
            variation="Opposite directional thesis selected deterministically.",
            strategy=candidates.get("contrarian"),
            multiplier=Decimal("1"),
        )
        await self._add_candidate_branch(
            session,
            record,
            key="ai_alternative",
            label="AI specialist alternative",
            variation="Agent 7 intent with deterministically selected contracts.",
            strategy=candidates.get("ai_alternative"),
            multiplier=Decimal("1"),
        )
        return record

    async def mark_session_from_quotes(
        self,
        session: AsyncSession,
        *,
        shadow_session_id: str,
        observed_at: datetime,
        quotes: dict[str, dict[str, Any]],
        source: str,
        feed: str,
        max_quote_age_seconds: int,
    ) -> None:
        """Value virtual branches from the same timestamped NBBO snapshot.

        A missing bid/ask never receives a midpoint substitute. The affected
        branch becomes incomplete while cash remains a complete control.
        """

        await self.record_observation(
            session,
            shadow_session_id=shadow_session_id,
            observed_at=observed_at,
            source=source,
            feed=feed,
            payload={"quotes": quotes},
        )
        shadow_session = await session.get(ShadowSessionModel, shadow_session_id)
        if shadow_session is None:
            raise ValueError("ShadowFund session does not exist")
        branches = list(
            (
                await session.scalars(
                    select(ShadowBranchModel).where(
                        ShadowBranchModel.session_id == shadow_session_id
                    )
                )
            ).all()
        )
        for branch in branches:
            if branch.state == "incomplete":
                continue
            if branch.strategy_json is None:
                await self.record_valuation(
                    session,
                    branch_id=branch.id,
                    observed_at=observed_at,
                    gross_pnl=Decimal("0"),
                    net_pnl=Decimal("0"),
                    drawdown=Decimal("0"),
                    mae=Decimal("0"),
                    mfe=Decimal("0"),
                    capital_at_risk=Decimal("0"),
                    coverage_pct=Decimal("100"),
                    confidence="high",
                )
                continue
            strategy = OptionStrategy.model_validate_json(branch.strategy_json)
            if not self._quotes_are_fresh(
                strategy,
                quotes,
                observed_at=observed_at,
                max_quote_age_seconds=max_quote_age_seconds,
            ):
                branch.state = "incomplete"
                branch.reason = "DATA_UNAVAILABLE: incomplete or stale historical quote"
                continue
            entry = self._strategy_value(strategy, quotes, entry=True)
            mark = self._strategy_value(strategy, quotes, entry=False)
            if entry is None or mark is None:
                branch.state = "incomplete"
                branch.reason = "DATA_UNAVAILABLE: incomplete or stale historical quote"
                continue
            if branch.entry_cost is None:
                branch.entry_cost = entry
                branch.entry_at = observed_at.astimezone(UTC)
            gross = (mark - branch.entry_cost) * Decimal("100") * branch.allocation_multiplier
            prior = await session.execute(
                select(
                    func.min(ShadowValuationModel.net_pnl),
                    func.max(ShadowValuationModel.net_pnl),
                ).where(ShadowValuationModel.branch_id == branch.id)
            )
            low, high = prior.one()
            mae = min(Decimal(str(low)) if low is not None else gross, gross)
            mfe = max(Decimal(str(high)) if high is not None else gross, gross)
            exit_reason = self._exit_reason(
                shadow_session.exit_policy_json,
                strategy,
                entry_cost=branch.entry_cost,
                mark=mark,
                observed_at=observed_at,
                horizon_at=shadow_session.horizon_at,
            )
            await self.record_valuation(
                session,
                branch_id=branch.id,
                observed_at=observed_at,
                gross_pnl=gross,
                net_pnl=gross,
                drawdown=min(Decimal("0"), mae),
                mae=mae,
                mfe=mfe,
                capital_at_risk=branch.entry_cost * Decimal("100") * branch.allocation_multiplier,
                coverage_pct=Decimal("100"),
                confidence="high",
                exit_reason=exit_reason,
            )
            if exit_reason is not None:
                branch.state = "complete"
                branch.reason = exit_reason
        await self._complete_if_terminal(session, shadow_session)

    @staticmethod
    def _quotes_are_fresh(
        strategy: OptionStrategy,
        quotes: dict[str, dict[str, Any]],
        *,
        observed_at: datetime,
        max_quote_age_seconds: int,
    ) -> bool:
        for leg in strategy.legs:
            timestamp = quotes.get(leg.symbol, {}).get("quote_timestamp")
            if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
                return False
            age = (observed_at.astimezone(UTC) - timestamp.astimezone(UTC)).total_seconds()
            if age < 0 or age > max_quote_age_seconds:
                return False
        return True

    @staticmethod
    def _exit_reason(
        exit_policy_json: str | None,
        strategy: OptionStrategy,
        *,
        entry_cost: Decimal,
        mark: Decimal,
        observed_at: datetime,
        horizon_at: datetime | None,
    ) -> str | None:
        if horizon_at is not None and observed_at >= horizon_at:
            return "HORIZON_CLOSE"
        if entry_cost <= 0:
            return "DATA_UNAVAILABLE"
        try:
            policy = json.loads(exit_policy_json or "{}")
            pct = (mark - entry_cost) / entry_cost * Decimal("100")
            if pct >= Decimal(str(policy.get("take_profit_pct", "75"))):
                return "TAKE_PROFIT"
            if pct <= -Decimal(str(policy.get("stop_loss_pct", "50"))):
                return "STOP_LOSS"
            expiry = min(datetime.fromisoformat(leg.expiration).date() for leg in strategy.legs)
            threshold = int(policy.get("dte_threshold", 7))
            if (expiry - observed_at.date()).days <= threshold:
                return "DTE_EXIT"
        except (TypeError, ValueError):
            return "DATA_UNAVAILABLE"
        return None

    @staticmethod
    async def _complete_if_terminal(
        session: AsyncSession, shadow_session: ShadowSessionModel
    ) -> None:
        open_count = await session.scalar(
            select(func.count())
            .select_from(ShadowBranchModel)
            .where(
                ShadowBranchModel.session_id == shadow_session.id,
                ShadowBranchModel.state == "open",
            )
        )
        if open_count == 0:
            shadow_session.state = "complete"
            shadow_session.completed_at = datetime.now(UTC)

    @staticmethod
    def _strategy_value(
        strategy: OptionStrategy, quotes: dict[str, dict[str, Any]], *, entry: bool
    ) -> Decimal | None:
        total = Decimal("0")
        for leg in strategy.legs:
            quote = quotes.get(leg.symbol)
            if not quote or quote.get("bid") is None or quote.get("ask") is None:
                return None
            price_key = "ask" if (leg.side.value == "buy") == entry else "bid"
            price = Decimal(str(quote[price_key]))
            direction = Decimal("1") if leg.side.value == "buy" else Decimal("-1")
            total += direction * price * leg.ratio_qty
        return total if total > 0 else None

    async def record_observation(
        self,
        session: AsyncSession,
        *,
        shadow_session_id: str,
        observed_at: datetime,
        source: str,
        feed: str,
        payload: dict[str, Any],
    ) -> ShadowObservationModel:
        digest = _digest({"session_id": shadow_session_id, "payload": payload})
        existing = await session.scalar(
            select(ShadowObservationModel).where(ShadowObservationModel.payload_digest == digest)
        )
        if existing is not None:
            return existing
        record = ShadowObservationModel(
            id=str(uuid4()),
            session_id=shadow_session_id,
            observed_at=observed_at.astimezone(UTC),
            source=source,
            feed=feed,
            payload_digest=digest,
            payload_json=json.dumps(payload, default=str, sort_keys=True),
        )
        session.add(record)
        await session.flush()
        return record

    async def record_valuation(
        self,
        session: AsyncSession,
        *,
        branch_id: str,
        observed_at: datetime,
        gross_pnl: Decimal,
        net_pnl: Decimal,
        drawdown: Decimal,
        mae: Decimal,
        mfe: Decimal,
        capital_at_risk: Decimal,
        coverage_pct: Decimal,
        confidence: str,
        exit_reason: str | None = None,
    ) -> ShadowValuationModel:
        record = ShadowValuationModel(
            id=str(uuid4()),
            branch_id=branch_id,
            observed_at=observed_at.astimezone(UTC),
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            drawdown=drawdown,
            mae=mae,
            mfe=mfe,
            capital_at_risk=capital_at_risk,
            coverage_pct=coverage_pct,
            confidence=confidence,
            exit_reason=exit_reason,
        )
        session.add(record)
        await session.flush()
        return record

    async def attach_confirmed_paper_fill(
        self,
        session: AsyncSession,
        *,
        shadow_session_id: str,
        strategy: OptionStrategy,
        filled_average_price: Decimal,
        filled_at: datetime,
    ) -> None:
        """Replace the cash chosen path only with a confirmed paper fill.

        The calling worker supplies a confirmed receipt value; this service
        never reads execution persistence or contacts Alpaca.
        """

        branch = await session.scalar(
            select(ShadowBranchModel).where(
                ShadowBranchModel.session_id == shadow_session_id,
                ShadowBranchModel.branch_key == "chosen",
            )
        )
        if branch is None:
            raise ValueError("Chosen ShadowFund branch does not exist")
        if branch.entry_cost is not None:
            return
        if filled_average_price <= 0:
            raise ValueError("Confirmed paper fill requires a positive average price")
        branch.label = "Chosen path: confirmed paper fill"
        branch.variation = "Confirmed paper fill supplied by the worker receipt."
        branch.strategy_json = strategy.model_dump_json()
        branch.entry_cost = filled_average_price
        branch.entry_at = filled_at.astimezone(UTC)
        branch.state = "open"
        branch.reason = None
        await self.record_valuation(
            session,
            branch_id=branch.id,
            observed_at=filled_at,
            gross_pnl=Decimal("0"),
            net_pnl=Decimal("0"),
            drawdown=Decimal("0"),
            mae=Decimal("0"),
            mfe=Decimal("0"),
            capital_at_risk=filled_average_price * Decimal("100"),
            coverage_pct=Decimal("100"),
            confidence="confirmed_paper_fill",
        )

    async def persist_post_analysis_batch(
        self,
        session: AsyncSession,
        *,
        source_mode: str,
        window_start: datetime,
        window_end: datetime,
        model_metadata: dict[str, Any],
        summary: dict[str, Any],
        recommendations: list[dict[str, str]],
    ) -> ShadowPostAnalysisBatchModel:
        """Persist manual-review-only, BA-bounded recommendation evidence.

        This method deliberately does not call an LLM or mutate an AI profile.
        A caller supplies validated structured research output after the one
        permitted scoring/backtest trigger.
        """

        digest = _digest(
            {
                "source_mode": source_mode,
                "window_start": window_start,
                "window_end": window_end,
                "model_metadata": model_metadata,
                "summary": summary,
                "recommendations": recommendations,
            }
        )
        existing = await session.scalar(
            select(ShadowPostAnalysisBatchModel).where(
                ShadowPostAnalysisBatchModel.input_digest == digest
            )
        )
        if existing is not None:
            return existing
        batch = ShadowPostAnalysisBatchModel(
            id=str(uuid4()),
            created_at=datetime.now(UTC),
            source_mode=source_mode,
            window_start=window_start.astimezone(UTC),
            window_end=window_end.astimezone(UTC),
            input_digest=digest,
            model_metadata_json=json.dumps(model_metadata, default=str, sort_keys=True),
            state="NO_RECOMMENDATION" if not recommendations else "DRAFT",
            summary_json=json.dumps(summary, default=str, sort_keys=True),
        )
        session.add(batch)
        await session.flush()
        ruleset = get_authorized_ruleset()
        active = ruleset.profiles[ruleset.default_profile]
        for recommendation in recommendations:
            parameter_id = recommendation.get("parameter_id", "")
            suggested = recommendation.get("suggested_value", "")
            validation_state = "REJECTED_OUTSIDE_AUTHORIZED_BOUNDS"
            current = ""
            if parameter_id in ruleset.profile_bounds:
                bound = ruleset.profile_bounds[parameter_id]
                current = str(getattr(active, parameter_id))
                try:
                    candidate = Decimal(suggested)
                    if bound.minimum <= candidate <= bound.maximum:
                        validation_state = "WITHIN_AUTHORIZED_BOUNDS"
                except Exception:
                    validation_state = "REJECTED_INVALID_VALUE"
            session.add(
                ShadowProfileRecommendationModel(
                    id=str(uuid4()),
                    batch_id=batch.id,
                    parameter_id=parameter_id,
                    current_value=current,
                    suggested_value=suggested,
                    rationale=recommendation.get("rationale", "No rationale supplied."),
                    confidence=recommendation.get("confidence", "low"),
                    validation_state=validation_state,
                    manual_review_required=True,
                )
            )
        await session.flush()
        return batch

    async def _add_candidate_branch(
        self,
        session: AsyncSession,
        shadow_session: ShadowSessionModel,
        *,
        key: str,
        label: str,
        variation: str,
        strategy: OptionStrategy | None,
        multiplier: Decimal,
    ) -> None:
        await self._add_branch(
            session,
            shadow_session,
            key=key,
            label=label,
            variation=variation,
            strategy=strategy,
            multiplier=multiplier,
            chosen_path=False,
            state="open" if strategy else "incomplete",
            reason=None if strategy else "DATA_UNAVAILABLE: no eligible deterministic strategy",
        )

    async def _add_branch(
        self,
        session: AsyncSession,
        shadow_session: ShadowSessionModel,
        *,
        key: str,
        label: str,
        variation: str,
        strategy: OptionStrategy | None,
        multiplier: Decimal,
        chosen_path: bool,
        state: str,
        reason: str | None = None,
    ) -> None:
        session.add(
            ShadowBranchModel(
                id=str(uuid4()),
                session_id=shadow_session.id,
                branch_key=key,
                label=label,
                variation=variation,
                strategy_json=strategy.model_dump_json() if strategy else None,
                allocation_multiplier=multiplier,
                entry_cost=None,
                entry_at=None,
                chosen_path=chosen_path,
                state=state,
                reason=reason,
            )
        )
        await session.flush()
