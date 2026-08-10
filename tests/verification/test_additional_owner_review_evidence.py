from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_controlled_additional_contact_models_pass() -> None:
    path = ROOT / "qualification" / "external_reference_digests" / "contact_additional_models.json"
    summary = json.loads(path.read_text(encoding="utf-8"))

    assert summary["campaign_id"] == "VNV-CONTACT-ADDITIONAL-MODELS-008"
    assert summary["status"] == "PASS_INTERNAL"
    assert len(summary["cases"]) == 3
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert len(summary["evidence_manifest_sha256"]) == 64


def test_controlled_code_aster_contact_curves_pass_after_refinement() -> None:
    path = (
        ROOT
        / "qualification"
        / "external_reference_digests"
        / "contact_code_aster_additional.json"
    )
    summary = json.loads(path.read_text(encoding="utf-8"))

    assert summary["study_id"] == "VNV-CONTACT-CODEASTER-ADDITIONAL-009"
    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert len(summary["cases"]) == 3
    statuses = {check["status"] for check in summary["checks"]}
    assert statuses == {"PASS"}
    assert summary["cases"][2]["diagnostics"]["qf_calculix_precontact_error"] < 1.0e-5
    assert summary["cases"][2]["elements"] == 768
    assert summary["cases"][2]["displacement_curve_error"] < 0.05
    assert len(summary["evidence_manifest_sha256"]) == 64


def test_controlled_ten_thousand_element_contact_confirmation_passes() -> None:
    path = (
        ROOT
        / "qualification"
        / "external_reference_digests"
        / "contact_code_aster_additional_h10k.json"
    )
    summary = json.loads(path.read_text(encoding="utf-8"))

    assert summary["study_id"] == "VNV-CONTACT-CODEASTER-ADDITIONAL-H10K-010"
    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert len(summary["cases"]) == 3
    tet4_case = summary["cases"][2]
    assert tet4_case["elements"] == 9984
    assert tet4_case["nodes"] == 2190
    assert tet4_case["displacement_curve_error"] < 1.0e-10
    assert tet4_case["diagnostics"]["calculix_precontact_probe"] == "not_applicable"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert len(summary["evidence_manifest_sha256"]) == 64


def test_controlled_additional_orthotropic_stress_cases_pass() -> None:
    path = ROOT / "qualification" / "external_reference_digests" / "orthotropic_additional_stress.json"
    summary = json.loads(path.read_text(encoding="utf-8"))

    assert summary["campaign_id"] == "VNV-ORTHOTROPIC-ADDITIONAL-STRESS-006"
    assert summary["status"] == "PASS_STRESS_ACCEPTANCE"
    assert len(summary["cases"]) == 2
    assert all(case["assessment"]["status"] == "PASS" for case in summary["cases"])
    assert all(case["same_mesh_code_aster_status"] == "PASS" for case in summary["cases"])
    assert len(summary["evidence_manifest_sha256"]) == 64
