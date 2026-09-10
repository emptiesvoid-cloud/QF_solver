"""WP09 PYRAMID5 feasibility gates frozen by the predeclared contract."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.run_wp09_pyramid5 import (
    CONTRACT_PATH,
    EVIDENCE_PATH,
    distorted_coordinates,
    elemental_metrics,
    geometric_metrics,
    gmsh_import_metrics,
    load_metrics,
    patch_metrics,
    regular_coordinates,
    transition_metrics,
)
from solveur.elements.registry import ElementRegistry
from solveur.elements.solid.pyramid5 import Pyramid5Element
from solveur.materials.solid import SolidMaterial


ROOT = Path(__file__).resolve().parents[2]


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp09_contract_precedes_the_feasibility_campaign() -> None:
    contract = _load(CONTRACT_PATH)
    evidence = _load(EVIDENCE_PATH)

    assert contract["status"] == "PREDECLARED_FEASIBILITY_CONTRACT"
    assert contract["tolerance_policy"]["fixed_before_execution"] is True
    assert contract["tolerance_policy"]["post_observation_retuning"] is False
    assert evidence["baseline_sha"] == contract["baseline_sha"]
    assert evidence["technical_decision"] == "FEASIBLE_CONTINUE"
    assert evidence["integrity"]["historical_0_2_7_evidence_changed"] is False
    assert evidence["integrity"]["wp07_wp08_claims_changed"] is False


def test_pyramid5_elemental_mathematical_gates_pass() -> None:
    contract = _load(CONTRACT_PATH)["tolerance_policy"]
    metrics = elemental_metrics()

    assert ElementRegistry.get("PYRAMID5").node_count == 5
    assert metrics["kronecker_max_abs"] <= contract["kronecker_absolute"]
    assert metrics["partition_unity_max_abs"] <= contract["partition_unity_absolute"]
    assert metrics["derivative_sum_max_abs"] <= contract["derivative_sum_absolute"]
    assert metrics["affine_strain_max_abs"] <= contract["affine_displacement_and_strain_relative"]
    assert metrics["stiffness_rank"] == contract["expected_stiffness_rank"]
    assert metrics["stiffness_symmetry_relative"] <= contract["stiffness_symmetry_relative"]
    assert metrics["rigid_body_relative_residual"] <= contract["affine_displacement_and_strain_relative"]
    assert metrics["minimum_positive_eigenvalue_relative"] >= contract["positive_energy_relative_eigenvalue"]
    assert metrics["production_reference_stiffness_relative"] <= contract["production_reference_stiffness_relative"]
    assert metrics["mass_conservation_relative"] <= contract["mass_conservation_relative"]


def test_pyramid5_geometry_rejects_the_bounded_invalid_cases() -> None:
    metrics = geometric_metrics()
    assert metrics["status"] == "PASS"
    assert set(metrics["valid_cases"]) == {"regular", "apex_offset", "base_distorted", "reduced_height"}
    assert all("PYRAMID5_JACOBIAN_INVALID" in value for value in metrics["invalid_cases"].values())

    element = Pyramid5Element(SolidMaterial(E=210.0e9, nu=0.3, density=7_800.0))
    with np.testing.assert_raises_regex(ValueError, "undefined at the collapsed apex"):
        element.shape_derivatives_reference((0.0, 0.0, 1.0))
    Pyramid5Element.validate_geometry(regular_coordinates())
    Pyramid5Element.validate_geometry(distorted_coordinates())


def test_pyramid5_patch_load_import_and_transition_gates_pass() -> None:
    contract = _load(CONTRACT_PATH)["tolerance_policy"]
    patch = patch_metrics()
    loads = load_metrics()
    imported = gmsh_import_metrics()
    transition = transition_metrics()

    assert patch["displacement_max_abs_error"] <= contract["affine_displacement_and_strain_relative"]
    assert patch["strain_max_abs_error"] <= contract["affine_displacement_and_strain_relative"]
    assert patch["stress_relative_error"] <= contract["patch_reaction_energy_relative"]
    assert patch["free_residual_relative"] <= contract["patch_reaction_energy_relative"]
    assert patch["force_balance_relative"] <= contract["patch_reaction_energy_relative"]
    assert patch["energy_identity_relative"] <= contract["patch_reaction_energy_relative"]
    assert patch["post_processing"] == "PASS"
    assert loads["body_resultant_relative"] <= contract["patch_reaction_energy_relative"]
    assert all(value > 0.0 for value in loads["surface_traction_vector_norms"].values())
    assert imported == {"status": "PASS", "family": "PYRAMID5", "element_type": "PYRAMID5"}
    assert transition["status"] == "PASS"
    assert transition["duplicate_global_dofs"] is False
    assert transition["affine_displacement_max_abs_error"] <= contract["affine_displacement_and_strain_relative"]
    assert transition["force_balance_relative"] <= contract["transition_equilibrium_relative"]
    assert transition["energy_identity_relative"] <= contract["transition_equilibrium_relative"]


def test_wp09_replays_are_exact_and_no_maturity_is_promoted() -> None:
    evidence = _load(EVIDENCE_PATH)
    replay = evidence["replay_determinism"]

    assert replay["status"] == "PASS"
    assert replay["digests"][0] == replay["digests"][1]
    assert evidence["convergence"].startswith("NOT_RUN")
    assert "No production qualification" in evidence["limitations"][0]
