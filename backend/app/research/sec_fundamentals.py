"""Small, server-side SEC companyfacts adapter used by autonomous research.

The bundled financial registry is intentionally illustrative.  This adapter is
the executable path: it only returns a record when the SEC has supplied the
required statement facts and an ``as_of`` date.  Missing or malformed facts are
raised so the caller can record ``NO_TRADE`` rather than filling values in.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
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
    "GOOGL": "0001652044",
    "AMZN": "0001018724",
}


class SecFundamentalsUnavailable(RuntimeError):
    """The SEC record cannot safely support autonomous fundamental analysis."""


def _annual_values(facts: dict[str, Any], tags: tuple[str, ...]) -> list[tuple[Decimal, datetime]]:
    """Return annual USD/USD-per-share facts ordered by filing date."""
    values: list[tuple[Decimal, datetime]] = []
    usgaap = facts.get("us-gaap", {})
    for tag in tags:
        units = usgaap.get(tag, {}).get("units", {})
        unit_values = units.get("USD") or units.get("USD/shares") or units.get("shares")
        if not isinstance(unit_values, list):
            continue
        for entry in unit_values:
            # Annual values must be 10-K/20-F facts or explicitly carry a one
            # year frame.  Quarterly values are not silently added together.
            form = str(entry.get("form", ""))
            frame = str(entry.get("frame", ""))
            if form not in {"10-K", "10-K/A", "20-F", "20-F/A"} and not frame.startswith("CY"):
                continue
            try:
                value = Decimal(str(entry["val"]))
                end = datetime.fromisoformat(str(entry["end"])).replace(tzinfo=UTC)
            except (KeyError, TypeError, ValueError):
                continue
            filed = str(entry.get("filed", entry.get("end", "")))
            try:
                filed_at = datetime.fromisoformat(filed).replace(tzinfo=UTC)
            except ValueError:
                filed_at = end
            values.append((value, filed_at))
        if values:
            break
    values.sort(key=lambda item: item[1], reverse=True)
    # SEC may repeat a fact across amended filings. Keep one value per date.
    deduped: list[tuple[Decimal, datetime]] = []
    for value, filed_at in values:
        if filed_at.date() in {d.date() for _, d in deduped}:
            continue
        deduped.append((value, filed_at))
    return deduped


def _value(
    facts: dict[str, Any], tags: tuple[str, ...], name: str
) -> tuple[Decimal, Decimal, datetime]:
    values = _annual_values(facts, tags)
    if not values:
        raise SecFundamentalsUnavailable(f"SEC fact unavailable: {name}")
    current, current_at = values[0]
    prior = values[1][0] if len(values) > 1 else current
    return current, prior, current_at


def _filed_by_checkpoint(value: Any, checkpoint: datetime) -> bool:
    if not isinstance(value, dict):
        return False
    filed = value.get("filed", value.get("end"))
    try:
        return datetime.fromisoformat(str(filed)).replace(tzinfo=UTC) <= checkpoint
    except (TypeError, ValueError):
        return False


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

    revenue, prior_revenue, as_of = _value(
        facts,
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"),
        "revenue",
    )
    gross_profit, prior_gross_profit, _ = _value(facts, ("GrossProfit",), "gross profit")
    operating_income, prior_operating_income, _ = _value(
        facts, ("OperatingIncomeLoss",), "operating income"
    )
    net_income, prior_net_income, _ = _value(facts, ("NetIncomeLoss", "ProfitLoss"), "net income")
    eps, _, _ = _value(facts, ("EarningsPerShareDiluted",), "diluted EPS")
    total_assets, prior_assets, _ = _value(facts, ("Assets",), "assets")
    current_assets, _, _ = _value(facts, ("AssetsCurrent",), "current assets")
    current_liabilities, _, _ = _value(facts, ("LiabilitiesCurrent",), "current liabilities")
    equity, _, _ = _value(
        facts,
        (
            "StockholdersEquity",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        ),
        "stockholders equity",
    )
    retained_earnings, _, _ = _value(
        facts,
        (
            "RetainedEarningsAccumulatedDeficit",
            "RetainedEarningsAccumulatedDeficitIncludingAccumulatedOtherComprehensiveIncome",
        ),
        "retained earnings",
    )
    cash, _, _ = _value(
        facts,
        (
            "CashAndCashEquivalentsAtCarryingValue",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        ),
        "cash",
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
    debt, _, _ = _value(
        facts,
        (
            "LongTermDebtAndFinanceLeaseObligationsCurrent",
            "LongTermDebtCurrent",
            "LongTermDebtNoncurrent",
        ),
        "debt",
    )
    interest, _, _ = _value(
        facts,
        ("InterestExpenseNonOperating", "InterestExpenseDebt"),
        "interest expense",
    )
    shares, _, _ = _value(
        facts,
        ("EntityCommonStockSharesOutstanding", "CommonStocksIncludingAdditionalPaidInCapital"),
        "shares outstanding",
    )
    depreciation, _, _ = _value(
        facts,
        ("DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet"),
        "depreciation and amortization",
    )

    def millions(value: Decimal) -> Decimal:
        return value / Decimal("1000000")

    prior_ratio = (
        (current_assets / current_liabilities) if current_liabilities != 0 else Decimal("0")
    )
    prior_margin = (
        (prior_gross_profit / prior_revenue) * Decimal("100")
        if prior_revenue != 0
        else Decimal("0")
    )
    # EBITDA is derived only from sourced operating income and D&A facts.
    ebitda = operating_income + depreciation
    prior_ebitda = prior_operating_income + depreciation
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
        provenance="sec_filing",
        data_as_of=as_of,
    )
