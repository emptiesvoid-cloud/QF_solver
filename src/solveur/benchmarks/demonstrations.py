"""Cross-cutting catalog of documented, reproducible demonstrations."""

from __future__ import annotations

import importlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from solveur.benchmarks.catalog import BenchmarkCatalog
from solveur.benchmarks.runner import BenchmarkRunner
from solveur.core.errors import InputValidationError
from solveur.core.qualification import enforce_qualification_policy, qualification_summary
from solveur.core.router import AnalysisRouter
from solveur.io.evidence_writer import EvidenceBundleWriter
from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.large.campaign import run_large_scale_campaign
from solveur.paths import project_path, project_root
from solveur.verification.campaign import QualificationCampaignRunner

DEFAULT_CATALOG = project_path("qualification/demonstrations.json")
PROJECT_ROOT = project_root()
_GENERATED_MODEL_PREFIX = "generated:"
DEFAULT_QUALIFICATION_CAMPAIGN = PROJECT_ROOT / "qualification" / "campaign.json"
_BENCHMARK_OUTPUTS = frozenset({"benchmark_summary.json", "benchmark_manifest.json"})
_QUALIFICATION_CASE_OUTPUTS = frozenset({"qualification_case_summary.json", "evidence_manifest.json"})
_MODEL_OUTPUTS = frozenset({"demonstration_summary.json", "results.json", "evidence_manifest.json"})
_LARGE_PLAN_OUTPUTS = frozenset({"large_campaign.json", "large_campaign.md", "evidence_manifest.json"})


@dataclass(frozen=True)
class DemonstrationDescriptor:
    """Documentation and reproducibility contract for one demonstration."""

    demo_id: str
    benchmark_id: str
    title: str
    family: str
    method: str
    maturity: str
    model: str
    runner: str
    documentation: str
    tests: tuple[str, ...]
    requirements: tuple[str, ...]
    references: tuple[str, ...]
    outputs: tuple[str, ...]
    limitations: tuple[str, ...]
    execution: str = "benchmark"
    case_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DemonstrationIntegrityReport:
    """File, runner and traceability checks for the demonstration registry."""

    checked_count: int
    issues: tuple[str, ...]

    @property
    def status(self) -> str:
        """Return the machine-readable integrity verdict."""
        return "PASS" if not self.issues else "FAIL"


class DemonstrationCatalog:
    """Load, validate and filter the public demonstration registry."""

    def __init__(self, path: str | Path = DEFAULT_CATALOG) -> None:
        self.path = Path(path)
        self._descriptors = self._load()

    def list(self, *, family: str | None = None, method: str | None = None,
             maturity: str | None = None) -> tuple[DemonstrationDescriptor, ...]:
        values = tuple(self._descriptors[key] for key in sorted(self._descriptors))
        return tuple(item for item in values
                     if _matches(item.family, family)
                     and _matches(item.method, method)
                     and _matches(item.maturity, maturity))

    def get(self, identifier: str) -> DemonstrationDescriptor:
        try:
            return self._descriptors[str(identifier).upper()]
        except KeyError as exc:
            available = ", ".join(sorted(self._descriptors))
            raise InputValidationError(f"Unknown demonstration {identifier!r}; available: {available}.") from exc

    def validate_integrity(self, root: str | Path = PROJECT_ROOT) -> DemonstrationIntegrityReport:
        """Check documentation, runner and traceability references without running a case.

        The check is deliberately opt-in: installed users can list the public
        library catalog without bundling the documentation site, while CI can
        reject an orphaned demonstration before publication.
        """
        base = Path(root).resolve()
        benchmark_ids = {item.identifier for item in BenchmarkCatalog().list()}
        qualification_case_ids = _qualification_case_ids(base)
        requirement_ids = _requirement_ids(base)
        reference_ids = _reference_ids(base)
        issues: list[str] = []
        for item in self.list():
            prefix = f"{item.demo_id}:"
            if item.execution == "benchmark" and item.benchmark_id not in benchmark_ids:
                issues.append(f"{prefix} unknown benchmark {item.benchmark_id!r}")
            if item.execution == "qualification_case" and item.case_id not in qualification_case_ids:
                issues.append(f"{prefix} unknown qualification case {item.case_id!r}")
            if not _model_is_reproducible(item, base):
                issues.append(f"{prefix} missing or invalid model {item.model!r}")
            if not (base / item.documentation).is_file():
                issues.append(f"{prefix} missing documentation {item.documentation!r}")
            if not _runner_is_callable(item.runner):
                issues.append(f"{prefix} missing runner {item.runner!r}")
            for test_path in item.tests:
                if not (base / test_path).is_file():
                    issues.append(f"{prefix} missing test {test_path!r}")
            for requirement in item.requirements:
                if requirement not in requirement_ids:
                    issues.append(f"{prefix} unknown requirement {requirement!r}")
            for reference in item.references:
                if reference not in reference_ids:
                    issues.append(f"{prefix} unknown reference {reference!r}")
            missing_outputs = sorted(_required_outputs(item) - set(item.outputs))
            if missing_outputs:
                issues.append(f"{prefix} non-reproducible outputs missing {missing_outputs}")
        return DemonstrationIntegrityReport(len(self._descriptors), tuple(sorted(issues)))

    def _load(self) -> dict[str, DemonstrationDescriptor]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InputValidationError(f"Cannot load demonstration catalog {self.path}: {exc}") from exc
        if not isinstance(payload, dict) or int(payload.get("schema_version", 0)) != 1:
            raise InputValidationError("Demonstration catalog schema_version must be 1.")
        records = payload.get("demonstrations")
        if not isinstance(records, list) or not records:
            raise InputValidationError("Demonstration catalog must contain records.")
        result: dict[str, DemonstrationDescriptor] = {}
        for index, record in enumerate(records):
            descriptor = _descriptor(record, index)
            if descriptor.demo_id in result:
                raise InputValidationError(f"Duplicate demonstration id {descriptor.demo_id!r}.")
            result[descriptor.demo_id] = descriptor
        return result


class DemonstrationRunner:
    """Expose demonstrations while reusing the existing benchmark runners."""

    def __init__(self, catalog: DemonstrationCatalog | None = None) -> None:
        self.catalog = catalog or DemonstrationCatalog()
        self.benchmarks = BenchmarkRunner()
        self.qualification = QualificationCampaignRunner()

    def list(self, **filters: str | None) -> tuple[DemonstrationDescriptor, ...]:
        return self.catalog.list(**filters)

    def run(self, identifier: str, output_dir: str | Path, *, profile: str = "engineering") -> object:
        descriptor = self.catalog.get(identifier)
        if descriptor.execution == "benchmark":
            return self.benchmarks.run(descriptor.benchmark_id, output_dir, profile=profile)
        if descriptor.execution == "qualification_case" and descriptor.case_id is not None:
            return self.qualification.run_case(DEFAULT_QUALIFICATION_CAMPAIGN, descriptor.case_id, output_dir)
        if descriptor.execution == "model":
            return run_model_demonstration(PROJECT_ROOT / descriptor.model, output_dir, profile=profile)
        if descriptor.execution == "large_plan":
            return run_large_plan_demonstration(output_dir)
        raise InputValidationError(f"Unsupported demonstration execution {descriptor.execution!r}.")


def run_model_demonstration(
    model_path: str | Path,
    output_dir: str | Path,
    *,
    profile: str = "engineering",
) -> dict[str, Any]:
    """Solve one checked-in JSON model and write a compact evidence bundle.

    This execution route is for documented examples that already have an
    independently maintained V&V campaign but are not Gmsh benchmarks.  It
    deliberately reuses the public solver path and evidence format rather
    than duplicating an element-specific demonstration runner.
    """
    source = Path(model_path).resolve()
    target = Path(output_dir)
    model = JsonModelReader().read(source)
    model.verification_profile = profile
    result = enforce_qualification_policy(AnalysisRouter().solve(model), model)
    artifacts = EvidenceBundleWriter().write(model=model, result=result, directory=target, input_path=source)
    verdict = getattr(getattr(result, "run_verdict", None), "value", getattr(result, "run_verdict", ""))
    summary = {
        "status": str(verdict or getattr(result, "status", "")),
        "analysis": model.analysis.type,
        "verification_profile": model.verification_profile,
        "qualification": qualification_summary(result, model),
        "artifacts": {name: str(path) for name, path in sorted(artifacts.items())},
    }
    write_json_file(target / "demonstration_summary.json", summary)
    return summary


def run_large_plan_demonstration(output_dir: str | Path) -> dict[str, Any]:
    """Plan the 1M-DOF PETSc/MPI demonstration without allocating a model.

    The returned verdict intentionally remains ``PLANNED`` when the local
    environment is ready and ``BLOCKED`` when PETSc/MPI is unavailable.  A
    distributed solve is a separate controlled campaign, never an implicit
    workstation-side fallback.
    """
    return run_large_scale_campaign(
        output_dir,
        targets=(1_000_000,),
        solver_backend="petsc",
        execute=False,
    )


def _matches(value: str, expected: str | None) -> bool:
    return expected is None or value.casefold() == str(expected).casefold()


def _model_is_reproducible(item: DemonstrationDescriptor, root: Path) -> bool:
    """Accept a checked-in input file or an explicit deterministic benchmark generator."""
    if item.model.startswith(_GENERATED_MODEL_PREFIX):
        return item.model.removeprefix(_GENERATED_MODEL_PREFIX).upper() == item.benchmark_id
    return (root / item.model).is_file()


def _required_outputs(item: DemonstrationDescriptor) -> frozenset[str]:
    """Return evidence files required by the selected execution route."""
    if item.execution == "qualification_case":
        return _QUALIFICATION_CASE_OUTPUTS
    if item.execution == "model":
        return _MODEL_OUTPUTS
    if item.execution == "large_plan":
        return _LARGE_PLAN_OUTPUTS
    return _BENCHMARK_OUTPUTS


def _runner_is_callable(path: str) -> bool:
    """Resolve a dotted runner path without executing the benchmark."""
    parts = path.split(".")
    for split in range(len(parts) - 1, 0, -1):
        try:
            value: object = importlib.import_module(".".join(parts[:split]))
        except ImportError:
            continue
        try:
            for name in parts[split:]:
                value = getattr(value, name)
        except AttributeError:
            return False
        return callable(value)
    return False


def _qualification_case_ids(root: Path) -> set[str]:
    """Read the controlled single-case identifiers without running the campaign."""
    try:
        payload = json.loads((root / "qualification" / "campaign.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    records = payload.get("cases", []) if isinstance(payload, dict) else []
    return {str(item.get("id")).upper() for item in records if isinstance(item, dict) and item.get("id")}


def _requirement_ids(root: Path) -> set[str]:
    """Load requirement identifiers only; full traceability stays in its own registry."""
    try:
        payload = json.loads((root / "qualification" / "requirements.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    records = payload.get("requirements", []) if isinstance(payload, dict) else []
    return {str(item.get("id")) for item in records if isinstance(item, dict) and item.get("id")}


def _reference_ids(root: Path) -> set[str]:
    """Extract stable bibliography identifiers from the controlled reference page."""
    try:
        text = (root / "docs" / "reference" / "references.md").read_text(encoding="utf-8")
    except OSError:
        return set()
    return set(re.findall(r"REF-[A-Z0-9-]+", text))


def _descriptor(value: Any, index: int) -> DemonstrationDescriptor:
    if not isinstance(value, dict):
        raise InputValidationError(f"Demonstration record {index} must be an object.")
    required = {"demo_id", "benchmark_id", "title", "family", "method", "maturity", "model",
                "runner", "documentation", "tests", "requirements", "references", "outputs", "limitations"}
    missing = sorted(required - value.keys())
    if missing:
        raise InputValidationError(f"Demonstration record {index} misses fields {missing}.")
    sequences = {name: value[name] for name in ("tests", "requirements", "references", "outputs", "limitations")}
    if any(not isinstance(items, list) or not items for items in sequences.values()):
        raise InputValidationError(f"Demonstration {value.get('demo_id')!r} requires non-empty traceability lists.")
    maturity = str(value["maturity"])
    if maturity not in {"stable", "stable_after_reinforced_tests", "experimental", "research"}:
        raise InputValidationError(f"Demonstration {value.get('demo_id')!r} has unsupported maturity {maturity!r}.")
    execution = str(value.get("execution", "benchmark")).lower()
    if execution not in {"benchmark", "qualification_case", "model", "large_plan"}:
        raise InputValidationError(f"Demonstration {value.get('demo_id')!r} has unsupported execution {execution!r}.")
    case_id = str(value.get("case_id", "")).upper() or None
    if execution == "qualification_case" and case_id is None:
        raise InputValidationError(f"Demonstration {value.get('demo_id')!r} requires a qualification case id.")
    return DemonstrationDescriptor(
        demo_id=str(value["demo_id"]).upper(), benchmark_id=str(value["benchmark_id"]).upper(),
        title=str(value["title"]), family=str(value["family"]), method=str(value["method"]), maturity=maturity,
        model=str(value["model"]), runner=str(value["runner"]), documentation=str(value["documentation"]),
        tests=tuple(str(item) for item in sequences["tests"]),
        requirements=tuple(str(item) for item in sequences["requirements"]),
        references=tuple(str(item) for item in sequences["references"]),
        outputs=tuple(str(item) for item in sequences["outputs"]),
        limitations=tuple(str(item) for item in sequences["limitations"]),
        execution=execution,
        case_id=case_id,
    )
