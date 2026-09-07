"""Run the additive QF Solver 0.2.8 WEDGE6 static V&V campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Callable

import numpy as np

from solveur.elements.solid.wedge6 import Wedge6Element
from solveur.loads.entities import SurfaceLoad
from solveur.loads.integration import DistributedLoadIntegrator
from solveur.materials.solid import SolidMaterial
from solveur.mesh.quality_contract import INVALID, VALID, VALID_WITH_WARNING, assess_element
from solveur.mesh.topology import WEDGE6_FACES
from solveur.verification.v2 import ExecutionOutput, VnvRunner, canonical_sha256, load_cases, load_json_strict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_wedge6_wp07 as wp07  # noqa: E402
from scripts import run_wp08_wedge6 as wp08  # noqa: E402
from scripts import run_wp09_wedge6 as wp09  # noqa: E402


CONTRACT = ROOT / "qualification/0_2_8/wp05_wedge6_contract.json"
HISTORICAL_EXTERNAL = ROOT / "qualification/0_2_7/vnv_v2/wp09_final_external_evidence.json"
HISTORICAL_EXTERNAL_CONTRACT = ROOT / "qualification/0_2_7/external_oracles/wedge6/wp09_final_contract.json"
SOURCE_COMPARISON_COMMIT = "4b2fcdc9ed51821b05b52851912be3ebbe764b14"
GIT = shutil.which("git.exe") or shutil.which("git") or "git"
MATERIAL = SolidMaterial(E=210.0e9, nu=0.3, density=7800.0)
NODES = np.asarray(
    (
        (0.0, 0.0, 0.0),
        (2.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
        (2.0, 0.0, 1.0),
        (0.0, 1.0, 1.0),
    ),
    dtype=float,
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _run_catalog(
    catalog: Path,
    executor: Callable[[Any], ExecutionOutput],
    source_sha: str,
    runner_name: str,
) -> list[dict[str, Any]]:
    runner = VnvRunner(source_sha=source_sha, environment={"runner": runner_name, "catalog": catalog.name})
    return [runner.run(case, executor).to_dict() for case in load_cases(catalog)]


def _wp09_executor(case: Any) -> ExecutionOutput:
    details = wp09._execute_internal(case.case_id, case.expected_failure)
    return ExecutionOutput({"status": details["status"]})


def _wp08_executor(case: Any) -> ExecutionOutput:
    try:
        return wp08._result(case.case_id)
    except Exception as exc:
        if case.expected_failure and "WEDGE6" in str(exc):
            raise RuntimeError(case.expected_failure) from exc
        raise


def _catalog_replay(
    catalog: Path,
    executor: Callable[[Any], ExecutionOutput],
    source_sha: str,
    runner_name: str,
) -> dict[str, Any]:
    first = _run_catalog(catalog, executor, source_sha, runner_name)
    second = _run_catalog(catalog, executor, source_sha, runner_name)
    first_digests = [item["result_digest"] for item in first]
    second_digests = [item["result_digest"] for item in second]
    counts = {
        verdict: sum(item["verdict"] == verdict for item in first)
        for verdict in sorted({item["verdict"] for item in first})
    }
    return {
        "catalog": str(catalog.relative_to(ROOT)).replace("\\", "/"),
        "case_count": len(first),
        "verdict_counts": counts,
        "case_ids": [item["case_id"] for item in first],
        "case_result_digests": first_digests,
        "replay_digests": [canonical_sha256(first_digests), canonical_sha256(second_digests)],
        "deterministic": first_digests == second_digests,
        "all_declared_verdicts_pass": all(
            item["verdict"] in {"PASS", "EXPECTED_FAILURE_PASS"} for item in first
        ),
    }


def _elemental_checks() -> dict[str, Any]:
    element = Wedge6Element(MATERIAL)
    point = (0.21, 0.37, -0.23)
    shape = element.shape_functions(point)
    derivatives = element.shape_derivatives_reference(point)
    nodal_errors = []
    for index, node in enumerate(element.reference_nodes):
        values = element.shape_functions(tuple(node))
        nodal_errors.append(float(np.max(np.abs(values - np.eye(6)[index]))))
    transform = np.asarray(((2.0, 0.2, 0.1), (0.0, 1.5, 0.2), (0.1, 0.0, 3.0)))
    mapped_nodes = element.reference_nodes @ transform.T + (1.0, -2.0, 0.5)
    mapped_point = shape @ mapped_nodes
    expected_point = np.asarray(point) @ transform.T + (1.0, -2.0, 0.5)
    coords = NODES
    stiffness = element.stiffness(coords)
    reference_stiffness = element.reference_stiffness(coords)
    stiffness_scale = max(float(np.linalg.norm(stiffness)), 1.0e-30)
    stiffness_symmetry = float(np.linalg.norm(stiffness - stiffness.T) / stiffness_scale)
    rank = int(np.linalg.matrix_rank(stiffness, tol=np.max(np.abs(stiffness)) * 1.0e-10))
    centroid = np.mean(coords, axis=0)
    rigid_vectors = [
        np.tile((1.0, 0.0, 0.0), 6),
        np.tile((0.0, 1.0, 0.0), 6),
        np.tile((0.0, 0.0, 1.0), 6),
    ]
    for axis in np.eye(3):
        rigid_vectors.append(np.cross(axis, coords - centroid).reshape(-1))
    rigid_residual = max(
        float(np.linalg.norm(stiffness @ vector) / max(np.linalg.norm(stiffness) * np.linalg.norm(vector), 1.0e-30))
        for vector in rigid_vectors
    )
    strain_matrix = np.asarray(
        ((0.02, 0.002, 0.003), (0.002, -0.01, -0.0025), (0.003, -0.0025, 0.03)),
        dtype=float,
    )
    displacement = (coords @ strain_matrix.T).reshape(-1)
    expected_strain = np.asarray(
        (
            strain_matrix[0, 0],
            strain_matrix[1, 1],
            strain_matrix[2, 2],
            strain_matrix[0, 1] + strain_matrix[1, 0],
            strain_matrix[1, 2] + strain_matrix[2, 1],
            strain_matrix[0, 2] + strain_matrix[2, 0],
        )
    )
    strain_errors = [
        float(np.max(np.abs(element.strain_at(coords, displacement, point) - expected_strain)))
        for point in element.integration_points
    ]
    expected_stress = MATERIAL.elasticity_matrix @ expected_strain
    stress_errors = [
        float(np.linalg.norm(element.stress_at(coords, displacement, point) - expected_stress) / max(np.linalg.norm(expected_stress), 1.0e-30))
        for point in element.integration_points
    ]
    internal, tangent = element.internal_force_and_tangent(coords, displacement)
    energy = 0.5 * float(displacement @ internal)
    tangent_energy = 0.5 * float(displacement @ tangent @ displacement)
    production_volume = element.signed_volume(coords)
    reference_volume = element.signed_volume(coords, "reference")
    production_reference_difference = float(
        np.linalg.norm(stiffness - reference_stiffness) / max(np.linalg.norm(reference_stiffness), 1.0e-30)
    )
    results = element.integration_point_results(coords, displacement, MATERIAL)
    return {
        "shape_partition_abs": abs(float(np.sum(shape)) - 1.0),
        "shape_kronecker_max_abs": max(nodal_errors),
        "derivative_sum_max_abs": float(np.max(np.abs(np.sum(derivatives, axis=0)))),
        "affine_mapping_abs": float(np.max(np.abs(mapped_point - expected_point))),
        "minimum_production_detJ": min(element.jacobian_determinant(coords, point) for point in element.integration_points),
        "stiffness_symmetry_relative": stiffness_symmetry,
        "stiffness_rank": rank,
        "rigid_body_residual_relative": rigid_residual,
        "affine_strain_max_abs": max(strain_errors),
        "constitutive_stress_relative": max(stress_errors),
        "energy_identity_relative": abs(energy - tangent_energy) / max(abs(energy), 1.0e-30),
        "production_reference_stiffness_relative": production_reference_difference,
        "production_volume": production_volume,
        "reference_volume": reference_volume,
        "integration_point_count": len(results),
        "post_processing_finite": bool(
            all(np.isfinite(np.asarray(row["strain"])).all() and np.isfinite(np.asarray(row["stress"])).all() for row in results)
        ),
    }


def _face_load_checks() -> dict[str, Any]:
    model = wp08._model()
    integrator = DistributedLoadIntegrator()
    pressure_errors = []
    face_resultants: dict[str, list[float]] = {}
    for face_index, face in enumerate(WEDGE6_FACES):
        face_coords = NODES[list(face)]
        if len(face) == 3:
            area_vector = 0.5 * np.cross(face_coords[1] - face_coords[0], face_coords[2] - face_coords[0])
        else:
            area_vector = 0.5 * (
                np.cross(face_coords[1] - face_coords[0], face_coords[2] - face_coords[0])
                + np.cross(face_coords[2] - face_coords[0], face_coords[3] - face_coords[0])
            )
        expected = -2.0 * area_vector
        load = SurfaceLoad(0, "pressure", 2.0, face=face_index)
        details = integrator.integrate_sparse(model, model.dof_manager(), load, face_index).details
        actual = np.asarray(details["resultant"], dtype=float)
        pressure_errors.append(float(np.linalg.norm(actual - expected) / max(np.linalg.norm(expected), 1.0e-30)))
        face_resultants[str(face_index)] = actual.tolist()
    traction = SurfaceLoad(0, "surface_traction", (1.0, -2.0, 3.0), face=2)
    traction_details = integrator.integrate_sparse(model, model.dof_manager(), traction, 5).details
    side = NODES[list(WEDGE6_FACES[2])]
    side_area = 0.5 * np.linalg.norm(
        np.cross(side[1] - side[0], side[2] - side[0]) + np.cross(side[2] - side[0], side[3] - side[0])
    )
    expected_traction = np.asarray((1.0, -2.0, 3.0)) * side_area
    traction_resultant = np.asarray(traction_details["resultant"], dtype=float)
    return {
        "pressure_all_faces_max_relative_error": max(pressure_errors),
        "pressure_face_resultants": face_resultants,
        "traction_relative_error": float(
            np.linalg.norm(traction_resultant - expected_traction) / max(np.linalg.norm(expected_traction), 1.0e-30)
        ),
        "triangular_faces_checked": 2,
        "quadrilateral_faces_checked": 3,
    }


def _geometry_checks() -> dict[str, Any]:
    skew = np.asarray(((1.0, 0.25, 0.0), (0.0, 1.0, 0.15), (0.0, 0.0, 1.0)))
    skewed = NODES @ skew.T
    flat = NODES.copy()
    flat[3:, 2] = 0.0
    near_degenerate = NODES.copy()
    near_degenerate[3:, 2] = (1.0e-9, 3.0, 3.0)
    inverted = NODES[[0, 2, 1, 3, 5, 4]]
    cyclic = NODES[[1, 2, 0, 4, 5, 3]]
    nominal = assess_element(0, "WEDGE6", NODES)
    valid_skew = assess_element(1, "WEDGE6", skewed)
    warning = assess_element(2, "WEDGE6", near_degenerate)
    flat_assessment = assess_element(3, "WEDGE6", flat)
    inverted_assessment = assess_element(4, "WEDGE6", inverted)
    cyclic_assessment = assess_element(5, "WEDGE6", cyclic)
    return {
        "nominal": nominal.classification,
        "valid_skew": valid_skew.classification,
        "near_degenerate": warning.classification,
        "flat": flat_assessment.classification,
        "flat_fatal_findings": list(flat_assessment.fatal_findings),
        "inverted": inverted_assessment.classification,
        "inverted_fatal_findings": list(inverted_assessment.fatal_findings),
        "cyclic_permutation": cyclic_assessment.classification,
        "cyclic_permutation_policy": "explicitly assessed; no automatic repair",
        "direct_invalid_geometry_rejected": _direct_invalid_geometry_rejected(inverted),
    }


def _direct_invalid_geometry_rejected(coords: np.ndarray) -> bool:
    try:
        Wedge6Element(MATERIAL).validate_geometry(coords)
    except ValueError as exc:
        return "WEDGE6_JACOBIAN_ORIENTATION_INVALID" in str(exc)
    return False


def _convergence_checks() -> dict[str, Any]:
    observations = []
    for level in (1, 2, 4):
        details = wp09._solve_details(wp09._stacked_model(level))
        observations.append(
            {
                "level": level,
                "element_count": details["element_count"],
                "node_count": details["node_count"],
                "status": details["status"],
                "displacement_norm": details["displacement_norm"],
                "free_relative_residual": details["free_relative_residual"],
                "force_balance_relative_error": details["force_balance_relative_error"],
                "moment_balance_relative_error": details["moment_balance_relative_error"],
                "strain_energy": details["strain_energy"],
            }
        )
    return {
        "levels": observations,
        "all_pass": all(item["status"] == "PASS" for item in observations),
        "refinement_levels": [item["level"] for item in observations],
    }


def _external_audit() -> dict[str, Any]:
    evidence = load_json_strict(HISTORICAL_EXTERNAL)
    contract = load_json_strict(HISTORICAL_EXTERNAL_CONTRACT)
    records = evidence["records"]
    pass_records = [record for record in records if record["verdict"] == "PASS_EXTERNAL_CORRELATION_BOUNDED"]
    source_paths = (
        "src/solveur/elements/solid/wedge6.py",
        "src/solveur/mesh/quality_contract.py",
        "src/solveur/mesh/topology.py",
        "src/solveur/loads/integration.py",
    )
    unchanged_since_external = all(
        subprocess.run(
            [GIT, "diff", "--quiet", SOURCE_COMPARISON_COMMIT, "--", path],
            cwd=ROOT,
            check=False,
        ).returncode
        == 0
        for path in source_paths
    )
    max_errors = {
        observable: max(record["relative_error"][observable] for record in pass_records)
        for observable in ("displacement", "total_reaction", "strain_energy")
    }
    return {
        "artifact": str(HISTORICAL_EXTERNAL.relative_to(ROOT)).replace("\\", "/"),
        "artifact_sha256": _sha256_file(HISTORICAL_EXTERNAL),
        "contract_sha256": _sha256_file(HISTORICAL_EXTERNAL_CONTRACT),
        "historical_source_sha": evidence["source_sha"],
        "current_numeric_source_unchanged_since_external": unchanged_since_external,
        "solver": evidence["headless_oracle"],
        "cases_total": evidence["summary"]["cases_total"],
        "external_cases_run": evidence["summary"]["external_cases_run"],
        "external_pass": evidence["summary"]["external_pass"],
        "external_fail": evidence["summary"]["external_fail"],
        "external_skipped": evidence["summary"]["external_skipped"],
        "max_relative_errors": max_errors,
        "tolerance_policy_fixed_before_execution": evidence["tolerance_policy"]["fixed_before_execution"],
        "post_result_retuning": evidence["tolerance_policy"]["post_result_retuning"],
        "external_replay": evidence["determinism"]["external_final_case"],
        "qf_replay": evidence["determinism"]["qf_final_case"],
        "calculix_status": evidence["calculix"]["verdict"],
        "independent_comparable": len(pass_records) == 12 and contract["external_policy"]["calculix"] != "PASS",
        "executed_in_wp05": False,
        "reuse_policy": "The 0.2.7 controlled Code_Aster artifact is preserved and audited; it is not rewritten or falsely relabeled as a current rerun.",
    }


def run(output: Path) -> dict[str, Any]:
    contract = load_json_strict(CONTRACT)
    source_sha = subprocess.check_output([GIT, "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if source_sha != contract["baseline_sha"]:
        raise RuntimeError(f"WP05 must execute at its declared baseline {contract['baseline_sha']}, got {source_sha}.")
    wp07_summary = _catalog_replay(
        ROOT / "qualification/0_2_7/vnv_v2/wp07_cases.json", wp07._execute, source_sha, "run_wp05_wp07_replay"
    )
    wp08_summary = _catalog_replay(
        ROOT / "qualification/0_2_7/vnv_v2/wp08_cases.json", _wp08_executor, source_sha, "run_wp05_wp08_replay"
    )
    wp09_summary = _catalog_replay(
        ROOT / "qualification/0_2_7/vnv_v2/wp09_cases.json", _wp09_executor, source_sha, "run_wp05_wp09_replay"
    )
    elemental = _elemental_checks()
    face_loads = _face_load_checks()
    geometry = _geometry_checks()
    convergence = _convergence_checks()
    external = _external_audit()
    internal_pass = all(
        item["deterministic"] and item["all_declared_verdicts_pass"]
        for item in (wp07_summary, wp08_summary, wp09_summary)
    )
    elemental_pass = (
        elemental["shape_partition_abs"] <= contract["tolerance_policy"]["element_partition_and_derivative_sum_abs"]
        and elemental["shape_kronecker_max_abs"] <= contract["tolerance_policy"]["element_partition_and_derivative_sum_abs"]
        and elemental["derivative_sum_max_abs"] <= contract["tolerance_policy"]["element_partition_and_derivative_sum_abs"]
        and elemental["affine_mapping_abs"] <= contract["tolerance_policy"]["affine_mapping_abs"]
        and elemental["stiffness_symmetry_relative"] <= contract["tolerance_policy"]["stiffness_symmetry_relative"]
        and elemental["stiffness_rank"] == contract["tolerance_policy"]["stiffness_rank"]
        and elemental["rigid_body_residual_relative"] <= contract["tolerance_policy"]["rigid_body_residual_relative"]
        and elemental["affine_strain_max_abs"] <= contract["tolerance_policy"]["affine_strain_abs"]
        and elemental["constitutive_stress_relative"] <= contract["tolerance_policy"]["constitutive_stress_relative"]
        and elemental["energy_identity_relative"] <= contract["tolerance_policy"]["energy_identity_relative"]
        and elemental["production_reference_stiffness_relative"] <= contract["tolerance_policy"]["production_reference_stiffness_relative"]
        and elemental["post_processing_finite"]
    )
    loads_pass = (
        face_loads["pressure_all_faces_max_relative_error"] <= contract["tolerance_policy"]["load_resultant_relative"]
        and face_loads["traction_relative_error"] <= contract["tolerance_policy"]["load_resultant_relative"]
    )
    geometry_pass = (
        geometry["nominal"] == VALID
        and geometry["valid_skew"] == VALID
        and geometry["near_degenerate"] == VALID_WITH_WARNING
        and geometry["flat"] == INVALID
        and geometry["inverted"] == INVALID
        and geometry["direct_invalid_geometry_rejected"]
    )
    external_pass = (
        external["independent_comparable"]
        and external["current_numeric_source_unchanged_since_external"]
        and external["tolerance_policy_fixed_before_execution"]
        and not external["post_result_retuning"]
        and external["external_replay"]["status"] == "PASS"
        and external["qf_replay"] == "PASS"
    )
    technical_decision = "QUALIFIED_BOUNDED" if all((internal_pass, elemental_pass, loads_pass, geometry_pass, convergence["all_pass"], external_pass)) else "EXPERIMENTAL"
    payload = {
        "schema_version": 1,
        "record_id": "QF-028-WP05-WEDGE6-VNV",
        "work_package": "WP05",
        "applicable_version": "0.2.8-development",
        "baseline_sha": source_sha,
        "contract": str(CONTRACT.relative_to(ROOT)).replace("\\", "/"),
        "status": "CAMPAIGN_COMPLETE_OWNER_GATE_PENDING",
        "technical_decision": technical_decision,
        "public_maturity": "EXPERIMENTAL",
        "owner_gate_required": True,
        "historical_0_2_7_evidence_modified": False,
        "numerical_source_modified": False,
        "baseline_modified": False,
        "bug_audit": {"bugs_found": False, "bugs_fixed": False},
        "checks": {
            "elemental": {"status": "PASS" if elemental_pass else "FAIL", "observed": elemental},
            "patch_affine": "PASS" if elemental_pass else "FAIL",
            "multi_element_and_equilibrium": "PASS" if internal_pass else "FAIL",
            "face_loads": {"status": "PASS" if loads_pass else "FAIL", "observed": face_loads},
            "post_processing": "PASS" if elemental["post_processing_finite"] else "FAIL",
            "geometry_robustness": {"status": "PASS" if geometry_pass else "FAIL", "observed": geometry},
            "convergence": {"status": "PASS" if convergence["all_pass"] else "FAIL", "observed": convergence},
            "external_oracle": {"status": "PASS" if external_pass else "FAIL", "observed": external},
        },
        "current_replays": {
            "wp07": wp07_summary,
            "wp08": wp08_summary,
            "wp09": wp09_summary,
            "required_replays": 2,
            "replay_policy": "result_digest equality; timestamps and runtimes are not part of the deterministic comparison",
        },
        "promotion_boundary": {
            "scope": contract["scope"],
            "technical_gate": contract["promotion_gate"]["technical_decision"],
            "public_action": "No public maturity relabel is applied before a separate Owner gate.",
            "excluded_routes_remain": ["COMB-WEDGE6-modal public state is unchanged", "WEDGE6 Newmark", "WEDGE6 harmonic"],
        },
        "global_state": {
            "current_public": {"QUALIFIED_BOUNDED": 31, "EXPERIMENTAL": 14, "NOT_QUALIFIED": 1, "TOTAL": 46},
            "technical_if_owner_approves": {"QUALIFIED_BOUNDED": 32, "EXPERIMENTAL": 13, "NOT_QUALIFIED": 1, "TOTAL": 46},
            "not_qualified_combination": "COMB-HEX8-linear_buckling",
            "wedge6_static_current_public": "EXPERIMENTAL",
        },
        "artifact_classification": "CONTROLLED_PROOF",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"technical_decision": technical_decision, "internal_pass": internal_pass, "external_pass": external_pass}, sort_keys=True))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "qualification/0_2_8/wp05_wedge6_vnv.json")
    args = parser.parse_args()
    run(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
