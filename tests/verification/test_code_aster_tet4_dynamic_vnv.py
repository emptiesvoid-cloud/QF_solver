"""Opt-in Docker execution for the structural TET4 dynamic correlation."""

from __future__ import annotations

import os

import pytest

from solveur.verification.code_aster_tet4_dynamic import CodeAsterTet4DynamicsCampaign


def test_code_aster_tet4_dynamics_matches_qf_solver(tmp_path) -> None:
    if os.environ.get("QF_SOLVER_RUN_EXTERNAL") != "1":
        pytest.skip("Set QF_SOLVER_RUN_EXTERNAL=1 to execute the pinned Docker oracle.")
    summary = CodeAsterTet4DynamicsCampaign(tmp_path).run()
    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert all(check["status"] != "FAIL" for check in summary["checks"])
    assert (tmp_path / "comparison.png").is_file()
