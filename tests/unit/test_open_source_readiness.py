"""Contracts that keep the future public release honest and complete."""

from __future__ import annotations

import tomllib
from pathlib import Path

import solveur
from solveur.version import __version__

ROOT = Path(__file__).resolve().parents[2]


def test_publication_governance_files_and_package_urls_exist() -> None:
    for filename in (
        "OPEN_SOURCE_READINESS.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "SUPPORT.md",
        "CITATION.cff",
        ".github/pull_request_template.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/mechanical_vnv.yml",
    ):
        assert (ROOT / filename).is_file(), filename

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["name"] == "qf-solver"
    assert project["license"] == "Apache-2.0"
    assert "LICENSE" in project["license-files"]
    assert (ROOT / "LICENSE").is_file()
    assert (ROOT / "LICENSE-DOCS").is_file()
    assert project["urls"]["Source"].endswith("/Solveur")
    assert solveur.__version__ == __version__ == project["version"]


def test_open_source_documents_do_not_claim_a_license_that_does_not_exist() -> None:
    readiness = (ROOT / "OPEN_SOURCE_READINESS.md").read_text(encoding="utf-8")
    public_doc = (ROOT / "docs" / "reference" / "open_source.md").read_text(encoding="utf-8")
    assert "Apache-2.0" in readiness
    assert "Apache-2.0" in public_doc
    assert "CC BY 4.0" in public_doc
