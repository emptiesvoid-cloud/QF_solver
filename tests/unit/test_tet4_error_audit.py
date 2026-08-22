"""Tests for the causal TET4 error audit."""

from __future__ import annotations

import pytest
import json
from pathlib import Path

from solveur.verification.tet4_error_audit import build_tet4_error_audit, write_tet4_error_audit


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _report() -> dict:
    return build_tet4_error_audit(
        _read("qualification/maturity_evidence_0_2_1/tet4_linear_static.json"),
        _read("qualification/maturity_evidence_0_2_1/tet4_linear_dynamics.json"),
        _read("qualification/vnv/external/code_aster_tet4_static/reference/summary.json"),
        _read("qualification/vnv/tet4_tet10_corrected_reference_002/summary.json"),
    )


def test_tet4_audit_separates_static_spatial_error_from_time_step() -> None:
    report = _report()
    assert report["status"] == "PASS_DIAGNOSTIC"
    assert report["conclusion"]["primary_static_cause"] == "spatial_discretization_low_order_constant_strain"
    assert report["conclusion"]["static_time_step_cause"] is False
    assert report["conclusion"]["static_linear_solver_cause"] is False
    assert report["conclusion"]["under_one_percent_demonstrated"] is True
    assert report["conclusion"]["under_one_percent_general_tet4_proven"] is False


def test_tet4_audit_preserves_mesh_plateau_warning_and_dynamic_margin() -> None:
    report = _report()
    assert report["static"]["mesh_behavior"]["qf_final_mesh_increment"] > 0.01
    assert report["dynamic"]["external_code_aster"]["relative_errors"]["newmark_history"] < 0.01
    assert report["dynamic"]["external_code_aster"]["relative_errors"]["harmonic_response"] < 0.01
    assert any(check["id"] == "TET4-STATIC-MESH-INCREMENT" and check["status"] == "WARNING" for check in report["checks"])


def test_tet4_audit_writes_json_markdown_plot_and_manifest(tmp_path: Path) -> None:
    report = write_tet4_error_audit(
        ROOT / "qualification/maturity_evidence_0_2_1/tet4_linear_static.json",
        ROOT / "qualification/maturity_evidence_0_2_1/tet4_linear_dynamics.json",
        ROOT / "qualification/vnv/external/code_aster_tet4_static/reference/summary.json",
        ROOT / "qualification/vnv/tet4_tet10_corrected_reference_002/summary.json",
        tmp_path,
    )
    assert report["status"] == "PASS_DIAGNOSTIC"
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "report.md").is_file()
    assert (tmp_path / "tet4_error_convergence.png").stat().st_size > 1000
    assert (tmp_path / "vnv_manifest.json").is_file()

pytestmark = pytest.mark.evidence
