from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.autonomous.worker import AutonomousWorker
from app.contracts.models import (
    OptionLeg,
    OptionPayoffEconomics,
    OptionSide,
    OptionStrategy,
    OptionType,
)
from app.portfolio.metadata import metadata_complete, parse_instrument
from app.research.historical_analogs import (
    HistoricalAnalogSummary,
    compute_option_payoff_ev,
)
from app.research.iv_rank import IvRankUnavailable, compute_iv_rank, infer_iv_observations


def test_iv_rank_requires_timestamped_sourced_history() -> None:
    now = datetime(2026, 8, 30, 13, 30, tzinfo=UTC)
    observations = [
        {
            "observed_at": now - timedelta(days=index),
            "implied_volatility": Decimal("0.20") + Decimal(index) / Decimal("1000"),
            "source": "test-provider",
        }
        for index in range(10)
    ]
    result = compute_iv_rank(
        Decimal("0.205"), observations, now=now, minimum_observations=10, lookback_days=30
    )
    assert result.observation_count == 10
    assert result.rank == Decimal("60")
    with pytest.raises(IvRankUnavailable):
        compute_iv_rank(Decimal("0.205"), observations[:2], now=now, minimum_observations=10)
    with pytest.raises(IvRankUnavailable):
        compute_iv_rank(
            Decimal("0.205"),
            [
                {
                    "observed_at": now - timedelta(days=index),
                    "implied_volatility": Decimal("0.20"),
                    "source": "illustrative_fixture",
                }
                for index in range(10)
            ],
            now=now,
            minimum_observations=10,
        )


def test_option_ev_includes_premium_slippage_and_fill_probability() -> None:
    now = datetime(2026, 8, 30, 13, 30, tzinfo=UTC)
    summary = HistoricalAnalogSummary(
        count=30,
        direction="bullish",
        expected_return_pct=Decimal("2"),
        win_rate_pct=Decimal("60"),
        net_ev_r=Decimal("1"),
        observed_from=now - timedelta(days=100),
        observed_to=now,
        outcome_returns_pct=tuple(Decimal(value) for value in ("-5", "0", "5", "10")),
    )
    strategy = OptionStrategy(
        kind="long_call",
        legs=[
            OptionLeg(
                symbol="NVDA260918C00100000",
                underlying="NVDA",
                expiration="2026-09-18",
                option_type=OptionType.CALL,
                side=OptionSide.BUY,
                strike_price=Decimal("100"),
                position_intent="buy_to_open",
            )
        ],
        limit_price=Decimal("2.00"),
    )
    result = compute_option_payoff_ev(
        summary,
        strategy,
        underlying_price=Decimal("100"),
        quotes={
            "NVDA260918C00100000": {
                "bid": Decimal("1.90"),
                "ask": Decimal("2.10"),
            }
        },
    )
    assert result.ev_method.startswith("option_payoff_")
    assert result.premium_per_contract == Decimal("200")
    assert result.slippage_per_contract == Decimal("10")
    assert result.fill_probability == Decimal("0")
    assert result.net_ev_r == Decimal("0")
    assert result.reward_risk_ratio == Decimal("0")


def test_bearish_analog_returns_are_mapped_back_to_underlying_prices() -> None:
    now = datetime(2026, 8, 30, 13, 30, tzinfo=UTC)
    summary = HistoricalAnalogSummary(
        count=30,
        direction="bearish",
        expected_return_pct=Decimal("5"),
        win_rate_pct=Decimal("100"),
        net_ev_r=Decimal("1"),
        observed_from=now - timedelta(days=100),
        observed_to=now,
        outcome_returns_pct=(Decimal("5"),),
    )
    strategy = OptionStrategy(
        kind="long_put",
        legs=[
            OptionLeg(
                symbol="NVDA260918P00100000",
                underlying="NVDA",
                expiration="2026-09-18",
                option_type=OptionType.PUT,
                side=OptionSide.BUY,
                strike_price=Decimal("100"),
                position_intent="buy_to_open",
            )
        ],
        limit_price=Decimal("2"),
    )
    result = compute_option_payoff_ev(
        summary,
        strategy,
        underlying_price=Decimal("100"),
        quotes={"NVDA260918P00100000": {"bid": Decimal("1.90"), "ask": Decimal("2.00")}},
    )
    assert result.expected_profit_per_contract is not None
    assert result.expected_profit_per_contract > 0


def test_occ_position_metadata_is_classified_without_guessing_unknowns() -> None:
    option = parse_instrument("NVDA260918C00100000")
    assert option.underlying == "NVDA"
    assert option.expiration.isoformat() == "2026-09-18"
    assert option.strike == Decimal("100")
    assert metadata_complete(option) is True
    assert metadata_complete(parse_instrument("UNKNOWN260918C00100000")) is False


def test_portfolio_snapshot_does_not_fallback_missing_account_values() -> None:
    now = datetime(2026, 8, 30, 13, 30, tzinfo=UTC)
    snapshot = AutonomousWorker._portfolio_snapshot(
        {
            "status": "ACTIVE",
            "cash": "100000",
            "buying_power": "100000",
            # Missing portfolio/equity values must not be replaced with the
            # configured starting-capital fixture.
            "last_equity": None,
        },
        [],
        now,
    )
    assert snapshot["account_values_complete"] is False
    assert snapshot["portfolio_value"] is None
    assert snapshot["start_of_day_equity"] is None


def test_option_economics_contract_can_represent_negative_expected_profit() -> None:
    economics = OptionPayoffEconomics(
        method="test",
        expected_profit_per_contract=Decimal("-1"),
        expected_loss_per_contract=Decimal("1"),
        max_loss_per_contract=Decimal("100"),
        premium_per_contract=Decimal("100"),
        slippage_per_contract=Decimal("1"),
        fill_probability=Decimal("0.5"),
        net_ev_r=Decimal("-0.01"),
        reward_risk_ratio=Decimal("0"),
    )
    assert economics.expected_profit_per_contract == Decimal("-1")


def test_iv_can_be_inverted_from_observed_alpaca_option_bars() -> None:
    now = datetime(2026, 8, 30, 13, 30, tzinfo=UTC)
    leg = OptionLeg(
        symbol="NVDA260918C00100000",
        underlying="NVDA",
        expiration="2026-09-18",
        option_type=OptionType.CALL,
        side=OptionSide.BUY,
        strike_price=Decimal("100"),
    )
    option_bars = [
        {"timestamp": now - timedelta(days=index), "close": Decimal("2.00")}
        for index in range(1, 25)
    ]
    underlying_bars = [
        {"timestamp": now - timedelta(days=index), "close": Decimal("100.00")}
        for index in range(1, 25)
    ]
    observations = infer_iv_observations(option_bars, underlying_bars, leg=leg)
    assert len(observations) == 24
    assert observations[0].implied_volatility > 0
    assert observations[0].source.startswith("alpaca_option_bars:")
