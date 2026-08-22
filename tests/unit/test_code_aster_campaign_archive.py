from __future__ import annotations

import json
from pathlib import Path

from scripts.archive_code_aster_campaign import build_catalog


def test_catalog_records_missing_and_completed_studies(tmp_path: Path) -> None:
    input_dir = tmp_path / "tmp" / "code_aster"
    complete = input_dir / "complete"
    complete.mkdir(parents=True)
    (complete / "summary.json").write_text(
        json.dumps(
            {
                "study_id": "EXAMPLE-001",
                "status": "PASS_EXTERNAL_CORRELATION",
                "maturity": "experimental",
                "external_solver": {"name": "Code_Aster"},
            }
        ),
        encoding="utf-8",
    )
    (complete / "report.md").write_text("report", encoding="utf-8")
    (input_dir / "missing").mkdir()

    # The helper uses the repository root for relative paths; only the
    # discovery contract is asserted here, while integration covers the CLI.
    catalog = build_catalog(input_dir, tmp_path / "catalog.json")

    assert catalog["summary"]["study_count"] == 2
    assert catalog["summary"]["pass_external_correlation"] == 1
    assert catalog["summary"]["failure"] == 0
    assert catalog["summary"]["unavailable"] == 1
    assert "executable" not in catalog["runtime"]["python"]
    assert "processor" not in catalog["runtime"]["platform"]
    assert str(tmp_path) not in json.dumps(catalog)
    records = {record["directory"]: record for record in catalog["studies"]}
    complete_record = next(key for key in records if key.endswith("complete"))
    missing_record = next(key for key in records if key.endswith("missing"))
    assert records[complete_record]["status"] == "PASS_EXTERNAL_CORRELATION"
    assert records[missing_record]["missing"] == ["summary.json"]


def test_catalog_can_exclude_diagnostic_directories(tmp_path: Path) -> None:
    input_dir = tmp_path / "tmp" / "code_aster"
    (input_dir / "official").mkdir(parents=True)
    (input_dir / "probe").mkdir(parents=True)

    catalog = build_catalog(
        input_dir,
        tmp_path / "catalog.json",
        excluded_directories={"probe"},
    )

    assert catalog["summary"]["study_count"] == 1
    assert catalog["summary"]["excluded_directories"] == ["probe"]
