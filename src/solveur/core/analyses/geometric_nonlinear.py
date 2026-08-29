"""Public geometrically nonlinear TET4 static solver."""

from __future__ import annotations

import numpy as np

from solveur.contact.solver import assemble_penalty_contact
from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError, MeshValidationError
from solveur.core.analyses.geometric_nonlinear_controls import GeometricNonlinearControls
from solveur.core.assembly.geometric import (
    TotalLagrangianHighOrderAssembly,
    build_total_lagrangian_assembly,
)
from solveur.core.nonlinear.iteration import (
    CompositeNonlinearAssembly,
    NonlinearAssemblyProtocol,
    _line_search_assembly,
    solve_adaptive_full_newton,
    solve_full_newton,
)
from solveur.core.nonlinear.controls import AdaptiveLoadControls
from solveur.core.nonlinear.robustness import NonlinearRobustnessOptions
from solveur.core.model import FiniteElementModel
from solveur.core.results import SolveResult
from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.elements.solid.hex8_total_lagrangian_batch import TotalLagrangianHex8Assembly
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
        geometric_assembly = build_total_lagrangian_assembly(model)
        contact_assembly = _PenaltyContactAssembly(model, dofs) if model.contacts else None
        assembly: NonlinearAssemblyProtocol = (
            CompositeNonlinearAssembly((geometric_assembly, contact_assembly))
            if contact_assembly is not None
            else geometric_assembly
        )
        external: np.ndarray = np.zeros(assembly.ndof, dtype=float)
        for load in model.loads:
            external[dofs.index(load.node, load.dof)] += load.value
        fixed = np.unique(
            [dofs.index(condition.node, name) for condition in model.fixed_dofs for name in condition.dofs]
        )
        adaptive_controls = (
            AdaptiveLoadControls.from_parameters(
                parameters,
                load_steps=controls.load_increments,
                max_iterations=max_iterations,
            )
            if bool(parameters.get("adaptive_load_steps", False))
            else None
        )
        robustness_options = NonlinearRobustnessOptions.from_parameters(parameters)
        displacement, diagnostics = _newton_dead_load(
            assembly,
            external,
            fixed,
            increments=controls.load_increments,
            tolerance=tolerance,
            max_iterations=max_iterations,
            determinant_assembly=geometric_assembly,
            adaptive_controls=adaptive_controls,
            robustness_options=robustness_options,
        )
        states = geometric_assembly.element_states(displacement)
        element_results = [
            {
                "index": index,
                "type": f"{model.elements[index].type}_TOTAL_LAGRANGIAN",
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
                "adaptive_load_steps": adaptive_controls is not None,
                "strain_energy": geometric_assembly.strain_energy(displacement),
                "minimum_det_f": float(np.min(states["det_f"])),
                "scope": (
                    {
                        "TET4": "tet4-total-lagrangian-structural-v2",
                        "TET10": "tet10-total-lagrangian-structural-research",
                        "HEX8": "hex8-total-lagrangian-structural-v1",
                        "HEX20": "hex20-total-lagrangian-structural-research",
                    }[next(iter({element.type for element in model.elements}))]
                ),
                "maturity": "research",
            }
        )
        assembly_diagnostics = getattr(geometric_assembly, "assembly_diagnostics", None)
        if callable(assembly_diagnostics):
            diagnostics["sparse_assembly"] = assembly_diagnostics()
        if contact_assembly is not None:
            diagnostics["contact"] = dict(contact_assembly.last_details)
        return SolveResult(
            status="success",
            displacements=displacement,
            dofs=dofs,
            mesh_report=report,
            node_count=model.node_count,
            element_count=len(model.elements),
            analysis="geometric_nonlinear_static",
            method="newton_raphson",
            message="Total-Lagrangian dead-load equilibrium converged.",
            solver=diagnostics,
            element_results=element_results,
        )

    @staticmethod
    def _validate_scope(model: FiniteElementModel) -> None:
        families = {element.type for element in model.elements}
        if not families or not families <= {"TET4", "TET10", "HEX8", "HEX20"}:
            raise InputValidationError(
                "geometric_nonlinear_static supports TET4, TET10, HEX8 and HEX20."
            )
        if len(families) != 1:
            raise InputValidationError(
                "geometric_nonlinear_static currently requires one homogeneous element family."
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
        if model.contacts:
            if str(model.analysis.parameters.get("contact_mode", "")).lower() != "penalty":
                raise InputValidationError(
                    "geometric_nonlinear_static contact requires explicit contact_mode='penalty'."
                )
            if any(contact.friction_coefficient > 0.0 for contact in model.contacts):
                raise InputValidationError(
                    "geometric_nonlinear_static currently supports frictionless contact only."
                )


class _PenaltyContactAssembly:
    """Adapt the existing sparse penalty contribution to the geometric driver."""

    def __init__(self, model: FiniteElementModel, dofs: DofManager) -> None:
        self.model = model
        self.dofs = dofs
        self.ndof = dofs.ndof
        self.last_details: dict[str, object] = {}

    def assemble(
        self, displacement: np.ndarray, *, tangent_required: bool = True
    ) -> tuple[np.ndarray, object | None]:
        internal, tangent, details = assemble_penalty_contact(
            self.model,
            self.dofs,
            displacement,
            penalty=float(self.model.analysis.parameters.get("contact_penalty", 1.0e6)),
        )
        self.last_details = details
        return internal, tangent if tangent_required else None


def _newton_dead_load(
    assembly: NonlinearAssemblyProtocol,
    external: np.ndarray,
    fixed: np.ndarray,
    *,
    increments: int,
    tolerance: float,
    max_iterations: int,
    determinant_assembly: TotalLagrangianTet4Assembly | TotalLagrangianHex8Assembly | TotalLagrangianHighOrderAssembly | None = None,
    adaptive_controls: AdaptiveLoadControls | None = None,
    robustness_options: NonlinearRobustnessOptions | None = None,
) -> tuple[np.ndarray, dict[str, object]]:
    if fixed.size == 0:
        raise MeshValidationError("geometric_nonlinear_static requires constrained dofs.")
    if adaptive_controls is None:
        displacement, diagnostics = solve_full_newton(
            assembly,
            external,
            fixed,
            increments=increments,
            tolerance=tolerance,
            max_iterations=max_iterations,
            robustness_options=robustness_options,
        )
    else:
        displacement, diagnostics = solve_adaptive_full_newton(
            assembly,
            external,
            fixed,
            increments=increments,
            tolerance=tolerance,
            max_iterations=max_iterations,
            controls=adaptive_controls,
            robustness_options=robustness_options,
        )
    determinant_source: object = determinant_assembly or assembly
    deformation_determinants = getattr(determinant_source, "deformation_determinants", None)
    increment_items = diagnostics.get("increments")
    if callable(deformation_determinants) and isinstance(increment_items, list):
        minimum_det_f = float(np.min(deformation_determinants(displacement)))
        for item in increment_items:
            if isinstance(item, dict):
                item["minimum_det_f"] = minimum_det_f
    return displacement, diagnostics


def _line_search(
    assembly: TotalLagrangianTet4Assembly | TotalLagrangianHex8Assembly | TotalLagrangianHighOrderAssembly,
    displacement: np.ndarray,
    free: np.ndarray,
    correction: np.ndarray,
    target: np.ndarray,
    residual_norm: float,
) -> np.ndarray:
    """Compatibility wrapper for the shared Newton line-search contract."""
    return _line_search_assembly(assembly, displacement, free, correction, target, residual_norm)
