from __future__ import annotations

import numpy as np

from solveur.verification.orthotropic_singularity_vnv import (
    _material_s11,
    _sample_stress,
    _volume_weighted_nodal_recovery,
    apply_external_oracle_policy,
    parse_calculix_nodal_stress,
)


def test_material_s11_projects_global_stress_to_rotated_material_axes() -> None:
    stresses = np.array([[100.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
    assert np.allclose(_material_s11(stresses, 0.0), [100.0])
    assert np.allclose(_material_s11(stresses, 90.0), [0.0], atol=1.0e-12)


def test_sampling_uses_fixed_geometric_targets_and_band_average() -> None:
    centroids = np.array([[0.7, 0.0, 0.0], [1.0, 0.0, 0.0], [1.3, 0.0, 0.0], [0.9, 0.2, 0.0]])
    path, band = _sample_stress(
        centroids,
        np.array([70.0, 100.0, 130.0, 90.0]),
        (0.0, 0.0),
        (1.0, 0.0),
        (0.7, 1.0, 1.3),
        (0.65, 1.05),
        path_radius=0.01,
    )
    assert path == [70.0, 100.0, 130.0]
    assert band == 86.66666666666667


def test_sampling_compact_kernel_prioritizes_centroids_near_target() -> None:
    centroids = np.array([[1.0, 0.0, 0.0], [1.08, 0.0, 0.0], [1.18, 0.0, 0.0]])
    path, _ = _sample_stress(
        centroids,
        np.array([100.0, 200.0, 900.0]),
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0,),
        (0.8, 1.2),
        path_radius=0.2,
    )

    assert 100.0 < path[0] < 200.0


def test_volume_weighted_nodal_recovery_is_exact_for_constant_field() -> None:
    elements = np.array([[0, 1, 2, 3], [1, 2, 3, 4]], dtype=np.int64)
    recovered = _volume_weighted_nodal_recovery(
        5,
        elements,
        np.array([12.0, 12.0]),
        np.array([1.0, 3.0]),
    )

    assert np.allclose(recovered, 12.0)


def test_calculix_frd_parser_reads_final_nodal_stress_block(tmp_path) -> None:
    path = tmp_path / "case.frd"
    path.write_text(
        " -4  STRESS      6    1\n -1         1 1.0E+00-2.0E+00 3.0E+00 4.0E+00 5.0E+00 6.0E+00\n"
        " -1         2 7.0E+00 8.0E+00 9.0E+00 1.0E+01 1.1E+01 1.2E+01\n -3\n",
        encoding="ascii",
    )
    assert np.allclose(parse_calculix_nodal_stress(path, 2), [[1, -2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12]])


def test_external_oracle_policy_keeps_calculix_nodal_difference_diagnostic() -> None:
    level = {
        "level": 1,
        "same_mesh_relative_path_error": 1.0e-12,
        "same_mesh_relative_band_error": 1.0e-12,
        "calculix_nodal_path_error": 0.08,
        "calculix_nodal_band_error": 0.10,
    }
    summary = {
        "cases": [
            {
                "levels": [level],
                "assessment": {"status": "FAIL", "checks": [{"status": "PASS"}]},
            }
        ]
    }

    updated = apply_external_oracle_policy(summary)

    assert updated["status"] == "PASS_STRESS_ACCEPTANCE"
    case = updated["cases"][0]
    assert case["same_mesh_code_aster_checks"][0]["status"] == "PASS"
    assert case["secondary_calculix_nodal_checks"][0]["status"] == "WARNING"
