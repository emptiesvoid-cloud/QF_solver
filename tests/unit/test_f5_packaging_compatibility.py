"""F5 guards for clean-package runtime resources and public identity."""

from __future__ import annotations

import json

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib
from pathlib import Path

from solveur.version import __version__


ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = ROOT / "qualification/0_2_7/f5_packaging_compatibility_audit.json"
DOC_PATH = ROOT / "docs/verification/0_2_7/0_2_7_f5_packaging_compatibility_audit.md"


def _project() -> dict[str, object]:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def test_f5_runtime_resources_cover_release_vv_loader() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    resources = set(data["tool"]["setuptools"]["data-files"]["qualification"])
    assert {
        "qualification/element_analysis_matrix.json",
        "qualification/technical_content_coverage.json",
        "qualification/release_vv_0_2_1.json",
    } <= resources
    assert all((ROOT / path).is_file() for path in resources)


def test_f5_distribution_identity_and_entry_points_are_explicit() -> None:
    project = _project()
    assert project["name"] == "qf-solver"
    assert project["version"] == __version__
    assert project["requires-python"] == ">=3.10"
    scripts = project["scripts"]
    assert scripts["qf-solver"] == "solveur.cli.main:main"
    assert scripts["solveur-ef"] == "solveur.cli.main:legacy_main"


def test_f5_optional_solver_dependencies_do_not_become_core_dependencies() -> None:
    project = _project()
    dependencies = set(project["dependencies"])
    optional = {
        dependency.split("[", 1)[0].split("=", 1)[0].split(">", 1)[0].split("<", 1)[0]
        for group in ("large", "hpc")
        for dependency in project["optional-dependencies"][group]
    }
    assert not {"mpi4py", "petsc4py", "slepc4py"} & dependencies
    assert {"mpi4py", "petsc4py"} <= optional


def test_f5_audit_record_closes_packaging_blockers_without_release_actions() -> None:
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    assert audit["schema_version"] == 1
    assert audit["record_type"] == "f5_packaging_compatibility_audit"
    assert audit["audit_start_sha"] == "124c61f6492eee351a34e3542d198a13c00c2874"
    assert audit["summary"] == {
        "p0_found": 0,
        "p1_found": 1,
        "p2_found": 2,
        "p3_found": 1,
        "p0_fixed": 0,
        "p1_fixed": 1,
        "p2_fixed": 0,
        "p3_fixed": 0,
        "release_blockers_remaining": 0,
    }
    assert audit["controls"]["numerical_source_changed"] is False
    assert audit["controls"]["historical_evidence_modified"] is False
    assert audit["controls"]["maturity_promoted"] is False
    assert audit["controls"]["pypi_published"] is False
    assert audit["publication_readiness"]["wheel_ready"] is True
    assert audit["publication_readiness"]["sdist_ready"] is True


def test_f5_audit_and_document_are_registered() -> None:
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    assert DOC_PATH.is_file()
    for path in audit["evidence_refs"]:
        assert (ROOT / path).is_file(), path
    manifest = json.loads((ROOT / "qualification/0_2_7/manifest.json").read_text(encoding="utf-8"))
    assert manifest["f5_status"] == "PASS_WITH_LIMITATIONS"
    assert manifest["f5_packaging_audit"] == "qualification/0_2_7/f5_packaging_compatibility_audit.json"
    registry = json.loads((ROOT / "docs/document_registry.json").read_text(encoding="utf-8"))
    entries = [entry for entry in registry["documents"] if entry["id"] == "DOC-027-F5-PACKAGE-001"]
    assert len(entries) == 1
    assert entries[0]["examples"] == [
        "qualification/0_2_7/f5_packaging_compatibility_audit.json",
        "tests/unit/test_f5_packaging_compatibility.py",
    ]
