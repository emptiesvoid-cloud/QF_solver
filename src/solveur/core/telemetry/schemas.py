"""Small schema helpers for backend-neutral telemetry measurements."""

from __future__ import annotations

import math
from collections.abc import Mapping

from solveur.core.telemetry.events import TelemetryValidationError, validate_json_value


LINEAR_BACKENDS = frozenset({"DIRECT", "CG", "MINRES", "GMRES", "PETSC_KSP"})
LINEAR_SOLVER_FIELDS = frozenset(
    {
        "backend",
        "preconditioner",
        "matrix_rows",
        "matrix_columns",
        "matrix_nnz",
        "method",
        "rtol",
        "atol",
        "max_iterations",
        "iterations",
        "raw_residual_norm",
        "relative_residual_norm",
        "backward_error_eta_inf",
        "converged",
        "fallback_used",
        "fallback_reason",
        "solve_time_s",
        "setup_time_s",
    }
)
MEMORY_FIELD_NAMES = frozenset(
    {
        "peak_rss_process",
        "peak_private_or_uss_process",
        "telemetry_sample_peak_rss",
        "telemetry_sample_peak_private",
    }
)
TIMING_FIELD_NAMES = frozenset(
    {
        "mesh_setup_time_s",
        "assembly_time_s",
        "factorization_setup_time_s",
        "linear_solve_time_s",
        "communication_time_s",
        "checkpoint_io_time_s",
        "postprocess_time_s",
        "total_analysis_time_s",
    }
)

_START_REQUIRED = frozenset(
    {
        "backend",
        "preconditioner",
        "matrix_rows",
        "matrix_columns",
        "matrix_nnz",
        "method",
        "rtol",
        "atol",
        "max_iterations",
    }
)
_END_REQUIRED = frozenset(
    {
        "converged",
        "status",
        "iterations",
        "raw_residual_norm",
        "relative_residual_norm",
        "backward_error_eta_inf",
        "fallback_used",
        "solve_time_s",
    }
)


def _missing_token(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("value") is None
        and isinstance(value.get("reason"), str)
    )


def _number(value: object, field_name: str, *, nonnegative: bool = True) -> None:
    if _missing_token(value):
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TelemetryValidationError(f"{field_name} must be numeric or an explicit missing value.")
    numeric = float(value)
    if not math.isfinite(numeric) or (nonnegative and numeric < 0.0):
        raise TelemetryValidationError(f"{field_name} must be finite and valid.")


def _integer(value: object, field_name: str) -> None:
    if _missing_token(value):
        return
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TelemetryValidationError(f"{field_name} must be a non-negative integer or an explicit missing value.")


def _text(value: object, field_name: str) -> None:
    if _missing_token(value):
        return
    if not isinstance(value, str) or not value.strip():
        raise TelemetryValidationError(f"{field_name} must be a non-empty string or an explicit missing value.")


def _measurement(value: object, field_name: str) -> None:
    if _missing_token(value):
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TelemetryValidationError(f"{field_name} must be numeric or an explicit missing value.")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0.0:
        raise TelemetryValidationError(f"{field_name} must be finite and non-negative.")


def validate_linear_solver_metrics(
    metrics: Mapping[str, object],
    *,
    phase: str = "end",
) -> dict[str, object]:
    """Validate start, iteration or terminal linear-solver measurements."""

    if not isinstance(metrics, Mapping):
        raise TelemetryValidationError("Linear solver metrics must be a mapping.")
    normalised = validate_json_value(dict(metrics), allow_null=False, path="linear_metrics")
    if not isinstance(normalised, dict):
        raise TelemetryValidationError("Linear solver metrics must remain a mapping.")
    if phase not in {"start", "iteration", "end"}:
        raise ValueError("phase must be start, iteration or end.")
    required = _START_REQUIRED if phase == "start" else _END_REQUIRED if phase == "end" else frozenset()
    missing = sorted(required.difference(normalised))
    if missing:
        raise TelemetryValidationError(f"Missing linear {phase} fields: {', '.join(missing)}.")
    if "backend" in normalised:
        backend = normalised["backend"]
        if not _missing_token(backend) and backend not in LINEAR_BACKENDS:
            raise TelemetryValidationError(f"Unsupported linear backend: {backend!r}.")
    for field_name in ("preconditioner", "method", "status", "fallback_reason"):
        if field_name in normalised:
            _text(normalised[field_name], field_name)
    for field_name in ("matrix_rows", "matrix_columns", "matrix_nnz", "max_iterations", "iterations"):
        if field_name in normalised:
            _integer(normalised[field_name], field_name)
    for field_name in (
        "rtol",
        "atol",
        "raw_residual_norm",
        "relative_residual_norm",
        "backward_error_eta_inf",
        "solve_time_s",
        "setup_time_s",
    ):
        if field_name in normalised:
            _number(normalised[field_name], field_name)
    for field_name in ("converged", "fallback_used"):
        if field_name in normalised:
            value = normalised[field_name]
            if not _missing_token(value) and not isinstance(value, bool):
                raise TelemetryValidationError(f"{field_name} must be boolean or an explicit missing value.")
    return normalised


def validate_linear_solve_metrics(
    metrics: Mapping[str, object],
    *,
    phase: str = "end",
) -> dict[str, object]:
    """Compatibility alias with the event name terminology."""

    return validate_linear_solver_metrics(metrics, phase=phase)


def _validate_named_measurements(
    metrics: Mapping[str, object],
    allowed: frozenset[str],
    *,
    category: str,
) -> dict[str, object]:
    if not isinstance(metrics, Mapping):
        raise TelemetryValidationError(f"{category} metrics must be a mapping.")
    unknown = sorted(set(metrics).difference(allowed))
    if unknown:
        raise TelemetryValidationError(f"Unknown {category} metrics: {', '.join(unknown)}.")
    normalised = validate_json_value(dict(metrics), allow_null=True, path=category)
    if not isinstance(normalised, dict):
        raise TelemetryValidationError(f"{category} metrics must remain a mapping.")
    for field_name, value in normalised.items():
        _measurement(value, field_name)
    return normalised


def validate_memory_metrics(metrics: Mapping[str, object]) -> dict[str, object]:
    """Validate normalized memory names and finite byte measurements."""

    return _validate_named_measurements(metrics, MEMORY_FIELD_NAMES, category="memory")


def validate_timing_metrics(metrics: Mapping[str, object]) -> dict[str, object]:
    """Validate normalized phase timing names and finite seconds."""

    return _validate_named_measurements(metrics, TIMING_FIELD_NAMES, category="timing")
