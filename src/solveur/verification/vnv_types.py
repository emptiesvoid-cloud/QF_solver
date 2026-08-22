"""Typed records for controlled verification and validation studies."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VnvQuantitySpec:
    """One scalar mechanical quantity and its acceptance rule."""

    identifier: str
    label: str
    metric: str
    limit: float
    absolute_floor: float
    extraction: dict[str, str]


@dataclass(frozen=True)
class VnvLevel:
    """One mesh level and the two normalized result files to compare."""

    identifier: str
    characteristic_size: float
    qf_result: Path
    reference_result: Path


@dataclass(frozen=True)
class VnvConvergenceSpec:
    """Convergence requirements attached to one compared quantity."""

    quantity: str
    require_monotonic: bool
    minimum_order: float | None
    finest_error_limit: float


@dataclass(frozen=True)
class VnvStudy:
    """Validated V&V protocol loaded from a study JSON file."""

    source_path: Path
    identifier: str
    title: str
    scope: str
    subject: dict[str, str]
    units_system: str
    author: dict[str, str]
    validation: dict[str, Any]
    reference: dict[str, str]
    quantities: tuple[VnvQuantitySpec, ...]
    levels: tuple[VnvLevel, ...]
    convergence: tuple[VnvConvergenceSpec, ...]
    deformation_requirement: str


@dataclass(frozen=True)
class VnvQuantityValue:
    """One normalized scalar result with an explicit unit."""

    value: float
    unit: str


@dataclass(frozen=True)
class VnvNormalizedResult:
    """Solver-neutral result record used by the comparator."""

    source_path: Path
    case_id: str
    producer: dict[str, str]
    units_system: str
    mesh: dict[str, int | float]
    quantities: dict[str, VnvQuantityValue]
    diagnostics: dict[str, Any]
    visualization: dict[str, Any]
    artifacts: dict[str, Path]


@dataclass
class VnvStudyRun:
    """Generated comparison, convergence and owner-review status."""

    study: VnvStudy
    status: str
    automated_verdict: str
    owner_decision: str
    comparisons: list[dict[str, Any]]
    convergence: list[dict[str, Any]]
    checks: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]
    files: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "study": {
                "id": self.study.identifier,
                "title": self.study.title,
                "scope": self.study.scope,
                "subject": self.study.subject,
                "units_system": self.study.units_system,
                "author": self.study.author,
                "validation": self.study.validation,
                "reference": self.study.reference,
                "quantities": [asdict(item) for item in self.study.quantities],
                "levels": [
                    {"id": item.identifier, "characteristic_size": item.characteristic_size}
                    for item in self.study.levels
                ],
            },
            "status": self.status,
            "automated_verdict": self.automated_verdict,
            "owner_decision": self.owner_decision,
            "comparisons": self.comparisons,
            "convergence": self.convergence,
            "checks": self.checks,
            "artifacts": self.artifacts,
            "files": self.files,
        }
