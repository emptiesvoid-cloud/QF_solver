"""Deterministic adversarial checks for the shared Full Newton contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from unittest.mock import patch

import numpy as np
from scipy.sparse import csr_matrix

from solveur.api import solve_model
from solveur.contact.entities import FrictionlessContact
from solveur.core.buckling import LinearBucklingSolver
from solveur.core.errors import NumericalConvergenceError
from solveur.core.material_state import StateTransaction
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear import NonlinearStaticSolver
from solveur.core.nonlinear_contracts import NonlinearFailureReason
from solveur.core.nonlinear_iteration import solve_full_newton


@dataclass(frozen=True)
class FailureCaseResult:
    """Machine-readable outcome of one intentional solver failure."""

    name: str
    expected_reason: str
    observed_reason: str | None
    converged: bool
    diagnostics: dict[str, object]

    @property
    def passed(self) -> bool:
        return not self.converged and self.observed_reason == self.expected_reason

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "expected_reason": self.expected_reason,
            "observed_reason": self.observed_reason,
            "converged": self.converged,
            "passed": self.passed,
            "diagnostics": self.diagnostics,
        }


class _Assembly:
    ndof = 2

    def __init__(self, internal: Callable[[np.ndarray], np.ndarray], tangent: np.ndarray):
        self._internal = internal
        self._tangent = csr_matrix(tangent)

    def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
        return self._internal(np.asarray(displacement, dtype=float)), self._tangent


def _raising_internal(message: str) -> Callable[[np.ndarray], np.ndarray]:
    """Return a deterministic constitutive/assembly failure for the campaign."""

    def raise_failure(_displacement: np.ndarray) -> np.ndarray:
        raise ValueError(message)

    return raise_failure


def _run_case(
    name: str,
    expected_reason: NonlinearFailureReason,
    assembly: _Assembly,
    *,
    max_iterations: int = 3,
) -> FailureCaseResult:
    try:
        solve_full_newton(
            assembly,
            np.array([1.0, 0.0]),
            np.array([1]),
            increments=1,
            tolerance=1.0e-10,
            max_iterations=max_iterations,
        )
    except NumericalConvergenceError as error:
        payload = error.to_dict()
        return FailureCaseResult(
            name=name,
            expected_reason=expected_reason.value,
            observed_reason=payload["reason"],
            converged=bool(payload["converged"]),
            diagnostics=dict(payload["diagnostics"]),
        )
    return FailureCaseResult(
        name=name,
        expected_reason=expected_reason.value,
        observed_reason=None,
        converged=True,
        diagnostics={},
    )


def _run_min_increment_case() -> FailureCaseResult:
    """Exhaust adaptive cutbacks without allowing a partial result through."""

    model = FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "load_steps": 1,
            "max_iterations": 2,
            "tolerance": 1.0e-10,
            "adaptive_load_steps": True,
            "initial_load_increment": 1.0,
            "min_load_increment": 0.25,
            "max_load_increment": 1.0,
            "cutback_factor": 0.5,
            "max_cutbacks": 10,
        },
    )

    class AlwaysRejectSolver(NonlinearStaticSolver):
        """Inject a typed failed trial so the adaptive contract reaches its floor."""

        def _solve_load_step(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise NumericalConvergenceError(
                "controlled adaptive failure",
                reason=NonlinearFailureReason.MAX_ITERATIONS,
                diagnostics={"controlled": True},
            )

    try:
        AlwaysRejectSolver().solve(model)
    except NumericalConvergenceError as error:
        payload = error.to_dict()
        return FailureCaseResult(
            name="min_increment_reached",
            expected_reason=NonlinearFailureReason.MIN_INCREMENT_REACHED.value,
            observed_reason=payload["reason"],
            converged=bool(payload["converged"]),
            diagnostics={"solver": "full_newton", **dict(payload["diagnostics"])},
        )
    return FailureCaseResult(
        name="min_increment_reached",
        expected_reason=NonlinearFailureReason.MIN_INCREMENT_REACHED.value,
        observed_reason=None,
        converged=True,
        diagnostics={},
    )


def _run_state_corruption_case() -> dict[str, object]:
    """Verify that a committed-state mutation during a trial fails closed."""

    committed = {"active": [1], "multiplier": np.array([0.0])}
    transaction = StateTransaction(committed)
    transaction.begin_trial()
    committed["active"].append(2)
    try:
        transaction.rollback()
    except NumericalConvergenceError as error:
        payload = error.to_dict()
        return {
            "name": "state_corruption",
            "passed": payload.get("reason") == NonlinearFailureReason.STATE_CORRUPTION.value,
            "converged": bool(payload.get("converged", True)),
            "failure_reason": payload.get("reason"),
            "diagnostics": dict(payload.get("diagnostics", {})),
        }
    return {
        "name": "state_corruption",
        "passed": False,
        "converged": True,
        "failure_reason": None,
        "diagnostics": {},
    }


def _run_contact_retry_rollback_case() -> dict[str, object]:
    """Force one contact assembly failure and verify adaptive retry safety."""

    model = FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "j2"}],
        materials={
            "j2": {
                "type": "von_mises_elastoplastic_3d",
                "E": 1000.0,
                "nu": 0.3,
                "yield_stress": 0.02,
                "hardening_modulus": 10.0,
            }
        },
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (0, 2, 3)],
        loads=[{"node": 1, "dof": "UX", "value": -1.0}],
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "parameters": {
                "contact_mode": "penalty",
                "contact_penalty": 1.0e5,
                "adaptive_load_steps": True,
                "initial_load_increment": 1.0,
                "min_load_increment": 0.25,
                "max_load_increment": 1.0,
                "cutback_factor": 0.5,
                "max_cutbacks": 4,
                "max_iterations": 30,
                "tolerance": 1.0e-8,
            },
        },
    )
    model.contacts.append(FrictionlessContact(slave_node=1, master_nodes=(0, 2, 3)))

    import solveur.core.nonlinear_assembly as nonlinear_assembly

    original = nonlinear_assembly.assemble_penalty_contact
    calls = 0

    def fail_once(*args: object, **kwargs: object):
        nonlocal calls
        if calls == 0:
            calls += 1
            raise NumericalConvergenceError(
                "controlled contact assembly failure",
                reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                diagnostics={"controlled": True},
            )
        return original(*args, **kwargs)

    try:
        with patch.object(nonlinear_assembly, "assemble_penalty_contact", side_effect=fail_once):
            result = solve_model(model, enforce_policy=False)
    except Exception as error:  # pragma: no cover - campaign result records unexpected failures
        return {
            "name": "contact_retry_rollback",
            "passed": False,
            "converged": False,
            "failure_reason": type(error).__name__,
            "diagnostics": {"message": str(error)},
        }

    solver = result.to_dict()["solver"]
    rejection_log = list(solver.get("rejection_log", []))
    steps = list(solver.get("steps", []))
    retry_ok = (
        result.status == "PASS"
        and calls == 1
        and len(rejection_log) == 1
        and rejection_log[0].get("failure_reason") == NonlinearFailureReason.CONTACT_UPDATE_FAILURE.value
        and rejection_log[0].get("retry_increment") == 0.5
        and [step.get("load_factor") for step in steps] == [0.5, 1.0]
        and all(step.get("state_committed") is True for step in steps)
    )
    return {
        "name": "contact_retry_rollback",
        "passed": retry_ok,
        "converged": result.status == "PASS",
        "failure_reason": rejection_log[0].get("failure_reason") if rejection_log else None,
        "diagnostics": {
            "injected_failures": calls,
            "rejection_log": rejection_log,
            "committed_steps": [step.get("load_factor") for step in steps],
            "rollback_before_retry": True,
        },
    }


def _run_contact_penetration_limit_case() -> dict[str, object]:
    """Verify that an explicitly configured penetration limit fails closed."""

    model = FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (0, 2, 3)],
        loads=[{"node": 1, "dof": "UX", "value": -300.0}],
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "parameters": {
                "contact_mode": "penalty",
                "contact_penalty": 1.0e5,
                "contact_max_penetration": 1.0e-8,
                "max_iterations": 20,
                "tolerance": 1.0e-8,
            },
        },
    )
    model.contacts.append(FrictionlessContact(slave_node=1, master_nodes=(0, 2, 3)))
    try:
        solve_model(model, enforce_policy=False)
    except NumericalConvergenceError as error:
        payload = error.to_dict()
        return {
            "name": "contact_penetration_limit",
            "passed": payload.get("reason") == NonlinearFailureReason.CONTACT_PENETRATION_EXCESSIVE.value,
            "converged": bool(payload.get("converged", True)),
            "failure_reason": payload.get("reason"),
            "diagnostics": {"solver": "full_newton", **dict(payload.get("diagnostics", {}))},
        }
    return {
        "name": "contact_penetration_limit",
        "passed": False,
        "converged": True,
        "failure_reason": None,
        "diagnostics": {"solver": "full_newton"},
    }


def _contact_penetration_cutback_model(*, guarded: bool) -> FiniteElementModel:
    """Build the regular block used by the real contact cutback evidence."""

    model = FiniteElementModel.from_raw(
        nodes=[
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
        ],
        elements=[
            {"type": "TET4", "nodes": [0, 1, 3, 4], "material": "solid"},
            {"type": "TET4", "nodes": [1, 2, 3, 6], "material": "solid"},
            {"type": "TET4", "nodes": [1, 3, 4, 6], "material": "solid"},
            {"type": "TET4", "nodes": [1, 4, 5, 6], "material": "solid"},
            {"type": "TET4", "nodes": [3, 4, 6, 7], "material": "solid"},
        ],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=[
            {"node": node, "dofs": ["UX", "UY", "UZ"]}
            for node in (0, 3, 4, 7)
        ],
        loads=[
            {"node": node, "dof": "UX", "value": -500.0}
            for node in (1, 2, 5, 6)
        ],
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "parameters": {
                "contact_mode": "penalty",
                "contact_penalty": 1.0e5,
                "contact_search_mode": "initial",
                "max_iterations": 40,
                "tolerance": 1.0e-7,
                **(
                    {
                        "contact_max_penetration": 0.1,
                        "adaptive_load_steps": True,
                        "initial_load_increment": 1.0,
                        "min_load_increment": 0.0625,
                        "max_load_increment": 1.0,
                        "cutback_factor": 0.5,
                        "max_cutbacks": 10,
                        "load_steps": 1,
                    }
                    if guarded
                    else {
                        "adaptive_load_steps": False,
                        "load_path": [0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0],
                    }
                ),
            },
        },
    )
    model.contacts.append(FrictionlessContact(name="plane", slave_node=1, master_nodes=(0, 3, 4)))
    return model


def _audit_norm(result: object, name: str) -> float:
    """Read an audit vector norm without coupling the campaign to its type."""

    audit = getattr(result, "audit", None)
    for vector in getattr(audit, "vectors", ()):
        if isinstance(vector, dict) and vector.get("name") == name:
            return float(vector.get("norm", float("nan")))
    return float("nan")


def _run_contact_penetration_cutback_case() -> dict[str, object]:
    """Verify a real contact guard failure, adaptive retry and reference recovery."""

    try:
        guarded = solve_model(_contact_penetration_cutback_model(guarded=True), enforce_policy=False)
        reference = solve_model(_contact_penetration_cutback_model(guarded=False), enforce_policy=False)
    except Exception as error:  # pragma: no cover - campaign records infrastructure surprises
        return {
            "name": "contact_penetration_cutback",
            "passed": False,
            "converged": False,
            "failure_reason": type(error).__name__,
            "diagnostics": {"message": str(error)},
        }

    guarded_solver = guarded.to_dict()["solver"]
    reference_solver = reference.to_dict()["solver"]
    rejection_log = list(guarded_solver.get("rejection_log", []))
    guarded_steps = list(guarded_solver.get("steps", []))
    reference_steps = list(reference_solver.get("steps", []))
    factors = [float(step["load_factor"]) for step in guarded_steps]
    displacement_scale = max(float(np.linalg.norm(reference.displacements)), 1.0)
    displacement_difference = float(np.linalg.norm(guarded.displacements - reference.displacements))
    displacement_relative_difference = displacement_difference / displacement_scale
    guarded_gap = float(guarded_steps[-1]["contact_gaps"][0]) if guarded_steps else float("nan")
    reference_gap = float(reference_steps[-1]["contact_gaps"][0]) if reference_steps else float("nan")
    reaction_norm_difference = abs(_audit_norm(guarded, "reactions") - _audit_norm(reference, "reactions"))
    reasons = [entry.get("failure_reason") for entry in rejection_log]
    passed = (
        guarded.status == "PASS"
        and reference.status == "PASS"
        and factors == [0.5, 0.75, 1.0]
        and len(rejection_log) == 2
        and reasons == [
            NonlinearFailureReason.CONTACT_PENETRATION_EXCESSIVE.value,
            NonlinearFailureReason.CONTACT_PENETRATION_EXCESSIVE.value,
        ]
        and all(step.get("state_committed") is True for step in guarded_steps)
        and displacement_relative_difference < 1.0e-10
        and reaction_norm_difference < 1.0e-8
        and abs(guarded_gap - reference_gap) < 1.0e-10
        and max((float(step["relative_residual"]) for step in guarded_steps), default=float("inf")) < 1.0e-7
    )
    return {
        "name": "contact_penetration_cutback",
        "passed": passed,
        "converged": guarded.status == "PASS" and reference.status == "PASS",
        "failure_reason": reasons[0] if reasons else None,
        "diagnostics": {
            "solver": "full_newton",
            "contact_max_penetration": 0.1,
            "rejection_log": rejection_log,
            "committed_steps": factors,
            "reference_load_path": [step["load_factor"] for step in reference_steps],
            "rollback_before_retry": True,
            "displacement_difference": displacement_difference,
            "displacement_relative_difference": displacement_relative_difference,
            "reaction_norm_difference": reaction_norm_difference,
            "guarded_final_gap": guarded_gap,
            "reference_final_gap": reference_gap,
            "final_penetration": max(-guarded_gap, 0.0),
            "maximum_relative_residual": max(
                (float(step["relative_residual"]) for step in guarded_steps),
                default=float("inf"),
            ),
        },
    }


def _run_multistep_retry_rollback_case() -> dict[str, object]:
    """Reject the second adaptive increment after the first one was committed."""

    model = FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "j2"}],
        materials={
            "j2": {
                "type": "von_mises_elastoplastic_3d",
                "E": 1000.0,
                "nu": 0.3,
                "yield_stress": 0.02,
                "hardening_modulus": 10.0,
            }
        },
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (0, 2, 3)],
        loads=[{"node": 1, "dof": "UX", "value": -1.0}],
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "parameters": {
                "adaptive_load_steps": True,
                "initial_load_increment": 0.5,
                "min_load_increment": 0.125,
                "max_load_increment": 0.5,
                "cutback_factor": 0.5,
                "max_cutbacks": 4,
                "max_iterations": 30,
                "tolerance": 1.0e-8,
            },
        },
    )

    class RejectSecondStepSolver(NonlinearStaticSolver):
        """Inject one failure after a converged first increment."""

        def __init__(self) -> None:
            super().__init__()
            self.injected = False

        def _solve_load_step(self, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
            step = int(kwargs.get("step", args[6] if len(args) > 6 else 0))
            if step == 2 and not self.injected:
                self.injected = True
                raise NumericalConvergenceError(
                    "controlled failure after one committed adaptive increment",
                    reason=NonlinearFailureReason.MAX_ITERATIONS,
                    diagnostics={"controlled": True, "step": step},
                )
            return super()._solve_load_step(*args, **kwargs)

    try:
        result = RejectSecondStepSolver().solve(model)
    except Exception as error:  # pragma: no cover - campaign result records unexpected failures
        return {
            "name": "multistep_retry_rollback",
            "passed": False,
            "converged": False,
            "failure_reason": type(error).__name__,
            "diagnostics": {"message": str(error)},
        }

    solver = result.to_dict()["solver"]
    rejection_log = list(solver.get("rejection_log", []))
    steps = list(solver.get("steps", []))
    factors = [float(step.get("load_factor")) for step in steps]
    retry_ok = (
        result.status == "PASS"
        and len(rejection_log) == 1
        and rejection_log[0].get("base_load_factor") == 0.5
        and rejection_log[0].get("retry_increment") == 0.25
        and factors == [0.5, 0.75, 1.0]
        and all(step.get("state_committed") is True for step in steps)
    )
    return {
        "name": "multistep_retry_rollback",
        "passed": retry_ok,
        "converged": result.status == "PASS",
        "failure_reason": rejection_log[0].get("failure_reason") if rejection_log else None,
        "diagnostics": {
            "injected_step": 2,
            "committed_before_failure": factors[:1] == [0.5],
            "committed_steps": factors,
            "rejection_log": rejection_log,
            "rollback_before_retry": True,
        },
    }


def _run_linear_backend_failure_case() -> dict[str, object]:
    """Verify that a sparse backend runtime error has its own failure reason."""

    assembly = _Assembly(lambda _displacement: np.zeros(2), np.eye(2))
    import solveur.core.nonlinear_iteration as nonlinear_iteration

    def fail(*args: object, **kwargs: object):
        raise RuntimeError("controlled sparse factorization failure")

    try:
        with patch.object(nonlinear_iteration, "spsolve", side_effect=fail):
            solve_full_newton(
                assembly,
                np.array([1.0, 0.0]),
                np.array([1]),
                increments=1,
                tolerance=1.0e-8,
                max_iterations=2,
            )
    except NumericalConvergenceError as error:
        payload = error.to_dict()
        reason = payload.get("reason")
        diagnostics = dict(payload.get("diagnostics", {}))
        return {
            "name": "linear_solver_failure",
            "passed": reason == NonlinearFailureReason.LINEAR_SOLVER_FAILURE.value,
            "converged": bool(payload.get("converged", True)),
            "failure_reason": reason,
            "diagnostics": diagnostics,
        }
    return {
        "name": "linear_solver_failure",
        "passed": False,
        "converged": True,
        "failure_reason": None,
        "diagnostics": {},
    }


def _run_arc_length_failure_case() -> dict[str, object]:
    """Verify that a continuation step cap is reported, not silently truncated."""

    model = FiniteElementModel.from_raw(
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
            "method": "arc_length",
            "load_steps": 5,
            "max_iterations": 50,
            "tolerance": 1.0e-9,
            "max_arc_steps": 1,
            "target_load_factor": 1.0,
        },
    )
    try:
        solve_model(model, enforce_policy=False)
    except NumericalConvergenceError as error:
        payload = error.to_dict()
        return {
            "name": "arc_length_failure",
            "passed": payload.get("reason") == NonlinearFailureReason.ARC_LENGTH_FAILURE.value,
            "converged": bool(payload.get("converged", True)),
            "failure_reason": payload.get("reason"),
            "diagnostics": {"solver": "arc_length", **dict(payload.get("diagnostics", {}))},
        }
    return {
        "name": "arc_length_failure",
        "passed": False,
        "converged": True,
        "failure_reason": None,
        "diagnostics": {"solver": "arc_length"},
    }


def _run_buckling_failure_case() -> dict[str, object]:
    """Verify that an unbracketed tensile preload is classified explicitly."""

    model = FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        # Tension keeps the constrained tangent positive definite.  The
        # sparse generalized path therefore declines the problem and the
        # bounded bracket must report BUCKLING_FAILURE.
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
        analysis={
            "type": "linear_buckling",
            "method": "eigsh",
            "preload_factor": 1.0,
            "load_increments": 4,
            "initial_factor": 1.0,
            "maximum_factor": 2.0,
        },
    )
    try:
        LinearBucklingSolver().solve(model)
    except NumericalConvergenceError as error:
        payload = error.to_dict()
        return {
            "name": "buckling_failure",
            "passed": payload.get("reason") == NonlinearFailureReason.BUCKLING_FAILURE.value,
            "converged": bool(payload.get("converged", True)),
            "failure_reason": payload.get("reason"),
            "diagnostics": {"solver": "linear_buckling", **dict(payload.get("diagnostics", {}))},
        }
    return {
        "name": "buckling_failure",
        "passed": False,
        "converged": True,
        "failure_reason": None,
        "diagnostics": {"solver": "linear_buckling"},
    }


def run_failure_campaign() -> dict[str, object]:
    """Run intentional failures and return a non-release evidence report."""
    cases = [
        _run_case(
            "max_iterations",
            NonlinearFailureReason.MAX_ITERATIONS,
            _Assembly(lambda displacement: displacement, np.eye(2)),
            max_iterations=1,
        ),
        _run_case(
            "singular_tangent",
            NonlinearFailureReason.SINGULAR_TANGENT,
            _Assembly(lambda displacement: np.zeros(2), np.zeros((2, 2))),
        ),
        _run_case(
            "nan_detected",
            NonlinearFailureReason.NAN_DETECTED,
            _Assembly(lambda displacement: np.array([np.nan, 0.0]), np.eye(2)),
        ),
        _run_case(
            "inf_detected",
            NonlinearFailureReason.NAN_DETECTED,
            _Assembly(lambda displacement: np.array([np.inf, 0.0]), np.eye(2)),
        ),
        _run_case(
            "line_search_failure",
            NonlinearFailureReason.LINE_SEARCH_FAILURE,
            _Assembly(lambda displacement: np.zeros(2), np.eye(2)),
        ),
        _run_case(
            "invalid_element",
            NonlinearFailureReason.INVALID_ELEMENT,
            _Assembly(_raising_internal("Invalid HEX8 orientation"), np.eye(2)),
        ),
        _run_case(
            "material_update_failure",
            NonlinearFailureReason.MATERIAL_UPDATE_FAILURE,
            _Assembly(_raising_internal("material constitutive update failed"), np.eye(2)),
        ),
        _run_case(
            "contact_update_failure",
            NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
            _Assembly(_raising_internal("contact projection produced a non-finite gap"), np.eye(2)),
        ),
        _run_min_increment_case(),
    ]
    retry_cases = [_run_contact_retry_rollback_case(), _run_linear_backend_failure_case()]
    contact_failure_cases = [
        _run_contact_penetration_limit_case(),
        _run_contact_penetration_cutback_case(),
    ]
    multi_step_cases = [_run_multistep_retry_rollback_case()]
    path_failure_cases = [_run_arc_length_failure_case(), _run_buckling_failure_case()]
    state_failure_cases = [_run_state_corruption_case()]
    return {
        "campaign": "qf-solver-nonlinear-failure-contract-0.2.5a0",
        "status": (
            "PASS_INTERNAL_FAILURE_CONTRACT"
            if all(case.passed for case in cases)
            and all(case["passed"] for case in retry_cases)
            and all(case["passed"] for case in contact_failure_cases)
            and all(case["passed"] for case in multi_step_cases)
            and all(case["passed"] for case in path_failure_cases)
            and all(case["passed"] for case in state_failure_cases)
            else "FAIL"
        ),
        "release_claim": False,
        "cases": [case.to_dict() for case in cases],
        "retry_cases": retry_cases,
        "contact_failure_cases": contact_failure_cases,
        "multi_step_cases": multi_step_cases,
        "path_failure_cases": path_failure_cases,
        "state_failure_cases": state_failure_cases,
    }
