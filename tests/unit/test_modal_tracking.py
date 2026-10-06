"""Phase/order invariance, degeneracy and ambiguity tests for WP06 tracking."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from solveur.core.analyses.modal_tracking import complex_mac, complex_mac_matrix, track_modal_sweep


def test_complex_mac_is_invariant_to_complex_phase_and_nonzero_scaling() -> None:
    mode = np.asarray([1.0 + 2.0j, -0.5j, 3.0 - 1.0j])
    mass = np.diag([2.0, 3.0, 4.0])
    changed = (2.5 * np.exp(1.37j)) * mode

    assert complex_mac(mode, changed, mass) == pytest.approx(1.0, abs=1.0e-14)


def test_complex_mac_orthogonal_and_conjugate_behavior_is_explicit() -> None:
    mass = np.eye(2)
    first = np.asarray([1.0 + 0.0j, 0.0j])
    second = np.asarray([0.0j, 1.0 + 0.0j])
    circular = np.asarray([1.0 + 0.0j, 1.0j]) / np.sqrt(2.0)
    opposite_circular = np.conjugate(circular)

    assert complex_mac(first, second, mass) == pytest.approx(0.0, abs=1.0e-14)
    assert complex_mac(circular, opposite_circular, mass) == pytest.approx(0.0, abs=1.0e-14)
    assert complex_mac_matrix(first[:, None], second[:, None], mass)[0, 0] == pytest.approx(0.0)


def _result(speed: float, frequencies: list[float], modes: np.ndarray) -> SimpleNamespace:
    values = np.asarray([1j * (2.0 * np.pi * item) for item in frequencies], dtype=np.complex128)
    return SimpleNamespace(
        spin_speed_rad_s=speed,
        axis_global=(1.0, 0.0, 0.0),
        modes=np.asarray(modes, dtype=np.complex128),
        eigenvalues=values,
        frequencies_hz=np.asarray(frequencies, dtype=float),
        qep_residuals=np.zeros(len(frequencies), dtype=float),
        selected_mode_indices=tuple(range(len(frequencies))),
        dofs=SimpleNamespace(node_dofs={}),
    )


def _branch_signature(branches: list[dict[str, object]]) -> list[tuple[str, tuple[float | None, ...]]]:
    return [
        (
            str(branch["branch_id"]),
            tuple(None if sample is None else float(sample["frequencies_hz"][0]) for sample in branch["samples"]),
        )
        for branch in branches
    ]


def test_tracking_is_invariant_to_eigenpair_order_phase_and_scaling() -> None:
    mass = np.eye(2)
    modes_0 = np.eye(2, dtype=np.complex128)
    modes_1 = np.column_stack((2.0j * modes_0[:, 1], -3.0 * np.exp(0.4j) * modes_0[:, 0]))
    modes_2 = np.column_stack((np.exp(-0.7j) * modes_0[:, 0], 0.25 * modes_0[:, 1]))
    baseline, baseline_diagnostics = track_modal_sweep(
        [_result(0.0, [10.0, 20.0], modes_0), _result(1.0, [10.1, 20.2], modes_2)], mass
    )
    permuted, permuted_diagnostics = track_modal_sweep(
        [_result(0.0, [10.0, 20.0], modes_0), _result(1.0, [20.2, 10.1], modes_1)], mass
    )

    assert _branch_signature(permuted) == _branch_signature(baseline)
    assert [item["status"] for item in permuted_diagnostics] == [item["status"] for item in baseline_diagnostics]
    assert all(branch["samples"][1] is not None for branch in permuted)


def test_degenerate_cluster_split_records_parent_child_lineage() -> None:
    mass = np.eye(2)
    degenerate = np.eye(2, dtype=np.complex128)
    split = np.asarray([[1.0, 1.0], [1.0j, -1.0j]], dtype=np.complex128) / np.sqrt(2.0)
    branches, diagnostics = track_modal_sweep(
        [_result(0.0, [10.0, 10.0], degenerate), _result(5.0, [9.0, 11.0], split)], mass
    )

    parent = next(branch for branch in branches if branch["branch_id"] == "cluster-000")
    children = parent["child_branch_ids"]
    assert len(children) == 2
    assert all(next(branch for branch in branches if branch["branch_id"] == child)["parent_branch_ids"] == ["cluster-000"] for child in children)
    split_events = [item for item in diagnostics if item.get("event") == "CLUSTER_SPLIT"]
    assert len(split_events) == 2
    assert all(item["combined_subspace_minimum_singular_value"] == pytest.approx(1.0) for item in split_events)


def test_degenerate_basis_rotation_is_reported_as_cluster_ambiguity() -> None:
    mass = np.eye(2)
    previous = np.eye(2, dtype=np.complex128)
    angle = np.pi / 4.0
    current = np.asarray([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]], dtype=np.complex128)
    branches, diagnostics = track_modal_sweep(
        [_result(1.0, [10.0, 10.0], previous), _result(2.0, [10.0, 10.0], current)], mass
    )

    assert len(branches) == 1
    assert branches[0]["samples"][1]["ambiguity_status"] == "DEGENERATE_CLUSTER"
    assert diagnostics[0]["individual_association_status"] == "MULTIPLE_CANDIDATES"
    assert diagnostics[0]["individual_edges_committed"] is False


def test_competing_source_modes_make_the_global_assignment_ambiguous() -> None:
    mass = np.eye(2)
    first = np.asarray([1.0, 0.0], dtype=np.complex128)
    angle = 0.2
    second = np.asarray([np.cos(angle), np.sin(angle)], dtype=np.complex128)
    middle = np.asarray([np.cos(angle / 2.0), np.sin(angle / 2.0)], dtype=np.complex128)
    branches, diagnostics = track_modal_sweep(
        [
            _result(0.0, [10.0, 10.1], np.column_stack((first, second))),
            _result(1.0, [10.05], middle[:, None]),
        ],
        mass,
    )

    sample = next(branch["samples"][1] for branch in branches if branch["samples"][1] is not None)
    assert sample["ambiguity_status"] == "MULTIPLE_CANDIDATES"
    assert len(sample["candidate_branch_ids"]) == 2
    assert 0.0 <= diagnostics[0]["ambiguity_margin"] < 0.05
    assert len(diagnostics[0]["admissible_edges_for_target"]) == 2
    assert all("complex_mac" in edge and "assignment_cost" in edge for edge in diagnostics[0]["admissible_edges_for_target"])
