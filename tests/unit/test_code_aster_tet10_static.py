"""Contract tests for the static TET10/TETRA10 external deck."""

from __future__ import annotations

import json

from solveur.verification.code_aster_tet10_static import CodeAsterTet10StaticCampaign, _static_comm


def test_tet10_static_deck_uses_3d_tetra10_and_all_load_components() -> None:
    deck = _static_comm(
        70.0e9,
        0.3,
        [
            {"node": 1, "dof": "UX", "value": 2.0},
            {"node": 2, "dof": "UY", "value": -3.0},
            {"node": 3, "dof": "UZ", "value": -4.0},
        ],
        [],
    )
    assert 'MODELISATION="3D"' in deck
    assert "MECA_STATIQUE" in deck
    assert 'GROUP_NO="ROOT"' in deck
    assert 'FX=2' in deck
    assert 'FY=-3' in deck
    assert 'FZ=-4' in deck


def test_tet10_static_campaign_records_tet4_higher_order_reference_gap(tmp_path) -> None:
    source = tmp_path / "tet4.json"
    source.write_text(
        json.dumps({"rows": [{"tet4_elements": 12, "tet4_tip_uz_m": -1.0}]}),
        encoding="utf-8",
    )
    campaign = CodeAsterTet10StaticCampaign(
        tmp_path / "tet10.json",
        tmp_path / "out",
        tet4_summary_path=source,
        publish_reference=False,
    )
    comparison = campaign._tet4_reference(12, -2.0, -2.0)

    assert comparison is not None
    assert comparison["qf_tet4_to_code_aster_tetra10_difference"] == 0.5
