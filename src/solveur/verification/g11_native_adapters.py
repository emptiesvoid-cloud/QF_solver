"""Route-native adapters for the four focused 026-G11 adversarial cases.

The adapters deliberately live outside the solver routes.  They invoke the
public model/solve APIs or existing focused verification helpers and convert
only their observations into :class:`G11AdapterResult` records.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from solveur.api.public import solve_model
from solveur.core.errors import InputValidationError, MeshValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.solver import NonlinearStaticSolver
from solveur.verification.g11_runner import G11AdapterResult, G11CaseSpec, G11Runner, load_case_specs
from solveur.verification.robustness_mesh import run_adversarial_rollback_benchmark


CASE_SINGULAR = "VNV026-ADV-PLN-001"
CASE_UNSUPPORTED = "VNV026-ADV-PLN-002"
CASE_NONCONVERGENCE = "VNV026-ADV-PLN-003"
CASE_ROLLBACK = "VNV026-ADV-PLN-004"

NATIVE_ROUTE_STATUS = {
    "linear_static": "READY",
    "nonlinear_static": "READY",
    "geometric_nonlinear_static": "PARTIAL",
    "modal": "PARTIAL",
    "linear_buckling": "PARTIAL",
    "linear_static_contact": "PARTIAL",
}


def _tet4_model(*, fixed: bool, analysis: str | dict[str, object] = "linear_static") -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=(
            [
                {"node": 0, "dofs": ["UX", "UY", "UZ"]},
                {"node": 2, "dofs": ["UX", "UY", "UZ"]},
                {"node": 3, "dofs": ["UX", "UY", "UZ"]},
            ]
            if fixed
            else []
        ),
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
        analysis=analysis,
    )


def _singular_system(case: G11CaseSpec) -> object:
    """Invoke linear static with a connected but unconstrained TET4 model."""

    try:
        result = solve_model(_tet4_model(fixed=False), enforce_policy=False)
    except NumericalConvergenceError as error:
        if "singular" not in str(error).lower():
            raise
        return G11AdapterResult(
            success=False,
            error_type_or_code="NumericalConvergenceError:singular",
            diagnostics={
                "native_exception_type": type(error).__name__,
                "native_message": str(error),
                "classification_basis": "linear sparse solve reported singular matrix",
            },
        )
    return G11AdapterResult(success=True, payload=getattr(result, "to_dict", lambda: result)())


def _unsupported_combination(case: G11CaseSpec) -> object:
    """Reject a real linear-static TET4/local-body-force mismatch before assembly."""

    model = _tet4_model(fixed=True)
    model.distributed_loads = []
    model = FiniteElementModel.from_raw(
        nodes=model.nodes.tolist(),
        elements=[{"type": item.type, "nodes": list(item.nodes), "material": item.material} for item in model.elements],
        materials=model.materials,
        fixed_dofs=[{"node": item.node, "dofs": list(item.dofs)} for item in model.fixed_dofs],
        loads=[{"node": item.node, "dof": item.dof, "value": item.value} for item in model.loads],
        distributed_loads=[
            {
                "type": "body_force",
                "value": [1.0, 0.0, 0.0],
                "elements": [0],
                "coordinate_system": "local",
            }
        ],
        analysis="linear_static",
    )
    try:
        result = solve_model(model, enforce_policy=False)
    except (InputValidationError, MeshValidationError) as error:
        if "shell elements only" not in str(error).lower():
            raise
        return G11AdapterResult(
            success=False,
            error_type_or_code=f"{type(error).__name__}:UNSUPPORTED_EXPLICIT",
            diagnostics={
                "native_exception_type": type(error).__name__,
                "native_message": str(error),
                "classification_basis": "TET4 local body force is outside the supported load-element pairing",
            },
        )
    return G11AdapterResult(success=True, payload=getattr(result, "to_dict", lambda: result)())


def _controlled_nonconvergence(case: G11CaseSpec) -> object:
    """Run the public nonlinear driver with one controlled rejected trial."""

    model = _tet4_model(
        fixed=True,
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
            "max_cutbacks": 0,
        },
    )

    class AlwaysRejectSolver(NonlinearStaticSolver):
        """Inject a typed trial failure without changing production code."""

        def _solve_load_step(self, *args: object, **kwargs: object) -> object:  # type: ignore[no-untyped-def]
            raise NumericalConvergenceError(
                "controlled G11 trial non-convergence",
                reason=NonlinearFailureReason.MAX_ITERATIONS,
                diagnostics={"controlled": True, "case_id": case.case_id},
            )

    try:
        AlwaysRejectSolver().solve(model)
    except NumericalConvergenceError as error:
        payload = error.to_dict()
        return G11AdapterResult(
            success=False,
            error_type_or_code=f"NumericalConvergenceError:{payload.get('reason')}",
            payload=payload,
            diagnostics={"route_native": True, "failure_reason": payload.get("reason")},
        )
    return G11AdapterResult(success=True)


def _rollback_state_integrity(case: G11CaseSpec) -> object:
    """Execute one real rejected-increment/retry benchmark and expose its digests."""

    outcome = run_adversarial_rollback_benchmark("TET4")
    clean_retry = bool(outcome.get("clean_retry"))
    rejected = int(outcome.get("rejected_increments", 0))
    return G11AdapterResult(
        success=False,
        error_type_or_code="NumericalConvergenceError:rejected_increment",
        state_preserved=clean_retry and rejected == 1,
        payload=outcome,
        diagnostics={
            "route_native": True,
            "rejected_increments": rejected,
            "committed_digest_before_failure": outcome.get("committed_digest_before_failure"),
            "retry_state_digest": outcome.get("retry_state_digest"),
            "rollback_verified": clean_retry,
        },
    )


def native_adapters() -> dict[str, Callable[[G11CaseSpec], object]]:
    """Return the four approved case adapters keyed by their stable case IDs."""

    return {
        CASE_SINGULAR: _singular_system,
        CASE_UNSUPPORTED: _unsupported_combination,
        CASE_NONCONVERGENCE: _controlled_nonconvergence,
        CASE_ROLLBACK: _rollback_state_integrity,
    }


def native_route_status() -> dict[str, str]:
    """Return route introspection status without claiming unexecuted coverage."""

    return dict(NATIVE_ROUTE_STATUS)


def run_native_g11_cases(
    cases_path: str | Path,
    archive_dir: str | Path,
    *,
    source_sha: str,
) -> dict[str, dict[str, object]]:
    """Execute exactly the four approved cases and archive each envelope."""

    cases = load_case_specs(cases_path)
    runner = G11Runner(native_adapters(), source_sha=source_sha, provenance={"execution_mode": "native_route"})
    results: dict[str, dict[str, object]] = {}
    target_dir = Path(archive_dir)
    for case in cases:
        result = runner.run_case(case, evidence_id=f"G11-NATIVE-{case.case_id}")
        runner.archive_result(result, target_dir / f"{case.case_id}.json")
        results[case.case_id] = result
    return results


__all__ = [
    "CASE_NONCONVERGENCE",
    "CASE_ROLLBACK",
    "CASE_SINGULAR",
    "CASE_UNSUPPORTED",
    "native_adapters",
    "native_route_status",
    "run_native_g11_cases",
]
