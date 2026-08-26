from __future__ import annotations

import pytest
import json
from pathlib import Path

from solveur.api import run_release_vv
from solveur.verification.release_vv import ReleaseVvRunner


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = PROJECT_ROOT / "qualification" / "release_vv_0_2_1.json"


def test_release_vv_pack_keeps_required_scopes_and_baseline(tmp_path: Path) -> None:
    summary = run_release_vv(tmp_path / "release")

    assert summary["release"]["version"] == "0.2.5a0"
    assert summary["baseline"]["tag"] == "v0.2.0-alpha"
    assert summary["baseline"]["commit"] == "1804a03aee0c4e4bc6ac2c56e9461bedd9aac6d4"
    assert summary["status"] == "FAIL"
    required = {row["id"]: row for row in summary["scopes"] if row["required"]}
    assert "tet4-linear-static" in required
    assert len(required) >= 10
    assert all(row["status"] == "PASS" for row in required.values())
    assert (tmp_path / "release" / "release_vv_summary.json").is_file()
    assert (tmp_path / "release" / "release_vv_summary.md").is_file()
    assert (tmp_path / "release" / "release_vv_manifest.json").is_file()


def test_release_vv_report_does_not_publish_machine_paths(tmp_path: Path) -> None:
    summary = run_release_vv(tmp_path / "release")
    encoded = json.dumps(summary, ensure_ascii=True)

    assert str(Path.cwd()) not in encoded
    assert "executable" not in summary["provenance"]["runtime"]["python"]
    assert "processor" not in summary["provenance"]["runtime"]["platform"]
    assert all(isinstance(value, bool) for value in summary["provenance"]["runtime"]["parallel_environment"].values())


def test_release_vv_fail_on_required_scope_readiness(tmp_path: Path) -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    registry["scopes"][0]["id"] = "material-nonlinear"
    custom = tmp_path / "release_registry.json"
    custom.write_text(json.dumps(registry), encoding="utf-8")

    summary = ReleaseVvRunner(custom).run(tmp_path / "release")

    assert summary["status"] == "FAIL"
    assert any(check["id"] == "SCOPE-material-nonlinear" and check["status"] == "FAIL" for check in summary["checks"])


def test_release_vv_excludes_declared_nonstable_matrix_rows(tmp_path: Path) -> None:
    summary = run_release_vv(tmp_path / "release")

    scope_ids = {row["id"] for row in summary["scopes"]}
    assert "tet4-linear-static" in scope_ids
    assert "mitc3-laminate-static-curved" not in scope_ids
    assert "tet4-total-lagrangian-structural-v2" not in scope_ids
    assert "material-nonlinear" not in scope_ids
    assert "tet4-nonlinear-dynamic" not in scope_ids
    assert "mitc4-geometric-nonlinear-static" not in scope_ids


def test_release_vv_uses_exact_element_analysis_evidence(tmp_path: Path) -> None:
    summary = run_release_vv(tmp_path / "release")

    static = next(row for row in summary["scopes"] if row["id"] == "tet4-linear-static")
    dynamic = next(row for row in summary["scopes"] if row["id"] == "tet4-transient-dynamic")
    assert static["proof"]["evidence_origin"] == "technical_content_coverage"
    assert dynamic["proof"]["evidence_origin"] == "technical_content_coverage"
    assert static["proof"]["evidence"] != dynamic["proof"]["evidence"]


def test_release_vv_accepts_current_campaign_contract(tmp_path: Path) -> None:
    summary = run_release_vv(tmp_path / "release", execute_campaign=True)

    assert summary["campaign"]["diagnostic"] == "all_campaign_cases_accepted"
    assert summary["campaign"]["numerical_or_infrastructure_failure_count"] == 0
    assert summary["campaign"]["qualification_policy_blocked_count"] == 0


def test_release_vv_exposes_current_blocker_categories(tmp_path: Path) -> None:
    summary = run_release_vv(tmp_path / "release")

    categories = summary["blocker_summary"]
    assert categories.get("maturity_not_stable", 0) == 0
    assert categories.get("evidence_missing", 0) == 0
    assert categories["campaign_not_green"] == 1
    assert categories.get("owner_review_pending", 0) == 0


def test_release_vv_verifies_internal_linear_dynamics_bundle(tmp_path: Path) -> None:
    summary = run_release_vv(tmp_path / "release")

    check = next(
        item
        for item in summary["checks"]
        if item["id"] == "EVIDENCE-BUNDLE-INTERNAL-LINEAR-DYNAMICS-2026-08-14"
    )
    assert check["status"] == "PASS"
    assert check["checked_file_count"] == 11

pytestmark = pytest.mark.evidence
