"""Structured execution result for a V&V case."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


_STATUSES = {"PASS", "FAIL", "EXPECTED_FAILURE", "BLOCKED", "SKIPPED", "NOT_STARTED"}


@dataclass(frozen=True)
class VnvCaseResult:
    """Result data intentionally separate from its immutable case definition."""

    case_id: str
    run_id: str
    source_sha: str | None
    timestamp_utc: str
    solver_version: str
    status: str
    failure_category: str | None
    environment: dict[str, Any]
    configuration: dict[str, Any]
    threshold_source: str
    metrics: dict[str, Any]
    diagnostics: dict[str, Any]
    artifact_digests: dict[str, str]
    wall_time_seconds: float
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise ValueError(f"Unsupported V&V result status {self.status!r}.")
        if self.status == "FAIL" and not self.failure_category:
            raise ValueError("A failing V&V result requires a failure_category.")

    def to_mapping(self) -> dict[str, Any]:
        data = asdict(self)
        data["warnings"] = list(self.warnings)
        return data
