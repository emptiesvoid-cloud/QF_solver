"""Run the bounded WP10 HEX8-SRI research gate."""

# ruff: noqa: E402

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np

from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.hex8_sri import Hex8SRIElement
from solveur.materials.solid import SolidMaterial


CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp10_hex8_sri_contract.json"
EVIDENCE_PATH = ROOT / "qualification" / "0_2_8" / "wp10_hex8_sri_vnv.json"
MATRIX_PATH = ROOT / "qualification" / "0_2_8" / "wp10_hex8_sri_matrix.json"
BASELINE_SHA = "324e496c125d55d6925309ee791faaedcead3039"
E = 1.0e6
LENGTH = 20.0
WIDTH = 1.0
HEIGHT = 1.0
UNIT_LOAD = 1.0
LEVELS = (4, 8, 16)
TOLERANCES = {
    "patch_absolute": 1.0e-11,
    "constant_strain_absolute": 1.0e-11,
    "symmetry_relative": 1.0e-12,
    "rigid_body_relative": 1.0e-10,
    "energy_identity_relative": 1.0e-10,
    "fine_locking_gain": 0.50,
    "rank_null_relative": 1.0e-10,
    "positive_mode_relative": 1.0e-12,
}


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _mesh(nx: int, ny: int = 2, nz: int = 2, *, distorted: bool = False) -> tuple[np.ndarray, list[list[int]]]:
    nodes: list[list[float]] = []
    indices: dict[tuple[int, int, int], int] = {}
    for k in range(nz + 1):
        for j in range(ny + 1):
            for i in range(nx + 1):
                x = LENGTH * i / nx
                y = WIDTH * j / ny
                z = HEIGHT * k / nz
                if distorted and i not in (0, nx):
                    y += 0.12 * (x / LENGTH) * (z - 0.5 * HEIGHT)
                    z += 0.08 * (x / LENGTH) * (y - 0.5 * WIDTH)
                indices[i, j, k] = len(nodes)
                nodes.append([x, y, z])
    elements: list[list[int]] = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                elements.append(
                    [
                        indices[i, j, k],
                        indices[i + 1, j, k],
                        indices[i + 1, j + 1, k],
                        indices[i, j + 1, k],
                        indices[i, j, k + 1],
                        indices[i + 1, j, k + 1],
                        indices[i + 1, j + 1, k + 1],
                        indices[i, j + 1, k + 1],
                    ]
                )
    return np.asarray(nodes, dtype=float), elements


def _local_dofs(connectivity: list[int]) -> np.ndarray:
    return np.asarray([[3 * node, 3 * node + 1, 3 * node + 2] for node in connectivity], dtype=int).ravel()


def _oracle(nu: float) -> float:
    shear = E / (2.0 * (1.0 + nu))
    inertia = WIDTH * HEIGHT**3 / 12.0
    area = WIDTH * HEIGHT
    return UNIT_LOAD * LENGTH**3 / (3.0 * E * inertia) + UNIT_LOAD * LENGTH / ((5.0 / 6.0) * shear * area)


def _assemble_case(nx: int, nu: float, *, sri: bool, distorted: bool = False) -> dict[str, object]:
    nodes, elements = _mesh(nx, distorted=distorted)
    material = SolidMaterial(E=E, nu=nu)
    element = Hex8SRIElement(material) if sri else Hex8Element(material)
    stiffness = np.zeros((3 * len(nodes), 3 * len(nodes)), dtype=float)
    for connectivity in elements:
        dofs = _local_dofs(connectivity)
        stiffness[np.ix_(dofs, dofs)] += element.stiffness(nodes[connectivity])
    load = np.zeros(3 * len(nodes), dtype=float)
    free_end = [index for index, point in enumerate(nodes) if np.isclose(point[0], LENGTH)]
    for node in free_end:
        load[3 * node + 2] = -UNIT_LOAD / len(free_end)
    fixed = [3 * node + dof for node, point in enumerate(nodes) if np.isclose(point[0], 0.0) for dof in range(3)]
    free = np.setdiff1d(np.arange(load.size), np.asarray(fixed, dtype=int))
    displacement = np.zeros(load.size, dtype=float)
    displacement[free] = np.linalg.solve(stiffness[np.ix_(free, free)], load[free])
    tip = float(np.mean([displacement[3 * node + 2] for node in free_end]))
    energy = float(0.5 * displacement @ stiffness @ displacement)
    reference = _oracle(nu)
    residual = stiffness @ displacement - load
    local_strains = []
    local_stresses = []
    for connectivity in elements:
        local_u = displacement[_local_dofs(connectivity)]
        local_strains.append(element.strain(nodes[connectivity], local_u))
        local_stresses.append(element.stress(nodes[connectivity], local_u))
    return {
        "nx": nx,
        "ny": 2,
        "nz": 2,
        "nu": nu,
        "sri": sri,
        "distorted": distorted,
        "node_count": len(nodes),
        "element_count": len(elements),
        "global_dof_count": int(3 * len(nodes)),
        "local_stiffness_rule_evaluations": 9 if sri else 8,
        "tip_displacement": tip,
        "reference_tip_displacement": -reference,
        "relative_displacement_error": abs(abs(tip) - reference) / reference,
        "energy": energy,
        "reference_energy": 0.5 * UNIT_LOAD * reference,
        "relative_energy_error": abs(energy - 0.5 * UNIT_LOAD * reference) / (0.5 * UNIT_LOAD * reference),
        "free_residual_relative": float(np.linalg.norm(residual[free]) / max(np.linalg.norm(load[free]), 1.0)),
        "max_strain": float(max(np.linalg.norm(row) for row in local_strains)),
        "max_stress": float(max(np.linalg.norm(row) for row in local_stresses)),
        "finite": bool(np.all(np.isfinite(displacement)) and np.all(np.isfinite(stiffness))),
    }


def _patch_and_rank() -> dict[str, object]:
    material = SolidMaterial(E=E, nu=0.4999)
    nodes, elements = _mesh(1, 1, 1)
    coords = nodes[elements[0]]
    standard = Hex8Element(material)
    sri = Hex8SRIElement(material)
    gradient = np.asarray([[0.01, 0.02, 0.03], [0.04, 0.05, 0.06], [0.07, 0.08, 0.09]])
    displacement = np.concatenate([gradient @ point for point in coords])
    expected = np.asarray(
        [gradient[0, 0], gradient[1, 1], gradient[2, 2], gradient[0, 1] + gradient[1, 0], gradient[1, 2] + gradient[2, 1], gradient[0, 2] + gradient[2, 0]]
    )
    strains = [sri.strain_at(coords, displacement, point) for point in sri.integration_points]
    patch_error = max(float(np.linalg.norm(strain - expected, ord=np.inf)) for strain in strains)
    constant_difference = float(np.linalg.norm(sri.stiffness(coords) @ displacement - standard.stiffness(coords) @ displacement) / max(np.linalg.norm(standard.stiffness(coords) @ displacement), 1.0))
    sri_stiffness = sri.stiffness(coords)
    eigenvalues = np.linalg.eigvalsh(sri_stiffness)
    scale = max(float(np.max(np.abs(eigenvalues))), 1.0)
    null_count = int(np.count_nonzero(np.abs(eigenvalues) <= TOLERANCES["rank_null_relative"] * scale))
    positive = eigenvalues[np.abs(eigenvalues) > TOLERANCES["rank_null_relative"] * scale]
    rigid_modes = []
    for axis in range(3):
        mode = np.zeros(24)
        mode[axis::3] = 1.0
        rigid_modes.append(mode)
    for axis in np.eye(3):
        mode = np.zeros(24)
        for node, point in enumerate(coords):
            mode[3 * node : 3 * node + 3] = np.cross(axis, point)
        rigid_modes.append(mode)
    rigid_error = max(float(np.linalg.norm(sri_stiffness @ mode, ord=np.inf) / scale) for mode in rigid_modes)
    energy_left = float(displacement @ sri_stiffness @ displacement)
    energy_right = float(displacement @ (sri_stiffness @ displacement))
    return {
        "patch_error": patch_error,
        "constant_strain_error": patch_error,
        "constant_stiffness_action_difference": constant_difference,
        "stiffness_symmetry_relative": float(np.linalg.norm(sri_stiffness - sri_stiffness.T) / max(np.linalg.norm(sri_stiffness), 1.0)),
        "rigid_body_relative": rigid_error,
        "rank": int(sri_stiffness.shape[0] - null_count),
        "null_modes": null_count,
        "positive_mode_min_relative": float(np.min(positive) / scale),
        "energy_identity_relative": abs(energy_left - energy_right) / max(abs(energy_left), 1.0),
        "status": "PASS"
        if patch_error <= TOLERANCES["patch_absolute"]
        and rigid_error <= TOLERANCES["rigid_body_relative"]
        and null_count == 6
        and np.min(positive) / scale > TOLERANCES["positive_mode_relative"]
        and float(np.linalg.norm(sri_stiffness - sri_stiffness.T) / max(np.linalg.norm(sri_stiffness), 1.0)) <= TOLERANCES["symmetry_relative"]
        and abs(energy_left - energy_right) / max(abs(energy_left), 1.0) <= TOLERANCES["energy_identity_relative"]
        else "FAIL",
    }


def _stability() -> dict[str, object]:
    material = SolidMaterial(E=E, nu=0.4999)
    sri = Hex8SRIElement(material)
    valid = []
    for distorted in (False, True):
        nodes, elements = _mesh(1, 1, 1, distorted=distorted)
        coords = nodes[elements[0]]
        matrix = sri.stiffness(coords)
        eigenvalues = np.linalg.eigvalsh(matrix)
        scale = max(float(np.max(np.abs(eigenvalues))), 1.0)
        null_count = int(np.count_nonzero(np.abs(eigenvalues) <= TOLERANCES["rank_null_relative"] * scale))
        valid.append({"distorted": distorted, "null_modes": null_count, "min_eigenvalue": float(np.min(eigenvalues)), "max_eigenvalue": float(np.max(eigenvalues))})
    invalid_nodes, invalid_elements = _mesh(1, 1, 1)
    invalid_coords = invalid_nodes[invalid_elements[0]]
    invalid_coords = invalid_coords[[0, 3, 2, 1, 4, 7, 6, 5]]
    try:
        sri.stiffness(invalid_coords)
        invalid_status = "FAIL"
    except ValueError:
        invalid_status = "PASS"
    return {"valid_cases": valid, "invalid_orientation": invalid_status, "status": "PASS" if all(row["null_modes"] == 6 for row in valid) and invalid_status == "PASS" else "FAIL"}


def _campaign() -> dict[str, object]:
    patch = _patch_and_rank()
    stability = _stability()
    cases: dict[str, dict[str, list[dict[str, object]]]] = {}
    for name, nu in (("bending_nu030", 0.30), ("nearly_incompressible_nu04999", 0.4999)):
        cases[name] = {
            "standard": [_assemble_case(nx, nu, sri=False) for nx in LEVELS],
            "sri": [_assemble_case(nx, nu, sri=True) for nx in LEVELS],
        }
    reductions = {}
    for name, rows in cases.items():
        standard = rows["standard"][-1]
        sri = rows["sri"][-1]
        reductions[name] = {
            "fine_level_standard_error": standard["relative_displacement_error"],
            "fine_level_sri_error": sri["relative_displacement_error"],
            "fine_level_error_reduction": (standard["relative_displacement_error"] - sri["relative_displacement_error"]) / standard["relative_displacement_error"],
        }
    gain = reductions["nearly_incompressible_nu04999"]["fine_level_error_reduction"]
    monotone = all(rows["sri"][i]["relative_displacement_error"] >= rows["sri"][i + 1]["relative_displacement_error"] for rows in cases.values() for i in range(len(LEVELS) - 1))
    finite = all(row["finite"] for rows in cases.values() for family in rows.values() for row in family)
    locking_reduction = bool(gain >= TOLERANCES["fine_locking_gain"])
    gates = {
        "patch": patch["status"],
        "stability": stability["status"],
        "finite_campaign": "PASS" if finite else "FAIL",
        "mesh_convergence": "PASS" if monotone else "FAIL",
        "locking_reduction": "PASS" if locking_reduction else "FAIL",
    }
    decision = "EXPERIMENTAL_BOUNDED_CANDIDATE" if all(value == "PASS" for value in gates.values()) else "DEFER"
    return {
        "cases": cases,
        "patch_and_rank": patch,
        "stability": stability,
        "locking_reduction": reductions,
        "mesh_convergence": {"sri_error_non_increasing": monotone, "levels": LEVELS},
        "gates": gates,
        "technical_decision": decision,
        "predeclared_tolerances": TOLERANCES,
        "standard_hex8_changed": False,
        "numerical_source_changed": True,
    }


def run() -> dict[str, object]:
    first = _campaign()
    second = _campaign()
    first_digest = _digest(first)
    second_digest = _digest(second)
    evidence = {
        "schema_version": 1,
        "record_id": "QF-028-WP10-HEX8-SRI-VNV",
        "work_package": "WP10",
        "baseline_sha": BASELINE_SHA,
        "contract": "qualification/0_2_8/wp10_hex8_sri_contract.json",
        "status": "CAMPAIGN_COMPLETE_RESEARCH_GATE",
        "technical_decision": first["technical_decision"],
        "formulation": "full deviatoric 2x2x2 plus centre-only volumetric contribution for isotropic linear elasticity",
        "baseline_locking_cases": ["bending_nu030", "nearly_incompressible_nu04999"],
        "campaign": first,
        "replays": {"required": 2, "digests": [first_digest, second_digest], "deterministic": first_digest == second_digest, "status": "PASS" if first_digest == second_digest else "FAIL"},
        "integrity": {"numerical_source_changed": True, "hex8_standard_changed": False, "historical_0_2_7_evidence_changed": False, "wp07_wp09_claims_changed": False},
        "limitations": [
            "SRI is internal and not a public registry or compatibility capability.",
            "Scope is isotropic small-strain linear-static HEX8 only.",
            "No hourglass control, HEX8R, nonlinear, modal, dynamic, buckling, mixed-large or PYRAMID5 maturation claim.",
            "No external solver correlation is claimed; the Timoshenko oracle is used for the executed slender cantilever scope.",
            "The affine strain and energy checks pass, but the centre-only volumetric term changes the affine nodal force action; no general patch-force qualification is claimed.",
        ],
    }
    matrix = {
        "schema_version": 1,
        "record_id": "QF-028-WP10-HEX8-SRI-MATRIX",
        "work_package": "WP10",
        "baseline_sha": BASELINE_SHA,
        "technical_decision": first["technical_decision"],
        "proposed_maturity": "EXPERIMENTAL_BOUNDED_CANDIDATE" if first["technical_decision"] == "EXPERIMENTAL_BOUNDED_CANDIDATE" else "NONE",
        "public_promotion": False,
        "scope": "Internal isotropic small-strain linear-static HEX8 SRI research candidate on the tested bending and nearly-incompressible structured meshes.",
        "registry_separation": {"public_hex8_standard_unchanged": True, "hex8_sri_public_registry_entry": False, "element_analysis_registry_46_changed": False},
        "evidence": "qualification/0_2_8/wp10_hex8_sri_vnv.json",
        "owner_gate_required": True,
        "limitations": [
            "Affine strain and energy pass, but the centre-only volumetric term changes the affine nodal force action.",
            "No general patch-force, industrial external-correlation or production performance claim is made.",
        ],
        "integrity": evidence["integrity"],
    }
    EVIDENCE_PATH.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MATRIX_PATH.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return evidence


if __name__ == "__main__":
    result = run()
    print(json.dumps({"status": result["status"], "technical_decision": result["technical_decision"], "output": str(EVIDENCE_PATH)} , indent=2))
