from pathlib import Path

from solveur.api import inspect_model, save_audit_markdown
from solveur.core.audit_checks import build_audit_checks
from solveur.io.audit_markdown import AuditMarkdownWriter
from solveur.mesh.validation import MeshReport
from tests.unit.test_mesh_validation import valid_tet4_model


def test_audit_detail_levels_are_additive_and_values_stays_exhaustive():
    model = valid_tet4_model()
    summary = inspect_model(model, detail="summary").to_dict()
    diagnostic = inspect_model(model, detail="diagnostic").to_dict()
    values = inspect_model(model, detail="values").to_dict()

    assert summary["detail"] == "summary"
    assert summary["element_audits"] == []
    assert diagnostic["detail"] == "diagnostic"
    assert diagnostic["element_audits"] == []
    assert diagnostic["diagnostic"]["element_quality"]["TET4"]["count"] == 1
    assert values["detail"] == "values"
    assert values["element_audits"][0]["local_dofs"]
    assert values["element_audits"][0]["assembly_entries"]
    assert "values" in values["element_audits"][0]["matrices"][0]

    warned = inspect_model(model, detail="values", values_warning_rows=0).to_dict()
    assert "export_size_warning" in warned["diagnostic"]
    assert any("detail='values'" in note for note in warned["notes"])


def test_markdown_keeps_warnings_and_failures_when_pass_rows_are_limited(tmp_path: Path):
    data = {
        "detail": "values",
        "analysis": "linear_static",
        "checks": [
            {"status": "PASS", "name": "pass:one", "value": 0, "limit": 1, "message": "ok"},
            {"status": "WARNING", "name": "warning:balance", "value": 2e-10, "limit": 1e-10, "message": "warn"},
            {"status": "FAIL", "name": "fail:finite", "value": False, "limit": True, "message": "bad"},
        ],
    }
    text = AuditMarkdownWriter(values_warning_rows=0).render(
        data,
        detail="values",
        max_pass_rows=0,
    )
    assert "warning:balance" in text
    assert "fail:finite" in text
    assert "max_pass_rows=0" in text
    summary_text = AuditMarkdownWriter().render(data, detail="summary")
    assert "pass:one" not in summary_text
    assert "warning:balance" in summary_text
    assert "fail:finite" in summary_text

    data["post_results"] = [
        {
            "element": 7,
            "type": "TET4",
            "calculation_displacement": [float("nan")],
        }
    ]
    post_text = AuditMarkdownWriter().render(data, detail="values", max_pass_rows=0)
    assert "| 7 | TET4 |" in post_text


def test_public_markdown_warning_threshold_is_configurable(tmp_path: Path):
    path = tmp_path / "audit.md"
    audit = inspect_model(valid_tet4_model(), detail="values")
    save_audit_markdown(audit, path, detail="values", values_warning_rows=0)
    text = path.read_text(encoding="utf-8")
    assert "seuil d'alerte" in text
    assert "O(N elements x controles)" in text


def test_equilibrium_thresholds_remain_relative_and_warn_at_observed_scale():
    checks = build_audit_checks(
        analysis="linear_static",
        report=MeshReport(status="PASS"),
        boundary={},
        matrices=[],
        elements=[],
        equilibrium={
            "force_balance_relative_error": 1.771174e-10,
            "moment_balance_relative_error": 1.211158e-10,
        },
    )
    statuses = {check.name: check.status for check in checks}
    assert statuses["equilibrium:global_force_balance"] == "WARNING"
    assert statuses["equilibrium:global_moment_balance"] == "WARNING"
