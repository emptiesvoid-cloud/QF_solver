import numpy as np

from solveur.elements.solid.hex20 import Hex20Element
from solveur.elements.solid.hex8 import Hex8Element
from solveur.verification.robustness_nonlinear_solids import element_coordinates, j2_material


def test_distorted_hex8_and_hex20_keep_positive_jacobians_and_finite_plastic_response() -> None:
    for family, element_type in (("HEX8", Hex8Element), ("HEX20", Hex20Element)):
        coords = element_coordinates(family, distorted=True)
        element = element_type(j2_material())
        displacement = np.concatenate([0.08 * np.asarray([[0.08, 0.015, -0.01], [0.005, -0.015, 0.01], [0.0, 0.008, 0.02]]) @ point for point in coords])
        internal, tangent, states = element.internal_force_tangent_state(coords, displacement)

        assert min(element_type.jacobian_determinant(coords, point) for point in element_type.integration_points) > 0.0
        assert np.all(np.isfinite(internal))
        assert np.all(np.isfinite(tangent))
        assert max(float(state["equivalent_plastic_strain"]) for state in states) > 0.0
