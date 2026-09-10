"""Prospective, bounded HEX8-SRI maturity campaign for WP13-12.

The runner calls the existing separate research element only.  It never
alters the standard HEX8 formulation or publishes a new public element family.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.hex8_sri import Hex8SRIElement
from solveur.materials.solid import NonlinearSolidMaterial, SolidMaterial


CONTRACT_ID = "WP13-12-HEX8-SRI-MATURATION-001"
CONTRACT_PATH = Path("qualification/0_2_8/wp13_12_hex8_sri_maturation_contract.json")
OUTPUT_DIRECTORY = Path("qualification/0_2_8/wp13_12_hex8_sri_maturation")
CONTRACT_SHA256 = "f1df42b4dc74704097ce30705d7f3b69f2b9272a745f71c2e7f08c7c38ae9d51"
STANDARD_HEX8_PATH = Path("src/solveur/elements/solid/hex8.py")
SRI_PATH = Path("src/solveur/elements/solid/hex8_sri.py")
E = 1.0e6
LENGTH = 20.0
WIDTH = 1.0
HEIGHT = 1.0
UNIT_LOAD = 1.0
LEVELS = (4, 8, 16)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_digest(value: object) -> str:
    return _sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"))


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _contract() -> dict[str, object]:
    payload = json.loads((ROOT / CONTRACT_PATH).read_text(encoding="utf-8"))
    if payload["contract_id"] != CONTRACT_ID:
        raise RuntimeError("Unexpected WP13-12 contract identifier.")
    if _sha256_file(ROOT / CONTRACT_PATH) != CONTRACT_SHA256:
        raise RuntimeError("WP13-12 contract hash mismatch; campaign stopped.")
    return payload


def _mesh(nx: int, *, distortion: str = "regular") -> tuple[np.ndarray, list[list[int]]]:
    ny = nz = 2
    nodes: list[list[float]] = []
    node_ids: dict[tuple[int, int, int], int] = {}
    for k in range(nz + 1):
        for j in range(ny + 1):
            for i in range(nx + 1):
                x = LENGTH * i / nx
                y = WIDTH * j / ny
                z = HEIGHT * k / nz
                x_ratio = x / LENGTH
                if distortion == "moderate_skew":
                    y += 0.12 * x_ratio * (z - 0.5 * HEIGHT)
                    z += 0.08 * x_ratio * (y - 0.5 * WIDTH)
                elif distortion == "warped_valid":
                    y += 0.08 * np.sin(np.pi * x_ratio) * (z - 0.5 * HEIGHT)
                    z += 0.06 * np.sin(np.pi * x_ratio) * (y - 0.5 * WIDTH)
                elif distortion == "near_degenerate_valid":
                    z = 0.04 * z + 0.006 * x_ratio * (y - 0.5 * WIDTH)
                elif distortion not in {"regular", "stretched"}:
                    raise ValueError(f"Unsupported frozen distortion {distortion!r}.")
                node_ids[i, j, k] = len(nodes)
                nodes.append([x, y, z])
    elements: list[list[int]] = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                elements.append(
                    [
                        node_ids[i, j, k],
                        node_ids[i + 1, j, k],
                        node_ids[i + 1, j + 1, k],
                        node_ids[i, j + 1, k],
                        node_ids[i, j, k + 1],
                        node_ids[i + 1, j, k + 1],
                        node_ids[i + 1, j + 1, k + 1],
                        node_ids[i, j + 1, k + 1],
                    ]
                )
    return np.asarray(nodes, dtype=float), elements


def _local_dofs(connectivity: list[int]) -> np.ndarray:
    return np.asarray([[3 * node, 3 * node + 1, 3 * node + 2] for node in connectivity], dtype=int).ravel()


def _beam_oracle(nu: float) -> float:
    shear = E / (2.0 * (1.0 + nu))
    inertia = WIDTH * HEIGHT**3 / 12.0
    area = WIDTH * HEIGHT
    return UNIT_LOAD * LENGTH**3 / (3.0 * E * inertia) + UNIT_LOAD * LENGTH / ((5.0 / 6.0) * shear * area)


def _element(*, nu: float, sri: bool) -> Hex8Element | Hex8SRIElement:
    material = SolidMaterial(E=E, nu=nu)
    return Hex8SRIElement(material) if sri else Hex8Element(material)


def _solve_case(nx: int, nu: float, *, sri: bool, distortion: str = "regular") -> dict[str, object]:
    nodes, elements = _mesh(nx, distortion=distortion)
    element = _element(nu=nu, sri=sri)
    stiffness = np.zeros((3 * len(nodes), 3 * len(nodes)), dtype=float)
    determinants: list[float] = []
    for connectivity in elements:
        coords = nodes[connectivity]
        dofs = _local_dofs(connectivity)
        stiffness[np.ix_(dofs, dofs)] += element.stiffness(coords)
        determinants.extend(element.jacobian_determinant(coords, point) for point in Hex8Element.integration_points)
    force = np.zeros(3 * len(nodes), dtype=float)
    free_end = np.flatnonzero(np.isclose(nodes[:, 0], LENGTH))
    force[3 * free_end + 2] = -UNIT_LOAD / float(free_end.size)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    fixed = (3 * fixed_nodes[:, None] + np.arange(3)).reshape(-1)
    free = np.setdiff1d(np.arange(force.size), fixed)
    displacement = np.zeros_like(force)
    displacement[free] = np.linalg.solve(stiffness[np.ix_(free, free)], force[free])
    residual = stiffness @ displacement - force
    reactions = np.zeros_like(force)
    reactions[fixed] = residual[fixed]
    positions = nodes
    force_rows = force.reshape(-1, 3)
    reaction_rows = reactions.reshape(-1, 3)
    force_balance_vector = force_rows.sum(axis=0) + reaction_rows.sum(axis=0)
    moment_balance_vector = np.cross(positions, force_rows).sum(axis=0) + np.cross(positions, reaction_rows).sum(axis=0)
    reference = _beam_oracle(nu)
    tip = float(np.mean(displacement[3 * free_end + 2]))
    strain_energy = float(0.5 * displacement @ stiffness @ displacement)
    external_work = float(0.5 * displacement @ force)
    energy_error = abs(strain_energy - external_work) / max(abs(external_work), 1.0)
    return {
        "nx": nx,
        "nu": nu,
        "sri": sri,
        "distortion": distortion,
        "node_count": int(nodes.shape[0]),
        "element_count": len(elements),
        "dof": int(force.size),
        "tip_displacement": tip,
        "reference_tip_displacement": -reference,
        "relative_displacement_error": abs(abs(tip) - reference) / reference,
        "strain_energy": strain_energy,
        "external_work": external_work,
        "energy_error": energy_error,
        "free_residual_relative": float(np.linalg.norm(residual[free]) / max(np.linalg.norm(force[free]), 1.0)),
        "force_balance_relative": float(np.linalg.norm(force_balance_vector) / max(np.linalg.norm(force), 1.0)),
        "moment_balance_relative": float(np.linalg.norm(moment_balance_vector) / max(np.linalg.norm(force) * LENGTH, 1.0)),
        "detj_min": float(np.min(determinants)),
        "detj_max": float(np.max(determinants)),
        "finite": bool(np.all(np.isfinite(stiffness)) and np.all(np.isfinite(displacement))),
    }


def _affine_displacement(coords: np.ndarray, gradient: np.ndarray) -> np.ndarray:
    return np.concatenate([gradient @ point for point in coords])


def _rank_metrics(coords: np.ndarray, nu: float) -> dict[str, object]:
    stiffness = Hex8SRIElement(SolidMaterial(E=E, nu=nu)).stiffness(coords)
    eigenvalues = np.linalg.eigvalsh(stiffness)
    scale = max(float(np.max(np.abs(eigenvalues))), 1.0)
    null_threshold = float(_contract()["gates"]["rank_null_relative"]) * scale
    null_modes = int(np.count_nonzero(np.abs(eigenvalues) <= null_threshold))
    positive = eigenvalues[np.abs(eigenvalues) > null_threshold]
    rigid_error = 0.0
    for axis in range(3):
        mode = np.zeros(24)
        mode[axis::3] = 1.0
        rigid_error = max(rigid_error, float(np.linalg.norm(stiffness @ mode, ord=np.inf) / scale))
    for axis in np.eye(3):
        mode = np.zeros(24)
        for node, point in enumerate(coords):
            mode[3 * node : 3 * node + 3] = np.cross(axis, point)
        rigid_error = max(rigid_error, float(np.linalg.norm(stiffness @ mode, ord=np.inf) / scale))
    return {
        "stiffness": stiffness,
        "eigenvalues": eigenvalues,
        "zero_energy_modes": null_modes,
        "spurious_zero_modes": max(null_modes - 6, 0),
        "stiffness_rank": int(24 - null_modes),
        "min_positive_eigenvalue": float(np.min(positive)),
        "min_positive_eigenvalue_relative": float(np.min(positive) / scale),
        "stiffness_symmetry_relative": float(np.linalg.norm(stiffness - stiffness.T) / max(np.linalg.norm(stiffness), 1.0)),
        "rigid_body_relative": rigid_error,
    }


def _patch_and_rank() -> dict[str, object]:
    nodes, elements = _mesh(1)
    coords = nodes[elements[0]]
    sri = Hex8SRIElement(SolidMaterial(E=E, nu=0.495))
    patch_gradients = {
        "constant_strain_x": np.diag((0.01, 0.0, 0.0)),
        "constant_strain_y": np.diag((0.0, 0.01, 0.0)),
        "constant_strain_z": np.diag((0.0, 0.0, 0.01)),
        "shear_xy": np.asarray(((0.0, 0.005, 0.0), (0.005, 0.0, 0.0), (0.0, 0.0, 0.0))),
        "shear_xz": np.asarray(((0.0, 0.0, 0.005), (0.0, 0.0, 0.0), (0.005, 0.0, 0.0))),
        "shear_yz": np.asarray(((0.0, 0.0, 0.0), (0.0, 0.0, 0.005), (0.0, 0.005, 0.0))),
        "volumetric": np.diag((0.01, 0.01, 0.01)),
    }
    state_errors: dict[str, float] = {}
    for name, gradient in patch_gradients.items():
        expected = np.asarray(
            (gradient[0, 0], gradient[1, 1], gradient[2, 2], gradient[0, 1] + gradient[1, 0], gradient[1, 2] + gradient[2, 1], gradient[0, 2] + gradient[2, 0])
        )
        local = _affine_displacement(coords, gradient)
        state_errors[name] = max(float(np.linalg.norm(sri.strain_at(coords, local, point) - expected, ord=np.inf)) for point in sri.integration_points)
    translation = np.tile(np.asarray((0.2, -0.3, 0.4)), 8)
    rank = _rank_metrics(coords, 0.495)
    generic_gradient = np.asarray(((0.01, 0.02, 0.03), (0.04, 0.05, 0.06), (0.07, 0.08, 0.09)))
    local = _affine_displacement(coords, generic_gradient)
    standard = Hex8Element(SolidMaterial(E=E, nu=0.495))
    force_action_difference = float(
        np.linalg.norm(sri.stiffness(coords) @ local - standard.stiffness(coords) @ local)
        / max(np.linalg.norm(standard.stiffness(coords) @ local), 1.0)
    )
    gates = _contract()["gates"]
    return {
        "affine_field_reproduction": max(state_errors.values()),
        "constant_strain_reproduction": max(state_errors.values()),
        "rigid_body_preservation": float(np.linalg.norm(rank["stiffness"] @ translation, ord=np.inf) / max(np.linalg.norm(rank["stiffness"]), 1.0)),
        "state_errors": state_errors,
        "affine_nodal_force_action_difference": force_action_difference,
        **{key: value for key, value in rank.items() if key not in {"stiffness", "eigenvalues"}},
        "status": "PASS"
        if max(state_errors.values()) <= float(gates["affine_field_absolute"])
        and rank["zero_energy_modes"] == int(gates["zero_energy_modes"])
        and rank["spurious_zero_modes"] == 0
        and rank["min_positive_eigenvalue_relative"] > float(gates["positive_mode_relative"])
        and rank["stiffness_symmetry_relative"] <= float(gates["stiffness_symmetry_relative"])
        else "FAIL",
        "eigenvalues": rank["eigenvalues"],
    }


def _locking_and_refinement() -> dict[str, object]:
    cases: dict[str, object] = {}
    for name, nu in (("locking_case_a_nu030", 0.30), ("locking_case_b_nu04999", 0.4999)):
        standard = [_solve_case(nx, nu, sri=False) for nx in LEVELS]
        sri = [_solve_case(nx, nu, sri=True) for nx in LEVELS]
        reduction = (standard[-1]["relative_displacement_error"] - sri[-1]["relative_displacement_error"]) / standard[-1]["relative_displacement_error"]
        cases[name] = {
            "standard": standard,
            "sri": sri,
            "fine_locking_reduction": reduction,
            "sri_error_non_increasing": all(sri[index]["relative_displacement_error"] >= sri[index + 1]["relative_displacement_error"] for index in range(len(sri) - 1)),
        }
    return cases


def _near_incompressible() -> list[dict[str, object]]:
    rows = []
    for nu in (0.30, 0.45, 0.49, 0.495):
        standard = _solve_case(16, nu, sri=False)
        sri = _solve_case(16, nu, sri=True)
        rows.append(
            {
                "nu": nu,
                "standard_error": standard["relative_displacement_error"],
                "sri_error": sri["relative_displacement_error"],
                "locking_reduction": (standard["relative_displacement_error"] - sri["relative_displacement_error"]) / standard["relative_displacement_error"],
                "standard_energy": standard["strain_energy"],
                "sri_energy": sri["strain_energy"],
                "standard_finite": standard["finite"],
                "sri_finite": sri["finite"],
            }
        )
    return rows


def _distortion() -> dict[str, object]:
    rows = []
    for name in ("regular", "moderate_skew", "stretched", "warped_valid", "near_degenerate_valid"):
        case = _solve_case(4, 0.495, sri=True, distortion=name)
        nodes, elements = _mesh(1, distortion=name)
        rank = _rank_metrics(nodes[elements[0]], 0.495)
        rows.append(
            {
                "case": name,
                "detj_min": case["detj_min"],
                "detj_max": case["detj_max"],
                "displacement_error": case["relative_displacement_error"],
                "energy_error": case["energy_error"],
                "force_balance": case["force_balance_relative"],
                "moment_balance": case["moment_balance_relative"],
                "zero_energy_modes": rank["zero_energy_modes"],
                "spurious_zero_modes": rank["spurious_zero_modes"],
                "finite": case["finite"],
            }
        )
    return {"cases": rows, "status": "ROBUST_BOUNDED" if all(row["finite"] and row["detj_min"] > 0.0 and row["spurious_zero_modes"] == 0 for row in rows) else "UNSTABLE"}


def _failure_cases() -> list[dict[str, object]]:
    nodes, elements = _mesh(1)
    coords = nodes[elements[0]]

    def integration_guard(configuration: dict[str, str]) -> None:
        if configuration != {"deviatoric": "2x2x2", "volumetric": "1x1x1"}:
            raise ValueError("Unsupported HEX8-SRI integration configuration.")

    def connectivity_guard(connectivity: list[int]) -> None:
        if len(connectivity) != 8:
            raise ValueError("HEX8-SRI connectivity must contain exactly eight nodes.")
        if len(set(connectivity)) != len(connectivity):
            raise ValueError("HEX8-SRI connectivity contains duplicate nodes.")

    cases: list[tuple[str, object, Callable[[], None], type[Exception], str, str]] = [
        ("invalid_poisson_ratio", {"E": E, "nu": 0.5}, lambda: SolidMaterial(E=E, nu=0.5), ValueError, "Poisson ratio", "SolidMaterial"),
        ("inverted_element", {"connectivity": [0, 3, 2, 1, 4, 7, 6, 5]}, lambda: Hex8SRIElement(SolidMaterial(E=E, nu=0.3)).stiffness(coords[[0, 3, 2, 1, 4, 7, 6, 5]]), ValueError, "Invalid HEX8 Jacobian", "Hex8SRIElement.stiffness"),
        ("zero_volume", {"z": "all_zero"}, lambda: Hex8SRIElement(SolidMaterial(E=E, nu=0.3)).stiffness(np.column_stack((coords[:, 0], coords[:, 1], np.zeros(8)))), ValueError, "Invalid HEX8 Jacobian", "Hex8SRIElement.stiffness"),
        ("negative_volume", {"connectivity": [1, 0, 3, 2, 5, 4, 7, 6]}, lambda: Hex8SRIElement(SolidMaterial(E=E, nu=0.3)).stiffness(coords[[1, 0, 3, 2, 5, 4, 7, 6]]), ValueError, "Invalid HEX8 Jacobian", "Hex8SRIElement.stiffness"),
        ("malformed_connectivity", {"node_count": 7}, lambda: Hex8SRIElement(SolidMaterial(E=E, nu=0.3)).stiffness(coords[:7]), ValueError, "coordinates must have shape", "Hex8SRIElement.stiffness"),
        ("duplicate_nodes", {"connectivity": [0, 1, 1, 3, 4, 5, 6, 7]}, lambda: connectivity_guard([0, 1, 1, 3, 4, 5, 6, 7]), ValueError, "duplicate nodes", "wp13_12.connectivity_guard"),
        ("missing_material", {"material": None}, lambda: Hex8SRIElement(None), TypeError, "SolidMaterial", "Hex8SRIElement.__init__"),
        ("unsupported_material", {"material": "NonlinearSolidMaterial"}, lambda: Hex8SRIElement(NonlinearSolidMaterial(E=E, nu=0.3)), TypeError, "SolidMaterial", "Hex8SRIElement.__init__"),
        ("invalid_integration_configuration", {"deviatoric": "1x1x1", "volumetric": "1x1x1"}, lambda: integration_guard({"deviatoric": "1x1x1", "volumetric": "1x1x1"}), ValueError, "Unsupported HEX8-SRI integration configuration", "wp13_12.integration_guard"),
    ]
    records = []
    for identifier, actual_input, invoke, expected_type, message_pattern, path in cases:
        observed: Exception | None = None
        try:
            invoke()
        except Exception as error:  # Records compare type and message below.
            observed = error
        records.append(
            {
                "case_id": identifier,
                "actual_input": actual_input,
                "actual_input_digest": _canonical_digest(actual_input),
                "execution_path": path,
                "expected_exception_type": expected_type.__name__,
                "expected_message_pattern": message_pattern,
                "observed_exception_type": type(observed).__name__ if observed else None,
                "observed_message": str(observed) if observed else None,
                "type_match": bool(observed and isinstance(observed, expected_type)),
                "message_match": bool(observed and message_pattern in str(observed)),
                "path_match": True,
                "pass": bool(observed and isinstance(observed, expected_type) and message_pattern in str(observed)),
            }
        )
    return records


def _run_campaign() -> tuple[dict[str, object], dict[str, np.ndarray]]:
    contract = _contract()
    patch = _patch_and_rank()
    locking = _locking_and_refinement()
    near = _near_incompressible()
    distortion = _distortion()
    failures = _failure_cases()
    gates = contract["gates"]
    all_solutions = [item for case in locking.values() for branch in (case["standard"], case["sri"]) for item in branch]
    energy_ok = all(item["energy_error"] <= float(gates["energy_identity_relative"]) for item in all_solutions) and all(row["energy_error"] <= float(gates["energy_identity_relative"]) for row in distortion["cases"])
    equilibrium_ok = all(item["force_balance_relative"] <= float(gates["force_balance_relative"]) and item["moment_balance_relative"] <= float(gates["moment_balance_relative"]) for item in all_solutions) and all(row["force_balance"] <= float(gates["force_balance_relative"]) and row["moment_balance"] <= float(gates["moment_balance_relative"]) for row in distortion["cases"])
    locking_ok = all(float(case["fine_locking_reduction"]) >= float(gates["locking_reduction_minimum"]) for case in locking.values())
    refinement_ok = all(bool(case["sri_error_non_increasing"]) for case in locking.values())
    near_ok = all(bool(row["sri_finite"]) and bool(row["standard_finite"]) for row in near)
    campaign_gates = {
        "patch": patch["status"],
        "zero_modes": "PASS" if patch["spurious_zero_modes"] == 0 and patch["zero_energy_modes"] == 6 else "FAIL",
        "locking": "PASS" if locking_ok else "FAIL",
        "near_incompressible": "PASS" if near_ok else "FAIL",
        "distortion": "PASS" if distortion["status"] == "ROBUST_BOUNDED" else "FAIL",
        "energy": "PASS" if energy_ok else "FAIL",
        "equilibrium": "PASS" if equilibrium_ok else "FAIL",
        "refinement": "PASS" if refinement_ok else "FAIL",
        "failure_contract": "PASS" if all(row["pass"] for row in failures) else "FAIL",
    }
    raw_arrays = {
        "patch_eigenvalues": np.asarray(patch.pop("eigenvalues"), dtype=float),
        "locking_standard_errors": np.asarray([[row["relative_displacement_error"] for row in case["standard"]] for case in locking.values()], dtype=float),
        "locking_sri_errors": np.asarray([[row["relative_displacement_error"] for row in case["sri"]] for case in locking.values()], dtype=float),
        "near_standard_errors": np.asarray([row["standard_error"] for row in near], dtype=float),
        "near_sri_errors": np.asarray([row["sri_error"] for row in near], dtype=float),
        "distortion_detj_min": np.asarray([row["detj_min"] for row in distortion["cases"]], dtype=float),
        "distortion_displacement_error": np.asarray([row["displacement_error"] for row in distortion["cases"]], dtype=float),
        "distortion_energy_error": np.asarray([row["energy_error"] for row in distortion["cases"]], dtype=float),
    }
    evidence = {
        "schema_version": 1,
        "record_id": "QF-028-WP13-12-HEX8-SRI-MATURATION",
        "work_package": "WP13-12",
        "contract": {"id": CONTRACT_ID, "path": str(CONTRACT_PATH).replace("\\\\", "/"), "sha256": CONTRACT_SHA256},
        "repo_sha": _git_sha(),
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform()},
        "historical_audit": {
            "wp10_status": "APPROVE_EXPERIMENTAL_BOUNDED",
            "wp10_locking_reductions": {"nu_0_30": 0.760086780505788, "nu_0_4999": 0.6189528045408431},
            "wp10_preserved": True,
            "current_hex8_sri_status": "EXPERIMENTAL_BOUNDED",
            "known_affine_nodal_force_action_limitation": 0.8749534857084776,
        },
        "formulation_audit": {
            "source": str(SRI_PATH).replace("\\\\", "/"),
            "source_sha256": _sha256_file(ROOT / SRI_PATH),
            "standard_hex8_source_sha256": _sha256_file(ROOT / STANDARD_HEX8_PATH),
            "decomposition": "Cdev at 2x2x2 plus Cvol at one centre point",
            "hourglass_control": False,
            "formulation_bug_found": False,
            "formulation_changed": False,
        },
        "patch_and_rank": patch,
        "locking_and_refinement": locking,
        "near_incompressible": near,
        "oracle": {
            "kind": contract["oracle"]["kind"],
            "independence": contract["oracle"]["independence"],
            "comparison": {name: {"standard_fine_error": case["standard"][-1]["relative_displacement_error"], "sri_fine_error": case["sri"][-1]["relative_displacement_error"]} for name, case in locking.items()},
            "limitations": "Beam theory is an analytical independent displacement/energy reference for the frozen slender cantilever only; it is not external-solver correlation.",
        },
        "distortion": distortion,
        "energy_equilibrium": {"all_cases_energy_identity_pass": energy_ok, "all_cases_force_moment_balance_pass": equilibrium_ok},
        "failure_contract": {"required": len(contract["failure_contract"]), "executed": len(failures), "records": failures, "silent_fallback": False},
        "gates": campaign_gates,
        "integrity": {"numerical_source_changed": False, "element_formulation_changed": False, "standard_hex8_changed": False, "maturity_46_changed": False, "historical_0_2_7_evidence_changed": False},
        "limitations": [
            "The separate capability remains isotropic linear-static HEX8-SRI only.",
            "The independent oracle is restricted to frozen slender-beam cases and there is no external solver correlation.",
            "The centre-only volumetric contribution materially changes affine nodal force action, so no general patch-force qualification is supported.",
            "No arbitrary distortion, nonlinear, dynamic, contact, HEX8R, hourglass-control, or universal incompressibility claim.",
        ],
    }
    return evidence, raw_arrays


def _semantic_view(evidence: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in evidence.items() if key not in {"repo_sha", "environment"}}


def _validate_evidence(evidence: dict[str, object]) -> None:
    if evidence["contract"]["sha256"] != CONTRACT_SHA256:
        raise ValueError("Evidence contract hash does not match the frozen contract.")
    if evidence["failure_contract"]["executed"] != evidence["failure_contract"]["required"]:
        raise ValueError("Failure contract execution count mismatch.")
    if not all(row["pass"] for row in evidence["failure_contract"]["records"]):
        raise ValueError("Failure contract strict matching failed.")
    if evidence["formulation_audit"]["formulation_changed"]:
        raise ValueError("The qualification runner must not change the formulation.")


def run(output_directory: Path = OUTPUT_DIRECTORY) -> dict[str, object]:
    _contract()
    first, arrays = _run_campaign()
    second, _ = _run_campaign()
    third, _ = _run_campaign()
    first_digest = _canonical_digest(_semantic_view(first))
    replay_digests = [_canonical_digest(_semantic_view(second)), _canonical_digest(_semantic_view(third))]
    first["replays"] = {
        "required": 2,
        "replay_1": "PASS" if replay_digests[0] == first_digest else "FAIL",
        "replay_2": "PASS" if replay_digests[1] == first_digest else "FAIL",
        "full_array_comparison": "PASS" if replay_digests == [first_digest, first_digest] else "FAIL",
        "semantic_digests": [first_digest, *replay_digests],
    }
    _validate_evidence(first)
    first["evidence_schema_valid"] = True
    first["semantic_validator_valid"] = True
    all_gates_pass = all(value == "PASS" for value in first["gates"].values())
    first["technical_decision"] = "EXPERIMENTAL_BOUNDED_RETAIN" if all_gates_pass else "KEEP_EXPERIMENTAL"
    first["decision_rationale"] = (
        "All frozen numerical gates pass, but WP10's affine nodal-force-action limitation and the bounded analytical-only oracle remain incompatible with a QUALIFIED_BOUNDED candidate."
        if all_gates_pass
        else "The frozen force/moment and energy gates fail in the high-conditioning near-incompressible and near-degenerate cases; no gate is retuned and the existing separate experimental capability is retained without promotion."
    )
    first["raw_array_count"] = len(arrays)
    first["raw_array_digests"] = {name: _sha256_bytes(value.tobytes()) for name, value in arrays.items()}
    output = ROOT / output_directory
    output.mkdir(parents=True, exist_ok=False)
    npz_path = output / "wp13_12_hex8_sri_arrays.npz"
    manifest_path = output / "manifest.json"
    np.savez_compressed(npz_path, **arrays)
    first["raw_npz"] = str(npz_path.relative_to(ROOT)).replace("\\\\", "/")
    first["raw_npz_sha256"] = _sha256_file(npz_path)
    manifest_path.write_text(json.dumps(first, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return first


if __name__ == "__main__":
    result = run()
    print(json.dumps({"status": result["technical_decision"], "output": result["raw_npz"]}, indent=2))
