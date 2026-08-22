from __future__ import annotations

import json
from pathlib import Path

from scripts.package_code_aster_evidence import package_campaign
from solveur.io.evidence_verifier import EvidenceBundleVerifier
from solveur.io.manifest import write_json_file


def test_package_code_aster_evidence_keeps_controlled_files_only(tmp_path: Path) -> None:
    source = tmp_path / "campaign"
    study = source / "study_a"
    study.mkdir(parents=True)
    (study / "summary.json").write_text(
        json.dumps({"study_id": "A", "status": "PASS_EXTERNAL_CORRELATION"}),
        encoding="utf-8",
    )
    (study / "report.md").write_text("report", encoding="utf-8")
    (study / "STUDY.md").write_text("study report", encoding="utf-8")
    (study / "vnv_manifest.json").write_text("{}", encoding="utf-8")
    (study / "code_aster_raw.json").write_text("{}", encoding="utf-8")
    (study / "figure.png").write_bytes(b"PNG")
    (study / "large_mail_file.mail").write_bytes(b"do not copy")
    catalog = tmp_path / "catalog.json"
    write_json_file(
        catalog,
        {
            "catalog_id": "TEST-CATALOG",
            "summary": {"study_count": 1},
            "studies": [
                {
                    "directory": str(study),
                    "status": "PASS_EXTERNAL_CORRELATION",
                    "study_id": "A",
                }
            ],
        },
    )
    output = package_campaign(source, catalog, tmp_path / "bundle")

    assert (output / "evidence_manifest.json").is_file()
    assert (output / "studies" / "study_a" / "summary.json").is_file()
    assert (output / "studies" / "study_a" / "figure.png").is_file()
    assert (output / "studies" / "study_a" / "STUDY.md").is_file()
    assert not (output / "studies" / "study_a" / "large_mail_file.mail").exists()
    manifest = json.loads((output / "evidence_manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_schema_version"] == 2
    assert manifest["traceability"]["status"] == "READY_FOR_OWNER_REVIEW"
    assert str(tmp_path) not in json.dumps(manifest)
    assert str(tmp_path) not in (output / "README.json").read_text(encoding="utf-8")
    assert EvidenceBundleVerifier().verify(output).status == "PASS"


def test_package_code_aster_evidence_preserves_unavailable_study_record(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.json"
    write_json_file(
        catalog,
        {
            "catalog_id": "TEST-CATALOG",
            "summary": {"study_count": 1},
            "studies": [{"directory": str(tmp_path / "missing"), "status": "UNAVAILABLE"}],
        },
    )
    output = package_campaign(tmp_path, catalog, tmp_path / "bundle")

    record = output / "studies" / "missing" / "record.json"
    assert record.is_file()
    assert json.loads(record.read_text(encoding="utf-8"))["status"] == "UNAVAILABLE"
    assert EvidenceBundleVerifier().verify(output).status == "PASS"
