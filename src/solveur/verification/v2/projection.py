"""Deterministic public projection for prospective structured V&V records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from typing import Any, Mapping

from solveur.verification.v2.execution_identity import (
    EVIDENCE_AVAILABILITY,
    ExecutionIdentityError,
    InputFileIdentity,
    _canonical_scientific_value,
    _reject_private_path,
)


_PUBLIC_FIELDS = {
    "record_schema_version",
    "benchmark_id",
    "source_sha",
    "execution_key",
    "numerical_status",
    "metrics",
    "limitations",
    "provenance",
    "evidence_availability",
    "maturity_status",
    "maturity_authority",
    "maturity_decision_id",
    "evidence_link",
}
_NUMERICAL_STATUSES = {"PASS", "FAIL", "SKIPPED", "NOT_AVAILABLE", "NOT_APPLICABLE", "RESOURCE_LIMITED"}
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class PublicProjectionError(ValueError):
    """Raised when a public record is incomplete or could leak local metadata."""


def _required_text(data: Mapping[str, Any], name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str) or not value.strip():
        raise PublicProjectionError(f"{name} must be a non-empty string.")
    try:
        _reject_private_path(value, name)
    except ExecutionIdentityError as exc:
        raise PublicProjectionError(str(exc)) from exc
    return value.strip()


@dataclass(frozen=True)
class PublicBenchmarkRecord:
    """User-facing projection with maturity kept distinct from numeric outcome."""

    benchmark_id: str
    source_sha: str
    execution_key: str
    numerical_status: str
    metrics: dict[str, Any]
    limitations: tuple[str, ...]
    provenance: tuple[InputFileIdentity, ...]
    evidence_availability: str
    maturity_status: str
    maturity_authority: str
    maturity_decision_id: str
    evidence_link: str
    record_schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            isinstance(self.record_schema_version, bool)
            or not isinstance(self.record_schema_version, int)
            or self.record_schema_version != 1
        ):
            raise PublicProjectionError("Unsupported public projection schema version.")
        for name in (
            "benchmark_id",
            "source_sha",
            "execution_key",
            "maturity_status",
            "maturity_authority",
            "maturity_decision_id",
            "evidence_link",
        ):
            _required_text(asdict(self), name)
        if self.numerical_status not in _NUMERICAL_STATUSES:
            raise PublicProjectionError(f"Unsupported numerical status {self.numerical_status!r}.")
        if not _GIT_SHA_PATTERN.fullmatch(self.source_sha):
            raise PublicProjectionError("source_sha must be a full lowercase Git SHA.")
        if not _SHA256_PATTERN.fullmatch(self.execution_key):
            raise PublicProjectionError("execution_key must be a lowercase SHA-256 digest.")
        if self.evidence_availability not in EVIDENCE_AVAILABILITY:
            raise PublicProjectionError(f"Unsupported evidence availability {self.evidence_availability!r}.")
        if not isinstance(self.metrics, dict) or not isinstance(self.limitations, tuple):
            raise PublicProjectionError("metrics must be an object and limitations must be a list.")
        if not all(isinstance(item, str) and item.strip() for item in self.limitations):
            raise PublicProjectionError("Each limitation must be a non-empty public statement.")
        try:
            for item in self.limitations:
                _reject_private_path(item, "public limitation")
        except ExecutionIdentityError as exc:
            raise PublicProjectionError(str(exc)) from exc
        if not all(isinstance(item, InputFileIdentity) for item in self.provenance):
            raise PublicProjectionError("provenance must contain content-addressed input records.")
        try:
            _canonical_scientific_value(self.metrics, "public.metrics")
        except ExecutionIdentityError as exc:
            raise PublicProjectionError(str(exc)) from exc

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PublicBenchmarkRecord":
        if not isinstance(data, Mapping):
            raise PublicProjectionError("Public projection must be an object.")
        unknown = set(data) - _PUBLIC_FIELDS
        missing = _PUBLIC_FIELDS - {"record_schema_version"} - set(data)
        if unknown:
            raise PublicProjectionError(f"Public projection has non-public/unknown fields: {sorted(unknown)}.")
        if missing:
            raise PublicProjectionError(f"Public projection is missing fields: {sorted(missing)}.")
        if not isinstance(data["metrics"], Mapping):
            raise PublicProjectionError("metrics must be an object.")
        if not isinstance(data["limitations"], list):
            raise PublicProjectionError("limitations must be a list.")
        if not isinstance(data["provenance"], list):
            raise PublicProjectionError("provenance must be a list.")
        schema_version = data.get("record_schema_version", 1)
        if isinstance(schema_version, bool) or not isinstance(schema_version, int) or schema_version != 1:
            raise PublicProjectionError("record_schema_version must be the integer 1.")
        try:
            provenance = tuple(InputFileIdentity.from_dict(item) for item in data["provenance"])
        except ExecutionIdentityError as exc:
            raise PublicProjectionError(f"Invalid public provenance: {exc}") from exc
        return cls(
            benchmark_id=_required_text(data, "benchmark_id"),
            source_sha=_required_text(data, "source_sha"),
            execution_key=_required_text(data, "execution_key"),
            numerical_status=_required_text(data, "numerical_status"),
            metrics=dict(data["metrics"]),
            limitations=tuple(data["limitations"]),
            provenance=provenance,
            evidence_availability=_required_text(data, "evidence_availability"),
            maturity_status=_required_text(data, "maturity_status"),
            maturity_authority=_required_text(data, "maturity_authority"),
            maturity_decision_id=_required_text(data, "maturity_decision_id"),
            evidence_link=_required_text(data, "evidence_link"),
            record_schema_version=schema_version,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_schema_version": self.record_schema_version,
            "benchmark_id": self.benchmark_id,
            "source_sha": self.source_sha,
            "execution_key": self.execution_key,
            "numerical_status": self.numerical_status,
            "metrics": _canonical_scientific_value(self.metrics, "public.metrics"),
            "limitations": list(self.limitations),
            "provenance": [item.to_dict() for item in self.provenance],
            "evidence_availability": self.evidence_availability,
            "maturity_status": self.maturity_status,
            "maturity_authority": self.maturity_authority,
            "maturity_decision_id": self.maturity_decision_id,
            "evidence_link": self.evidence_link,
        }


def render_public_benchmark(data: PublicBenchmarkRecord | Mapping[str, Any]) -> str:
    """Render a stable Markdown summary; numerical PASS never promotes maturity."""

    record = data if isinstance(data, PublicBenchmarkRecord) else PublicBenchmarkRecord.from_dict(data)
    metrics = json.dumps(record.metrics, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    lines = [
        f"### {record.benchmark_id}",
        "",
        f"- Numerical result: **{record.numerical_status}**",
        f"- Evidence availability: **{record.evidence_availability}**",
        f"- Maturity decision: **{record.maturity_status}** ({record.maturity_decision_id}; authority: {record.maturity_authority})",
        f"- Source: `{record.source_sha}`",
        f"- Execution key: `{record.execution_key}`",
        f"- Metrics: `{metrics}`",
        f"- Evidence: {record.evidence_link}",
        "- Limitations:",
    ]
    lines.extend(f"  - {item}" for item in record.limitations)
    lines.extend(["- Provenance:"])
    for item in sorted(record.provenance, key=lambda value: (value.logical_role, value.logical_id)):
        lines.append(
            "  - "
            f"{item.logical_role}: `{item.logical_id}`; SHA-256 `{item.sha256}`; "
            f"{item.size_bytes} bytes; {item.provenance}; {item.availability_status}"
        )
    return "\n".join(lines) + "\n"
