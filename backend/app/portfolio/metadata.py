"""Server-side portfolio instrument classification.

Alpaca position objects do not carry PRISM's sector, correlated-cluster, or
option Greek/expiry fields.  This module parses OCC symbols and applies the
versioned seven-symbol classification used by the Industry Agent.  Unknown
instruments remain incomplete and therefore fail closed; no guessed sector or
cluster is emitted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class InstrumentMetadata:
    symbol: str
    underlying: str
    asset_class: str
    sector: str | None
    correlated_cluster: str | None
    expiration: date | None = None
    option_type: str | None = None
    strike: Decimal | None = None


# The mapping is deliberately explicit for the autonomous allowlist.  The
# sector names mirror Industry Agent's documented registry; clusters represent
# the correlated exposure buckets used by the authorized concentration rule.
UNIVERSE_METADATA: dict[str, tuple[str, str]] = {
    "NVDA": ("Semiconductors & AI Compute", "AI_COMPUTE"),
    "AMD": ("Semiconductors & Computing", "AI_COMPUTE"),
    "TSLA": ("Automotive & Clean Mobility", "EV_MOBILITY"),
    "AAPL": ("Consumer Hardware & Platforms", "MEGA_CAP_TECH"),
    "MSFT": ("Enterprise Cloud & Software", "MEGA_CAP_TECH"),
    "GOOGL": ("Digital Advertising & AI Services", "MEGA_CAP_TECH"),
    "AMZN": ("E-Commerce & Cloud Infrastructure", "MEGA_CAP_TECH"),
}

_OCC_SYMBOL = re.compile(r"^([A-Z]{1,6})(\d{6})([CP])(\d{8})$")


def parse_instrument(symbol: str) -> InstrumentMetadata:
    normalized = symbol.strip().upper()
    match = _OCC_SYMBOL.fullmatch(normalized)
    if match:
        underlying, expiry_raw, option_type, strike_raw = match.groups()
        try:
            expiry = date(2000 + int(expiry_raw[:2]), int(expiry_raw[2:4]), int(expiry_raw[4:6]))
            strike = Decimal(str(int(strike_raw))) / Decimal("1000")
        except (ValueError, InvalidOperation) as exc:
            raise ValueError("Invalid OCC option symbol") from exc
        sector_cluster = UNIVERSE_METADATA.get(underlying)
        return InstrumentMetadata(
            symbol=normalized,
            underlying=underlying,
            asset_class="us_option",
            sector=sector_cluster[0] if sector_cluster else None,
            correlated_cluster=sector_cluster[1] if sector_cluster else None,
            expiration=expiry,
            option_type="call" if option_type == "C" else "put",
            strike=strike,
        )
    sector_cluster = UNIVERSE_METADATA.get(normalized)
    return InstrumentMetadata(
        symbol=normalized,
        underlying=normalized,
        asset_class="us_equity",
        sector=sector_cluster[0] if sector_cluster else None,
        correlated_cluster=sector_cluster[1] if sector_cluster else None,
    )


def metadata_complete(metadata: InstrumentMetadata) -> bool:
    """Return whether all controls can be evaluated for this instrument."""

    if not metadata.sector or not metadata.correlated_cluster:
        return False
    if metadata.asset_class == "us_option":
        return metadata.expiration is not None and metadata.option_type in {"call", "put"}
    return True
