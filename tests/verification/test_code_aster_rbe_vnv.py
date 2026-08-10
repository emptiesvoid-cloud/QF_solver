"""Opt-in Docker execution for the RBE2 Code_Aster correlation."""

import os

import pytest

from solveur.verification.code_aster_rbe import CodeAsterRbe2Campaign


def test_code_aster_rbe2_matches_qf_solver(tmp_path) -> None:
    if os.environ.get("QF_SOLVER_RUN_EXTERNAL") != "1":
        pytest.skip("Set QF_SOLVER_RUN_EXTERNAL=1 to execute the pinned Docker oracle.")
    summary = CodeAsterRbe2Campaign(tmp_path).run()
    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
