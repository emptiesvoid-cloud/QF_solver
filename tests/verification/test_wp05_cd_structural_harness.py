"""Targeted tests for the prospective WP05-C/D structural harness."""

from __future__ import annotations

import json

import numpy as np
import pytest

from scripts.wp05_cd_structural_harness import (
    CONTRACT_JSON,
    DEFAULT_TERMINATION_POLICY,
    MESH_LEVELS,
    StructuralBenchmarkContract,
    StructuralQualificationRunner,
    build_mesh,
    check_load_conservation,
    check_volume_conservation,
    extract_structural_observables,
    mesh_quality,
)


def test_frozen_structural_contract_values() -> None:
    contract = StructuralBenchmarkContract()
    assert (contract.length, contract.height, contract.depth) == (4.0, 0.5, 0.5)
    assert (contract.young_modulus, contract.poisson_ratio) == (1.0e6, 0.30)
    assert contract.total_load == (0.0, -50.0, 0.0)
    assert contract.sample_region == ((0.40, 0.60), (0.70, 0.95), (0.20, 0.80))
    assert contract.deformation_envelope == (0.20, (0.75, 1.30), 0.30)
    assert dict(contract.mesh_thresholds)["representative_sigma_xx"] == 0.08
    assert dict(contract.equilibrium_thresholds) == {"force_relative_error": 1.0e-8, "moment_relative_error": 1.0e-8}


def test_machine_readable_contract_is_valid_and_preparation_only() -> None:
    record = json.loads(CONTRACT_JSON.read_text(encoding="utf-8"))
    assert record["evidence_id"] == "VNV029-WP05-CD-STRUCTURAL-CONTRACT-001"
    assert record["status"] == "PREPARATION_ONLY_PENDING_WP04"
    assert record["execution"]["h2_qualification"] == "NO"
    assert record["execution"]["h3_qualification"] == "NO"
    assert record["governance"]["solver_or_formulation_changed"] is False


def test_frozen_benchmark_mesh_levels_and_counts() -> None:
    assert [(level.name, level.nx, level.ny, level.nz) for level in MESH_LEVELS] == [
        ("H1", 4, 2, 2),
        ("H2", 8, 4, 4),
        ("H3", 16, 8, 8),
    ]
    def counts(family: str, level) -> tuple[int, int]:
        mesh = build_mesh(family, level)
        return mesh.nodes, mesh.elements

    assert {family: {level.name: counts(family, level) for level in MESH_LEVELS} for family in ("TET10", "HEX20")} == {
        "TET10": {"H1": (225, 96), "H2": (1377, 768), "H3": (9537, 6144)},
        "HEX20": {"H1": (141, 16), "H2": (785, 128), "H3": (5121, 1024)},
    }


@pytest.mark.parametrize("family", ["TET10", "HEX20"])
def test_h1_generation_is_deterministic_and_qualitatively_valid(family: str) -> None:
    first = build_mesh(family, "H1")
    second = build_mesh(family, "H1")
    np.testing.assert_array_equal(first.coordinates, second.coordinates)
    assert first.connectivity == second.connectivity
    quality = mesh_quality(first)
    assert quality["finite_coordinates"] is True
    assert quality["connectivity_in_range"] is True
    assert quality["unique_local_connectivity"] is True
    assert quality["unique_midside_nodes"] is True
    if family == "TET10":
        assert quality["positive_reference_orientation"] is True
        assert quality["finite_positive_hammer4_jacobians"] is True
        assert quality["straight_sided"] is True
    else:
        assert quality["positive_jacobians_all_27_gauss_points"] is True
        assert quality["gauss_points_per_element"] == 27
        assert quality["full_integration"] is True
        assert quality["reduced_integration_or_hourglass_claim"] is False


@pytest.mark.parametrize("family", ["TET10", "HEX20"])
@pytest.mark.parametrize("level", MESH_LEVELS)
def test_load_and_reference_volume_are_mesh_independent(family: str, level) -> None:
    mesh = build_mesh(family, level)
    assert check_load_conservation(mesh)["status"] == "PASS"
    np.testing.assert_allclose(check_load_conservation(mesh)["resultant"], [0.0, -50.0, 0.0], atol=1.0e-12, rtol=0.0)
    assert check_volume_conservation(mesh)["status"] == "PASS"
    assert mesh.reference_volume == pytest.approx(1.0, abs=1.0e-12)


def _synthetic_observable_inputs(mesh):
    displacement = np.zeros((mesh.nodes, 3), dtype=float)
    displacement[np.asarray(mesh.end_face_nodes), 1] = -0.125
    reactions = np.zeros((mesh.nodes, 3), dtype=float)
    clamp_nodes = [index for index, point in enumerate(mesh.coordinates) if point[0] == 0.0]
    reactions[np.asarray(clamp_nodes), 1] = 50.0 / len(clamp_nodes)
    records = [
        {
            "coordinates": [2.0, 0.40, 0.25],
            "weight": 1.0,
            "deformation_gradient": np.eye(3),
            "green_lagrange_strain": np.zeros((3, 3)),
            "cauchy_stress": np.diag([10.0, 0.0, 0.0]),
        },
        {
            "coordinates": [2.0, 0.45, 0.30],
            "weight": 3.0,
            "deformation_gradient": np.eye(3),
            "green_lagrange_strain": np.zeros((3, 3)),
            "cauchy_stress": np.diag([20.0, 0.0, 0.0]),
        },
    ]
    diagnostics = {"increments": [{"load_factor": 0.5, "iterations": 3}, {"load_factor": 1.0, "iterations": 4}]}
    return displacement, reactions, records, diagnostics


def test_observable_extraction_and_deformation_envelope_are_explicit() -> None:
    mesh = build_mesh("HEX20", "H1")
    displacement, reactions, records, diagnostics = _synthetic_observable_inputs(mesh)
    observables = extract_structural_observables(mesh, displacement, reactions, 2.5, records, diagnostics)
    assert observables["mean_end_displacement_y"] == pytest.approx(-0.125)
    assert observables["clamp_reaction_resultant"] == pytest.approx([0.0, 50.0, 0.0])
    assert observables["clamp_reaction_moment_z"] == pytest.approx(0.0)
    assert observables["representative_sigma_xx"] == pytest.approx(17.5)
    assert observables["accepted_load_factor_history"] == [0.5, 1.0]
    assert observables["newton_iteration_count"] == 7
    assert StructuralQualificationRunner().evaluate_precomputed(observables)["status"] == "PASS"


def test_replay_checker_is_deterministic_and_uses_frozen_tolerance() -> None:
    mesh = build_mesh("TET10", "H1")
    displacement, reactions, records, diagnostics = _synthetic_observable_inputs(mesh)
    runner = StructuralQualificationRunner()
    first = extract_structural_observables(mesh, displacement, reactions, 2.5, records, diagnostics)
    second = dict(first)
    assert runner.check_replay(first, second)["status"] == "PASS"
    second["strain_energy"] = first["strain_energy"] * (1.0 + 2.0e-12)
    assert runner.check_replay(first, second)["status"] == "FAIL"
    assert runner.termination_policy == DEFAULT_TERMINATION_POLICY
    assert runner.termination_policy.agent_a_policy is False


def test_nonfinite_observable_input_is_rejected() -> None:
    mesh = build_mesh("HEX20", "H1")
    displacement, reactions, records, diagnostics = _synthetic_observable_inputs(mesh)
    displacement[mesh.end_face_nodes[0], 1] = np.inf
    with pytest.raises(ValueError, match="Displacement"):
        extract_structural_observables(mesh, displacement, reactions, 2.5, records, diagnostics)


def test_sampling_region_rejects_missing_physical_samples() -> None:
    mesh = build_mesh("TET10", "H1")
    displacement, reactions, records, diagnostics = _synthetic_observable_inputs(mesh)
    records[0]["coordinates"] = [0.0, 0.0, 0.0]
    records[1]["coordinates"] = [4.0, 0.5, 0.5]
    with pytest.raises(ValueError, match="sampling region"):
        extract_structural_observables(mesh, displacement, reactions, 2.5, records, diagnostics)
