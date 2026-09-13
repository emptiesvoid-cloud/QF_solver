"""Versioned, finite-only telemetry events for solver-wide observers.

The event model is deliberately independent from mechanics and from any
particular output sink. Legacy WP04 payloads are adapted in legacy.py; they
are not emitted by this module.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import cast


SCHEMA_VERSION = 1


class TelemetryValidationError(ValueError):
    """Raised when an event cannot satisfy the finite JSON contract."""


class SequenceError(TelemetryValidationError):
    """Raised when a per-analysis sequence is duplicated, skipped or regresses."""


class EventType(str, Enum):
    """Controlled event identifiers shared by future analysis routes."""

    ANALYSIS_START = "ANALYSIS_START"
    ANALYSIS_END = "ANALYSIS_END"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    MESH_READY = "MESH_READY"
    ASSEMBLY_START = "ASSEMBLY_START"
    ASSEMBLY_END = "ASSEMBLY_END"
    LINEAR_SOLVE_START = "LINEAR_SOLVE_START"
    LINEAR_SOLVE_ITERATION = "LINEAR_SOLVE_ITERATION"
    LINEAR_SOLVE_END = "LINEAR_SOLVE_END"
    STEP_START = "STEP_START"
    STEP_ACCEPTED = "STEP_ACCEPTED"
    STEP_REJECTED = "STEP_REJECTED"
    NONLINEAR_ITERATION = "NONLINEAR_ITERATION"
    LINE_SEARCH_TRIAL = "LINE_SEARCH_TRIAL"
    LINE_SEARCH_ACCEPTED = "LINE_SEARCH_ACCEPTED"
    LINE_SEARCH_REJECTED = "LINE_SEARCH_REJECTED"
    CHECKPOINT = "CHECKPOINT"
    CONTACT_STATE = "CONTACT_STATE"
    TIME_STEP_START = "TIME_STEP_START"
    TIME_STEP_ACCEPTED = "TIME_STEP_ACCEPTED"
    TIME_STEP_REJECTED = "TIME_STEP_REJECTED"
    MODAL_MODE_FOUND = "MODAL_MODE_FOUND"


class EventStatus(str, Enum):
    """Controlled lifecycle statuses used in the common envelope."""

    STARTED = "STARTED"
    RUNNING = "RUNNING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    CHECKPOINTED = "CHECKPOINTED"
    DEGRADED = "DEGRADED"
    INTERRUPTED = "INTERRUPTED"
    INFO = "INFO"


class MissingValueReason(str, Enum):
    """Reasons allowed for an explicitly unavailable measurement."""

    NOT_COMPUTABLE = "NOT_COMPUTABLE"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    BACKEND_UNSUPPORTED = "BACKEND_UNSUPPORTED"
    NOT_SAMPLED = "NOT_SAMPLED"
    NOT_EMITTED = "NOT_EMITTED"
    REDACTED = "REDACTED"


_MISSING_REASONS = frozenset(reason.value for reason in MissingValueReason)
_OPTIONAL_FIELDS = frozenset(
    {
        "timestamp",
        "step",
        "iteration",
        "load_factor",
        "physical_time",
        "solver_backend",
        "message",
    }
)
_MANDATORY_FIELDS = frozenset(
    {
        "schema_version",
        "event_type",
        "analysis_id",
        "analysis_type",
        "route",
        "sequence_number",
        "elapsed_time_s",
        "status",
        "metrics",
        "metadata",
    }
)


def missing_value(reason: MissingValueReason | str, *, detail: str | None = None) -> dict[str, object]:
    """Return an explicit JSON-safe representation for an unavailable metric."""

    value = reason.value if isinstance(reason, MissingValueReason) else reason
    if not isinstance(value, str) or value not in _MISSING_REASONS:
        raise TelemetryValidationError(f"Unknown missing-value reason: {reason!r}.")
    result: dict[str, object] = {"value": None, "reason": value}
    if detail is not None:
        if not isinstance(detail, str) or not detail.strip():
            raise TelemetryValidationError("Missing-value detail must be a non-empty string.")
        result["detail"] = detail
    return result


def _normalise_json_value(value: object, *, path: str, allow_null: bool) -> object:
    """Validate and detach a JSON value, rejecting non-finite numbers."""

    if value is None:
        if not allow_null:
            raise TelemetryValidationError(f"{path} is null without an explicit missing-value reason.")
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TelemetryValidationError(f"{path} must be finite, got {value!r}.")
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        normalised: dict[str, object] = {}
        is_missing_token = value.get("value", object()) is None and "reason" in value
        if is_missing_token:
            reason = value["reason"]
            if not isinstance(reason, str) or reason not in _MISSING_REASONS:
                raise TelemetryValidationError(f"{path}.reason is not a controlled missing-value reason.")
        for key, child in value.items():
            if not isinstance(key, str):
                raise TelemetryValidationError(f"{path} has a non-string key: {key!r}.")
            child_allow_null = True if is_missing_token and key == "value" else allow_null
            normalised[key] = _normalise_json_value(child, path=f"{path}.{key}", allow_null=child_allow_null)
        if is_missing_token and normalised.get("value") is not None:
            raise TelemetryValidationError(f"{path}.value must be null for a missing-value token.")
        if is_missing_token and set(normalised).difference({"value", "reason", "detail"}):
            raise TelemetryValidationError(f"{path} contains unsupported missing-value fields.")
        return normalised
    if isinstance(value, (list, tuple)):
        return [
            _normalise_json_value(child, path=f"{path}[{index}]", allow_null=allow_null)
            for index, child in enumerate(value)
        ]
    raise TelemetryValidationError(f"{path} is not JSON-compatible: {type(value).__name__}.")


def validate_json_value(value: object, *, allow_null: bool = True, path: str = "$") -> object:
    """Validate a detached JSON value for use by integrations and tests."""

    return _normalise_json_value(value, path=path, allow_null=allow_null)


def _finite_number(value: object, *, field_name: str, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TelemetryValidationError(f"{field_name} must be a finite number.")
    converted = float(value)
    if not math.isfinite(converted) or (nonnegative and converted < 0.0):
        raise TelemetryValidationError(f"{field_name} must be finite and valid, got {value!r}.")
    return converted


def _nonnegative_integer(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TelemetryValidationError(f"{field_name} must be a non-negative integer.")
    return value


@dataclass(frozen=True, slots=True)
class TelemetryEvent(Mapping[str, object]):
    """Validated common telemetry envelope.

    metrics rejects bare null values so that an unavailable measurement must
    use the missing_value helper. metadata may contain ordinary nulls for
    optional provenance fields.
    """

    schema_version: int
    event_type: EventType | str
    analysis_id: str
    analysis_type: str
    route: str
    sequence_number: int
    elapsed_time_s: float
    status: EventStatus | str
    metrics: Mapping[str, object]
    metadata: Mapping[str, object]
    timestamp: str | None = None
    step: int | None = None
    iteration: int | None = None
    load_factor: float | None = None
    physical_time: float | None = None
    solver_backend: str | None = None
    message: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.schema_version, bool) or not isinstance(self.schema_version, int):
            raise TelemetryValidationError("schema_version must be an integer.")
        if self.schema_version != SCHEMA_VERSION:
            raise TelemetryValidationError(
                f"Unsupported schema_version {self.schema_version!r}; expected {SCHEMA_VERSION}."
            )
        try:
            event_type = self.event_type if isinstance(self.event_type, EventType) else EventType(self.event_type)
        except (TypeError, ValueError) as error:
            raise TelemetryValidationError(f"Unknown event_type: {self.event_type!r}.") from error
        try:
            status = self.status if isinstance(self.status, EventStatus) else EventStatus(self.status)
        except (TypeError, ValueError) as error:
            raise TelemetryValidationError(f"Unknown status: {self.status!r}.") from error
        object.__setattr__(self, "event_type", event_type)
        object.__setattr__(self, "status", status)

        for field_name in ("analysis_id", "analysis_type", "route"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise TelemetryValidationError(f"{field_name} must be a non-empty string.")
        object.__setattr__(self, "sequence_number", _nonnegative_integer(self.sequence_number, field_name="sequence_number"))
        object.__setattr__(
            self,
            "elapsed_time_s",
            _finite_number(self.elapsed_time_s, field_name="elapsed_time_s", nonnegative=True),
        )
        if not isinstance(self.metrics, Mapping):
            raise TelemetryValidationError("metrics must be a mapping.")
        if not isinstance(self.metadata, Mapping):
            raise TelemetryValidationError("metadata must be a mapping.")
        metrics = _normalise_json_value(self.metrics, path="metrics", allow_null=False)
        metadata = _normalise_json_value(self.metadata, path="metadata", allow_null=True)
        if not isinstance(metrics, dict) or not isinstance(metadata, dict):
            raise TelemetryValidationError("metrics and metadata must remain mappings after validation.")
        object.__setattr__(self, "metrics", metrics)
        object.__setattr__(self, "metadata", metadata)

        if self.timestamp is not None and (not isinstance(self.timestamp, str) or not self.timestamp.strip()):
            raise TelemetryValidationError("timestamp must be a non-empty string when present.")
        for field_name in ("step", "iteration"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _nonnegative_integer(value, field_name=field_name))
        for field_name in ("load_factor", "physical_time"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _finite_number(value, field_name=field_name))
        for field_name in ("solver_backend", "message"):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, str):
                raise TelemetryValidationError(f"{field_name} must be a string when present.")

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "TelemetryEvent":
        """Validate a mapping without silently dropping unknown fields."""

        if not isinstance(value, Mapping):
            raise TelemetryValidationError("Telemetry event must be a mapping.")
        keys = set(value)
        missing = sorted(_MANDATORY_FIELDS.difference(keys))
        unknown = sorted(keys.difference(_MANDATORY_FIELDS | _OPTIONAL_FIELDS), key=str)
        if missing:
            raise TelemetryValidationError(f"Missing mandatory event fields: {', '.join(missing)}.")
        if unknown:
            raise TelemetryValidationError(f"Unknown event fields: {', '.join(map(str, unknown))}.")
        return cls(**dict(value))  # type: ignore[arg-type]

    def to_dict(self) -> dict[str, object]:
        """Return a detached mapping suitable for sinks and evidence."""

        result: dict[str, object] = {
            "schema_version": self.schema_version,
            "event_type": cast(EventType, self.event_type).value,
            "analysis_id": self.analysis_id,
            "analysis_type": self.analysis_type,
            "route": self.route,
            "sequence_number": self.sequence_number,
            "elapsed_time_s": self.elapsed_time_s,
            "status": cast(EventStatus, self.status).value,
            "metrics": dict(self.metrics),
            "metadata": dict(self.metadata),
        }
        for field_name in _OPTIONAL_FIELDS:
            field_value = getattr(self, field_name)
            if field_value is not None:
                result[field_name] = field_value
        return result

    def to_json(self) -> str:
        """Serialize deterministically and reject non-finite values."""

        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)

    def __getitem__(self, key: str) -> object:
        return self.to_dict()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_dict())

    def __len__(self) -> int:
        return len(self.to_dict())
