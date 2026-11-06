"""Synthetic reporting checks: no element assembly or mechanical solve."""

from types import SimpleNamespace

import pytest

from solveur.core.errors import ModalResidualValidationError
from solveur.verification import hex20


@pytest.mark.parametrize("validation_status", ["INCONCLUSIVE", "FAIL"])
def test_modal_certification_refusal_remains_a_global_failure(monkeypatch, validation_status):
    def fake_solve(analysis):
        if isinstance(analysis, dict) and analysis.get("type") == "modal":
            raise ModalResidualValidationError(
                "synthetic refusal", validation_status=validation_status,
                diagnostics={"reason": "synthetic_reason"},
            )
        return SimpleNamespace(status="PASS", solver={})

    monkeypatch.setattr(hex20, "_model", lambda analysis: analysis)
    monkeypatch.setattr(hex20, "solve_model", fake_solve)
    monkeypatch.setattr(hex20.Hex20MechanicalVerifier, "run", lambda self: {"status": "PASS"})
    monkeypatch.setattr(hex20.Hex20InternalCampaign, "_load_checks", lambda self: {"status": "PASS"})
    monkeypatch.setattr(hex20.Hex20InternalCampaign, "_j2_case", lambda self: {"status": "PASS"})
    monkeypatch.setattr(hex20, "run_hex20_multi_model_benchmark", lambda output: {"status": "PASS_INTERNAL", "rows": []})

    result = hex20.Hex20InternalCampaign().run()
    assert result["status"] == "FAIL"
    assert result["modal_certification"] == validation_status
    rows = {row["id"]: row for row in result["common_analysis_paths"]}
    assert rows["modal"]["status"] == "FAIL"
    assert rows["modal"]["modal_validation_reason"] == "synthetic_reason"
    assert all(rows[name]["status"] == "PASS" for name in ("static", "newmark", "harmonic"))


def test_fully_passing_synthetic_campaign_retains_pass_internal(monkeypatch):
    monkeypatch.setattr(hex20, "_model", lambda analysis: analysis)
    monkeypatch.setattr(
        hex20, "solve_model",
        lambda analysis: SimpleNamespace(status="PASS", solver={"modal_residual_validation": {"status": "PASS_CERTIFIED"}}),
    )
    monkeypatch.setattr(hex20.Hex20MechanicalVerifier, "run", lambda self: {"status": "PASS"})
    monkeypatch.setattr(hex20.Hex20InternalCampaign, "_load_checks", lambda self: {"status": "PASS"})
    monkeypatch.setattr(hex20.Hex20InternalCampaign, "_j2_case", lambda self: {"status": "PASS"})
    monkeypatch.setattr(hex20, "run_hex20_multi_model_benchmark", lambda output: {"status": "PASS_INTERNAL", "rows": []})

    result = hex20.Hex20InternalCampaign().run()
    assert result["status"] == "PASS_INTERNAL"
    assert result["modal_certification"] == "PASS_CERTIFIED"
    assert "Certification modale : **PASS_CERTIFIED**" in hex20.Hex20InternalCampaign._markdown(result)


@pytest.mark.parametrize(
    ("solver_status", "validation_status"),
    [("PASS", "INCONCLUSIVE"), ("PASS", "FAIL"), ("PASS", "NOT_REPORTED"), ("INCONCLUSIVE", "PASS_CERTIFIED")],
)
def test_modal_result_is_not_promoted_without_a_certified_passing_status(monkeypatch, solver_status, validation_status):
    def fake_solve(analysis):
        if isinstance(analysis, dict) and analysis.get("type") == "modal":
            solver = {} if validation_status == "NOT_REPORTED" else {
                "modal_residual_validation": {"status": validation_status, "reason": "synthetic_reason"}
            }
            return SimpleNamespace(status=solver_status, solver=solver)
        return SimpleNamespace(status="PASS", solver={})

    monkeypatch.setattr(hex20, "_model", lambda analysis: analysis)
    monkeypatch.setattr(hex20, "solve_model", fake_solve)
    monkeypatch.setattr(hex20.Hex20MechanicalVerifier, "run", lambda self: {"status": "PASS"})
    monkeypatch.setattr(hex20.Hex20InternalCampaign, "_load_checks", lambda self: {"status": "PASS"})
    monkeypatch.setattr(hex20.Hex20InternalCampaign, "_j2_case", lambda self: {"status": "PASS"})
    monkeypatch.setattr(hex20, "run_hex20_multi_model_benchmark", lambda output: {"status": "PASS_INTERNAL"})

    result = hex20.Hex20InternalCampaign().run()
    assert result["status"] == "FAIL"
    assert result["modal_certification"] == validation_status
    row = next(row for row in result["common_analysis_paths"] if row["id"] == "modal")
    assert row["status"] == "FAIL"
    if validation_status != "NOT_REPORTED":
        assert row["modal_validation_reason"] == "synthetic_reason"


def test_legacy_summary_without_modal_certification_remains_renderable():
    summary = {
        "study_id": "synthetic-legacy-summary",
        "status": "FAIL",
        "kernel_verification": {"status": "PASS"},
        "load_cases": {"status": "PASS"},
        "j2_case": {"status": "PASS"},
        "tet_hex20_benchmark": {"status": "PASS_INTERNAL", "rows": []},
        "common_analysis_paths": [{"id": "modal", "status": "FAIL"}],
        "external_correlation": {"status": "OPEN"},
    }

    rendered = hex20.Hex20InternalCampaign._markdown(summary)

    assert "# synthetic-legacy-summary" in rendered
    assert "| modal | FAIL |" in rendered
    assert "Certification modale :" not in rendered
