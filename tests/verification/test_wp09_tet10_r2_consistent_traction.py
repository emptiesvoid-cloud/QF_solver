from __future__ import annotations

import json

import numpy as np

from scripts.run_wp09_tet10_r2_consistent_traction import (
    CONTRACT_PATH,
    LEVELS,
    _load_metadata,
    _model,
)


def test_contract_freezes_tet10_full_3d_hierarchy() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["scope"].startswith("TET10-only")
    assert [tuple(level["cells"]) for level in contract["mesh_hierarchy"]["levels"]] == [cells for _, cells in LEVELS]
    assert contract["load_definition"]["equal_share_nodal_load"] is False


def test_tet10_meshes_have_positive_quality_and_shared_nodes() -> None:
    counts: list[tuple[int, int, int]] = []
    for _, cells in LEVELS:
        model, _ = _model(cells)
        counts.append((model.node_count, len(model.elements), model.dof_manager().ndof))
        assert model.node_count > 0
        assert len(model.elements) == 5 * cells[0] * cells[1] * cells[2]
        assert all(element.type == "TET10" for element in model.elements)
    assert counts[0][0] < counts[1][0] < counts[2][0]


def test_consistent_tet10_surface_load_preserves_resultant_and_moment() -> None:
    for _, cells in LEVELS:
        model, _ = _model(cells)
        metadata = _load_metadata(model)
        assert np.allclose(metadata["resultant"], [0.25, 0.0, 0.0], atol=1.0e-12)
        assert np.allclose(metadata["moment_about_origin"], [0.0, 0.125, -0.125], atol=1.0e-12)
        assert float(metadata["resultant_error_norm"]) <= 1.0e-12
