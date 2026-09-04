"""Deterministic evidence and performance records for Level-Up 2."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
from numbers import Real
from pathlib import Path
from typing import Any, Iterable, Mapping

from solveur.io.manifest import git_source_state, runtime_fingerprint, utc_timestamp
from solveur.paths import project_root
from solveur.version import DISPLAY_NAME, __version__


OBSERVATORY_SCHEMA_VERSION = 1
CLASSIFICATIONS = frozenset(
    {
        "PASS",
        "PASS_WITH_LIMITATIONS",
        "FAIL",
        "EXPECTED_FAILURE",
        "NOT_COMPARABLE",
        "UNAVAILABLE",
        "RESOURCE_LIMITED",
    }
)
_PROVENANCE_REQUIRED = frozenset({"PASS", "PASS_WITH_LIMITATIONS", "EXPECTED_FAILURE"})
_SHA256 = "0123456789abcdef"


class ObservatoryValidationError(ValueError):
    """Raised when an observatory record is incomplete or unsafe."""


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON-compatible data with stable UTF-8/LF-independent bytes."""
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ObservatoryValidationError(f"Value is not canonical JSON: {exc}") from exc


def canonical_digest(value: Any) -> str:
    """Return the SHA-256 digest of canonical JSON data."""
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def make_observatory_record(
    *,
    case_id: str,
    requirement_id: str | None = None,
    capability_refs: Iterable[str] = (),
    model_id: str | None = None,
    element_family: str | None = None,
    analysis: str | None = None,
    material: str | None = None,
    route: str | None = None,
    backend: str | None = None,
    solver: str | None = None,
    preconditioner: str | None = None,
    rank_count: int = 1,
    dof: int | None = None,
    elements: int | None = None,
    input_digest: str | None = None,
    observables: Mapping[str, Any] | None = None,
    tolerances: Mapping[str, Any] | None = None,
    classification: str = "PASS",
    metrics: Mapping[str, Any] | None = None,
    source: Mapping[str, Any] | None = None,
    environment: Mapping[str, Any] | None = None,
    artifacts: Mapping[str, str] | None = None,
    command: Iterable[str] = (),
    oracle: Mapping[str, Any] | None = None,
    deterministic_seed: int | str | None = None,
    configuration: Mapping[str, Any] | None = None,
    message: str = "",
) -> dict[str, Any]:
    """Build a complete observatory record without executing a solver."""
    if classification not in CLASSIFICATIONS:
        raise ObservatoryValidationError(f"Unknown classification: {classification!r}")
    metrics_data = dict(metrics or {})
    timings = _phase_metrics(metrics_data.get("timings_seconds"))
    resources = _resource_metrics(metrics_data.get("resources"))
    result_observables = dict(observables or {})
    result_digest = str((artifacts or {}).get("result_digest", ""))
    if not result_digest:
        result_digest = canonical_digest(
            {"classification": classification, "observables": result_observables, "message": message}
        )
    artifact_digests = dict(artifacts or {})
    artifact_digests["result_digest"] = result_digest
    artifact_digests["configuration_digest"] = canonical_digest(dict(configuration or {}))
    if input_digest is not None:
        artifact_digests["input_digest"] = input_digest

    source_data = dict(source or git_source_state(project_root()))
    source_data.setdefault("repository", ".")
    environment_data = _environment(rank_count, environment)
    return {
        "schema_version": OBSERVATORY_SCHEMA_VERSION,
        "record_type": "lu2_performance_observation",
        "case_id": case_id,
        "requirement_id": requirement_id,
        "capability_refs": sorted(str(value) for value in capability_refs),
        "solver": {"name": DISPLAY_NAME, "version": __version__},
        "source": source_data,
        "environment": environment_data,
        "execution": {
            "route": route,
            "backend": backend,
            "solver": solver,
            "preconditioner": preconditioner,
            "rank_count": rank_count,
            "deterministic_seed": deterministic_seed,
            "configuration": dict(configuration or {}),
        },
        "workload": {
            "model_id": model_id,
            "element_family": element_family,
            "analysis": analysis,
            "material": material,
            "dof": dof,
            "elements": elements,
        },
        "oracle": dict(oracle or {}),
        "tolerances": dict(tolerances or {}),
        "metrics": {
            "timings_seconds": timings,
            "iterations": metrics_data.get("iterations"),
            "matvecs": metrics_data.get("matvecs"),
            "residual": metrics_data.get("residual"),
            "equilibrium": metrics_data.get("equilibrium"),
            "energy": metrics_data.get("energy"),
            "resources": resources,
        },
        "result": {
            "classification": classification,
            "observables": result_observables,
            "message": message,
        },
        "artifacts": {"input_digest": input_digest, **artifact_digests},
        "provenance": {
            "captured_at_utc": utc_timestamp(),
            "command": [str(value) for value in command],
            "artifact_classification": "CONTROLLED_PROOF",
        },
    }


def validate_observatory_record(record: Mapping[str, Any]) -> None:
    """Validate a record and reject incomplete provenance or non-finite values."""
    if not isinstance(record, Mapping):
        raise ObservatoryValidationError("Observatory record must be an object.")
    required = {
        "schema_version",
        "record_type",
        "case_id",
        "source",
        "environment",
        "execution",
        "workload",
        "tolerances",
        "metrics",
        "result",
        "artifacts",
        "provenance",
    }
    missing = sorted(required - set(record))
    if missing:
        raise ObservatoryValidationError(f"Missing observatory fields: {missing}")
    if record["schema_version"] != OBSERVATORY_SCHEMA_VERSION:
        raise ObservatoryValidationError("Unsupported observatory schema version.")
    if record["record_type"] != "lu2_performance_observation":
        raise ObservatoryValidationError("Unexpected observatory record type.")
    if not isinstance(record["case_id"], str) or not record["case_id"].strip():
        raise ObservatoryValidationError("case_id must be a non-empty string.")
    source = _mapping(record, "source")
    if not isinstance(source.get("dirty"), bool) or not isinstance(source.get("revision"), str):
        raise ObservatoryValidationError("source must include revision and boolean dirty state.")
    environment = _mapping(record, "environment")
    for field in ("hostname", "os", "cpu", "python_version", "petsc_version", "mpi_version"):
        if field not in environment:
            raise ObservatoryValidationError(f"environment.{field} is required, even when null.")
    execution = _mapping(record, "execution")
    rank_count = execution.get("rank_count")
    if not isinstance(rank_count, int) or isinstance(rank_count, bool) or rank_count < 1:
        raise ObservatoryValidationError("execution.rank_count must be a positive integer.")
    result = _mapping(record, "result")
    classification = result.get("classification")
    if classification not in CLASSIFICATIONS:
        raise ObservatoryValidationError(f"Unsupported result classification: {classification!r}")
    artifacts = _mapping(record, "artifacts")
    if classification in _PROVENANCE_REQUIRED:
        revision = source.get("revision", "")
        if not _is_revision(revision):
            raise ObservatoryValidationError("PASS-like evidence requires a committed source revision.")
        if source.get("dirty") is not False:
            raise ObservatoryValidationError("PASS-like evidence requires a clean source state.")
        _require_digest(artifacts, "input_digest")
        _require_digest(artifacts, "result_digest")
        _require_digest(artifacts, "configuration_digest")
        provenance = _mapping(record, "provenance")
        if not isinstance(provenance.get("command"), list) or not provenance["command"]:
            raise ObservatoryValidationError("PASS-like evidence requires a non-empty command list.")
        if not provenance.get("artifact_classification"):
            raise ObservatoryValidationError("PASS-like evidence requires artifact classification.")
    _walk_finite(record)
    canonical_json_bytes(record)


def write_observatory_record(path: str | Path, record: Mapping[str, Any]) -> Path:
    """Validate and write an observatory record using canonical JSON bytes."""
    validate_observatory_record(record)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_json_bytes(record) + b"\n")
    return target


def record_performance_run(path: str | Path, **kwargs: Any) -> dict[str, Any]:
    """Build, validate and write one generic performance observation."""
    record = make_observatory_record(**kwargs)
    write_observatory_record(path, record)
    return record


def read_observatory_record(path: str | Path) -> dict[str, Any]:
    """Read a record while rejecting duplicate JSON keys."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (OSError, json.JSONDecodeError, ObservatoryValidationError) as exc:
        raise ObservatoryValidationError(f"Invalid observatory record: {exc}") from exc
    validate_observatory_record(data)
    return data


def compare_observatory_runs(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    """Compare compatible runs without declaring a regression or improvement."""
    validate_observatory_record(left)
    validate_observatory_record(right)
    reasons: list[str] = []
    for label, path in (
        ("case_id", ("case_id",)),
        ("model_id", ("workload", "model_id")),
        ("input_digest", ("artifacts", "input_digest")),
        ("route", ("execution", "route")),
        ("backend", ("execution", "backend")),
        ("solver", ("execution", "solver")),
        ("preconditioner", ("execution", "preconditioner")),
        ("rank_count", ("execution", "rank_count")),
        ("tolerances", ("tolerances",)),
    ):
        if _at(left, path) != _at(right, path):
            reasons.append(f"{label} differs")
    left_metrics = _mapping(left, "metrics")
    right_metrics = _mapping(right, "metrics")
    return {
        "schema_version": OBSERVATORY_SCHEMA_VERSION,
        "compatible": not reasons,
        "compatibility_reasons": reasons,
        "timing_deltas_seconds": _numeric_deltas(
            _mapping(left_metrics, "timings_seconds"), _mapping(right_metrics, "timings_seconds")
        ),
        "metric_deltas": _numeric_deltas(left_metrics, right_metrics, excluded={"timings_seconds", "resources"}),
        "resource_deltas": _numeric_deltas(
            _mapping(left_metrics, "resources"), _mapping(right_metrics, "resources")
        ),
        "environment_differences": _mapping_differences(
            _mapping(left, "environment"), _mapping(right, "environment")
        ),
        "comparison_policy": "descriptive_only; no regression or improvement verdict is inferred",
    }


def aggregate_rank_metrics(rank_metrics: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate deterministic MPI-like rank metrics without requiring MPI."""
    rows = sorted((dict(row) for row in rank_metrics), key=lambda row: int(row.get("rank", 0)))
    if not rows:
        raise ObservatoryValidationError("At least one rank metric is required.")
    rss = [int(row["peak_rss_bytes"]) for row in rows if row.get("peak_rss_bytes") is not None]
    iterations = [int(row["iterations"]) for row in rows if row.get("iterations") is not None]
    timings = [
        _mapping(row, "timings_seconds")
        for row in rows
        if isinstance(row.get("timings_seconds"), Mapping)
    ]
    result: dict[str, Any] = {
        "rank_count": len(rows),
        "peak_rss_per_rank_bytes": max(rss) if rss else None,
        "peak_rss_total_bytes": sum(rss) if rss else None,
        "iterations": max(iterations) if iterations else None,
        "timings_seconds": {
            name: max(float(timing[name]) for timing in timings if name in timing)
            if any(name in timing for timing in timings)
            else None
            for name in _PHASES
        },
    }
    if rss:
        mean = sum(rss) / len(rss)
        result["imbalance"] = max(rss) / mean - 1.0 if mean else 0.0
    else:
        result["imbalance"] = None
    return result


def record_benchmark_run(
    run: Any,
    path: str | Path,
    *,
    requirement_id: str | None = None,
    capability_refs: Iterable[str] = (),
    input_digest: str | None = None,
    command: Iterable[str] = (),
) -> dict[str, Any]:
    """Adapt a legacy ``BenchmarkRun`` without changing its execution path."""
    status = str(getattr(run, "status", "NOT_COMPARABLE"))
    classification = status if status in CLASSIFICATIONS else "NOT_COMPARABLE"
    message = str(getattr(run, "message", ""))
    source = git_source_state(project_root())
    if classification in _PROVENANCE_REQUIRED and (
        input_digest is None or source.get("dirty") is not False
    ):
        classification = "NOT_COMPARABLE"
        message = (
            f"Legacy run lacks clean input provenance; original status was {status}. {message}"
        ).strip()
    descriptor = getattr(run, "descriptor", None)
    metrics = dict(getattr(run, "metrics", {}) or {})
    descriptor_data = descriptor.to_dict() if descriptor is not None and hasattr(descriptor, "to_dict") else {}
    record = make_observatory_record(
        case_id=str(getattr(descriptor, "identifier", "legacy-benchmark")),
        requirement_id=requirement_id,
        capability_refs=capability_refs,
        model_id=str(getattr(descriptor, "identifier", "legacy-benchmark")),
        element_family=descriptor_data.get("family"),
        analysis=(descriptor_data.get("analyses") or [None])[0],
        route="legacy-benchmark-runner",
        backend=metrics.get("backend"),
        solver=metrics.get("solver"),
        input_digest=input_digest,
        observables=metrics.get("observables", {}),
        tolerances=descriptor_data.get("criteria", {}),
        classification=classification,
        metrics=metrics,
        artifacts={"legacy_run_digest": canonical_digest(getattr(run, "to_dict", lambda: {})())},
        command=command,
        source=source,
        message=message,
    )
    write_observatory_record(path, record)
    return record


_PHASES = (
    "model_setup",
    "preflight",
    "assembly_operator",
    "redistribution",
    "pc_setup",
    "ksp_solve",
    "communication",
    "io",
    "post_processing",
    "total",
)


def _phase_metrics(value: Any) -> dict[str, float | None]:
    source = dict(value) if isinstance(value, Mapping) else {}
    return {name: source.get(name) for name in _PHASES}


def _resource_metrics(value: Any) -> dict[str, Any]:
    source = dict(value) if isinstance(value, Mapping) else {}
    return {
        "peak_rss_total_bytes": source.get("peak_rss_total_bytes", source.get("peak_rss_bytes")),
        "peak_rss_per_rank_bytes": source.get("peak_rss_per_rank_bytes"),
        "imbalance": source.get("imbalance"),
        "gpu_vram_bytes": source.get("gpu_vram_bytes"),
    }


def _environment(rank_count: int, overrides: Mapping[str, Any] | None) -> dict[str, Any]:
    runtime = runtime_fingerprint()
    packages = runtime.get("packages", {})
    data = {
        "hostname": platform.node() or None,
        "os": platform.platform(),
        "cpu": platform.processor() or platform.machine() or None,
        "ram_bytes": _physical_memory_bytes(),
        "python_version": runtime.get("python", {}).get("version"),
        "petsc_version": packages.get("petsc4py"),
        "mpi_version": packages.get("mpi4py"),
        "container_digest": os.environ.get("CONTAINER_IMAGE_DIGEST"),
        "threads": _optional_int_env("OMP_NUM_THREADS"),
        "rank_count": rank_count,
    }
    data.update(dict(overrides or {}))
    data["rank_count"] = rank_count
    return data


def _physical_memory_bytes() -> int | None:
    try:
        import psutil

        return int(psutil.virtual_memory().total)
    except (ImportError, AttributeError, OSError):
        return None


def _optional_int_env(name: str) -> int | None:
    try:
        return int(os.environ[name])
    except (KeyError, TypeError, ValueError):
        return None


def _mapping(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    child = value.get(key)
    if not isinstance(child, Mapping):
        raise ObservatoryValidationError(f"{key} must be an object.")
    return child


def _at(value: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _numeric_deltas(left: Mapping[str, Any], right: Mapping[str, Any], excluded: set[str] | None = None) -> dict[str, float]:
    excluded = excluded or set()
    result: dict[str, float] = {}
    for key in sorted(set(left) | set(right)):
        if key in excluded:
            continue
        left_value = left.get(key)
        right_value = right.get(key)
        if isinstance(left_value, Real) and isinstance(right_value, Real):
            result[key] = float(right_value) - float(left_value)
    return result


def _mapping_differences(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        key: {"left": left.get(key), "right": right.get(key)}
        for key in sorted(set(left) | set(right))
        if left.get(key) != right.get(key)
    }


def _require_digest(mapping: Mapping[str, Any], key: str) -> None:
    value = mapping.get(key)
    if not isinstance(value, str) or len(value) != 64 or any(char not in _SHA256 for char in value.lower()):
        raise ObservatoryValidationError(f"PASS-like evidence requires a SHA-256 {key}.")


def _is_revision(value: Any) -> bool:
    return isinstance(value, str) and 7 <= len(value) <= 64 and all(char in _SHA256 for char in value.lower())


def _walk_finite(value: Any, path: str = "record") -> None:
    if isinstance(value, Real) and not isinstance(value, bool) and not math.isfinite(float(value)):
        raise ObservatoryValidationError(f"Non-finite numeric value at {path}.")
    if isinstance(value, Mapping):
        for key, child in value.items():
            _walk_finite(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _walk_finite(child, f"{path}[{index}]")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ObservatoryValidationError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result
