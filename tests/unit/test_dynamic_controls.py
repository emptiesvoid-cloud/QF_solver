from __future__ import annotations

import math

import numpy as np
import pytest

from solveur.api import solve_model
from solveur.core.dynamic_controls import (
    component_load_factors,
    rayleigh_damping_definition,
    validate_per_load_factors,
)
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel


def test_modal_targets_recover_known_rayleigh_coefficients() -> None:
    alpha = 0.3
    beta = 5.0e-4
    frequencies = (2.0, 12.0)
    targets = [
        {
            "frequency_hz": frequency,
            "damping_ratio": alpha / (4.0 * math.pi * frequency)
            + beta * math.pi * frequency,
        }
        for frequency in frequencies
    ]
    definition = rayleigh_damping_definition({"modal_damping_targets": targets})
    assert definition.source == "rayleigh_fitted_to_modal_targets"
    assert definition.alpha == pytest.approx(alpha)
    assert definition.beta == pytest.approx(beta)


@pytest.mark.parametrize(
    "parameters",
    [
        {"modal_damping_targets": []},
        {
            "modal_damping_targets": [
                {"frequency_hz": 1.0, "damping_ratio": 0.02},
                {"frequency_hz": 1.0, "damping_ratio": 0.02},
            ]
        },
        {
            "modal_damping_targets": [
                {"frequency_hz": 1.0, "damping_ratio": 0.10},
                {"frequency_hz": 10.0, "damping_ratio": 0.001},
            ]
        },
        {
            "rayleigh_alpha": 0.1,
            "modal_damping_targets": [
                {"frequency_hz": 1.0, "damping_ratio": 0.02},
                {"frequency_hz": 10.0, "damping_ratio": 0.02},
            ],
        },
    ],
)
def test_invalid_modal_damping_targets_are_rejected(parameters: dict[str, object]) -> None:
    with pytest.raises(InputValidationError):
        rayleigh_damping_definition(parameters)


def test_per_load_factor_validation_and_step_selection() -> None:
    histories = {"0": [0.0, 1.0], "2": [1.0, -1.0, 0.5]}
    validate_per_load_factors(histories, 3)
    assert component_load_factors(histories, 3, 0, 0.25) == [0.0, 0.25, 1.0]
    assert component_load_factors(histories, 3, 4, 0.25) == [1.0, 0.25, 0.5]
    with pytest.raises(InputValidationError, match="outside"):
        validate_per_load_factors({"3": [1.0]}, 3)
    with pytest.raises(InputValidationError, match="non-empty"):
        validate_per_load_factors({"0": []}, 3)


def test_multicomponent_newmark_response_obeys_superposition() -> None:
    steps = 12
    first = [math.sin(math.pi * step / steps) for step in range(steps + 1)]
    second = [step / steps for step in range(steps + 1)]
    combined = _two_component_model(first, second)
    first_only = _two_component_model(first, [0.0] * (steps + 1))
    second_only = _two_component_model([0.0] * (steps + 1), second)
    result = solve_model(combined)
    result_first = solve_model(first_only)
    result_second = solve_model(second_only)
    np.testing.assert_allclose(
        result.displacements,
        result_first.displacements + result_second.displacements,
        rtol=1.0e-11,
        atol=1.0e-13,
    )
    np.testing.assert_allclose(
        result.velocities,
        result_first.velocities + result_second.velocities,
        rtol=1.0e-11,
        atol=1.0e-13,
    )
    assert result.solver["load_component_count"] == 2
    assert result.solver["time_history"][5]["load_component_factors"] == [first[6], second[6]]


def test_newmark_reports_rayleigh_fit_from_modal_targets() -> None:
    alpha = 0.2
    beta = 2.0e-4
    targets = []
    for frequency in (3.0, 15.0):
        targets.append(
            {
                "frequency_hz": frequency,
                "damping_ratio": alpha / (4.0 * math.pi * frequency)
                + beta * math.pi * frequency,
            }
        )
    model = _two_component_model([0.0] * 13, [0.0] * 13)
    model.analysis.parameters.pop("rayleigh_alpha")
    model.analysis.parameters["modal_damping_targets"] = targets
    result = solve_model(model)
    assert result.solver["rayleigh_alpha"] == pytest.approx(alpha)
    assert result.solver["rayleigh_beta"] == pytest.approx(beta)
    assert result.solver["damping_definition"]["source"] == (
        "rayleigh_fitted_to_modal_targets"
    )


def test_newmark_summary_postprocess_avoids_element_field_materialization() -> None:
    model = _two_component_model([0.0] * 13, [0.0] * 13)
    model.analysis.parameters["postprocess_mode"] = "summary"

    result = solve_model(model)

    assert result.status == "PASS"
    assert result.solver["postprocess_mode"] == "summary"
    assert result.element_results == []
    assert result.nodal_results == []


def _two_component_model(
    first_factors: list[float], second_factors: list[float]
) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        analysis={
            "type": "transient_dynamic",
            "method": "newmark",
            "time_step": 0.002,
            "steps": 12,
            "rayleigh_alpha": 0.05,
            "load_factors_by_load": {"0": first_factors, "1": second_factors},
        },
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        materials={
            "steel": {
                "type": "isotropic_3d",
                "E": 1000.0,
                "nu": 0.25,
                "density": 10.0,
            }
        },
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 1, "dofs": ["UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[
            {"node": 1, "dof": "UX", "value": 1.0},
            {"node": 1, "dof": "UY", "value": -0.7},
        ],
    )
