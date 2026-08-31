from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.contracts.models import (
    AltmanZone,
    BalanceSheetRedFlag,
    EarningsSurpriseEvent,
    FundamentalAnalysisReport,
    FundamentalHealth,
    ProfitabilityMetrics,
    SolvencyMetrics,
    ValuationMetrics,
    ValuationStance,
)
from app.research.fundamental_data import CompanyFinancials, get_company_financials


def _to_decimal(val: Any) -> Decimal:
    return Decimal(str(val))


def compute_profitability_metrics(fin: CompanyFinancials) -> ProfitabilityMetrics:
    """Compute margins and capital efficiency ratios."""
    rev = fin.revenue_ttm if fin.revenue_ttm > Decimal("0.0") else Decimal("1.0")
    equity = (
        fin.stockholders_equity if fin.stockholders_equity != Decimal("0.0") else Decimal("1.0")
    )
    assets = fin.total_assets if fin.total_assets > Decimal("0.0") else Decimal("1.0")

    gross_margin = (fin.gross_profit_ttm / rev) * Decimal("100.0")
    op_margin = (fin.operating_income_ttm / rev) * Decimal("100.0")
    net_margin = (fin.net_income_ttm / rev) * Decimal("100.0")
    roe = (fin.net_income_ttm / equity) * Decimal("100.0")
    roa = (fin.net_income_ttm / assets) * Decimal("100.0")

    return ProfitabilityMetrics(
        gross_margin_pct=round(gross_margin, 2),
        operating_margin_pct=round(op_margin, 2),
        net_margin_pct=round(net_margin, 2),
        roe_pct=round(roe, 2),
        roa_pct=round(roa, 2),
    )


def compute_solvency_metrics(fin: CompanyFinancials) -> SolvencyMetrics:
    """Compute liquidity, leverage, and debt coverage metrics."""
    curr_liab = (
        fin.current_liabilities if fin.current_liabilities > Decimal("0.0") else Decimal("1.0")
    )
    equity = (
        fin.stockholders_equity if fin.stockholders_equity != Decimal("0.0") else Decimal("1.0")
    )
    int_exp = fin.interest_expense_ttm

    curr_ratio = fin.current_assets / curr_liab
    debt_equity = fin.total_debt / equity
    int_coverage = (
        fin.operating_income_ttm / int_exp
        if int_exp > Decimal("0")
        else (Decimal("999.99") if fin.operating_income_ttm > Decimal("0") else Decimal("0"))
    )
    net_debt = fin.total_debt - fin.cash_and_equivalents

    return SolvencyMetrics(
        current_ratio=round(curr_ratio, 2),
        debt_to_equity=round(debt_equity, 2),
        interest_coverage_ratio=round(int_coverage, 2),
        net_debt_millions=round(net_debt, 2),
    )


def compute_valuation_metrics(
    fin: CompanyFinancials, current_price: Decimal
) -> tuple[ValuationMetrics, Decimal, Decimal]:
    """Compute valuation multiples and return (metrics, market_cap_m, enterprise_val_m)."""
    market_cap_m = (current_price * fin.shares_outstanding_millions) / Decimal("1.0")
    ev_m = market_cap_m + fin.total_debt - fin.cash_and_equivalents
    fcf_m = fin.operating_cash_flow_ttm - fin.capex_ttm

    pe_ratio = (
        round(current_price / fin.diluted_eps_ttm, 2)
        if fin.diluted_eps_ttm > Decimal("0.0")
        else None
    )
    ev_to_ebitda = (
        round(ev_m / fin.ebitda_ttm, 2)
        if fin.ebitda_ttm > Decimal("0.0") and ev_m > Decimal("0.0")
        else None
    )
    pb_ratio = (
        round(market_cap_m / fin.stockholders_equity, 2)
        if fin.stockholders_equity > Decimal("0.0") and market_cap_m > Decimal("0.0")
        else None
    )
    fcf_yield = (
        round((fcf_m / market_cap_m) * Decimal("100.0"), 2)
        if market_cap_m > Decimal("0.0")
        else None
    )

    val_metrics = ValuationMetrics(
        pe_ratio_ttm=pe_ratio,
        ev_to_ebitda=ev_to_ebitda,
        price_to_book=pb_ratio,
        fcf_yield_pct=fcf_yield,
        free_cash_flow_millions=round(fcf_m, 2),
    )
    return val_metrics, round(market_cap_m, 2), round(ev_m, 2)


def compute_piotroski_f_score(fin: CompanyFinancials) -> int:
    """Compute 9-point Piotroski F-Score evaluating profitability, leverage, and efficiency."""
    score = 0
    # 1. Net Income > 0
    if fin.net_income_ttm > Decimal("0.0"):
        score += 1
    # 2. Operating Cash Flow > 0
    if fin.operating_cash_flow_ttm > Decimal("0.0"):
        score += 1
    # 3. Quality of earnings: OCF > Net Income (low accruals)
    if fin.operating_cash_flow_ttm > fin.net_income_ttm:
        score += 1
    # 4. ROA increased YoY
    curr_roa = (
        fin.net_income_ttm / fin.total_assets
        if fin.total_assets > Decimal("0.0")
        else Decimal("0.0")
    )
    prior_roa = (
        fin.prior_net_income / fin.prior_total_assets
        if fin.prior_total_assets > Decimal("0.0")
        else Decimal("0.0")
    )
    if curr_roa > prior_roa:
        score += 1
    # 5. Long-term debt didn't increase significantly
    if fin.total_debt <= (fin.total_assets * Decimal("0.5")):
        score += 1
    # 6. Current ratio improved or healthy (> 1.5)
    curr_ratio = (
        fin.current_assets / fin.current_liabilities
        if fin.current_liabilities > Decimal("0.0")
        else Decimal("1.0")
    )
    if curr_ratio >= fin.prior_current_ratio or curr_ratio >= Decimal("1.5"):
        score += 1
    # 7. No major share dilution.  Unknown share history is not a pass.
    if (
        fin.prior_shares_outstanding_millions is not None
        and fin.prior_shares_outstanding_millions > Decimal("0")
        and fin.shares_outstanding_millions
        <= fin.prior_shares_outstanding_millions * Decimal("1.05")
    ):
        score += 1
    # 8. Gross margin improved or very strong (> 40%)
    curr_gm = (
        (fin.gross_profit_ttm / fin.revenue_ttm) * Decimal("100.0")
        if fin.revenue_ttm > Decimal("0.0")
        else Decimal("0.0")
    )
    if curr_gm >= fin.prior_gross_margin_pct or curr_gm >= Decimal("40.0"):
        score += 1
    # 9. Asset turnover healthy
    curr_turnover = (
        fin.revenue_ttm / fin.total_assets if fin.total_assets > Decimal("0.0") else Decimal("0.0")
    )
    if curr_turnover >= Decimal("0.3"):
        score += 1

    return min(9, max(0, score))


def compute_altman_z_score(
    fin: CompanyFinancials, market_cap_m: Decimal
) -> tuple[Decimal, AltmanZone]:
    """Compute Altman Z-Score for non-financial corporate default risk."""
    total_assets = fin.total_assets if fin.total_assets > Decimal("0.0") else Decimal("1.0")
    working_cap = fin.current_assets - fin.current_liabilities
    # Retained earnings must come from the filing.  A missing value contributes
    # zero rather than an arbitrary percentage of equity.
    retained_est = fin.retained_earnings or Decimal("0")
    ebit = fin.operating_income_ttm
    market_val_equity = market_cap_m if market_cap_m > Decimal("0.0") else fin.stockholders_equity
    total_liab = fin.total_debt + fin.current_liabilities
    if total_liab <= Decimal("0.0"):
        total_liab = Decimal("1.0")
    sales = fin.revenue_ttm

    # Standard Altman Z-Score formula:
    # Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 0.999*X5
    x1 = working_cap / total_assets
    x2 = retained_est / total_assets
    x3 = ebit / total_assets
    x4 = market_val_equity / total_liab
    x5 = sales / total_assets

    z = (
        (Decimal("1.2") * x1)
        + (Decimal("1.4") * x2)
        + (Decimal("3.3") * x3)
        + (Decimal("0.6") * x4)
        + (Decimal("0.999") * x5)
    )
    z_score = round(z, 2)

    if z_score >= Decimal("3.0"):
        zone = AltmanZone.SAFE
    elif z_score >= Decimal("1.8"):
        zone = AltmanZone.GREY
    else:
        zone = AltmanZone.DISTRESS

    return z_score, zone


def compute_composite_fundamental_score(
    prof: ProfitabilityMetrics,
    solv: SolvencyMetrics,
    f_score: int,
    z_score: Decimal,
    pe_ratio: Decimal | None,
) -> tuple[Decimal, FundamentalHealth, ValuationStance]:
    """Compute composite 0-100 fundamental quality score, health category, and valuation stance."""
    # 1. Profitability Factor (30 pts max)
    prof_pts = min(
        Decimal("30.0"),
        max(
            Decimal("0.0"), (prof.net_margin_pct * Decimal("0.6")) + (prof.roe_pct * Decimal("0.4"))
        ),
    )

    # 2. Solvency Factor (30 pts max)
    solv_pts = Decimal("0.0")
    if solv.current_ratio >= Decimal("1.5"):
        solv_pts += Decimal("10.0")
    elif solv.current_ratio >= Decimal("1.0"):
        solv_pts += Decimal("5.0")

    if solv.debt_to_equity <= Decimal("0.5"):
        solv_pts += Decimal("10.0")
    elif solv.debt_to_equity <= Decimal("1.5"):
        solv_pts += Decimal("5.0")

    if solv.interest_coverage_ratio >= Decimal("5.0"):
        solv_pts += Decimal("10.0")
    elif solv.interest_coverage_ratio >= Decimal("2.0"):
        solv_pts += Decimal("5.0")

    # 3. Piotroski & Altman Quality Factor (25 pts max)
    f_pts = (Decimal(str(f_score)) / Decimal("9.0")) * Decimal("15.0")
    z_pts = min(Decimal("10.0"), max(Decimal("0.0"), (z_score / Decimal("4.0")) * Decimal("10.0")))

    # 4. Valuation Quality (15 pts max)
    val_pts = Decimal("10.0")
    if pe_ratio is not None:
        if pe_ratio < Decimal("15.0"):
            val_pts = Decimal("15.0")
            stance = ValuationStance.UNDERVALUED
        elif pe_ratio <= Decimal("30.0"):
            val_pts = Decimal("12.0")
            stance = ValuationStance.FAIRLY_VALUED
        elif pe_ratio <= Decimal("55.0"):
            val_pts = Decimal("8.0")
            stance = ValuationStance.PREMIUM
        else:
            val_pts = Decimal("5.0")
            stance = ValuationStance.OVERVALUED
    else:
        stance = ValuationStance.FAIRLY_VALUED

    total_score = min(
        Decimal("100.0"),
        max(Decimal("0.0"), round(prof_pts + solv_pts + f_pts + z_pts + val_pts, 1)),
    )

    # Determine Health Category
    if total_score >= Decimal("80.0"):
        health = FundamentalHealth.EXCELLENT
    elif total_score >= Decimal("65.0"):
        health = FundamentalHealth.HEALTHY
    elif total_score >= Decimal("45.0"):
        health = FundamentalHealth.MODERATE
    elif total_score >= Decimal("30.0"):
        health = FundamentalHealth.VULNERABLE
    else:
        health = FundamentalHealth.DISTRESSED

    return total_score, health, stance


def detect_balance_sheet_red_flags(
    fin: CompanyFinancials,
    solv: SolvencyMetrics,
    z_score: Decimal,
) -> list[BalanceSheetRedFlag]:
    """Deterministically audit balance sheet and cash flows for credit/liquidity red flags."""
    flags: list[BalanceSheetRedFlag] = []

    # 1. Earnings quality: Operating cash flow < 70% of Net Income (severe accruals divergence)
    if fin.net_income_ttm > Decimal("0.0") and fin.operating_cash_flow_ttm < (
        fin.net_income_ttm * Decimal("0.70")
    ):
        flags.append(BalanceSheetRedFlag.ACCRUAL_EARNINGS_DIVERGENCE)

    # 2. Liquidity: Current ratio < 1.0 (working capital deficit)
    if solv.current_ratio < Decimal("1.0"):
        flags.append(BalanceSheetRedFlag.WORKING_CAPITAL_DEFICIT)

    # 3. Solvency: Debt-to-Equity > 2.0 (high leverage burden)
    if solv.debt_to_equity > Decimal("2.0"):
        flags.append(BalanceSheetRedFlag.HIGH_LEVERAGE_BURDEN)

    # 4. Debt service: Interest coverage < 2.0x (coverage strain)
    if solv.interest_coverage_ratio < Decimal("2.0"):
        flags.append(BalanceSheetRedFlag.INTEREST_COVERAGE_STRAIN)

    # 5. Bankruptcy/distress risk: Altman Z < 1.80
    if z_score < Decimal("1.80"):
        flags.append(BalanceSheetRedFlag.ALTMAN_DISTRESS_RISK)

    if not flags:
        flags.append(BalanceSheetRedFlag.NONE_DETECTED)

    return flags


def compute_earnings_surprise_event(fin: CompanyFinancials) -> EarningsSurpriseEvent | None:
    """Compute quantified EPS/revenue surprise percentages and event details."""
    if fin.eps_actual is None and fin.revenue_actual is None:
        return None

    eps_surprise: Decimal | None = None
    if (
        fin.eps_actual is not None
        and fin.eps_consensus is not None
        and fin.eps_consensus != Decimal("0.0")
    ):
        eps_diff = fin.eps_actual - fin.eps_consensus
        eps_surprise = round((eps_diff / abs(fin.eps_consensus)) * Decimal("100.0"), 2)

    rev_surprise: Decimal | None = None
    if (
        fin.revenue_actual is not None
        and fin.revenue_consensus is not None
        and fin.revenue_consensus > Decimal("0.0")
    ):
        rev_diff = fin.revenue_actual - fin.revenue_consensus
        rev_surprise = round((rev_diff / fin.revenue_consensus) * Decimal("100.0"), 2)

    return EarningsSurpriseEvent(
        quarter=fin.quarter,
        eps_actual=fin.eps_actual,
        eps_consensus=fin.eps_consensus,
        eps_surprise_pct=eps_surprise,
        revenue_actual_millions=fin.revenue_actual,
        revenue_consensus_millions=fin.revenue_consensus,
        revenue_surprise_pct=rev_surprise,
        guidance_change=fin.guidance_change,
        gross_margin_surprise_bps=fin.gross_margin_surprise_bps,
        operating_margin_surprise_bps=fin.operating_margin_surprise_bps,
        estimate_revision_trend=fin.estimate_revision_trend,
    )


def compute_fundamental_analysis(
    symbol: str,
    latest_close: Decimal | None = None,
    trace_id: UUID | None = None,
    *,
    allow_illustrative: bool = True,
    financials: CompanyFinancials | None = None,
) -> FundamentalAnalysisReport:
    """Perform deterministic fundamental analysis.

    ``allow_illustrative`` is retained for the presentation/demo surface only.
    Executable workflows must pass ``False`` so missing sourced inputs fail closed.
    """
    sym = symbol.strip().upper()
    t_id = trace_id or uuid4()
    fin = financials or get_company_financials(sym, allow_illustrative=allow_illustrative)
    if fin.symbol.strip().upper() != sym:
        raise ValueError("Fundamental record symbol does not match requested symbol")
    if not allow_illustrative and fin.provenance != "sec_filing":
        raise ValueError("Autonomous fundamentals require a sourced SEC filing record")
    if not allow_illustrative:
        required_positive = (
            "shares_outstanding_millions",
            "revenue_ttm",
            "total_assets",
            "current_assets",
            "current_liabilities",
            "stockholders_equity",
        )
        if any(getattr(fin, field) <= Decimal("0") for field in required_positive):
            raise ValueError("Sourced fundamentals contain non-positive required facts")
        if fin.data_as_of is None or fin.data_as_of.tzinfo is None:
            raise ValueError("Sourced fundamentals are missing an as-of timestamp")

    if latest_close is None or latest_close <= Decimal("0.0"):
        if not allow_illustrative:
            raise ValueError(f"No fresh market close available for {sym}")
        close_price = Decimal("100.0")
    else:
        close_price = latest_close

    # 1. Compute Metrics
    prof = compute_profitability_metrics(fin)
    solv = compute_solvency_metrics(fin)
    val, market_cap_m, ev_m = compute_valuation_metrics(fin, close_price)
    f_score = compute_piotroski_f_score(fin)
    z_score, z_zone = compute_altman_z_score(fin, market_cap_m)

    # 2. Composite Scoring & Classifications
    composite_score, health, stance = compute_composite_fundamental_score(
        prof=prof,
        solv=solv,
        f_score=f_score,
        z_score=z_score,
        pe_ratio=val.pe_ratio_ttm,
    )

    # 3. Detect Balance Sheet Red Flags & Earnings Event
    red_flags = detect_balance_sheet_red_flags(fin, solv, z_score)
    earnings_event = compute_earnings_surprise_event(fin)

    event_desc = ""
    if earnings_event and earnings_event.quarter:
        event_desc = (
            f" {earnings_event.quarter} EPS surprise: {earnings_event.eps_surprise_pct or 0}% "
            f"(Guidance: {earnings_event.guidance_change.value})."
        )

    flag_desc = ""
    if red_flags and red_flags != [BalanceSheetRedFlag.NONE_DETECTED]:
        flag_desc = f" Red flags: {', '.join(f.value for f in red_flags)}."

    summary = (
        f"{fin.company_name} ({sym}) displays {health.value.upper()} fundamental health "
        f"with a Quality Score of {composite_score}/100 and Piotroski F-Score of {f_score}/9. "
        f"Altman Z-Score is {z_score} ({z_zone.value.upper()} ZONE). "
        f"Profitability reflects a {prof.net_margin_pct}% net margin and {prof.roe_pct}% ROE. "
        f"Valuation stance is {stance.value.upper()} at {val.pe_ratio_ttm or 'N/A'}x P/E."
        f"{event_desc}{flag_desc}"
    )

    return FundamentalAnalysisReport(
        id=uuid4(),
        trace_id=t_id,
        symbol=sym,
        current_price=round(close_price, 2),
        market_cap_millions=market_cap_m,
        enterprise_value_millions=ev_m,
        profitability=prof,
        solvency=solv,
        valuation=val,
        piotroski_f_score=f_score,
        altman_z_score=z_score,
        altman_zone=z_zone,
        composite_quality_score=composite_score,
        fundamental_health=health,
        valuation_stance=stance,
        earnings_event=earnings_event,
        red_flags=red_flags,
        summary=summary,
        provenance=fin.provenance,
        data_as_of=fin.data_as_of,
    )
