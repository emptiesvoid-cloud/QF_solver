from __future__ import annotations

import numpy as np

from solveur.core.dofs import DofManager
from solveur.core.result_serialization import (
    complex_nodal_state,
    legacy_six_dof_vector,
    modal_shape,
    nodal_state,
)


def _dofs() -> DofManager:
    return DofManager.from_node_requirements({2: {"UZ", "UX"}, 0: {"UX", "RZ"}})


def test_nodal_and_modal_serialization_are_sorted_and_named() -> None:
    dofs = _dofs()
    values = np.arange(dofs.ndof, dtype=float)
    rows = nodal_state(dofs, values)
    assert [row["node"] for row in rows] == [0, 2]
    assert rows[0]["dofs"] == {"UX": 0.0, "RZ": 1.0}
    assert modal_shape(dofs, values[:, None], 0) == rows


def test_complex_serialization_exposes_real_imag_amplitude_and_phase() -> None:
    dofs = _dofs()
    values = np.asarray([1.0 + 2.0j, 0.0 + 1.0j, -2.0 + 0.0j, 3.0 - 4.0j])
    rows = complex_nodal_state(dofs, values)
    assert rows[0]["dofs"]["UX"]["real"] == 1.0
    assert rows[0]["dofs"]["UX"]["imag"] == 2.0
    assert rows[0]["dofs"]["UX"]["amplitude"] == 5**0.5
    assert rows[1]["dofs"]["UX"]["phase_degrees"] == 180.0


def test_legacy_six_dof_vector_pads_missing_shell_dofs() -> None:
    dofs = _dofs()
    values = np.arange(dofs.ndof, dtype=float)
    vector = legacy_six_dof_vector(dofs, values, node_count=3)
    assert vector.shape == (18,)
    assert vector[0] == 0.0
    assert vector[5] == 1.0
    assert vector[12 + 0] == 2.0
    assert vector[12 + 1] == 0.0
    assert vector[13] == 0.0
    assert vector[15:].tolist() == [0.0] * 3
