"""Traceability checks for the consolidated 0.2.4a0 J2 evidence digest."""

import json
from pathlib import Path

import pytest

from solveur.verification.j2_step_sensitivity import J2MeshSensitivityCampaign
from solveur.verification.rqg08_external_j2 import code_aster_mesh


def test_j2_unified_nonlinear_digest_keeps_bounded_scope() -> None:
    root = Path(__file__).resolve().parents[2]
    digest = json.loads(
        (root / "qualification" / "external_reference_digests" / "j2_unified_nonlinear_024.json").read_text(
            encoding="utf-8"
        )
    )

    assert digest["campaign_id"] == "VNV-J2-UNIFIED-NONLINEAR-024"
    assert digest["status"] == "PASS_INTERNAL_INITIAL"
    assert digest["evidence"]["V2_methods"]["modified_newton"] == "NON_CONVERGED"
    assert digest["evidence"]["V2_mesh_sensitivity"]["status"] == "PASS_INTERNAL"
    assert digest["evidence"]["V2_mesh_sensitivity"]["maximum_state_relative_sensitivity"] < 1.0e-8
    assert digest["evidence"]["V4_CalculiX"]["scope"].endswith("not an element qualification.")
    assert any("not physical validation" in limitation for limitation in digest["limitations"])


@pytest.mark.benchmark
def test_j2_mesh_sensitivity_campaign_is_reproducible(tmp_path: Path) -> None:
    summary = J2MeshSensitivityCampaign(tmp_path / "mesh").run()

    assert summary["status"] == "PASS_INTERNAL"
    assert summary["mesh_sizes"] == [0.36, 0.24, 0.18]
    assert summary["maximum_state_relative_sensitivity"] < 1.0e-8
    assert summary["maximum_step_residual"] < 1.0e-7


def test_j2_gate_status_does_not_claim_release_closure() -> None:
    root = Path(__file__).resolve().parents[2]
    status = json.loads(
        (root / "qualification" / "reviews" / "qf_solver_0_2_4a0_gate_status.json").read_text(
            encoding="utf-8"
        )
    )

    assert status["release_claim"] is False
    assert status["release_sha"] is None
    assert status["gates"]["NL-G12"] == "PARTIAL_SHA_PENDING"
    assert status["gates"]["NL-G13"] == "ACCEPTED_WITH_RECOMMENDATIONS"
    assert status["owner_decision"]["decision"] == "accepted_with_recommendations"
    assert status["gates"]["RQ-G08"] == "PASS_EXTERNAL_CORRELATION_BOUNDED"


def test_robustness_digest_is_internal_and_keeps_external_gate_open() -> None:
    root = Path(__file__).resolve().parents[2]
    digest = json.loads(
        (root / "qualification" / "external_reference_digests" / "robustness_nonlinear_solids_024.json").read_text(
            encoding="utf-8"
        )
    )

    assert digest["status"] == "PASS_INTERNAL"
    assert digest["scope"]["elements"] == ["TET4", "TET10", "HEX8", "HEX20"]
    assert digest["consistent_tangent"]["maximum_relative_error"] < 1.0e-6
    assert digest["newton_rate_study"]["status"] == "PASS_CHARACTERIZED"
    assert digest["newton_rate_study"]["modified_newton"]["HEX20"] == "NON_CONVERGED"
    assert digest["external_correlations"]["status"] == "PASS_EXTERNAL_CORRELATION_BOUNDED"
    assert digest["external_correlations"]["j2_external_correlation"]["status"] == "PASS_EXTERNAL_CORRELATION_BOUNDED"


def test_rqg08_external_j2_correlation_is_archived_and_bounded() -> None:
    root = Path(__file__).resolve().parents[2]
    digest = json.loads(
        (root / "qualification" / "external_reference_digests" / "rqg08_j2_common_024.json").read_text(
            encoding="utf-8"
        )
    )

    assert digest["campaign_id"] == "VNV-RQ-G08-J2-COMMON-024"
    assert digest["status"] == "PASS_EXTERNAL_CORRELATION_BOUNDED"
    assert digest["external_solver"]["image"].startswith("simvia/code_aster@sha256:")
    assert digest["scope"]["elements"] == ["TET4", "TET10", "HEX8", "HEX20"]
    assert digest["checks"]["total"] == 80
    assert digest["checks"]["passed"] == 80
    assert digest["checks"]["failed"] == 0
    assert digest["checks"]["maximum_relative_error"] < 5.0e-4
    assert any("not physical validation" in limitation for limitation in digest["limitations"])

    raw_summary = root / "qualification" / "vnv" / "external" / "rqg08_j2_common_024" / "reference" / "summary.json"
    if raw_summary.is_file():
        summary = json.loads(raw_summary.read_text(encoding="utf-8"))
        assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
        assert len(summary["checks"]) == digest["checks"]["total"]


def test_rqg08_hex20_mesh_uses_validated_code_aster_connectivity() -> None:
    _, _, mesh = code_aster_mesh("HEX20")
    lines = mesh.splitlines()
    start = lines.index("M1") + 1
    assert lines[start : start + 20] == [
        "N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8", "N9", "N12",
        "N14", "N10", "N11", "N13", "N15", "N16", "N17", "N19", "N20", "N18",
    ]
