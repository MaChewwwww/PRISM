from __future__ import annotations

from decimal import Decimal

import pytest

from app.profiles.service import ProfileGovernanceError, ProfileGovernanceService
from app.rules.registry import ProfileParameters


def test_frs_017_profile_validator_rejects_values_outside_authorized_bounds() -> None:
    invalid = ProfileParameters(
        target_position_size_pct=Decimal("2.51"),
        opportunity_score_threshold=Decimal("84"),
    )

    with pytest.raises(ProfileGovernanceError, match="outside BA-authorized bounds"):
        ProfileGovernanceService._validate_bounds(invalid)
