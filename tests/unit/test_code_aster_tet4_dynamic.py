"""Contract tests for the structural TET4 Code_Aster dynamic deck."""

from __future__ import annotations

import numpy as np

from solveur.api import solve_model
from solveur.verification.code_aster_tet10_dynamic import _modal_analysis, _pulse_table
from solveur.verification.code_aster_tet4_dynamic import CodeAsterTet4DynamicsCampaign


def test_tet4_dynamic_mesh_and_deck_use_linear_tetrahedra(tmp_path) -> None:
    campaign = CodeAsterTet4DynamicsCampaign(tmp_path, mesh_size=0.80)
    model, root, tip = campaign._model(0.80, _modal_analysis())
    mesh = campaign._code_aster_mesh(model.nodes, model.elements, root, tip)
    deck = campaign._code_aster_comm(tip, _pulse_table(0.001, 8), [1.0, 2.0])

    assert set(element.type for element in model.elements) == {"TET4"}
    assert all(len(element.nodes) == 4 for element in model.elements)
    assert "TETRA4" in mesh
    assert "GROUP_NO\nROOT" in mesh and "GROUP_NO\nTIP" in mesh
    assert 'MODELISATION="3D"' in deck
    assert "CALC_MODES" in deck and 'TYPE_CALCUL="HARM"' in deck


def test_tet4_dynamic_qf_modal_model_is_structural_and_finite(tmp_path) -> None:
    campaign = CodeAsterTet4DynamicsCampaign(tmp_path, mesh_size=0.80)
    model, root, tip = campaign._model(0.80, _modal_analysis())
    result = solve_model(model, enforce_policy=False)

    assert model.node_count > 20
    assert len(model.elements) > 20
    assert len(root) > 3 and len(tip) > 3
    assert np.all(np.isfinite(result.frequencies_hz))
    assert result.frequencies_hz[0] > 0.0
