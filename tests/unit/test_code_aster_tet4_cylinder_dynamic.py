from __future__ import annotations

import numpy as np

from solveur.verification.code_aster_tet4_cylinder_dynamic import CodeAsterTet4CylinderDynamicsCampaign


def test_circular_tet4_dynamic_geometry_has_circular_end_sections(tmp_path) -> None:
    campaign = CodeAsterTet4CylinderDynamicsCampaign(tmp_path, mesh_size=0.80)
    model, root, tip = campaign._model(0.80, "modal")

    assert model.node_count > 0
    assert root.size > 0
    assert tip.size > 0
    assert np.allclose(model.nodes[root, 0], 0.0)
    assert np.allclose(model.nodes[tip, 0], campaign.length)
    root_radius = np.linalg.norm(model.nodes[root, 1:3], axis=1)
    tip_radius = np.linalg.norm(model.nodes[tip, 1:3], axis=1)
    assert np.max(root_radius) == np.max(tip_radius)
    assert np.isclose(np.max(root_radius), 0.4, atol=1.0e-10)

