"""Targeted tests for the WP09 HEX20 R2 load and mesh definition."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.run_wp09_hex20_r2_consistent_traction import _consistent_face_loads, _mesh, _model


ROOT = Path(__file__).resolve().parents[2]


def test_r2_contract_freezes_consistent_traction_and_3d_levels() -> None:
    contract = json.loads((ROOT / "qualification/0_2_9/wp09_hex20_r2_consistent_traction_contract.json").read_text())
    assert contract["load_definition"]["equal_share_nodal_load"] is False
    assert [row["cells"] for row in contract["mesh_hierarchy"]["levels"]] == [[1, 1, 1], [2, 2, 2], [3, 3, 3]]


def test_consistent_quad8_face_load_preserves_resultant_and_moment() -> None:
    nodes, _, faces = _mesh(1, 1, 1)
    loads, audit = _consistent_face_loads(nodes, faces, 0.25)
    assert np.isclose(sum(loads.values()), 0.25, atol=1.0e-12)
    assert np.allclose(audit["origin_moment"], [0.0, 0.125, -0.125], atol=1.0e-12)


def test_full_3d_hex20_mesh_has_expected_topology_and_dofs() -> None:
    model, load_info = _model((2, 2, 2))
    assert len(model.elements) == 8
    assert model.node_count == 81
    assert model.dof_manager().ndof == 243
    assert load_info["loaded_face_count"] == 4
    assert np.isclose(sum(load.value for load in model.loads), 0.25, atol=1.0e-12)
