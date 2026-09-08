"""Focused validation contract for Newmark initial conditions."""

from __future__ import annotations

import pytest

from solveur.api import solve_model
from solveur.core.errors import InputValidationError
from tests.unit.test_analysis_features import transient_tet4_model
from scripts import run_wp13_02b2_evidence as wp13_02b2


def _model(initial_displacements: object) -> object:
    model = transient_tet4_model()
    model.loads = []
    model.analysis.parameters.update(
        {
            "steps": 1,
            "load_factors": [0.0],
            "initial_displacements": initial_displacements,
            "initial_velocities": [],
        }
    )
    return model


def test_valid_initial_conditions_list_is_preserved() -> None:
    result = solve_model(
        _model([{"node": 1, "dof": "UX", "value": 1.0e-3}]),
        enforce_policy=False,
    )
    assert result.status == "PASS"


@pytest.mark.parametrize(
    "initial_displacements",
    [
        {"node": 1, "dof": "UX", "value": 1.0e-3},
        ( {"node": 1, "dof": "UX", "value": 1.0e-3}, ),
    ],
)
def test_non_list_initial_conditions_are_rejected(initial_displacements: object) -> None:
    with pytest.raises(InputValidationError, match="must be provided as a list"):
        solve_model(_model(initial_displacements), enforce_policy=False)


@pytest.mark.parametrize(
    "initial_displacements, message",
    [
        (["not an entry"], "must be an object"),
        ([{"node": 1, "dof": "UX"}], "missing required field"),
        ([{"node": 99, "dof": "UX", "value": 1.0}], "Invalid initial-condition"),
        ([{"node": 1, "dof": "UX", "value": "not a number"}], "Invalid initial-condition"),
        ([{"node": 1, "dof": "UX", "value": float("nan")}], None),
    ],
)
def test_malformed_initial_conditions_are_rejected(
    initial_displacements: object, message: str | None
) -> None:
    expected = pytest.raises(InputValidationError, match=message) if message else pytest.raises(InputValidationError)
    with expected:
        solve_model(_model(initial_displacements), enforce_policy=False)


def test_empty_initial_conditions_list_is_supported() -> None:
    result = solve_model(_model([]), enforce_policy=False)
    assert result.status == "PASS"


def test_mixed_newmark_smoke_keeps_all_element_families() -> None:
    base = wp13_02b2.build(1)
    reference = wp13_02b2.reference(base)
    model = wp13_02b2.clone(base, reference, reference["period"] / 20.0, 2)

    result = solve_model(model, enforce_policy=False)

    assert result.status == "PASS"
    assert {element.type for element in model.elements} == {"TET4", "WEDGE6", "HEX8"}
