"""Route-neutral runner for the controlled 026-G11 failure envelope."""

from __future__ import annotations

import json
import hashlib
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from numbers import Number
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


SUPPORTED_ROUTES = frozenset(
    {
        "linear_static",
        "nonlinear_static",
        "geometric_nonlinear_static",
        "modal",
        "linear_buckling",
        "linear_static_contact",
    }
)
ENVELOPE_FIELDS = (
    "FAILURE_CLASS",
    "ROUTE",
    "EXPECTED_BEHAVIOR",
    "ERROR_TYPE_OR_CODE",
    "STATE_PRESERVED",
    "DETERMINISTIC",
    "NO_NAN_INF",
    "NO_SILENT_PASS",
    "EVIDENCE_ID",
)
RUNNER_VERSION = "026-G11-runner-1"


@dataclass(frozen=True)
class G11CaseSpec:
    """A deterministic failure case description independent of a solver route."""

    case_id: str
    failure_class: str
    route: str
    expected_behavior: str
    adapter_id: str
    requirements: tuple[str, ...] = ()
    stateful: bool = False
    expected_error_types: tuple[str, ...] = ()
    expected_error_codes: tuple[str, ...] = ()
    expected_failure: bool = True
    definition_sha256: str | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        required = {
            "case_id": self.case_id,
            "failure_class": self.failure_class,
            "route": self.route,
            "expected_behavior": self.expected_behavior,
            "adapter_id": self.adapter_id,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"G11 case fields are required: {', '.join(missing)}")
        if self.route not in SUPPORTED_ROUTES:
            raise ValueError(f"Unsupported G11 route {self.route!r}.")
        if not self.expected_failure:
            raise ValueError("G11 runner only accepts failure/expected-failure cases.")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "G11CaseSpec":
        required = ("case_id", "failure_class", "route", "expected_behavior", "error_type_or_code")
        missing = [name for name in required if name not in data]
        if missing:
            raise ValueError(f"G11 case mapping is missing required field(s): {', '.join(missing)}")
        error_type_or_code = str(data["error_type_or_code"])
        error_parts = [part.strip() for part in error_type_or_code.split("/") if part.strip()]
        parsed = cls(
            case_id=str(data["case_id"]),
            failure_class=str(data["failure_class"]),
            route=str(data["route"]),
            expected_behavior=str(data["expected_behavior"]),
            adapter_id=str(data.get("adapter_id", data["case_id"])),
            requirements=tuple(str(item) for item in data.get("requirements", ())),
            stateful=bool(data.get("stateful", data.get("state_preserved") is True)),
            expected_error_types=tuple(
                str(item) for item in data.get("expected_error_types", error_parts[:1])
            ),
            expected_error_codes=tuple(
                str(item) for item in data.get("expected_error_codes", error_parts[1:])
            ),
            expected_failure=bool(data.get("expected_failure", True)),
        )
        encoded = json.dumps(dict(data), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return cls(**{**asdict(parsed), "definition_sha256": hashlib.sha256(encoded).hexdigest()})

    def definition_hash(self) -> str:
        """Return a stable digest of the case definition used for execution."""

        if self.definition_sha256:
            return self.definition_sha256
        payload = asdict(self)
        payload.pop("definition_sha256", None)
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class G11AdapterResult:
    """Route-adapter result without requiring a common Python exception type."""

    success: bool
    error_type_or_code: str | None = None
    state_preserved: bool | str = "NOT_APPLICABLE"
    payload: object = None
    diagnostics: Mapping[str, object] = field(default_factory=dict)


Adapter = Callable[[G11CaseSpec], object]


def load_case_specs(path: str | Path) -> tuple[G11CaseSpec, ...]:
    """Load and validate planned G11 cases without executing them."""

    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("G11 case specification must contain a non-empty cases list.")
    return tuple(G11CaseSpec.from_mapping(case) for case in cases)


class G11Runner:
    """Execute injected adapters and emit the qualitative G11 envelope."""

    def __init__(
        self,
        adapters: Mapping[str, Adapter],
        *,
        source_sha: str,
        provenance: Mapping[str, object] | None = None,
    ) -> None:
        if not source_sha:
            raise ValueError("G11 runner requires a non-empty source_sha.")
        self._adapters = dict(adapters)
        self._source_sha = source_sha
        self._provenance = dict(provenance or {})

    def run_case(self, case: G11CaseSpec, *, evidence_id: str | None = None) -> dict[str, object]:
        """Run one adapter twice and return the envelope plus audit metadata."""

        adapter = self._adapters.get(case.adapter_id)
        if adapter is None:
            raise ValueError(f"No G11 adapter registered for {case.adapter_id!r}.")
        first = self._observe(case, adapter)
        second = self._observe(case, adapter)
        deterministic = self._signature(first) == self._signature(second)
        envelope = {
            "FAILURE_CLASS": case.failure_class,
            "ROUTE": case.route,
            "EXPECTED_BEHAVIOR": case.expected_behavior,
            "ERROR_TYPE_OR_CODE": first["error_type_or_code"],
            "STATE_PRESERVED": first["state_preserved"],
            "DETERMINISTIC": deterministic,
            "NO_NAN_INF": first["no_nan_inf"],
            "NO_SILENT_PASS": first["no_silent_pass"],
            "EVIDENCE_ID": evidence_id or case.case_id,
        }
        expected_failure_observed = bool(first["observed_failure"])
        error_matches = self._error_matches(case, first)
        state_ok = not case.stateful or first["state_preserved"] is True
        status = "PASS" if all(
            (expected_failure_observed, error_matches, deterministic, first["no_nan_inf"], first["no_silent_pass"], state_ok)
        ) else "FAIL"
        return {
            "status": status,
            "envelope": envelope,
            "provenance": {
                "source_sha": self._source_sha,
                "runner_version": RUNNER_VERSION,
                "case_definition_sha256": case.definition_hash(),
                "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                **self._provenance,
            },
            "observations": {
                "first": _archive_observation(first),
                "replay": _archive_observation(second),
            },
            "requirements": list(case.requirements),
            "checks": {
                "expected_failure_observed": expected_failure_observed,
                "error_matches": error_matches,
                "state_check": state_ok,
                "adapter_id": case.adapter_id,
            },
        }

    def archive_result(self, result: Mapping[str, object], path: str | Path) -> Path:
        """Archive a JSON-safe runner record with the common envelope."""

        envelope = result.get("envelope")
        if not isinstance(envelope, Mapping) or set(envelope) != set(ENVELOPE_FIELDS):
            raise ValueError("Cannot archive a G11 result without the complete common envelope.")
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(dict(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target

    @staticmethod
    def _observe(case: G11CaseSpec, adapter: Adapter) -> dict[str, object]:
        try:
            raw = adapter(case)
        except Exception as error:  # route-native exceptions are intentionally captured, not replaced
            diagnostics = getattr(error, "diagnostics", {})
            if not isinstance(diagnostics, Mapping):
                diagnostics = {"message": str(error)}
            return {
                "observed_failure": True,
                "error_type_or_code": _error_type_or_code(error),
                "state_preserved": False if case.stateful else "NOT_APPLICABLE",
                "no_nan_inf": not _contains_nonfinite(diagnostics),
                "no_silent_pass": True,
                "diagnostics": dict(diagnostics),
            }
        if isinstance(raw, G11AdapterResult):
            observed_failure = not raw.success
            value = {"payload": raw.payload, "diagnostics": raw.diagnostics}
            error_type_or_code = raw.error_type_or_code if observed_failure else None
            state_preserved: bool | str = raw.state_preserved
            if case.stateful and state_preserved == "NOT_APPLICABLE":
                state_preserved = False
        else:
            observed_failure = False
            value = raw
            error_type_or_code = None
            state_preserved = False if case.stateful else "NOT_APPLICABLE"
        return {
            "observed_failure": observed_failure,
            "error_type_or_code": error_type_or_code,
            "state_preserved": state_preserved,
            "no_nan_inf": not _contains_nonfinite(value),
            "no_silent_pass": not (case.expected_failure and not observed_failure),
            "diagnostics": dict(raw.diagnostics) if isinstance(raw, G11AdapterResult) else {},
        }

    @staticmethod
    def _signature(observation: Mapping[str, object]) -> tuple[object, ...]:
        return tuple(observation.get(key) for key in ("observed_failure", "error_type_or_code", "state_preserved", "no_nan_inf", "no_silent_pass"))

    @staticmethod
    def _error_matches(case: G11CaseSpec, observation: Mapping[str, object]) -> bool:
        actual = str(observation["error_type_or_code"] or "")
        if not actual:
            return False
        if case.expected_error_types and not any(expected in actual for expected in case.expected_error_types):
            return False
        if case.expected_error_codes and not any(expected in actual for expected in case.expected_error_codes):
            return False
        return True


def _error_type_or_code(error: BaseException) -> str:
    reason = getattr(error, "reason", None)
    if isinstance(reason, Enum):
        reason = reason.value
    if reason is None:
        reason = getattr(error, "error_code", None)
    if reason is None:
        return type(error).__name__
    return f"{type(error).__name__}:{reason}"


def _archive_observation(observation: Mapping[str, object]) -> dict[str, object]:
    """Keep stable diagnostics while excluding potentially large solver payloads."""

    return {
        key: observation.get(key)
        for key in (
            "observed_failure",
            "error_type_or_code",
            "state_preserved",
            "no_nan_inf",
            "no_silent_pass",
            "diagnostics",
        )
    }


def _contains_nonfinite(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_nonfinite(item) for item in value.values())
    if isinstance(value, (str, bytes)) or value is None:
        return False
    if isinstance(value, Sequence):
        return any(_contains_nonfinite(item) for item in value)
    if isinstance(value, Number):
        try:
            return not math.isfinite(float(value))
        except (OverflowError, TypeError, ValueError):
            return True
    try:
        import numpy as np

        array = np.asarray(value)
        if array.dtype.kind in "fc":
            return bool(not np.isfinite(array).all())
    except (ImportError, TypeError, ValueError):
        pass
    return False
