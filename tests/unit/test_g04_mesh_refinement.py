"""Controlled 026-G04 HEX8 refinement study with a predeclared observable."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from solveur.api.public import solve_model
from solveur.io.json_reader import JsonModelReader


ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "qualification" / "0_2_6" / "g04_mesh_refinement_study.json"


def _hex8_bar(nx: int) -> dict[str, object]:
    nodes: list[list[float]] = []
    for index in range(nx + 1):
        x = index / nx
        nodes.extend([[x, 0.0, 0.0], [x, 1.0, 0.0], [x, 0.0, 1.0], [x, 1.0, 1.0]])

    elements: list[dict[str, object]] = []
    for index in range(nx):
        left = 4 * index
        right = 4 * (index + 1)
        elements.append(
            {
                "type": "HEX8",
                "nodes": [left, right, right + 1, left + 1, left + 2, right + 2, right + 3, left + 3],
                "material": "steel",
            }
        )

    return {
        "analysis": "linear_static",
        "nodes": nodes,
        "elements": elements,
        "materials": {"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
        "fixed_dofs": [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(4)],
        "loads": [{"node": 4 * nx + node, "dof": "UX", "value": 250.0} for node in range(4)],
    }


def test_g04_hex8_refinement_uses_predeclared_q_and_reference() -> None:
    study = json.loads(STUDY.read_text(encoding="utf-8"))
    assert study["metric"]["policy_id"] == "G04-POL-003"
    assert study["metric"]["threshold"] == 0.01
    assert study["observable"]["name"] == "q"
    assert study["reference"]["name"] == "q_ref"
    assert len(study["model_definition"]["mesh_levels"]) >= 3

    q_values: dict[int, float] = {}
    for level in study["model_definition"]["mesh_levels"]:
        result = solve_model(JsonModelReader().from_dict(_hex8_bar(int(level))), enforce_policy=False)
        end_nodes = range(4 * int(level), 4 * int(level) + 4)
        q_values[int(level)] = sum(float(result.displacements[3 * node]) for node in end_nodes) / 4.0

    assert all(value > 0.0 for value in q_values.values())
    assert q_values[1] < q_values[2] < q_values[4] < q_values[8]
    q_ref = float(study["reference"]["value"])
    final_change = abs(q_values[8] - q_values[4]) / max(abs(q_values[8]), abs(q_values[4]), abs(q_ref))
    assert final_change <= float(study["metric"]["threshold"])
    assert q_values[8] == pytest.approx(4.571463783673658e-09, rel=1.0e-12)
