"""Public geometrically nonlinear TET4 static solver."""

from __future__ import annotations

import warnings

import numpy as np
from scipy.sparse.linalg import MatrixRankWarning, spsolve

from solveur.core.errors import InputValidationError, MeshValidationError, NumericalConvergenceError
from solveur.core.geometric_nonlinear_controls import GeometricNonlinearControls
from solveur.core.model import FiniteElementModel
from solveur.core.results import SolveResult
from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.materials.solid import SolidMaterial
from solveur.mesh.validation import MeshValidator


class GeometricNonlinearStaticSolver:
    """Solve a bounded TET4 Saint-Venant-Kirchhoff dead-load problem."""

    def solve(self, model: FiniteElementModel) -> SolveResult:
        self._validate_scope(model)
        report = MeshValidator().validate(model)
        if report.status == "FAIL":
            raise MeshValidationError("; ".join(report.errors))
        parameters = model.analysis.parameters
        controls = GeometricNonlinearControls(
            load_increments=int(parameters.get("load_increments", 10))
        )
        tolerance = float(parameters.get("tolerance", 1.0e-9))
        max_iterations = int(parameters.get("max_iterations", 30))
        if not 0.0 < tolerance < 1.0:
            raise InputValidationError("geometric nonlinear tolerance must be in (0, 1).")
        if max_iterations < 2:
            raise InputValidationError("geometric nonlinear max_iterations must be at least 2.")
        dofs = model.dof_manager()
        connectivity = np.asarray([element.nodes for element in model.elements], dtype=int)
        raw_material = model.materials[model.elements[0].material]
        assembly = TotalLagrangianTet4Assembly(
            model.nodes,
            connectivity,
            SolidMaterial(E=float(raw_material["E"]), nu=float(raw_material["nu"])),
        )
        external = np.zeros(assembly.ndof, dtype=float)
        for load in model.loads:
            external[dofs.index(load.node, load.dof)] += load.value
        fixed = np.unique(
            [dofs.index(condition.node, name) for condition in model.fixed_dofs for name in condition.dofs]
        )
        displacement, diagnostics = _newton_dead_load(
            assembly,
            external,
            fixed,
            increments=controls.load_increments,
            tolerance=tolerance,
            max_iterations=max_iterations,
        )
        states = assembly.element_states(displacement)
        element_results = [
            {
                "index": index,
                "type": "TET4_TOTAL_LAGRANGIAN",
                "det_f": float(states["det_f"][index]),
                "green_lagrange_strain": states["green_lagrange_strain"][index].tolist(),
                "second_piola_stress": states["second_piola_stress"][index].tolist(),
                "cauchy_stress": states["cauchy_stress"][index].tolist(),
                "strain_energy_density": float(states["strain_energy_density"][index]),
            }
            for index in range(connectivity.shape[0])
        ]
        diagnostics.update(
            {
                "load_increments": controls.load_increments,
                "strain_energy": assembly.strain_energy(displacement),
                "minimum_det_f": float(np.min(states["det_f"])),
                "scope": "tet4-total-lagrangian-structural-v2",
                "maturity": "research",
            }
        )
        return SolveResult(
            status="success",
            displacements=displacement,
            dofs=dofs,
            mesh_report=report,
            node_count=model.node_count,
            element_count=len(model.elements),
            analysis="geometric_nonlinear_static",
            method="newton_raphson",
            message="Total-Lagrangian TET4 dead-load equilibrium converged.",
            solver=diagnostics,
            element_results=element_results,
        )

    @staticmethod
    def _validate_scope(model: FiniteElementModel) -> None:
        if not model.elements or {element.type for element in model.elements} != {"TET4"}:
            raise InputValidationError(
                "geometric_nonlinear_static currently supports TET4 elements exclusively."
            )
        material_names = {element.material for element in model.elements}
        if len(material_names) != 1:
            raise InputValidationError(
                "geometric_nonlinear_static currently requires one homogeneous material."
            )
        material = model.materials[next(iter(material_names))]
        if str(material.get("type", "")) != "isotropic_3d":
            raise InputValidationError(
                "geometric_nonlinear_static requires material type 'isotropic_3d'."
            )
        if model.distributed_loads:
            raise InputValidationError(
                "geometric_nonlinear_static currently accepts nodal dead loads only."
            )


def _newton_dead_load(
    assembly: TotalLagrangianTet4Assembly,
    external: np.ndarray,
    fixed: np.ndarray,
    *,
    increments: int,
    tolerance: float,
    max_iterations: int,
) -> tuple[np.ndarray, dict[str, object]]:
    if fixed.size == 0:
        raise MeshValidationError("geometric_nonlinear_static requires constrained dofs.")
    free = np.setdiff1d(np.arange(assembly.ndof), fixed)
    displacement = np.zeros(assembly.ndof, dtype=float)
    history: list[dict[str, object]] = []
    total_iterations = 0
    for step in range(1, increments + 1):
        target = (step / increments) * external
        scale = max(float(np.linalg.norm(target[free])), 1.0)
        for iteration in range(1, max_iterations + 1):
            internal, tangent = assembly.assemble(displacement)
            assert tangent is not None
            residual = target - internal
            relative = float(np.linalg.norm(residual[free]) / scale)
            if relative <= tolerance:
                break
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", MatrixRankWarning)
                    correction = spsolve(tangent[free, :][:, free], residual[free])
            except MatrixRankWarning as exc:
                raise NumericalConvergenceError(
                    f"Geometric nonlinear tangent is singular at increment {step}."
                ) from exc
            if not np.all(np.isfinite(correction)):
                raise NumericalConvergenceError(
                    f"Geometric nonlinear correction is non-finite at increment {step}."
                )
            displacement = _line_search(
                assembly, displacement, free, correction, target, np.linalg.norm(residual[free])
            )
            total_iterations += 1
        else:
            raise NumericalConvergenceError(
                f"Geometric nonlinear solve did not converge at increment {step}; "
                f"relative residual={relative:.6e}."
            )
        history.append(
            {
                "increment": step,
                "load_factor": step / increments,
                "iterations": iteration,
                "relative_residual": relative,
                "minimum_det_f": float(np.min(assembly.deformation_determinants(displacement))),
            }
        )
    return displacement, {
        "converged": True,
        "newton_iterations": total_iterations,
        "final_relative_residual": history[-1]["relative_residual"],
        "increments": history,
    }


def _line_search(
    assembly: TotalLagrangianTet4Assembly,
    displacement: np.ndarray,
    free: np.ndarray,
    correction: np.ndarray,
    target: np.ndarray,
    residual_norm: float,
) -> np.ndarray:
    alpha = 1.0
    for _ in range(14):
        trial = displacement.copy()
        trial[free] += alpha * correction
        try:
            internal, _ = assembly.assemble(trial, tangent_required=False)
        except ValueError:
            alpha *= 0.5
            continue
        if np.linalg.norm((target - internal)[free]) < residual_norm:
            return trial
        alpha *= 0.5
    raise NumericalConvergenceError("Geometric nonlinear line search failed to reduce the residual.")
