"""Deck-level checks for the bounded Code_Aster friction oracle."""

from __future__ import annotations

import json

from solveur.verification import code_aster_friction_contact as friction

from solveur.verification.code_aster_friction_contact import friction_contact_comm, surface_pair_mesh


def test_code_aster_friction_deck_declares_traceable_continuous_coulomb_contact() -> None:
    """The portable deck retains its distinct penalty and contact assumptions."""
    mesh = surface_pair_mesh()
    commands = friction_contact_comm(200.0)
    calibrated_commands = friction_contact_comm(50.0, 2000.0)

    assert "TRIA3" in mesh
    assert "MASTER_SURFACE" in mesh
    assert "SLAVE_SURFACE" in mesh
    assert 'FORMULATION="CONTINUE"' in commands
    assert 'FROTTEMENT="COULOMB"' in commands
    assert "COEF_PENA_CONT=1.0e8" in commands
    assert "COEF_PENA_FROT=10000" in commands
    assert "COEF_PENA_FROT=2000" in calibrated_commands
    assert "COULOMB=0.5" in commands
    assert "FX=66.66666666666667" in commands


def test_campaign_normalizes_saturated_sliding_evidence_without_docker(tmp_path, monkeypatch) -> None:
    """The campaign contract is testable without its opt-in Docker oracle."""
    values = {
        "slip": {"ux_m": 0.15, "uz_m": -0.1},
    }

    def fake_code_aster(work, stem, **_kwargs) -> None:
        (work / "code_aster_raw.json").write_text(json.dumps(values[stem]), encoding="utf-8")
        (work / "code_aster_stdout.log").write_text("controlled test", encoding="utf-8")
        (work / "code_aster_stderr.log").write_text("", encoding="utf-8")

    monkeypatch.setattr(friction, "run_code_aster", fake_code_aster)
    summary = friction.CodeAsterFrictionContactCampaign(tmp_path).run()

    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert [row["id"] for row in summary["cases"]] == ["slip"]
    assert summary["cases"][0]["qf_state"] == "slip"
    assert all(row["status"] == "PASS" for row in summary["checks"])
