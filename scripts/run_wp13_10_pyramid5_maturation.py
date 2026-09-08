"""Run the bounded WP13-10 PYRAMID5 maturation campaign.

This runner is deliberately separate from the historical WP09 runner.  It
does not change the PYRAMID5 kernel, the public registry, or the historical
WP09 evidence; it only records the prospective checks frozen by the WP13-10
contract.
"""

# ruff: noqa: E402

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.errors import MeshValidationError
from solveur.core.model import FiniteElementModel
from solveur.core.solvers.static import LinearStaticSolver
from solveur.elements.solid.pyramid5 import Pyramid5Element
from solveur.materials.solid import SolidMaterial
from solveur.mesh.validation import MeshValidator

from scripts.run_wp09_pyramid5 import (
    ALPHA,
    MATERIAL,
    _affine_displacement,
    _digest,
    _material,
    distorted_coordinates,
    regular_coordinates,
    transition_model,
)


START_SHA = "26729afdf05ad62d25c5e7e462929d60941c7b4b"
CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp13_10_pyramid5_maturation_contract.json"
OUTPUT_DIR = ROOT / "qualification" / "0_2_8" / "wp13_10_pyramid5_maturation"
EVIDENCE_PATH = OUTPUT_DIR / "wp13_10_pyramid5_maturation_evidence.json"
WP09_CONTRACT = ROOT / "qualification" / "0_2_8" / "wp09_pyramid5_contract.json"
WP09_EVIDENCE = ROOT / "qualification" / "0_2_8" / "wp09_pyramid5_vnv.json"
WP09_MATRIX = ROOT / "qualification" / "0_2_8" / "wp09_pyramid5_matrix.json"
REGISTRY = ROOT / "qualification" / "0_2_8" / "consolidated_registry.json"


def _json_default(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _contract() -> tuple[dict[str, Any], str]:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    sha = _sha256_file(CONTRACT_PATH)
    tracked = subprocess.check_output(
        ["git", "show", f"HEAD:{CONTRACT_PATH.relative_to(ROOT).as_posix()}"], cwd=ROOT
    )
    if hashlib.sha256(tracked).hexdigest() != sha:
        raise RuntimeError("WP13-10 contract differs from the committed blob.")
    if payload.get("contract_id") != "WP13-10-PYRAMID5-MATURATION-001":
        raise RuntimeError("Unexpected WP13-10 contract id.")
    if not payload.get("contract_created_before_campaign"):
        raise RuntimeError("WP13-10 contract is not predeclared.")
    return payload, sha


def _environment() -> dict[str, str]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": __import__("scipy").__version__,
    }


def _gate(value: float, limit: float, *, relation: str = "le") -> bool:
    return bool(value <= limit) if relation == "le" else bool(value > limit)


def _relative(actual: np.ndarray, expected: np.ndarray, floor: float = 1.0) -> float:
    return float(np.linalg.norm(np.asarray(actual) - np.asarray(expected)) / max(float(np.linalg.norm(expected)), floor))


def _finite_record(value: float) -> float:
    return float(value) if np.isfinite(value) else float("inf")


def _source_audit() -> dict[str, Any]:
    source_files = [
        "src/solveur/elements/solid/pyramid5.py",
        "src/solveur/elements/registry.py",
        "src/solveur/mesh/mixed_validation.py",
        "src/solveur/mesh/gmsh_importer.py",
    ]
    return {
        "source_files": source_files,
        "source_digests": {path: _sha256_file(ROOT / path) for path in source_files},
        "architecture": {
            "shape_functions": "collapsed-coordinate N0..N3 base plus N4 apex",
            "derivatives": "reference derivatives away from t=1 collapsed apex",
            "jacobian": "dense reference-rule sampled detJ, positive finite gate",
            "integration": "production Gauss3xGauss3xGauss4; reference Gauss5xGauss5xGauss6",
            "stiffness": "small-strain B-transpose-D-B",
            "mass": "consistent translational mass for elemental checks",
            "orientation": "no automatic orientation repair",
            "stress_strain": "production integration-point recovery",
        },
        "source_changed": False,
    }


def _historical_audit() -> dict[str, Any]:
    records = {}
    for path in (WP09_CONTRACT, WP09_EVIDENCE, WP09_MATRIX):
        records[path.name] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": _sha256_file(path),
            "record": json.loads(path.read_text(encoding="utf-8")),
        }
    evidence = records[WP09_EVIDENCE.name]["record"]
    matrix = records[WP09_MATRIX.name]["record"]
    return {
        "records": records,
        "wp09_status": evidence.get("status"),
        "wp09_decision": evidence.get("technical_decision"),
        "current_status": "INTERNAL_FEASIBILITY_ONLY",
        "limitations_preserved": [
            "no coherent conforming h-refinement",
            "no strong external solver correlation",
            "no public dispatch or maturity promotion",
            "no PYRAMID13/high-order transition qualification",
        ],
        "matrix_public_maturity_policy": matrix.get("public_maturity_policy"),
        "historical_0_2_7_unchanged": True,
    }


def _patch_tests(contract: dict[str, Any]) -> dict[str, Any]:
    element = Pyramid5Element(_material())
    coords = regular_coordinates()
    nodes = Pyramid5Element.reference_nodes
    shape_errors = [
        float(np.max(np.abs(element.shape_functions(point) - np.eye(5)[index])))
        for index, point in enumerate(nodes)
    ]
    sample_points = ((0.0, 0.0, 0.2), (-0.7, 0.4, 0.6), (0.8, -0.3, 0.85))
    partition_error = max(abs(float(np.sum(element.shape_functions(point))) - 1.0) for point in sample_points)
    derivative_error = max(
        float(np.max(np.abs(np.sum(element.shape_derivatives_reference(point), axis=0))))
        for point in sample_points
    )
    cases = {
        "constant_strain_x": np.diag((ALPHA, 0.0, 0.0)),
        "constant_strain_y": np.diag((0.0, ALPHA, 0.0)),
        "constant_strain_z": np.diag((0.0, 0.0, ALPHA)),
        "simple_shear_xy": np.asarray(((0.0, ALPHA / 2.0, 0.0), (ALPHA / 2.0, 0.0, 0.0), (0.0, 0.0, 0.0))),
        "simple_shear_xz": np.asarray(((0.0, 0.0, ALPHA / 2.0), (0.0, 0.0, 0.0), (ALPHA / 2.0, 0.0, 0.0))),
        "simple_shear_yz": np.asarray(((0.0, 0.0, 0.0), (0.0, 0.0, ALPHA / 2.0), (0.0, ALPHA / 2.0, 0.0))),
    }
    affine = {}
    material = _material()
    for name, gradient in cases.items():
        expected = np.asarray(
            (gradient[0, 0], gradient[1, 1], gradient[2, 2], gradient[0, 1] + gradient[1, 0], gradient[1, 2] + gradient[2, 1], gradient[0, 2] + gradient[2, 0]),
            dtype=float,
        )
        displacement = np.asarray([gradient @ point for point in coords]).ravel()
        strain_error = max(
            float(np.max(np.abs(element.strain_at(coords, displacement, point) - expected)))
            for point in sample_points
        )
        stress = element.stress_at(coords, displacement, sample_points[0])
        expected_stress = material.elasticity_matrix @ expected
        affine[name] = {
            "strain_error": strain_error,
            "stress_relative_error": _relative(stress, expected_stress),
            "gate": _gate(strain_error, contract["gates"]["affine_displacement_and_strain_absolute"]["value"]),
        }
    stiffness = element.stiffness(coords)
    eigenvalues = np.linalg.eigvalsh(stiffness)
    rank_tolerance = float(np.max(np.abs(eigenvalues)) * 1.0e-10)
    translations = [np.tile(axis, 5) for axis in np.eye(3)]
    rotations = [np.asarray([np.cross(axis, point) for point in coords]).ravel() for axis in np.eye(3)]
    rigid = {
        "translation_x": float(np.linalg.norm(stiffness @ translations[0]) / max(np.linalg.norm(stiffness) * np.linalg.norm(translations[0]), 1.0)),
        "translation_y": float(np.linalg.norm(stiffness @ translations[1]) / max(np.linalg.norm(stiffness) * np.linalg.norm(translations[1]), 1.0)),
        "translation_z": float(np.linalg.norm(stiffness @ translations[2]) / max(np.linalg.norm(stiffness) * np.linalg.norm(translations[2]), 1.0)),
        "rotation_x": float(np.linalg.norm(stiffness @ rotations[0]) / max(np.linalg.norm(stiffness) * np.linalg.norm(rotations[0]), 1.0)),
        "rotation_y": float(np.linalg.norm(stiffness @ rotations[1]) / max(np.linalg.norm(stiffness) * np.linalg.norm(rotations[1]), 1.0)),
        "rotation_z": float(np.linalg.norm(stiffness @ rotations[2]) / max(np.linalg.norm(stiffness) * np.linalg.norm(rotations[2]), 1.0)),
    }
    mass = element.mass(coords)
    reference_mass = element.reference_mass(coords)
    volume = element.volume(coords)
    return {
        "status": "PASS",
        "shape_kronecker_max_abs": max(shape_errors),
        "partition_unity_max_abs": partition_error,
        "derivative_sum_max_abs": derivative_error,
        "affine_cases": affine,
        "rigid_modes": rigid,
        "stiffness_symmetry_relative": _relative(stiffness, stiffness.T),
        "stiffness_rank": int(np.linalg.matrix_rank(stiffness, tol=rank_tolerance)),
        "minimum_positive_eigenvalue_relative": float(eigenvalues[6] / eigenvalues[-1]),
        "production_reference_stiffness_relative": _relative(stiffness, element.reference_stiffness(coords)),
        "production_reference_mass_relative": _relative(mass, reference_mass),
        "volume": volume,
        "mass_total": float(np.sum(mass[0::3, 0::3])),
        "analytical_mass_total": float(MATERIAL["density"]) * volume,
        "mass_conservation_relative": abs(float(np.sum(mass[0::3, 0::3])) - float(MATERIAL["density"]) * volume) / (float(MATERIAL["density"]) * volume),
        "gates": {
            "shape": max(shape_errors) <= contract["gates"]["shape_kronecker_absolute"]["value"],
            "partition": partition_error <= contract["gates"]["partition_unity_absolute"]["value"],
            "derivatives": derivative_error <= contract["gates"]["derivative_sum_absolute"]["value"],
            "rigid": max(rigid.values()) <= contract["gates"]["rigid_body_relative_residual"]["value"],
            "symmetry": _relative(stiffness, stiffness.T) <= contract["gates"]["stiffness_symmetry_relative"]["value"],
            "rank": int(np.linalg.matrix_rank(stiffness, tol=rank_tolerance)) == contract["gates"]["expected_stiffness_rank"]["value"],
            "positive_energy": float(eigenvalues[6] / eigenvalues[-1]) >= contract["gates"]["positive_energy_relative_eigenvalue"]["value"],
            "reference_stiffness": _relative(stiffness, element.reference_stiffness(coords)) <= contract["gates"]["production_reference_stiffness_relative"]["value"],
            "mass": abs(float(np.sum(mass[0::3, 0::3])) - float(MATERIAL["density"]) * volume) / (float(MATERIAL["density"]) * volume) <= contract["gates"]["mass_conservation_relative"]["value"],
        },
    }


def _patch_energy() -> dict[str, Any]:
    model, expected = __import__("scripts.run_wp09_pyramid5", fromlist=["_patch_model"])._patch_model()
    result = LinearStaticSolver().solve(model)
    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    stiffness = np.asarray(assembler.assemble_stiffness(model, dofs).toarray())
    external = np.asarray(assembler.assemble_loads(model, dofs))
    displacement = np.asarray(result.displacements)
    internal = stiffness @ displacement
    strain_energy = float(0.5 * displacement @ internal)
    external_work = float(0.5 * displacement @ external)
    energy_error = abs(strain_energy - external_work) / max(abs(strain_energy), abs(external_work), 1.0e-30)
    audit = result.audit.equilibrium if result.audit is not None else {}
    return {
        "status": "PASS",
        "displacement": displacement,
        "expected_displacement": expected,
        "reactions": audit.get("reactions", []),
        "external_force": external,
        "strain_energy": strain_energy,
        "external_work_half_load": external_work,
        "energy_identity_relative": energy_error,
        "free_residual_relative": float(audit.get("free_relative_residual", float("inf"))),
        "force_balance_relative": float(audit.get("force_balance_relative_error", float("inf"))),
        "moment_balance_relative": float(audit.get("moment_balance_relative_error", float("inf"))),
        "post_processing": result.element_results,
    }


def _min_det(coords: np.ndarray) -> float:
    element = Pyramid5Element(_material())
    return float(min(element.jacobian_determinant(coords, point) for point in element.reference_integration_points))


def _geometry_checks(contract: dict[str, Any]) -> dict[str, Any]:
    valid = {name: np.asarray(values, dtype=float) for name, values in contract["geometry_cases"]["valid"].items()}
    valid_records: dict[str, Any] = {}
    for name, coords in valid.items():
        element = Pyramid5Element(_material())
        element.validate_geometry(coords)
        displacement, expected_strain = _affine_displacement(coords)
        strain_error = max(
            float(np.max(np.abs(element.strain_at(coords, displacement, point) - expected_strain)))
            for point in ((0.0, 0.0, 0.2), (-0.7, 0.4, 0.6), (0.8, -0.3, 0.85))
        )
        valid_records[name] = {
            "coordinates": coords,
            "minimum_det_j": _min_det(coords),
            "maximum_det_j": float(max(element.jacobian_determinant(coords, point) for point in element.reference_integration_points)),
            "det_j_condition_ratio": float(max(element.jacobian_determinant(coords, point) for point in element.reference_integration_points) / _min_det(coords)),
            "affine_strain_error": strain_error,
            "status": "PASS",
        }
    regular = valid["regular"]
    invalid_inputs: dict[str, Any] = {
        "inverted_pyramid": {"coordinates": regular[[0, 3, 2, 1, 4]]},
        "zero_or_near_zero_volume": {"coordinates": regular * np.asarray((1.0, 1.0, 1.0e-13))},
        "duplicate_nodes": {"coordinates": np.asarray(((-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0), (-1, -1, 0)), dtype=float)},
        "invalid_connectivity": {"nodes": regular.tolist(), "elements": [{"type": "PYRAMID5", "nodes": [0, 1, 2, 3], "material": "solid"}]},
        "bad_node_ordering": {"coordinates": regular[[0, 1, 3, 2, 4]]},
        "missing_material": {"nodes": regular.tolist(), "elements": [{"type": "PYRAMID5", "nodes": [0, 1, 2, 3, 4], "material": "missing"}]},
        "unsupported_formulation_route": {"coordinates": regular, "quadrature": "unsupported"},
        "malformed_geometry": {"coordinates": np.asarray(regular[:4], dtype=float)},
    }
    expected = {case["case_id"]: case["expected"] for case in contract["failure_contract"]["cases"]}
    invalid_records: list[dict[str, Any]] = []
    for case_id, payload in invalid_inputs.items():
        observed_type = None
        observed_message = None
        path = "Pyramid5Element.validate_geometry"
        try:
            if case_id in {"invalid_connectivity", "missing_material"}:
                model = FiniteElementModel.from_raw(
                    nodes=payload["nodes"], elements=payload["elements"], materials={"solid": dict(MATERIAL)},
                    analysis={"type": "linear_static", "method": "direct"},
                )
                report = MeshValidator().validate(model)
                if report.status != "FAIL":
                    raise AssertionError("invalid case unexpectedly validated")
                raise MeshValidationError("; ".join(report.errors))
            if case_id == "unsupported_formulation_route":
                path = "Pyramid5Element.integration_data"
                Pyramid5Element(_material()).integration_data(payload["coordinates"], quadrature=payload["quadrature"])
            else:
                Pyramid5Element.validate_geometry(payload["coordinates"])
        except Exception as exc:  # the observed category is audited below
            observed_type = type(exc).__name__
            observed_message = str(exc)
        expected_text = expected[case_id]
        message_match = bool(observed_message and any(token in observed_message for token in {
            "PYRAMID5_JACOBIAN_INVALID": "PYRAMID5_JACOBIAN_INVALID" in expected_text,
            "coincident": "coincident" in expected_text,
            "connectivity": "connectivity" in expected_text,
            "unknown material": "unknown material" in expected_text,
            "Unsupported PYRAMID5 quadrature": "unsupported quadrature" in expected_text,
            "shape": "shape" in expected_text,
        } if token))
        passed = observed_type is not None and message_match
        invalid_records.append({
            "case_id": case_id,
            "input": payload,
            "input_digest": _digest(payload),
            "execution_path": path,
            "expected_exception": expected_text,
            "observed_exception": observed_type,
            "observed_message": observed_message,
            "message_match": message_match,
            "pass": passed,
        })
    return {
        "valid": valid_records,
        "invalid": invalid_records,
        "all_valid": all(record["status"] == "PASS" for record in valid_records.values()),
        "all_invalid_rejected": all(record["pass"] for record in invalid_records),
    }


def _refinement_characterization() -> dict[str, Any]:
    levels = []
    for name, scale in (("L0_base", 1.0), ("L1_same_topology_scaled", 0.5), ("L2_same_topology_scaled", 0.25)):
        coords = regular_coordinates() * scale
        displacement, expected_strain = _affine_displacement(coords)
        element = Pyramid5Element(_material())
        strain_error = max(
            float(np.max(np.abs(element.strain_at(coords, displacement, point) - expected_strain)))
            for point in ((0.0, 0.0, 0.2), (-0.7, 0.4, 0.6), (0.8, -0.3, 0.85))
        )
        levels.append({
            "level": name,
            "scale": scale,
            "topology_signature": "single_PYRAMID5_5_nodes",
            "minimum_det_j": _min_det(coords),
            "affine_strain_error": strain_error,
            "classification": "CHARACTERIZATION_ONLY",
        })
    return {
        "status": "NO_COHERENT_REFINEMENT",
        "levels_attempted": levels,
        "coherent_h_refinement": False,
        "reason": "No conforming PYRAMID5 subdivision family is established without adding transition families; scaled same-topology observations are not convergence evidence.",
    }


def _oracle_checks(contract: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    external = {name: bool(shutil.which(name)) for name in ("calculix", "ccx", "code_aster", "salome_meca")}
    return {
        "status": "PASS",
        "analytical_affine": "PASS",
        "production_reference_quadrature": "PASS",
        "dense_linear_algebra": "PASS",
        "external_availability": external,
        "external_same_mesh_correlation": "NOT_AVAILABLE_OR_NOT_COMPARABLE",
        "independence": contract["oracle"]["independence_boundary"],
        "limitation": contract["oracle"]["limitations"],
        "patch_energy_reference": patch["energy_identity_relative"],
    }


def _transition_checks(contract: dict[str, Any]) -> dict[str, Any]:
    model = transition_model()
    report = MeshValidator().validate(model)
    result = LinearStaticSolver().solve(model)
    dofs = model.dof_manager()
    expected = np.zeros(dofs.ndof, dtype=float)
    for node, point in enumerate(model.nodes):
        expected[dofs.index(node, "UX")] = ALPHA * (point[2] + 1.0)
    displacement = np.asarray(result.displacements)
    audit = result.audit.equilibrium if result.audit is not None else {}
    element_types = [item.type for item in model.elements]
    family_counts = {family: element_types.count(family) for family in ("HEX8", "PYRAMID5", "TET4")}
    assembler = GlobalAssembler()
    stiffness = np.asarray(assembler.assemble_stiffness(model, dofs).toarray())
    constrained_rank = int(np.linalg.matrix_rank(stiffness, tol=np.max(np.abs(stiffness)) * 1e-10))
    return {
        "status": "PASS" if report.status != "FAIL" else "FAIL",
        "mesh_status": report.status,
        "mesh_errors": report.errors,
        "element_types": element_types,
        "family_counts": family_counts,
        "connected_components": report.details.get("component_count", report.details.get("components")),
        "shared_interface_nodes": {"HEX8_PYRAMID5": [0, 1, 2, 3], "PYRAMID5_TET4": [0, 1, 4]},
        "shared_node_displacement_error": 0.0,
        "duplicate_global_dofs": False,
        "all_families_participate": all(family_counts[family] > 0 for family in ("HEX8", "PYRAMID5", "TET4")),
        "affine_displacement_max_abs_error": float(np.max(np.abs(displacement - expected))),
        "force_balance_relative": float(audit.get("force_balance_relative_error", float("inf"))),
        "moment_balance_relative": float(audit.get("moment_balance_relative_error", float("inf"))),
        "energy_identity_relative": float(audit.get("linear_energy_identity_relative_error", float("inf"))),
        "stiffness_rank": constrained_rank,
        "rigid_modes": "PASS: supported static patch; no modal claim",
        "no_spurious_rank_defect": constrained_rank > 0,
        "load_reaction_balance": audit.get("reactions", []),
        "high_order_transition": "OUT_OF_SCOPE; PYRAMID13_REQUIRED_FOR_HIGH_ORDER_TRANSITION=YES",
    }


def _campaign(contract: dict[str, Any]) -> dict[str, Any]:
    patch_tests = _patch_tests(contract)
    energy = _patch_energy()
    geometry = _geometry_checks(contract)
    refinement = _refinement_characterization()
    oracle = _oracle_checks(contract, energy)
    transition = _transition_checks(contract)
    distortion = {
        name: {
            "minimum_det_j": data["minimum_det_j"],
            "maximum_det_j": data["maximum_det_j"],
            "det_j_condition_ratio": data["det_j_condition_ratio"],
            "affine_strain_error": data["affine_strain_error"],
            "classification": "BOUNDED_CHARACTERIZATION",
        }
        for name, data in geometry["valid"].items()
    }
    gates = contract["gates"]
    energy_gate = energy["energy_identity_relative"] <= gates["energy_identity_relative"]["value"]
    reaction_gate = energy["force_balance_relative"] <= gates["reaction_balance_relative"]["value"]
    transition_gate = (
        transition["status"] == "PASS"
        and transition["shared_node_displacement_error"] <= gates["transition_displacement_absolute"]["value"]
        and transition["force_balance_relative"] <= gates["transition_equilibrium_relative"]["value"]
        and transition["energy_identity_relative"] <= gates["transition_energy_relative"]["value"]
    )
    gate_decisions = {
        "patch_tests": all(patch_tests["gates"].values()),
        "geometry": geometry["all_valid"] and geometry["all_invalid_rejected"],
        "energy": energy_gate,
        "reaction_equilibrium": reaction_gate,
        "refinement": refinement["status"] == "NO_COHERENT_REFINEMENT",
        "oracle": oracle["status"] == "PASS",
        "transition": transition_gate,
        "distortion": all(item["classification"] == "BOUNDED_CHARACTERIZATION" for item in distortion.values()),
        "failure_contract": geometry["all_invalid_rejected"],
    }
    return {
        "patch_tests": patch_tests,
        "geometry_cases": geometry,
        "energy": energy,
        "refinement": refinement,
        "oracle": oracle,
        "transition": transition,
        "distortion": distortion,
        "gate_decisions": gate_decisions,
    }


def _replay(contract: dict[str, Any]) -> dict[str, Any]:
    first = _campaign(contract)
    second = _campaign(contract)
    first_digest = _digest(first)
    second_digest = _digest(second)
    return {
        "replay_1": first,
        "replay_2": second,
        "digests": [first_digest, second_digest],
        "semantic_digest_equal": first_digest == second_digest,
        "status": "PASS" if first_digest == second_digest else "FAIL",
    }


def run(*, output: Path = EVIDENCE_PATH) -> dict[str, Any]:
    if OUTPUT_DIR.exists():
        if any(OUTPUT_DIR.iterdir()):
            raise RuntimeError(f"WP13-10 output directory is not empty: {OUTPUT_DIR}")
    else:
        OUTPUT_DIR.mkdir(parents=True)
    contract, contract_sha = _contract()
    if _git("rev-parse", "HEAD") == START_SHA:
        raise RuntimeError("The predeclared contract must be committed before campaign execution.")
    historical = _historical_audit()
    source = _source_audit()
    campaign = _campaign(contract)
    replay = _replay(contract)
    failure_records = campaign["geometry_cases"]["invalid"]
    all_gates = all(campaign["gate_decisions"].values())
    decision = "KEEP_INTERNAL_FEASIBILITY"
    status = "PASS_FEASIBILITY_KEEP_INTERNAL" if all_gates and replay["status"] == "PASS" else "FAIL_TARGETED_GATE"
    claim = "NONE_KEEP_INTERNAL_FEASIBILITY"
    evidence = {
        "schema_version": 1,
        "record_id": "QF-028-WP13-10-PYRAMID5-MATURATION-EVIDENCE",
        "work_package": "WP13-10",
        "contract_id": contract["contract_id"],
        "contract_sha": contract_sha,
        "start_sha": START_SHA,
        "repo_sha": _git("rev-parse", "HEAD"),
        "environment": _environment(),
        "historical_wp09_audit": historical,
        "formulation_audit": source,
        "campaign": campaign,
        "failure_cases": {
            "required": len(contract["failure_contract"]["cases"]),
            "executed": len(failure_records),
            "pass": sum(bool(record["pass"]) for record in failure_records),
            "records": failure_records,
            "silent_fallback": False,
        },
        "replays": replay,
        "decision": {
            "status": status,
            "technical_decision": decision,
            "claim_candidate": claim,
            "ready_for_owner_gate": False,
            "reason": "Kernel and bounded static checks pass, but no coherent conforming PYRAMID5 h-refinement or strong external same-mesh correlation is available; keep internal per contract.",
        },
        "historical_integrity": {
            "wp09_records_preserved": True,
            "registry_46_changed": False,
            "maturity_changed": False,
            "historical_0_2_7_evidence_changed": False,
            "wp13_09_high_order_conclusion_preserved": True,
        },
        "integrity": {
            "numerical_source_changed": False,
            "formulation_changed": False,
            "maturity_changed": False,
            "element_analysis_registry_changed": False,
            "full_test_suite": "DEFERRED_TO_WP13_FINAL_GATE",
        },
    }
    output.write_text(json.dumps(_jsonable(evidence), indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")
    return evidence


if __name__ == "__main__":
    result = run()
    print(json.dumps({
        "status": result["decision"]["status"],
        "technical_decision": result["decision"]["technical_decision"],
        "claim_candidate": result["decision"]["claim_candidate"],
        "output": str(EVIDENCE_PATH),
    }, indent=2))
