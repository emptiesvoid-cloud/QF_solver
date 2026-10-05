"""Fail-closed resume checks for prospective V&V execution records."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Mapping


_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_ABSOLUTE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")


class ResumeContractError(ValueError):
    """Raised for malformed or ambiguous safe-resume contracts."""


@dataclass(frozen=True)
class ResumeArtifact:
    """Required result artifact identified by a logical name and exact bytes."""

    logical_id: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.logical_id, str)
            or not self.logical_id
            or self.logical_id.startswith(("/", "\\"))
            or "\\" in self.logical_id
            or _WINDOWS_ABSOLUTE_PATTERN.match(self.logical_id)
            or self.logical_id.lower().startswith("file://")
        ):
            raise ResumeContractError("Artifact logical_id must be a non-empty relative identifier.")
        if any(part == ".." for part in self.logical_id.split("/")):
            raise ResumeContractError("Artifact logical_id cannot traverse parent directories.")
        if not isinstance(self.sha256, str) or not _SHA256_PATTERN.fullmatch(self.sha256):
            raise ResumeContractError("Artifact sha256 must be a lowercase 64-character digest.")
        if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int) or self.size_bytes < 0:
            raise ResumeContractError("Artifact size_bytes must be a non-negative integer.")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ResumeArtifact":
        if not isinstance(data, Mapping):
            raise ResumeContractError("Resume artifact must be an object.")
        if set(data) != {"logical_id", "sha256", "size_bytes"}:
            raise ResumeContractError("Resume artifact must declare exactly logical_id, sha256, and size_bytes.")
        return cls(**dict(data))


@dataclass(frozen=True)
class SafeResumeRecord:
    """Minimum record needed to assess reuse without relying on source SHA alone."""

    schema_version: int
    execution_key: str
    required_artifacts: tuple[ResumeArtifact, ...]

    def __post_init__(self) -> None:
        if isinstance(self.schema_version, bool) or not isinstance(self.schema_version, int) or self.schema_version != 1:
            raise ResumeContractError(f"Unsupported safe-resume schema {self.schema_version}.")
        if not isinstance(self.execution_key, str) or not _SHA256_PATTERN.fullmatch(self.execution_key):
            raise ResumeContractError("execution_key must be a lowercase SHA-256 digest.")
        if not isinstance(self.required_artifacts, tuple) or not self.required_artifacts:
            raise ResumeContractError("At least one required result artifact must be declared for reuse.")
        if not all(isinstance(item, ResumeArtifact) for item in self.required_artifacts):
            raise ResumeContractError("required_artifacts must contain only validated ResumeArtifact records.")
        ids = [item.logical_id for item in self.required_artifacts]
        if len(ids) != len(set(ids)):
            raise ResumeContractError("required_artifacts contains duplicate logical identifiers.")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SafeResumeRecord":
        if not isinstance(data, Mapping):
            raise ResumeContractError("Safe-resume record must be an object.")
        if set(data) != {"schema_version", "execution_key", "required_artifacts"}:
            raise ResumeContractError("Safe-resume record has missing or unknown fields.")
        artifacts = data["required_artifacts"]
        if not isinstance(artifacts, list):
            raise ResumeContractError("required_artifacts must be a list.")
        return cls(
            schema_version=data["schema_version"],
            execution_key=data["execution_key"],
            required_artifacts=tuple(ResumeArtifact.from_dict(item) for item in artifacts),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "execution_key": self.execution_key,
            "required_artifacts": [
                {"logical_id": item.logical_id, "sha256": item.sha256, "size_bytes": item.size_bytes}
                for item in self.required_artifacts
            ],
        }


@dataclass(frozen=True)
class ResumeAssessment:
    """Explicit decision; callers must execute unless status is exactly REUSE."""

    status: str
    reason: str


def assess_safe_resume(
    record: SafeResumeRecord | Mapping[str, Any],
    *,
    current_execution_key: str,
    artifact_bytes: Mapping[str, bytes],
    compatible_schema_versions: tuple[int, ...] = (1,),
) -> ResumeAssessment:
    """Return REUSE only when identity, schema and every required artifact match."""

    try:
        candidate = record if isinstance(record, SafeResumeRecord) else SafeResumeRecord.from_dict(record)
    except (ResumeContractError, TypeError, ValueError) as exc:
        return ResumeAssessment("REFUSE_RESUME", f"INVALID_RESUME_RECORD: {exc}")
    if not isinstance(compatible_schema_versions, tuple) or not all(
        isinstance(version, int) and not isinstance(version, bool) for version in compatible_schema_versions
    ):
        return ResumeAssessment("REFUSE_RESUME", "INVALID_COMPATIBLE_SCHEMA_VERSIONS")
    if candidate.schema_version not in compatible_schema_versions:
        return ResumeAssessment("REFUSE_RESUME", "INCOMPATIBLE_RESUME_SCHEMA")
    if not isinstance(current_execution_key, str) or not _SHA256_PATTERN.fullmatch(current_execution_key):
        return ResumeAssessment("REFUSE_RESUME", "INVALID_CURRENT_EXECUTION_KEY")
    if not isinstance(artifact_bytes, Mapping):
        return ResumeAssessment("REFUSE_RESUME", "INVALID_ARTIFACT_BYTES_MAPPING")
    if candidate.execution_key != current_execution_key:
        return ResumeAssessment("REEXECUTE", "EXECUTION_KEY_MISMATCH")
    for artifact in candidate.required_artifacts:
        content = artifact_bytes.get(artifact.logical_id)
        if not isinstance(content, bytes):
            return ResumeAssessment("REEXECUTE", f"REQUIRED_ARTIFACT_MISSING:{artifact.logical_id}")
        if len(content) != artifact.size_bytes or hashlib.sha256(content).hexdigest() != artifact.sha256:
            return ResumeAssessment("REEXECUTE", f"REQUIRED_ARTIFACT_MISMATCH:{artifact.logical_id}")
    return ResumeAssessment("REUSE", "EXECUTION_IDENTITY_SCHEMA_AND_ARTIFACTS_MATCH")
