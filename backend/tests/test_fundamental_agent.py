from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from app.contracts.models import (
    AltmanZone,
    FundamentalHealth,
    ValuationStance,
)
from app.research.fundamental_data import (
    get_company_financials,
)
from app.research.fundamental_engine import (
    compute_altman_z_score,
    compute_composite_fundamental_score,
    compute_fundamental_analysis,
    compute_piotroski_f_score,
    compute_profitability_metrics,
    compute_solvency_metrics,
    compute_valuation_metrics,
)


def test_compute_profitability_metrics() -> None:
    fin = get_company_financials("NVDA")
    prof = compute_profitability_metrics(fin)

    assert prof.gross_margin_pct > Decimal("70.0")
    assert prof.operating_margin_pct > Decimal("50.0")
    assert prof.net_margin_pct > Decimal("50.0")
    assert prof.roe_pct > Decimal("50.0")
    assert prof.roa_pct > Decimal("40.0")


def test_compute_solvency_metrics() -> None:
    fin = get_company_financials("NVDA")
    solv = compute_solvency_metrics(fin)

    assert solv.current_ratio > Decimal("2.0")
    assert solv.debt_to_equity < Decimal("0.5")
    assert solv.interest_coverage_ratio > Decimal("50.0")
    assert solv.net_debt_millions < Decimal("0.0")  # Net Cash position (cash > debt)


def test_compute_valuation_metrics() -> None:
    fin = get_company_financials("NVDA")
    val, market_cap_m, ev_m = compute_valuation_metrics(fin, current_price=Decimal("120.0"))

    assert market_cap_m > Decimal("1000000.0")
    assert ev_m > Decimal("0.0")
    assert val.pe_ratio_ttm is not None and val.pe_ratio_ttm > Decimal("10.0")
    assert val.fcf_yield_pct is not None
    assert val.free_cash_flow_millions > Decimal("50000.0")


def test_compute_piotroski_f_score() -> None:
    fin = get_company_financials("NVDA")
    f_score = compute_piotroski_f_score(fin)
    assert 7 <= f_score <= 9  # NVDA is financially elite


def test_compute_altman_z_score() -> None:
    fin = get_company_financials("TSLA")
    z_score, zone = compute_altman_z_score(fin, market_cap_m=Decimal("700000.0"))

    assert z_score > Decimal("3.0")
    assert zone == AltmanZone.SAFE


def test_compute_composite_fundamental_score_and_classifications() -> None:
    fin = get_company_financials("NVDA")
    prof = compute_profitability_metrics(fin)
    solv = compute_solvency_metrics(fin)
    val, market_cap_m, _ = compute_valuation_metrics(fin, current_price=Decimal("120.0"))
    f_score = compute_piotroski_f_score(fin)
    z_score, _ = compute_altman_z_score(fin, market_cap_m)

    score, health, stance = compute_composite_fundamental_score(
        prof=prof,
        solv=solv,
        f_score=f_score,
        z_score=z_score,
        pe_ratio=val.pe_ratio_ttm,
    )

    assert score >= Decimal("75.0")
    assert health in {FundamentalHealth.EXCELLENT, FundamentalHealth.HEALTHY}
    assert stance in {
        ValuationStance.FAIRLY_VALUED,
        ValuationStance.PREMIUM,
        ValuationStance.OVERVALUED,
    }


def test_compute_fundamental_analysis_known_and_unlisted_symbols() -> None:
    trace_id = uuid4()

    # 1. Known symbol (NVDA)
    nvda_report = compute_fundamental_analysis(
        symbol="NVDA",
        latest_close=Decimal("125.50"),
        trace_id=trace_id,
    )
    assert nvda_report.symbol == "NVDA"
    assert nvda_report.current_price == Decimal("125.50")
    assert nvda_report.fundamental_health == FundamentalHealth.EXCELLENT
    assert "NVIDIA Corporation" in nvda_report.summary

    # 2. Known symbol (TSLA)
    tsla_report = compute_fundamental_analysis(
        symbol="TSLA",
        latest_close=Decimal("215.00"),
        trace_id=trace_id,
    )
    assert tsla_report.symbol == "TSLA"
    assert tsla_report.profitability.gross_margin_pct == Decimal("18.20")
    assert tsla_report.solvency.debt_to_equity == Decimal("0.15")

    # 3. Unlisted symbol fallback (PLTR)
    unlisted_report = compute_fundamental_analysis(
        symbol="PLTR",
        latest_close=Decimal("30.00"),
        trace_id=trace_id,
    )
    assert unlisted_report.symbol == "PLTR"
    assert unlisted_report.profitability.gross_margin_pct == Decimal("45.00")
    assert unlisted_report.composite_quality_score > Decimal("0.0")
    assert unlisted_report.red_flags is not None


def test_detect_balance_sheet_red_flags() -> None:
    from app.contracts.models import BalanceSheetRedFlag, SolvencyMetrics
    from app.research.fundamental_data import CompanyFinancials
    from app.research.fundamental_engine import detect_balance_sheet_red_flags

    # 1. Healthy financial profile
    healthy_fin = get_company_financials("NVDA")
    healthy_solv = compute_solvency_metrics(healthy_fin)
    healthy_flags = detect_balance_sheet_red_flags(
        healthy_fin, healthy_solv, z_score=Decimal("4.5")
    )
    assert healthy_flags == [BalanceSheetRedFlag.NONE_DETECTED]

    # 2. Distressed profile with multiple warning flags
    distressed_fin = CompanyFinancials(
        symbol="DIST",
        company_name="Distressed Corp",
        shares_outstanding_millions=Decimal("100.0"),
        revenue_ttm=Decimal("1000.0"),
        gross_profit_ttm=Decimal("200.0"),
        operating_income_ttm=Decimal("20.0"),
        net_income_ttm=Decimal("50.0"),  # Positive Net Income
        diluted_eps_ttm=Decimal("0.50"),
        total_assets=Decimal("2000.0"),
        current_assets=Decimal("400.0"),
        current_liabilities=Decimal("600.0"),  # Current Ratio < 1.0
        total_debt=Decimal("1500.0"),
        cash_and_equivalents=Decimal("50.0"),
        stockholders_equity=Decimal("400.0"),  # Debt/Equity = 1500/400 = 3.75 (> 2.0)
        operating_cash_flow_ttm=Decimal("-20.0"),  # Negative OCF < Net Income (accruals risk)
        capex_ttm=Decimal("100.0"),
        ebitda_ttm=Decimal("50.0"),
        interest_expense_ttm=Decimal("40.0"),  # EBIT/Interest = 20/40 = 0.5x (< 2.0x)
        prior_net_income=Decimal("40.0"),
        prior_operating_cash_flow=Decimal("10.0"),
        prior_total_assets=Decimal("1900.0"),
        prior_current_ratio=Decimal("0.8"),
        prior_gross_margin_pct=Decimal("20.0"),
    )
    distressed_solv = SolvencyMetrics(
        current_ratio=Decimal("0.67"),
        debt_to_equity=Decimal("3.75"),
        interest_coverage_ratio=Decimal("0.50"),
        net_debt_millions=Decimal("1450.0"),
    )
    distressed_flags = detect_balance_sheet_red_flags(
        distressed_fin, distressed_solv, z_score=Decimal("1.20")
    )

    assert BalanceSheetRedFlag.ACCRUAL_EARNINGS_DIVERGENCE in distressed_flags
    assert BalanceSheetRedFlag.WORKING_CAPITAL_DEFICIT in distressed_flags
    assert BalanceSheetRedFlag.HIGH_LEVERAGE_BURDEN in distressed_flags
    assert BalanceSheetRedFlag.INTEREST_COVERAGE_STRAIN in distressed_flags
    assert BalanceSheetRedFlag.ALTMAN_DISTRESS_RISK in distressed_flags


def test_compute_earnings_surprise_event() -> None:
    from app.contracts.models import GuidanceChange
    from app.research.fundamental_engine import compute_earnings_surprise_event

    nvda_fin = get_company_financials("NVDA")
    event = compute_earnings_surprise_event(nvda_fin)

    assert event is not None
    assert event.quarter == "Q2 2026"
    assert event.eps_actual == Decimal("0.68")
    assert event.eps_consensus == Decimal("0.64")
    assert event.eps_surprise_pct == Decimal("6.25")  # (0.68 - 0.64) / 0.64 * 100 = 6.25%
    assert event.revenue_actual_millions == Decimal("30040.0")
    assert event.revenue_surprise_pct == Decimal("4.67")
    assert event.guidance_change == GuidanceChange.RAISED
    assert event.gross_margin_surprise_bps == Decimal("120.0")
