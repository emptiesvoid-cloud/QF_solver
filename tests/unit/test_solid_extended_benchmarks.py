from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from solveur.benchmarks.solid_extended import apply_consistent_circular_torsion


def test_consistent_circular_torsion_preserves_requested_resultants() -> None:
    root_three_over_two = np.sqrt(3.0) / 2.0
    model = SimpleNamespace(
        nodes=np.asarray(
            [
                [0.0, 0.0, 0.0],
                [1.0, 1.0, 0.0],
                [1.0, -0.5, root_three_over_two],
                [1.0, -0.5, -root_three_over_two],
            ]
        ),
        elements=[SimpleNamespace(type="TET4", nodes=(0, 1, 2, 3))],
        loads=[],
    )

    diagnostics = apply_consistent_circular_torsion(model, 125.0)

    assert diagnostics["face_count"] == 1.0
    assert diagnostics["resultant_torque_x"] == pytest.approx(125.0, rel=1.0e-14)
    assert diagnostics["resultant_force_norm"] <= 1.0e-13
    assert model.loads
    assert {load.dof for load in model.loads} == {"UY", "UZ"}


def test_consistent_circular_torsion_supports_quadratic_tet10_face() -> None:
    root_three_over_two = np.sqrt(3.0) / 2.0
    corners = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [1.0, -0.5, root_three_over_two],
            [1.0, -0.5, -root_three_over_two],
        ]
    )
    nodes = np.vstack(
        (
            corners,
            0.5 * (corners[0] + corners[1]),
            0.5 * (corners[1] + corners[2]),
            0.5 * (corners[2] + corners[0]),
            0.5 * (corners[0] + corners[3]),
            0.5 * (corners[1] + corners[3]),
            0.5 * (corners[2] + corners[3]),
        )
    )
    model = SimpleNamespace(
        nodes=nodes,
        elements=[SimpleNamespace(type="TET10", nodes=tuple(range(10)))],
        loads=[],
    )

    diagnostics = apply_consistent_circular_torsion(model, 125.0)

    assert diagnostics["face_count"] == 1.0
    assert diagnostics["resultant_torque_x"] == pytest.approx(125.0, rel=1.0e-14)
    assert diagnostics["resultant_force_norm"] <= 1.0e-12
    assert model.loads


def test_consistent_circular_torsion_rejects_model_without_terminal_face() -> None:
    model = SimpleNamespace(
        nodes=np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]),
        elements=[SimpleNamespace(type="TET4", nodes=(0, 1, 2, 3))],
        loads=[],
    )

    with pytest.raises(ValueError, match="no terminal"):
        apply_consistent_circular_torsion(model, 125.0)
