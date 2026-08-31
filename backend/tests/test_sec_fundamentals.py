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
