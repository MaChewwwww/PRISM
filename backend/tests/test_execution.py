from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from app.contracts.models import (
    AllowedOrderPayload,
    AuthorizationDecision,
    AuthorizationOutcome,
    MarketRegime,
    OptionLeg,
    OptionSide,
    OptionStrategy,
    OptionType,
    PortfolioRiskState,
    StrategyKind,
    TradeProposal,
)
from app.core.config import Settings
from app.execution.cli_gateway import (
    AlpacaCliExecutionGateway,
    CommandResult,
    InMemoryReceiptRepository,
    verify_cli_capabilities,
)
from app.execution.validation import ExecutionRejected, validate_authorization, validate_strategy


class RecordingRunner:
    def __init__(self, results: list[CommandResult | BaseException] | None = None):
        self.results = results or [CommandResult(0, '{"id":"broker-1","status":"accepted"}', "")]
        self.calls: list[tuple[list[str], str, dict[str, str], float]] = []

    def run(
        self, argv: list[str], stdin: str, env: dict[str, str], timeout: float
    ) -> CommandResult:
        self.calls.append((argv, stdin, env, timeout))
        result = self.results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


class AsyncInMemoryReceiptRepository:
    def __init__(self) -> None:
        self.receipts: dict[str, Any] = {}

    async def save(self, receipt: Any) -> None:
        self.receipts[receipt.client_order_id] = receipt.model_copy(deep=True)

    async def find_by_client_order_id(self, client_order_id: str) -> Any | None:
        return self.receipts.get(client_order_id)

    async def find_by_payload_digest(self, payload_digest: str) -> Any | None:
        return next(
            (
                receipt
                for receipt in self.receipts.values()
                if receipt.payload_digest == payload_digest
            ),
            None,
        )


def build_proposal(kind: StrategyKind = StrategyKind.LONG_CALL) -> TradeProposal:
    trace_id = uuid4()
    is_spread = kind in {StrategyKind.CALL_DEBIT_SPREAD, StrategyKind.PUT_DEBIT_SPREAD}
    option_type = (
        OptionType.PUT
        if kind in {StrategyKind.LONG_PUT, StrategyKind.PUT_DEBIT_SPREAD}
        else OptionType.CALL
    )
    long_strike = Decimal("105") if option_type == OptionType.PUT and is_spread else Decimal("100")
    short_strike = Decimal("100") if option_type == OptionType.PUT else Decimal("105")
    legs = [
        OptionLeg(
            symbol="SPY270115C00100000",
            underlying="SPY",
            expiration="2027-01-15",
            option_type=option_type,
            side=OptionSide.BUY,
            strike_price=long_strike,
            position_intent="buy_to_open",
        )
    ]
    if is_spread:
        legs.append(
            OptionLeg(
                symbol="SPY270115C00105000",
                underlying="SPY",
                expiration="2027-01-15",
                option_type=option_type,
                side=OptionSide.SELL,
                strike_price=short_strike,
                position_intent="sell_to_open",
            )
        )
    return TradeProposal(
        trace_id=trace_id,
        research_report_id=uuid4(),
        symbol="SPY",
        strategy=OptionStrategy(kind=kind, legs=legs, limit_price=Decimal("2.50")),
        quantity=1,
        rationale="Test fixture",
        research_bundle_digest=hashlib.sha256(b"research-bundle").hexdigest(),
        proposal_digest=hashlib.sha256(b"proposal").hexdigest(),
    )


def build_decision(proposal: TradeProposal, **updates: object) -> AuthorizationDecision:
    values: dict[str, object] = {
        "trace_id": proposal.trace_id,
        "proposal_id": proposal.id,
        "proposal_version": proposal.proposal_version,
        "proposal_digest": proposal.proposal_digest,
        "ruleset_id": "prism-authorized-baseline",
        "ruleset_version": "rules-v1",
        "profile_id": uuid4(),
        "profile_version": 1,
        "outcome": AuthorizationOutcome.APPROVE,
        "allowed_order_payload_digest": proposal.proposal_digest,
        "allowed_order_payload": {
            "symbol": proposal.symbol,
            "strategy": proposal.strategy,
            "quantity": proposal.quantity,
        },
        "market_snapshot_digest": "1" * 64,
        "portfolio_snapshot_digest": "2" * 64,
        "market_regime": MarketRegime.NORMAL,
        "portfolio_risk_state": PortfolioRiskState.NORMAL,
        "expires_at": datetime.now(UTC) + timedelta(minutes=1),
        "account_observed_at": datetime.now(UTC),
        "supported_options_level": 3,
        "account_verified": True,
        "rule_trace": [
            {
                "trace_id": proposal.trace_id,
                "proposal_id": proposal.id,
                "rule_id": "P0-TEST",
                "priority": "P0",
                "ruleset_version": "rules-v1",
                "outcome": "PASS",
                "reason_codes": [],
                "explanation": "test",
                "input_snapshot_digest": "3" * 64,
            }
        ],
    }
    values.update(updates)
    values["allowed_order_payload_digest"] = hashlib.sha256(
        json.dumps(
            AllowedOrderPayload.model_validate(values["allowed_order_payload"]).model_dump(
                mode="json"
            ),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return AuthorizationDecision(**values)


def execution_settings(**updates: Any) -> Settings:
    values: dict[str, Any] = {
        "_env_file": None,
        "execution_enabled": True,
        "execution_kill_switch": False,
        "active_ruleset_version": "rules-v1",
        "alpaca_api_key": "paper-key",
        "alpaca_secret_key": "paper-secret",
    }
    values.update(updates)
    return Settings(**values)


@pytest.mark.parametrize(
    ("decision_updates", "message"),
    [
        ({"outcome": AuthorizationOutcome.REJECT}, "not approved"),
        (
            {"outcome": AuthorizationOutcome.MODIFIED_PENDING_ACCEPTANCE},
            "not approved",
        ),
        ({"proposal_digest": "0" * 64}, "does not match"),
        (
            {
                "allowed_order_payload": {
                    "symbol": "SPY",
                    "strategy": build_proposal().strategy,
                    "quantity": 2,
                }
            },
            "Authorized payload does not match",
        ),
        ({"expires_at": datetime.now(UTC) - timedelta(seconds=1)}, "expired"),
        ({"account_observed_at": datetime.now(UTC) - timedelta(minutes=5)}, "not fresh"),
        ({"supported_options_level": 1}, "insufficient"),
    ],
)
def test_frs_010_rejected_decisions_never_invoke_cli(
    decision_updates: dict[str, object], message: str
) -> None:
    proposal = build_proposal()
    runner = RecordingRunner()
    gateway = AlpacaCliExecutionGateway(execution_settings(), runner, InMemoryReceiptRepository())
    with pytest.raises(ExecutionRejected, match=message):
        gateway.submit(proposal, build_decision(proposal, **decision_updates))
    assert runner.calls == []


def test_frs_011_submits_json_stdin_without_shell_command() -> None:
    proposal = build_proposal(StrategyKind.CALL_DEBIT_SPREAD)
    runner = RecordingRunner()
    gateway = AlpacaCliExecutionGateway(execution_settings(), runner, InMemoryReceiptRepository())
    receipt = gateway.submit(proposal, build_decision(proposal))
    argv, body, env, _ = runner.calls[0]
    assert argv[1:] == ["api", "POST", "/v2/orders", "--quiet"]
    assert '"order_class":"mleg"' in body
    assert "paper-secret" not in " ".join(argv)
    assert env["ALPACA_LIVE_TRADE"] == "false"
    assert receipt.broker_order_id == "broker-1"


def test_cli_capability_probe_is_non_mutating() -> None:
    runner = RecordingRunner([CommandResult(0, "ok", "") for _ in range(4)])
    assert verify_cli_capabilities(Settings(_env_file=None), runner)
    assert [call[0][1:] for call in runner.calls] == [
        ["version"],
        ["order", "submit", "--help"],
        ["order", "submit", "--schema"],
        ["order", "submit", "--dry-run", "--help"],
    ]


def test_frs_013_timeout_reconciles_without_resubmission() -> None:
    proposal = build_proposal()
    runner = RecordingRunner(
        [
            subprocess.TimeoutExpired("alpaca", 1),
            CommandResult(0, '{"id":"recovered","status":"accepted"}', ""),
        ]
    )
    gateway = AlpacaCliExecutionGateway(execution_settings(), runner, InMemoryReceiptRepository())
    receipt = gateway.submit(proposal, build_decision(proposal))
    assert len(runner.calls) == 2
    assert runner.calls[1][0][1] == "order"
    assert "get-by-client-id" in runner.calls[1][0]
    assert receipt.broker_order_id == "recovered"


def test_nfrs_004_duplicate_intent_reuses_persisted_receipt() -> None:
    proposal = build_proposal()
    runner = RecordingRunner()
    repository = InMemoryReceiptRepository()
    gateway = AlpacaCliExecutionGateway(execution_settings(), runner, repository)
    decision = build_decision(proposal)
    first = gateway.submit(proposal, decision)
    second = gateway.submit(proposal, decision)
    assert first.client_order_id == second.client_order_id
    assert len(runner.calls) == 1


def test_frs_014_kill_switch_prevents_invocation() -> None:
    proposal = build_proposal()
    runner = RecordingRunner()
    gateway = AlpacaCliExecutionGateway(
        execution_settings(execution_kill_switch=True), runner, InMemoryReceiptRepository()
    )
    with pytest.raises(ExecutionRejected, match="kill-switched"):
        gateway.submit(proposal, build_decision(proposal))
    assert not runner.calls


def test_broker_rejection_is_not_reported_as_submitted() -> None:
    proposal = build_proposal()
    runner = RecordingRunner([CommandResult(0, '{"id":"broker-2","status":"rejected"}', "")])
    gateway = AlpacaCliExecutionGateway(execution_settings(), runner, InMemoryReceiptRepository())
    receipt = gateway.submit(proposal, build_decision(proposal))
    assert receipt.status.value == "rejected"
    assert receipt.error_code == "broker_rejected"


def test_position_close_persists_an_exit_receipt_without_sending_internal_client_id() -> None:
    runner = RecordingRunner([CommandResult(0, '{"id":"close-1","status":"accepted"}', "")])
    repository = AsyncInMemoryReceiptRepository()
    gateway = AlpacaCliExecutionGateway(execution_settings(), runner, None)  # type: ignore[arg-type]

    receipt = asyncio.run(
        gateway.close_position_async(
            "nvda260909c00220000",
            trace_id=uuid4(),
            exit_reason="pnl_threshold",
            requested_quantity=Decimal("1"),
            repository=repository,
        )
    )

    argv, body, _, _ = runner.calls[0]
    assert argv[1:] == ["api", "DELETE", "/v2/positions/NVDA260909C00220000"]
    assert body == ""
    assert receipt.operation.value == "exit"
    assert receipt.proposal_id is None
    assert receipt.symbol == "NVDA260909C00220000"
    assert receipt.exit_reason.value == "pnl_threshold"
    assert receipt.status.value == "submitted"
    assert receipt.broker_order_id == "close-1"
    assert receipt.client_order_id not in " ".join(argv)

    second = asyncio.run(
        gateway.close_position_async(
            "NVDA260909C00220000",
            trace_id=uuid4(),
            exit_reason="pnl_threshold",
            requested_quantity=Decimal("1"),
            repository=repository,
        )
    )
    assert second.client_order_id == receipt.client_order_id
    assert len(runner.calls) == 1


def test_close_position_async_retries_after_failure() -> None:
    runner = RecordingRunner(
        [
            CommandResult(1, "", "transient error"),
            CommandResult(0, '{"id":"close-2","status":"accepted"}', ""),
        ]
    )
    gateway = AlpacaCliExecutionGateway(execution_settings(), runner, InMemoryReceiptRepository())
    repository = AsyncInMemoryReceiptRepository()

    first = asyncio.run(
        gateway.close_position_async(
            "NVDA260909C00225000",
            trace_id=uuid4(),
            exit_reason="dte_threshold",
            requested_quantity=Decimal("4"),
            repository=repository,
        )
    )
    assert first.status.value == "failed"
    assert first.error_code == "alpaca_cli_exit_1"
    assert len(runner.calls) == 1

    second = asyncio.run(
        gateway.close_position_async(
            "NVDA260909C00225000",
            trace_id=uuid4(),
            exit_reason="dte_threshold",
            requested_quantity=Decimal("4"),
            repository=repository,
        )
    )
    assert second.status.value == "submitted"
    assert second.broker_order_id == "close-2"
    assert len(runner.calls) == 2


def test_frs_009_autonomous_trading_window_blocks_out_of_window_authorization() -> None:
    proposal = build_proposal()
    window_now = datetime(2026, 8, 31, 13, 30, tzinfo=UTC)
    decision = build_decision(
        proposal,
        decision_at=window_now,
        expires_at=window_now + timedelta(minutes=1),
        account_observed_at=window_now,
    )
    settings = execution_settings(
        autonomous_trading_enabled=True,
        autonomous_trading_start_at="2026-08-31T13:30:00Z",
        autonomous_trading_end_at="2026-09-03T20:00:00Z",
    )

    with pytest.raises(ExecutionRejected, match="Autonomous trading window is not active"):
        validate_authorization(
            proposal,
            decision,
            settings,
            now=datetime(2026, 8, 31, 13, 29, 59, tzinfo=UTC),
        )

    validate_authorization(
        proposal,
        decision,
        settings,
        now=window_now,
    )


def test_frs_007_rejects_uncovered_short() -> None:
    proposal = build_proposal()
    proposal.strategy.legs[0].side = OptionSide.SELL
    with pytest.raises(ExecutionRejected, match="long call or long put"):
        validate_strategy(proposal.strategy)


@pytest.mark.parametrize("mutation", ["ratio", "underlying", "expiration", "both_buy", "credit"])
def test_frs_007_rejects_malformed_spreads(mutation: str) -> None:
    proposal = build_proposal(StrategyKind.CALL_DEBIT_SPREAD)
    long_leg, short_leg = proposal.strategy.legs
    if mutation == "ratio":
        short_leg.ratio_qty = 2
    elif mutation == "underlying":
        short_leg.underlying = "QQQ"
    elif mutation == "expiration":
        short_leg.expiration = "2027-02-19"
    elif mutation == "both_buy":
        short_leg.side = OptionSide.BUY
    else:
        long_leg.strike_price = Decimal("110")
    with pytest.raises(ExecutionRejected):
        validate_strategy(proposal.strategy)


def test_frs_008_spread_requires_level_three() -> None:
    proposal = build_proposal(StrategyKind.PUT_DEBIT_SPREAD)
    runner = RecordingRunner()
    gateway = AlpacaCliExecutionGateway(execution_settings(), runner, InMemoryReceiptRepository())
    with pytest.raises(ExecutionRejected, match="insufficient"):
        gateway.submit(proposal, build_decision(proposal, supported_options_level=2))
    assert not runner.calls
