from __future__ import annotations

import json
from pathlib import Path

from scripts.package_release_artifacts import package_release_artifacts
from solveur.io.evidence_verifier import EvidenceBundleVerifier


def test_release_artifact_archive_records_missing_paths_and_sanitizes_metadata(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "summary.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "runtime": {"python": {"executable": "C:/private/python.exe"}},
                "source_directory": "C:/private/work",
            }
        ),
        encoding="utf-8",
    )
    requirements = tmp_path / "requirements.json"
    requirements.write_text(
        json.dumps(
            {
                "requirements": [
                    {"id": "REQ-X", "artifacts": ["source/summary.json", "missing.json"]}
                ]
            }
        ),
        encoding="utf-8",
    )

    output = package_release_artifacts(requirements, tmp_path / "bundle")

    catalog = json.loads((output / "artifact_catalog.json").read_text(encoding="utf-8"))
    assert catalog["summary"]["archived_count"] == 1
    assert catalog["summary"]["missing_count"] == 1
    archived = output / "contents" / source.relative_to(tmp_path) / "summary.json"
    assert archived.is_file()
    assert "private/python.exe" not in archived.read_text(encoding="utf-8")
    assert EvidenceBundleVerifier().verify(output).status == "PASS"


def test_traceability_uses_only_declared_existing_alias(tmp_path: Path) -> None:
    from solveur.verification.traceability import QualificationRegistry

    existing = tmp_path / "controlled.json"
    existing.write_text("{}", encoding="utf-8")
    requirements = tmp_path / "requirements.json"
    requirements.write_text(
        json.dumps(
            {
                "artifact_aliases": {"aliases": {"historical.json": "controlled.json"}},
                "scopes": {"candidate": {"status": "candidate", "requirements": ["REQ-X"]}},
                "requirements": [
                    {
                        "id": "REQ-X",
                        "design": ["README.md"],
                        "code": ["src/solveur/core/solver.py"],
                        "functions": ["LinearStaticSolver.solve"],
                        "tests": ["tests/unit/test_solver.py"],
                        "artifacts": ["historical.json"],
                        "independent_references": ["closed form"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    report = QualificationRegistry(requirements).readiness("candidate")
    assert report.missing_paths == ()
    assert report.artifact_aliases_used == ("historical.json->controlled.json",)
