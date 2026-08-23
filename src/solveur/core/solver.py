"""Linear static solver."""

from __future__ import annotations

from time import perf_counter
from typing import Any

import numpy as np

from solveur.contact.solver import FrictionlessActiveSetSolver
from solveur.core.assembler import GlobalAssembler
from solveur.core.constraints import ConstraintReduction, recover_constraint_forces
from solveur.core.audit import SolverAudit
from solveur.core.audit import static_equilibrium_summary
from solveur.core.errors import MeshValidationError, NumericalConvergenceError
from solveur.core.linear_methods import LinearSystemSolver
from solveur.core.linear_policy import LinearSolverPolicy, linear_execution_settings
from solveur.core.model import FiniteElementModel
from solveur.core.results import SolveResult
from solveur.core.solver_backend import select_backend
from solveur.mesh.validation import MeshValidator
from solveur.post.audit import PostProcessingAuditor
from solveur.post.stress import StressPostProcessor


class LinearStaticSolver:
    """Validate, assemble and solve a linear static finite element model."""

    def __init__(self) -> None:
        self.validator = MeshValidator()
        self.assembler = GlobalAssembler()
        self.linear_solver = LinearSystemSolver()
        self.post = StressPostProcessor()
        self.post_auditor = PostProcessingAuditor()

    def solve(self, model: FiniteElementModel, *, detail_level: str = "full") -> SolveResult:
        if detail_level not in {"full", "summary"}:
            raise ValueError("detail_level must be 'full' or 'summary'.")
        include_detail = detail_level == "full"
        run_started = perf_counter()
        report = self.validator.validate(model)
        if report.status == "FAIL":
            raise MeshValidationError("Mesh validation failed: " + "; ".join(report.errors))
        dofs = model.dof_manager()
        assembly_started = perf_counter()
        plan = self.assembler.prepare_plan(model, dofs)
        stiffness = self.assembler.assemble_stiffness(model, dofs, plan=plan)
        loads = self.assembler.assemble_loads(model, dofs)
        fixed = self.assembler.fixed_indices(model, dofs)
        assembly_seconds = perf_counter() - assembly_started
        contact_details: dict[str, object] | None = None
        solver_info: dict[str, Any]
        constraint_transform = None
        if model.contacts:
            contact_state = FrictionlessActiveSetSolver().solve(model, dofs, stiffness, loads, fixed)
            free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
            reduced = contact_state.reduced_stiffness
            displacement = contact_state.displacement
            internal = contact_state.internal_force
            loads = contact_state.applied_loads
            contact_details = contact_state.details
            solver_info = {
                "method": str(contact_details["method"]),
                "iterations": contact_details["iteration_count"],
                "converged": contact_details["converged"],
                "residual_norm": 0.0,
            }
        else:
            reduction = ConstraintReduction.from_system(
                dofs, stiffness, loads, model.linear_constraints(), fixed
            )
            free = reduction.independent
            reduced = reduction.matrix
            requested_method = model.analysis.method
            selection = LinearSolverPolicy.assess(reduced, requested_method, model.analysis.parameters)
            LinearSolverPolicy.enforce_method_contract(selection, model.analysis.parameters)
            backend_selection = select_backend(
                model.analysis.parameters.get("backend", "auto"),
                problem_size=reduced.shape[0],
                parameters=model.analysis.parameters,
            )
            effective_method = (
                selection.recommended_method if requested_method in LinearSolverPolicy._AUTO else requested_method
            )
            linear_started = perf_counter()
            solution, info = self.linear_solver.solve(
                reduced,
                reduction.rhs,
                method=effective_method,
                parameters=model.analysis.parameters,
            )
            if not info.converged:
                raise NumericalConvergenceError(
                    f"Linear method {info.method} did not converge; residual={info.residual_norm:.6e}."
                )
            displacement = reduction.expand(solution)
            internal = stiffness @ displacement
            constraint_transform = reduction.transform
            solver_info = info.to_dict()
            solver_info["selection"] = selection.to_dict(used_method=info.method)
            solver_info["execution"] = linear_execution_settings(
                requested_method,
                model.analysis.parameters,
                used_method=info.method,
            )
            solver_info["execution"]["used_method"] = info.method
            solver_info["execution"]["backend_used"] = info.backend
            solver_info["execution"]["fallback_used"] = backend_selection.fallback_used
            solver_info["execution"]["linear_solve_seconds"] = perf_counter() - linear_started
            solver_info["backend"] = backend_selection.to_dict()
        if not np.all(np.isfinite(displacement)):
            raise NumericalConvergenceError("Linear solve produced non-finite displacements.")
        element_results = self.post.element_results(model, dofs, displacement) if include_detail else []
        nodal_results = self.post.nodal_results(model, element_results) if include_detail else []
        post_results = (
            self.post_auditor.element_audits(model, dofs, displacement, element_results)
            if include_detail
            else []
        )
        residual = internal - loads
        reactions = np.zeros_like(residual)
        reactions[fixed] = residual[fixed]
        ground_reactions = -self.assembler.ground_spring_internal_force(model, dofs, displacement)
        reactions += ground_reactions
        constraint_forces, fixed_constraint_reactions, constraint_summary = recover_constraint_forces(
            stiffness,
            loads,
            displacement,
            dofs,
            model.linear_constraints(),
            fixed,
            residual_override=residual if model.contacts else None,
        )
        equilibrium = static_equilibrium_summary(
            model=model,
            dofs=dofs,
            loads=loads,
            internal=internal,
            displacement=displacement,
            fixed=fixed,
            free=free,
            constraint_transform=constraint_transform,
            ground_spring_reactions=ground_reactions,
            fixed_constraint_reactions=fixed_constraint_reactions,
        )
        from solveur.loads.integration import load_balance

        resultant, moment = load_balance(model, dofs, constraint_forces)
        residual_resultant, residual_moment = load_balance(model, dofs, residual)
        force_imbalance = residual_resultant + resultant
        moment_imbalance = residual_moment + moment
        force_scale = max(float(np.linalg.norm(residual_resultant)), float(np.linalg.norm(resultant)), 1.0)
        moment_scale = max(float(np.linalg.norm(residual_moment)), float(np.linalg.norm(moment)), 1.0)
        constraint_summary["generalized_force_norm"] = float(np.linalg.norm(constraint_forces))
        constraint_summary["resultant"] = resultant.tolist()
        constraint_summary["moment_about_origin"] = moment.tolist()
        constraint_summary["residual_resultant"] = residual_resultant.tolist()
        constraint_summary["residual_moment_about_origin"] = residual_moment.tolist()
        constraint_summary["global_force_closure_relative_error"] = float(np.linalg.norm(force_imbalance) / force_scale)
        constraint_summary["global_moment_closure_relative_error"] = float(np.linalg.norm(moment_imbalance) / moment_scale)
        equilibrium["constraint_forces"] = constraint_summary
        if contact_details is not None:
            _apply_contact_moment_transport(equilibrium, contact_details, moment_scale)
        audit = SolverAudit.from_state(
            model=model,
            dofs=dofs,
            report=report,
            fixed=fixed,
            free=free,
            method=str(solver_info["method"]),
            vectors={
                "loads": loads,
                "displacements": displacement,
                "internal_force": internal,
                "residual": residual,
                "reactions": reactions,
            },
            load_assembly=self.assembler.last_load_diagnostics,
            matrices={"stiffness": stiffness, "reduced_stiffness": reduced},
            equilibrium=equilibrium,
            post_results=post_results,
            solver_selection=dict(solver_info.get("selection", {})),
            include_element_audits=include_detail,
            include_element_dofs=include_detail,
            notes=([] if include_detail else ["Summary audit: element-wise audit and full nodal serialization omitted."]),
        )
        solver_info.setdefault("execution", {})
        solver_info["execution"]["assembly_seconds"] = assembly_seconds
        solver_info["execution"]["total_seconds"] = perf_counter() - run_started
        solver_info["execution"]["resource_estimate"] = dict(solver_info.get("selection", {}).get("resource_estimate", {}))
        return SolveResult(
            status="PASS",
            displacements=displacement,
            dofs=dofs,
            mesh_report=report,
            node_count=model.node_count,
            element_count=len(model.elements),
            method=str(solver_info["method"]),
            solver={
                **solver_info,
                "load_assembly": dict(self.assembler.last_load_diagnostics),
                "multipoint_constraints": (
                    reduction.diagnostics if not model.contacts else {"strategy": "not_applicable_for_contact"}
                ),
                "contact": contact_details or {},
            },
            element_results=element_results,
            nodal_results=nodal_results,
            audit=audit,
        )


def _apply_contact_moment_transport(
    equilibrium: dict[str, object], contact_details: dict[str, object], moment_scale: float
) -> None:
    """Correct the reference-position moment of a tangential contact force.

    In the frozen-normal small-displacement model, the slave starts at an
    initial normal gap while the contact force acts at the projected master
    point once closed.  Nodal force summation at the *initial* slave position
    creates the artificial couple ``g0 * n x ft``.  The correction keeps the
    raw value visible and supplies a contact-work-consistent global moment
    closure for the audit.
    """
    rows = contact_details.get("contacts", [])
    correction: np.ndarray = np.zeros(3, dtype=float)
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            normal = np.asarray(row.get("normal", (0.0, 0.0, 0.0)), dtype=float)
            tangential = np.asarray(row.get("tangential_force", (0.0, 0.0)), dtype=float)
            tangent_one = np.asarray(row.get("tangent_one", (0.0, 0.0, 0.0)), dtype=float)
            tangent_two = np.asarray(row.get("tangent_two", (0.0, 0.0, 0.0)), dtype=float)
            if normal.shape != (3,) or tangent_one.shape != (3,) or tangent_two.shape != (3,) or tangential.shape != (2,):
                continue
            force = tangential[0] * tangent_one + tangential[1] * tangent_two
            correction -= float(row.get("initial_gap", 0.0)) * np.cross(normal, force)
    raw = np.asarray(equilibrium.get("moment_imbalance_about_origin", (0.0, 0.0, 0.0)), dtype=float)
    corrected = raw + correction
    equilibrium["raw_moment_imbalance_about_origin"] = raw.tolist()
    equilibrium["contact_reference_moment_correction"] = correction.tolist()
    equilibrium["moment_imbalance_about_origin"] = corrected.tolist()
    equilibrium["moment_balance_relative_error"] = float(np.linalg.norm(corrected) / moment_scale)
