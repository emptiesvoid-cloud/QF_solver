from __future__ import annotations

import numpy as np

from solveur.verification.code_aster_mitc3 import (
    _qf_model,
    code_aster_static_comm,
    code_aster_triangle_mesh,
)


def test_mitc3_code_aster_deck_preserves_triangle_mesh_and_groups() -> None:
    model, triangles, root, tip = _qf_model(4, 2, dof="UZ", total_load=-1.0)
    text = code_aster_triangle_mesh(model.nodes, triangles, root, tip)

    assert "TRIA3" in text
    assert "GROUP_MA\nSHELL" in text
    assert "GROUP_NO\nROOT" in text
    assert "GROUP_NO\nTIP" in text
    assert text.count("\nM") >= len(triangles)


def test_mitc3_code_aster_command_uses_dkt_and_preserves_total_load() -> None:
    text = code_aster_static_comm("UZ", -12.0, 3)
    assert 'MODELISATION="DKT"' in text
    assert "FZ=-4" in text
    assert 'getValuesWithDescription("DZ", ["TIP"])' in text


def test_mitc3_external_qf_model_has_exact_nodal_resultant() -> None:
    model, _, _, tip = _qf_model(4, 2, dof="UX", total_load=900.0)
    assert len(tip) == 3
    assert np.sum([load.value for load in model.loads]) == 900.0
