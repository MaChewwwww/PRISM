from __future__ import annotations

from decimal import Decimal

from app.research.sec_fundamentals import _annual_values


def test_annual_values_reads_sec_companyfacts_taxonomy() -> None:
    facts = {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {
                        "USD": [
                            {
                                "val": 123456,
                                "end": "2025-12-31",
                                "filed": "2026-02-01",
                                "form": "10-K",
                            }
                        ]
                    }
                }
            }
        }
    }

    values = _annual_values(
        facts,
        ("RevenueFromContractWithCustomerExcludingAssessedTax",),
    )

    assert len(values) == 1
    assert values[0][0] == Decimal("123456")


def test_annual_values_keeps_comparatives_and_rejects_quarterly_frames() -> None:
    facts = {
        "facts": {
            "us-gaap": {
                "Revenue": {
                    "units": {
                        "USD": [
                            {
                                "val": 300,
                                "start": "2025-01-01",
                                "end": "2025-12-31",
                                "filed": "2026-02-01",
                                "form": "10-K",
                                "frame": "CY2025",
                            },
                            {
                                "val": 250,
                                "start": "2024-01-01",
                                "end": "2024-12-31",
                                "filed": "2026-02-01",
                                "form": "10-K",
                                "frame": "CY2024",
                            },
                            {
                                "val": 80,
                                "start": "2026-01-01",
                                "end": "2026-03-31",
                                "filed": "2026-05-01",
                                "form": "10-Q",
                                "frame": "CY2026Q1",
                            },
                        ]
                    }
                }
            },
            "dei": {
                "EntityCommonStockSharesOutstanding": {
                    "units": {
                        "shares": [
                            {
                                "val": 1000,
                                "end": "2025-12-31",
                                "filed": "2026-02-01",
                                "form": "10-K",
                            }
                        ]
                    }
                }
            },
        }
    }

    annual = _annual_values(facts, ("Revenue",))
    instant = _annual_values(
        facts,
        ("EntityCommonStockSharesOutstanding",),
        include_instant=True,
    )

    assert [value for value, _filed_at in annual] == [Decimal("300"), Decimal("250")]
    assert [value for value, _filed_at in instant] == [Decimal("1000")]
