"""Frozen local reproduction of the pre-weight HEX8-SRI volumetric operator.

This adapter is isolated to the research campaign. It does not alter or register
the production Hex8SRIElement and intentionally reproduces the parent-source
formula that omitted the reference-cube integration weight 8.
"""

from __future__ import annotations

import numpy as np

from solveur.elements.solid.hex8_sri import Hex8SRIElement


class HistoricalHex8SRIElement(Hex8SRIElement):
    """HEX8-SRI with the historical unweighted one-point volumetric block."""

    historical_parent_commit = "2aa994f34900f39bef8df9db5fb025157fb694bb"
    historical_central_weight = 1.0

    def volumetric_stiffness(self, coords: np.ndarray) -> np.ndarray:
        self.validate_geometry(coords)
        _, volumetric = self._constitutive_split(self.material)
        point = self.volumetric_integration_points[0]
        b_matrix, determinant = self.b_matrix(coords, point)
        stiffness = self.historical_central_weight * determinant * (
            b_matrix.T @ volumetric @ b_matrix
        )
        return 0.5 * (stiffness + stiffness.T)
