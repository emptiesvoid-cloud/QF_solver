"""Public benchmark descriptors and run summaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class BenchmarkDescriptor:
    """Controlled definition of one reproducible mechanical benchmark."""

    identifier: str
    title: str
    family: str
    analyses: tuple[str, ...]
    maturity: str
    reference_type: str
    reference: str
    reference_id: str
    reference_url: str
    requirements: tuple[str, ...]
    criteria: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkRun:
    """Result and artifacts produced by one benchmark execution."""

    descriptor: BenchmarkDescriptor
    status: str
    metrics: dict[str, Any]
    checks: list[dict[str, Any]]
    files: dict[str, str] = field(default_factory=dict)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark": self.descriptor.to_dict(),
            "status": self.status,
            "metrics": self.metrics,
            "checks": self.checks,
            "files": self.files,
            "message": self.message,
        }
