"""Deterministic fail-closed invalid-input contracts for 026-G04."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from solveur.api.public import solve_model
from solveur.core.errors import InputValidationError, MeshValidationError, NumericalConvergenceError
from solveur.io.json_reader import JsonModelReader


ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "qualification" / "0_2_6" / "g04_invalid_input_cases.json"
ERRORS = {
    "InputValidationError": InputValidationError,
    "MeshValidationError": MeshValidationError,
    "NumericalConvergenceError": NumericalConvergenceError,
}


def _tet4_model() -> dict[str, object]:
    return {
        "analysis": "linear_static",
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        "materials": {"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
        "fixed_dofs": [
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 1, "dofs": ["UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY"]},
        ],
        "loads": [{"node": 1, "dof": "UX", "value": 1.0}],
    }


def _case_model(category: str) -> dict[str, object]:
    data = _tet4_model()
    if category == "invalid_connectivity":
        data["elements"] = [{"type": "TET4", "nodes": [0, 1, 2], "material": "steel"}]
    elif category == "incomplete_material":
        data["materials"] = {"steel": {"type": "isotropic_3d", "E": 210.0e9}}
    elif category == "insufficient_boundary_conditions":
        data["fixed_dofs"] = []
    elif category == "incoherent_boundary_dof":
        data["fixed_dofs"] = [{"node": 0, "dofs": ["RX"]}]
    elif category == "degenerate_geometry":
        data["nodes"] = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 0.0]]
    elif category == "invalid_element_parameter":
        data = {
            "analysis": "linear_static",
            "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
            "elements": [{"type": "BEAM2", "nodes": [0, 1], "material": "beam"}],
            "materials": {"beam": {"type": "beam_isotropic", "E": 210.0e9, "G": 80.0e9, "A": 0.0, "Iy": 1.0e-6, "Iz": 1.0e-6, "J": 1.0e-6}},
            "fixed_dofs": [{"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}],
            "loads": [{"node": 1, "dof": "UX", "value": 1.0}],
        }
    else:
        raise AssertionError(f"unmapped G04 invalid-input category: {category}")
    return data


@pytest.mark.parametrize(
    "case",
    json.loads(CASES.read_text(encoding="utf-8"))["cases"],
    ids=lambda case: case["case_id"],
)
def test_g04_invalid_inputs_fail_closed_and_deterministically(case: dict[str, str]) -> None:
    expected_type = ERRORS[case["expected_exception"]]
    messages: list[str] = []
    for _ in range(2):
        with pytest.raises(expected_type) as exc_info:
            model = JsonModelReader().from_dict(copy.deepcopy(_case_model(case["category"])))
            if case["operation"] == "solve":
                solve_model(model, enforce_policy=False)
        messages.append(str(exc_info.value))
    assert messages[0] == messages[1]
    assert case["message_fragment"] in messages[0]
