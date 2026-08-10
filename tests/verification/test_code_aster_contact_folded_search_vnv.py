"""Opt-in Docker execution for autonomous folded-surface contact search."""

import os

import pytest

from solveur.verification.code_aster_contact_folded_search import CodeAsterFoldedSearchCampaign


def test_code_aster_autonomous_folded_search_matches_qf_patch(tmp_path) -> None:
    if os.environ.get("QF_SOLVER_RUN_EXTERNAL") != "1":
        pytest.skip("Set QF_SOLVER_RUN_EXTERNAL=1 to execute the pinned Docker oracle.")
    summary = CodeAsterFoldedSearchCampaign(tmp_path).run()
    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert summary["relative_difference"] <= 0.01
