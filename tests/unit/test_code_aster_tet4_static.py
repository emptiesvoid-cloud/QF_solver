from __future__ import annotations

import numpy as np

from solveur.verification.code_aster_tet4_static import CodeAsterTet4StaticCampaign, _static_comm


def test_tet4_static_campaign_contract() -> None:
    campaign = CodeAsterTet4StaticCampaign("unused")
    assert campaign.study_id == "VNV-TET4-STATIC-CODEASTER-TETRA4-021"
    assert campaign.relative_limit == 0.01
    assert campaign.mesh_sizes == (0.95, 0.60, 0.42, 0.30)
    assert campaign.publish_reference is True


def test_tet4_static_code_aster_deck_is_same_mesh_static() -> None:
    deck = _static_comm(70.0e9, 0.3, -1.0, np.array([0, 1, 2]), np.array([0.25, 0.5, 0.25]))
    assert 'MODELISATION="3D"' in deck
    assert "MECA_STATIQUE" in deck
    assert 'GROUP_NO="ROOT"' in deck
    assert 'NOEUD="N2"' in deck
    assert 'NOEUD="N3"' in deck
    assert 'MODELISATION="DST"' not in deck
