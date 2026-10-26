"""Collection-only placeholders for the six pending HEX8-SRI FEM cases.

The nodes are intentionally skipped. The campaign is not registered with the
development controller, and no global solve may run until Owner authorization,
source freeze, and controller registration are complete.
"""

from __future__ import annotations

import pytest
import numpy as np

from solveur.elements.solid.hex8_sri import Hex8SRIElement


CASES = (
    pytest.param("hex8_standard", 0.3, id="hex8_standard_nu_0p3"),
    pytest.param("sri_historical", 0.3, id="sri_historical_nu_0p3"),
    pytest.param("sri_corrected", 0.3, id="sri_corrected_nu_0p3"),
    pytest.param("hex8_standard", 0.4999, id="hex8_standard_nu_0p4999"),
    pytest.param("sri_historical", 0.4999, id="sri_historical_nu_0p4999"),
    pytest.param("sri_corrected", 0.4999, id="sri_corrected_nu_0p4999"),
)


class HistoricalHex8SRIElement(Hex8SRIElement):
    """Research-only copy of the parent commit's unweighted central operator."""

    historical_parent_commit = "2aa994f34900f39bef8df9db5fb025157fb694bb"

    def volumetric_stiffness(self, coords: np.ndarray) -> np.ndarray:
        self.validate_geometry(coords)
        _, volumetric = self._constitutive_split(self.material)
        point = self.volumetric_integration_points[0]
        b_matrix, determinant = self.b_matrix(coords, point)
        stiffness = determinant * (b_matrix.T @ volumetric @ b_matrix)
        return 0.5 * (stiffness + stiffness.T)


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
