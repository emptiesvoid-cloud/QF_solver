"""Machine-readable contracts for declarative V&V v2 cases."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import re
from typing import Any, Mapping

from solveur.verification.v2.execution_identity import ExecutionIdentityError, prospective_identity_inputs

LEGACY_CASE_SCHEMA_VERSION = 1
CASE_SCHEMA_VERSION = 2
ORACLE_TYPES = {
    "ANALYTICAL",
    "INTERNAL_INVARIANT",
    "CROSS_ELEMENT",
    "EXTERNAL_SOLVER",
    "REFERENCE_DATA",
    "FAILURE_EXPECTATION",
}
EXECUTION_TIERS = {"T0", "T1", "T2", "T3"}
VERDICTS = {
    "PASS",
    "FAIL",
    "SKIPPED_EXTERNAL_UNAVAILABLE",
    "RESOURCE_LIMITED",
    "EXPECTED_FAILURE_PASS",
    "INVALID_EVIDENCE",
}
COMPARISON_RULES = {"exact", "absolute", "relative", "present"}
_CASE_FIELDS = {
    "schema_version",
    "case_id",
    "requirement_id",
    "capability_refs",
    "element",
    "analysis",
    "material",
    "route",
    "model_input",
    "oracle",
    "observables",
    "tolerance",
    "expected_failure",
    "execution_tier",
    "provenance",
    "execution_identity",
}
_EXPECTED_FAILURE_FIELDS = {
    "expected_stage",
    "expected_error_type",
    "expected_reason",
    "expected_error_code",
    "optional_message_pattern",
}
_ORACLE_FIELDS = {
    "type",
    "source",
    "observable",
    "unit",
    "comparison_rule",
    "tolerance",
    "expected",
    "provenance",
}


class VnvSchemaError(ValueError):
    """Raised when a declarative case or oracle violates the v2 schema."""


@dataclass(frozen=True)
class ExpectedFailureContract:
    """Specific, prospective expected-failure contract for schema-2 cases."""

    expected_stage: str
    expected_error_type: str
    expected_reason: str
    expected_error_code: str | None = None
    optional_message_pattern: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExpectedFailureContract":
        if not isinstance(data, Mapping):
            raise VnvSchemaError("expected_failure must be an object.")
        unknown = set(data) - _EXPECTED_FAILURE_FIELDS
        if unknown:
            raise VnvSchemaError(f"Unknown expected_failure fields: {sorted(unknown)}.")
        required = {"expected_stage", "expected_error_type", "expected_reason"}
        missing = required - set(data)
        if missing:
            raise VnvSchemaError(f"expected_failure is missing fields: {sorted(missing)}.")
        values: dict[str, str | None] = {}
        for name in required:
            value = data[name]
            if not isinstance(value, str) or not value.strip():
                raise VnvSchemaError(f"expected_failure.{name} must be a non-empty string.")
            values[name] = value.strip()
        for name in ("expected_error_code", "optional_message_pattern"):
            value = data.get(name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise VnvSchemaError(f"expected_failure.{name} must be null or a non-empty string.")
            values[name] = value.strip() if isinstance(value, str) else None
        pattern = values["optional_message_pattern"]
        if pattern is not None:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise VnvSchemaError(f"Invalid expected_failure.optional_message_pattern: {exc}.") from exc
        return cls(**values)

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


def _required(data: Mapping[str, Any], name: str) -> Any:
    if name not in data:
        raise VnvSchemaError(f"Missing required field {name!r}.")
    return data[name]


def _text(data: Mapping[str, Any], name: str) -> str:
    value = _required(data, name)
    if not isinstance(value, str) or not value.strip():
        raise VnvSchemaError(f"Field {name!r} must be a non-empty string.")
    return value.strip()


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise VnvSchemaError(f"Field {name!r} must be an object.")
    return dict(value)


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise VnvSchemaError(f"Field {name!r} must be finite numeric data.")
    return float(value)


@dataclass(frozen=True)
class VnvOracle:
    """One explicit oracle and its predeclared comparison policy."""

    type: str
    source: str
    observable: str
    unit: str
    comparison_rule: str
    tolerance: float
    expected: Any
    provenance: dict[str, Any]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "VnvOracle":
        unknown = set(data) - _ORACLE_FIELDS
        if unknown:
            raise VnvSchemaError(f"Unknown oracle fields: {sorted(unknown)}.")
        oracle_type = _text(data, "type").upper()
        if oracle_type not in ORACLE_TYPES:
            raise VnvSchemaError(f"Unsupported oracle type {oracle_type!r}.")
        comparison = _text(data, "comparison_rule").lower()
        if comparison not in COMPARISON_RULES:
            raise VnvSchemaError(f"Unsupported comparison rule {comparison!r}.")
        tolerance = _finite_number(_required(data, "tolerance"), "tolerance")
        if tolerance < 0.0:
            raise VnvSchemaError("Oracle tolerance must be non-negative.")
        provenance = _mapping(_required(data, "provenance"), "provenance")
        if not provenance:
            raise VnvSchemaError("Oracle provenance must not be empty.")
        return cls(
            type=oracle_type,
            source=_text(data, "source"),
            observable=_text(data, "observable"),
            unit=_text(data, "unit"),
            comparison_rule=comparison,
            tolerance=tolerance,
            expected=data.get("expected"),
            provenance=provenance,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VnvCase:
    """A complete declarative V&V case, independent of its executor."""

    case_id: str
    requirement_id: str
    capability_refs: tuple[str, ...]
    element: str
    analysis: str
    material: str
    route: str
    model_input: Any
    oracle: VnvOracle
    observables: tuple[str, ...]
    tolerance: float
    expected_failure: str | ExpectedFailureContract | None
    execution_tier: str
    provenance: dict[str, Any]
    schema_version: int = LEGACY_CASE_SCHEMA_VERSION
    execution_identity: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "VnvCase":
        if not isinstance(data, Mapping):
            raise VnvSchemaError("V&V case must be an object.")
        unknown = set(data) - _CASE_FIELDS
        if unknown:
            raise VnvSchemaError(f"Unknown case fields: {sorted(unknown)}.")
        raw_version = data.get("schema_version", LEGACY_CASE_SCHEMA_VERSION)
        if isinstance(raw_version, bool) or not (
            isinstance(raw_version, int) or (isinstance(raw_version, str) and raw_version.strip() in {"1", "2"})
        ):
            raise VnvSchemaError(f"Unsupported V&V case schema version {raw_version!r}.")
        version = int(raw_version)
        if version not in {LEGACY_CASE_SCHEMA_VERSION, CASE_SCHEMA_VERSION}:
            raise VnvSchemaError(f"Unsupported V&V case schema version {version}.")
        refs = _required(data, "capability_refs")
        if not isinstance(refs, list) or not refs or not all(isinstance(item, str) and item.strip() for item in refs):
            raise VnvSchemaError("capability_refs must be a non-empty list of strings.")
        observables = _required(data, "observables")
        if not isinstance(observables, list) or not observables or not all(isinstance(item, str) and item.strip() for item in observables):
            raise VnvSchemaError("observables must be a non-empty list of strings.")
        tolerance = _finite_number(_required(data, "tolerance"), "tolerance")
        if tolerance < 0.0:
            raise VnvSchemaError("Case tolerance must be non-negative.")
        failure = data.get("expected_failure")
        if version == LEGACY_CASE_SCHEMA_VERSION:
            if "execution_identity" in data:
                raise VnvSchemaError("execution_identity is only supported by schema-2 cases.")
            if failure is not None and (not isinstance(failure, str) or not failure.strip()):
                raise VnvSchemaError("Legacy expected_failure must be null or a non-empty string.")
            expected_failure: str | ExpectedFailureContract | None = failure.strip() if isinstance(failure, str) else None
            execution_identity = None
        else:
            if "expected_failure" not in data:
                raise VnvSchemaError("Schema-2 cases must explicitly declare expected_failure as an object or null.")
            if failure is not None and not isinstance(failure, Mapping):
                raise VnvSchemaError("Schema-2 expected_failure must be null or a structured object.")
            expected_failure = ExpectedFailureContract.from_dict(failure) if isinstance(failure, Mapping) else None
            identity = _mapping(_required(data, "execution_identity"), "execution_identity")
            try:
                execution_identity = prospective_identity_inputs(identity)
            except ExecutionIdentityError as exc:
                raise VnvSchemaError(f"Invalid execution_identity: {exc}") from exc
        tier = _text(data, "execution_tier").upper()
        if tier not in EXECUTION_TIERS:
            raise VnvSchemaError(f"Unsupported execution tier {tier!r}.")
        provenance = _mapping(_required(data, "provenance"), "provenance")
        if not provenance:
            raise VnvSchemaError("Case provenance must not be empty.")
        return cls(
            schema_version=version,
            case_id=_text(data, "case_id"),
            requirement_id=_text(data, "requirement_id"),
            capability_refs=tuple(item.strip() for item in refs),
            element=_text(data, "element").upper(),
            analysis=_text(data, "analysis").lower(),
            material=_text(data, "material").lower(),
            route=_text(data, "route").lower(),
            model_input=data.get("model_input"),
            oracle=VnvOracle.from_dict(_mapping(_required(data, "oracle"), "oracle")),
            observables=tuple(item.strip() for item in observables),
            tolerance=tolerance,
            expected_failure=expected_failure,
            execution_tier=tier,
            provenance=provenance,
            execution_identity=execution_identity,
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["capability_refs"] = list(self.capability_refs)
        result["observables"] = list(self.observables)
        result["oracle"] = self.oracle.to_dict()
        if isinstance(self.expected_failure, ExpectedFailureContract):
            result["expected_failure"] = self.expected_failure.to_dict()
        if self.execution_identity is None:
            result.pop("execution_identity", None)
        return result
