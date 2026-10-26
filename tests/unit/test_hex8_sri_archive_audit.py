"""Synthetic-only tests for archived-state integrity post-processing."""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from experiments.hex8_sri_equilibrium.archive_audit import (
    load_npz_arrays,
    recompute_archived_state,
    verify_file_hash,
)


def _synthetic_axial_spring() -> dict[str, np.ndarray]:
    stiffness = np.zeros((6, 6), dtype=float)
    stiffness[np.ix_((0, 3), (0, 3))] = ((10.0, -10.0), (-10.0, 10.0))
    stiffness[4, 4] = 20.0
    stiffness[5, 5] = 30.0
    fixed = np.asarray((0, 1, 2), dtype=np.int64)
    free = np.asarray((3, 4, 5), dtype=np.int64)
    displacement = np.asarray((0.0, 0.0, 0.0, -0.2, 0.0, 0.0))
    force = stiffness @ displacement
    residual = stiffness @ displacement - force
    return {
        "K": stiffness,
        "Kff": stiffness[np.ix_(free, free)],
        "nodes_m": np.asarray(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0))),
        "fixed_dofs": fixed,
        "free_dofs": free,
        "F_N": force,
        "u_m": displacement,
        "free_residual_N": residual[free],
        "support_reactions_N": residual[fixed],
    }


def test_synthetic_archived_state_recomputes_residual_reaction_and_energy() -> None:
    arrays = _synthetic_axial_spring()

    actual = recompute_archived_state(arrays)

    assert actual["free_residual_l2_N"] == 0.0
    assert actual["free_residual_max_abs_difference_from_archive_N"] == 0.0
    assert actual["support_reactions_max_abs_difference_from_archive_N"] == 0.0
    assert actual["internal_energy_J"] == pytest.approx(0.2)
    assert actual["external_load_work_J"] == pytest.approx(0.4)
    assert actual["energy_defect_J"] == pytest.approx(0.0)
    assert actual["stiffness_symmetry_relative_fro"] == 0.0
    assert actual["condition_number_2_Kff"] == pytest.approx(3.0)
    assert actual["reduced_matrix_matches_global_block"] is True


def test_recompute_refuses_an_incomplete_or_overlapping_dof_partition() -> None:
    arrays = _synthetic_axial_spring()
    arrays["free_dofs"] = np.asarray((2, 3, 4), dtype=np.int64)

    with pytest.raises(ValueError, match="disjoint partition"):
        recompute_archived_state(arrays)


def test_recompute_refuses_a_reduced_matrix_not_bound_to_archived_global_matrix() -> None:
    arrays = _synthetic_axial_spring()
    arrays["Kff"] = arrays["Kff"] + np.eye(3)

    with pytest.raises(ValueError, match="differs from the free-free block"):
        recompute_archived_state(arrays)


def test_npz_loader_disallows_pickle_and_reads_only_archived_arrays(tmp_path) -> None:
    path = tmp_path / "synthetic-state.npz"
    np.savez(path, **_synthetic_axial_spring())

    arrays = load_npz_arrays(path)

    assert set(arrays) == set(_synthetic_axial_spring())
    assert recompute_archived_state(arrays)["reduced_matrix_matches_global_block"] is True


def test_file_hash_verifier_reports_missing_and_changed_files(tmp_path) -> None:
    path = tmp_path / "evidence.bin"
    expected = hashlib.sha256(b"immutable evidence").hexdigest()

    missing = verify_file_hash(path, expected)
    assert missing["status"] == "MISSING_ARTIFACT"

    path.write_bytes(b"altered evidence")
    changed = verify_file_hash(path, expected)
    assert changed["status"] == "INTEGRITY_MISMATCH"
