"""Small, server-side SEC companyfacts adapter used by autonomous research.

The bundled financial registry is intentionally illustrative.  This adapter is
the executable path: it only returns a record when the SEC has supplied the
required statement facts and an ``as_of`` date.  Missing or malformed facts are
raised so the caller can record ``NO_TRADE`` rather than filling values in.
"""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import httpx

from app.research.fundamental_data import CompanyFinancials

SEC_CIK_BY_SYMBOL: dict[str, str] = {
    "NVDA": "0001045810",
    "TSLA": "0001318605",
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "AMD": "0000002488",
    "META": "0001326801",
    "GOOGL": "0001652044",
    "AMZN": "0001018724",
}


class SecFundamentalsUnavailable(RuntimeError):
    """The SEC record cannot safely support autonomous fundamental analysis."""


def _parse_timestamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _annual_values(
    facts: dict[str, Any],
    tags: tuple[str, ...],
    *,
    include_instant: bool = False,
) -> list[tuple[Decimal, datetime]]:
    """Return sourced annual (or explicitly instant) facts by period end.

    SEC Companyfacts contains multiple aliases, taxonomies, amendments, and
    comparative periods in one response.  We collect all matching aliases,
    reject quarterly frames when an annual value is required, then keep the
    newest filing for each distinct period end.  This prevents stale aliases
    and same-filing comparative values from silently replacing one another.
    """
    candidates: list[tuple[datetime, datetime, Decimal, int]] = []
    # Companyfacts responses nest taxonomies below the top-level ``facts``
    # object.  Keep the adapter strict: an absent or malformed taxonomy simply
    # yields no values and fails closed at the caller instead of using fixtures.
    facts_by_taxonomy = facts.get("facts", {})
    if not isinstance(facts_by_taxonomy, dict):
        return []
    annual_forms = {"10-K", "10-K/A", "20-F", "20-F/A"}
    taxonomies = (
        facts_by_taxonomy.get("us-gaap", {}),
        facts_by_taxonomy.get("dei", {}),
    )
    for tag_priority, tag in enumerate(tags):
        for taxonomy in taxonomies:
            if not isinstance(taxonomy, dict):
                continue
            fact = taxonomy.get(tag)
            if not isinstance(fact, dict):
                continue
            units = fact.get("units", {})
            if not isinstance(units, dict):
                continue
            unit_values: list[Any] = []
            for unit_name in ("USD", "USD/shares", "shares"):
                values_for_unit = units.get(unit_name)
                if isinstance(values_for_unit, list):
                    unit_values.extend(values_for_unit)
            for entry in unit_values:
                if not isinstance(entry, dict):
                    continue
                form = str(entry.get("form", "")).upper()
                frame = str(entry.get("frame", ""))
                start = entry.get("start")
                annual = form in annual_forms or re.fullmatch(r"CY\d{4}", frame) is not None
                instant = (
                    include_instant
                    and start is None
                    and (form in annual_forms or form in {"10-Q", "10-Q/A"} or frame.endswith("I"))
                )
                if not annual and not instant:
                    continue
                period_end = _parse_timestamp(entry.get("end"))
                if period_end is None:
                    continue
                try:
                    value = Decimal(str(entry["val"]))
                except (KeyError, TypeError, ValueError):
                    continue
                filed_at = _parse_timestamp(entry.get("filed", entry.get("end"))) or period_end
                candidates.append((period_end, filed_at, value, tag_priority))

    candidates.sort(key=lambda item: (item[0], item[1], -item[3]), reverse=True)
    seen_periods: set[date] = set()
    values: list[tuple[Decimal, datetime]] = []
    for period_end, filed_at, value, _tag_priority in candidates:
        if period_end.date() in seen_periods:
            continue
        seen_periods.add(period_end.date())
        values.append((value, filed_at))
    return values


def _value(
    facts: dict[str, Any],
    tags: tuple[str, ...],
    name: str,
    *,
    include_instant: bool = False,
) -> tuple[Decimal, Decimal, datetime]:
    values = _annual_values(facts, tags, include_instant=include_instant)
    if not values:
        raise SecFundamentalsUnavailable(f"SEC fact unavailable: {name}")
    current, current_at = values[0]
    prior = values[1][0] if len(values) > 1 else current
    return current, prior, current_at


def _filed_by_checkpoint(value: Any, checkpoint: datetime) -> bool:
    if not isinstance(value, dict):
        return False
    filed = value.get("filed", value.get("end"))
    parsed = _parse_timestamp(filed)
    if parsed is None or checkpoint.tzinfo is None or checkpoint.utcoffset() is None:
        return False
    return parsed <= checkpoint.astimezone(UTC)


def fetch_sec_company_financials(
    symbol: str,
    *,
    user_agent: str = "PRISM autonomous research contact: operator@prism.local",
    timeout_seconds: float = 10.0,
    client: httpx.Client | None = None,
    as_of: datetime | None = None,
) -> CompanyFinancials:
    sym = symbol.strip().upper()
    cik = SEC_CIK_BY_SYMBOL.get(sym)
    if cik is None:
        raise SecFundamentalsUnavailable(f"No SEC CIK mapping for {sym}")
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    headers = {"User-Agent": user_agent, "Accept": "application/json"}
    owned_client = client is None
    request_client = client or httpx.Client(timeout=timeout_seconds)
    try:
        response = request_client.get(url, headers=headers)
        response.raise_for_status()
        facts = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise SecFundamentalsUnavailable("SEC companyfacts request failed") from exc
    finally:
        if owned_client:
            request_client.close()
    if not isinstance(facts, dict):
        raise SecFundamentalsUnavailable("SEC companyfacts response is malformed")
    if as_of is not None:
        checkpoint = as_of.astimezone(UTC)
        facts = deepcopy(facts)
        for taxonomy in facts.get("facts", {}).values():
            if not isinstance(taxonomy, dict):
                continue
            for fact in taxonomy.values():
                if not isinstance(fact, dict):
                    continue
                for values in fact.get("units", {}).values():
                    if not isinstance(values, list):
                        continue
                    values[:] = [
                        value for value in values if _filed_by_checkpoint(value, checkpoint)
                    ]

    revenue, prior_revenue, revenue_as_of = _value(
        facts,
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"),
        "revenue",
    )
    try:
        gross_profit, prior_gross_profit, _ = _value(facts, ("GrossProfit",), "gross profit")
    except SecFundamentalsUnavailable:
        cost_of_revenue, prior_cost_of_revenue, _ = _value(
            facts,
            ("CostOfRevenue", "CostOfGoodsAndServicesSold"),
            "gross profit or cost of revenue",
        )
        gross_profit = revenue - cost_of_revenue
        prior_gross_profit = prior_revenue - prior_cost_of_revenue
    operating_income, prior_operating_income, _ = _value(
        facts, ("OperatingIncomeLoss",), "operating income"
    )
    net_income, prior_net_income, _ = _value(facts, ("NetIncomeLoss", "ProfitLoss"), "net income")
    eps, _, _ = _value(facts, ("EarningsPerShareDiluted",), "diluted EPS")
    total_assets, prior_assets, _ = _value(facts, ("Assets",), "assets", include_instant=True)
    current_assets, prior_current_assets, _ = _value(
        facts, ("AssetsCurrent",), "current assets", include_instant=True
    )
    current_liabilities, prior_current_liabilities, _ = _value(
        facts, ("LiabilitiesCurrent",), "current liabilities", include_instant=True
    )
    equity, _, _ = _value(
        facts,
        (
            "StockholdersEquity",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        ),
        "stockholders equity",
        include_instant=True,
    )
    retained_earnings, _, _ = _value(
        facts,
        (
            "RetainedEarningsAccumulatedDeficit",
            "RetainedEarningsAccumulatedDeficitIncludingAccumulatedOtherComprehensiveIncome",
        ),
        "retained earnings",
        include_instant=True,
    )
    cash, _, _ = _value(
        facts,
        (
            "CashAndCashEquivalentsAtCarryingValue",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        ),
        "cash",
        include_instant=True,
    )
    ocf, prior_ocf, _ = _value(
        facts,
        ("NetCashProvidedByUsedInOperatingActivities",),
        "operating cash flow",
    )
    capex, _, _ = _value(
        facts,
        ("PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"),
        "capital expenditure",
    )
    debt_parts: list[tuple[Decimal, Decimal]] = []
    for debt_tags in (
        ("LongTermDebtAndFinanceLeaseObligationsCurrent", "LongTermDebtCurrent"),
        (
            "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
            "LongTermDebtNoncurrent",
            "LongTermDebt",
        ),
    ):
        try:
            debt_current, debt_prior, _ = _value(facts, debt_tags, "debt", include_instant=True)
        except SecFundamentalsUnavailable:
            continue
        debt_parts.append((debt_current, debt_prior))
    if not debt_parts:
        raise SecFundamentalsUnavailable("SEC fact unavailable: debt")
    debt = sum((part[0] for part in debt_parts), Decimal("0"))
    interest, _, _ = _value(
        facts,
        (
            "InterestExpense",
            "InterestExpenseNonOperating",
            "InterestExpenseDebt",
            "FinanceLeaseInterestExpense",
        ),
        "interest expense",
    )
    shares, prior_shares, _ = _value(
        facts,
        (
            "EntityCommonStockSharesOutstanding",
            "CommonStockSharesOutstanding",
            "CommonStocksIncludingAdditionalPaidInCapital",
        ),
        "shares outstanding",
        include_instant=True,
    )
    depreciation, prior_depreciation, _ = _value(
        facts,
        (
            "DepreciationDepletionAndAmortization",
            "DepreciationAmortizationAndAccretionNet",
            "Depreciation",
            "AmortizationOfIntangibleAssets",
        ),
        "depreciation and amortization",
    )

    def millions(value: Decimal) -> Decimal:
        return value / Decimal("1000000")

    prior_ratio = (
        (prior_current_assets / prior_current_liabilities)
        if prior_current_liabilities != 0
        else Decimal("0")
    )
    prior_margin = (
        (prior_gross_profit / prior_revenue) * Decimal("100")
        if prior_revenue != 0
        else Decimal("0")
    )
    # EBITDA is derived only from sourced operating income and D&A facts.
    ebitda = operating_income + depreciation
    prior_ebitda = prior_operating_income + prior_depreciation
    return CompanyFinancials(
        symbol=sym,
        company_name=str(facts.get("entityName", sym)),
        shares_outstanding_millions=millions(shares),
        revenue_ttm=millions(revenue),
        gross_profit_ttm=millions(gross_profit),
        operating_income_ttm=millions(operating_income),
        net_income_ttm=millions(net_income),
        diluted_eps_ttm=eps,
        total_assets=millions(total_assets),
        current_assets=millions(current_assets),
        current_liabilities=millions(current_liabilities),
        total_debt=millions(debt),
        cash_and_equivalents=millions(cash),
        stockholders_equity=millions(equity),
        operating_cash_flow_ttm=millions(ocf),
        capex_ttm=millions(capex),
        ebitda_ttm=millions(ebitda if ebitda != 0 else prior_ebitda),
        interest_expense_ttm=millions(interest),
        prior_net_income=millions(prior_net_income),
        prior_operating_cash_flow=millions(prior_ocf),
        prior_total_assets=millions(prior_assets),
        prior_current_ratio=prior_ratio,
        prior_gross_margin_pct=prior_margin,
        retained_earnings=millions(retained_earnings),
        prior_shares_outstanding_millions=millions(prior_shares),
        provenance="sec_filing",
        data_as_of=revenue_as_of,
    )
