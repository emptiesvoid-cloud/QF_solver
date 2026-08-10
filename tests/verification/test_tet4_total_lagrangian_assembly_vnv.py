"""Assembled checks for the total-Lagrangian TET4 research kernel."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.elements.solid.tet4 import Tet4Element
from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.verification.tet4_total_lagrangian_assembly import (
    TotalLagrangianAssemblyCampaign,
    _relative_error,
    _structured_tet4_mesh,
)


def test_structured_assembly_has_expected_size_and_positive_orientation():
    nodes, elements = _structured_tet4_mesh(8, 2, 2, 4.0, 0.5, 0.5)

    assert nodes.shape == (81, 3)
    assert elements.shape == (192, 4)
    volumes = np.array([Tet4Element.signed_volume(nodes[element]) for element in elements])
    assert np.all(volumes > 0.0)
    np.testing.assert_allclose(np.sum(volumes), 1.0, rtol=0.0, atol=1.0e-14)


def test_assembled_patch_and_rotation_invariants_on_192_elements(tmp_path):
    campaign = TotalLagrangianAssemblyCampaign(tmp_path)
    nodes, elements = _structured_tet4_mesh(8, 2, 2, 4.0, 0.5, 0.5)
    assembly = TotalLagrangianTet4Assembly(nodes, elements, campaign.material)

    assert campaign._patch_error(assembly) <= 1.0e-12
    assert campaign._rotation_error(assembly) <= 1.0e-13


def test_reference_error_is_normalized_by_the_reference_value():
    assert _relative_error(-0.54, -0.60) == pytest.approx(0.10)
