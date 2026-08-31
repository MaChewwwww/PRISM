from __future__ import annotations

import inspect
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.backtest.historical_options import (
    HistoricalOptionContract,
    HistoricalOptionQuote,
    normalize_contract,
    normalize_quote,
    quote_map_at,
)
from app.backtest.simulator import DeterministicOptionSimulator, ReplayWindow
from app.contracts.models import OptionLeg, OptionSide, OptionStrategy, OptionType, StrategyKind
from app.market.option_selection import select_option_strategy


def _strategy() -> OptionStrategy:
    return OptionStrategy(
        kind=StrategyKind.LONG_CALL,
        legs=[
            OptionLeg(
                symbol="NVDA260904C00100000",
                underlying="NVDA",
                expiration="2026-09-04",
                option_type=OptionType.CALL,
                side=OptionSide.BUY,
                strike_price=Decimal("100"),
                position_intent="buy_to_open",
            )
        ],
        limit_price=Decimal("1.10"),
    )


def test_historical_option_inputs_normalize_to_decimal_utc() -> None:
    contract = normalize_contract(
        {
            "symbol": "nvda260904c00100000",
            "underlying": "nvda",
            "expiration": "2026-09-04",
            "strike": "100.00",
            "option_type": "call",
        }
    )
    quote = normalize_quote(
        {
            "symbol": "nvda260904c00100000",
            "timestamp": "2026-08-24T13:30:00Z",
            "bid": "1.00",
            "ask": "1.10",
        },
        feed="OPRA",
    )
    assert isinstance(contract, HistoricalOptionContract)
    assert contract.strike == Decimal("100.00")
    assert isinstance(quote, HistoricalOptionQuote)
    assert quote.bid == Decimal("1.00")
    assert quote.quote_timestamp == datetime(2026, 8, 24, 13, 30, tzinfo=UTC)
    assert len(contract.payload_digest or "") == 64
    assert len(quote.payload_digest or "") == 64


def test_historical_quote_feed_mismatch_fails_closed() -> None:
    with pytest.raises(ValueError, match="feed"):
        normalize_quote(
            {
                "symbol": "NVDA260904C00100000",
                "timestamp": "2026-08-24T13:30:00Z",
                "bid": "1.00",
                "ask": "1.10",
                "feed": "SIP",
            },
            feed="OPRA",
        )


def test_contract_availability_is_filtered_at_checkpoint() -> None:
    from app.backtest.historical_options import StaticHistoricalOptionsProvider

    provider = StaticHistoricalOptionsProvider(
        [
            normalize_contract(
                {
                    "symbol": "NVDA260904C00100000",
                    "underlying": "NVDA",
                    "expiration": "2026-09-04",
                    "strike": "100",
                    "option_type": "call",
                    "available_at": "2026-08-25T13:30:00Z",
                }
            )
        ],
        [],
    )
    start = datetime(2026, 8, 24, tzinfo=UTC)
    with pytest.raises(ValueError):
        provider.list_contracts(
            "NVDA", start=start, end=start, as_of=datetime(2026, 8, 24, 20, tzinfo=UTC)
        )
    assert provider.list_contracts(
        "NVDA", start=start, end=start, as_of=datetime(2026, 8, 25, 14, tzinfo=UTC)
    )


def test_quote_map_rejects_future_and_stale_rows() -> None:
    quote = HistoricalOptionQuote(
        symbol="NVDA260904C00100000",
        quote_timestamp=datetime(2026, 8, 24, 13, 30, tzinfo=UTC),
        bid=Decimal("1"),
        ask=Decimal("1.1"),
        feed="OPRA",
    )
    assert quote_map_at([quote], observed_at=datetime(2026, 8, 24, 13, 30, tzinfo=UTC))
    assert quote_map_at(
        [quote],
        observed_at=datetime(2026, 8, 24, 13, 30, 1, tzinfo=UTC),
        max_age_seconds=30,
    )
    assert not quote_map_at(
        [quote],
        observed_at=datetime(2026, 8, 24, 13, 30, 31, tzinfo=UTC),
        max_age_seconds=30,
    )
    assert not quote_map_at(
        [quote],
        observed_at=datetime(2026, 8, 24, 13, 31, tzinfo=UTC),
        max_age_seconds=0,
    )


def test_replay_window_is_four_sessions_with_authorized_cutoffs() -> None:
    window = ReplayWindow()
    grid = window.grid()
    assert window.sessions() == [
        datetime(2026, 8, 24, tzinfo=UTC).date(),
        datetime(2026, 8, 25, tzinfo=UTC).date(),
        datetime(2026, 8, 26, tzinfo=UTC).date(),
        datetime(2026, 8, 27, tzinfo=UTC).date(),
    ]
    assert len(grid) == 4 * 79
    assert grid[0] == datetime(2026, 8, 24, 13, 30, tzinfo=UTC)
    assert grid[-1] == datetime(2026, 8, 27, 20, tzinfo=UTC)
    assert window.is_entry_allowed(datetime(2026, 8, 26, 19, 55, tzinfo=UTC))
    assert not window.is_entry_allowed(datetime(2026, 8, 26, 20, tzinfo=UTC))
    assert not window.is_entry_allowed(datetime(2026, 8, 27, 13, 30, tzinfo=UTC))


def test_option_selection_uses_entry_touches_for_simulation() -> None:
    now = datetime(2026, 8, 24, 13, 30, tzinfo=UTC)
    contracts = [
        {
            "symbol": "NVDA260904C00100000",
            "underlying": "NVDA",
            "expiration": "2026-09-04",
            "strike": "100",
            "option_type": "call",
            "active": True,
            "tradable": True,
        }
    ]
    quotes = {
        contracts[0]["symbol"]: {
            "bid": Decimal("1.00"),
            "ask": Decimal("1.10"),
            "quote_timestamp": now,
        }
    }
    strategy = select_option_strategy(
        contracts,
        quotes,
        underlying_price=Decimal("100"),
        direction="bullish",
        structure="long",
        now=now,
        pricing="entry_touch",
    )
    assert strategy.limit_price == Decimal("1.10")


def test_simulator_records_touch_fill_and_take_profit() -> None:
    strategy = _strategy()
    quotes = [
        HistoricalOptionQuote(
            symbol=strategy.legs[0].symbol,
            quote_timestamp=datetime(2026, 8, 24, 13, 30, tzinfo=UTC),
            bid=Decimal("1.00"),
            ask=Decimal("1.10"),
            feed="OPRA",
        ),
        HistoricalOptionQuote(
            symbol=strategy.legs[0].symbol,
            quote_timestamp=datetime(2026, 8, 24, 13, 35, tzinfo=UTC),
            bid=Decimal("2.00"),
            ask=Decimal("2.10"),
            feed="OPRA",
        ),
    ]
    result = DeterministicOptionSimulator().replay(
        strategy,
        quotes,
        window=ReplayWindow(),
        exit_policy_json='{"take_profit_pct":"75","stop_loss_pct":"50","dte_threshold":7}',
    )
    assert result.fill.status == "filled"
    assert result.fill.entry_price == Decimal("1.10")
    assert result.fill.exit_price == Decimal("2.00")
    assert result.fill.exit_reason == "TAKE_PROFIT"
    assert result.valuations[0].net_pnl == Decimal("-10.00")


def test_simulator_applies_max_hold_after_daily_replay() -> None:
    strategy = _strategy()
    quotes = [
        HistoricalOptionQuote(
            symbol=strategy.legs[0].symbol,
            quote_timestamp=timestamp,
            bid=Decimal("1.00"),
            ask=Decimal("1.10"),
            feed="OPRA",
        )
        for timestamp in (
            datetime(2026, 8, 24, 13, 30, tzinfo=UTC),
            datetime(2026, 8, 25, 13, 30, tzinfo=UTC),
        )
    ]
    result = DeterministicOptionSimulator().replay(
        strategy,
        quotes,
        window=ReplayWindow(),
        exit_policy_json='{"take_profit_pct":"75","stop_loss_pct":"50","dte_threshold":2,"max_hold_days":1}',
    )
    assert result.fill.status == "filled"
    assert result.fill.exit_reason == "MAX_HOLD"


def test_backtest_modules_have_no_execution_dependency() -> None:
    from app.backtest import run, simulator, virtual_authorization

    source = "".join(
        inspect.getsource(module) for module in (run, simulator, virtual_authorization)
    )
    assert "app.execution" not in source
    assert "autonomous.worker" not in source
