from __future__ import annotations

import pytest
import numpy as np

from solveur.verification.code_aster_tet4_thick_dynamic import CodeAsterTet4ThickDynamicsCampaign


def test_second_tet4_dynamic_geometry_is_distinct(tmp_path) -> None:
    campaign = CodeAsterTet4ThickDynamicsCampaign(tmp_path, mesh_size=0.80)

    assert campaign.length == 2.4
    assert campaign.width == 0.8
    assert campaign.height == 0.6

    model, root, tip = campaign._model(0.80, "modal")

    assert model.node_count > 0
    assert root.size > 0
    assert tip.size > 0
    assert np.allclose(model.nodes[root, 0], 0.0)
    assert np.allclose(model.nodes[tip, 0], campaign.length)

pytestmark = pytest.mark.evidence
