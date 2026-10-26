from __future__ import annotations

import numpy as np
import pytest

from solveur.elements.solid.hex8_sri import Hex8SRIElement
from solveur.materials.solid import SolidMaterial


def unit_hex() -> np.ndarray:
    return np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
        ],
        dtype=float,
    )


def test_center_volumetric_rule_integrates_constant_over_reference_hex() -> None:
    material = SolidMaterial(E=1000.0, nu=0.3)
    coords = unit_hex()
    element = Hex8SRIElement(material)
    affine_dilatation = coords.reshape(-1)

    actual_energy = 0.5 * affine_dilatation @ (
        element.volumetric_stiffness(coords) @ affine_dilatation
    )
    bulk_modulus = material.E / (3.0 * (1.0 - 2.0 * material.nu))
    expected_energy = 0.5 * bulk_modulus * 3.0**2 * 1.0

    assert actual_energy == pytest.approx(expected_energy, rel=1.0e-12)
