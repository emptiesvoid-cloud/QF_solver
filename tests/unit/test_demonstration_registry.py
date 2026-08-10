"""Checks for the public demonstration/documentation contract."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from solveur.benchmarks import BenchmarkCatalog, DemonstrationCatalog, DemonstrationRunner


ROOT = Path(__file__).resolve().parents[2]


def test_demonstrations_are_traceable_to_existing_runners_and_documents() -> None:
    benchmarks = {item.identifier for item in BenchmarkCatalog().list()}
    demonstrations = DemonstrationCatalog().list()
    benchmark_demos = [item for item in demonstrations if item.execution == "benchmark"]
    qualification_demos = [item for item in demonstrations if item.execution == "qualification_case"]
    model_demos = [item for item in demonstrations if item.execution == "model"]
    assert {item.benchmark_id for item in benchmark_demos} == benchmarks
    assert qualification_demos
    assert {item.demo_id for item in model_demos} >= {
        "DEMO-ORTHO-TET4-STATIC-001",
        "DEMO-ORTHO-TET10-NEWMARK-001",
        "DEMO-MITC4-LAMINATE-STATIC-001",
    }
    for item in demonstrations:
        assert (ROOT / item.documentation).is_file()
        assert all((ROOT / path).is_file() for path in item.tests)
        assert item.references
        assert item.outputs
        assert item.limitations
    report = DemonstrationCatalog().validate_integrity(ROOT)
    assert report.status == "PASS", report.issues
    assert report.checked_count == len(demonstrations)


def test_demonstration_integrity_rejects_unknown_qualification_case() -> None:
    catalog = DemonstrationCatalog()
    item = catalog.get("DEMO-TET4-STATIC-QUAL-001")
    catalog._descriptors[item.demo_id] = replace(item, case_id="SOV-MISSING-001")

    report = catalog.validate_integrity(ROOT)
    assert report.status == "FAIL"
    assert any("unknown qualification case" in issue for issue in report.issues)


@pytest.mark.parametrize(
    ("attribute", "value", "message"),
    [
        ("documentation", "docs/missing.md", "missing documentation"),
        ("runner", "solveur.benchmarks.solid.missing", "missing runner"),
        ("tests", ("tests/missing.py",), "missing test"),
        ("references", ("REF-MISSING",), "unknown reference"),
        ("outputs", ("result.json",), "non-reproducible outputs"),
    ],
)
def test_demonstration_integrity_rejects_orphaned_traceability(
    attribute: str, value: object, message: str
) -> None:
    catalog = DemonstrationCatalog()
    item = catalog.get("DEMO-TET4-PATCH-001")
    catalog._descriptors[item.demo_id] = replace(item, **{attribute: value})

    report = catalog.validate_integrity(ROOT)
    assert report.status == "FAIL"
    assert any(message in issue for issue in report.issues)


def test_demonstration_filters_and_runner_registry_are_deterministic() -> None:
    catalog = DemonstrationCatalog()
    modal = catalog.list(family="TET4", method="modal+newmark+harmonic_response")
    assert [item.demo_id for item in modal] == ["DEMO-DYNAMIC-CANTILEVER-001"]
    assert DemonstrationRunner().catalog.get("demo-tet4-patch-001").benchmark_id == "BM-SOL-TET4-PATCH-001"
    qualification_case = DemonstrationRunner().catalog.get("demo-tet4-static-qual-001")
    assert qualification_case.execution == "qualification_case"
    assert qualification_case.case_id == "SOV-TET4-STATIC-001"
    model = DemonstrationRunner().catalog.get("demo-ortho-tet4-static-001")
    assert model.execution == "model"
    assert model.benchmark_id == "MODEL-ORTHO-TET4-STATIC-001"
    large = DemonstrationRunner().catalog.get("demo-large-petsc-plan-001")
    assert large.execution == "large_plan"
    assert large.model == "generated:MODEL-LARGE-PETSC-PLAN-001"


def test_demonstration_requirement_is_registered() -> None:
    payload = json.loads((ROOT / "qualification" / "requirements.json").read_text(encoding="utf-8"))
    ids = {item["id"] for item in payload["requirements"]}
    assert "REQ-DOC-001" in ids
