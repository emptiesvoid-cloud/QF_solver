from __future__ import annotations

import numpy as np

from solveur.verification.code_aster_tet10_j2_complex import (
    CodeAsterTet4J2ComplexCampaign,
    _aster_mesh,
    _aster_commands,
)


def test_tet4_campaign_uses_tetra4_and_preserves_structural_path() -> None:
    campaign = CodeAsterTet4J2ComplexCampaign("results/test-tet4-j2")
    assert campaign.element_type == "TET4"
    assert campaign.study_id == "VNV-TET4-J2-CODEASTER-COMPLEX-027"
    deck = _aster_commands(campaign, np.array([0, 4], dtype=int))
    assert 'RELATION="VMIS_ISOT_LINE"' in deck
    mesh = _aster_mesh(
        type("Model", (), {"nodes": np.zeros((4, 3)), "elements": [type("Element", (), {"nodes": (0, 1, 2, 3)})()]})(),
        np.array([0]),
        np.array([3]),
        "TET4",
    )
    assert "TETRA4" in mesh
    assert "TETRA10" not in mesh
