from __future__ import annotations

import numpy as np

from solveur.verification.code_aster_tet10_cylinder_dynamic import CodeAsterTet10CylinderDynamicsCampaign


def test_circular_tet10_dynamic_geometry_preserves_quadratic_nodes(tmp_path) -> None:
    campaign = CodeAsterTet10CylinderDynamicsCampaign(tmp_path, mesh_size=0.80)
    model, root, tip = campaign._model(0.80, "modal")

    assert set(element.type for element in model.elements) == {"TET10"}
    assert all(len(element.nodes) == 10 for element in model.elements)
    assert np.allclose(model.nodes[root, 0], 0.0)
    assert np.allclose(model.nodes[tip, 0], campaign.length)

