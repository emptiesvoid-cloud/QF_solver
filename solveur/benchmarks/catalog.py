"""Machine-readable benchmark catalog."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from solveur.core.errors import InputValidationError
from solveur.benchmarks.types import BenchmarkDescriptor


DEFAULT_CATALOG = Path(__file__).resolve().parents[2] / "qualification" / "benchmarks.json"


class BenchmarkCatalog:
    """Load and validate the controlled benchmark registry."""

    def __init__(self, path: str | Path = DEFAULT_CATALOG) -> None:
        self.path = Path(path)
        self._descriptors = self._load()

    def list(self) -> tuple[BenchmarkDescriptor, ...]:
        return tuple(self._descriptors[key] for key in sorted(self._descriptors))

    def get(self, identifier: str) -> BenchmarkDescriptor:
        try:
            return self._descriptors[str(identifier).upper()]
        except KeyError as exc:
            available = ", ".join(sorted(self._descriptors))
            raise InputValidationError(f"Unknown benchmark {identifier!r}; available: {available}.") from exc

    def _load(self) -> dict[str, BenchmarkDescriptor]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InputValidationError(f"Cannot load benchmark catalog {self.path}: {exc}") from exc
        if not isinstance(payload, dict) or int(payload.get("schema_version", 0)) != 1:
            raise InputValidationError("Benchmark catalog schema_version must be 1.")
        records = payload.get("benchmarks")
        if not isinstance(records, list) or not records:
            raise InputValidationError("Benchmark catalog must contain benchmark records.")
        descriptors: dict[str, BenchmarkDescriptor] = {}
        for index, record in enumerate(records):
            descriptor = _descriptor(record, index)
            if descriptor.identifier in descriptors:
                raise InputValidationError(f"Duplicate benchmark id {descriptor.identifier!r}.")
            descriptors[descriptor.identifier] = descriptor
        return descriptors


def _descriptor(value: Any, index: int) -> BenchmarkDescriptor:
    if not isinstance(value, dict):
        raise InputValidationError(f"Benchmark record {index} must be an object.")
    required = {
        "id",
        "title",
        "family",
        "analysis",
        "maturity",
        "reference_type",
        "reference",
        "reference_id",
        "reference_url",
        "requirements",
        "criteria",
    }
    missing = sorted(required - value.keys())
    if missing:
        raise InputValidationError(f"Benchmark record {index} misses fields {missing}.")
    criteria = value["criteria"]
    if not isinstance(criteria, dict) or not criteria:
        raise InputValidationError(f"Benchmark {value['id']!r} requires numeric criteria.")
    analyses = value["analysis"]
    requirements = value["requirements"]
    maturity = str(value["maturity"])
    reference_url = str(value["reference_url"])
    if not isinstance(analyses, list) or not analyses:
        raise InputValidationError(f"Benchmark {value['id']!r} requires an analysis list.")
    if not isinstance(requirements, list) or not requirements:
        raise InputValidationError(f"Benchmark {value['id']!r} requires requirement identifiers.")
    if maturity not in {"stable", "stable_after_reinforced_tests", "experimental", "research"}:
        raise InputValidationError(f"Benchmark {value['id']!r} has unsupported maturity {maturity!r}.")
    if not reference_url.startswith("https://"):
        raise InputValidationError(f"Benchmark {value['id']!r} requires an HTTPS primary reference URL.")
    try:
        numeric_criteria = {str(key): float(item) for key, item in criteria.items()}
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"Benchmark {value['id']!r} has non-numeric criteria.") from exc
    if any(not math.isfinite(limit) or limit <= 0.0 for limit in numeric_criteria.values()):
        raise InputValidationError(f"Benchmark {value['id']!r} criteria must be finite and positive.")
    return BenchmarkDescriptor(
        identifier=str(value["id"]).upper(),
        title=str(value["title"]),
        family=str(value["family"]),
        analyses=tuple(str(item) for item in analyses),
        maturity=maturity,
        reference_type=str(value["reference_type"]),
        reference=str(value["reference"]),
        reference_id=str(value["reference_id"]),
        reference_url=reference_url,
        requirements=tuple(str(item) for item in requirements),
        criteria=numeric_criteria,
    )
