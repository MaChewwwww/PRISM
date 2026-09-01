from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.autonomous.read_service import cycle_read, execution_read, portfolio_read


def test_cycle_read_projects_only_safe_operational_fields() -> None:
    now = datetime(2026, 8, 31, 13, 30, tzinfo=UTC)
    row = SimpleNamespace(
        id=str(uuid4()),
        started_at=now,
        completed_at=now,
        outcome="NO_TRADE",
        symbols_json='["NVDA", "AMD"]',
        reason="Kill switch active",
        exit_checks_json=json.dumps([]),
        worker_version="autonomous-v1",
    )

    payload = cycle_read(row).model_dump()

    assert payload["symbols"] == ["NVDA", "AMD"]
    assert payload["reason"] == "Kill switch active"
    assert payload["exit_checks"] == []


def test_cycle_read_preserves_pnl_threshold_exit_evidence() -> None:
    now = datetime(2026, 8, 31, 13, 30, tzinfo=UTC)
    row = SimpleNamespace(
        id=str(uuid4()),
        started_at=now,
        completed_at=now,
        outcome="NO_TRADE",
        symbols_json='["NVDA"]',
        reason="Production-parity cycle completed",
        exit_checks_json=json.dumps(
            [{"symbol": "NVDA260909C00220000", "result": "exit", "reason": "pnl_threshold"}]
        ),
        worker_version="autonomous-v1",
    )

    payload = cycle_read(row).model_dump()

    assert payload["exit_checks"] == [
        {
            "symbol": "NVDA260909C00220000",
            "result": "exit",
            "reason": "pnl_threshold",
        }
    ]


def test_execution_read_omits_order_identifiers_and_broker_error_text() -> None:
    now = datetime(2026, 8, 31, 13, 30, tzinfo=UTC)
    row = SimpleNamespace(
        id=str(uuid4()),
        trace_id=str(uuid4()),
        proposal_id=str(uuid4()),
        operation="entry",
        symbol=None,
        exit_reason=None,
        requested_quantity=None,
        status="rejected",
        filled_quantity=Decimal("0"),
        filled_average_price=None,
        error_code="broker_rejected",
        error_message="provider response containing account data",
        client_order_id="private-client-order-id",
        broker_order_id="private-broker-order-id",
        created_at=now,
        submitted_at=now,
        reconciled_at=now,
    )

    serialized = execution_read(row).model_dump_json()

    assert "private-client-order-id" not in serialized
    assert "private-broker-order-id" not in serialized
    assert "provider response" not in serialized
    assert "broker_rejected" in serialized


def test_execution_read_projects_position_exit_receipt_without_proposal_id() -> None:
    now = datetime(2026, 8, 31, 13, 30, tzinfo=UTC)
    row = SimpleNamespace(
        id=str(uuid4()),
        trace_id=str(uuid4()),
        proposal_id=None,
        operation="exit",
        symbol="NVDA260909C00220000",
        exit_reason="pnl_threshold",
        requested_quantity=Decimal("1"),
        status="submitted",
        filled_quantity=Decimal("0"),
        filled_average_price=None,
        error_code=None,
        created_at=now,
        submitted_at=now,
        reconciled_at=None,
    )

    payload = execution_read(row).model_dump()

    assert payload["operation"] == "exit"
    assert payload["proposal_id"] is None
    assert payload["symbol"] == "NVDA260909C00220000"
    assert payload["exit_reason"] == "pnl_threshold"
    assert payload["requested_quantity"] == Decimal("1")


def test_portfolio_read_selects_normalized_fields_and_omits_account_payload() -> None:
    now = datetime(2026, 8, 31, 13, 30, tzinfo=UTC)
    row = SimpleNamespace(
        observed_at=now,
        account_verified=True,
        supported_options_level=3,
        payload_json=json.dumps(
            {
                "observed_at": now.isoformat(),
                "account_number": "private-account-number",
                "account_verified": True,
                "supported_options_level": 3,
                "account_values_complete": True,
                "cash": "100000.00",
                "buying_power": "200000.00",
                "portfolio_value": "100000.00",
                "start_of_day_equity": "99900.00",
                "positions": [
                    {
                        "symbol": "NVDA260904C00120000",
                        "underlying": "NVDA",
                        "asset_class": "us_option",
                        "qty": "1",
                        "market_value": "120.00",
                        "avg_entry_price": "1.10",
                        "unrealized_pl": "10.00",
                        "unrealized_plpc": "0.10",
                        "metadata_complete": True,
                        "provider_raw": "private provider payload",
                    }
                ],
            }
        ),
    )

    serialized = portfolio_read(row).model_dump_json()

    assert "private-account-number" not in serialized
    assert "private provider payload" not in serialized
    assert '"portfolio_value":"100000.00"' in serialized
    assert '"symbol":"NVDA260904C00120000"' in serialized
