"""Contracts for the external structural TET10 J2 campaign."""

import numpy as np

from solveur.verification.code_aster_tet10_j2_structural import (
    CodeAsterTet10J2StructuralCampaign,
    _aster_commands,
    _trim_initial,
)


def test_code_aster_j2_deck_uses_tet10_material_and_tip_nodes() -> None:
    campaign = CodeAsterTet10J2StructuralCampaign("results/test")
    tip = np.asarray([3, 7, 12], dtype=int)
    deck = _aster_commands(campaign, tip, campaign.load_factors)

    assert 'MODELISATION="3D"' in deck
    assert 'RELATION="VMIS_ISOT_LINE"' in deck
    assert 'D_SIGM_EPSI=' in deck
    assert 'N4' in deck
    assert 'N8' in deck
    assert 'N13' in deck
    assert "DEFI_LIST_REEL" in deck


def test_trim_initial_removes_code_aster_zero_state() -> None:
    raw = {
        "rows": [
            {"tip_ux_m": 0.0, "equivalent_plastic_strain": 0.0},
            {"tip_ux_m": 1.0e-3, "equivalent_plastic_strain": 0.0},
            {"tip_ux_m": 2.0e-3, "equivalent_plastic_strain": 1.0e-3},
        ]
    }

    rows = _trim_initial(raw, 2)

    assert rows[0]["tip_ux_m"] == 1.0e-3
    assert rows[-1]["equivalent_plastic_strain"] == 1.0e-3
