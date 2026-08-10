from __future__ import annotations

import math

import numpy as np
import pytest

from solveur.api import solve_model
from solveur.core.assembler import GlobalAssembler
from solveur.core.errors import InputValidationError
from solveur.core.model import NodalLoad
from solveur.verification.transient_modal_oracle import PiecewiseLinearModalOracle
from tests.unit.test_analysis_features import transient_tet4_model
from tests.unit.test_mitc4_dynamics import _soft_dynamic_plate


def test_half_sine_pulse_and_linear_chirp_factors_are_explicit() -> None:
    pulse = transient_tet4_model()
    pulse.analysis.parameters.update(
        {
            "steps": 4,
            "time_step": 0.25,
            "load_function": "half_sine_pulse",
            "pulse_duration": 0.5,
        }
    )
    pulse_factors = [row["load_factor"] for row in solve_model(pulse).solver["time_history"]]
    np.testing.assert_allclose(pulse_factors, [1.0, 0.0, 0.0, 0.0], atol=1.0e-15)

    chirp = transient_tet4_model()
    chirp.analysis.parameters.update(
        {
            "steps": 4,
            "time_step": 0.25,
            "load_function": "linear_chirp",
            "chirp_start_hz": 0.0,
            "chirp_end_hz": 1.0,
            "chirp_duration": 1.0,
        }
    )
    factors = [row["load_factor"] for row in solve_model(chirp).solver["time_history"]]
    expected = [math.sin(2.0 * math.pi * 0.5 * time**2) for time in (0.25, 0.5, 0.75, 1.0)]
    np.testing.assert_allclose(factors, expected, rtol=0.0, atol=1.0e-15)


@pytest.mark.parametrize(
    "parameters",
    [
        {"load_function": "unknown"},
        {"load_function": "half_sine_pulse"},
        {"load_function": "linear_chirp", "chirp_start_hz": 0.0, "chirp_end_hz": 1.0},
    ],
)
def test_invalid_broadband_load_definition_is_rejected(parameters: dict[str, object]) -> None:
    model = transient_tet4_model()
    model.analysis.parameters.update(parameters)
    with pytest.raises(InputValidationError):
        solve_model(model)


def test_transient_shell_face_stress_probe_is_signed_and_finite() -> None:
    model = _soft_dynamic_plate(
        {
            "type": "transient_dynamic",
            "method": "newmark",
            "time_step": 1.0e-3,
            "steps": 2,
            "load_function": "linear_ramp",
            "history_shell_stress_probes": [
                {"node": 1, "face": "top", "component": "S11", "label": "top_s11"}
            ],
        }
    )
    model.loads = [NodalLoad(node=1, dof="UZ", value=1.0)]
    history = solve_model(model).solver["time_history"]
    assert all(np.isfinite(row["shell_stress_probes"]["top_s11"]) for row in history)


def test_piecewise_linear_modal_oracle_matches_constant_load_closed_form() -> None:
    model = transient_tet4_model()
    assembler = GlobalAssembler()
    dofs = model.dof_manager()
    load = assembler.assemble_loads(model, dofs)
    oracle = PiecewiseLinearModalOracle(model)
    dt = 0.01
    probe = dofs.index(1, "UX")
    history = oracle.propagate(
        load,
        np.asarray([1.0, 1.0]),
        dt,
        displacement_probe_index=probe,
    )
    reduced_load = oracle.reducer.reduce_load(load)
    modal_load = oracle.modes.T @ reduced_load
    modal_q = modal_load / oracle.eigenvalues * (
        1.0 - np.cos(np.sqrt(oracle.eigenvalues) * dt)
    )
    expected = oracle.reducer.expand_state(oracle.modes @ modal_q, load)[probe]
    assert history.displacement_probe[0] == pytest.approx(expected, rel=1.0e-11, abs=1.0e-14)
