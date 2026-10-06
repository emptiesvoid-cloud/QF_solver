"""Deterministic execution and evidence handling for V&V v2 cases."""

from __future__ import annotations

from dataclasses import MISSING, asdict, dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
import re
from time import perf_counter
from typing import Any, Callable, Mapping

from solveur.io.manifest import content_digest
from solveur.verification.v2.execution_identity import ExecutionIdentity, ExecutionIdentityError
from solveur.verification.v2.schema import (
    CASE_SCHEMA_VERSION,
    ExpectedFailureContract,
    VnvCase,
    VnvSchemaError,
    VERDICTS,
)


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonical(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Canonical V&V data cannot contain non-finite floats.")
        return value
    if isinstance(value, Path):
        return value.as_posix()
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON-compatible data with stable ordering and UTF-8 bytes."""

    return (json.dumps(_canonical(value), ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _digest(value: Any) -> str:
    return content_digest(canonical_json_bytes(value))


canonical_sha256 = _digest


class ExternalUnavailableError(RuntimeError):
    """Raised by an executor when an external oracle cannot be run."""


class ResourceLimitedError(RuntimeError):
    """Raised by an executor when declared resources prevent completion."""


class DuplicateJsonKeyError(ValueError):
    """Raised when a machine-readable contract contains a duplicate key."""


class VnvExecutionError(RuntimeError):
    """Structured executor error that can satisfy an exact schema-2 expectation."""

    def __init__(self, *, stage: str, reason: str, error_code: str | None = None) -> None:
        super().__init__(reason)
        self.stage = stage
        self.reason = reason
        self.error_code = error_code


@dataclass(frozen=True)
class ExecutionOutput:
    """Solver-independent observations returned by a case executor."""

    observables: dict[str, Any]
    runtime_seconds: float = 0.0
    peak_memory_mb: float | None = None
    artifacts: dict[str, str] | None = None
    provenance: dict[str, Any] | None = None


@dataclass(frozen=True)
class VnvEvidence:
    """Machine-readable evidence record emitted for one execution."""

    case_id: str
    requirement_id: str
    source_sha: str
    input_digest: str
    result_digest: str
    timestamp: str
    environment: dict[str, Any]
    observables: dict[str, Any]
    oracle: dict[str, Any]
    tolerance: float
    verdict: str
    failure_reason: str | None
    runtime_seconds: float
    peak_memory_mb: float | None
    provenance: dict[str, Any]
    artifact_classification: str
    execution_key: str | None = None
    identity_schema_version: int | None = None

    def __post_init__(self) -> None:
        if self.verdict not in VERDICTS:
            raise ValueError(f"Invalid V&V verdict {self.verdict!r}.")
        if self.execution_key is not None and not re.fullmatch(r"[0-9a-f]{64}", self.execution_key):
            raise ValueError("execution_key must be a lowercase SHA-256 digest.")
        if (self.execution_key is None) != (self.identity_schema_version is None):
            raise ValueError("execution_key and identity_schema_version must be present together.")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if self.execution_key is None:
            result.pop("execution_key")
            result.pop("identity_schema_version")
        return result


Executor = Callable[[VnvCase], ExecutionOutput | Mapping[str, Any]]


def _case_execution_identity(case: VnvCase, source_sha: str) -> ExecutionIdentity | None:
    if case.schema_version != CASE_SCHEMA_VERSION:
        return None
    supplemental = case.execution_identity
    if supplemental is None:
        raise VnvSchemaError("Schema-2 case has no execution identity block.")
    expected_failure = case.expected_failure
    if isinstance(expected_failure, ExpectedFailureContract):
        expected_failure_value: Any = expected_failure.to_dict()
    else:
        expected_failure_value = expected_failure
    payload = {
        "schema_version": 1,
        "source_sha": source_sha,
        "case_contract_version": supplemental["case_contract_version"],
        "units_resolved": supplemental["units_resolved"],
        "case_definition": {
            "case_id": case.case_id,
            "requirement_id": case.requirement_id,
            "capability_refs": list(case.capability_refs),
            "element": case.element,
            "analysis": case.analysis,
            "material": case.material,
            "route": case.route,
            "observables": list(case.observables),
            "expected_failure": expected_failure_value,
            "execution_tier": case.execution_tier,
        },
        "model_input": case.model_input,
        "input_files": supplemental["input_files"],
        "mesh": supplemental["mesh"],
        "material_data": supplemental["material_data"],
        "boundary_conditions": supplemental["boundary_conditions"],
        "loads": supplemental["loads"],
        "solver_configuration": supplemental["solver_configuration"],
        "resolved_overrides": supplemental["resolved_overrides"],
        "reference_identity": {
            "declared": supplemental["reference_identity"],
            "oracle": case.oracle.to_dict(),
        },
        "reference_files": supplemental["reference_files"],
        "tolerance_policy": {
            "declared": supplemental["tolerance_policy"],
            "case_tolerance": case.tolerance,
            "oracle_tolerance": case.oracle.tolerance,
            "comparison_rule": case.oracle.comparison_rule,
        },
        "metric_definitions": {
            "declared": supplemental["metric_definitions"],
            "observables": list(case.observables),
        },
        "software_versions": supplemental["software_versions"],
        "numerical_environment": supplemental["numerical_environment"],
        "rotation_configuration": supplemental["rotation_configuration"],
    }
    try:
        return ExecutionIdentity.from_dict(payload)
    except (ExecutionIdentityError, TypeError) as exc:
        raise VnvSchemaError(f"Cannot build schema-2 execution identity: {exc}") from exc


def _matches_expected_failure(expected: ExpectedFailureContract, exc: Exception) -> bool:
    actual_type = f"{type(exc).__module__}.{type(exc).__qualname__}"
    actual_stage = getattr(exc, "stage", None)
    actual_reason = getattr(exc, "reason", str(exc))
    actual_code = getattr(exc, "error_code", None)
    if actual_type != expected.expected_error_type or actual_stage != expected.expected_stage:
        return False
    if actual_reason != expected.expected_reason:
        return False
    if expected.expected_error_code is not None and actual_code != expected.expected_error_code:
        return False
    if expected.optional_message_pattern is not None:
        if re.search(expected.optional_message_pattern, str(exc)) is None:
            return False
    return True


def validate_case(data: VnvCase | Mapping[str, Any]) -> VnvCase:
    if isinstance(data, VnvCase):
        return data
    return VnvCase.from_dict(data)


def _default_environment() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "implementation": platform.python_implementation(),
    }


def _coerce_output(value: ExecutionOutput | Mapping[str, Any]) -> ExecutionOutput:
    if isinstance(value, ExecutionOutput):
        return value
    if not isinstance(value, Mapping) or not isinstance(value.get("observables"), Mapping):
        raise VnvSchemaError("Executor must return ExecutionOutput or an object with observables.")
    return ExecutionOutput(
        observables=dict(value["observables"]),
        runtime_seconds=float(value.get("runtime_seconds", 0.0)),
        peak_memory_mb=value.get("peak_memory_mb"),
        artifacts=dict(value.get("artifacts", {})),
        provenance=dict(value.get("provenance", {})),
    )


def _numeric(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _compare(case: VnvCase, observables: Mapping[str, Any]) -> tuple[bool, str | None]:
    oracle = case.oracle
    if oracle.observable not in observables:
        return False, f"Missing observable {oracle.observable!r}."
    observed = observables[oracle.observable]
    expected = oracle.expected
    if oracle.comparison_rule == "present":
        if observed is None:
            return False, f"Observable {oracle.observable!r} is null."
        return True, None
    if oracle.comparison_rule == "exact":
        return (observed == expected, f"Exact comparison failed for {oracle.observable!r}." if observed != expected else None)
    actual = _numeric(observed)
    target = _numeric(expected)
    if actual is None or target is None:
        return False, f"Observable {oracle.observable!r} and oracle expected value must be finite numbers."
    tolerance = oracle.tolerance if oracle.tolerance is not None else case.tolerance
    if oracle.comparison_rule == "absolute":
        error = abs(actual - target)
        return error <= tolerance, f"Absolute error {error:.6e} exceeds {tolerance:.6e}." if error > tolerance else None
    scale = max(abs(target), 1.0e-30)
    error = abs(actual - target) / scale
    return error <= tolerance, f"Relative error {error:.6e} exceeds {tolerance:.6e}." if error > tolerance else None


def _result_digest(case: VnvCase, observables: Mapping[str, Any], verdict: str, reason: str | None) -> str:
    return canonical_sha256(
        {
            "case_id": case.case_id,
            "observables": dict(observables),
            "verdict": verdict,
            "failure_reason": reason,
        }
    )


class VnvRunner:
    """Run validated cases and persist evidence without touching legacy runners."""

    def __init__(self, *, source_sha: str, environment: Mapping[str, Any] | None = None) -> None:
        if not isinstance(source_sha, str) or len(source_sha) < 7:
            raise ValueError("source_sha must identify the executed source revision.")
        self.source_sha = source_sha
        self.environment = dict(environment or _default_environment())

    def run(self, data: VnvCase | Mapping[str, Any], executor: Executor) -> VnvEvidence:
        case = validate_case(data)
        execution_identity = _case_execution_identity(case, self.source_sha)
        execution_key = execution_identity.execution_key() if execution_identity is not None else None
        input_digest = canonical_sha256(case.model_input)
        started = perf_counter()
        observables: dict[str, Any] = {}
        failure_reason: str | None = None
        verdict = "PASS"
        runtime_seconds = 0.0
        peak_memory_mb: float | None = None
        provenance = dict(case.provenance)
        try:
            output = _coerce_output(executor(case))
            observables = dict(output.observables)
            runtime_seconds = output.runtime_seconds
            peak_memory_mb = output.peak_memory_mb
            provenance.update(output.provenance or {})
            if case.expected_failure:
                verdict = "FAIL"
                failure_reason = f"Expected failure {case.expected_failure!r} did not occur."
            else:
                passed, failure_reason = _compare(case, observables)
                verdict = "PASS" if passed else "FAIL"
        except ExternalUnavailableError as exc:
            verdict = "SKIPPED_EXTERNAL_UNAVAILABLE"
            failure_reason = str(exc) or exc.__class__.__name__
        except ResourceLimitedError as exc:
            verdict = "RESOURCE_LIMITED"
            failure_reason = str(exc) or exc.__class__.__name__
        except Exception as exc:  # The evidence record must classify executor failures, never hide them.
            failure_reason = str(exc) or exc.__class__.__name__
            if isinstance(case.expected_failure, ExpectedFailureContract) and _matches_expected_failure(
                case.expected_failure, exc
            ):
                failure_reason = str(getattr(exc, "reason", failure_reason))
                verdict = "EXPECTED_FAILURE_PASS"
            elif isinstance(case.expected_failure, str) and case.expected_failure in failure_reason:
                verdict = "EXPECTED_FAILURE_PASS"
            else:
                verdict = "FAIL" if case.expected_failure is None else "INVALID_EVIDENCE"
        runtime_seconds = runtime_seconds or (perf_counter() - started)
        result_digest = _result_digest(case, observables, verdict, failure_reason)
        return VnvEvidence(
            case_id=case.case_id,
            requirement_id=case.requirement_id,
            source_sha=self.source_sha,
            input_digest=input_digest,
            result_digest=result_digest,
            timestamp=datetime.now(timezone.utc).isoformat(),
            environment=dict(self.environment),
            observables=observables,
            oracle=case.oracle.to_dict(),
            tolerance=case.tolerance,
            verdict=verdict,
            failure_reason=failure_reason,
            runtime_seconds=float(runtime_seconds),
            peak_memory_mb=peak_memory_mb,
            provenance=provenance,
            artifact_classification="CONTROLLED_PROOF",
            execution_key=execution_key,
            identity_schema_version=1 if execution_identity is not None else None,
        )

    @staticmethod
    def write_evidence(evidence: VnvEvidence, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(canonical_json_bytes(evidence.to_dict()))
        return target


def load_cases(path: str | Path) -> tuple[VnvCase, ...]:
    payload = load_json_strict(path)
    if not isinstance(payload, list):
        raise VnvSchemaError("V&V case catalog root must be a list.")
    return tuple(validate_case(item) for item in payload)


def load_prospective_cases(path: str | Path) -> tuple[VnvCase, ...]:
    """Load a new-campaign catalog and reject implicit inheritance of schema 1."""

    cases = load_cases(path)
    if not cases:
        raise VnvSchemaError("Prospective V&V case catalogs must not be empty.")
    legacy = [case.case_id for case in cases if case.schema_version != CASE_SCHEMA_VERSION]
    if legacy:
        raise VnvSchemaError(
            "Prospective catalogs must explicitly use schema_version 2; legacy cases: " + ", ".join(legacy)
        )
    return cases


def load_evidence(path: str | Path) -> VnvEvidence:
    payload = load_json_strict(path)
    required = _required_evidence_fields()
    missing = required - set(payload)
    if missing:
        raise VnvSchemaError(f"Evidence is missing fields: {sorted(missing)}.")
    allowed = {field.name for field in VnvEvidence.__dataclass_fields__.values()}
    return VnvEvidence(**{key: value for key, value in payload.items() if key in allowed})


def replay_case(
    data: VnvCase | Mapping[str, Any],
    executor: Executor,
    previous: VnvEvidence | Mapping[str, Any],
    *,
    source_sha: str,
    environment: Mapping[str, Any] | None = None,
) -> tuple[bool, str, VnvEvidence | None]:
    """Replay a case and explicitly classify source, input or result mismatches."""

    case = validate_case(data)
    prior = previous if isinstance(previous, VnvEvidence) else load_evidence_from_dict(previous)
    if prior.source_sha != source_sha:
        return False, "SOURCE_SHA_MISMATCH", None
    input_digest = canonical_sha256(case.model_input)
    if prior.input_digest != input_digest:
        return False, "INPUT_DIGEST_MISMATCH", None
    runner = VnvRunner(source_sha=source_sha, environment=environment)
    if case.schema_version == CASE_SCHEMA_VERSION:
        identity = _case_execution_identity(case, source_sha)
        expected_key = identity.execution_key() if identity is not None else None
        if prior.execution_key is None:
            return False, "EXECUTION_KEY_MISSING", None
        if prior.execution_key != expected_key:
            return False, "EXECUTION_KEY_MISMATCH", None
    current = runner.run(case, executor)
    if current.result_digest != prior.result_digest:
        return False, "RESULT_DIGEST_MISMATCH", current
    return True, "PASS", current


def load_evidence_from_dict(payload: Mapping[str, Any]) -> VnvEvidence:
    required = _required_evidence_fields()
    missing = required - set(payload)
    if missing:
        raise VnvSchemaError(f"Evidence is missing fields: {sorted(missing)}.")
    allowed = {field.name for field in VnvEvidence.__dataclass_fields__.values()}
    return VnvEvidence(**{key: value for key, value in payload.items() if key in allowed})


def _required_evidence_fields() -> set[str]:
    return {
        name
        for name, field in VnvEvidence.__dataclass_fields__.items()
        if field.default is MISSING and field.default_factory is MISSING
    }


def load_json_strict(path: str | Path) -> Any:
    """Load UTF-8 JSON and fail closed when an object repeats a key."""

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DuplicateJsonKeyError(f"Duplicate JSON key {key!r} in {Path(path)}.")
            result[key] = value
        return result

    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)
