from __future__ import annotations

import math

import numpy as np
import pytest

from scripts.docs_fields import (
    beam_curvature_measure,
    equivalent_strain_3d,
    shell_face_strain_measure,
)


def test_equivalent_strain_3d_uses_engineering_shear_convention() -> None:
    gamma = 0.012
    assert equivalent_strain_3d([0.0, 0.0, 0.0, gamma, 0.0, 0.0]) == pytest.approx(
        gamma / math.sqrt(3.0)
    )


def test_equivalent_strain_3d_is_rotation_invariant_for_principal_permutation() -> None:
    first = equivalent_strain_3d([0.01, -0.003, -0.007, 0.0, 0.0, 0.0])
    second = equivalent_strain_3d([-0.007, 0.01, -0.003, 0.0, 0.0, 0.0])
    assert first == pytest.approx(second)


def test_shell_measure_uses_tensor_shear_not_raw_engineering_shear() -> None:
    exx, eyy, gamma_xy = 0.01, -0.004, 0.006
    expected = math.sqrt(exx**2 + eyy**2 + 0.5 * gamma_xy**2)
    assert shell_face_strain_measure([exx, eyy, gamma_xy]) == pytest.approx(expected)


def test_beam_measure_keeps_curvature_separate_from_dimensionless_strain() -> None:
    generalized = [0.2, 0.3, 0.4, 1.0, 2.0, 2.0]
    assert beam_curvature_measure(generalized) == pytest.approx(3.0)


@pytest.mark.parametrize(
    ("function", "values"),
    [
        (equivalent_strain_3d, np.zeros(5)),
        (shell_face_strain_measure, np.zeros(2)),
        (beam_curvature_measure, np.zeros(7)),
    ],
)
def test_field_measures_reject_wrong_component_counts(function: object, values: np.ndarray) -> None:
    with pytest.raises(ValueError):
        function(values)
