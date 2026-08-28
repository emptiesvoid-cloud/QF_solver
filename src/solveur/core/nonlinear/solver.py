"""Nonlinear static solver."""

from __future__ import annotations


import numpy as np
from scipy.sparse import csr_matrix

from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.audit import SolverAudit, static_equilibrium_summary
from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError, MeshValidationError
from solveur.core.solvers.linear import LinearSystemSolver
from solveur.core.nonlinear.material_state import MaterialStateTable
from solveur.core.nonlinear.material_state import copy_material_states
from solveur.core.nonlinear.material_state import initial_material_states
from solveur.core.assembly.nonlinear import (
    NonlinearAssemblyPlan,
    assemble_internal_tangent,
    build_nonlinear_assembly_plan,
)
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.controls import (
    ArcLengthControls,
    NonlinearSolverOptions,
    validated_load_path,
)
from solveur.core.nonlinear.checkpoint import NonlinearCheckpointSession, NonlinearCheckpointStore
from solveur.core.nonlinear.arc_length import NonlinearArcLengthMixin
from solveur.core.nonlinear.load_control import NonlinearLoadControlMixin
from solveur.core.results import SolveResult
from solveur.mesh.validation import MeshValidator
from solveur.post.audit import PostProcessingAuditor
from solveur.post.stress import StressPostProcessor


class NonlinearStaticSolver(NonlinearArcLengthMixin, NonlinearLoadControlMixin):
    """Common load-control Newton driver for supported nonlinear solid elements."""

    supported_methods = ("newton_raphson", "modified_newton", "newton_line_search", "arc_length")

    def __init__(self, checkpoint_store: NonlinearCheckpointStore | None = None) -> None:
        self.validator = MeshValidator()
        self.assembler = GlobalAssembler()
        self.linear_solver = LinearSystemSolver()
        self.post = StressPostProcessor()
        self.post_auditor = PostProcessingAuditor()
        self.checkpoint_store = checkpoint_store
        self._assembly_plan: NonlinearAssemblyPlan | None = None

    def solve(self, model: FiniteElementModel) -> SolveResult:
        if model.analysis.method not in self.supported_methods:
            raise InputValidationError(f"Unsupported nonlinear method {model.analysis.method!r}.")

        self._assembly_plan = None
        report = self.validator.validate(model)
        if report.status == "FAIL":
            raise MeshValidationError("Mesh validation failed: " + "; ".join(report.errors))
        dofs = model.dof_manager()
        loads = self.assembler.assemble_loads(model, dofs)
        fixed = self.assembler.fixed_indices(model, dofs)
        free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
        if free.size == 0:
            raise MeshValidationError("No free degree of freedom remains after boundary conditions.")

        params = model.analysis.parameters
        self._validate_kinematics_scope(model, params)
        self._assembly_plan = build_nonlinear_assembly_plan(model, dofs)
        options = NonlinearSolverOptions.from_parameters(params)
        load_steps = options.load_steps
        max_iterations = options.max_iterations
        tolerance = options.tolerance
        linear_method = options.linear_method
        min_alpha = options.line_search_min_alpha
        max_reductions = options.line_search_max_reductions
        armijo = options.line_search_c
        adaptive = options.adaptive_load_steps
        load_path = validated_load_path(params, load_steps)
        if load_path is not None and adaptive:
            raise InputValidationError("analysis.load_path is not yet compatible with adaptive_load_steps.")
        if load_path is not None and model.analysis.method == "arc_length":
            raise InputValidationError("analysis.load_path is not compatible with arc_length.")
        checkpoint_requested = any(key in params for key in ("checkpoint_path", "restart_from"))
        if checkpoint_requested and adaptive:
            raise InputValidationError("Nonlinear checkpoint/restart currently requires fixed load-control steps.")
        self._rejected_increments = 0
        self._rejection_log: list[dict[str, object]] = []
        reference_force_norm = max(float(np.linalg.norm(loads[free])), 1.0)
        arc_length_controls = (
            ArcLengthControls.from_parameters(params, max_iterations=max_iterations)
            if model.analysis.method == "arc_length"
            else None
        )
        displacement = np.zeros(dofs.ndof, dtype=float)
        material_states = initial_material_states(model)
        checkpoint_session: NonlinearCheckpointSession | None = None
        completed_factors: list[float] = []
        if model.analysis.method == "arc_length":
            checkpoint_session = NonlinearCheckpointSession.create(
                model,
                max(1, int(params.get("max_arc_steps", max(load_steps * 4, load_steps + 1)))),
                self.checkpoint_store,
            )
            displacement, material_states, continuation_state = checkpoint_session.restore_continuation(
                displacement,
                material_states,
                float(params.get("target_load_factor", 1.0)),
                float(
                    params.get(
                        "arc_length_load_factor_limit",
                        max(abs(float(params.get("target_load_factor", 1.0))), 1.0),
                    )
                ),
            )
            history = self._solve_arc_length(
                model,
                dofs,
                displacement,
                free,
                loads,
                material_states,
                load_steps,
                max_iterations,
                tolerance,
                linear_method,
                checkpoint_session,
                continuation_state,
                arc_length_controls,
            )
        elif adaptive:
            history = self._solve_adaptive_load_steps(
                model,
                dofs,
                displacement,
                free,
                loads,
                material_states,
                load_steps,
                max_iterations,
                tolerance,
                linear_method,
                min_alpha,
                max_reductions,
                armijo,
            )
        else:
            history = []
            factors = load_path or [step / load_steps for step in range(1, load_steps + 1)]
            checkpoint_session = NonlinearCheckpointSession.create(model, len(factors), self.checkpoint_store)
            displacement, material_states = checkpoint_session.restore(displacement, material_states, factors)
            previous_factor = 0.0 if checkpoint_session.restart_step == 0 else factors[checkpoint_session.restart_step - 1]
            for step, load_factor in enumerate(
                factors[checkpoint_session.restart_step :], start=checkpoint_session.restart_step + 1
            ):
                target_load = load_factor * loads
                cached_tangent: csr_matrix | None = None
                history.append(
                    self._solve_load_step(
                        model,
                        dofs,
                        displacement,
                        free,
                        target_load,
                        material_states,
                        step,
                        load_factor,
                        load_factor - previous_factor,
                        cached_tangent,
                        max_iterations,
                        tolerance,
                        linear_method,
                        min_alpha,
                        max_reductions,
                        armijo,
                        previous_factor * loads,
                        reference_force_norm,
                    )
                )
                previous_factor = load_factor
                checkpoint_session.save(step, load_factor, displacement, material_states)
            completed_factors = list(factors)

        element_results = self.post.element_results(model, dofs, displacement, material_states)
        nodal_results = self.post.nodal_results(model, element_results)
        post_results = self.post_auditor.element_audits(model, dofs, displacement, element_results)
        internal, tangent, _ = self._assemble_internal_tangent(model, dofs, displacement, material_states)
        load_factor = completed_factors[-1] if completed_factors else (history[-1].load_factor if history else 1.0)
        external = load_factor * loads
        residual = internal - external
        reactions = np.zeros_like(residual)
        reactions[fixed] = residual[fixed]
        audit = SolverAudit.from_state(
            model=model,
            dofs=dofs,
            report=report,
            fixed=fixed,
            free=free,
            vectors={
                "reference_loads": loads,
                "final_external_load": external,
                "displacements": displacement,
                "final_internal_force": internal,
                "residual": residual,
                "reactions": reactions,
            },
            load_assembly=self.assembler.last_load_diagnostics,
            matrices={"final_tangent": tangent, "reduced_final_tangent": tangent[free, :][:, free]},
            equilibrium=static_equilibrium_summary(
                model=model,
                dofs=dofs,
                loads=loads,
                internal=internal,
                displacement=displacement,
                fixed=fixed,
                free=free,
                load_factor=load_factor,
            ),
            post_results=post_results,
            notes=["Nonlinear audit uses the tangent matrix at the converged final displacement."],
        )
        return SolveResult(
            status="PASS",
            displacements=displacement,
            dofs=dofs,
            mesh_report=report,
            node_count=model.node_count,
            element_count=len(model.elements),
            analysis="nonlinear_static",
            method=model.analysis.method,
            solver={
                "nonlinear_options": {
                    "load_steps": options.load_steps,
                    "max_iterations": options.max_iterations,
                    "tolerance": options.tolerance,
                    "linear_method": options.linear_method,
                    "line_search_min_alpha": options.line_search_min_alpha,
                    "line_search_max_reductions": options.line_search_max_reductions,
                    "line_search_c": options.line_search_c,
                    "adaptive_load_steps": options.adaptive_load_steps,
                },
                "adaptive_load_steps": adaptive,
                "arc_length": model.analysis.method == "arc_length",
                "adaptive_arc_length": bool(arc_length_controls and arc_length_controls.adaptive_radius),
                "arc_length_growth_factor": (
                    arc_length_controls.growth_factor if arc_length_controls else None
                ),
                "arc_length_shrink_factor": (
                    arc_length_controls.shrink_factor if arc_length_controls else None
                ),
                "arc_length_minimum_radius": (
                    arc_length_controls.minimum_radius if arc_length_controls else None
                ),
                "arc_length_stop_mode": str(params.get("arc_length_stop_mode", "target_load")).lower(),
                "arc_length_allow_load_factor_turning": bool(
                    params.get(
                        "arc_length_allow_load_factor_turning",
                        str(params.get("arc_length_stop_mode", "target_load")).lower() == "max_steps",
                    )
                ),
                "arc_length_load_factor_limit": float(
                    params.get(
                        "arc_length_load_factor_limit",
                        max(abs(float(params.get("target_load_factor", 1.0))), 1.0),
                    )
                ),
                "arc_length_control_dof": params.get("arc_length_control_dof"),
                "kinematics": str(params.get("kinematics", "small_strain")).lower(),
                "contact_mode": str(params.get("contact_mode", "none")).lower(),
                "contact_search_mode": str(params.get("contact_search_mode", "initial")).lower(),
                "path_dependent_material_state": bool(material_states),
                "load_path": completed_factors or [item.load_factor for item in history],
                "restart_step": checkpoint_session.restart_step if checkpoint_session else 0,
                "history_is_partial": bool(checkpoint_session and checkpoint_session.restart_step > 0),
                "checkpoint_path": checkpoint_session.settings.path if checkpoint_session else None,
                "checkpoint_files": checkpoint_session.files if checkpoint_session else [],
                "checkpoint_model_signature": checkpoint_session.signature if checkpoint_session else "",
                "rejected_increments": self._rejected_increments,
                "rejection_log": list(self._rejection_log),
                "load_assembly": dict(self.assembler.last_load_diagnostics),
                "steps": [item.to_dict() for item in history],
            },
            element_results=element_results,
            nodal_results=nodal_results,
            material_states=copy_material_states(material_states),
            audit=audit,
        )







    @staticmethod
    def _validate_kinematics_scope(model: FiniteElementModel, params: dict[str, object]) -> None:
        """Validate the supported common finite-kinematic nonlinear branches."""
        if model.contacts:
            contact_mode = str(params.get("contact_mode", "")).lower()
            if contact_mode != "penalty":
                raise InputValidationError(
                    "Nonlinear contact requires explicit contact_mode='penalty'; "
                    "the historical active-set solver is not silently reused."
                )
            if any(contact.friction_coefficient > 0.0 for contact in model.contacts):
                raise InputValidationError("The common nonlinear contact path is frictionless only.")
        kinematics = str(params.get("kinematics", "small_strain")).lower()
        if kinematics == "small_strain":
            return
        if kinematics not in {"total_lagrangian", "total_lagrangian_j2"}:
            raise InputValidationError(
                "nonlinear_static kinematics must be 'small_strain', 'total_lagrangian' "
                "or 'total_lagrangian_j2'."
            )
        if model.analysis.method == "modified_newton":
            raise InputValidationError(
                f"{kinematics} is qualified only with Full Newton; "
                "modified_newton remains outside the 0.2.5 production scope."
            )
        families = {element.type for element in model.elements}
        if not families or not families <= {"TET4", "TET10", "HEX8", "HEX20"}:
            raise InputValidationError(
                f"{kinematics} currently supports homogeneous TET4, TET10, HEX8 or HEX20 meshes."
            )
        if len(families) != 1:
            raise InputValidationError(
                f"{kinematics} currently requires one homogeneous element family."
            )
        material_types = {
            str(model.materials[element.material].get("type", "")).lower()
            for element in model.elements
        }
        expected_material = (
            "von_mises_elastoplastic_3d"
            if kinematics == "total_lagrangian_j2"
            else "isotropic_3d"
        )
        if material_types != {expected_material}:
            raise InputValidationError(
                f"{kinematics} requires material type '{expected_material}'."
            )

    def _assemble_internal_tangent(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        displacement: np.ndarray,
        material_states: MaterialStateTable | None = None,
        *,
        contact_diagnostics: dict[str, object] | None = None,
        timing: dict[str, float | int] | None = None,
    ) -> tuple[np.ndarray, csr_matrix, MaterialStateTable]:
        return assemble_internal_tangent(
            model,
            dofs,
            displacement,
            material_states,
            contact_diagnostics=contact_diagnostics,
            timing=timing,
            plan=self._assembly_plan,
        )
