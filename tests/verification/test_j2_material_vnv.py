import json

import pytest

from solveur.verification.j2_material import J2MaterialVerificationCampaign


def test_j2_material_campaign_passes_all_acceptance_checks(tmp_path):
    summary = J2MaterialVerificationCampaign(tmp_path).run()

    assert summary["status"] == "PASS_INTERNAL"
    assert len(summary["checks"]) >= 23
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert summary["maturity"] == "experimental"


def test_j2_material_campaign_writes_auditable_json_and_markdown(tmp_path):
    summary = J2MaterialVerificationCampaign(tmp_path).run()
    stored = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    report = (tmp_path / "report.md").read_text(encoding="utf-8")

    assert stored == summary
    assert summary["campaign_id"] in report
    assert "PASS_INTERNAL" in report
    assert "$" not in report
    assert "Revue independante : non realisee" in report
    assert (tmp_path / "uniaxial_comparison.png").stat().st_size > 10_000


def test_j2_cycle_contains_loading_unloading_and_reloading(tmp_path):
    summary = J2MaterialVerificationCampaign(tmp_path).run()
    path = summary["paths"]["isotropic_hardening_cycle"]
    equivalent_plastic_strain = [row["equivalent_plastic_strain"] for row in path]

    assert any(not row["elastic"] for row in path)
    assert path[5]["elastic"] is True
    assert path[6]["elastic"] is True
    assert equivalent_plastic_strain[6] == pytest.approx(equivalent_plastic_strain[4])
    assert equivalent_plastic_strain[-1] > equivalent_plastic_strain[4]


def test_j2_uniaxial_matches_bilinear_theory_and_published_abaqus_points(tmp_path):
    summary = J2MaterialVerificationCampaign(tmp_path).run()
    checks = {check["name"]: check for check in summary["checks"]}
    correlation = summary["external_correlations"]["abaqus_published"]

    assert checks["uniaxial bilinear analytical strain"]["status"] == "PASS"
    assert checks["Abaqus published monotonic plastic strain"]["status"] == "PASS"
    assert correlation["execution_status"] == "published_not_executed_locally"
    assert correlation["comparison_scope"] == "monotonic increments 1-4 only"
    assert correlation["excluded_points"]["increments"] == [5, 6, 7, 8, 9, 10]
