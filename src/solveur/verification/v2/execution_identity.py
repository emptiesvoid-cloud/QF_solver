"""Canonical, path-free identity contracts for prospective V&V executions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping


IDENTITY_SCHEMA_VERSION = 1
EVIDENCE_AVAILABILITY = {
    "AVAILABLE_AND_REPRODUCIBLE",
    "AVAILABLE_HISTORICAL_ONLY",
    "AVAILABLE_LOCAL_ONLY",
    "RECONSTRUCTED",
    "OPTIONAL_DEPENDENCY",
    "MISSING",
}
PROVENANCE_KINDS = {
    "REPOSITORY",
    "GENERATED",
    "EXTERNAL_VERSIONED",
    "LOCAL_ONLY",
    "MISSING",
    "RECONSTRUCTED",
    "OPTIONAL",
}
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_WINDOWS_ABSOLUTE_PATTERN = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/][^\s]*")
_POSIX_LOCAL_PATH_PATTERN = re.compile(
    r"(?<![A-Za-z0-9:])/(?:home|Users|tmp|private|var|workspace|workspaces|runner|mnt|root|Volumes)/"
)
_IDENTITY_FIELDS = {
    "schema_version",
    "source_sha",
    "case_contract_version",
    "units_resolved",
    "case_definition",
    "model_input",
    "input_files",
    "mesh",
    "material_data",
    "boundary_conditions",
    "loads",
    "solver_configuration",
    "resolved_overrides",
    "reference_identity",
    "reference_files",
    "tolerance_policy",
    "metric_definitions",
    "software_versions",
    "numerical_environment",
    "rotation_configuration",
}
_INPUT_FILE_FIELDS = {
    "logical_role",
    "logical_id",
    "sha256",
    "size_bytes",
    "provenance",
    "availability_status",
    "public_identifier",
}


class ExecutionIdentityError(ValueError):
    """Raised when a prospective execution identity is incomplete or unsafe."""


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExecutionIdentityError(f"{name} must be a non-empty string.")
    return value.strip()


def _reject_private_path(value: str, context: str) -> None:
    if (
        value.startswith("/")
        or "\\" in value
        or _WINDOWS_ABSOLUTE_PATTERN.search(value)
        or _POSIX_LOCAL_PATH_PATTERN.search(value)
    ):
        raise ExecutionIdentityError(f"Absolute local path is forbidden in {context}.")
    if value.lower().startswith("file://"):
        raise ExecutionIdentityError(f"file:// URI is forbidden in {context}.")


def _canonical_scientific_value(value: Any, context: str = "identity") -> Any:
    if isinstance(value, Path):
        raise ExecutionIdentityError(f"Path objects are forbidden in {context}; hash file bytes instead.")
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ExecutionIdentityError(f"Object keys in {context} must be strings.")
            normalized[key] = _canonical_scientific_value(item, f"{context}.{key}")
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, (list, tuple)):
        return [_canonical_scientific_value(item, f"{context}[]") for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ExecutionIdentityError(f"Non-finite number in {context}.")
        return value
    if isinstance(value, str):
        _reject_private_path(value, context)
        return value
    if value is None or isinstance(value, (bool, int)):
        return value
    raise ExecutionIdentityError(f"Unsupported value {type(value).__name__} in {context}.")


@dataclass(frozen=True)
class InputFileIdentity:
    """Content-addressed file provenance without a machine-local path."""

    logical_role: str
    logical_id: str
    sha256: str | None
    size_bytes: int | None
    provenance: str
    availability_status: str
    public_identifier: str | None = None

    def __post_init__(self) -> None:
        _text(self.logical_role, "logical_role")
        logical_id = _text(self.logical_id, "logical_id")
        _reject_private_path(logical_id, "logical_id")
        if "\\" in logical_id or any(part == ".." for part in logical_id.split("/")):
            raise ExecutionIdentityError("logical_id must be a safe relative/public identifier.")
        if not isinstance(self.provenance, str) or self.provenance not in PROVENANCE_KINDS:
            raise ExecutionIdentityError(f"Unsupported provenance kind {self.provenance!r}.")
        if not isinstance(self.availability_status, str) or self.availability_status not in EVIDENCE_AVAILABILITY:
            raise ExecutionIdentityError(f"Unsupported evidence availability {self.availability_status!r}.")
        if (self.sha256 is None) != (self.size_bytes is None):
            raise ExecutionIdentityError("sha256 and size_bytes must either both be present or both be null.")
        if self.sha256 is None:
            if self.availability_status not in {"MISSING", "OPTIONAL_DEPENDENCY"}:
                raise ExecutionIdentityError("Missing content digests require MISSING or OPTIONAL_DEPENDENCY status.")
        elif not isinstance(self.sha256, str) or not _SHA256_PATTERN.fullmatch(self.sha256):
            raise ExecutionIdentityError("sha256 must be a lowercase 64-character digest.")
        if self.size_bytes is not None and (
            isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int) or self.size_bytes < 0
        ):
            raise ExecutionIdentityError("size_bytes must be a non-negative integer or null for unavailable bytes.")
        if self.public_identifier is not None:
            public_identifier = _text(self.public_identifier, "public_identifier")
            _reject_private_path(public_identifier, "public_identifier")
            if "\\" in public_identifier or any(part == ".." for part in public_identifier.split("/")):
                raise ExecutionIdentityError("public_identifier must not contain unsafe path segments.")

    @classmethod
    def from_bytes(
        cls,
        *,
        logical_role: str,
        logical_id: str,
        content: bytes,
        provenance: str,
        availability_status: str,
        public_identifier: str | None = None,
    ) -> "InputFileIdentity":
        if not isinstance(content, bytes):
            raise ExecutionIdentityError("Input content must be bytes.")
        return cls(
            logical_role=logical_role,
            logical_id=logical_id,
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
            provenance=provenance,
            availability_status=availability_status,
            public_identifier=public_identifier,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "InputFileIdentity":
        if not isinstance(data, Mapping):
            raise ExecutionIdentityError("Input-file identity must be an object.")
        unknown = set(data) - _INPUT_FILE_FIELDS
        if unknown:
            raise ExecutionIdentityError(f"Unknown input-file fields: {sorted(unknown)}.")
        required = _INPUT_FILE_FIELDS - {"public_identifier"}
        missing = required - set(data)
        if missing:
            raise ExecutionIdentityError(f"Input-file identity is missing fields: {sorted(missing)}.")
        return cls(**dict(data))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def scientific_dict(self) -> dict[str, Any]:
        """Return the identity-bearing content fields, excluding availability labels."""

        return {
            "logical_role": self.logical_role,
            "logical_id": self.logical_id,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "public_identifier": self.public_identifier,
        }


@dataclass(frozen=True)
class ExecutionIdentity:
    """All declared scientific inputs and policies that define one V&V run."""

    source_sha: str
    case_contract_version: str
    units_resolved: bool
    case_definition: dict[str, Any]
    model_input: Any
    input_files: tuple[InputFileIdentity, ...]
    mesh: dict[str, Any]
    material_data: dict[str, Any]
    boundary_conditions: dict[str, Any]
    loads: dict[str, Any]
    solver_configuration: dict[str, Any]
    resolved_overrides: dict[str, Any]
    reference_identity: dict[str, Any]
    reference_files: tuple[InputFileIdentity, ...]
    tolerance_policy: dict[str, Any]
    metric_definitions: dict[str, Any]
    software_versions: dict[str, Any]
    numerical_environment: dict[str, Any]
    rotation_configuration: dict[str, Any]
    schema_version: int = IDENTITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != IDENTITY_SCHEMA_VERSION
        ):
            raise ExecutionIdentityError(f"Unsupported identity schema version {self.schema_version}.")
        if not isinstance(self.source_sha, str) or not _GIT_SHA_PATTERN.fullmatch(self.source_sha):
            raise ExecutionIdentityError("source_sha must be a full 40-character Git SHA.")
        _text(self.case_contract_version, "case_contract_version")
        if self.units_resolved is not True:
            raise ExecutionIdentityError("Execution identity requires resolved, canonical units.")
        for name in (
            "case_definition",
            "mesh",
            "material_data",
            "boundary_conditions",
            "loads",
            "solver_configuration",
            "resolved_overrides",
            "reference_identity",
            "tolerance_policy",
            "metric_definitions",
            "software_versions",
            "numerical_environment",
            "rotation_configuration",
        ):
            if not isinstance(getattr(self, name), dict):
                raise ExecutionIdentityError(f"{name} must be an object, including when empty.")
        self._validate_file_set(self.input_files, "input_files")
        self._validate_file_set(self.reference_files, "reference_files")
        # Validate nested JSON values and reject private paths before any run starts.
        for name, value in self.to_dict().items():
            _canonical_scientific_value(value, name)

    @staticmethod
    def _validate_file_set(files: tuple[InputFileIdentity, ...], name: str) -> None:
        if not isinstance(files, tuple) or not all(isinstance(item, InputFileIdentity) for item in files):
            raise ExecutionIdentityError(f"{name} must be a tuple of InputFileIdentity records.")
        ids = [(item.logical_role, item.logical_id) for item in files]
        if len(ids) != len(set(ids)):
            raise ExecutionIdentityError(f"{name} contains duplicate logical role/identifier pairs.")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExecutionIdentity":
        if not isinstance(data, Mapping):
            raise ExecutionIdentityError("Execution identity must be an object.")
        unknown = set(data) - _IDENTITY_FIELDS
        if unknown:
            raise ExecutionIdentityError(f"Unknown execution identity fields: {sorted(unknown)}.")
        missing = _IDENTITY_FIELDS - set(data)
        if missing:
            raise ExecutionIdentityError(f"Execution identity is missing fields: {sorted(missing)}.")
        value = dict(data)
        if not isinstance(value["input_files"], list) or not isinstance(value["reference_files"], list):
            raise ExecutionIdentityError("input_files and reference_files must be lists.")
        value["input_files"] = tuple(InputFileIdentity.from_dict(item) for item in value["input_files"])
        value["reference_files"] = tuple(InputFileIdentity.from_dict(item) for item in value["reference_files"])
        return cls(**value)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["input_files"] = [item.to_dict() for item in self.input_files]
        value["reference_files"] = [item.to_dict() for item in self.reference_files]
        return value

    def scientific_payload(self) -> dict[str, Any]:
        value = self.to_dict()
        value["input_files"] = [item.scientific_dict() for item in self._sorted_files(self.input_files)]
        value["reference_files"] = [item.scientific_dict() for item in self._sorted_files(self.reference_files)]
        return _canonical_scientific_value(value)

    @staticmethod
    def _sorted_files(files: tuple[InputFileIdentity, ...]) -> tuple[InputFileIdentity, ...]:
        return tuple(sorted(files, key=lambda item: (item.logical_role, item.logical_id)))

    def execution_key(self, *, operational_context: Mapping[str, Any] | None = None) -> str:
        """Hash scientific identity; timestamp/output/temp context is deliberately excluded."""

        # This argument is explicitly out-of-band; it may contain machine-local
        # output/temp paths and timestamps and is never inspected or serialized.
        # No fields are filtered from the scientific payload itself.
        del operational_context
        payload = json.dumps(
            self.scientific_payload(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(b"QF-VNV-EXECUTION-IDENTITY-v1\n" + payload).hexdigest()


def prospective_identity_inputs(data: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the case-level supplemental identity block used by schema 2."""

    if not isinstance(data, Mapping):
        raise ExecutionIdentityError("Supplemental execution identity must be an object.")
    required = {
        "case_contract_version",
        "units_resolved",
        "input_files",
        "mesh",
        "material_data",
        "boundary_conditions",
        "loads",
        "solver_configuration",
        "resolved_overrides",
        "reference_identity",
        "reference_files",
        "tolerance_policy",
        "metric_definitions",
        "software_versions",
        "numerical_environment",
        "rotation_configuration",
    }
    unknown = set(data) - required
    missing = required - set(data)
    if unknown:
        raise ExecutionIdentityError(f"Unknown supplemental identity fields: {sorted(unknown)}.")
    if missing:
        raise ExecutionIdentityError(f"Supplemental identity is missing fields: {sorted(missing)}.")
    if data["units_resolved"] is not True:
        raise ExecutionIdentityError("units_resolved must be true before case execution.")
    for name in required - {"case_contract_version", "units_resolved", "input_files", "reference_files"}:
        if not isinstance(data[name], Mapping):
            raise ExecutionIdentityError(f"Supplemental identity field {name} must be an object.")
        _canonical_scientific_value(data[name], name)
    _text(data["case_contract_version"], "case_contract_version")
    for name in ("input_files", "reference_files"):
        if not isinstance(data[name], list):
            raise ExecutionIdentityError(f"Supplemental identity field {name} must be a list.")
        for item in data[name]:
            InputFileIdentity.from_dict(item)
    return dict(data)
