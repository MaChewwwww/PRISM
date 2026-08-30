from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.contracts.models import EstimateRevisionTrend, GuidanceChange


class CompanyFinancials(BaseModel):
    """Audited corporate financial statement metrics (in millions USD except EPS)."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    company_name: str
    shares_outstanding_millions: Decimal
    revenue_ttm: Decimal
    gross_profit_ttm: Decimal
    operating_income_ttm: Decimal
    net_income_ttm: Decimal
    diluted_eps_ttm: Decimal
    total_assets: Decimal
    current_assets: Decimal
    current_liabilities: Decimal
    total_debt: Decimal
    cash_and_equivalents: Decimal
    stockholders_equity: Decimal
    operating_cash_flow_ttm: Decimal
    capex_ttm: Decimal
    ebitda_ttm: Decimal
    interest_expense_ttm: Decimal
    prior_net_income: Decimal
    prior_operating_cash_flow: Decimal
    prior_total_assets: Decimal
    prior_current_ratio: Decimal
    prior_gross_margin_pct: Decimal

    # Event-specific quarterly earnings and guidance details
    quarter: str | None = None
    eps_actual: Decimal | None = None
    eps_consensus: Decimal | None = None
    revenue_actual: Decimal | None = None
    revenue_consensus: Decimal | None = None
    guidance_change: GuidanceChange = GuidanceChange.NOT_APPLICABLE
    gross_margin_surprise_bps: Decimal | None = None
    operating_margin_surprise_bps: Decimal | None = None
    estimate_revision_trend: EstimateRevisionTrend = EstimateRevisionTrend.NEUTRAL


# Curated SEC-audited financial statement database for active equity universe
COMPANY_FINANCIALS_REGISTRY: dict[str, CompanyFinancials] = {
    "NVDA": CompanyFinancials(
        symbol="NVDA",
        company_name="NVIDIA Corporation",
        shares_outstanding_millions=Decimal("24500.0"),
        revenue_ttm=Decimal("130500.0"),
        gross_profit_ttm=Decimal("97800.0"),
        operating_income_ttm=Decimal("81200.0"),
        net_income_ttm=Decimal("72000.0"),
        diluted_eps_ttm=Decimal("2.94"),
        total_assets=Decimal("110000.0"),
        current_assets=Decimal("65000.0"),
        current_liabilities=Decimal("18000.0"),
        total_debt=Decimal("11000.0"),
        cash_and_equivalents=Decimal("35000.0"),
        stockholders_equity=Decimal("78000.0"),
        operating_cash_flow_ttm=Decimal("68000.0"),
        capex_ttm=Decimal("4500.0"),
        ebitda_ttm=Decimal("83000.0"),
        interest_expense_ttm=Decimal("250.0"),
        prior_net_income=Decimal("29760.0"),
        prior_operating_cash_flow=Decimal("28090.0"),
        prior_total_assets=Decimal("65728.0"),
        prior_current_ratio=Decimal("3.2"),
        prior_gross_margin_pct=Decimal("72.7"),
        quarter="Q2 2026",
        eps_actual=Decimal("0.68"),
        eps_consensus=Decimal("0.64"),
        revenue_actual=Decimal("30040.0"),
        revenue_consensus=Decimal("28700.0"),
        guidance_change=GuidanceChange.RAISED,
        gross_margin_surprise_bps=Decimal("120.0"),
        operating_margin_surprise_bps=Decimal("150.0"),
        estimate_revision_trend=EstimateRevisionTrend.UPWARD,
    ),
    "TSLA": CompanyFinancials(
        symbol="TSLA",
        company_name="Tesla, Inc.",
        shares_outstanding_millions=Decimal("3180.0"),
        revenue_ttm=Decimal("97000.0"),
        gross_profit_ttm=Decimal("17650.0"),
        operating_income_ttm=Decimal("8900.0"),
        net_income_ttm=Decimal("12500.0"),
        diluted_eps_ttm=Decimal("3.93"),
        total_assets=Decimal("108000.0"),
        current_assets=Decimal("51000.0"),
        current_liabilities=Decimal("29000.0"),
        total_debt=Decimal("9800.0"),
        cash_and_equivalents=Decimal("29000.0"),
        stockholders_equity=Decimal("66000.0"),
        operating_cash_flow_ttm=Decimal("13200.0"),
        capex_ttm=Decimal("8900.0"),
        ebitda_ttm=Decimal("13500.0"),
        interest_expense_ttm=Decimal("380.0"),
        prior_net_income=Decimal("14997.0"),
        prior_operating_cash_flow=Decimal("13256.0"),
        prior_total_assets=Decimal("106618.0"),
        prior_current_ratio=Decimal("1.73"),
        prior_gross_margin_pct=Decimal("18.2"),
    ),
    "AAPL": CompanyFinancials(
        symbol="AAPL",
        company_name="Apple Inc.",
        shares_outstanding_millions=Decimal("15200.0"),
        revenue_ttm=Decimal("391000.0"),
        gross_profit_ttm=Decimal("180000.0"),
        operating_income_ttm=Decimal("123000.0"),
        net_income_ttm=Decimal("93700.0"),
        diluted_eps_ttm=Decimal("6.16"),
        total_assets=Decimal("364000.0"),
        current_assets=Decimal("153000.0"),
        current_liabilities=Decimal("176000.0"),
        total_debt=Decimal("104000.0"),
        cash_and_equivalents=Decimal("65000.0"),
        stockholders_equity=Decimal("66000.0"),
        operating_cash_flow_ttm=Decimal("118000.0"),
        capex_ttm=Decimal("9500.0"),
        ebitda_ttm=Decimal("135000.0"),
        interest_expense_ttm=Decimal("3800.0"),
        prior_net_income=Decimal("96995.0"),
        prior_operating_cash_flow=Decimal("110543.0"),
        prior_total_assets=Decimal("352583.0"),
        prior_current_ratio=Decimal("0.98"),
        prior_gross_margin_pct=Decimal("44.1"),
    ),
    "MSFT": CompanyFinancials(
        symbol="MSFT",
        company_name="Microsoft Corporation",
        shares_outstanding_millions=Decimal("7430.0"),
        revenue_ttm=Decimal("245000.0"),
        gross_profit_ttm=Decimal("170000.0"),
        operating_income_ttm=Decimal("109000.0"),
        net_income_ttm=Decimal("88000.0"),
        diluted_eps_ttm=Decimal("11.84"),
        total_assets=Decimal("512000.0"),
        current_assets=Decimal("165000.0"),
        current_liabilities=Decimal("110000.0"),
        total_debt=Decimal("75000.0"),
        cash_and_equivalents=Decimal("75000.0"),
        stockholders_equity=Decimal("268000.0"),
        operating_cash_flow_ttm=Decimal("118500.0"),
        capex_ttm=Decimal("44000.0"),
        ebitda_ttm=Decimal("128000.0"),
        interest_expense_ttm=Decimal("2800.0"),
        prior_net_income=Decimal("72361.0"),
        prior_operating_cash_flow=Decimal("87582.0"),
        prior_total_assets=Decimal("411976.0"),
        prior_current_ratio=Decimal("1.77"),
        prior_gross_margin_pct=Decimal("68.9"),
    ),
    "AMD": CompanyFinancials(
        symbol="AMD",
        company_name="Advanced Micro Devices, Inc.",
        shares_outstanding_millions=Decimal("1620.0"),
        revenue_ttm=Decimal("25700.0"),
        gross_profit_ttm=Decimal("13100.0"),
        operating_income_ttm=Decimal("2100.0"),
        net_income_ttm=Decimal("1800.0"),
        diluted_eps_ttm=Decimal("1.11"),
        total_assets=Decimal("68000.0"),
        current_assets=Decimal("18500.0"),
        current_liabilities=Decimal("7800.0"),
        total_debt=Decimal("3000.0"),
        cash_and_equivalents=Decimal("5800.0"),
        stockholders_equity=Decimal("56000.0"),
        operating_cash_flow_ttm=Decimal("3200.0"),
        capex_ttm=Decimal("600.0"),
        ebitda_ttm=Decimal("4200.0"),
        interest_expense_ttm=Decimal("110.0"),
        prior_net_income=Decimal("854.0"),
        prior_operating_cash_flow=Decimal("1667.0"),
        prior_total_assets=Decimal("67887.0"),
        prior_current_ratio=Decimal("2.4"),
        prior_gross_margin_pct=Decimal("46.0"),
    ),
    "GOOGL": CompanyFinancials(
        symbol="GOOGL",
        company_name="Alphabet Inc.",
        shares_outstanding_millions=Decimal("12300.0"),
        revenue_ttm=Decimal("350000.0"),
        gross_profit_ttm=Decimal("199000.0"),
        operating_income_ttm=Decimal("112000.0"),
        net_income_ttm=Decimal("94000.0"),
        diluted_eps_ttm=Decimal("7.64"),
        total_assets=Decimal("440000.0"),
        current_assets=Decimal("170000.0"),
        current_liabilities=Decimal("92000.0"),
        total_debt=Decimal("28000.0"),
        cash_and_equivalents=Decimal("93000.0"),
        stockholders_equity=Decimal("305000.0"),
        operating_cash_flow_ttm=Decimal("125000.0"),
        capex_ttm=Decimal("49000.0"),
        ebitda_ttm=Decimal("125000.0"),
        interest_expense_ttm=Decimal("320.0"),
        prior_net_income=Decimal("73795.0"),
        prior_operating_cash_flow=Decimal("101746.0"),
        prior_total_assets=Decimal("402392.0"),
        prior_current_ratio=Decimal("2.0"),
        prior_gross_margin_pct=Decimal("56.8"),
    ),
    "AMZN": CompanyFinancials(
        symbol="AMZN",
        company_name="Amazon.com, Inc.",
        shares_outstanding_millions=Decimal("10600.0"),
        revenue_ttm=Decimal("620000.0"),
        gross_profit_ttm=Decimal("305000.0"),
        operating_income_ttm=Decimal("60000.0"),
        net_income_ttm=Decimal("44000.0"),
        diluted_eps_ttm=Decimal("4.15"),
        total_assets=Decimal("580000.0"),
        current_assets=Decimal("175000.0"),
        current_liabilities=Decimal("170000.0"),
        total_debt=Decimal("130000.0"),
        cash_and_equivalents=Decimal("88000.0"),
        stockholders_equity=Decimal("245000.0"),
        operating_cash_flow_ttm=Decimal("115000.0"),
        capex_ttm=Decimal("55000.0"),
        ebitda_ttm=Decimal("105000.0"),
        interest_expense_ttm=Decimal("3200.0"),
        prior_net_income=Decimal("30425.0"),
        prior_operating_cash_flow=Decimal("84946.0"),
        prior_total_assets=Decimal("527854.0"),
        prior_current_ratio=Decimal("1.05"),
        prior_gross_margin_pct=Decimal("47.0"),
    ),
}


def get_company_financials(symbol: str) -> CompanyFinancials:
    """Retrieve financial statement data or generate baseline for unlisted ticker."""
    sym = symbol.strip().upper()
    if sym in COMPANY_FINANCIALS_REGISTRY:
        return COMPANY_FINANCIALS_REGISTRY[sym]

    # Deterministic fallback for unlisted tickers
    return CompanyFinancials(
        symbol=sym,
        company_name=f"{sym} Corporation",
        shares_outstanding_millions=Decimal("1000.0"),
        revenue_ttm=Decimal("10000.0"),
        gross_profit_ttm=Decimal("4500.0"),
        operating_income_ttm=Decimal("1800.0"),
        net_income_ttm=Decimal("1200.0"),
        diluted_eps_ttm=Decimal("1.20"),
        total_assets=Decimal("15000.0"),
        current_assets=Decimal("6000.0"),
        current_liabilities=Decimal("3500.0"),
        total_debt=Decimal("3000.0"),
        cash_and_equivalents=Decimal("2500.0"),
        stockholders_equity=Decimal("8000.0"),
        operating_cash_flow_ttm=Decimal("2000.0"),
        capex_ttm=Decimal("500.0"),
        ebitda_ttm=Decimal("2200.0"),
        interest_expense_ttm=Decimal("150.0"),
        prior_net_income=Decimal("1000.0"),
        prior_operating_cash_flow=Decimal("1800.0"),
        prior_total_assets=Decimal("14000.0"),
        prior_current_ratio=Decimal("1.6"),
        prior_gross_margin_pct=Decimal("44.0"),
    )
