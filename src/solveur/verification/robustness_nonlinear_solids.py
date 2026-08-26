"""Bounded robustness qualification for the common J2 solid path.

The campaign deliberately separates internal verification from external
correlation.  It exercises the same constitutive contract and element
assembly used by the solver; it does not promote a scope by itself.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from solveur.api import solve_model
from solveur.contact.entities import FrictionlessContact
from solveur.contact.solver import assemble_penalty_contact
from solveur.core.errors import NumericalConvergenceError
from solveur.core.material_state import MaterialStateSession
from solveur.core.material_state import state_digest
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear import NonlinearStaticSolver
from solveur.elements.solid.hex20 import Hex20Element
from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.tet10 import Tet10Element
from solveur.elements.solid.tet4 import Tet4Element
from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.elements.solid.total_lagrangian_j2 import (
    TotalLagrangianJ2Hex20Element,
    TotalLagrangianJ2Hex8Element,
    TotalLagrangianJ2Tet10Element,
    TotalLagrangianJ2Tet4Element,
)
from solveur.io.manifest import write_json_file
from solveur.materials.solid import VonMisesElastoplasticMaterial
from solveur.materials.solid import SolidMaterial
from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh
from solveur.verification.tet4_total_lagrangian_buckling import TotalLagrangianBucklingCampaign
from solveur.verification.nonlinear_failure_campaign import run_failure_campaign
from solveur.verification.total_lagrangian_structural import trace_sparse_arc_length


ELEMENT_TYPES = ("TET4", "TET10", "HEX8", "HEX20")
CAMPAIGN_ID = "VNV-ROBUSTNESS-NONLINEAR-SOLIDS-025"


def _archived_external_correlation() -> dict[str, Any]:
    """Read the bounded RQ-G08 archive when it is present in the checkout."""

    root = Path(__file__).resolve().parents[3]
    tracked_path = root / "qualification" / "external_reference_digests" / "rqg08_j2_common_024.json"
    raw_path = root / "qualification" / "vnv" / "external" / "rqg08_j2_common_024" / "reference" / "summary.json"
    path = tracked_path if tracked_path.is_file() else raw_path
    if not path.is_file():
        return {
            "status": "PENDING_EXTERNAL",
            "solvers": ["Code_Aster", "CalculiX"],
            "note": "The bounded RQ-G08 archive is not present in this checkout.",
        }
    evidence = json.loads(path.read_text(encoding="utf-8"))
    status = evidence["status"]
    if path == raw_path:
        status = "PASS_EXTERNAL_CORRELATION_BOUNDED" if status == "PASS_EXTERNAL_CORRELATION" else status
        reference = "qualification/vnv/external/rqg08_j2_common_024/reference/summary.json"
        checks = len(evidence["checks"])
        solver = evidence["external_solver"]
    else:
        checks = evidence["checks"]["total"]
        solver = evidence["external_solver"]
        reference = "qualification/external_reference_digests/rqg08_j2_common_024.json"
    return {
        "status": status,
        "solver": solver,
        "reference": reference,
        "checks": checks,
        "scope": "One affine displacement-controlled element per family; no physical validation claim.",
    }


def j2_material() -> VonMisesElastoplasticMaterial:
    """Return the deterministic material used by the bounded campaign."""

    return VonMisesElastoplasticMaterial(E=1000.0, nu=0.3, yield_stress=0.02, hardening_modulus=10.0, density=1.0)


def element_coordinates(element_type: str, *, distorted: bool = False) -> np.ndarray:
    """Return canonical unit-volume coordinates for one supported element."""

    corners = np.asarray(
        [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]],
        dtype=float,
    )
    family = str(element_type).upper()
    if family == "TET4":
        result = corners[[0, 1, 3, 4]]
    elif family == "TET10":
        base = corners[[0, 1, 3, 4]]
        edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
        result = np.vstack([base, [(base[first] + base[second]) / 2.0 for first, second in edges]])
    elif family == "HEX8":
        result = corners.copy()
    elif family == "HEX20":
        edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
        result = np.vstack([corners, [(corners[first] + corners[second]) / 2.0 for first, second in edges]])
    else:
        raise ValueError(f"Unsupported robustness element {element_type!r}.")

    if distorted and family in {"HEX8", "HEX20"}:
        result = result.copy()
        result[6] += np.asarray([0.12, -0.07, 0.08])
        if family == "HEX20":
            edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
            for index, (first, second) in enumerate(edges, start=8):
                result[index] = 0.5 * (result[first] + result[second])
    return result


def material_paths() -> dict[str, list[np.ndarray]]:
    """Return deterministic multiaxial strain histories."""

    zero = np.zeros(6)

    def vector(ex: float = 0.0, ey: float = 0.0, ez: float = 0.0, gxy: float = 0.0, gyz: float = 0.0, gxz: float = 0.0) -> np.ndarray:
        return np.asarray([ex, ey, ez, gxy, gyz, gxz], dtype=float)

    return {
        "traction_unload_reload": [
            zero,
            vector(ex=0.01),
            vector(ex=0.04),
            vector(ex=0.01),
            zero,
            vector(ex=-0.025),
            zero,
            vector(ex=0.03),
        ],
        "pure_shear": [zero, vector(gxy=0.01), vector(gxy=0.05), vector(gxy=0.01), zero, vector(gxy=-0.04)],
        "non_proportional": [
            zero,
            vector(ex=0.025),
            vector(ex=0.025, gxy=0.02),
            vector(ex=0.01, gxy=0.04),
            vector(ex=-0.015, gxy=0.02),
            vector(ex=-0.015, gxy=-0.03),
        ],
    }


def run_constitutive_paths() -> dict[str, Any]:
    """Evaluate all material paths and verify finite, transactional responses."""

    material = j2_material()
    histories: dict[str, Any] = {}
    checks: list[dict[str, Any]] = []
    for name, path in material_paths().items():
        committed = material.initial_state()
        rows = []
        for strain in path:
            response = material.evaluate(strain, committed)
            committed = deepcopy(response.trial_state)
            rows.append(
                {
                    "strain": strain.tolist(),
                    "stress": response.stress.tolist(),
                    "von_mises": float(response.trial_state["equivalent_stress"]),
                    "equivalent_plastic_strain": float(response.trial_state["equivalent_plastic_strain"]),
                    "yield_function": float(response.trial_state["yield_function"]),
                }
            )
        finite = all(np.all(np.isfinite(row["stress"])) for row in rows)
        plastic = max(row["equivalent_plastic_strain"] for row in rows)
        checks.append({"id": name, "status": "PASS" if finite and plastic > 0.0 else "FAIL", "plastic_max": plastic})
        histories[name] = rows
    return {"status": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL", "checks": checks, "histories": histories}


def tangent_finite_difference() -> dict[str, Any]:
    """Compare the algorithmic tangent with central differences over states."""

    material = j2_material()
    limit = 1.0e-6
    common_steps = (1.0e-5, 1.0e-6, 1.0e-7)

    def vector(ex: float = 0.0, ey: float = 0.0, ez: float = 0.0, gxy: float = 0.0, gyz: float = 0.0, gxz: float = 0.0) -> np.ndarray:
        return np.asarray([ex, ey, ez, gxy, gyz, gxz], dtype=float)

    def committed_before(path: list[np.ndarray], index: int) -> dict[str, object]:
        state = material.initial_state()
        for strain in path[:index]:
            state = deepcopy(material.evaluate(strain, state).trial_state)
        return state

    traction_path = material_paths()["traction_unload_reload"]
    non_proportional_path = material_paths()["non_proportional"]
    shear_path = material_paths()["pure_shear"]
    cases = [
        ("elastic", vector(ex=1.0e-5), material.initial_state(), common_steps),
        ("near_yield_elastic", vector(ex=2.5e-5), material.initial_state(), (1.0e-7, 1.0e-8, 1.0e-9)),
        ("plastic_traction", vector(ex=0.08, ey=0.005, ez=-0.002, gxy=0.01, gyz=-0.004, gxz=0.006), material.initial_state(), common_steps),
        ("plastic_compression", vector(ex=-0.08), material.initial_state(), common_steps),
        ("plastic_shear", vector(gxy=0.05), material.initial_state(), common_steps),
        ("plastic_non_proportional", non_proportional_path[-1], committed_before(non_proportional_path, len(non_proportional_path) - 1), (1.0e-6, 1.0e-7, 1.0e-8)),
        ("plastic_reload", traction_path[-1], committed_before(traction_path, len(traction_path) - 1), (1.0e-6, 1.0e-7, 1.0e-8)),
        ("plastic_shear_cycle", shear_path[-1], committed_before(shear_path, len(shear_path) - 1), (1.0e-6, 1.0e-7, 1.0e-8)),
    ]
    case_rows: list[dict[str, Any]] = []
    for name, strain, committed, steps in cases:
        response = material.evaluate(strain, committed)
        errors: list[float] = []
        for step in steps:
            numerical = np.column_stack(
                [
                    (
                        material.evaluate(strain + step * np.eye(6)[column], committed).stress
                        - material.evaluate(strain - step * np.eye(6)[column], committed).stress
                    )
                    / (2.0 * step)
                    for column in range(6)
                ]
            )
            errors.append(float(np.linalg.norm(response.tangent - numerical) / max(np.linalg.norm(numerical), 1.0)))
        case_rows.append(
            {
                "name": name,
                "steps": list(steps),
                "relative_errors": errors,
                "maximum_relative_error": max(errors),
                "elastic": bool(response.trial_state.get("elastic", False)),
                "yield_function": float(response.trial_state.get("yield_function", 0.0)),
                "equivalent_plastic_strain": float(response.trial_state.get("equivalent_plastic_strain", 0.0)),
                "status": "PASS" if max(errors) < limit and all(np.isfinite(errors)) else "FAIL",
            }
        )
    primary = next(row for row in case_rows if row["name"] == "plastic_traction")
    maximum_error = max(row["maximum_relative_error"] for row in case_rows)
    return {
        "status": "PASS" if all(row["status"] == "PASS" for row in case_rows) else "FAIL",
        "steps": list(common_steps),
        "relative_errors": primary["relative_errors"],
        "maximum_relative_error": maximum_error,
        "limit": limit,
        "cases": case_rows,
        "scope": "elastic, near-yield, traction, compression, shear, reload and non-proportional committed states",
    }


def transaction_check() -> dict[str, Any]:
    """Prove that failed trial work does not alter committed integration states."""

    material = j2_material()
    committed = {0: [material.initial_state(), material.initial_state()]}
    before = deepcopy(committed)
    session = MaterialStateSession(committed)
    trial = session.begin_trial()
    response = material.evaluate(np.asarray([0.08, 0.01, 0.0, 0.02, 0.0, 0.0]), trial[0][0])
    trial[0][0] = response.trial_state
    session.rollback()
    rollback_untouched = committed == before
    trial = session.begin_trial()
    trial[0][0] = response.trial_state
    session.commit()
    commit_changed = committed != before
    return {"status": "PASS" if rollback_untouched and commit_changed else "FAIL", "rollback_untouched": rollback_untouched, "commit_changed": commit_changed}


def _element_class(element_type: str) -> type:
    return {"TET4": Tet4Element, "TET10": Tet10Element, "HEX8": Hex8Element, "HEX20": Hex20Element}[element_type]


def run_element_matrix() -> dict[str, Any]:
    """Run the common affine history on all four element contracts."""

    gradient = np.asarray([[0.08, 0.015, -0.01], [0.005, -0.015, 0.01], [0.0, 0.008, 0.02]])
    factors = (0.25, 0.5, 0.75, 1.0, 0.5, 0.0, -0.5)
    rows = []
    for family in ELEMENT_TYPES:
        coords = element_coordinates(family, distorted=family in {"HEX8", "HEX20"})
        element = _element_class(family)(j2_material())
        committed: list[dict[str, object]] | None = None
        force_rows = []
        for factor in factors:
            displacement = np.concatenate([factor * gradient @ point for point in coords])
            internal, tangent, trial = element.internal_force_tangent_state(coords, displacement, committed)
            committed = deepcopy(trial)
            peeq = max(float(item.get("equivalent_plastic_strain", 0.0)) for item in committed)
            vm = max(float(item.get("equivalent_stress", 0.0)) for item in committed)
            force_rows.append({"factor": factor, "reaction_norm": float(np.linalg.norm(internal)), "energy": float(0.5 * displacement @ internal), "von_mises_max": vm, "peeq_max": peeq, "tangent_norm": float(np.linalg.norm(tangent))})
        rows.append({"element": family, "distorted": family in {"HEX8", "HEX20"}, "integration_points": len(committed or []), "dof_count": int(coords.size), "history": force_rows, "status": "PASS" if all(np.isfinite(row["energy"]) for row in force_rows) else "FAIL"})
    return {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "rows": rows, "factors": list(factors)}


def _global_model(element_type: str) -> FiniteElementModel:
    coords = element_coordinates(element_type)
    fixed = [{"node": 0, "dofs": ["UX", "UY", "UZ"]}, {"node": 1, "dofs": ["UY", "UZ"]}, {"node": 2, "dofs": ["UZ"]}]
    return FiniteElementModel.from_raw(
        nodes=coords.tolist(),
        elements=[{"type": element_type, "nodes": list(range(len(coords))), "material": "j2"}],
        materials={"j2": {"type": "von_mises_elastoplastic_3d", "E": 1000.0, "nu": 0.3, "density": 1.0, "yield_stress": 0.02, "hardening_modulus": 10.0}},
        fixed_dofs=fixed,
        loads=[{"node": 1, "dof": "UX", "value": 5.0}],
        analysis={"type": "nonlinear_static", "method": "newton_raphson", "load_path": [0.25, 0.5, 0.75, 1.0], "max_iterations": 30, "tolerance": 1.0e-7},
    )


def _newton_rate_metrics(residual_histories: list[list[float]]) -> dict[str, Any]:
    """Summarize observed Newton residual reduction without claiming a rate.

    The histories are evidence emitted by the solver.  This helper only
    describes the observed sequence; it deliberately does not classify a
    method as quadratic or convergent and therefore cannot hide a failed
    increment behind a scalar score.
    """

    reduction_ratios: list[list[float]] = []
    observed_orders: list[list[float]] = []
    monotone_histories: list[bool] = []
    finite_histories: list[bool] = []
    for history in residual_histories:
        values = [float(value) for value in history]
        finite = bool(values) and bool(np.all(np.isfinite(values)))
        finite_histories.append(finite)
        monotone_histories.append(
            finite
            and all(next_value <= current * (1.0 + 1.0e-12) for current, next_value in zip(values, values[1:]))
        )

        ratios: list[float] = []
        for current, next_value in zip(values, values[1:]):
            if current > 0.0 and np.isfinite(current) and np.isfinite(next_value):
                ratio = next_value / current
                if np.isfinite(ratio):
                    ratios.append(float(ratio))
        reduction_ratios.append(ratios)

        orders: list[float] = []
        for previous, current, next_value in zip(values, values[1:], values[2:]):
            if min(previous, current, next_value) <= 0.0 or not np.all(np.isfinite([previous, current, next_value])):
                continue
            denominator = float(np.log(current / previous))
            numerator = float(np.log(next_value / current))
            if abs(denominator) <= 1.0e-14:
                continue
            order = numerator / denominator
            if np.isfinite(order):
                orders.append(float(order))
        observed_orders.append(orders)

    flat_ratios = [ratio for history in reduction_ratios for ratio in history]
    return {
        "history_count": len(residual_histories),
        "finite_histories": bool(finite_histories) and all(finite_histories),
        "monotone_nonincreasing": bool(monotone_histories) and all(monotone_histories),
        "residual_reduction_ratios": reduction_ratios,
        "observed_order_estimates": observed_orders,
        "final_reduction_ratios": [history[-1] if history else None for history in reduction_ratios],
        "maximum_reduction_ratio": max(flat_ratios, default=None),
        "minimum_reduction_ratio": min(flat_ratios, default=None),
    }


def run_common_global_benchmark() -> dict[str, Any]:
    """Run the same bounded nonlinear load history through the global driver."""

    rows = []
    for family in ELEMENT_TYPES:
        started = perf_counter()
        result = solve_model(_global_model(family))
        data = result.to_dict()
        steps = data["solver"]["steps"]
        reaction_norm = 0.0
        if result.audit is not None:
            for vector in result.audit.vectors:
                name = vector.get("name", "") if isinstance(vector, dict) else getattr(vector, "name", "")
                if name == "reactions":
                    reaction_norm = float(vector.get("norm", 0.0) if isinstance(vector, dict) else vector.norm)
                    break
        residual_histories = [list(map(float, step.get("residual_history", []))) for step in steps]
        rows.append({"element": family, "status": "PASS" if result.status == "PASS" else "FAIL", "dof_count": int(result.displacements.size), "newton_iterations": int(sum(step["iterations"] for step in steps)), "maximum_relative_residual": float(max(step["relative_residual"] for step in steps)), "final_displacement_norm": float(np.linalg.norm(result.displacements)), "final_peeq": float(steps[-1]["equivalent_plastic_strain_max"]), "elapsed_seconds": float(perf_counter() - started), "reaction_norm": reaction_norm, "residual_histories": residual_histories, "rate_metrics": _newton_rate_metrics(residual_histories)})
    rate = run_newton_rate_study(rows)
    return {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "rows": rows, "load_path": [0.25, 0.5, 0.75, 1.0], "newton_rate_study": rate}


def multi_element_mesh(element_type: str) -> tuple[np.ndarray, list[list[int]]]:
    """Build two connected elements for the common global J2 benchmark."""
    family = str(element_type).upper()
    if family in {"HEX8", "HEX20"}:
        node_ids: dict[tuple[float, float, float], int] = {}
        elements: list[list[int]] = []

        def node_id(point: np.ndarray | tuple[float, float, float]) -> int:
            key = tuple(float(value) for value in point)
            if key not in node_ids:
                node_ids[key] = len(node_ids)
            return node_ids[key]

        edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
        for x0 in (0.0, 1.0):
            corners = np.asarray(
                [[x0, 0, 0], [x0 + 1, 0, 0], [x0 + 1, 1, 0], [x0, 1, 0], [x0, 0, 1], [x0 + 1, 0, 1], [x0 + 1, 1, 1], [x0, 1, 1]],
                dtype=float,
            )
            corner_ids = [node_id(point) for point in corners]
            if family == "HEX8":
                elements.append(corner_ids)
            else:
                midpoint_ids = [node_id(0.5 * (corners[first] + corners[second])) for first, second in edges]
                elements.append(corner_ids + midpoint_ids)
        nodes = np.zeros((len(node_ids), 3), dtype=float)
        for point, index in node_ids.items():
            nodes[index] = point
        return nodes, elements
    if family in {"TET4", "TET10"}:
        corners = np.asarray([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 1]], dtype=float)
        base_elements = ((0, 1, 2, 3), (1, 2, 3, 4))
        if family == "TET4":
            return corners, [list(item) for item in base_elements]
        node_ids = {tuple(point): index for index, point in enumerate(corners)}
        edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
        elements = []
        for element in base_elements:
            midpoint_ids = []
            for first, second in edges:
                point = tuple(0.5 * (corners[element[first]] + corners[element[second]]))
                node_ids.setdefault(point, len(node_ids))
                midpoint_ids.append(node_ids[point])
            elements.append(list(element) + midpoint_ids)
        nodes = np.zeros((len(node_ids), 3), dtype=float)
        for point, index in node_ids.items():
            nodes[index] = point
        return nodes, elements
    raise ValueError(f"Unsupported robustness element {element_type!r}.")


def mesh_refinement_mesh(element_type: str, cells: int) -> tuple[np.ndarray, list[list[int]]]:
    """Build a regular unit-block mesh at one refinement level.

    The topology is shared by all four families: HEX families use the block
    directly, while TET families split each block into five tetrahedra. Higher
    order nodes are generated from globally shared edge midpoints, so the
    comparison exercises the same assembled interface rather than independent
    element samples.
    """
    family = str(element_type).upper()
    if family not in ELEMENT_TYPES:
        raise ValueError(f"Unsupported robustness element {element_type!r}.")
    if isinstance(cells, bool) or not isinstance(cells, int) or cells < 1:
        raise ValueError("Mesh refinement cells must be a positive integer.")

    coordinates: list[tuple[float, float, float]] = []
    node_ids: dict[tuple[float, float, float], int] = {}

    def node_id(point: np.ndarray | tuple[float, float, float]) -> int:
        key = tuple(round(float(value), 14) for value in point)
        if key not in node_ids:
            node_ids[key] = len(coordinates)
            coordinates.append(key)
        return node_ids[key]

    def block_corners(index: int) -> list[int]:
        x0 = index / cells
        x1 = (index + 1) / cells
        points = (
            (x0, 0.0, 0.0),
            (x1, 0.0, 0.0),
            (x1, 1.0, 0.0),
            (x0, 1.0, 0.0),
            (x0, 0.0, 1.0),
            (x1, 0.0, 1.0),
            (x1, 1.0, 1.0),
            (x0, 1.0, 1.0),
        )
        return [node_id(point) for point in points]

    edge_order = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
    tet_corner_templates = ((0, 1, 3, 4), (1, 2, 3, 6), (1, 3, 4, 6), (1, 4, 5, 6), (3, 4, 6, 7))
    elements: list[list[int]] = []
    for index in range(cells):
        corners = block_corners(index)
        if family in {"HEX8", "HEX20"}:
            if family == "HEX8":
                elements.append(corners)
            else:
                mids = [node_id(0.5 * (np.asarray(coordinates[corners[first]]) + np.asarray(coordinates[corners[second]]))) for first, second in edge_order]
                elements.append(corners + mids)
            continue
        for template in tet_corner_templates:
            tet = [corners[position] for position in template]
            signed_volume = Tet4Element.signed_volume(np.asarray([coordinates[item] for item in tet]))
            if signed_volume < 0.0:
                tet[2], tet[3] = tet[3], tet[2]
            if family == "TET4":
                elements.append(tet)
                continue
            mids = [
                node_id(
                    0.5
                    * (
                        np.asarray(coordinates[tet[first]])
                        + np.asarray(coordinates[tet[second]])
                    )
                )
                for first, second in ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
            ]
            elements.append(tet + mids)
    return np.asarray(coordinates, dtype=float), elements


def _refinement_model(element_type: str, cells: int) -> FiniteElementModel:
    nodes, elements = mesh_refinement_mesh(element_type, cells)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": element_type, "nodes": item, "material": "j2"} for item in elements],
        materials={"j2": {"type": "von_mises_elastoplastic_3d", "E": 1000.0, "nu": 0.3, "yield_stress": 0.02, "hardening_modulus": 10.0}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=[{"node": int(node), "dof": "UX", "value": 1.0 / len(loaded_nodes)} for node in loaded_nodes],
        analysis={"type": "nonlinear_static", "method": "newton_raphson", "load_path": [0.25, 0.5, 0.75, 1.0], "max_iterations": 40, "tolerance": 1.0e-7},
    )


def _reaction_norm(result: Any) -> float:
    """Extract the reaction norm without coupling the campaign to an audit type."""
    if result.audit is None:
        return 0.0
    for vector in result.audit.vectors:
        name = vector.get("name", "") if isinstance(vector, dict) else getattr(vector, "name", "")
        if name == "reactions":
            return float(vector.get("norm", 0.0) if isinstance(vector, dict) else vector.norm)
    return 0.0


def run_mesh_refinement_benchmark(
    element_types: tuple[str, ...] = ELEMENT_TYPES,
    levels: tuple[int, ...] = (1, 2, 4),
) -> dict[str, Any]:
    """Record assembled J2 response trends across regular mesh refinements."""
    if not levels or any(level < 1 for level in levels) or tuple(sorted(set(levels))) != levels:
        raise ValueError("Mesh refinement levels must be a non-empty increasing tuple of positive integers.")
    rows: list[dict[str, Any]] = []
    for family in element_types:
        family_rows: list[dict[str, Any]] = []
        for cells in levels:
            started = perf_counter()
            result = solve_model(_refinement_model(family, cells), enforce_policy=False)
            steps = result.to_dict()["solver"]["steps"]
            final = steps[-1]
            von_mises_max = max(
                (float(row.get("von_mises", 0.0)) for row in result.element_results),
                default=0.0,
            )
            family_rows.append(
                {
                    "element": family,
                    "cells_x": cells,
                    "node_count": int(result.node_count),
                    "element_count": int(result.element_count),
                    "dof_count": int(result.displacements.size),
                    "tip_displacement_norm": float(np.linalg.norm(result.displacements)),
                    "reaction_norm": _reaction_norm(result),
                    "von_mises_max": von_mises_max,
                    "peeq_max": float(final["equivalent_plastic_strain_max"]),
                    "plastic_dissipation": float(final["plastic_dissipation_max"]),
                    "energy": float(sum(step["incremental_internal_work"] for step in steps)),
                    "newton_iterations": int(sum(step["iterations"] for step in steps)),
                    "maximum_relative_residual": float(max(step["relative_residual"] for step in steps)),
                    "elapsed_seconds": float(perf_counter() - started),
                    "status": "PASS" if result.status == "PASS" else "FAIL",
                }
            )
        coarse = family_rows[0]
        fine = family_rows[-1]
        fine["change_from_coarse"] = {
            key: abs(float(fine[key]) - float(coarse[key])) / max(abs(float(fine[key])), 1.0e-15)
            for key in ("tip_displacement_norm", "reaction_norm", "von_mises_max", "peeq_max", "energy")
        }
        rows.append({"element": family, "levels": family_rows, "status": "PASS" if all(row["status"] == "PASS" for row in family_rows) else "FAIL"})
    return {
        "status": "PASS_INTERNAL_MESH_REFINEMENT" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "levels": list(levels),
        "rows": rows,
        "owner_acceptance_band_required": True,
        "limitations": [
            "Regular unit-block mesh with a single x refinement direction.",
            "The recorded trends are internal evidence; no convergence threshold is invented.",
            "External solver correlation and physical validation remain separate gates.",
        ],
    }


def run_cyclic_load_benchmark(element_types: tuple[str, ...] = ELEMENT_TYPES) -> dict[str, Any]:
    """Exercise global loading, unloading, reversal and reloading paths."""
    path = [
        0.1,
        0.2,
        0.3,
        0.4,
        0.5,
        0.6,
        0.7,
        0.8,
        0.9,
        1.0,
        0.8,
        0.6,
        0.4,
        0.2,
        0.0,
        -0.1,
        -0.2,
        -0.3,
        -0.4,
        -0.5,
        -0.4,
        -0.3,
        -0.2,
        -0.1,
        0.0,
        0.1,
        0.2,
        0.3,
        0.4,
        0.5,
        0.6,
        0.7,
        0.8,
        0.9,
        1.0,
    ]
    load_scale = 0.2
    rows: list[dict[str, Any]] = []
    for family in element_types:
        model = _multi_element_model(family)
        model.loads = [replace(load, value=load.value * load_scale) for load in model.loads]
        model.analysis = replace(
            model.analysis,
            parameters={**model.analysis.parameters, "load_path": path, "max_iterations": 80},
        )
        result = solve_model(model, enforce_policy=False)
        steps = result.to_dict()["solver"]["steps"]
        peeq_history = [float(step["equivalent_plastic_strain_max"]) for step in steps]
        dissipation_history = [float(step["plastic_dissipation_max"]) for step in steps]
        rows.append(
            {
                "element": family,
                "status": "PASS" if result.status == "PASS" and all(np.isfinite(peeq_history)) else "FAIL",
                "load_path": path,
                "load_scale": load_scale,
                "newton_iterations": int(sum(step["iterations"] for step in steps)),
                "peeq_history": peeq_history,
                "plastic_dissipation_history": dissipation_history,
                "final_peeq": peeq_history[-1],
                "final_plastic_dissipation": dissipation_history[-1],
                "maximum_relative_residual": float(max(step["relative_residual"] for step in steps)),
                "monotonic_peeq": bool(np.all(np.diff(peeq_history) >= -1.0e-12)),
                "monotonic_dissipation": bool(np.all(np.diff(dissipation_history) >= -1.0e-12)),
            }
        )
    return {
        "status": "PASS_INTERNAL_CYCLIC" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "rows": rows,
        "owner_acceptance_band_required": True,
        "limitations": [
            "The current isotropic hardening law is not a cyclic calibration claim.",
            "Bauschinger effects and experimental validation are outside this campaign.",
        ],
    }


def _multi_element_model(element_type: str) -> FiniteElementModel:
    nodes, elements = multi_element_mesh(element_type)
    fixed = [
        {"node": index, "dofs": ["UX", "UY", "UZ"]}
        for index, point in enumerate(nodes)
        if point[0] <= 1.0e-12
    ]
    anchor = next(index for index, point in enumerate(nodes) if np.allclose(point, [1.0, 0.0, 0.0]))
    fixed.append({"node": anchor, "dofs": ["UY", "UZ"]})
    load_node = max(range(len(nodes)), key=lambda index: float(nodes[index, 0]))
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": element_type, "nodes": item, "material": "j2"} for item in elements],
        materials={"j2": {"type": "von_mises_elastoplastic_3d", "E": 1000.0, "nu": 0.3, "yield_stress": 0.02, "hardening_modulus": 10.0}},
        fixed_dofs=fixed,
        loads=[{"node": load_node, "dof": "UX", "value": 1.0}],
        analysis={"type": "nonlinear_static", "method": "newton_raphson", "load_path": [0.25, 0.5, 0.75, 1.0], "max_iterations": 40, "tolerance": 1.0e-7},
    )


def run_multi_element_benchmark() -> dict[str, Any]:
    """Run a connected two-element J2 history through the global solver."""
    rows: list[dict[str, Any]] = []
    for family in ELEMENT_TYPES:
        started = perf_counter()
        result = solve_model(_multi_element_model(family), enforce_policy=False)
        data = result.to_dict()
        steps = data["solver"]["steps"]
        rows.append(
            {
                "element": family,
                "status": "PASS" if result.status == "PASS" else "FAIL",
                "node_count": int(result.node_count),
                "element_count": int(result.element_count),
                "dof_count": int(result.displacements.size),
                "newton_iterations": int(sum(step["iterations"] for step in steps)),
                "maximum_relative_residual": float(max(step["relative_residual"] for step in steps)),
                "final_displacement_norm": float(np.linalg.norm(result.displacements)),
                "final_peeq": float(steps[-1]["equivalent_plastic_strain_max"]),
                "final_plastic_dissipation": float(steps[-1]["plastic_dissipation_max"]),
                "external_work": float(sum(step["incremental_external_work"] for step in steps)),
                "internal_work": float(sum(step["incremental_internal_work"] for step in steps)),
                "maximum_work_imbalance": float(max(step["relative_work_imbalance"] for step in steps)),
                "elapsed_seconds": float(perf_counter() - started),
            }
        )
    return {
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "rows": rows,
        "mesh": "two connected elements with shared interface nodes",
        "limitations": ["This is an internal V&V benchmark; it is not an external correlation or physical validation."],
    }


def _energy_balance_for_result(result: Any) -> dict[str, Any]:
    """Recover global energy terms from one converged nonlinear result.

    The solver already records incremental external and internal work. The
    elastic and plastic terms are reconstructed from committed integration
    point states so this check stays independent of the Newton implementation.
    """

    steps = result.to_dict()["solver"]["steps"]
    external_work = float(sum(float(step["incremental_external_work"]) for step in steps))
    internal_work = float(sum(float(step["incremental_internal_work"]) for step in steps))
    elastic_energy = 0.0
    plastic_dissipation = 0.0
    minimum_point_dissipation = float("inf")
    state_count = 0

    for element_index, element_result in enumerate(result.element_results):
        states = result.material_states.get(element_index, [])
        points = element_result.get("integration_points", [])
        if len(states) != len(points):
            return {
                "status": "FAIL",
                "reason": "integration_point_state_cardinality_mismatch",
                "element": element_index,
                "state_count": len(states),
                "point_count": len(points),
            }
        for point_index, point in enumerate(points):
            state = states[point_index]
            weight = float(point["weight"])
            strain = np.asarray(point["strain"], dtype=float)
            stress = np.asarray(state["stress"], dtype=float)
            plastic_strain = np.asarray(state.get("plastic_strain", np.zeros(6)), dtype=float)
            point_dissipation = float(state.get("plastic_dissipation", 0.0))
            elastic_energy += weight * 0.5 * float((strain - plastic_strain) @ stress)
            plastic_dissipation += weight * point_dissipation
            minimum_point_dissipation = min(minimum_point_dissipation, point_dissipation)
            state_count += 1

    balance_error = external_work - elastic_energy - plastic_dissipation
    relative_balance_error = abs(balance_error) / max(abs(external_work), 1.0e-15)
    finite = all(
        np.isfinite(value)
        for value in (
            external_work,
            internal_work,
            elastic_energy,
            plastic_dissipation,
            balance_error,
            relative_balance_error,
        )
    )
    nonnegative_dissipation = minimum_point_dissipation >= -1.0e-12
    return {
        "status": "PASS_INTERNAL_ENERGY" if finite and nonnegative_dissipation else "FAIL",
        "total_external_work": external_work,
        "total_internal_work": internal_work,
        "elastic_strain_energy": float(elastic_energy),
        "plastic_dissipation": float(plastic_dissipation),
        "absolute_balance_error": float(abs(balance_error)),
        "signed_balance_error": float(balance_error),
        "relative_balance_error": float(relative_balance_error),
        "minimum_point_dissipation": float(minimum_point_dissipation if state_count else 0.0),
        "nonnegative_dissipation": nonnegative_dissipation,
        "integration_point_state_count": state_count,
        "owner_acceptance_band_required": True,
        "limitations": [
            "This is an internal energy-consistency check, not physical validation.",
            "The release acceptance band remains an Owner decision; no release threshold is invented here.",
        ],
    }


def run_energy_balance_benchmark(
    element_types: tuple[str, ...] = ELEMENT_TYPES,
    load_path: tuple[float, ...] = tuple(index / 10.0 for index in range(1, 11)),
) -> dict[str, Any]:
    """Check work, elastic energy and plastic dissipation on all four families."""

    rows: list[dict[str, Any]] = []
    for family in element_types:
        model = _multi_element_model(family)
        model.analysis = replace(
            model.analysis,
            parameters={**model.analysis.parameters, "load_path": list(load_path)},
        )
        result = solve_model(model, enforce_policy=False)
        balance = _energy_balance_for_result(result)
        rows.append(
            {
                "element": family,
                "solver_status": result.status,
                **balance,
                "maximum_relative_residual": float(
                    max(step["relative_residual"] for step in result.to_dict()["solver"]["steps"])
                ),
            }
        )
    return {
        "status": "PASS_INTERNAL_ENERGY" if all(row["status"] == "PASS_INTERNAL_ENERGY" for row in rows) else "FAIL",
        "load_path": list(load_path),
        "rows": rows,
        "owner_acceptance_band_required": True,
    }


def run_adversarial_rollback_benchmark() -> dict[str, Any]:
    """Reject one trial increment and verify clean cutback/retry semantics."""

    model = _multi_element_model("TET4")
    parameters = dict(model.analysis.parameters)
    parameters.pop("load_path", None)
    parameters.update(
        {
            "adaptive_load_steps": True,
            "initial_load_increment": 1.0,
            "min_load_increment": 0.25,
            "max_load_increment": 1.0,
            "cutback_factor": 0.5,
            "growth_factor": 1.0,
        }
    )
    model.analysis = replace(model.analysis, parameters=parameters)

    class RejectFirstTrialSolver(NonlinearStaticSolver):
        """Inject one failure after mutating only the detached trial objects."""

        attempts = 0
        first_displacement_norm = float("nan")
        committed_digest_before_failure = ""
        retry_state_digest = ""
        retry_displacement_norm = float("nan")
        clean_retry = False

        def _solve_load_step(
            self,
            model: FiniteElementModel,
            dofs: Any,
            displacement: np.ndarray,
            free: np.ndarray,
            target_load: np.ndarray,
            material_states: Any,
            step: int,
            load_factor: float,
            load_increment: float,
            cached_tangent: Any,
            max_iterations: int,
            tolerance: float,
            linear_method: str,
            min_alpha: float,
            max_reductions: int,
            armijo: float,
            previous_load: np.ndarray | None = None,
            reference_force_norm: float | None = None,
        ):
            self.attempts += 1
            if self.attempts == 1:
                self.first_displacement_norm = float(np.linalg.norm(displacement))
                self.committed_digest_before_failure = state_digest(material_states)
                displacement[:] = 123.0
                material_states[0][0]["equivalent_plastic_strain"] = 999.0
                raise NumericalConvergenceError("controlled adversarial increment rejection")
            if self.attempts == 2:
                self.retry_state_digest = state_digest(material_states)
                self.retry_displacement_norm = float(np.linalg.norm(displacement))
                self.clean_retry = bool(
                    self.retry_displacement_norm == 0.0
                    and self.retry_state_digest == self.committed_digest_before_failure
                )
            return super()._solve_load_step(
                model,
                dofs,
                displacement,
                free,
                target_load,
                material_states,
                step,
                load_factor,
                load_increment,
                cached_tangent,
                max_iterations,
                tolerance,
                linear_method,
                min_alpha,
                max_reductions,
                armijo,
                previous_load,
                reference_force_norm,
            )

    solver = RejectFirstTrialSolver()
    result = solver.solve(model)

    reference_model = _multi_element_model("TET4")
    reference_model.analysis = replace(
        reference_model.analysis,
        parameters={
            **reference_model.analysis.parameters,
            "load_path": [0.25, 0.5, 0.75, 1.0],
        },
    )
    reference = solve_model(reference_model, enforce_policy=False)
    displacement_error = float(
        np.linalg.norm(result.displacements - reference.displacements)
        / max(np.linalg.norm(reference.displacements), 1.0e-15)
    )
    result_steps = result.to_dict()["solver"]["steps"]
    reference_steps = reference.to_dict()["solver"]["steps"]
    peeq_error = float(
        abs(
            float(result_steps[-1]["equivalent_plastic_strain_max"])
            - float(reference_steps[-1]["equivalent_plastic_strain_max"])
        )
    )
    data = result.to_dict()["solver"]
    return {
        "status": "PASS_INTERNAL_ROLLBACK" if result.status == "PASS" and solver.clean_retry and data["rejected_increments"] == 1 else "FAIL",
        "solver_status": result.status,
        "clean_retry": solver.clean_retry,
        "first_displacement_norm": solver.first_displacement_norm,
        "retry_displacement_norm": solver.retry_displacement_norm,
        "committed_digest_before_failure": solver.committed_digest_before_failure,
        "retry_state_digest": solver.retry_state_digest,
        "rejected_increments": data["rejected_increments"],
        "rejection_log": data["rejection_log"],
        "adaptive_load_path": data["load_path"],
        "reference_load_path": reference.to_dict()["solver"]["load_path"],
        "final_displacement_relative_error": displacement_error,
        "final_peeq_absolute_error": peeq_error,
        "owner_acceptance_band_required": True,
        "limitations": [
            "The first rejection is deterministic fault injection; it is not a material instability claim.",
            "The reference comparison is internal and does not close external correlation gates.",
        ],
    }


def run_finite_kinematic_j2_benchmark(
    element_types: tuple[str, ...] = ELEMENT_TYPES,
) -> dict[str, Any]:
    """Run the bounded Green-Lagrange/J2 candidate through common Newton.

    This is an internal research campaign. It records objectivity and solver
    diagnostics but deliberately does not promote the finite-kinematic model
    to a validated or production capability.
    """
    rows: list[dict[str, Any]] = []
    for family in element_types:
        if family not in ELEMENT_TYPES:
            raise ValueError("Finite-kinematic J2 benchmark supports TET4, TET10, HEX8 and HEX20.")
        model = _refinement_model(family, 1) if family in {"TET4", "TET10", "HEX8"} else _single_high_order_model(family)
        model.analysis = replace(
            model.analysis,
            parameters={
                **model.analysis.parameters,
                "kinematics": "total_lagrangian_j2",
                "load_steps": 3,
            },
        )
        result = solve_model(model, enforce_policy=False)
        data = result.to_dict()
        steps = data["solver"]["steps"]
        point_rows = [
            point
            for element in result.element_results
            for point in element.get("integration_points", [])
        ]
        rotation_residual = _finite_kinematic_rotation_residual(family)
        tangent_fd_error = _finite_kinematic_tangent_error(family)
        rows.append(
            {
                "element": family,
                "status": "PASS" if result.status == "PASS" and rotation_residual < 1.0e-9 and tangent_fd_error < 1.0e-6 else "FAIL",
                "kinematics": "green_lagrange_second_piola",
                "element_count": int(result.element_count),
                "dof_count": int(result.displacements.size),
                "newton_iterations": int(sum(step["iterations"] for step in steps)),
                "maximum_relative_residual": float(max(step["relative_residual"] for step in steps)),
                "final_peeq": float(steps[-1]["equivalent_plastic_strain_max"]),
                "plastic_dissipation": float(steps[-1]["plastic_dissipation_max"]),
                "minimum_det_f": float(min(float(point["det_f"]) for point in point_rows)),
                "rigid_rotation_internal_force_norm": rotation_residual,
                "tangent_fd_relative_error": tangent_fd_error,
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "rows": rows,
        "limitations": [
            "Green-Lagrange J2 is a bounded research model, not general finite-strain plasticity.",
            "HEX20 uses a single-element high-order smoke model; no multi-element HEX20 finite-kinematic claim is made.",
            "The TET10 result uses the existing refined multi-element smoke mesh, but is not an external or mesh-convergence qualification.",
            "No external correlation or physical validation claim is made.",
        ],
    }


def run_finite_kinematic_limit_recovery_benchmark(
    element_types: tuple[str, ...] = ELEMENT_TYPES,
) -> dict[str, Any]:
    """Check recovery of the small-strain path as the load tends to zero."""

    rows: list[dict[str, Any]] = []
    load_factor = 1.0e-4
    for family in element_types:
        if family not in ELEMENT_TYPES:
            raise ValueError("Finite-kinematic limit recovery supports TET4, TET10, HEX8 and HEX20.")
        builder = _refinement_model if family in {"TET4", "TET10", "HEX8"} else _single_high_order_model
        small_model = builder(family, 1) if builder is _refinement_model else builder(family)
        small_model.analysis = replace(
            small_model.analysis,
            parameters={
                **small_model.analysis.parameters,
                "load_path": [load_factor],
                "max_iterations": 40,
                "tolerance": 1.0e-9,
            },
        )
        small_result = solve_model(small_model, enforce_policy=False)
        finite_model = deepcopy(small_model)
        finite_model.analysis = replace(
            finite_model.analysis,
            parameters={
                **finite_model.analysis.parameters,
                "kinematics": "total_lagrangian_j2",
            },
        )
        finite_result = solve_model(finite_model, enforce_policy=False)
        displacement_error = float(
            np.linalg.norm(finite_result.displacements - small_result.displacements)
            / max(np.linalg.norm(small_result.displacements), 1.0e-15)
        )
        small_steps = small_result.to_dict()["solver"]["steps"]
        finite_steps = finite_result.to_dict()["solver"]["steps"]
        rows.append(
            {
                "element": family,
                "status": (
                    "PASS"
                    if small_result.status == "PASS"
                    and finite_result.status == "PASS"
                    and displacement_error < 1.0e-8
                    and float(finite_steps[-1]["equivalent_plastic_strain_max"]) == 0.0
                    else "FAIL"
                ),
                "load_factor": load_factor,
                "small_strain_status": small_result.status,
                "finite_kinematic_status": finite_result.status,
                "small_strain_displacement_norm": float(np.linalg.norm(small_result.displacements)),
                "finite_kinematic_displacement_norm": float(np.linalg.norm(finite_result.displacements)),
                "relative_displacement_error": displacement_error,
                "small_strain_relative_residual": float(small_steps[-1]["relative_residual"]),
                "finite_kinematic_relative_residual": float(finite_steps[-1]["relative_residual"]),
                "finite_kinematic_peeq": float(finite_steps[-1]["equivalent_plastic_strain_max"]),
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if rows and all(row["status"] == "PASS" for row in rows)
        else "FAIL",
        "rows": rows,
        "load_factor": load_factor,
        "comparison": "small_strain_vs_total_lagrangian_j2",
        "owner_acceptance_band_required": True,
        "limitations": [
            "Single small-load recovery point per family; no finite-strain material validation claim.",
            "This is a regime-consistency check and does not close the geometric nonlinearity gate.",
        ],
    }


def _single_high_order_model(element_type: str) -> FiniteElementModel:
    """Build one constrained high-order solid for finite-kinematic smoke V&V."""

    nodes = element_coordinates(element_type)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": element_type, "nodes": list(range(len(nodes))), "material": "j2"}],
        materials={
            "j2": {
                "type": "von_mises_elastoplastic_3d",
                "E": 1000.0,
                "nu": 0.3,
                "yield_stress": 0.02,
                "hardening_modulus": 10.0,
            }
        },
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=[{"node": int(node), "dof": "UX", "value": 1.0 / len(loaded_nodes)} for node in loaded_nodes],
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "load_steps": 3,
            "max_iterations": 40,
            "tolerance": 1.0e-7,
        },
    )


def run_high_order_geometric_benchmark(
    element_types: tuple[str, ...] = ("TET10", "HEX20"),
) -> dict[str, Any]:
    """Exercise the common geometric assembly on connected high-order meshes."""

    rows: list[dict[str, Any]] = []
    for family in element_types:
        if family not in {"TET10", "HEX20"}:
            raise ValueError("High-order geometric benchmark supports TET10 and HEX20.")
        nodes, elements = mesh_refinement_mesh(family, 1)
        fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
        loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
        model = FiniteElementModel.from_raw(
            nodes=nodes.tolist(),
            elements=[{"type": family, "nodes": item, "material": "solid"} for item in elements],
            materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
            fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
            loads=[{"node": int(node), "dof": "UX", "value": 1.0e-4 / len(loaded_nodes)} for node in loaded_nodes],
            analysis={
                "type": "geometric_nonlinear_static",
                "method": "newton_raphson",
                "parameters": {"load_increments": 6, "max_iterations": 30, "tolerance": 1.0e-8},
            },
        )
        result = solve_model(model, enforce_policy=False)
        solver = result.to_dict()["solver"]
        rows.append(
            {
                "element": family,
                "status": "PASS" if result.status == "success" and solver["minimum_det_f"] > 0.0 else "FAIL",
                "element_count": int(result.element_count),
                "dof_count": int(result.displacements.size),
                "newton_iterations": int(sum(step["iterations"] for step in solver["increments"])),
                "maximum_relative_residual": float(max(step["relative_residual"] for step in solver["increments"])),
                "minimum_det_f": float(solver["minimum_det_f"]),
                "strain_energy": float(solver["strain_energy"]),
                "scope": solver["scope"],
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "rows": rows,
        "owner_acceptance_band_required": True,
        "limitations": [
            "Connected one-block high-order smoke only; no large-rotation or mesh-convergence qualification.",
            "The path is elastic Saint-Venant-Kirchhoff geometry, not finite-strain J2 plasticity.",
            "No external correlation or physical validation claim is made.",
        ],
    }


def _large_rotation_model(element_type: str, cells: int, *, load_increments: int = 60, load_scale: float = 1.5) -> tuple[FiniteElementModel, np.ndarray, list[list[int]]]:
    """Build one reproducible large-deflection elastic solid model."""

    nodes, elements = mesh_refinement_mesh(element_type, cells)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": element_type, "nodes": item, "material": "solid"} for item in elements],
        materials={"solid": {"type": "isotropic_3d", "E": 10.0, "nu": 0.3}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=[
            {"node": int(node), "dof": "UZ", "value": load_scale / len(loaded_nodes)}
            for node in loaded_nodes
        ],
        analysis={
            "type": "geometric_nonlinear_static",
            "method": "newton_raphson",
            "parameters": {"load_increments": load_increments, "max_iterations": 100, "tolerance": 1.0e-8},
        },
    )
    return model, nodes, elements


def run_large_rotation_geometric_benchmark(
    element_types: tuple[str, ...] = ("TET4", "HEX8"),
) -> dict[str, Any]:
    """Exercise a bounded large-deflection geometric path for low-order solids.

    A transverse dead load is applied to the right face of a unit block. The
    measured end-line angle is deliberately large enough to exercise the
    geometric tangent while the positive Jacobian and residual checks remain
    explicit. This is an internal elastic research observation, not a
    post-buckling or physical-validation result.
    """

    rows: list[dict[str, Any]] = []
    for family in element_types:
        if family not in {"TET4", "HEX8"}:
            raise ValueError("Large-rotation benchmark supports TET4 and HEX8.")
        model, nodes, elements = _large_rotation_model(family, 1)
        fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
        loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
        result = solve_model(model, enforce_policy=False)
        solver = result.to_dict()["solver"]
        displacement = np.asarray(result.displacements, dtype=float).reshape(-1, 3)
        deformed_nodes = nodes + displacement
        base = np.mean(nodes[fixed_nodes], axis=0)
        tip = np.mean(deformed_nodes[loaded_nodes], axis=0)
        end_vector = tip - base
        end_angle = float(np.arctan2(np.linalg.norm(end_vector[1:]), end_vector[0]))
        increments = solver["increments"]
        rows.append(
            {
                "element": family,
                "status": "PASS"
                if result.status == "success"
                and solver["minimum_det_f"] > 0.0
                and end_angle > 0.5
                and all(np.isfinite(step["relative_residual"]) for step in increments)
                else "FAIL",
                "element_count": int(result.element_count),
                "dof_count": int(result.displacements.size),
                "load_increments": int(solver["load_increments"]),
                "maximum_relative_residual": float(
                    max(step["relative_residual"] for step in increments)
                ),
                "minimum_det_f": float(solver["minimum_det_f"]),
                "maximum_displacement_norm": float(
                    np.linalg.norm(displacement, axis=1).max()
                ),
                "end_line_angle_rad": end_angle,
                "end_line_angle_deg": float(np.degrees(end_angle)),
                "strain_energy": float(solver["strain_energy"]),
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "rows": rows,
        "owner_acceptance_band_required": True,
        "limitations": [
            "One unit-block low-order TET4/HEX8 elastic Saint-Venant-Kirchhoff path.",
            "This is a large-deflection smoke benchmark, not a large-rotation plasticity, post-buckling or external-correlation qualification.",
        ],
    }


def run_large_rotation_mesh_sensitivity_benchmark(
    element_types: tuple[str, ...] = ("TET4", "HEX8"),
    levels: tuple[int, ...] = (1, 2),
    *,
    load_increments: int = 60,
    load_scale: float = 1.0,
) -> dict[str, Any]:
    """Record bounded mesh sensitivity for the common geometric driver."""

    rows: list[dict[str, Any]] = []
    for family in element_types:
        if family not in ELEMENT_TYPES:
            raise ValueError("Large-rotation mesh sensitivity supports TET4, TET10, HEX8 and HEX20.")
        level_rows: list[dict[str, Any]] = []
        for cells in levels:
            model, nodes, _ = _large_rotation_model(
                family,
                cells,
                load_increments=load_increments,
                load_scale=load_scale,
            )
            result = solve_model(model, enforce_policy=False)
            solver = result.to_dict()["solver"]
            displacement = np.asarray(result.displacements, dtype=float).reshape(-1, 3)
            fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
            loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
            base = np.mean(nodes[fixed_nodes], axis=0)
            tip = np.mean((nodes + displacement)[loaded_nodes], axis=0)
            end_vector = tip - base
            end_angle = float(np.arctan2(np.linalg.norm(end_vector[1:]), end_vector[0]))
            increments = solver["increments"]
            level_rows.append(
                {
                    "cells": int(cells),
                    "element": family,
                    "status": "PASS" if result.status == "success" else "FAIL",
                    "element_count": int(result.element_count),
                    "dof_count": int(result.displacements.size),
                    "end_line_angle_rad": end_angle,
                    "end_line_angle_deg": float(np.degrees(end_angle)),
                    "maximum_displacement_norm": float(np.linalg.norm(displacement, axis=1).max()),
                    "minimum_det_f": float(solver["minimum_det_f"]),
                    "strain_energy": float(solver["strain_energy"]),
                    "maximum_relative_residual": float(max(step["relative_residual"] for step in increments)),
                    "newton_iterations": int(sum(step["iterations"] for step in increments)),
                }
            )
        coarse = level_rows[0]
        refined = level_rows[-1]
        rows.append(
            {
                "element": family,
                "status": "PASS_INTERNAL_RESEARCH" if all(row["status"] == "PASS" for row in level_rows) else "FAIL",
                "levels": level_rows,
                "coarse_to_refined": {
                    key: abs(coarse[key] - refined[key]) / max(abs(refined[key]), 1.0e-15)
                    for key in ("end_line_angle_rad", "maximum_displacement_norm", "strain_energy")
                },
                "owner_acceptance_band_required": True,
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if rows and all(row["status"] == "PASS_INTERNAL_RESEARCH" for row in rows) else "FAIL",
        "rows": rows,
        "levels": list(levels),
        "load_scale": float(load_scale),
        "load_increments": int(load_increments),
        "limitations": [
            "Internal elastic mesh sensitivity only; no plasticity or external correlation.",
            "The recorded coarse-to-refined changes are observations and do not define an acceptance band.",
            "The low-order load scale 1.5 smoke is not stable on refined HEX8.",
            "The TET10/HEX20 extension is deliberately limited to the recorded low-load study and remains research evidence.",
        ],
    }


def _finite_kinematic_rotation_residual(element_type: str) -> float:
    """Return the internal-force norm for a rigid rotation of one element."""
    material = j2_material()
    coords = element_coordinates(element_type)
    element_class = {
        "TET4": TotalLagrangianJ2Tet4Element,
        "TET10": TotalLagrangianJ2Tet10Element,
        "HEX8": TotalLagrangianJ2Hex8Element,
        "HEX20": TotalLagrangianJ2Hex20Element,
    }[element_type]
    element = element_class(material)
    angle = 0.7
    rotation = np.asarray(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
    )
    displacement = ((rotation @ coords.T).T - coords).ravel()
    states = [material.initial_state() for _ in range(element.integration_point_count)]
    internal, _, _ = element.internal_force_tangent_state(coords, displacement, states)
    return float(np.linalg.norm(internal))


def _finite_kinematic_tangent_error(element_type: str) -> float:
    """Compare the finite-kinematic element tangent with force differences."""

    material = j2_material()
    coords = element_coordinates(element_type)
    element_class = {
        "TET4": TotalLagrangianJ2Tet4Element,
        "TET10": TotalLagrangianJ2Tet10Element,
        "HEX8": TotalLagrangianJ2Hex8Element,
        "HEX20": TotalLagrangianJ2Hex20Element,
    }[element_type]
    element = element_class(material)
    deformation = np.asarray(
        [[1.04, 0.02, 0.0], [0.01, 0.98, 0.01], [0.0, 0.01, 1.03]],
        dtype=float,
    )
    displacement = ((deformation @ coords.T).T - coords).ravel()
    states = [material.initial_state() for _ in range(element.integration_point_count)]
    _, tangent, _ = element.internal_force_tangent_state(coords, displacement, states)
    numerical = np.zeros_like(tangent)
    step = 1.0e-7
    for column in range(displacement.size):
        perturbation = np.zeros_like(displacement)
        perturbation[column] = step
        plus = element.internal_force_tangent_state(coords, displacement + perturbation, states)[0]
        minus = element.internal_force_tangent_state(coords, displacement - perturbation, states)[0]
        numerical[:, column] = (plus - minus) / (2.0 * step)
    return float(np.linalg.norm(tangent - numerical) / max(np.linalg.norm(numerical), 1.0e-15))


def run_multi_element_load_step_sensitivity(
    element_types: tuple[str, ...] = ELEMENT_TYPES,
) -> dict[str, Any]:
    """Compare coarse, reference and refined load histories on connected meshes."""
    paths = {
        "coarse": [0.5, 1.0],
        "reference": [0.25, 0.5, 0.75, 1.0],
        "refined": [0.125 * index for index in range(1, 9)],
    }
    rows: list[dict[str, Any]] = []
    for family in element_types:
        histories: dict[str, dict[str, float]] = {}
        for name, path in paths.items():
            model = _multi_element_model(family)
            model.analysis = replace(
                model.analysis,
                parameters={**model.analysis.parameters, "load_path": path},
            )
            result = solve_model(model, enforce_policy=False)
            data = result.to_dict()
            steps = data["solver"]["steps"]
            final = steps[-1]
            histories[name] = {
                "displacement_norm": float(np.linalg.norm(result.displacements)),
                "peeq": float(final["equivalent_plastic_strain_max"]),
                "plastic_dissipation": float(final["plastic_dissipation_max"]),
                "maximum_relative_residual": float(max(step["relative_residual"] for step in steps)),
                "iterations": float(sum(step["iterations"] for step in steps)),
            }
        reference = histories["reference"]
        refined = histories["refined"]
        rows.append(
            {
                "element": family,
                "status": "PASS" if all(np.isfinite(list(item.values())).all() for item in histories.values()) else "FAIL",
                "histories": histories,
                "reference_to_refined": {
                    key: abs(reference[key] - refined[key]) / max(abs(refined[key]), 1.0e-15)
                    for key in ("displacement_norm", "peeq", "plastic_dissipation")
                },
                "owner_acceptance_band_required": True,
            }
        )
    return {
        "status": "PASS_INTERNAL_SENSITIVITY" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "paths": paths,
        "rows": rows,
        "limitations": [
            "The function records sensitivity; it does not invent a release tolerance.",
            "Meshes remain the connected two-element internal benchmark.",
        ],
    }


def run_newton_rate_study(reference_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Characterize full Newton against modified Newton without hiding failure."""

    rows = []
    reference_by_family = {row["element"]: row for row in (reference_rows or [])}
    for family in ELEMENT_TYPES:
        exact_row = reference_by_family.get(family)
        exact = None if exact_row is not None else solve_model(_global_model(family)).to_dict()
        modified_model = _global_model(family)
        modified_model.analysis = replace(modified_model.analysis, method="modified_newton")
        try:
            modified = solve_model(modified_model).to_dict()
            modified_histories = [list(map(float, step.get("residual_history", []))) for step in modified["solver"]["steps"]]
            modified_row = {"status": modified["status"], "iterations": int(sum(step["iterations"] for step in modified["solver"]["steps"])), "maximum_relative_residual": float(max(step["relative_residual"] for step in modified["solver"]["steps"])), "residual_histories": modified_histories, "rate_metrics": _newton_rate_metrics(modified_histories)}
        except Exception as error:
            modified_row = {"status": "NON_CONVERGED", "iterations": 30 * 4, "maximum_relative_residual": None, "failure_reason": type(error).__name__, "residual_histories": [], "rate_metrics": _newton_rate_metrics([])}
        if exact_row is not None:
            full_histories = exact_row.get("residual_histories", [])
            full_row = {"status": exact_row["status"], "iterations": exact_row["newton_iterations"], "maximum_relative_residual": exact_row["maximum_relative_residual"], "residual_histories": full_histories, "rate_metrics": exact_row.get("rate_metrics", _newton_rate_metrics(full_histories))}
        else:
            full_histories = [list(map(float, step.get("residual_history", []))) for step in exact["solver"]["steps"]]
            full_row = {"status": exact["status"], "iterations": int(sum(step["iterations"] for step in exact["solver"]["steps"])), "maximum_relative_residual": float(max(step["relative_residual"] for step in exact["solver"]["steps"])), "residual_histories": full_histories, "rate_metrics": _newton_rate_metrics(full_histories)}
        rows.append({"element": family, "full_newton": full_row, "modified_newton": modified_row})
    return {"status": "PASS_CHARACTERIZED" if all(row["full_newton"]["status"] == "PASS" and row["modified_newton"]["status"] in {"PASS", "NON_CONVERGED"} for row in rows) else "FAIL", "rows": rows, "interpretation": "Full Newton is the qualified path; modified Newton is characterized and any non-convergence is explicit."}


def _buckling_model(element_type: str) -> FiniteElementModel:
    """Build the bounded homogeneous model used by the buckling evidence."""

    family = str(element_type).upper()
    if family == "TET4":
        nodes = element_coordinates("TET4")
        fixed = [
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ]
        load_node = 1
    elif family == "HEX8":
        nodes = element_coordinates("HEX8")
        fixed = [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (0, 3, 4, 7)]
        load_node = 1
    elif family in {"TET10", "HEX20"}:
        nodes = element_coordinates(family)
        fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0)).tolist()
        load_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0)).tolist()
        if not fixed_nodes or not load_nodes:
            raise ValueError(f"Cannot construct the bounded {family} buckling boundary planes.")
        fixed = [{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes]
        load_node = int(load_nodes[0])
    else:
        raise ValueError("The bounded buckling campaign supports TET4, TET10, HEX8 and HEX20.")
    load_value = {"TET4": -1.0, "TET10": -0.1, "HEX8": -1.0, "HEX20": -10.0}[family]
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": family, "nodes": list(range(len(nodes))), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=fixed,
        loads=[{"node": load_node, "dof": "UX", "value": load_value}],
        analysis={
            "type": "linear_buckling",
            "method": "eigsh",
            "preload_factor": 1.0,
            "load_increments": 4,
            "maximum_factor": 100.0,
            "eigensolver_tolerance": 1.0e-8,
            "factor_tolerance": 1.0e-4,
        },
    )


def run_linear_buckling_benchmark(
    element_types: tuple[str, ...] = ("TET4", "HEX8"),
) -> dict[str, Any]:
    """Record a bounded sparse tangent-buckling path.

    The default remains TET4/HEX8 for compatibility with the original public
    benchmark. The internal robustness campaign supplies all four supported
    solid families explicitly, including research-only TET10/HEX20 rows.
    """

    rows: list[dict[str, Any]] = []
    for family in element_types:
        model = _buckling_model(family)
        result = solve_model(model, enforce_policy=False)
        data = result.to_dict()
        solver = data["solver"]
        bracket = solver["critical_bracket"]
        formulation = str(solver.get("eigen_formulation", bracket.get("method", "unknown")))
        if formulation == "generalized_eigsh":
            # The generalized solve returns an eigenvalue directly rather
            # than a bisection interval.
            width = 0.0
            relative_width = 0.0
        else:
            width = float(bracket["upper"] - bracket["lower"])
            relative_width = width / max(abs(float(bracket["upper"])), 1.0)
        dofs = model.dof_manager()
        fixed_indices = {
            dofs.index(condition.node, name)
            for condition in model.fixed_dofs
            for name in condition.dofs
        }
        reduced_dof_count = int(result.displacements.size - len(fixed_indices))
        rows.append(
            {
                "element": family,
                "status": "PASS" if result.status == "PASS" and np.isfinite(float(solver["critical_factor"])) else "FAIL",
                "critical_factor": float(solver["critical_factor"]),
                # Keep the historical numeric bracket contract stable;
                # formulation metadata is exported beside it.
                "bracket": {
                    "lower": float(bracket["lower"]),
                    "upper": float(bracket["upper"]),
                },
                "bracket_width": width,
                "relative_bracket_width": relative_width,
                "eigen_formulation": formulation,
                "generalized_fallback_reason": bracket.get("generalized_fallback_reason"),
                "dof_count": int(result.displacements.size),
                "initial_tangent_nnz": int(solver["initial_tangent_nnz"]),
                "geometric_tangent_nnz": int(solver["geometric_tangent_nnz"]),
                "critical_mode_norm": float(solver["critical_mode_norm"]),
                "critical_mode_residual_relative": float(solver["critical_mode_residual_relative"]),
                "critical_mode_free_dof_count": int(solver["critical_mode_free_dof_count"]),
                "eigen_backend": solver["backend"],
                "dense_fallback_possible": reduced_dof_count <= 3,
                "preload_residual": float(
                    max(
                        step["relative_residual"]
                        for step in solver["preload_diagnostics"]["increments"]
                    )
                ),
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "rows": rows,
        "scope": "bounded homogeneous sparse linearized tangent buckling for requested solid families",
        "owner_acceptance_band_required": True,
        "limitations": [
            "This evidence does not close Euler, external-correlation or post-buckling requirements.",
            "The reported factor is the first loss of positive definiteness on the bounded preload path.",
            "TET10 and HEX20 rows are internal research evidence only; no high-order buckling qualification is claimed.",
        ],
    }


def _buckling_mesh_model(element_type: str, cells: int) -> FiniteElementModel:
    """Build one assembled, homogeneous mesh for buckling trend evidence."""

    family = str(element_type).upper()
    nodes, elements = mesh_refinement_mesh(family, cells)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
    if fixed_nodes.size == 0 or loaded_nodes.size == 0:
        raise ValueError(f"Cannot construct the {family} buckling mesh boundary planes.")
    load_value = {"TET4": -1.0, "TET10": -10.0, "HEX8": -1.0, "HEX20": -10.0}[family]
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": family, "nodes": item, "material": "solid"} for item in elements],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=[
            {"node": int(node), "dof": "UX", "value": load_value / len(loaded_nodes)}
            for node in loaded_nodes
        ],
        analysis={
            "type": "linear_buckling",
            "method": "eigsh",
            "preload_factor": 1.0,
            "load_increments": 4,
            "maximum_factor": 100000.0,
            "eigensolver_tolerance": 1.0e-7,
            "factor_tolerance": 1.0e-3,
        },
    )


def run_buckling_mesh_sensitivity_benchmark(
    element_types: tuple[str, ...] = ELEMENT_TYPES,
    levels: tuple[int, ...] = (1, 2),
) -> dict[str, Any]:
    """Record a bounded assembled-mesh buckling sensitivity trend.

    This deliberately reports a coarse-to-medium sensitivity study rather
    than claiming mesh convergence. Every level uses the public sparse
    ``linear_buckling`` route and the same boundary/load convention for a
    given element family.
    """

    if not levels or any(
        isinstance(level, bool) or not isinstance(level, int) or level < 1 for level in levels
    ):
        raise ValueError("Buckling mesh levels must be a non-empty tuple of positive integers.")
    if tuple(sorted(set(levels))) != levels:
        raise ValueError("Buckling mesh levels must be strictly increasing.")
    rows: list[dict[str, Any]] = []
    for family in element_types:
        normalized = str(family).upper()
        family_rows: list[dict[str, Any]] = []
        for cells in levels:
            started = perf_counter()
            try:
                model = _buckling_mesh_model(normalized, cells)
                result = solve_model(model, enforce_policy=False)
                solver = result.solver
                bracket = solver["critical_bracket"]
                bracket_width = float(bracket["upper"] - bracket["lower"])
                family_rows.append(
                    {
                        "element": normalized,
                        "cells_x": cells,
                        "node_count": int(result.node_count),
                        "element_count": int(result.element_count),
                        "dof_count": int(result.displacements.size),
                        "critical_factor": float(solver["critical_factor"]),
                        "bracket_width": bracket_width,
                        "relative_bracket_width": bracket_width
                        / max(abs(float(bracket["upper"])), 1.0),
                        "initial_tangent_nnz": int(solver["initial_tangent_nnz"]),
                        "geometric_tangent_nnz": int(solver["geometric_tangent_nnz"]),
                        "critical_mode_norm": float(solver["critical_mode_norm"]),
                        "critical_mode_residual_relative": float(solver["critical_mode_residual_relative"]),
                        "critical_mode_free_dof_count": int(solver["critical_mode_free_dof_count"]),
                        "preload_residual": float(
                            max(
                                step["relative_residual"]
                                for step in solver["preload_diagnostics"]["increments"]
                            )
                        ),
                        "elapsed_seconds": float(perf_counter() - started),
                        "status": "PASS"
                        if result.status == "PASS" and np.isfinite(float(solver["critical_factor"]))
                        else "FAIL",
                    }
                )
            except Exception as error:
                family_rows.append(
                    {
                        "element": normalized,
                        "cells_x": cells,
                        "status": "FAIL",
                        "failure_reason": type(error).__name__,
                        "failure_message": str(error),
                        "elapsed_seconds": float(perf_counter() - started),
                    }
                )
        if all(row["status"] == "PASS" for row in family_rows):
            coarse = family_rows[0]
            fine = family_rows[-1]
            fine["critical_factor_relative_change"] = abs(
                fine["critical_factor"] - coarse["critical_factor"]
            ) / max(abs(fine["critical_factor"]), 1.0e-15)
            fine["dof_growth"] = fine["dof_count"] / max(coarse["dof_count"], 1)
            fine["nnz_growth"] = fine["initial_tangent_nnz"] / max(
                coarse["initial_tangent_nnz"], 1
            )
        rows.append(
            {
                "element": normalized,
                "levels": family_rows,
                "status": "PASS" if all(row["status"] == "PASS" for row in family_rows) else "FAIL",
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "levels": list(levels),
        "rows": rows,
        "scope": "assembled homogeneous mesh sensitivity for sparse linearized tangent buckling",
        "owner_acceptance_band_required": True,
        "limitations": [
            "Coarse-to-medium trend only; this is not a mesh-convergence closure.",
            "The one-block-in-y/z topology is a bounded structural trend case, not a general column qualification.",
            "No post-buckling continuation or external multi-family correlation is claimed.",
        ],
    }


def run_euler_buckling_benchmark(output_dir: str | Path) -> dict[str, Any]:
    """Run a bounded analytical Euler reference for the TET4 TL route.

    The existing Euler campaign is reused rather than copied into the 0.2.5
    runner. Two medium-to-fine levels keep this evidence suitable for targeted
    execution while retaining a refinement check. It remains internal research
    evidence until external and high-order buckling cells close.
    """
    summary = TotalLagrangianBucklingCampaign(
        output_dir,
        levels=((24, 6, 6), (32, 8, 8)),
    ).run()
    return {
        "status": "PASS_INTERNAL_RESEARCH" if summary["status"] == "PASS_BUCKLING_RESEARCH" else "FAIL",
        "study_id": summary["study_id"],
        "reference": summary["reference"],
        "levels": summary["levels"],
        "checks": summary["checks"],
        "artifacts": [
            "summary.json",
            "report.md",
            "buckling_convergence.png",
            "buckling_mode.png",
        ],
        "owner_acceptance_band_required": True,
        "limitations": [
            "TET4 total-Lagrangian Euler column only; no TET10/HEX8/HEX20 claim.",
            "Bifurcation detection is precritical and does not provide post-buckling continuation.",
            "The result is internal research evidence until external correlation is attached to a clean SHA.",
        ],
    }


def run_arc_length_benchmark() -> dict[str, Any]:
    """Exercise the sparse arc-length continuation path and compare endpoint data."""

    def model_for(method: str) -> FiniteElementModel:
        return FiniteElementModel.from_raw(
            nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
            elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "rubber"}],
            materials={"rubber": {"type": "nonlinear_isotropic_3d", "E": 1000.0, "nu": 0.25, "hardening": 1.0e6}},
            fixed_dofs=[
                {"node": 0, "dofs": ["UX", "UY", "UZ"]},
                {"node": 2, "dofs": ["UX", "UY", "UZ"]},
                {"node": 3, "dofs": ["UX", "UY", "UZ"]},
            ],
            loads=[{"node": 1, "dof": "UX", "value": 10.0}],
            analysis={
                "type": "nonlinear_static",
                "method": method,
                "load_steps": 5,
                "max_iterations": 50,
                "tolerance": 1.0e-9,
                "max_arc_steps": 12,
                "target_load_factor": 1.0,
            },
        )

    arc_model = model_for("arc_length")
    arc_result = solve_model(arc_model, enforce_policy=False)

    reference = solve_model(model_for("newton_raphson"), enforce_policy=False)
    arc_data = arc_result.to_dict()
    steps = arc_data["solver"]["steps"]
    factors = [float(step["load_factor"]) for step in steps]
    residuals = [float(step["relative_residual"]) for step in steps]
    displacement_error = float(
        np.linalg.norm(arc_result.displacements - reference.displacements)
        / max(np.linalg.norm(reference.displacements), 1.0e-15)
    )
    monotone = all(next_factor >= factor - 1.0e-12 for factor, next_factor in zip(factors, factors[1:]))
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if arc_result.status == "PASS" and factors and monotone and np.all(np.isfinite(residuals))
        else "FAIL",
        "method": arc_result.method,
        "load_factors": factors,
        "target_load_factor": 1.0,
        "reached_target": bool(factors and abs(factors[-1] - 1.0) <= 1.0e-3),
        "monotone_load_factor": monotone,
        "step_count": len(steps),
        "maximum_relative_residual": max(residuals, default=float("inf")),
        "residual_histories": [list(map(float, step.get("residual_history", []))) for step in steps],
        "endpoint_displacement_relative_error": displacement_error,
        "owner_acceptance_band_required": True,
        "limitations": [
            "The model is a proportional small-strain nonlinear material path without a snap-through limit point.",
            "This is continuation-path evidence, not a post-buckling or external-validation claim.",
        ],
    }


def run_fem_arc_length_benchmark() -> dict[str, Any]:
    """Record the existing sparse FEM arc-length path as bounded evidence."""

    length = 2.0
    nodes, elements = _structured_tet4_mesh(4, 1, 1, length, 0.5, 0.5)
    nodes[:, 2] += 0.005 * (1.0 - np.cos(0.5 * np.pi * nodes[:, 0] / length))
    assembly = TotalLagrangianTet4Assembly(
        nodes,
        elements,
        SolidMaterial(E=1.0e6, nu=0.3),
    )
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    tip_nodes = np.flatnonzero(np.isclose(nodes[:, 0], length))
    fixed = (3 * fixed_nodes[:, None] + np.arange(3)).reshape(-1)
    reference_load = np.zeros(assembly.ndof, dtype=float)
    reference_load[3 * tip_nodes] = -100.0 / tip_nodes.size
    displacement, history = trace_sparse_arc_length(
        assembly,
        reference_load,
        fixed,
        tip_nodes,
        steps=24,
        initial_load_increment=0.02,
        tolerance=1.0e-8,
    )
    factors = [float(point.load_factor) for point in history]
    residuals = [float(point.relative_residual) for point in history]
    minimum_det_f = min((float(point.minimum_det_f) for point in history), default=float("nan"))
    factor_differences = np.diff(factors)
    turn_count = int(np.count_nonzero((factor_differences[:-1] > 0.0) & (factor_differences[1:] < 0.0)))
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if len(history) == 24
        and factors
        and np.all(np.isfinite(displacement))
        and np.all(np.isfinite(residuals))
        and max(residuals) < 1.0e-7
        and minimum_det_f > 0.99
        else "FAIL",
        "method": "trace_sparse_arc_length",
        "node_count": int(nodes.shape[0]),
        "element_count": int(len(elements)),
        "dof_count": int(assembly.ndof),
        "step_count": len(history),
        "load_factor_range": [min(factors), max(factors)] if factors else [],
        "load_factor_turn_count": turn_count,
        "maximum_relative_residual": max(residuals, default=float("inf")),
        "minimum_det_f": minimum_det_f,
        "final_tip_axial_displacement": float(history[-1].tip_axial_displacement) if history else None,
        "final_tip_lateral_displacement": float(history[-1].tip_lateral_displacement) if history else None,
        "residual_history": residuals,
        "owner_acceptance_band_required": True,
        "limitations": [
            "Existing TET4 total-Lagrangian FEM path, separate from the common nonlinear driver.",
            "This case remains monotone over the bounded window and does not demonstrate a snap-through limit point.",
            "No material plasticity, contact, external correlation or production qualification is claimed.",
        ],
    }


def run_finite_kinematic_arc_length_benchmark(
    element_types: tuple[str, ...] = ELEMENT_TYPES,
) -> dict[str, Any]:
    """Exercise adaptive arc-length on homogeneous J2 solid families."""

    rows: list[dict[str, Any]] = []
    for family in element_types:
        if family not in ELEMENT_TYPES:
            raise ValueError("Finite-kinematic arc-length supports TET4, TET10, HEX8 and HEX20.")
        model = _multi_element_model(family)
        parameters = dict(model.analysis.parameters)
        parameters.pop("load_path", None)
        parameters.update(
            {
                "kinematics": "total_lagrangian_j2",
                "target_load_factor": 0.5,
                "max_arc_steps": 256,
                "arc_length_stop_mode": "target_load",
                "adaptive_arc_length": True,
                "arc_length_growth_factor": 1.5,
                "arc_length_shrink_factor": 0.5,
                "max_arc_length_radius": 0.1,
                "max_iterations": 60,
                "tolerance": 1.0e-7,
            }
        )
        model.analysis = replace(model.analysis, method="arc_length", parameters=parameters)
        result = solve_model(model, enforce_policy=False)
        solver = result.to_dict()["solver"]
        steps = solver["steps"]
        final_factor = float(steps[-1]["load_factor"])
        maximum_relative_residual = float(max(step["relative_residual"] for step in steps))
        final_peeq = float(steps[-1]["equivalent_plastic_strain_max"])
        load_factors = [float(step["load_factor"]) for step in steps]
        radius_history = [
            float(step["arc_length_radius"])
            for step in steps
            if step.get("arc_length_radius") is not None
        ]
        rows.append(
            {
                "element": family,
                "status": (
                    "PASS"
                    if result.status == "PASS"
                    and final_factor >= 0.5 - 1.0e-6
                    and maximum_relative_residual < 1.0e-7
                    and np.isfinite(final_peeq)
                    else "FAIL"
                ),
                "solver_status": result.status,
                "load_factor": load_factors,
                "load_factor_range": [min(load_factors), max(load_factors)],
                "radius_history": radius_history,
                "radius_range": [min(radius_history), max(radius_history)] if radius_history else [],
                "step_count": len(steps),
                "final_load_factor": final_factor,
                "maximum_relative_residual": maximum_relative_residual,
                "final_peeq": final_peeq,
                "adaptive_arc_length": bool(solver["adaptive_arc_length"]),
                "maximum_radius": float(parameters["max_arc_length_radius"]),
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL",
        "method": "arc_length",
        "kinematics": "total_lagrangian_j2",
        "elements": [row["element"] for row in rows],
        "target_load_factor": 0.5,
        "load_factor": rows[0]["load_factor"] if len(rows) == 1 else [],
        "load_factor_ranges": {row["element"]: row["load_factor_range"] for row in rows},
        "radius_ranges": {row["element"]: row["radius_range"] for row in rows},
        "step_count": max((row["step_count"] for row in rows), default=0),
        "final_load_factor": min((row["final_load_factor"] for row in rows), default=float("nan")),
        "maximum_relative_residual": max(
            (row["maximum_relative_residual"] for row in rows), default=float("inf")
        ),
        "final_peeq": max((row["final_peeq"] for row in rows), default=float("nan")),
        "rows": rows,
        "owner_acceptance_band_required": True,
        "limitations": [
            "Bounded monotone adaptive paths for TET4, TET10, HEX8 and HEX20 to load factor 0.5.",
            "This is an internal research proof; no snap-through, snap-back, post-buckling or external correlation is claimed.",
            "The load path is a plastic J2 path, but it is not a physical validation or release qualification.",
        ],
    }


def run_shallow_arch_arc_length_benchmark(
    *,
    steps: int = 80,
    radius: float = 0.05,
    max_iterations: int = 40,
) -> dict[str, Any]:
    """Verify branch following on a reduced shallow-arch equilibrium path.

    The reduced equilibrium equation is ``lambda = u - u**3``.  It has an
    analytically known limit point, so it is useful for testing the
    continuation algebra independently of a particular finite-element
    formulation.  This is algorithmic verification only: it is not a claim
    about a shell or solid shallow-arch discretisation.
    """

    if steps < 4 or max_iterations < 1 or radius <= 0.0:
        raise ValueError("The shallow-arch benchmark requires positive steps, radius and iterations.")
    stiffness = 1.0
    softening = 1.0
    reference_load = 1.0
    load_scale = 1.0
    u = 0.0
    load_factor = 0.0
    previous_du = 0.0
    previous_dlambda = 0.0
    rows: list[dict[str, Any]] = []

    def internal(value: float) -> float:
        return stiffness * value - softening * value**3

    def tangent(value: float) -> float:
        return stiffness - 3.0 * softening * value**2

    for step in range(1, steps + 1):
        base_u = u
        base_lambda = load_factor
        base_tangent = tangent(base_u)
        if abs(base_tangent) > 1.0e-8:
            du_per_lambda = reference_load / base_tangent
        else:
            du_per_lambda = previous_du / previous_dlambda if abs(previous_dlambda) > 1.0e-12 else 0.0
        direction = 1.0
        if previous_dlambda or previous_du:
            direction = 1.0 if du_per_lambda * previous_du + load_scale**2 * previous_dlambda >= 0.0 else -1.0
        delta_lambda = direction * radius / np.sqrt(du_per_lambda**2 + load_scale**2)
        trial_u = base_u + delta_lambda * du_per_lambda
        trial_lambda = base_lambda + delta_lambda
        residual_history: list[float] = []
        converged = False
        relative = float("inf")
        for iteration in range(1, max_iterations + 1):
            residual = reference_load * trial_lambda - internal(trial_u)
            delta_u = trial_u - base_u
            delta_load = trial_lambda - base_lambda
            constraint = delta_u**2 + (load_scale * delta_load) ** 2 - radius**2
            relative = max(abs(residual) / max(abs(reference_load), 1.0), abs(constraint) / radius**2)
            residual_history.append(abs(residual))
            if relative <= 1.0e-10:
                converged = True
                break
            matrix = np.asarray(
                [
                    [tangent(trial_u), -reference_load],
                    [2.0 * delta_u, 2.0 * load_scale**2 * delta_load],
                ],
                dtype=float,
            )
            try:
                correction_u, correction_lambda = np.linalg.solve(
                    matrix, np.asarray([residual, -constraint], dtype=float)
                )
            except np.linalg.LinAlgError as exc:
                raise NumericalConvergenceError(
                    "Reduced shallow-arch arc-length system is singular.",
                    reason="ARC_LENGTH_FAILURE",
                    diagnostics={"step": step, "iteration": iteration},
                ) from exc
            if not np.isfinite(correction_u) or not np.isfinite(correction_lambda):
                raise NumericalConvergenceError(
                    "Reduced shallow-arch arc-length correction is non-finite.",
                    reason="ARC_LENGTH_FAILURE",
                )
            trial_u += float(correction_u)
            trial_lambda += float(correction_lambda)
        if not converged:
            raise NumericalConvergenceError(
                f"Reduced shallow-arch step {step} did not converge.",
                reason="ARC_LENGTH_FAILURE",
                diagnostics={"step": step, "residual_history": residual_history},
            )
        u = float(trial_u)
        load_factor = float(trial_lambda)
        previous_du = u - base_u
        previous_dlambda = load_factor - base_lambda
        rows.append(
            {
                "step": step,
                "displacement": u,
                "load_factor": load_factor,
                "exact_load_factor": internal(u),
                "equilibrium_error": abs(load_factor - internal(u)),
                "iterations": iteration,
                "relative_residual": relative,
                "residual_history": residual_history,
                "tangent": tangent(u),
            }
        )

    factors = [float(row["load_factor"]) for row in rows]
    differences = np.diff(factors)
    limit_point_u = float(np.sqrt(stiffness / (3.0 * softening)))
    limit_point_lambda = float(internal(limit_point_u))
    turn_indices = np.flatnonzero((differences[:-1] > 0.0) & (differences[1:] < 0.0))
    max_equilibrium_error = max(float(row["equilibrium_error"]) for row in rows)
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if rows and turn_indices.size and max_equilibrium_error < 1.0e-8
        else "FAIL",
        "method": "sparse_arc_length_algebra_reduced_order",
        "steps": rows,
        "step_count": len(rows),
        "radius": radius,
        "max_iterations": max_iterations,
        "limit_point_reference": {
            "displacement": limit_point_u,
            "load_factor": limit_point_lambda,
        },
        "limit_point_observed": bool(turn_indices.size),
        "limit_point_step": int(turn_indices[0] + 2) if turn_indices.size else None,
        "maximum_equilibrium_error": max_equilibrium_error,
        "load_factor_range": [min(factors), max(factors)] if factors else [],
        "branch_turn_count": int(turn_indices.size),
        "owner_acceptance_band_required": True,
        "limitations": [
            "Reduced scalar equilibrium equation; no FEM shallow-arch claim.",
            "Internal algorithmic verification only; no external solver correlation.",
            "The result does not qualify snap-through of a production element formulation.",
        ],
    }


def run_common_contact_benchmark() -> dict[str, Any]:
    """Record local unilateral contact and common-driver composition evidence."""

    model = _refinement_model("TET4", 1)
    model.contacts.append(FrictionlessContact(slave_node=1, master_nodes=(0, 3, 4)))
    parameters = dict(model.analysis.parameters)
    parameters.update({"contact_mode": "penalty", "contact_penalty": 1.0e6, "load_steps": 2})
    model.analysis = replace(model.analysis, parameters=parameters)
    dofs = model.dof_manager()
    open_internal, open_tangent, open_details = assemble_penalty_contact(
        model, dofs, np.zeros(dofs.ndof), penalty=1.0e6
    )
    closed = np.zeros(dofs.ndof)
    closed[dofs.index(1, "UX")] = -1.2
    closed_internal, closed_tangent, closed_details = assemble_penalty_contact(
        model, dofs, closed, penalty=1.0e6
    )
    result = solve_model(model, enforce_policy=False)
    updated_model = deepcopy(model)
    updated_model.analysis = replace(
        updated_model.analysis,
        parameters={**updated_model.analysis.parameters, "contact_search_mode": "updated"},
    )
    updated_result = solve_model(updated_model, enforce_policy=False)
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if result.status == "PASS"
        and updated_result.status == "PASS"
        and np.allclose(open_internal, 0.0)
        and open_tangent.nnz == 0
        and closed_details["active_contacts"]
        and closed_tangent.nnz > 0
        else "FAIL",
        "global_solver_status": result.status,
        "updated_global_solver_status": updated_result.status,
        "contact_mode": result.to_dict()["solver"]["contact_mode"],
        "updated_contact_search_mode": "updated",
        "open": open_details,
        "closed": closed_details,
        "open_tangent_nnz": int(open_tangent.nnz),
        "closed_tangent_nnz": int(closed_tangent.nnz),
        "closed_internal_norm": float(np.linalg.norm(closed_internal)),
        "global_max_relative_residual": float(max(step["relative_residual"] for step in result.to_dict()["solver"]["steps"])),
        "updated_global_max_relative_residual": float(max(step["relative_residual"] for step in updated_result.to_dict()["solver"]["steps"])),
        "owner_acceptance_band_required": True,
        "limitations": [
            "Initial-configuration node-to-triangle frictionless penalty only.",
            "No finite-sliding, recontact-search or friction qualification is claimed.",
        ],
    }


def run_contact_tangent_fd_benchmark(
    perturbation_steps: tuple[float, ...] = (1.0e-4, 1.0e-6, 1.0e-8),
) -> dict[str, Any]:
    """Check the fixed-active penalty contact tangent by finite differences.

    The test intentionally freezes the initial master geometry and stays away
    from the active-set boundary. It verifies the smooth local tangent used by
    the common residual assembly, not the non-smooth opening/closing transition
    or a general surface-to-surface formulation.
    """

    if not perturbation_steps or any(
        not np.isfinite(step) or step <= 0.0 for step in perturbation_steps
    ):
        raise ValueError("perturbation_steps must contain finite positive values.")
    model = FiniteElementModel.from_raw(
        nodes=[
            [0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.1, 0.25, 0.25],
        ],
        elements=[],
        materials={},
        fixed_dofs=[],
        loads=[],
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "parameters": {"contact_search_mode": "initial"},
        },
    )
    model.contacts.append(
        FrictionlessContact(
            name="fixed_active_contact",
            slave_node=3,
            master_nodes=(0, 1, 2),
        )
    )
    dofs = model.dof_manager()
    base = np.zeros(dofs.ndof, dtype=float)
    base[dofs.index(3, "UX")] = -0.2
    penalty = 1.0e3
    _, tangent, base_details = assemble_penalty_contact(model, dofs, base, penalty=penalty)
    direction_indices = [
        dofs.index(node, dof)
        for node in range(4)
        for dof in ("UX", "UY", "UZ")
    ]
    rows: list[dict[str, Any]] = []
    for step in perturbation_steps:
        errors: list[float] = []
        for index in direction_indices:
            direction = np.zeros(dofs.ndof, dtype=float)
            direction[index] = 1.0
            plus, _, _ = assemble_penalty_contact(
                model, dofs, base + step * direction, penalty=penalty
            )
            minus, _, _ = assemble_penalty_contact(
                model, dofs, base - step * direction, penalty=penalty
            )
            finite_difference = (plus - minus) / (2.0 * step)
            tangent_direction = tangent @ direction
            denominator = max(
                float(np.linalg.norm(finite_difference)),
                float(np.linalg.norm(tangent_direction)),
                1.0,
            )
            errors.append(
                float(np.linalg.norm(finite_difference - tangent_direction) / denominator)
            )
        rows.append(
            {
                "perturbation_step": float(step),
                "maximum_relative_error": max(errors, default=float("inf")),
                "direction_count": len(direction_indices),
            }
        )
    maximum_error = max(
        (row["maximum_relative_error"] for row in rows), default=float("inf")
    )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if maximum_error <= 1.0e-8 else "FAIL",
        "formulation": "frictionless_penalty_fixed_active_initial_geometry",
        "penalty": penalty,
        "active_contacts": list(base_details["active_contacts"]),
        "base_gap": float(base_details["gaps"][0]),
        "tangent_nnz": int(tangent.nnz),
        "rows": rows,
        "maximum_relative_error": float(maximum_error),
        "owner_acceptance_band_required": True,
        "limitations": [
            "Smooth fixed-active local tangent only; active-set transitions are excluded.",
            "Bounded node-to-triangle penalty contact; no general surface-to-surface claim.",
            "Internal verification only; no external correlation or physical validation claim.",
        ],
    }


def _geometric_contact_model() -> FiniteElementModel:
    """Build a small geometric/contact composition model with fixed master nodes."""

    nodes = [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.9, -0.5, -0.5],
        [0.9, 0.5, -0.5],
        [0.9, -0.5, 0.5],
        [1.0, 0.5, 0.5],
    ]
    fixed_nodes = (0, 2, 3, 4, 5, 6, 7)
    model = FiniteElementModel.from_raw(
        nodes=nodes,
        elements=[
            {"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"},
            {"type": "TET4", "nodes": [4, 5, 6, 7], "material": "solid"},
        ],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=[
            {"node": node, "dofs": ["UX", "UY", "UZ"]}
            for node in fixed_nodes
        ]
        + [{"node": 1, "dofs": ["UY", "UZ"]}],
        loads=[{"node": 1, "dof": "UX", "value": -20.0}],
        analysis={
            "type": "geometric_nonlinear_static",
            "method": "newton_raphson",
            "parameters": {
                "load_increments": 20,
                "max_iterations": 100,
                "tolerance": 1.0e-8,
                "contact_mode": "penalty",
                "contact_penalty": 1.0e5,
                "contact_search_mode": "initial",
            },
        },
    )
    model.contacts.append(
        FrictionlessContact(name="geometric_master", slave_node=1, master_nodes=(4, 5, 6))
    )
    return model


def run_geometric_contact_benchmark() -> dict[str, Any]:
    """Verify geometric Total-Lagrangian assembly plus common penalty contact."""

    result = solve_model(_geometric_contact_model(), enforce_policy=False)
    solver = result.to_dict()["solver"]
    contact = dict(solver.get("contact", {}))
    steps = solver["increments"]
    gaps = list(contact.get("gaps", []))
    maximum_relative_residual = float(max(step["relative_residual"] for step in steps))
    return {
        "status": (
            "PASS_INTERNAL_RESEARCH"
            if result.status == "success"
            and contact.get("active_contacts")
            and gaps
            and float(gaps[0]) < 0.0
            and float(contact.get("maximum_penetration", float("inf"))) < 1.0e-3
            and float(solver["minimum_det_f"]) > 0.0
            and maximum_relative_residual < 1.0e-7
            else "FAIL"
        ),
        "solver_status": result.status,
        "analysis": result.analysis,
        "element_count": int(result.element_count),
        "dof_count": int(result.displacements.size),
        "contact": contact,
        "maximum_relative_residual": maximum_relative_residual,
        "minimum_det_f": float(solver["minimum_det_f"]),
        "strain_energy": float(solver["strain_energy"]),
        "owner_acceptance_band_required": True,
        "limitations": [
            "Two disconnected TET4 blocks with a fixed triangular master patch.",
            "Frictionless node-to-triangle penalty contact only; no surface-to-surface or finite-sliding qualification.",
            "Internal composition evidence only; no external or physical validation claim.",
        ],
    }


def run_contact_recontact_benchmark() -> dict[str, Any]:
    """Exercise open/close/reopen/reclose through one common load path."""

    model = _refinement_model("TET4", 1)
    model.materials["j2"] = {"type": "isotropic_3d", "E": 10.0, "nu": 0.3}
    model.loads = [replace(load, value=-5.0) for load in model.loads]
    model.contacts.append(FrictionlessContact(name="plane", slave_node=1, master_nodes=(0, 3, 4)))
    load_path = [0.25, 1.0, 0.0, 1.0]
    model.analysis = replace(
        model.analysis,
        parameters={
            **model.analysis.parameters,
            "load_path": load_path,
            "contact_mode": "penalty",
            "contact_penalty": 1.0e5,
            "contact_search_mode": "initial",
        },
    )
    result = solve_model(model, enforce_policy=False)
    steps = result.to_dict()["solver"]["steps"]
    active = [bool(step["contact_active_contacts"]) for step in steps]
    gaps = [float(step["contact_gaps"][0]) for step in steps]
    expected = [False, True, False, True]
    residuals = [float(step["relative_residual"]) for step in steps]
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if result.status == "PASS" and active == expected and max(residuals) <= 1.0e-7
        else "FAIL",
        "load_path": load_path,
        "active_by_step": active,
        "expected_active_by_step": expected,
        "gaps_by_step": gaps,
        "maximum_relative_residual": max(residuals),
        "search_mode": "initial",
        "common_driver": True,
        "state_transaction": "no material state; contact active set recomputed per Newton increment",
        "owner_acceptance_band_required": True,
        "limitations": [
            "One elastic TET4 contact path with a fixed planar master triangle.",
            "This verifies common load-path active-set transitions, not finite sliding or friction.",
        ],
    }


def run_contact_penalty_sensitivity_benchmark(
    penalties: tuple[float, ...] = (1.0e2, 1.0e3, 1.0e4, 1.0e5, 1.0e6),
) -> dict[str, Any]:
    """Measure bounded penalty/contact penetration behaviour on one common case.

    This is a conditioning and observability study, not a claim that a
    penalty value is universally acceptable.  The expected internal trend is
    decreasing penetration as the penalty increases while the common Newton
    path remains converged.  The Owner must still define the production
    acceptance band and scaling strategy for contact stiffness.
    """

    if not penalties or any(not np.isfinite(value) or value <= 0.0 for value in penalties):
        raise ValueError("penalties must be a non-empty tuple of finite positive values.")
    ordered = tuple(sorted(float(value) for value in penalties))
    rows: list[dict[str, Any]] = []
    for penalty in ordered:
        model = _refinement_model("TET4", 1)
        model.materials["j2"] = {"type": "isotropic_3d", "E": 10.0, "nu": 0.3}
        model.loads = [replace(load, value=-5.0) for load in model.loads]
        model.contacts.append(FrictionlessContact(slave_node=1, master_nodes=(0, 3, 4)))
        model.analysis = replace(
            model.analysis,
            parameters={
                **model.analysis.parameters,
                "load_path": [1.0],
                "contact_mode": "penalty",
                "contact_penalty": penalty,
                "contact_search_mode": "initial",
            },
        )
        result = solve_model(model, enforce_policy=False)
        solver = result.to_dict()["solver"]
        step = solver["steps"][-1]
        gap = float(step["contact_gaps"][0])
        rows.append(
            {
                "penalty": penalty,
                "solver_status": result.status,
                "converged": result.status == "PASS",
                "maximum_penetration": max(-gap, 0.0),
                "gap": gap,
                "relative_residual": float(step["relative_residual"]),
                "iterations": int(step["iterations"]),
                "active_contacts": list(step["contact_active_contacts"]),
                "contact_tangent_nnz": int(step.get("contact_tangent_nnz", 0)),
            }
        )
    penetrations = [row["maximum_penetration"] for row in rows]
    trend_ok = all(left >= right for left, right in zip(penetrations, penetrations[1:]))
    converged = all(row["converged"] for row in rows)
    finite = all(np.isfinite(row["relative_residual"]) for row in rows)
    return {
        "status": "PASS_INTERNAL_RESEARCH" if trend_ok and converged and finite else "FAIL",
        "rows": rows,
        "penetration_monotone_nonincreasing": trend_ok,
        "common_driver": True,
        "owner_acceptance_band_required": True,
        "limitations": [
            "One TET4 node-to-triangle frictionless penalty case in the initial configuration.",
            "Penalty selection, conditioning and finite-sliding behaviour are not qualified.",
            "No surface-to-surface or external correlation claim is made.",
        ],
    }


def run_contact_surface_search_benchmark() -> dict[str, Any]:
    """Check deterministic selection across a bounded two-face master surface."""

    model = FiniteElementModel.from_raw(
        nodes=[
            [0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 1.0, 1.0],
            [0.0, 0.0, 1.0],
            [0.1, 0.5, 0.5],
        ],
        elements=[],
        materials={},
        fixed_dofs=[],
        loads=[],
        analysis={
            "type": "linear_static",
            "method": "direct",
            "parameters": {"contact_search_mode": "updated"},
        },
    )
    model.contacts.append(
        FrictionlessContact(
            name="two_face_surface",
            slave_node=4,
            master_nodes=(0, 1, 2),
            master_faces=((0, 1, 2), (0, 2, 3)),
        )
    )
    dofs = model.dof_manager()
    face_indices: list[int] = []
    rows: list[dict[str, Any]] = []
    for position in ((0.75, 0.25), (0.25, 0.75)):
        displacement = np.zeros(dofs.ndof, dtype=float)
        displacement[dofs.index(4, "UY")] = position[0] - 0.5
        displacement[dofs.index(4, "UZ")] = position[1] - 0.5
        internal, tangent, details = assemble_penalty_contact(
            model, dofs, displacement, penalty=1.0e6
        )
        face_indices.append(int(details["master_face_indices"][0]))
        rows.append(
            {
                "position_yz": list(position),
                "master_face_index": int(details["master_face_indices"][0]),
                "master_face_count": int(details["master_face_counts"][0]),
                "gap": float(details["gaps"][0]),
                "active_contacts": list(details["active_contacts"]),
                "tangent_nnz": int(tangent.nnz),
                "internal_norm": float(np.linalg.norm(internal)),
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if face_indices == [0, 1]
        and all(row["master_face_count"] == 2 for row in rows)
        and all(not row["active_contacts"] for row in rows)
        else "FAIL",
        "rows": rows,
        "selected_face_indices": face_indices,
        "surface_face_count": 2,
        "common_contact_assembly": True,
        "owner_acceptance_band_required": True,
        "limitations": [
            "Bounded node-to-triangle master surface with two planar faces.",
            "This observes face selection only; it is not a general surface-to-surface or finite-sliding qualification.",
        ],
    }


def run_contact_updated_sliding_benchmark() -> dict[str, Any]:
    """Exercise a controlled multi-face crossing in the common nonlinear driver.

    The case is intentionally small: two connected TET4 elements provide the
    deformable body, while a fixed two-face master surface constrains one
    loaded node. The tangential load moves the projection from face 0 to face
    1 while the normal load closes the contact. This is bounded internal
    evidence for updated local search, not a general finite-sliding claim.
    """

    model = FiniteElementModel.from_raw(
        nodes=[
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.25, 0.5, 0.1],
        ],
        elements=[
            {"type": "TET4", "nodes": [0, 1, 2, 4], "material": "j2"},
            {"type": "TET4", "nodes": [1, 3, 2, 4], "material": "j2"},
        ],
        materials={
            "j2": {
                "type": "von_mises_elastoplastic_3d",
                "E": 10.0,
                "nu": 0.3,
                "yield_stress": 1.0e9,
                "hardening_modulus": 10.0,
            }
        },
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(4)],
        loads=[
            {"node": 4, "dof": "UX", "value": 5.0},
            {"node": 4, "dof": "UZ", "value": -5.0},
        ],
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "load_path": [0.25, 0.5, 0.75, 1.0],
            "max_iterations": 60,
            "tolerance": 1.0e-8,
            "contact_mode": "penalty",
            "contact_penalty": 1.0e5,
            "contact_search_mode": "updated",
            "contact_search_max_iterations": 20,
        },
    )
    model.contacts.append(
        FrictionlessContact(
            name="updated_sliding_surface",
            slave_node=4,
            master_nodes=(0, 1, 2),
            master_faces=((0, 1, 2), (1, 3, 2)),
        )
    )
    result = solve_model(model, enforce_policy=False)
    solver = result.to_dict()["solver"]
    steps = solver["steps"]
    face_sequence = [list(step.get("contact_master_face_indices", [])) for step in steps]
    gaps = [float(step.get("contact_gaps", [0.0])[0]) for step in steps]
    residuals = [float(step["relative_residual"]) for step in steps]
    expected_faces = [[0], [0], [1], [1]]
    finite = bool(
        all(np.isfinite(value) for value in gaps + residuals)
        and np.all(np.isfinite(result.displacements))
    )
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if result.status == "PASS" and face_sequence == expected_faces and finite
        else "FAIL",
        "solver_status": result.status,
        "common_driver": True,
        "search_mode": "updated",
        "load_path": [0.25, 0.5, 0.75, 1.0],
        "face_sequence": face_sequence,
        "expected_face_sequence": expected_faces,
        "face_switch_count": sum(
            left != right for left, right in zip(face_sequence, face_sequence[1:])
        ),
        "gaps": gaps,
        "maximum_penetration": max(-min(gaps, default=0.0), 0.0),
        "maximum_relative_residual": max(residuals, default=0.0),
        "iterations": int(sum(step["iterations"] for step in steps)),
        "final_slave_displacement": result.displacements[
            [result.dofs.index(4, dof) for dof in ("UX", "UY", "UZ")]
        ].tolist(),
        "owner_acceptance_band_required": True,
        "limitations": [
            "Two connected TET4 elements and one fixed two-face planar master surface.",
            "This verifies a bounded updated local face crossing, not general finite sliding, surface-to-surface contact or external correlation.",
        ],
    }


def run_contact_finite_sliding_benchmark() -> dict[str, Any]:
    """Record the bounded clamped-projection contract on a two-face surface.

    The slave point is deliberately placed just outside each side of a square
    master surface.  The opt-in finite-sliding path must retain the closest
    triangle, mark the projection as clamped, preserve the normal gap and
    assemble a sparse penalty tangent.  This is direct assembly evidence for
    the bounded node-to-triangle approximation; it is not a general contact
    or physical validation claim.
    """

    master_nodes = np.asarray(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]],
        dtype=float,
    )
    slave_reference = np.asarray([1.2, 0.25, -0.1], dtype=float)
    model = FiniteElementModel.from_raw(
        nodes=np.vstack([master_nodes, slave_reference]).tolist(),
        elements=[],
        materials={},
        fixed_dofs=[],
        loads=[],
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "parameters": {
                "contact_search_mode": "updated",
                "contact_finite_sliding": True,
            },
        },
    )
    model.contacts.append(
        FrictionlessContact(
            name="finite_sliding_surface",
            slave_node=4,
            master_nodes=(0, 1, 2),
            master_faces=((0, 1, 2), (0, 2, 3)),
        )
    )
    dofs = model.dof_manager()
    positions = (
        np.asarray([1.2, 0.25, -0.1], dtype=float),
        np.asarray([0.25, 1.2, -0.1], dtype=float),
    )
    rows: list[dict[str, Any]] = []
    for position in positions:
        displacement = np.zeros(dofs.ndof, dtype=float)
        displacement[[dofs.index(4, dof) for dof in ("UX", "UY", "UZ")]] = position - slave_reference
        internal, tangent, details = assemble_penalty_contact(
            model, dofs, displacement, penalty=1.0e3
        )
        rows.append(
            {
                "position": position.tolist(),
                "master_face_index": int(details["master_face_indices"][0]),
                "projection_clamped": bool(details["projection_clamped"][0]),
                "gap": float(details["gaps"][0]),
                "closest_distance": float(details["closest_distances"][0]),
                "active_contacts": list(details["active_contacts"]),
                "tangent_nnz": int(tangent.nnz),
                "internal_norm": float(np.linalg.norm(internal)),
            }
        )
    faces = [row["master_face_index"] for row in rows]
    status = (
        "PASS_INTERNAL_RESEARCH"
        if faces == [0, 1]
        and all(row["projection_clamped"] for row in rows)
        and all(row["gap"] == -0.1 for row in rows)
        and all(row["active_contacts"] == [0] for row in rows)
        and all(row["tangent_nnz"] > 0 for row in rows)
        and all(np.isfinite(row["closest_distance"]) for row in rows)
        else "FAIL"
    )
    return {
        "status": status,
        "search_mode": "updated",
        "finite_sliding": True,
        "projection_mode": "bounded_closest_point_node_to_triangle",
        "rows": rows,
        "selected_face_indices": faces,
        "face_switch_count": int(faces[0] != faces[1]),
        "common_sparse_assembly": True,
        "owner_acceptance_band_required": True,
        "limitations": [
            "Opt-in bounded projection on a fixed two-face planar master surface.",
            "No continuous large-sliding, surface-to-surface, friction or external correlation claim.",
        ],
    }


def run_multifamily_coupled_geometry_benchmark() -> dict[str, Any]:
    """Exercise connected J2 plus geometric nonlinearity on all solid families."""

    rows: list[dict[str, Any]] = []
    for family in ELEMENT_TYPES:
        model = _multi_element_model(family)
        model.analysis = replace(
            model.analysis,
            parameters={
                **model.analysis.parameters,
                "kinematics": "total_lagrangian_j2",
                "load_steps": 2,
            },
        )
        result = solve_model(model, enforce_policy=False)
        solver = result.to_dict()["solver"]
        steps = solver["steps"]
        rows.append(
            {
                "element": family,
                "status": "PASS" if result.status == "PASS" else "FAIL",
                "solver_status": result.status,
                "kinematics": solver["kinematics"],
                "contact_mode": solver["contact_mode"],
                "newton_iterations": int(sum(step["iterations"] for step in steps)),
                "step_count": len(steps),
                "maximum_relative_residual": float(max(step["relative_residual"] for step in steps)),
                "final_displacement_norm": float(np.linalg.norm(result.displacements)),
                "final_peeq": float(steps[-1]["equivalent_plastic_strain_max"]),
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "rows": rows,
        "shared_driver": True,
        "shared_residual_and_tangent": True,
        "owner_acceptance_band_required": True,
        "limitations": [
            "Two connected elements per family and no contact contribution.",
            "Internal research evidence only; no external coupled correlation or physical validation claim.",
            "The contact-coupled cases remain the bounded TET4 observations in the companion campaign.",
        ],
    }


def run_multifamily_coupled_contact_benchmark() -> dict[str, Any]:
    """Exercise finite-kinematic penalty contact on all four solid families.

    The body is deliberately reduced to one regular block per family.  A
    fixed triangular master surface is placed just in front of one loaded
    corner, so the same common ``total_lagrangian_j2`` residual/tangent path
    must cross from open to active contact for TET4, TET10, HEX8 and HEX20.
    This is composition evidence only; it is not a general surface-contact
    qualification.
    """

    rows: list[dict[str, Any]] = []
    load_path = [float(value) for value in np.linspace(0.02, 1.0, 50)]
    for family in ELEMENT_TYPES:
        try:
            nodes, elements = mesh_refinement_mesh(family, 1)
            nodes = np.asarray(nodes, dtype=float).copy()
            nodes[:, 0] *= 0.2
            slave = int(np.flatnonzero(np.isclose(nodes[:, 0], 0.2))[0])
            master_start = len(nodes)
            master_nodes = (master_start, master_start + 1, master_start + 2)
            nodes = np.vstack(
                (
                    nodes,
                    np.asarray(
                        [[0.19, -0.5, -0.5], [0.19, 0.5, -0.5], [0.19, 0.0, 0.5]],
                        dtype=float,
                    ),
                )
            )
            fixed_dofs = [
                {"node": node, "dofs": ["UX", "UY", "UZ"]}
                for node in range(len(nodes))
                if node != slave
            ]
            fixed_dofs.append({"node": slave, "dofs": ["UY", "UZ"]})
            model = FiniteElementModel.from_raw(
                nodes=nodes.tolist(),
                elements=[
                    {"type": family, "nodes": item, "material": "j2"}
                    for item in elements
                ],
                materials={
                    "j2": {
                        "type": "von_mises_elastoplastic_3d",
                        "E": 10.0,
                        "nu": 0.3,
                        "yield_stress": 0.02,
                        "hardening_modulus": 10.0,
                    }
                },
                fixed_dofs=fixed_dofs,
                loads=[{"node": slave, "dof": "UX", "value": -1.0}],
                analysis={
                    "type": "nonlinear_static",
                    "method": "newton_raphson",
                    "load_path": load_path,
                    "max_iterations": 100,
                    "tolerance": 1.0e-8,
                    "kinematics": "total_lagrangian_j2",
                    "contact_mode": "penalty",
                    "contact_penalty": 1.0e6,
                    "contact_search_mode": "updated",
                    "contact_max_penetration": 5.0e-3,
                },
            )
            model.contacts.append(
                FrictionlessContact(
                    name="nearby_master_plane",
                    slave_node=slave,
                    master_nodes=master_nodes,
                    master_faces=(master_nodes,),
                )
            )
            result = solve_model(model, enforce_policy=False)
            steps = result.to_dict()["solver"]["steps"]
            gaps = [float(step["contact_gaps"][0]) for step in steps]
            residuals = [float(step["relative_residual"]) for step in steps]
            active_steps = sum(bool(step["contact_active_contacts"]) for step in steps)
            maximum_penetration = max(-min(gaps, default=0.0), 0.0)
            final_peeq = float(steps[-1]["equivalent_plastic_strain_max"])
            row_status = (
                result.status == "PASS"
                and active_steps > 0
                and gaps[0] > 0.0
                and gaps[-1] < 0.0
                and maximum_penetration < 1.0e-4
                and max(residuals) < 1.0e-7
                and final_peeq > 0.0
            )
            rows.append(
                {
                    "element": family,
                    "status": "PASS" if row_status else "FAIL",
                    "solver_status": result.status,
                    "kinematics": "total_lagrangian_j2",
                    "contact_mode": "penalty",
                    "contact_search_mode": "updated",
                    "node_count": int(len(nodes)),
                    "element_count": int(len(elements)),
                    "active_step_count": int(active_steps),
                    "step_count": len(steps),
                    "initial_gap": gaps[0],
                    "final_gap": gaps[-1],
                    "maximum_penetration": maximum_penetration,
                    "maximum_relative_residual": max(residuals),
                    "newton_iterations": int(sum(step["iterations"] for step in steps)),
                    "final_peeq": final_peeq,
                    "final_slave_displacement": result.displacements[
                        [result.dofs.index(slave, dof) for dof in ("UX", "UY", "UZ")]
                    ].tolist(),
                }
            )
        except Exception as error:  # pragma: no cover - retained as explicit campaign evidence
            rows.append(
                {
                    "element": family,
                    "status": "FAIL",
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            )
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if rows and all(row["status"] == "PASS" for row in rows)
        else "FAIL",
        "rows": rows,
        "shared_driver": True,
        "shared_residual_and_tangent": True,
        "load_path": load_path,
        "owner_acceptance_band_required": True,
        "limitations": [
            "One regular block and one fixed triangular master plane per family.",
            "The small-strain J2 hardening law is active, but this remains a bounded composition case rather than a material qualification.",
            "This does not qualify general surface-to-surface contact, finite sliding, friction or external correlation.",
        ],
    }


def run_coupling_benchmark() -> dict[str, Any]:
    """Exercise the common driver with pairwise and triple nonlinear couplings.

    This is deliberately a bounded internal composition check.  It verifies
    that material, geometric and penalty-contact contributions coexist in one
    residual/tangent path; it does not qualify large deformation, contact
    search, or external physical behaviour.
    """

    cases = (
        ("j2_plus_geometry", {"kinematics": "total_lagrangian_j2"}, False),
        (
            "geometry_plus_contact",
            {
                "kinematics": "total_lagrangian_j2",
                "contact_mode": "penalty",
                "contact_penalty": 1.0e6,
            },
            True,
        ),
        (
            "j2_geometry_plus_updated_contact",
            {
                "kinematics": "total_lagrangian_j2",
                "contact_mode": "penalty",
                "contact_search_mode": "updated",
                "contact_penalty": 1.0e6,
            },
            True,
        ),
    )
    rows: list[dict[str, Any]] = []
    for name, updates, with_contact in cases:
        model = _multi_element_model("TET4")
        if with_contact:
            model.loads = [replace(load, value=-load.value) for load in model.loads]
            model.contacts.append(FrictionlessContact(slave_node=4, master_nodes=(1, 2, 3)))
        model.analysis = replace(
            model.analysis,
            parameters={**model.analysis.parameters, **updates, "load_steps": 2},
        )
        result = solve_model(model, enforce_policy=False)
        solver = result.to_dict()["solver"]
        steps = solver["steps"]
        rows.append(
            {
                "case": name,
                "status": "PASS" if result.status == "PASS" else "FAIL",
                "solver_status": result.status,
                "kinematics": solver["kinematics"],
                "contact_mode": solver["contact_mode"],
                "contact_search_mode": solver["contact_search_mode"],
                "newton_iterations": int(sum(step["iterations"] for step in steps)),
                "step_count": len(steps),
                "maximum_relative_residual": float(max(step["relative_residual"] for step in steps)),
                "final_displacement_norm": float(np.linalg.norm(result.displacements)),
                "final_peeq": float(steps[-1]["equivalent_plastic_strain_max"]),
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "rows": rows,
        "shared_driver": True,
        "shared_residual_and_tangent": True,
        "owner_acceptance_band_required": True,
        "limitations": [
            "One bounded two-element TET4 composition model only.",
            "Penalty contact is frictionless and limited to initial or updated local geometry.",
            "No multi-element coupled qualification, finite sliding, friction or external correlation is claimed.",
        ],
    }


class RobustnessQualificationCampaign:
    """Produce the internal evidence package for the robustness work packages."""

    campaign_id = CAMPAIGN_ID

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        constitutive = run_constitutive_paths()
        tangent = tangent_finite_difference()
        transactions = transaction_check()
        elements = run_element_matrix()
        benchmark = run_common_global_benchmark()
        multi_element = run_multi_element_benchmark()
        energy_balance = run_energy_balance_benchmark()
        adversarial_rollback = run_adversarial_rollback_benchmark()
        mesh_refinement = run_mesh_refinement_benchmark()
        cyclic = run_cyclic_load_benchmark()
        buckling = run_linear_buckling_benchmark(ELEMENT_TYPES)
        buckling_mesh_sensitivity = run_buckling_mesh_sensitivity_benchmark()
        euler_buckling = run_euler_buckling_benchmark(self.output_dir / "euler_buckling")
        arc_length = run_arc_length_benchmark()
        fem_arc_length = run_fem_arc_length_benchmark()
        finite_kinematic_arc_length = run_finite_kinematic_arc_length_benchmark()
        shallow_arch = run_shallow_arch_arc_length_benchmark()
        contact = run_common_contact_benchmark()
        contact_tangent_fd = run_contact_tangent_fd_benchmark()
        contact_recontact = run_contact_recontact_benchmark()
        contact_penalty_sensitivity = run_contact_penalty_sensitivity_benchmark()
        contact_surface_search = run_contact_surface_search_benchmark()
        contact_updated_sliding = run_contact_updated_sliding_benchmark()
        contact_finite_sliding = run_contact_finite_sliding_benchmark()
        geometric_contact = run_geometric_contact_benchmark()
        multifamily_coupled_geometry = run_multifamily_coupled_geometry_benchmark()
        multifamily_coupled_contact = run_multifamily_coupled_contact_benchmark()
        coupling = run_coupling_benchmark()
        finite_kinematic = run_finite_kinematic_j2_benchmark()
        finite_kinematic_limit = run_finite_kinematic_limit_recovery_benchmark()
        geometric_high_order = run_high_order_geometric_benchmark()
        large_rotation = run_large_rotation_geometric_benchmark()
        large_rotation_mesh_sensitivity = run_large_rotation_mesh_sensitivity_benchmark()
        high_order_large_rotation_mesh_sensitivity = run_large_rotation_mesh_sensitivity_benchmark(
            ("TET10", "HEX20"),
            load_increments=20,
            load_scale=0.25,
        )
        failure_campaign = run_failure_campaign()
        external = _archived_external_correlation()
        internal_items = (constitutive, tangent, transactions, elements, benchmark, multi_element, energy_balance, adversarial_rollback, mesh_refinement, cyclic, buckling, buckling_mesh_sensitivity, euler_buckling, arc_length, fem_arc_length, finite_kinematic_arc_length, shallow_arch, contact, contact_tangent_fd, contact_recontact, contact_penalty_sensitivity, contact_surface_search, contact_updated_sliding, contact_finite_sliding, geometric_contact, multifamily_coupled_geometry, multifamily_coupled_contact, coupling, finite_kinematic, finite_kinematic_limit, geometric_high_order, large_rotation, large_rotation_mesh_sensitivity, high_order_large_rotation_mesh_sensitivity, failure_campaign)
        summary: dict[str, Any] = {
            "campaign_id": self.campaign_id,
            "status": "PASS_INTERNAL" if all(str(item["status"]).startswith("PASS") for item in internal_items) else "FAIL",
            "maturity": "experimental",
            "scope": {"elements": list(ELEMENT_TYPES), "material": "small-strain J2 isotropic hardening", "external_correlation": external["status"], "large_scale_claim": False},
            "constitutive_paths": constitutive,
            "consistent_tangent": tangent,
            "transactions": transactions,
            "element_matrix": elements,
            "common_global_benchmark": benchmark,
            "multi_element_benchmark": multi_element,
            "energy_balance": energy_balance,
            "adversarial_rollback": adversarial_rollback,
            "mesh_refinement_benchmark": mesh_refinement,
            "cyclic_load_benchmark": cyclic,
            "buckling_benchmark": buckling,
            "buckling_mesh_sensitivity_benchmark": buckling_mesh_sensitivity,
            "euler_buckling_benchmark": euler_buckling,
            "arc_length_benchmark": arc_length,
            "fem_arc_length_benchmark": fem_arc_length,
            "finite_kinematic_arc_length_benchmark": finite_kinematic_arc_length,
            "shallow_arch_arc_length_benchmark": shallow_arch,
            "common_contact_benchmark": contact,
            "contact_tangent_fd_benchmark": contact_tangent_fd,
            "contact_recontact_benchmark": contact_recontact,
            "contact_penalty_sensitivity_benchmark": contact_penalty_sensitivity,
            "contact_surface_search_benchmark": contact_surface_search,
            "contact_updated_sliding_benchmark": contact_updated_sliding,
            "contact_finite_sliding_benchmark": contact_finite_sliding,
            "geometric_contact_benchmark": geometric_contact,
            "multifamily_coupled_geometry_benchmark": multifamily_coupled_geometry,
            "multifamily_coupled_contact_benchmark": multifamily_coupled_contact,
            "coupling_benchmark": coupling,
            "finite_kinematic_j2_benchmark": finite_kinematic,
            "finite_kinematic_limit_recovery_benchmark": finite_kinematic_limit,
            "high_order_geometric_benchmark": geometric_high_order,
            "large_rotation_geometric_benchmark": large_rotation,
            "large_rotation_mesh_sensitivity_benchmark": large_rotation_mesh_sensitivity,
            "high_order_large_rotation_mesh_sensitivity_benchmark": high_order_large_rotation_mesh_sensitivity,
            "failure_campaign": failure_campaign,
            "external_correlations": external,
            "limitations": ["Small-strain J2 only.", "Mesh refinement and cyclic paths are internal evidence and require Owner acceptance bands before gate closure.", "The bounded RQ-G08 external archive remains one affine element per family.", "No physical validation claim is made."],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._write_report(summary)
        self._write_plots(summary)
        return summary

    def _write_report(self, summary: dict[str, Any]) -> None:
        lines = [f"# {self.campaign_id}", "", f"Statut interne : **{summary['status']}**", "", "## Matrice elementaire", "", "| Element | Points Gauss | Distordu | Statut |", "| --- | ---: | --- | --- |"]
        for row in summary["element_matrix"]["rows"]:
            lines.append(f"| {row['element']} | {row['integration_points']} | {row['distorted']} | {row['status']} |")
        lines.extend(["", "## Benchmark global", "", "| Element | Iterations Newton | Residu max | PEEQ final | Reaction | Temps (s) |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
        for row in summary["common_global_benchmark"]["rows"]:
            lines.append(f"| {row['element']} | {row['newton_iterations']} | {row['maximum_relative_residual']:.3e} | {row['final_peeq']:.3e} | {row['reaction_norm']:.3e} | {row['elapsed_seconds']:.3f} |")
        lines.extend(["", "## Taux de convergence Newton observe", "", "Les ratios sont calcules entre residus consecutifs. Les ordres observes sont descriptifs et ne constituent pas un seuil de qualification.", "", "| Element | Historiques | Monotone | Ratio final max | Ordre observe |", "| --- | ---: | --- | ---: | ---: |"])
        for row in summary["common_global_benchmark"]["rows"]:
            metrics = row["rate_metrics"]
            orders = [value for history in metrics["observed_order_estimates"] for value in history]
            final_ratios = [value for value in metrics["final_reduction_ratios"] if value is not None]
            lines.append(f"| {row['element']} | {metrics['history_count']} | {metrics['monotone_nonincreasing']} | {max(final_ratios, default=float('nan')):.3e} | {max(orders, default=float('nan')):.3f} |")
        lines.extend(["", "| Element | Full Newton | Modified Newton |", "| --- | --- | --- |"])
        for row in summary["common_global_benchmark"]["newton_rate_study"]["rows"]:
            lines.append(f"| {row['element']} | {row['full_newton']['status']} ({row['full_newton']['iterations']} iter.) | {row['modified_newton']['status']} ({row['modified_newton']['iterations']} iter.) |")
        lines.extend(["", "## Benchmark global multi-element", "", "| Element | Noeuds | Elements | DDL | Iterations Newton | Residu max | PEEQ final | Dissipation plastique |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"])
        for row in summary["multi_element_benchmark"]["rows"]:
            lines.append(f"| {row['element']} | {row['node_count']} | {row['element_count']} | {row['dof_count']} | {row['newton_iterations']} | {row['maximum_relative_residual']:.3e} | {row['final_peeq']:.3e} | {row['final_plastic_dissipation']:.3e} |")
        lines.extend(["", "## Bilan energetique", "", "| Element | W externe | U elastique | D plastique | Erreur relative | Dissipation non negative |", "| --- | ---: | ---: | ---: | ---: | --- |"])
        for row in summary["energy_balance"]["rows"]:
            lines.append(f"| {row['element']} | {row['total_external_work']:.6e} | {row['elastic_strain_energy']:.6e} | {row['plastic_dissipation']:.6e} | {row['relative_balance_error']:.3e} | {row['nonnegative_dissipation']} |")
        lines.extend(["", "## Rollback adversarial", "", f"Statut : **{summary['adversarial_rollback']['status']}**", "", f"Retry propre : `{summary['adversarial_rollback']['clean_retry']}`", f"Increments rejetes : `{summary['adversarial_rollback']['rejected_increments']}`", f"Erreur displacement vs reference : `{summary['adversarial_rollback']['final_displacement_relative_error']:.3e}`", f"Erreur PEEQ finale vs reference : `{summary['adversarial_rollback']['final_peeq_absolute_error']:.3e}`"])
        lines.extend(["", "## Raffinement maillage", "", "Les variations coarse/fine sont archivees sans seuil automatique.", ""])
        for family in summary["mesh_refinement_benchmark"]["rows"]:
            finest = family["levels"][-1]
            lines.append(f"- {family['element']}: niveaux {[row['cells_x'] for row in family['levels']]}, DDL fin {finest['dof_count']}, variation coarse/fine deplacement `{finest['change_from_coarse']['tip_displacement_norm']:.3e}`")
        lines.extend(["", "## Chargement cyclique", "", "| Element | PEEQ final | Dissipation finale | Residu max |", "| --- | ---: | ---: | ---: |"])
        for row in summary["cyclic_load_benchmark"]["rows"]:
            lines.append(f"| {row['element']} | {row['final_peeq']:.3e} | {row['final_plastic_dissipation']:.3e} | {row['maximum_relative_residual']:.3e} |")
        lines.extend(["", "## Stabilité, continuation et contact", "", f"Buckling : **{summary['buckling_benchmark']['status']}**", "", "| Element | Facteur critique | Formulation | Bracket relatif | Résidu mode | Tangente initiale nnz |", "| --- | ---: | --- | ---: | ---: | ---: |"])
        for row in summary["buckling_benchmark"]["rows"]:
            lines.append(f"| {row['element']} | {row['critical_factor']:.6e} | {row['eigen_formulation']} | {row['relative_bracket_width']:.3e} | {row['critical_mode_residual_relative']:.3e} | {row['initial_tangent_nnz']} |")
        buckling_trend = summary["buckling_mesh_sensitivity_benchmark"]
        trend_changes = {
            row["element"]: row["levels"][-1].get("critical_factor_relative_change")
            for row in buckling_trend["rows"]
        }
        lines.append(
            f"Sensibilite maillage buckling : **{buckling_trend['status']}**, "
            f"niveaux `{buckling_trend['levels']}`, variation facteur coarse/medium `{trend_changes}`."
        )
        multifamily_coupling = summary["multifamily_coupled_geometry_benchmark"]
        lines.append(
            f"Couplage J2/geometrie quatre familles : **{multifamily_coupling['status']}**, "
            f"familles `{[row['element'] for row in multifamily_coupling['rows']]}`, "
            f"residu max `{max(row['maximum_relative_residual'] for row in multifamily_coupling['rows']):.3e}`."
        )
        lines.extend(["", f"Euler TET4 : **{summary['euler_buckling_benchmark']['status']}**, niveaux `{[row['cells'] for row in summary['euler_buckling_benchmark']['levels']]}`, erreur Euler finale `{100 * summary['euler_buckling_benchmark']['levels'][-1]['euler_relative_error']:.2f} %`.", f"Arc-length commun : **{summary['arc_length_benchmark']['status']}**, etapes `{summary['arc_length_benchmark']['step_count']}`, cible atteinte `{summary['arc_length_benchmark']['reached_target']}`.", f"Arc-length FEM TET4 : **{summary['fem_arc_length_benchmark']['status']}**, etapes `{summary['fem_arc_length_benchmark']['step_count']}`, facteur `{summary['fem_arc_length_benchmark']['load_factor_range']}`, residu `{summary['fem_arc_length_benchmark']['maximum_relative_residual']:.3e}`.", f"Shallow arch reduit : **{summary['shallow_arch_arc_length_benchmark']['status']}**, point limite observe `{summary['shallow_arch_arc_length_benchmark']['limit_point_observed']}`, branches `{summary['shallow_arch_arc_length_benchmark']['branch_turn_count']}`.", f"Contact commun : **{summary['common_contact_benchmark']['status']}**, tangent ouverte `{summary['common_contact_benchmark']['open_tangent_nnz']}`, tangent fermee `{summary['common_contact_benchmark']['closed_tangent_nnz']}`.", f"Recontact : **{summary['contact_recontact_benchmark']['status']}**, sequence `{summary['contact_recontact_benchmark']['active_by_step']}`.", f"Sensibilite penalty : **{summary['contact_penalty_sensitivity_benchmark']['status']}**, tendance penetration monotone `{summary['contact_penalty_sensitivity_benchmark']['penetration_monotone_nonincreasing']}`.", f"Recherche surface multi-face : **{summary['contact_surface_search_benchmark']['status']}**, faces `{summary['contact_surface_search_benchmark']['selected_face_indices']}`.", f"Couplages : **{summary['coupling_benchmark']['status']}**, driver commun `{summary['coupling_benchmark']['shared_driver']}`.", f"J2 finite-kinematic : **{summary['finite_kinematic_j2_benchmark']['status']}**, familles `{[row['element'] for row in summary['finite_kinematic_j2_benchmark']['rows']]}`.", f"Geometrie haut ordre : **{summary['high_order_geometric_benchmark']['status']}**, familles `{[row['element'] for row in summary['high_order_geometric_benchmark']['rows']]}`."])
        lines.append(
            f"Contact tangent FD : **{summary['contact_tangent_fd_benchmark']['status']}**, "
            f"erreur relative maximale `{summary['contact_tangent_fd_benchmark']['maximum_relative_error']:.3e}`."
        )
        lines.append(
            f"Glissement mis a jour : **{summary['contact_updated_sliding_benchmark']['status']}**, "
            f"sequence `{summary['contact_updated_sliding_benchmark']['face_sequence']}`."
        )
        lines.append(
            f"Geometrie + contact : **{summary['geometric_contact_benchmark']['status']}**, "
            f"contacts actifs `{summary['geometric_contact_benchmark']['contact'].get('active_contacts', [])}`, "
            f"penetration `{summary['geometric_contact_benchmark']['contact'].get('maximum_penetration', 0.0):.3e}`."
        )
        lines.append(
            f"Grande rotation : **{summary['large_rotation_geometric_benchmark']['status']}**, "
            f"angles `{[round(row['end_line_angle_deg'], 2) for row in summary['large_rotation_geometric_benchmark']['rows']]}` deg."
        )
        lines.append(
            f"Sensibilite maillage grande rotation : **{summary['large_rotation_mesh_sensitivity_benchmark']['status']}**, "
            f"niveaux `{summary['large_rotation_mesh_sensitivity_benchmark']['levels']}`, "
            f"variations `{[row['coarse_to_refined'] for row in summary['large_rotation_mesh_sensitivity_benchmark']['rows']]}`."
        )
        lines.append(
            f"Sensibilite maillage grande rotation haut ordre : **{summary['high_order_large_rotation_mesh_sensitivity_benchmark']['status']}**, "
            f"charge `{summary['high_order_large_rotation_mesh_sensitivity_benchmark']['load_scale']}`, "
            f"familles `{[row['element'] for row in summary['high_order_large_rotation_mesh_sensitivity_benchmark']['rows']]}`."
        )
        lines.append(
            f"Couplage contact quatre familles : **{summary['multifamily_coupled_contact_benchmark']['status']}**, "
            f"familles `{[row['element'] for row in summary['multifamily_coupled_contact_benchmark']['rows']]}`, "
            f"contacts actifs `{[row.get('active_step_count', 0) for row in summary['multifamily_coupled_contact_benchmark']['rows']]}`."
        )
        lines.append(
            f"Recuperation small-strain/finite-kinematic : **{summary['finite_kinematic_limit_recovery_benchmark']['status']}**, "
            f"ecarts `{[row['relative_displacement_error'] for row in summary['finite_kinematic_limit_recovery_benchmark']['rows']]}`."
        )
        lines.append(
            f"Failure contract : **{summary['failure_campaign']['status']}**, "
            f"cas principaux `{len(summary['failure_campaign']['cases'])}`, "
            f"retries `{len(summary['failure_campaign']['retry_cases'])}`."
        )
        lines.append(
            f"Arc-length J2 finite-kinematic : **{summary['finite_kinematic_arc_length_benchmark']['status']}**, "
            f"facteur final `{summary['finite_kinematic_arc_length_benchmark']['final_load_factor']:.6e}`, "
            f"residu `{summary['finite_kinematic_arc_length_benchmark']['maximum_relative_residual']:.3e}`."
        )
        lines.extend(
            [
                "",
                "### Arc-length J2 finite-kinematic par famille",
                "",
                "| Element | Etapes | Plage facteur | Plage rayon | Residu max | Statut |",
                "| --- | ---: | --- | --- | ---: | --- |",
            ]
        )
        for row in summary["finite_kinematic_arc_length_benchmark"]["rows"]:
            lines.append(
                f"| {row['element']} | {row['step_count']} | {row['load_factor_range']} | "
                f"{row['radius_range']} | {row['maximum_relative_residual']:.3e} | {row['status']} |"
            )
        lines.append("")
        lines.append("Le bilan travail externe/interne est enregistre dans `summary.json` avec l'imbalance relative par increment.")
        lines.extend(["", "## Robustesse", "", f"Tangent FD max : `{summary['consistent_tangent']['maximum_relative_error']:.3e}`", f"Transactions : **{summary['transactions']['status']}**", "", "![Force displacement](force_displacement.png)", "", "![Newton rate](newton_rate.png)", "", f"Correlation externe : **{summary['external_correlations']['status']}**", ""])
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")

    def _write_plots(self, summary: dict[str, Any]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        figure, axes = plt.subplots(1, 2, figsize=(10.0, 4.2), constrained_layout=True)
        for row in summary["element_matrix"]["rows"]:
            factors = [item["factor"] for item in row["history"]]
            axes[0].plot(factors, [item["reaction_norm"] for item in row["history"]], marker="o", label=row["element"])
        axes[0].set(xlabel="Facteur de charge", ylabel="Norme force interne", title="Force-deplacement borne")
        for row in summary["common_global_benchmark"]["rows"]:
            axes[1].bar(row["element"], row["newton_iterations"])
        axes[1].set(ylabel="Iterations Newton", title="Cout Newton par element")
        axes[0].legend()
        for axis in axes:
            axis.grid(alpha=0.25)
        figure.savefig(self.output_dir / "force_displacement.png", dpi=160)
        plt.close(figure)
        figure, axis = plt.subplots(figsize=(6.4, 4.0))
        for row in summary["common_global_benchmark"]["rows"]:
            for index, history in enumerate(row["residual_histories"]):
                axis.semilogy(range(1, len(history) + 1), history, marker="o", markersize=2, alpha=0.65, label=row["element"] if index == 0 else None)
        axis.set(xlabel="Iteration Newton", ylabel="Residu relatif", title="Historiques de convergence Newton")
        axis.grid(alpha=0.25)
        axis.legend()
        figure.savefig(self.output_dir / "newton_rate.png", dpi=160)
        plt.close(figure)
        figure, axis = plt.subplots(figsize=(6.4, 4.0))
        arch = summary["shallow_arch_arc_length_benchmark"]
        steps = arch["steps"]
        axis.plot(
            [row["displacement"] for row in steps],
            [row["load_factor"] for row in steps],
            "o-",
            label="arc-length",
            markersize=3,
        )
        u_reference = np.linspace(-1.05, 1.05, 300)
        axis.plot(u_reference, u_reference - u_reference**3, "--", label="reference")
        axis.set(xlabel="Deplacement reduit", ylabel="Facteur de charge", title="Shallow arch: suivi de branche")
        axis.grid(alpha=0.25)
        axis.legend()
        figure.savefig(self.output_dir / "shallow_arch_arc_length.png", dpi=160)
        plt.close(figure)
        figure, axes = plt.subplots(2, 1, figsize=(7.0, 6.0), sharex=False)
        arc = summary["finite_kinematic_arc_length_benchmark"]
        for row in arc["rows"]:
            axes[0].plot(row["load_factor"], marker=".", linewidth=1.0, label=row["element"])
            if row["radius_history"]:
                axes[1].semilogy(
                    range(1, len(row["radius_history"]) + 1),
                    row["radius_history"],
                    marker=".",
                    linewidth=1.0,
                    label=row["element"],
                )
        axes[0].set(xlabel="Etape", ylabel="Facteur de charge", title="Arc-length J2 finite-kinematic")
        axes[1].set(xlabel="Etape", ylabel="Rayon arc-length", title="Adaptation du rayon")
        for axis in axes:
            axis.grid(alpha=0.25)
            axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "finite_kinematic_arc_length.png", dpi=160)
        plt.close(figure)
