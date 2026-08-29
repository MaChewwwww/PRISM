from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from app.contracts.models import (
    AuthorizationDecision,
    ExecutionReceipt,
    ExecutionStatus,
    TradeProposal,
)
from app.core.config import Settings
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


class AlpacaCliExecutionGateway:
    def __init__(self, settings: Settings, runner: CommandRunner, repository: ReceiptRepository):
        self.settings = settings
        self.runner = runner
        self.repository = repository

    def submit(self, proposal: TradeProposal, decision: AuthorizationDecision) -> ExecutionReceipt:
        validate_authorization(proposal, decision, self.settings)
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
            return {**base, "symbol": leg.symbol, "side": "buy"}
        return {
            **base,
            "order_class": "mleg",
            "legs": [
                {"symbol": leg.symbol, "side": leg.side.value, "ratio_qty": str(leg.ratio_qty)}
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
        status = str(response.get("status", "submitted"))
        receipt.status = ExecutionStatus.FILLED if status == "filled" else ExecutionStatus.SUBMITTED
        receipt.filled_quantity = response.get("filled_qty", "0")
        receipt.filled_average_price = response.get("filled_avg_price")
