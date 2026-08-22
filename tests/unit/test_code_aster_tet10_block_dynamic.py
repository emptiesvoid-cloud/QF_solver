"""Contract tests for the non-cantilever TET10 campaign."""

from __future__ import annotations

import pytest
import numpy as np

from solveur.verification.code_aster_tet10_block_dynamic import (
    CodeAsterTet10BlockDynamicsCampaign,
)
from solveur.verification.code_aster_tet10_dynamic import _modal_analysis


def test_block_campaign_uses_bottom_and_top_faces(tmp_path) -> None:
    campaign = CodeAsterTet10BlockDynamicsCampaign(tmp_path, mesh_size=0.80)
    model, root, tip = campaign._model(0.80, _modal_analysis())
    assert {element.type for element in model.elements} == {"TET10"}
    assert np.allclose(model.nodes[root, 2], 0.0)
    assert np.allclose(model.nodes[tip, 2], 1.0)
    assert np.max(model.nodes[root, 0]) <= 1.0
    assert np.min(model.nodes[tip, 2]) == 1.0


def test_block_campaign_preserves_non_cantilever_scope() -> None:
    assert "block" in CodeAsterTet10BlockDynamicsCampaign.geometry_label
    assert CodeAsterTet10BlockDynamicsCampaign.study_id.endswith("-025")

pytestmark = pytest.mark.evidence
