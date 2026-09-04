"""Focused tests for the LU2 execution, diagnostic and recovery contract."""

from __future__ import annotations

import pytest

from solveur.core.errors import InfrastructureError, InputValidationError, NumericalConvergenceError
from solveur.execution import (
    DiagnosticCategory,
    DiagnosticCode,
    ExecutionContractError,
    ExecutionRecoveryError,
    ExecutionSession,
    ExecutionState,
    ResourceLimitationError,
    diagnostic_from_exception,
)


def _session() -> ExecutionSession:
    return ExecutionSession(
        case_id="LU2-WP06-UNIT-001",
        source_sha="0123456789abcdef",
        route="nonlinear_static",
        backend="scipy",
        provenance={"input_digest": "input-001"},
    )


def test_execution_lifecycle_is_explicit_and_serializable() -> None:
    session = _session()
    session.validate(provenance={"config_digest": "config-001"})
    result = session.execute(lambda: {"status": "ok"})
    session.checkpoint(evidence_link="evidence/run-001.json")
    restored = session.recover(lambda: result)
    session.transition(ExecutionState.RUNNING)

    assert restored == result
    assert session.state is ExecutionState.RUNNING
    assert session.state_history == [
        ExecutionState.CREATED,
        ExecutionState.VALIDATED,
        ExecutionState.RUNNING,
        ExecutionState.CONVERGED,
        ExecutionState.CHECKPOINTED,
        ExecutionState.RECOVERED,
        ExecutionState.RUNNING,
    ]
    record = session.to_dict()
    assert record["route"] == "nonlinear_static"
    assert record["evidence_link"] == "evidence/run-001.json"
    assert record["provenance"]["input_digest"] == "input-001"


def test_invalid_transition_fails_closed() -> None:
    session = _session()
    with pytest.raises(ExecutionContractError, match="requires the VALIDATED state"):
        session.execute(lambda: None)

    session.validate()
    with pytest.raises(ExecutionContractError, match="requires a structured diagnostic"):
        session.transition(ExecutionState.FAILED)


def test_operation_failure_is_terminal_and_structured() -> None:
    session = _session()
    session.validate()
    with pytest.raises(NumericalConvergenceError):
        session.execute(lambda: (_ for _ in ()).throw(NumericalConvergenceError("Newton did not converge.")))

    assert session.state is ExecutionState.FAILED
    assert session.diagnostic is not None
    assert session.diagnostic.code is DiagnosticCode.SOLVER_NON_CONVERGENCE
    assert session.diagnostic.category is DiagnosticCategory.SOLVER_NON_CONVERGENCE


def test_recovery_corruption_is_not_hidden() -> None:
    session = _session()
    session.validate()
    session.execute(lambda: "converged")
    session.checkpoint(evidence_link="state.npz")

    with pytest.raises(ExecutionRecoveryError) as raised:
        session.recover(lambda: (_ for _ in ()).throw(InputValidationError("Cannot read checkpoint: invalid or corrupted NPZ.")))

    assert raised.value.diagnostic.code is DiagnosticCode.CHECKPOINT_CORRUPTION
    assert session.state is ExecutionState.FAILED


@pytest.mark.parametrize(
    ("error", "code", "category", "recoverable"),
    [
        (InfrastructureError("PETSc backend unavailable."), DiagnosticCode.BACKEND_UNAVAILABLE, DiagnosticCategory.BACKEND_UNAVAILABLE, True),
        (ResourceLimitationError("5M run exceeded the declared wall-time budget."), DiagnosticCode.RESOURCE_LIMITATION, DiagnosticCategory.RESOURCE_LIMITATION, True),
        (InputValidationError("unsupported capability route."), DiagnosticCode.UNSUPPORTED_CAPABILITY, DiagnosticCategory.UNSUPPORTED_CAPABILITY, False),
        (NumericalConvergenceError("non-finite displacement."), DiagnosticCode.NUMERICAL_INVALIDITY, DiagnosticCategory.NUMERICAL_INVALIDITY, False),
    ],
)
def test_existing_solver_errors_map_to_stable_diagnostics(error, code, category, recoverable) -> None:
    diagnostic = diagnostic_from_exception(error, context={"phase": "solve"})

    assert diagnostic.code is code
    assert diagnostic.category is category
    assert diagnostic.recoverable is recoverable
    assert diagnostic.to_dict()["context"] == {"exception_type": error.__class__.__name__, "phase": "solve"}
