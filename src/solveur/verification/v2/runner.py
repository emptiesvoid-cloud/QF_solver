"""Deterministic execution and evidence handling for V&V v2 cases."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
from time import perf_counter
from typing import Any, Callable, Mapping

from solveur.io.manifest import content_digest
from solveur.verification.v2.schema import VnvCase, VnvSchemaError, VERDICTS


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

    def __post_init__(self) -> None:
        if self.verdict not in VERDICTS:
            raise ValueError(f"Invalid V&V verdict {self.verdict!r}.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


Executor = Callable[[VnvCase], ExecutionOutput | Mapping[str, Any]]


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
            if case.expected_failure and case.expected_failure in failure_reason:
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
        )

    @staticmethod
    def write_evidence(evidence: VnvEvidence, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(canonical_json_bytes(evidence.to_dict()))
        return target


def load_cases(path: str | Path) -> tuple[VnvCase, ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise VnvSchemaError("V&V case catalog root must be a list.")
    return tuple(validate_case(item) for item in payload)


def load_evidence(path: str | Path) -> VnvEvidence:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {field.name for field in VnvEvidence.__dataclass_fields__.values()}
    missing = required - set(payload)
    if missing:
        raise VnvSchemaError(f"Evidence is missing fields: {sorted(missing)}.")
    return VnvEvidence(**{key: payload[key] for key in required})


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
    current = VnvRunner(source_sha=source_sha, environment=environment).run(case, executor)
    if current.result_digest != prior.result_digest:
        return False, "RESULT_DIGEST_MISMATCH", current
    return True, "PASS", current


def load_evidence_from_dict(payload: Mapping[str, Any]) -> VnvEvidence:
    required = {field.name for field in VnvEvidence.__dataclass_fields__.values()}
    missing = required - set(payload)
    if missing:
        raise VnvSchemaError(f"Evidence is missing fields: {sorted(missing)}.")
    return VnvEvidence(**{key: payload[key] for key in required})
