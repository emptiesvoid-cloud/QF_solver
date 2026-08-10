"""Opt-in Docker execution for the saturated sliding external correlation."""

import os

import pytest

from solveur.verification.code_aster_friction_contact import CodeAsterFrictionContactCampaign


def test_code_aster_saturated_sliding_matches_qf_solver(tmp_path) -> None:
    """The external study remains explicit about its sliding-only scope."""
    if os.environ.get("QF_SOLVER_RUN_EXTERNAL") != "1":
        pytest.skip("Set QF_SOLVER_RUN_EXTERNAL=1 to execute the pinned Docker oracle.")
    summary = CodeAsterFrictionContactCampaign(tmp_path).run()

    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert summary["cases"][0]["qf_state"] == "slip"
    assert (tmp_path / "code_aster_friction_comparison.png").stat().st_size > 10_000
    assert (tmp_path / "slip" / "code_aster_stdout.log").is_file()
    assert (tmp_path / "vnv_manifest.json").is_file()
