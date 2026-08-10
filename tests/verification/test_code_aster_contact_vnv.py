"""Controlled external Code_Aster execution for the normal contact inequality."""

import os

import pytest

from solveur.verification.code_aster_contact import CodeAsterFrictionlessContactCampaign


def test_code_aster_unilateral_contact_matches_qf_solver(tmp_path) -> None:
    if os.environ.get("QF_SOLVER_RUN_EXTERNAL") != "1":
        pytest.skip("Set QF_SOLVER_RUN_EXTERNAL=1 to execute the pinned Docker oracle.")
    summary = CodeAsterFrictionlessContactCampaign(tmp_path).run()

    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert (tmp_path / "code_aster_contact_comparison.png").stat().st_size > 10_000
    assert (tmp_path / "compression" / "code_aster_stdout.log").is_file()
    assert (tmp_path / "vnv_manifest.json").is_file()
