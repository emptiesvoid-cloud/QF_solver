"""Targeted tests for the WP09 HEX20 extension study contract and mesh."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.run_wp09_hex20_extension import _model
from scripts.run_wp09_hex20_extension_reference import _recompute


ROOT = Path(__file__).resolve().parents[2]


def test_hex20_extension_contract_is_hex20_only() -> None:
    contract = json.loads((ROOT / "qualification/0_2_9/wp09_hex20_extension_contract.json").read_text())
    assert contract["mesh_hierarchy"]["family"] == "HEX20"
    assert [row["cells"] for row in contract["mesh_hierarchy"]["levels"]] == [1, 2, 3]
    assert contract["formal_status"]["wp09_official_points"] == "8/8 HEX8 unchanged"


def test_hex20_mesh_has_shared_quadratic_nodes_and_valid_dofs() -> None:
    model = _model(2)
    assert all(element.type == "HEX20" for element in model.elements)
    assert len(model.elements) == 2
    assert model.node_count == 32
    assert model.dof_manager().ndof == 96
    assert np.all(np.isfinite(model.nodes))


def test_independent_recomputation_rejects_missing_observables() -> None:
    values, errors = _recompute({"result": {}})
    assert values["selected_displacement"] == 0.0
    assert "missing:displacements" in errors
    assert "missing:solver_steps" in errors
