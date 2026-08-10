"""Contract tests for the structural TET10 Code_Aster dynamic deck."""

from __future__ import annotations

import numpy as np

from solveur.api import solve_model
from solveur.verification.code_aster_tet10_dynamic import (
    CodeAsterTet10DynamicsCampaign,
    _modal_analysis,
    _pulse_table,
    code_aster_tet10_dynamic_comm,
    code_aster_tet10_mesh,
)


def test_tet10_dynamic_mesh_preserves_quadratic_connectivity_and_node_groups(tmp_path) -> None:
    campaign = CodeAsterTet10DynamicsCampaign(tmp_path, mesh_size=0.80)
    model, root, tip = campaign._model(0.80, _modal_analysis())
    text = code_aster_tet10_mesh(model.nodes, model.elements, root, tip)

    assert set(element.type for element in model.elements) == {"TET10"}
    assert all(len(element.nodes) == 10 for element in model.elements)
    assert "TETRA10" in text
    assert "GROUP_NO\nROOT" in text
    assert "GROUP_NO\nTIP" in text


def test_tet10_dynamic_deck_uses_3d_mass_modal_newmark_and_harmonic(tmp_path) -> None:
    campaign = CodeAsterTet10DynamicsCampaign(tmp_path, mesh_size=0.80)
    _, _, tip = campaign._model(0.80, _modal_analysis())
    text = code_aster_tet10_dynamic_comm(tip, _pulse_table(0.001, 8), [1.0, 2.0])

    assert 'MODELISATION="3D"' in text
    assert 'OPTION="MASS_MECA"' in text
    assert "CALC_MODES" in text
    assert 'SCHEMA="NEWMARK", BETA=0.25, GAMMA=0.5' in text
    assert 'TYPE_CALCUL="HARM"' in text
    assert text.count('FZ=') == len(tip)


def test_tet10_dynamic_qf_modal_model_is_structural_and_finite(tmp_path) -> None:
    campaign = CodeAsterTet10DynamicsCampaign(tmp_path, mesh_size=0.80)
    model, root, tip = campaign._model(0.80, _modal_analysis())
    result = solve_model(model, enforce_policy=False)

    assert model.node_count > 100
    assert len(model.elements) > 20
    assert len(root) > 3 and len(tip) > 3
    assert np.all(np.isfinite(result.frequencies_hz))
    assert result.frequencies_hz[0] > 0.0
