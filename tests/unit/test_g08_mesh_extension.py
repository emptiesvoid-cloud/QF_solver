"""Contract checks for the supplemental G08 mesh extension harness."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.canonical_artifact_digest import canonical_artifact_sha256


ROOT = Path(__file__).resolve().parents[2]


def test_g08_mesh_extension_keeps_official_policy_and_scope() -> None:
    source = (ROOT / "scripts" / "run_g08_mesh_extension.py").read_text(encoding="utf-8")
    assert "EXTENSION_LEVELS = (16, 32)" in source
    assert "CONVERGED_BOUNDED_LIMIT = 0.01" in source
    assert "NEAR_CONVERGED_BOUNDED_LIMIT = 0.04" in source
    assert "official_policy_changed" in source
    assert "historical G08 closeout remains immutable" in source


def test_g08_mesh_extension_forces_local_source_imports() -> None:
    source = (ROOT / "scripts" / "run_g08_mesh_extension.py").read_text(encoding="utf-8")
    assert "sys.path.insert(0, str(ROOT / \"src\"))" in source
    assert "source_dirty" in source


def test_g08_mesh_extension_evidence_is_supplemental_and_consistent() -> None:
    data_path = ROOT / "qualification" / "0_2_6" / "g08_mesh_extension_evidence.json"
    report_path = ROOT / "qualification" / "0_2_6" / "g08_mesh_extension_evidence.md"
    data = json.loads(data_path.read_text(encoding="utf-8"))
    assert data["gate"] == "026-G08"
    assert data["status"] == "PASS_WITH_LIMITATIONS"
    assert data["gate_status_unchanged"] == "PASS_WITH_LIMITATIONS"
    assert data["source_dirty"] is False
    assert data["baseline_checkpoint_sha"] == "c9d5ce8d7ce456c5d3fdcc5ff43d0fcebb2c0c4c"
    assert data["case_counts"] == {
        "extension_cases_executed": 12,
        "extension_pass": 12,
        "extension_observed_limitations": 0,
        "extension_unexpected_failures": 0,
        "historical_mesh_cases_reused": 12,
    }
    families = {row["family"]: row for row in data["mesh_study"]["families"]}
    assert all(families[name]["classification"] == "CONVERGED_BOUNDED" for name in ("TET10", "HEX8", "HEX20"))
    added_rows = [row for family in families.values() for row in family["levels"][4:]]
    assert all(row["mode_quality"]["status"] == "PASS" for row in added_rows)
    assert all(row["mode_quality"]["sign_convention"] == "largest_absolute_component_positive" for row in added_rows)
    assert all(row["finite_values"] is True for row in added_rows)
    assert data["mesh_study"]["extension_stop_reason"].startswith("All three extended families")
    assert data["external_correlation"]["status"] == "BLOCKED_EXTERNAL_TOOL"
    assert data["high_order_oracle"]["status"] == "NO_COMPARABLE_ANALYTICAL_ORACLE"
    assert data["hex20_diagnosis"]["solver_or_eigensolver_modified"] is False
    assert canonical_artifact_sha256(report_path) == data["artifact_digests"]["g08_mesh_extension_evidence.md"]

    gates = json.loads((ROOT / "qualification" / "0_2_6" / "gates.json").read_text(encoding="utf-8"))
    g08 = next(row for row in gates["gates"] if row["id"] == "026-G08")
    assert g08["status"] == "PASS_WITH_LIMITATIONS"
    assert "g08_mesh_extension_evidence.json" in g08["evidence_ids"]
    assert "g08_mesh_extension_evidence.md" in g08["evidence_ids"]
