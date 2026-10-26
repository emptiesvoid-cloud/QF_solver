"""Collection-only placeholders for the six pending HEX8-SRI FEM cases.

The nodes are intentionally skipped. The campaign is not registered with the
development controller, and no global solve may run until Owner authorization,
source freeze, and controller registration are complete.
"""

from __future__ import annotations

import pytest


CASES = (
    pytest.param("hex8_standard", 0.3, id="hex8_standard_nu_0p3"),
    pytest.param("sri_historical", 0.3, id="sri_historical_nu_0p3"),
    pytest.param("sri_corrected", 0.3, id="sri_corrected_nu_0p3"),
    pytest.param("hex8_standard", 0.4999, id="hex8_standard_nu_0p4999"),
    pytest.param("sri_historical", 0.4999, id="sri_historical_nu_0p4999"),
    pytest.param("sri_corrected", 0.4999, id="sri_corrected_nu_0p4999"),
)


@pytest.mark.parametrize(("formulation", "poisson_ratio"), CASES)
@pytest.mark.skip(
    reason=(
        "Preparation only: Owner authorization, a frozen execution manifest, "
        "and development-controller registration are required before FEM."
    )
)
def test_hex8_sri_cantilever_campaign(
    formulation: str, poisson_ratio: float
) -> None:
    """Reserve exact nodeids; the execution harness is deliberately absent."""
    pytest.fail(
        f"FEM placeholder is not executable: {formulation}, nu={poisson_ratio}"
    )
