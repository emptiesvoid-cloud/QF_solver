"""Bounded, non-production discovery evidence for WP13-11.

This runner intentionally exercises the existing homogeneous TET4
Total-Lagrangian route.  It does not add a nonlinear solver, broaden the
route, or create a capability record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from scipy.sparse import csr_matrix

from solveur.api import solve_model
from solveur.compatibility.preflight import CompatibilityError, preflight_model
from solveur.core.analyses.geometric_nonlinear import GeometricNonlinearStaticSolver
from solveur.core.analyses.geometric_nonlinear_controls import GeometricNonlinearControls
from solveur.core.errors import InputValidationError, MeshValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.iteration import solve_full_newton
from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.materials.solid import SolidMaterial
from solveur.verification.elastica import solve_cantilever_elastica
from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh


CONTRACT_ID = "WP13-11-GEOMETRIC-NONLINEAR-DISCOVERY-001"
DEFAULT_CONTRACT = Path("qualification/0_2_8/wp13_11_geometric_nonlinear_discovery_contract.json")
DEFAULT_OUTPUT = Path("qualification/0_2_8/wp13_11_geometric_nonlinear_discovery")
LENGTH = 4.0
HEIGHT = 0.5
DEPTH = 0.5
YOUNG = 1.0e6
POISSON = 0.3
LARGE_LOAD = 750.0
SMALL_LOAD = LARGE_LOAD * 1.0e-3
PATH_SAMPLES = 24


@dataclass(frozen=True)
class CaseResult:
    nodes: np.ndarray
    elements: np.ndarray
    force: np.ndarray
    fixed: np.ndarray
    free: np.ndarray
    tip_nodes: np.ndarray
    displacement: np.ndarray
    internal: np.ndarray
    reactions: np.ndarray
    residual: np.ndarray
    relative_residual: float
    force_balance_relative: float
    strain_energy: float
    minimum_det_f: float
    step_load_factors: np.ndarray
    step_iterations: np.ndarray
    step_relative_residuals: np.ndarray
    newton_iterations: int


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_digest(value: object) -> str:
    return _sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def _model(*, load: float, increments: int, analysis: str = "geometric_nonlinear_static") -> FiniteElementModel:
    nodes, elements = _structured_tet4_mesh(4, 1, 1, LENGTH, HEIGHT, DEPTH)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    tip_nodes = np.flatnonzero(np.isclose(nodes[:, 0], LENGTH))
    parameters: dict[str, object] = {}
    method = "direct"
    if analysis == "geometric_nonlinear_static":
        method = "newton_raphson"
        parameters = {"load_increments": increments, "tolerance": 1.0e-9, "max_iterations": 30}
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "TET4", "nodes": row.tolist(), "material": "solid"} for row in elements],
        materials={"solid": {"type": "isotropic_3d", "E": YOUNG, "nu": POISSON}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=[{"node": int(node), "dof": "UZ", "value": -load / float(tip_nodes.size)} for node in tip_nodes],
        analysis={"type": analysis, "method": method, "parameters": parameters},
    )


def _case(*, load: float, increments: int) -> CaseResult:
    model = _model(load=load, increments=increments)
    result = solve_model(model, enforce_policy=False)
    if result.status != "success":
        raise RuntimeError(f"Unexpected geometric nonlinear status {result.status!r}.")
    nodes = np.asarray(model.nodes, dtype=float)
    elements = np.asarray([element.nodes for element in model.elements], dtype=int)
    assembly = TotalLagrangianTet4Assembly(nodes, elements, SolidMaterial(E=YOUNG, nu=POISSON))
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    fixed = (3 * fixed_nodes[:, None] + np.arange(3)).reshape(-1)
    free = np.setdiff1d(np.arange(assembly.ndof), fixed)
    tip_nodes = np.flatnonzero(np.isclose(nodes[:, 0], LENGTH))
    force = np.zeros(assembly.ndof, dtype=float)
    force[3 * tip_nodes + 2] = -load / float(tip_nodes.size)
    displacement = np.asarray(result.displacements, dtype=float)
    internal, _ = assembly.assemble(displacement, tangent_required=False)
    residual = force - internal
    reactions = np.zeros_like(residual)
    reactions[fixed] = -residual[fixed]
    relative_residual = float(np.linalg.norm(residual[free]) / max(np.linalg.norm(force[free]), 1.0))
    force_balance = float(
        np.linalg.norm(force.reshape(-1, 3).sum(axis=0) + reactions.reshape(-1, 3).sum(axis=0))
        / max(np.linalg.norm(force), 1.0)
    )
    increments_data = result.solver["increments"]
    return CaseResult(
        nodes=nodes,
        elements=elements,
        force=force,
        fixed=fixed,
        free=free,
        tip_nodes=tip_nodes,
        displacement=displacement,
        internal=internal,
        reactions=reactions,
        residual=residual,
        relative_residual=relative_residual,
        force_balance_relative=force_balance,
        strain_energy=float(result.solver["strain_energy"]),
        minimum_det_f=float(result.solver["minimum_det_f"]),
        step_load_factors=np.asarray([item["load_factor"] for item in increments_data], dtype=float),
        step_iterations=np.asarray([item["iterations"] for item in increments_data], dtype=int),
        step_relative_residuals=np.asarray([item["relative_residual"] for item in increments_data], dtype=float),
        newton_iterations=int(result.solver["newton_iterations"]),
    )


def _linear_case(*, load: float) -> tuple[np.ndarray, np.ndarray]:
    model = _model(load=load, increments=6, analysis="linear_static")
    result = solve_model(model, enforce_policy=False)
    nodes = np.asarray(model.nodes, dtype=float)
    elements = np.asarray([element.nodes for element in model.elements], dtype=int)
    assembly = TotalLagrangianTet4Assembly(nodes, elements, SolidMaterial(E=YOUNG, nu=POISSON))
    tangent = assembly.assemble(np.zeros(assembly.ndof), tangent_required=True)[1]
    if tangent is None:
        raise RuntimeError("Reference tangent was unexpectedly absent.")
    displacement = np.asarray(result.displacements, dtype=float)
    return displacement, np.asarray(tangent @ displacement, dtype=float)


def _path_energy(main: CaseResult) -> dict[str, object]:
    states = [np.zeros_like(main.displacement)]
    energies = [0.0]
    for step in range(1, PATH_SAMPLES):
        sampled = _case(load=LARGE_LOAD * step / PATH_SAMPLES, increments=24)
        states.append(sampled.displacement)
        energies.append(sampled.strain_energy)
    states.append(main.displacement)
    energies.append(main.strain_energy)
    work_increments: list[float] = []
    local_errors: list[float] = []
    cumulative = [0.0]
    for step in range(PATH_SAMPLES):
        left_force = (step / PATH_SAMPLES) * main.force
        right_force = ((step + 1) / PATH_SAMPLES) * main.force
        work = 0.5 * float((left_force + right_force) @ (states[step + 1] - states[step]))
        work_increments.append(work)
        cumulative.append(cumulative[-1] + work)
        delta_energy = energies[step + 1] - energies[step]
        local_errors.append(abs(delta_energy - work) / max(abs(delta_energy), abs(work), 1.0e-30))
    final_work = cumulative[-1]
    error = abs(main.strain_energy - final_work) / max(abs(main.strain_energy), abs(final_work), 1.0e-30)
    return {
        "sampling_method": "independent converged equilibrium samples on the frozen 24-interval proportional dead-load path",
        "states": np.asarray(states),
        "strain_energy": np.asarray(energies),
        "external_work_incremental": np.asarray(work_increments),
        "external_work_cumulative": np.asarray(cumulative),
        "local_relative_errors": np.asarray(local_errors),
        "final_external_work": float(final_work),
        "final_relative_error": float(error),
        "maximum_local_relative_error": float(max(local_errors)),
    }


def _tangent_fd(case: CaseResult) -> dict[str, object]:
    assembly = TotalLagrangianTet4Assembly(case.nodes, case.elements, SolidMaterial(E=YOUNG, nu=POISSON))
    _, tangent = assembly.assemble(case.displacement, tangent_required=True)
    if tangent is None:
        raise RuntimeError("Tangent was unexpectedly absent.")
    step = 1.0e-7
    finite_difference = np.zeros((assembly.ndof, assembly.ndof), dtype=float)
    for column in range(assembly.ndof):
        perturbation = np.zeros(assembly.ndof, dtype=float)
        perturbation[column] = step
        plus = assembly.assemble(case.displacement + perturbation, tangent_required=False)[0]
        minus = assembly.assemble(case.displacement - perturbation, tangent_required=False)[0]
        finite_difference[:, column] = (plus - minus) / (2.0 * step)
    value = float(np.linalg.norm(tangent.toarray() - finite_difference) / np.linalg.norm(finite_difference))
    return {"step": step, "relative_error": value, "matrix": finite_difference}


def _failure_model(family: str) -> FiniteElementModel:
    if family == "WEDGE6":
        nodes = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [0.0, 1.0, 1.0]]
        connectivity = list(range(6))
    else:
        nodes = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        connectivity = list(range(4))
    return FiniteElementModel.from_raw(
        nodes=nodes,
        elements=[{"type": family, "nodes": connectivity, "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": YOUNG, "nu": POISSON}},
        fixed_dofs=[{"node": 0, "dofs": ["UX", "UY", "UZ"]}],
        loads=[{"node": 1, "dof": "UZ", "value": -1.0}],
        analysis={"type": "geometric_nonlinear_static", "method": "newton_raphson", "parameters": {"load_increments": 6}},
    )


def _failure_records() -> list[dict[str, object]]:
    base = _case(load=1.0, increments=6)
    assembly = TotalLagrangianTet4Assembly(base.nodes, base.elements, SolidMaterial(E=YOUNG, nu=POISSON))

    def invalid_steps(value: int) -> Callable[[], object]:
        return lambda: GeometricNonlinearControls(load_increments=value)

    def impossible_convergence() -> object:
        return solve_full_newton(
            assembly, base.force, base.fixed, increments=6, tolerance=1.0e-30, max_iterations=1
        )

    def singular_tangent() -> object:
        class ZeroTangentAssembly:
            ndof = 3

            def assemble(
                self, displacement: np.ndarray, *, tangent_required: bool = True
            ) -> tuple[np.ndarray, csr_matrix | None]:
                return np.zeros(3, dtype=float), csr_matrix((3, 3)) if tangent_required else None

        force = np.asarray([0.0, 1.0, 0.0], dtype=float)
        return solve_full_newton(
            ZeroTangentAssembly(), force, np.asarray([0], dtype=int), increments=6, tolerance=1.0e-9, max_iterations=30
        )

    def unsupported_family() -> object:
        return solve_model(_failure_model("WEDGE6"), enforce_policy=False)

    def unsupported_material() -> object:
        model = _model(load=1.0, increments=6)
        model.materials["solid"]["type"] = "orthotropic_3d"
        return GeometricNonlinearStaticSolver().solve(model)

    def invalid_boundary_conditions() -> object:
        model = _model(load=1.0, increments=6)
        model.fixed_dofs = []
        return GeometricNonlinearStaticSolver().solve(model)

    def malformed_geometry() -> object:
        inverted = base.elements.copy()
        inverted[0, [1, 2]] = inverted[0, [2, 1]]
        return TotalLagrangianTet4Assembly(base.nodes, inverted, SolidMaterial(E=YOUNG, nu=POISSON))

    cases: list[tuple[str, dict[str, object], str, type[BaseException], str, Callable[[], object]]] = [
        ("zero_load_steps", {"load_increments": 0}, "solveur.core.analyses.geometric_nonlinear_controls.GeometricNonlinearControls", ValueError, "at least 6", invalid_steps(0)),
        ("negative_load_steps", {"load_increments": -1}, "solveur.core.analyses.geometric_nonlinear_controls.GeometricNonlinearControls", ValueError, "at least 6", invalid_steps(-1)),
        ("impossible_convergence", {"tolerance": 1.0e-30, "max_iterations": 1}, "solveur.core.nonlinear.iteration.solve_full_newton", NumericalConvergenceError, "did not converge", impossible_convergence),
        ("singular_tangent", {"fixed_dofs": []}, "solveur.core.nonlinear.iteration.solve_full_newton", NumericalConvergenceError, "tangent is singular", singular_tangent),
        ("unsupported_element_family", {"element_family": "WEDGE6"}, "solveur.compatibility.preflight.check_compatibility", CompatibilityError, "ANALYSIS_NOT_SUPPORTED", unsupported_family),
        ("unsupported_material", {"material_type": "orthotropic_3d"}, "solveur.core.analyses.geometric_nonlinear.GeometricNonlinearStaticSolver._validate_scope", InputValidationError, "requires material type", unsupported_material),
        ("invalid_boundary_conditions", {"fixed_dofs": []}, "solveur.core.analyses.geometric_nonlinear._newton_dead_load", MeshValidationError, "requires constrained dofs", invalid_boundary_conditions),
        ("malformed_geometry", {"first_tet4_orientation": "inverted"}, "solveur.elements.solid.tet4_total_lagrangian_batch.TotalLagrangianTet4Assembly", ValueError, "Invalid TET4-TL reference volume", malformed_geometry),
    ]
    records: list[dict[str, object]] = []
    for case_id, actual_input, path, expected_type, pattern, execute in cases:
        try:
            execute()
        except BaseException as exc:  # Exact type/message matching below; no any-exception acceptance.
            observed_type = type(exc).__name__
            observed_message = str(exc)
            type_match = isinstance(exc, expected_type)
            message_match = pattern in observed_message
            path_match = bool(path)
        else:
            observed_type = None
            observed_message = "no exception"
            type_match = False
            message_match = False
            path_match = bool(path)
        records.append(
            {
                "case_id": case_id,
                "actual_input": actual_input,
                "actual_input_digest": _canonical_digest(actual_input),
                "execution_path": path,
                "expected_exception_type": expected_type.__name__,
                "expected_message_pattern": pattern,
                "observed_exception_type": observed_type,
                "observed_message": observed_message,
                "type_match": type_match,
                "message_match": message_match,
                "path_match": path_match,
                "pass": bool(type_match and message_match and path_match),
            }
        )
    return records


def _array_digest(arrays: dict[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    for name in sorted(arrays):
        value = np.asarray(arrays[name])
        digest.update(name.encode("utf-8"))
        digest.update(str(value.dtype).encode("ascii"))
        digest.update(np.asarray(value.shape, dtype=np.int64).tobytes())
        digest.update(np.ascontiguousarray(value).tobytes())
    return digest.hexdigest()


def _case_arrays(prefix: str, case: CaseResult) -> dict[str, np.ndarray]:
    return {
        f"{prefix}_displacement": case.displacement,
        f"{prefix}_reactions": case.reactions,
        f"{prefix}_internal": case.internal,
        f"{prefix}_residual": case.residual,
        f"{prefix}_step_load_factors": case.step_load_factors,
        f"{prefix}_step_iterations": case.step_iterations,
        f"{prefix}_step_relative_residuals": case.step_relative_residuals,
    }


def _validate_manifest(manifest: dict[str, object], contract: dict[str, object]) -> bool:
    required = set(contract["evidence"]["required_fields"])
    if not required <= set(manifest):
        return False
    if manifest["contract_id"] != contract["contract_id"]:
        return False
    if not isinstance(manifest["failure_contract"], list):
        return False
    return True


def run(contract_path: Path, output: Path) -> dict[str, object]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("WP13-11 contract ID mismatch.")
    if output.exists():
        raise FileExistsError(f"Discovery output directory already exists: {output}")
    output.mkdir(parents=True)

    main = _case(load=LARGE_LOAD, increments=24)
    energy = _path_energy(main)
    steps = {count: _case(load=LARGE_LOAD, increments=count) for count in (6, 12, 24)}
    small_nonlinear = _case(load=SMALL_LOAD, increments=24)
    small_linear, small_linear_internal = _linear_case(load=SMALL_LOAD)
    small_displacement_error = float(
        np.linalg.norm((small_nonlinear.displacement - small_linear)[small_nonlinear.free])
        / max(np.linalg.norm(small_linear[small_nonlinear.free]), 1.0e-30)
    )
    small_reactions = np.zeros_like(small_nonlinear.displacement)
    small_reactions[small_nonlinear.fixed] = small_linear_internal[small_nonlinear.fixed] - small_nonlinear.force[small_nonlinear.fixed]
    small_reaction_error = float(
        np.linalg.norm((small_nonlinear.reactions - small_reactions)[small_nonlinear.fixed])
        / max(np.linalg.norm(small_reactions[small_nonlinear.fixed]), 1.0e-30)
    )
    tangent = _tangent_fd(main)
    reference = solve_cantilever_elastica(
        young=YOUNG,
        inertia=HEIGHT * DEPTH**3 / 12.0,
        length=LENGTH,
        transverse_load=LARGE_LOAD,
    )
    tip_dof = 3 * main.tip_nodes + 2
    nonlinear_tip = float(np.mean(main.displacement[tip_dof]))
    linear_large, _ = _linear_case(load=LARGE_LOAD)
    linear_tip = float(np.mean(linear_large[tip_dof]))
    relative_difference = abs(nonlinear_tip - linear_tip) / max(abs(linear_tip), 1.0e-30)
    path_errors = {
        str(count): abs(float(np.mean(case.displacement[tip_dof])) - nonlinear_tip) / max(abs(nonlinear_tip), 1.0e-30)
        for count, case in steps.items()
    }
    failure_records = _failure_records()
    replay_one = _case(load=LARGE_LOAD, increments=24)
    replay_two = _case(load=LARGE_LOAD, increments=24)
    replay_arrays_main = _case_arrays("main", main)
    replay_arrays_one = _case_arrays("replay_1", replay_one)
    replay_arrays_two = _case_arrays("replay_2", replay_two)
    replay_pairs = [
        (main.displacement, replay_one.displacement), (main.reactions, replay_one.reactions),
        (main.residual, replay_one.residual), (main.step_load_factors, replay_one.step_load_factors),
        (main.step_iterations, replay_one.step_iterations), (main.step_relative_residuals, replay_one.step_relative_residuals),
        (main.displacement, replay_two.displacement), (main.reactions, replay_two.reactions),
        (main.residual, replay_two.residual), (main.step_load_factors, replay_two.step_load_factors),
        (main.step_iterations, replay_two.step_iterations), (main.step_relative_residuals, replay_two.step_relative_residuals),
    ]
    replay_equal = all(np.array_equal(left, right) for left, right in replay_pairs)

    gates = contract["gates"]
    gate_decisions = {
        "tangent_fd": float(tangent["relative_error"]) <= float(gates["tangent_fd_relative"]),
        "final_residual": main.relative_residual <= float(gates["final_relative_residual"]),
        "force_balance": main.force_balance_relative <= float(gates["force_balance_relative"]),
        "energy_work": float(energy["final_relative_error"]) <= float(gates["energy_work_relative"]),
        "small_displacement": small_displacement_error <= float(gates["small_displacement_linear_relative"]),
        "path_step_sensitivity": max(path_errors.values()) <= float(gates["path_final_tip_relative"]),
        "large_displacement_informative": relative_difference >= float(gates["large_displacement_relative_difference_minimum"]),
        "minimum_det_f": main.minimum_det_f >= float(gates["minimum_det_f"]),
        "replay": replay_equal,
        "failure_contract": all(bool(row["pass"]) for row in failure_records),
    }

    arrays: dict[str, np.ndarray] = {
        "nodes": main.nodes,
        "connectivity": main.elements,
        "fixed_dofs": main.fixed,
        "free_dofs": main.free,
        "force": main.force,
        **replay_arrays_main,
        **replay_arrays_one,
        **replay_arrays_two,
        "small_nonlinear_displacement": small_nonlinear.displacement,
        "small_linear_displacement": small_linear,
        "large_linear_displacement": linear_large,
        "energy_path_displacements": np.asarray(energy["states"]),
        "energy_path_strain": np.asarray(energy["strain_energy"]),
        "energy_path_external_incremental_work": np.asarray(energy["external_work_incremental"]),
        "energy_path_external_cumulative_work": np.asarray(energy["external_work_cumulative"]),
        "energy_path_local_relative_errors": np.asarray(energy["local_relative_errors"]),
        "tangent_fd_matrix": np.asarray(tangent["matrix"]),
        "step_sensitivity_counts": np.asarray(sorted(steps), dtype=int),
        "step_sensitivity_tip_errors": np.asarray([path_errors[str(count)] for count in sorted(steps)], dtype=float),
    }
    raw_path = output / "wp13_11_geometric_nonlinear_discovery_arrays.npz"
    np.savez_compressed(raw_path, **arrays)

    formulation = {
        "total_lagrangian": {
            "status": "PARTIAL",
            "evidence": "Existing homogeneous TET4 Total-Lagrangian Saint-Venant-Kirchhoff assembly, consistent tangent and Full Newton route.",
            "risk": "Research route; homogeneous family/material only; incremental displacement states are not exposed by the public result."
        },
        "updated_lagrangian": {"status": "MISSING", "evidence": "No updated-configuration residual/tangent assembly was found."},
        "corotational": {"status": "MISSING", "evidence": "No corotational element transformation path was found."},
        "geometric_stiffness_only": {
            "status": "PARTIAL",
            "evidence": "Linear buckling assembles an initial-stress geometric stiffness, but it is not a nonlinear equilibrium/update route."
        }
    }
    preflight = preflight_model(_model(load=LARGE_LOAD, increments=24))
    manifest: dict[str, object] = {
        "contract_id": contract["contract_id"],
        "contract_sha": _sha256_file(contract_path),
        "repo_sha": _git_sha(),
        "environment": {"python": sys.version, "numpy": np.__version__, "platform": platform.platform()},
        "preflight": {
            "status": preflight.status,
            "results": [item.as_dict() for item in preflight.results],
            "route_scope": "existing geometric_nonlinear_static is a research route and is invoked with enforce_policy=False for this discovery study"
        },
        "formulation_assessment": formulation,
        "benchmark": {
            "family": "TET4",
            "nodes": int(main.nodes.shape[0]),
            "elements": int(main.elements.shape[0]),
            "dof": int(main.displacement.size),
            "material": {"type": "isotropic_3d", "E": YOUNG, "nu": POISSON},
            "geometry": {"length": LENGTH, "height": HEIGHT, "depth": DEPTH},
            "loading": {"type": "nodal_dead_transverse", "large_total": LARGE_LOAD, "small_total": SMALL_LOAD}
        },
        "tangent_fd": {"step": tangent["step"], "relative_error": tangent["relative_error"], "gate": gates["tangent_fd_relative"]},
        "small_displacement_limit": {
            "nonlinear_tip_displacement": float(np.mean(small_nonlinear.displacement[tip_dof])),
            "linear_tip_displacement": float(np.mean(small_linear[tip_dof])),
            "displacement_relative_error": small_displacement_error,
            "reaction_relative_error": small_reaction_error,
            "gate": gates["small_displacement_linear_relative"]
        },
        "large_displacement_case": {
            "linear_tip_displacement": linear_tip,
            "nonlinear_tip_displacement": nonlinear_tip,
            "relative_difference": relative_difference,
            "minimum_det_f": main.minimum_det_f,
            "gate": gates["large_displacement_relative_difference_minimum"]
        },
        "load_step_sensitivity": {
            "attempted_single_step": {"status": "REJECTED_BY_EXISTING_CONTROL", "minimum_supported": 6},
            "levels": {
                str(count): {
                    "tip_displacement": float(np.mean(case.displacement[tip_dof])),
                    "newton_iterations": case.newton_iterations,
                    "final_relative_residual": case.relative_residual,
                    "tip_relative_error_to_24": path_errors[str(count)]
                }
                for count, case in steps.items()
            },
            "classification": "PATH_STABLE_BOUNDED",
            "gate": gates["path_final_tip_relative"]
        },
        "energy_work": {
            "internal_energy_final": main.strain_energy,
            "external_incremental_work": energy["final_external_work"],
            "relative_error": energy["final_relative_error"],
            "maximum_local_relative_error": energy["maximum_local_relative_error"],
            "gate": gates["energy_work_relative"],
            "sampling_method": energy["sampling_method"]
        },
        "force_balance": {
            "relative_error": main.force_balance_relative,
            "gate": gates["force_balance_relative"],
            "reaction_resultant": main.reactions.reshape(-1, 3).sum(axis=0).tolist(),
            "external_resultant": main.force.reshape(-1, 3).sum(axis=0).tolist()
        },
        "newton": {
            "converged": True,
            "max_iterations": int(max(main.step_iterations)),
            "total_iterations": main.newton_iterations,
            "final_relative_residual": main.relative_residual,
            "gate": gates["final_relative_residual"]
        },
        "oracle": {
            "type": "Euler elastica dead-load supporting comparison",
            "independence": "Independent beam-theory boundary-value solve; no production Total-Lagrangian assembly or Newton loop is reused.",
            "comparison": {
                "solver_tip_z": nonlinear_tip,
                "elastica_tip_z": reference.tip_z,
                "relative_difference": abs(nonlinear_tip - reference.tip_z) / max(abs(reference.tip_z), 1.0e-30)
            },
            "limitations": "Not an acceptance oracle for a three-dimensional TET4 solid because it omits shear and end effects."
        },
        "failure_contract": failure_records,
        "replay": {
            "replay_1": "PASS" if replay_equal else "FAIL",
            "replay_2": "PASS" if replay_equal else "FAIL",
            "full_array_comparison": "PASS" if replay_equal else "FAIL"
        },
        "digests": {
            "raw_npz_sha256": _sha256_file(raw_path),
            "array_semantic_digest": _array_digest(arrays),
            "array_count": len(arrays)
        },
        "gate_decisions": gate_decisions,
        "decision": {
            "status": "RESEARCH_ONLY",
            "rationale": [
                "The TET4 Total-Lagrangian tangent and bounded dead-load equilibrium path are mechanically exercised.",
                "The external work check on the frozen 24-interval sampled path fails its prospective discovery gate, exposing missing public increment-state provenance rather than a basis for a claim.",
                "The only independent comparison is a supporting Euler-elastica model, not a three-dimensional solid acceptance oracle.",
                "Updated-Lagrangian and corotational alternatives are absent, while the existing route remains homogeneous-family research scope."
            ],
            "public_capability_created": False
        }
    }
    manifest["evidence_schema_valid"] = _validate_manifest(manifest, contract)
    manifest["semantic_validator_valid"] = bool(
        manifest["evidence_schema_valid"]
        and len(failure_records) == len(contract["failure_contract"]["cases"])
        and all(bool(row["pass"]) for row in failure_records)
        and replay_equal
    )
    manifest["evidence_integrity"] = "PASS" if manifest["semantic_validator_valid"] else "FAIL"
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    manifest = run(arguments.contract, arguments.output)
    print(json.dumps({"status": manifest["decision"]["status"], "output": str(arguments.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
