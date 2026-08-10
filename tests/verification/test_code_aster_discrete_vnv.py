"""Opt-in Docker execution for the discrete Code_Aster correlation."""

import os

import pytest

from solveur.verification.code_aster_discrete import CodeAsterDiscreteCampaign


def test_code_aster_discrete_matches_qf_solver(tmp_path) -> None:
    if os.environ.get("QF_SOLVER_RUN_EXTERNAL") != "1":
        pytest.skip("Set QF_SOLVER_RUN_EXTERNAL=1 to execute the pinned Docker oracle.")
    summary = CodeAsterDiscreteCampaign(tmp_path).run()
    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
