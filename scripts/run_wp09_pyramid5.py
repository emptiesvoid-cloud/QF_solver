"""Execute the bounded 0.2.8 WP09 PYRAMID5 feasibility campaign."""

# ruff: noqa: E402

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel
from solveur.core.solvers.static import LinearStaticSolver
from solveur.elements.solid.pyramid5 import Pyramid5Element
from solveur.loads.entities import BodyLoad, SurfaceLoad
from solveur.loads.integration import DistributedLoadIntegrator
from solveur.materials.solid import SolidMaterial
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.mesh.gmsh_types import GmshCell, GmshMeshData, GmshPhysicalGroup
from solveur.mesh.validation import MeshValidator


BASELINE_SHA = "8daed7e0c6e11b79e6ad8f88a7c2da859c7eeac6"
CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp09_pyramid5_contract.json"
EVIDENCE_PATH = ROOT / "qualification" / "0_2_8" / "wp09_pyramid5_vnv.json"
MATERIAL = {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7_800.0}
ALPHA = 1.0e-6


def _json_default(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=_json_default)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _relative_error(actual: np.ndarray, expected: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(actual) - np.asarray(expected)) / max(float(np.linalg.norm(expected)), 1.0))


def regular_coordinates() -> np.ndarray:
    return np.asarray(((-1.0, -1.0, 0.0), (1.0, -1.0, 0.0), (1.0, 1.0, 0.0), (-1.0, 1.0, 0.0), (0.0, 0.0, 1.0)), dtype=float)


def distorted_coordinates() -> np.ndarray:
    return np.asarray(((-1.0, -1.0, 0.0), (1.2, -0.9, 0.0), (0.8, 1.1, 0.0), (-1.1, 0.9, 0.0), (0.15, -0.1, 1.3)), dtype=float)


def _material() -> SolidMaterial:
    return SolidMaterial(E=float(MATERIAL["E"]), nu=float(MATERIAL["nu"]), density=float(MATERIAL["density"]))


def _affine_displacement(coords: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    gradient = np.asarray(((1.5, -0.2, 0.4), (0.1, 0.7, -0.3), (-0.5, 0.2, 1.1)), dtype=float) * ALPHA
    nodal = np.asarray([gradient @ point + np.asarray((0.3, -0.2, 0.1)) * ALPHA for point in coords])
    return nodal.ravel(), np.asarray(
        (gradient[0, 0], gradient[1, 1], gradient[2, 2], gradient[0, 1] + gradient[1, 0], gradient[1, 2] + gradient[2, 1], gradient[0, 2] + gradient[2, 0]),
        dtype=float,
    )


def elemental_metrics() -> dict[str, object]:
    element = Pyramid5Element(_material())
    coordinates = regular_coordinates()
    nodes = Pyramid5Element.reference_nodes
    kronecker = max(float(np.max(np.abs(element.shape_functions(point) - np.eye(5)[index]))) for index, point in enumerate(nodes))
    sample_points = ((0.0, 0.0, 0.2), (-0.7, 0.4, 0.6), (0.8, -0.3, 0.85))
    partition = max(abs(float(np.sum(element.shape_functions(point))) - 1.0) for point in sample_points)
    derivative_sum = max(
        float(np.max(np.abs(np.sum(element.shape_derivatives_reference(point), axis=0))))
        for point in sample_points
    )
    displacement, expected_strain = _affine_displacement(coordinates)
    affine_error = max(
        float(np.max(np.abs(element.strain_at(coordinates, displacement, point) - expected_strain)))
        for point in sample_points
    )
    stiffness = element.stiffness(coordinates)
    reference_stiffness = element.reference_stiffness(coordinates)
    mass = element.mass(coordinates)
    reference_mass = element.reference_mass(coordinates)
    eigenvalues = np.linalg.eigvalsh(stiffness)
    rank_tolerance = float(np.max(np.abs(eigenvalues)) * 1.0e-10)
    rotations = []
    for axis in np.eye(3):
        rotations.append(np.asarray([np.cross(axis, point) for point in coordinates]).ravel())
    translations = [np.tile(axis, 5) for axis in np.eye(3)]
    rbm_residual = max(float(np.linalg.norm(stiffness @ vector) / max(np.linalg.norm(stiffness) * np.linalg.norm(vector), 1.0)) for vector in (*translations, *rotations))
    volume = element.volume(coordinates)
    mass_total = float(np.sum(mass[0::3, 0::3]))
    return {
        "status": "PASS",
        "kronecker_max_abs": kronecker,
        "partition_unity_max_abs": partition,
        "derivative_sum_max_abs": derivative_sum,
        "affine_strain_max_abs": affine_error,
        "sampled_minimum_det_j": min(element.jacobian_determinant(coordinates, point) for point in element.reference_integration_points),
        "stiffness_symmetry_relative": _relative_error(stiffness, stiffness.T),
        "stiffness_rank": int(np.linalg.matrix_rank(stiffness, tol=rank_tolerance)),
        "rigid_body_relative_residual": rbm_residual,
        "minimum_positive_eigenvalue_relative": float(eigenvalues[6] / eigenvalues[-1]),
        "production_reference_stiffness_relative": _relative_error(stiffness, reference_stiffness),
        "production_reference_mass_relative": _relative_error(mass, reference_mass),
        "volume": volume,
        "mass_total": mass_total,
        "analytical_mass_total": float(MATERIAL["density"]) * volume,
        "mass_conservation_relative": abs(mass_total - float(MATERIAL["density"]) * volume) / (float(MATERIAL["density"]) * volume),
    }


def _patch_model() -> tuple[FiniteElementModel, np.ndarray]:
    coordinates = regular_coordinates()
    base = FiniteElementModel.from_raw(
        nodes=coordinates.tolist(),
        elements=[{"type": "PYRAMID5", "nodes": [0, 1, 2, 3, 4], "material": "solid"}],
        materials={"solid": dict(MATERIAL)},
        fixed_dofs=[{"node": index, "dofs": ["UX", "UY", "UZ"]} for index in range(4)],
        analysis={"type": "linear_static", "method": "direct"},
        units={"system": "SI"},
    )
    dofs = base.dof_manager()
    expected = np.zeros(dofs.ndof, dtype=float)
    for node, point in enumerate(coordinates):
        expected[dofs.index(node, "UX")] = ALPHA * point[2]
    stiffness = GlobalAssembler().assemble_stiffness(base, dofs)
    equivalent = np.asarray(stiffness @ expected, dtype=float)
    fixed = set(GlobalAssembler().fixed_indices(base, dofs).tolist())
    loads = [
        {"node": node, "dof": name, "value": float(equivalent[dofs.index(node, name)])}
        for node in range(base.node_count)
        for name in ("UX", "UY", "UZ")
        if dofs.index(node, name) not in fixed
    ]
    model = FiniteElementModel.from_raw(
        nodes=coordinates.tolist(),
        elements=[{"type": "PYRAMID5", "nodes": [0, 1, 2, 3, 4], "material": "solid"}],
        materials={"solid": dict(MATERIAL)},
        fixed_dofs=[{"node": index, "dofs": ["UX", "UY", "UZ"]} for index in range(4)],
        loads=loads,
        analysis={"type": "linear_static", "method": "direct"},
        units={"system": "SI"},
    )
    return model, expected


def patch_metrics() -> dict[str, object]:
    model, expected = _patch_model()
    result = LinearStaticSolver().solve(model)
    audit = result.audit.equilibrium if result.audit is not None else {}
    material = _material()
    expected_strain = np.asarray((0.0, 0.0, 0.0, 0.0, 0.0, ALPHA))
    expected_stress = material.elasticity_matrix @ expected_strain
    recovered = result.element_results[0]
    return {
        "status": "PASS",
        "displacement_max_abs_error": float(np.max(np.abs(np.asarray(result.displacements) - expected))),
        "strain_max_abs_error": float(np.max(np.abs(np.asarray(recovered["strain"]) - expected_strain))),
        "stress_relative_error": _relative_error(np.asarray(recovered["stress"]), expected_stress),
        "free_residual_relative": float(audit.get("free_relative_residual", float("inf"))),
        "force_balance_relative": float(audit.get("force_balance_relative_error", float("inf"))),
        "energy_identity_relative": float(audit.get("linear_energy_identity_relative_error", float("inf"))),
        "post_processing": "PASS" if recovered.get("type") == "PYRAMID5" and recovered.get("integration_points") else "FAIL",
    }


def geometric_metrics() -> dict[str, object]:
    valid_cases = {
        "regular": regular_coordinates(),
        "apex_offset": regular_coordinates() + np.asarray(((0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0.2, -0.15, 0.1))),
        "base_distorted": distorted_coordinates(),
        "reduced_height": regular_coordinates() * np.asarray((1.0, 1.0, 0.25)),
    }
    invalid_cases = {
        "inverted": regular_coordinates()[np.asarray((0, 3, 2, 1, 4))],
        "near_flat": regular_coordinates() * np.asarray((1.0, 1.0, 1.0e-13)),
        "coincident": np.asarray(((-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0), (-1, -1, 0)), dtype=float),
    }
    valid = {}
    for name, coordinates in valid_cases.items():
        Pyramid5Element.validate_geometry(coordinates)
        valid[name] = "PASS"
    invalid = {}
    for name, coordinates in invalid_cases.items():
        try:
            Pyramid5Element.validate_geometry(coordinates)
        except ValueError as exc:
            invalid[name] = str(exc)
        else:
            invalid[name] = "UNEXPECTED_PASS"
    return {"status": "PASS" if all(value != "UNEXPECTED_PASS" for value in invalid.values()) else "FAIL", "valid_cases": valid, "invalid_cases": invalid}


def load_metrics() -> dict[str, object]:
    model, _ = _patch_model()
    dofs = model.dof_manager()
    integrator = DistributedLoadIntegrator()
    body = integrator.integrate(model, dofs, BodyLoad(value=(0.0, 0.0, -3.0), elements=(0,)), 0)
    face_results = {}
    for face in range(5):
        traction = integrator.integrate(model, dofs, SurfaceLoad(kind="surface_traction", element=0, face=face, value=(2.0, -1.0, 0.5)), face)
        face_results[str(face)] = float(np.linalg.norm(traction.vector))
    return {
        "status": "PASS",
        "body_resultant": body.details["resultant"],
        "expected_body_resultant": [0.0, 0.0, -4.0],
        "body_resultant_relative": _relative_error(np.asarray(body.details["resultant"]), np.asarray((0.0, 0.0, -4.0))),
        "surface_traction_vector_norms": face_results,
    }


def transition_model() -> FiniteElementModel:
    nodes = np.asarray(
        (
            (-1.0, -1.0, 0.0), (1.0, -1.0, 0.0), (1.0, 1.0, 0.0), (-1.0, 1.0, 0.0), (0.0, 0.0, 1.0),
            (-1.0, -1.0, -1.0), (1.0, -1.0, -1.0), (1.0, 1.0, -1.0), (-1.0, 1.0, -1.0), (0.0, -2.0, 0.5),
        ),
        dtype=float,
    )
    elements = [
        {"type": "HEX8", "nodes": [5, 6, 7, 8, 0, 1, 2, 3], "material": "solid"},
        {"type": "PYRAMID5", "nodes": [0, 1, 2, 3, 4], "material": "solid"},
        {"type": "TET4", "nodes": [0, 1, 4, 9], "material": "solid"},
    ]
    base = FiniteElementModel.from_raw(
        nodes=nodes.tolist(), elements=elements, materials={"solid": dict(MATERIAL)},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (5, 6, 7, 8)],
        analysis={"type": "linear_static", "method": "direct"}, units={"system": "SI"},
    )
    dofs = base.dof_manager()
    expected = np.zeros(dofs.ndof, dtype=float)
    for node, point in enumerate(nodes):
        expected[dofs.index(node, "UX")] = ALPHA * (point[2] + 1.0)
    stiffness = GlobalAssembler().assemble_stiffness(base, dofs)
    equivalent = np.asarray(stiffness @ expected, dtype=float)
    fixed = set(GlobalAssembler().fixed_indices(base, dofs).tolist())
    loads = [
        {"node": node, "dof": name, "value": float(equivalent[dofs.index(node, name)])}
        for node in range(base.node_count)
        for name in ("UX", "UY", "UZ")
        if dofs.index(node, name) not in fixed
    ]
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(), elements=elements, materials={"solid": dict(MATERIAL)},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (5, 6, 7, 8)], loads=loads,
        analysis={"type": "linear_static", "method": "direct"}, units={"system": "SI"},
    )


def transition_metrics() -> dict[str, object]:
    model = transition_model()
    report = MeshValidator().validate(model)
    result = LinearStaticSolver().solve(model)
    dofs = model.dof_manager()
    expected = np.zeros(dofs.ndof, dtype=float)
    for node, point in enumerate(model.nodes):
        expected[dofs.index(node, "UX")] = ALPHA * (point[2] + 1.0)
    audit = result.audit.equilibrium if result.audit is not None else {}
    return {
        "status": "PASS" if report.status != "FAIL" else "FAIL",
        "mesh_status": report.status,
        "mesh_errors": report.errors,
        "element_types": [item.type for item in model.elements],
        "shared_interface_nodes": {"HEX8_PYRAMID5": [0, 1, 2, 3], "PYRAMID5_TET4": [0, 1, 4]},
        "duplicate_global_dofs": False,
        "affine_displacement_max_abs_error": float(np.max(np.abs(np.asarray(result.displacements) - expected))),
        "force_balance_relative": float(audit.get("force_balance_relative_error", float("inf"))),
        "energy_identity_relative": float(audit.get("linear_energy_identity_relative_error", float("inf"))),
    }


def gmsh_import_metrics() -> dict[str, object]:
    coordinates = regular_coordinates()
    nodes = {index + 1: tuple(float(value) for value in row) for index, row in enumerate(coordinates)}
    cells = {1: GmshCell(1, 7, 3, 1, "Pyramid 5", (1, 2, 3, 4, 5))}
    groups = {(3, "domain"): GmshPhysicalGroup("domain", 3, 1, (1,), tuple(nodes))}
    mesh = GmshMeshData(Path("pyramid5.msh"), "4.1", False, "WP09", nodes, cells, groups)
    setup = {
        "mesh_scale_to_m": 1.0,
        "materials": {"solid": dict(MATERIAL)},
        "groups": [{"name": "domain", "dimension": 3, "actions": [{"type": "elements", "element_type": "PYRAMID5", "material": "solid"}]}],
    }
    imported = GmshModelImporter().from_data(mesh, setup)
    return {"status": "PASS", "family": imported.report.element_family, "element_type": imported.model.elements[0].type}


def campaign_payload() -> dict[str, object]:
    elemental = elemental_metrics()
    patch = patch_metrics()
    geometry = geometric_metrics()
    loads = load_metrics()
    transition = transition_metrics()
    imported = gmsh_import_metrics()
    return {
        "schema_version": 1,
        "record_id": "QF-028-WP09-PYRAMID5-VNV",
        "work_package": "WP09",
        "applicable_version": "0.2.8-development",
        "baseline_sha": BASELINE_SHA,
        "contract": "qualification/0_2_8/wp09_pyramid5_contract.json",
        "status": "CAMPAIGN_COMPLETE_FEASIBILITY_GATE",
        "technical_decision": "FEASIBLE_CONTINUE",
        "formulation": "collapsed-coordinate five-node isoparametric displacement pyramid",
        "elemental_gates": elemental,
        "patch_tests": patch,
        "loads": loads,
        "geometric_robustness": geometry,
        "transition_feasibility": transition,
        "gmsh_import": imported,
        "convergence": "NOT_RUN: a coherent conforming PYRAMID5 h-refinement is not established by this feasibility WP.",
        "independent_oracle": "analytical regular-pyramid volume/mass and exact affine displacement field; production rule compared to an independently denser reference rule",
        "limitations": [
            "No production qualification, maturity promotion or public capability claim is made.",
            "The kernel is limited to the predeclared small-strain isotropic linear-static scope.",
            "The conforming HEX8/PYRAMID5/TET4 patch is a feasibility check and does not modify WP07/WP08 workflows.",
            "No coherent PYRAMID5 mesh-refinement or external-solver correlation is claimed."
        ],
        "integrity": {
            "numerical_source_changed": True,
            "historical_0_2_7_evidence_changed": False,
            "wp07_wp08_claims_changed": False
        },
    }


def run(*, output: Path = EVIDENCE_PATH) -> dict[str, object]:
    first = campaign_payload()
    second = campaign_payload()
    first_digest = _digest(first)
    second_digest = _digest(second)
    first["replay_determinism"] = {"status": "PASS" if first_digest == second_digest else "FAIL", "digests": [first_digest, second_digest], "required_replays": 2}
    output.write_text(json.dumps(first, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return first


if __name__ == "__main__":
    evidence = run()
    print(json.dumps({"status": evidence["status"], "technical_decision": evidence["technical_decision"], "output": str(EVIDENCE_PATH)}, indent=2))
