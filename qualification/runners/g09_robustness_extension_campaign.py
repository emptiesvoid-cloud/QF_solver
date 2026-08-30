"""Campaign helpers for the 026-G09 robustness extension."""

from __future__ import annotations

# The repository path bootstrap is required before importing the core module.
# ruff: noqa: E402,F401

import sys
from pathlib import Path

_IMPL_ROOT = Path(__file__).resolve().parents[2]
if str(_IMPL_ROOT) not in sys.path:
    sys.path.insert(0, str(_IMPL_ROOT))
if str(_IMPL_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_IMPL_ROOT / "src"))

from .g09_robustness_extension_core import (
    Any,
    COMPARISON_TOLERANCE,
    DETERMINISM_LIMIT,
    EQUILIBRIUM_LIMIT,
    FiniteElementModel,
    FrictionlessContact,
    GATE,
    LOT,
    MESH_LEVELS,
    MaterialStateSession,
    NonlinearSolverOptions,
    NonlinearStaticSolver,
    NumericalConvergenceError,
    PENALTIES,
    ROOT,
    SOURCE_SHA_DEFAULT,
    UTC,
    _artifact_paths,
    _bare_contact_model,
    _canonical,
    _distorted_spring_model,
    _finite,
    _geometry_solver_row,
    _git,
    _mesh_contact_model,
    _multi_face_patch_model,
    _now,
    _result_metrics,
    _rotated_spring_model,
    _rotation,
    _run_activation_matrix,
    _run_adversarial,
    _run_contact_cutback,
    _run_cycle_base,
    _run_geometry_matrix,
    _run_observed_path,
    _run_penalty_mesh_matrix,
    _sha256,
    _solve_contact_case,
    _solve_contact_case_with_equilibrium,
    _source_state,
    _unsupported_route,
    argparse,
    assemble_penalty_contact,
    build_nonlinear_assembly_plan,
    datetime,
    hashlib,
    initial_material_states,
    json,
    math,
    np,
    solve_model,
    state_digest,
    subprocess,
)

def _run_cycle(path: tuple[float, ...], name: str) -> dict[str, Any]:
    """Add an explicit penalty-energy/work trace to the existing cycle probe."""
    row = _run_cycle_base(path, name)
    result = solve_model(_mesh_contact_model(1, penalty=1.0e5, load_path=path), enforce_policy=False)
    steps = result.to_dict()["solver"]["steps"]
    penalty_energy = [0.5 * 1.0e5 * max(-float(gap), 0.0) ** 2 for gap in row["gaps_by_step"]]
    work_imbalance = [float(step.get("relative_work_imbalance", 0.0)) for step in steps]
    row["penalty_energy_by_step"] = penalty_energy
    row["energy_trace_valid"] = all(np.isfinite(value) and value >= 0.0 for value in penalty_energy)
    row["work_trace_finite"] = all(np.isfinite(value) and value >= 0.0 for value in work_imbalance)
    row["relative_work_imbalance_by_step"] = work_imbalance
    row["status"] = (
        row["status"]
        if row["energy_trace_valid"] and row["work_trace_finite"]
        else "FAIL"
    )
    return row


def _run_long_cycles() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for cycles, amplitude in ((10, 1.0), (20, 1.0), (50, 1.0), (10, 0.5)):
        path: list[float] = [0.0]
        for _ in range(cycles):
            path.extend((amplitude, 0.0))
        row = _run_cycle(tuple(path), f"{cycles}_cycles_amp_{amplitude:g}")
        row["cycle_count"] = cycles
        row["amplitude"] = amplitude
        rows.append(row)
    return {
        "rows": rows,
        "all_pass": all(row["status"] == "PASS_INTERNAL_RESEARCH" for row in rows),
        "determinism": all(row["final_reference_relative_difference"] <= DETERMINISM_LIMIT for row in rows),
        "limitation": "Load-path cycling probes stateless frictionless contact, not material cyclicity.",
    }

def _run_rollback_matrix() -> dict[str, Any]:
    rows = [
        _run_contact_cutback(-20.0, 1, 1.0),
        _run_contact_cutback(-30.0, 1, 1.0),
        _run_contact_cutback(-20.0, 2, 0.5),
        _run_contact_cutback(-20.0, 3, 0.25),
    ]
    return {
        "rows": rows,
        "all_pass": all(row["status"] == "PASS_INTERNAL_ROLLBACK" for row in rows),
        "state_integrity": all(row["clean_retry"] for row in rows),
        "limitation": "Contact active set is recomputed; common driver displacement/material transaction is checked.",
    }


def _contact_phase(model: FiniteElementModel, dofs: Any, displacement: np.ndarray, penalty: float) -> dict[str, Any]:
    """Observe active-set status without adding persistent contact state."""
    _, _, details = assemble_penalty_contact(model, dofs, displacement, penalty=penalty)
    gaps = [float(value) for value in details.get("gaps", [])]
    active = [int(value) for value in details.get("active_contacts", [])]
    return {
        "active": bool(active),
        "active_contacts": active,
        "gaps": gaps,
        "penetration": max(-min(gaps, default=0.0), 0.0),
    }


def _run_transactional_contact_path(
    model: FiniteElementModel,
    path: tuple[float, ...],
    *,
    reject_attempt: int | None = None,
) -> dict[str, Any]:
    """Run a fixed path with explicit trial/commit/rollback transactions.

    This is a verification-only driver. It reuses the production assembly and
    load-step routine while keeping the cutback orchestration local to the
    evidence harness, because the production adaptive route intentionally
    accepts monotonic paths only.
    """

    class PhaseRejectingSolver(NonlinearStaticSolver):
        def __init__(self, injected_attempt: int | None) -> None:
            super().__init__()
            self.injected_attempt = injected_attempt
            self.attempts = 0
            self.rejected = False
            self.failed_candidate: dict[str, Any] = {}
            self.failed_trial_state_digest = ""
            self.failed_trial_displacement_norm = 0.0

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
        ) -> Any:
            self.attempts += 1
            info = super()._solve_load_step(
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
            if (
                self.injected_attempt is not None
                and not self.rejected
                and self.attempts == self.injected_attempt
            ):
                self.failed_candidate = info.to_dict()
                self.failed_trial_state_digest = state_digest(material_states)
                self.failed_trial_displacement_norm = float(np.linalg.norm(displacement))
                displacement[:] = 123.0
                first_element = min(material_states)
                material_states[first_element][0]["equivalent_plastic_strain"] = 999.0
                self.rejected = True
                raise NumericalConvergenceError(
                    "Controlled phase-specific contact increment rejection."
                )
            return info

    solver = PhaseRejectingSolver(reject_attempt)
    report = solver.validator.validate(model)
    if report.status == "FAIL":
        raise RuntimeError("Contact phase model validation failed: " + "; ".join(report.errors))
    dofs = model.dof_manager()
    loads = solver.assembler.assemble_loads(model, dofs)
    fixed = solver.assembler.fixed_indices(model, dofs)
    free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
    solver._validate_kinematics_scope(model, model.analysis.parameters)
    solver._assembly_plan = build_nonlinear_assembly_plan(model, dofs)
    options = NonlinearSolverOptions.from_parameters(model.analysis.parameters)
    solver._rejected_increments = 0
    solver._rejection_log = []
    displacement = np.zeros(dofs.ndof, dtype=float)
    material_states = initial_material_states(model)
    reference_force_norm = max(float(np.linalg.norm(loads[free])), 1.0)
    penalty = float(model.analysis.parameters["contact_penalty"])
    current_factor = 0.0
    history: list[dict[str, Any]] = []
    transactions: list[dict[str, Any]] = []
    rejected = 0
    for path_index, target_factor in enumerate(path, start=1):
        trial = displacement.copy()
        session = MaterialStateSession(material_states)
        trial_states = session.begin_trial()
        committed_digest = state_digest(material_states)
        committed_displacement = displacement.copy()
        before_contact = _contact_phase(model, dofs, displacement, penalty)
        try:
            info = solver._solve_load_step(
                model,
                dofs,
                trial,
                free,
                target_factor * loads,
                trial_states,
                len(history) + 1,
                target_factor,
                target_factor - current_factor,
                None,
                options.max_iterations,
                options.tolerance,
                options.linear_method,
                options.line_search_min_alpha,
                options.line_search_max_reductions,
                options.line_search_c,
                current_factor * loads,
                reference_force_norm,
            )
        except NumericalConvergenceError as error:
            session.rollback()
            rejected += 1
            rollback_digest = state_digest(material_states)
            transactions.append(
                {
                    "path_index": path_index,
                    "base_factor": current_factor,
                    "target_factor": target_factor,
                    "before_contact": before_contact,
                    "failed_trial": solver.failed_candidate,
                    "failed_trial_contact": {
                        "active": bool(solver.failed_candidate.get("contact_active_contacts", [])),
                        "active_contacts": solver.failed_candidate.get("contact_active_contacts", []),
                        "gaps": solver.failed_candidate.get("contact_gaps", []),
                    },
                    "failure": type(error).__name__,
                    "rollback_digest": rollback_digest,
                    "committed_digest": committed_digest,
                    "state_preserved": rollback_digest == committed_digest,
                    "displacement_preserved": bool(np.array_equal(displacement, committed_displacement)),
                    "failed_trial_state_digest": solver.failed_trial_state_digest,
                    "failed_trial_displacement_norm": solver.failed_trial_displacement_norm,
                }
            )
            midpoint = current_factor + 0.5 * (target_factor - current_factor)
            solver._rejection_log.append(
                {
                    "base_load_factor": current_factor,
                    "rejected_increment": target_factor - current_factor,
                    "retry_increment": midpoint - current_factor,
                    "failure_reason": type(error).__name__,
                }
            )
            retry_trial = displacement.copy()
            retry_session = MaterialStateSession(material_states)
            retry_states = retry_session.begin_trial()
            retry_info = solver._solve_load_step(
                model,
                dofs,
                retry_trial,
                free,
                midpoint * loads,
                retry_states,
                len(history) + 1,
                midpoint,
                midpoint - current_factor,
                None,
                options.max_iterations,
                options.tolerance,
                options.linear_method,
                options.line_search_min_alpha,
                options.line_search_max_reductions,
                options.line_search_c,
                current_factor * loads,
                reference_force_norm,
            )
            displacement[:] = retry_trial
            retry_session.commit()
            history.append(retry_info.to_dict())
            current_factor = midpoint
            retry_trial = displacement.copy()
            retry_session = MaterialStateSession(material_states)
            retry_states = retry_session.begin_trial()
            retry_info = solver._solve_load_step(
                model,
                dofs,
                retry_trial,
                free,
                target_factor * loads,
                retry_states,
                len(history) + 1,
                target_factor,
                target_factor - current_factor,
                None,
                options.max_iterations,
                options.tolerance,
                options.linear_method,
                options.line_search_min_alpha,
                options.line_search_max_reductions,
                options.line_search_c,
                current_factor * loads,
                reference_force_norm,
            )
            displacement[:] = retry_trial
            retry_session.commit()
            history.append(retry_info.to_dict())
            current_factor = target_factor
            continue
        displacement[:] = trial
        session.commit()
        history.append(info.to_dict())
        current_factor = target_factor
    final_contact = _contact_phase(model, dofs, displacement, penalty)
    return {
        "status": "PASS" if current_factor == path[-1] else "FAIL",
        "attempts": solver.attempts,
        "rejected_increments": rejected,
        "history": history,
        "transactions": transactions,
        "final_displacement": displacement.copy(),
        "final_contact": final_contact,
        "rejection_log": list(solver._rejection_log),
    }


def _run_phase_rollback_matrix() -> dict[str, Any]:
    """Check rollback around activation, separation and recontact transitions."""
    cases = {
        "before_activation": ((0.10,), 1),
        "during_activation": ((0.10, 0.25), 2),
        "just_after_activation": ((0.10, 0.25, 0.75), 3),
        "during_separation": ((0.10, 0.25, 0.75, 0.0), 4),
        "during_recontact": ((0.10, 0.25, 0.75, 0.0, 0.25), 5),
    }
    rows: list[dict[str, Any]] = []
    for phase, (path, reject_step) in cases.items():
        model = _mesh_contact_model(
            1,
            penalty=1.0e5,
            load=-20.0,
            load_path=None,
            max_iterations=80,
            path_dependent=True,
        )
        observed = _run_transactional_contact_path(model, path, reject_attempt=reject_step)
        expanded_path: list[float] = []
        current = 0.0
        for index, target in enumerate(path, start=1):
            if index == reject_step:
                expanded_path.append(current + 0.5 * (target - current))
            expanded_path.append(target)
            current = target
        reference_model = _mesh_contact_model(
            1,
            penalty=1.0e5,
            load=-20.0,
            load_path=None,
            max_iterations=80,
            path_dependent=True,
        )
        reference = _run_transactional_contact_path(reference_model, tuple(expanded_path))
        reference_error = float(
            np.linalg.norm(observed["final_displacement"] - reference["final_displacement"])
            / max(np.linalg.norm(reference["final_displacement"]), 1.0e-15)
        )
        transaction = observed["transactions"][-1] if observed["transactions"] else {}
        energy_trace = [
            0.5 * 1.0e5 * max(-float(gap), 0.0) ** 2
            for step in observed["history"]
            for gap in step.get("contact_gaps", [])[:1]
        ]
        energy_trace.extend(
            0.5 * 1.0e5 * max(-float(gap), 0.0) ** 2
            for gap in transaction.get("failed_trial_contact", {}).get("gaps", [])[:1]
        )
        work_trace = [float(step.get("relative_work_imbalance", 0.0)) for step in observed["history"]]
        energy_trace_valid = all(np.isfinite(value) and value >= 0.0 for value in energy_trace)
        work_trace_finite = all(np.isfinite(value) and value >= 0.0 for value in work_trace)
        rows.append(
            {
                "phase": phase,
                "path": list(path),
                "expanded_reference_path": expanded_path,
                "reject_step": reject_step,
                "status": "PASS_INTERNAL_ROLLBACK"
                if observed["status"] == "PASS"
                and observed["rejected_increments"] == 1
                and transaction.get("state_preserved")
                and transaction.get("displacement_preserved")
                and energy_trace_valid
                and work_trace_finite
                and reference["status"] == "PASS"
                and reference_error <= COMPARISON_TOLERANCE
                else "FAIL",
                "attempts": observed["attempts"],
                "rejected_increments": observed["rejected_increments"],
                "before_contact": transaction.get("before_contact", {}),
                "failed_trial_contact": transaction.get("failed_trial_contact", {}),
                "rollback_digest": transaction.get("rollback_digest", ""),
                "committed_digest": transaction.get("committed_digest", ""),
                "state_preserved": bool(transaction.get("state_preserved", False)),
                "displacement_preserved": bool(transaction.get("displacement_preserved", False)),
                "failed_trial_state_digest": transaction.get("failed_trial_state_digest", ""),
                "failed_trial_displacement_norm": transaction.get("failed_trial_displacement_norm", 0.0),
                "penalty_energy_trace": energy_trace,
                "relative_work_imbalance_trace": work_trace,
                "energy_trace_valid": energy_trace_valid,
                "work_trace_finite": work_trace_finite,
                "final_contact": observed["final_contact"],
                "reference_final_contact": reference["final_contact"],
                "final_reference_relative_error": reference_error,
                "rejection_log": observed["rejection_log"],
                "contact_state_transaction": "N/A - frictionless active set is recomputed; displacement/material transaction checked",
            }
        )
    return {
        "rows": rows,
        "all_pass": all(row["status"] == "PASS_INTERNAL_ROLLBACK" for row in rows),
        "state_integrity": all(row["state_preserved"] and row["displacement_preserved"] for row in rows),
        "phase_coverage": [row["phase"] for row in rows],
        "limitation": "Contact active set is stateless; phase-specific rollback covers mutable common-driver state across activation, separation and recontact.",
    }
