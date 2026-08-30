from __future__ import annotations

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.models import (
    AuthorizationDecision,
    ExecutionReceipt,
    ExecutionStatus,
    TradeProposal,
)
from app.core.config import Settings
from app.execution.models import ExecutionReceiptModel
from app.execution.validation import validate_authorization


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    def run(
        self, argv: list[str], stdin: str, env: dict[str, str], timeout: float
    ) -> CommandResult: ...


class ReceiptRepository(Protocol):
    def save(self, receipt: ExecutionReceipt) -> None: ...

    def find_by_client_order_id(self, client_order_id: str) -> ExecutionReceipt | None: ...

    def find_by_payload_digest(self, payload_digest: str) -> ExecutionReceipt | None: ...


class AsyncReceiptRepository(Protocol):
    async def save(self, receipt: ExecutionReceipt) -> None: ...

    async def find_by_client_order_id(self, client_order_id: str) -> ExecutionReceipt | None: ...

    async def find_by_payload_digest(self, payload_digest: str) -> ExecutionReceipt | None: ...


class SqlAlchemyReceiptRepository:
    """Durable receipt store used by the autonomous worker.

    The repository is intentionally session-scoped: every state transition is
    committed before a broker call or reconciliation attempt can proceed.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_contract(model: ExecutionReceiptModel) -> ExecutionReceipt:
        return ExecutionReceipt(
            trace_id=UUID(model.trace_id),
            proposal_id=UUID(model.proposal_id),
            client_order_id=model.client_order_id,
            broker_order_id=model.broker_order_id,
            payload_digest=model.payload_digest,
            status=ExecutionStatus(model.status),
            filled_quantity=model.filled_quantity,
            filled_average_price=model.filled_average_price,
            error_code=model.error_code,
            error_message=model.error_message,
            submitted_at=model.submitted_at,
            reconciled_at=model.reconciled_at,
        )

    async def find_by_client_order_id(self, client_order_id: str) -> ExecutionReceipt | None:
        result = await self.session.execute(
            select(ExecutionReceiptModel).where(
                ExecutionReceiptModel.client_order_id == client_order_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_contract(model) if model is not None else None

    async def find_by_payload_digest(self, payload_digest: str) -> ExecutionReceipt | None:
        result = await self.session.execute(
            select(ExecutionReceiptModel).where(
                ExecutionReceiptModel.payload_digest == payload_digest
            )
        )
        model = result.scalar_one_or_none()
        return self._to_contract(model) if model is not None else None

    async def save(self, receipt: ExecutionReceipt) -> None:
        result = await self.session.execute(
            select(ExecutionReceiptModel).where(
                ExecutionReceiptModel.client_order_id == receipt.client_order_id
            )
        )
        model = result.scalar_one_or_none()
        values = {
            "trace_id": str(receipt.trace_id),
            "proposal_id": str(receipt.proposal_id),
            "client_order_id": receipt.client_order_id,
            "broker_order_id": receipt.broker_order_id,
            "payload_digest": receipt.payload_digest,
            "status": receipt.status.value,
            "filled_quantity": receipt.filled_quantity,
            "filled_average_price": receipt.filled_average_price,
            "error_code": receipt.error_code,
            "error_message": receipt.error_message,
            "submitted_at": receipt.submitted_at,
            "reconciled_at": receipt.reconciled_at,
        }
        if model is None:
            self.session.add(
                ExecutionReceiptModel(id=str(uuid4()), created_at=datetime.now(UTC), **values)
            )
        else:
            for key, value in values.items():
                setattr(model, key, value)
        await self.session.flush()


class SubprocessRunner:
    def run(
        self, argv: list[str], stdin: str, env: dict[str, str], timeout: float
    ) -> CommandResult:
        result = subprocess.run(
            argv,
            input=stdin,
            text=True,
            capture_output=True,
            env=env,
            timeout=timeout,
            check=False,
            shell=False,
        )
        return CommandResult(result.returncode, result.stdout, result.stderr)


class InMemoryReceiptRepository:
    def __init__(self) -> None:
        self.receipts: dict[str, ExecutionReceipt] = {}

    def save(self, receipt: ExecutionReceipt) -> None:
        self.receipts[receipt.client_order_id] = receipt.model_copy(deep=True)

    def find_by_client_order_id(self, client_order_id: str) -> ExecutionReceipt | None:
        return self.receipts.get(client_order_id)

    def find_by_payload_digest(self, payload_digest: str) -> ExecutionReceipt | None:
        return next(
            (
                receipt
                for receipt in self.receipts.values()
                if receipt.payload_digest == payload_digest
            ),
            None,
        )


def verify_cli_capabilities(settings: Settings, runner: CommandRunner | None = None) -> bool:
    """Probe the pinned CLI contract without submitting an order."""
    command_runner = runner or SubprocessRunner()
    probes = (
        [settings.alpaca_cli_path, "version"],
        [settings.alpaca_cli_path, "order", "submit", "--help"],
        [settings.alpaca_cli_path, "order", "submit", "--schema"],
        [settings.alpaca_cli_path, "order", "submit", "--dry-run", "--help"],
    )
    env = os.environ.copy()
    env.update({"ALPACA_LIVE_TRADE": "false", "ALPACA_OUTPUT": "json"})
    for argv in probes:
        try:
            result = command_runner.run(
                argv,
                "",
                env,
                settings.alpaca_request_timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired, TimeoutError):
            return False
        if result.returncode != 0:
            return False
    return True


class AlpacaCliExecutionGateway:
    def __init__(self, settings: Settings, runner: CommandRunner, repository: ReceiptRepository):
        self.settings = settings
        self.runner = runner
        self.repository = repository

    def submit(
        self,
        proposal: TradeProposal,
        decision: AuthorizationDecision,
        *,
        kill_switch_active: bool | None = None,
    ) -> ExecutionReceipt:
        validate_authorization(
            proposal, decision, self.settings, kill_switch_active=kill_switch_active
        )
        existing = self.repository.find_by_payload_digest(proposal.proposal_digest)
        if existing is not None:
            if existing.status in {ExecutionStatus.PENDING, ExecutionStatus.RECONCILING}:
                return self.reconcile(existing)
            return existing
        client_order_id = f"sf-{uuid4()}"
        receipt = ExecutionReceipt(
            trace_id=proposal.trace_id,
            proposal_id=proposal.id,
            client_order_id=client_order_id,
            payload_digest=proposal.proposal_digest,
            status=ExecutionStatus.PENDING,
        )
        self.repository.save(receipt)
        payload = self._order_payload(proposal, client_order_id)
        env = self._command_environment()
        try:
            result = self.runner.run(
                [self.settings.alpaca_cli_path, "api", "POST", "/v2/orders", "--quiet"],
                json.dumps(payload, separators=(",", ":")),
                env,
                self.settings.alpaca_request_timeout_seconds,
            )
        except (subprocess.TimeoutExpired, TimeoutError):
            return self.reconcile(receipt)
        if result.returncode != 0:
            receipt.status = ExecutionStatus.FAILED
            receipt.error_code = f"alpaca_cli_exit_{result.returncode}"
            receipt.error_message = "Alpaca CLI rejected the paper order"
            self.repository.save(receipt)
            return receipt
        response = self._parse_json(result.stdout)
        if response is None:
            return self.reconcile(receipt)
        self._apply_broker_response(receipt, response)
        receipt.submitted_at = datetime.now(UTC)
        self.repository.save(receipt)
        return receipt

    async def submit_async(
        self,
        proposal: TradeProposal,
        decision: AuthorizationDecision,
        repository: AsyncReceiptRepository,
        *,
        kill_switch_active: bool | None = None,
    ) -> ExecutionReceipt:
        """Durable async variant used by the autonomous worker."""
        validate_authorization(
            proposal, decision, self.settings, kill_switch_active=kill_switch_active
        )
        existing = await repository.find_by_payload_digest(proposal.proposal_digest)
        if existing is not None:
            if existing.status in {ExecutionStatus.PENDING, ExecutionStatus.RECONCILING}:
                return await self.reconcile_async(existing, repository)
            return existing
        client_order_id = f"sf-{uuid4()}"
        receipt = ExecutionReceipt(
            trace_id=proposal.trace_id,
            proposal_id=proposal.id,
            client_order_id=client_order_id,
            payload_digest=proposal.proposal_digest,
            status=ExecutionStatus.PENDING,
        )
        await repository.save(receipt)
        await self._commit_repository(repository)
        payload = self._order_payload(proposal, client_order_id)
        try:
            result = await asyncio.to_thread(
                self.runner.run,
                [self.settings.alpaca_cli_path, "api", "POST", "/v2/orders", "--quiet"],
                json.dumps(payload, separators=(",", ":")),
                self._command_environment(),
                self.settings.alpaca_request_timeout_seconds,
            )
        except (subprocess.TimeoutExpired, TimeoutError):
            return await self.reconcile_async(receipt, repository)
        if result.returncode != 0:
            receipt.status = ExecutionStatus.FAILED
            receipt.error_code = f"alpaca_cli_exit_{result.returncode}"
            receipt.error_message = "Alpaca CLI rejected the paper order"
            await repository.save(receipt)
            await self._commit_repository(repository)
            return receipt
        response = self._parse_json(result.stdout)
        if response is None:
            return await self.reconcile_async(receipt, repository)
        self._apply_broker_response(receipt, response)
        receipt.submitted_at = datetime.now(UTC)
        await repository.save(receipt)
        await self._commit_repository(repository)
        return receipt

    async def reconcile_async(
        self, receipt: ExecutionReceipt, repository: AsyncReceiptRepository
    ) -> ExecutionReceipt:
        receipt.status = ExecutionStatus.RECONCILING
        await repository.save(receipt)
        await self._commit_repository(repository)
        try:
            result = await asyncio.to_thread(
                self.runner.run,
                [
                    self.settings.alpaca_cli_path,
                    "order",
                    "get-by-client-id",
                    "--client-order-id",
                    receipt.client_order_id,
                    "--quiet",
                ],
                "",
                self._command_environment(),
                self.settings.alpaca_request_timeout_seconds,
            )
        except (subprocess.TimeoutExpired, TimeoutError):
            result = None
        response = self._parse_json(result.stdout) if result and result.returncode == 0 else None
        if response is None:
            receipt.error_code = "submission_ambiguous"
            receipt.error_message = "Paper submission is ambiguous; operator review is required"
        else:
            self._apply_broker_response(receipt, response)
        receipt.reconciled_at = datetime.now(UTC)
        await repository.save(receipt)
        await self._commit_repository(repository)
        return receipt

    @staticmethod
    async def _commit_repository(repository: AsyncReceiptRepository) -> None:
        session = getattr(repository, "session", None)
        if session is not None:
            await session.commit()

    def reconcile(self, receipt: ExecutionReceipt) -> ExecutionReceipt:
        receipt.status = ExecutionStatus.RECONCILING
        self.repository.save(receipt)
        result = self.runner.run(
            [
                self.settings.alpaca_cli_path,
                "order",
                "get-by-client-id",
                "--client-order-id",
                receipt.client_order_id,
                "--quiet",
            ],
            "",
            self._command_environment(),
            self.settings.alpaca_request_timeout_seconds,
        )
        response = self._parse_json(result.stdout) if result.returncode == 0 else None
        if response is None:
            receipt.error_code = "submission_ambiguous"
            receipt.error_message = "Paper submission is ambiguous; operator review is required"
        else:
            self._apply_broker_response(receipt, response)
        receipt.reconciled_at = datetime.now(UTC)
        self.repository.save(receipt)
        return receipt

    def _command_environment(self) -> dict[str, str]:
        env = os.environ.copy()
        if self.settings.alpaca_api_key:
            env["ALPACA_API_KEY"] = self.settings.alpaca_api_key
        if self.settings.alpaca_secret_key:
            env["ALPACA_SECRET_KEY"] = self.settings.alpaca_secret_key
        env["ALPACA_LIVE_TRADE"] = "false"
        env["ALPACA_OUTPUT"] = "json"
        return env

    @staticmethod
    def _order_payload(proposal: TradeProposal, client_order_id: str) -> dict[str, Any]:
        strategy = proposal.strategy
        base: dict[str, Any] = {
            "qty": str(proposal.quantity),
            "type": "limit",
            "limit_price": str(strategy.limit_price),
            "time_in_force": "day",
            "client_order_id": client_order_id,
            "extended_hours": False,
        }
        if len(strategy.legs) == 1:
            leg = strategy.legs[0]
            return {
                **base,
                "symbol": leg.symbol,
                "side": "buy",
                "position_intent": leg.position_intent,
            }
        return {
            **base,
            "order_class": "mleg",
            "legs": [
                {
                    "symbol": leg.symbol,
                    "side": leg.side.value,
                    "ratio_qty": str(leg.ratio_qty),
                    "position_intent": leg.position_intent,
                }
                for leg in strategy.legs
            ],
        }

    @staticmethod
    def _parse_json(value: str) -> dict[str, Any] | None:
        try:
            result = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None
        return result if isinstance(result, dict) else None

    @staticmethod
    def _apply_broker_response(receipt: ExecutionReceipt, response: dict[str, Any]) -> None:
        receipt.broker_order_id = str(response.get("id")) if response.get("id") else None
        status = str(response.get("status", "")).lower()
        if status == "filled":
            receipt.status = ExecutionStatus.FILLED
        elif status in {"rejected", "canceled", "cancelled", "expired", "failed"}:
            receipt.status = ExecutionStatus.REJECTED
            receipt.error_code = f"broker_{status}"
            receipt.error_message = "Paper order was rejected or not accepted by the broker"
        else:
            receipt.status = ExecutionStatus.SUBMITTED
        receipt.filled_quantity = response.get("filled_qty", "0")
        receipt.filled_average_price = response.get("filled_avg_price")
