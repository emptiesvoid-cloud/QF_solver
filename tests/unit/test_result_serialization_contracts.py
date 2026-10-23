from __future__ import annotations

import numpy as np

from solveur.core.dofs import DofManager
from solveur.core.results import ReducedHarmonicResult
from solveur.core.analyses.modal_newmark import ModalNewmarkResult
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


def test_versioned_experimental_result_dtos_round_trip_without_solver_execution() -> None:
    dofs = DofManager.from_node_requirements({0: {"UX"}})
    modal_newmark = ModalNewmarkResult(
        numerical_status="PASS",
        times=np.asarray([0.0, 1.0]),
        displacements=np.asarray([0.1]),
        velocities=np.asarray([0.2]),
        accelerations=np.asarray([0.3]),
        modal_displacements=np.asarray([0.4]),
        modal_velocities=np.asarray([0.5]),
        modal_accelerations=np.asarray([0.6]),
        dofs=dofs,
        node_count=1,
        element_count=0,
        solver={},
        provenance={"source_sha": "test-fixture"},
        result_availability={},
        execution_identity={},
        execution_key="synthetic-modal-newmark-result",
        qualification_scope_id="TEST_ONLY",
        mesh_report={},
    )
    restored_modal = ModalNewmarkResult.from_dict(modal_newmark.to_dict())
    assert restored_modal.to_dict()["schema"] == "qf-modal-newmark-result/v1"
    assert restored_modal.to_dict()["maturity"] == "EXPERIMENTAL"
    assert restored_modal.to_dict()["qualification_decision"] == "NOT_ASSESSED"
    np.testing.assert_array_equal(restored_modal.displacements, modal_newmark.displacements)

    reduced_harmonic = ReducedHarmonicResult(
        numerical_status="PASS",
        frequencies_hz=np.asarray([5.0]),
        responses=(np.asarray([1.0 + 2.0j]),),
        modal_coordinates=(np.asarray([0.5 - 0.25j]),),
        dof_signature=((0, ("UX",)),),
        full_dof_count=1,
        node_count=1,
        element_count=0,
        solver={},
        provenance={"source_sha": "test-fixture"},
        result_availability={},
        execution_identity={},
        execution_key="synthetic-reduced-harmonic-result",
        qualification_scope_id="TEST_ONLY",
        mesh_report={},
    )
    restored_harmonic = ReducedHarmonicResult.from_dict(reduced_harmonic.to_dict())
    encoded_harmonic = restored_harmonic.to_dict()
    assert encoded_harmonic["schema"] == "qf-reduced-harmonic-result/v1"
    assert encoded_harmonic["maturity"] == "EXPERIMENTAL"
    assert encoded_harmonic["qualification_decision"] == "NOT_ASSESSED"
    np.testing.assert_array_equal(restored_harmonic.responses[0], reduced_harmonic.responses[0])
