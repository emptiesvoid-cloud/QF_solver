"""Contract tests for the interior TET10 stress probe."""

from __future__ import annotations

import numpy as np

from solveur.verification.code_aster_tet10_block_dynamic import (
    CodeAsterTet10BlockDynamicsCampaign,
)
from solveur.verification.code_aster_tet10_stress_probe import (
    CodeAsterTet10CantileverStressProbeCampaign,
    CodeAsterTet10CylinderStressProbeCampaign,
    CodeAsterTet10StressProbeCampaign,
    _stress_comm,
)


def test_stress_probe_excludes_singular_boundaries(tmp_path) -> None:
    campaign = CodeAsterTet10StressProbeCampaign(tmp_path)
    campaign.mesh_size = 0.80
    block = CodeAsterTet10BlockDynamicsCampaign(tmp_path, mesh_size=0.80)
    model, _, _ = block._model(0.80, "linear_static", total_load=-1.0)
    selected = campaign._select_probes(model)
    assert len(selected) >= 3
    centers = [model.nodes[list(model.elements[index].nodes)].mean(axis=0) for index in selected]
    assert all(0.20 <= float(value) <= 0.80 for center in centers for value in center)


def test_stress_deck_requests_sief_elga_on_probe_group() -> None:
    deck = _stress_comm(
        tip=np.array([2, 5]),
        weights=np.array([0.25, 0.75]),
    )
    assert 'getField("SIEF_ELGA", order)' in deck
    assert 'getValuesWithDescription(name, ["PROBE"])' in deck
    assert 'FZ=-0.25' in deck and 'FZ=-0.75' in deck


def test_cantilever_stress_probe_uses_a_distinct_geometry(tmp_path) -> None:
    campaign = CodeAsterTet10CantileverStressProbeCampaign(tmp_path)
    source = campaign._build_campaign()
    assert campaign.study_id.endswith("-027")
    assert source.length == 4.0
    assert source.width == 0.4


def test_cylinder_stress_probe_uses_curved_mesh_campaign(tmp_path) -> None:
    campaign = CodeAsterTet10CylinderStressProbeCampaign(tmp_path)
    source = campaign._build_campaign()
    assert campaign.study_id.endswith("-028")
    assert source.geometry_label == "circular-shaft cantilever"
