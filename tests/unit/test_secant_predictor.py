"""No-FEM checks for the bounded experimental secant trial state."""

import numpy as np
import pytest

from solveur.core.errors import InputValidationError
from solveur.core.nonlinear.secant import secant_trial
from solveur.core.nonlinear.state import NonlinearState


def test_secant_trial_uses_load_ratio_preserves_fixed_dofs_and_source_states():
    previous = NonlinearState(np.array([0.0, 1.0]), load_factor=197 / 192)
    accepted = NonlinearState(np.array([0.0, 2.0]), load_factor=198 / 192)
    previous_digest = previous.digest
    accepted_digest = accepted.digest

    first, ratio = secant_trial(previous, accepted, 200 / 192, np.array([0]))
    assert ratio == pytest.approx(2.0)
    np.testing.assert_allclose(first.displacement, [0.0, 4.0], rtol=1.0e-13, atol=0.0)
    assert first.load_factor == accepted.load_factor

    accepted_next = NonlinearState(first.displacement, load_factor=200 / 192)
    second, ratio = secant_trial(accepted, accepted_next, 202 / 192, np.array([0]))
    assert ratio == pytest.approx(1.0)
    np.testing.assert_allclose(second.displacement, [0.0, 6.0], rtol=1.0e-13, atol=0.0)
    assert previous.digest == previous_digest
    assert accepted.digest == accepted_digest


@pytest.mark.parametrize(
    "previous,accepted,fixed",
    [
        (
            NonlinearState(np.array([0.0, 1.0]), load_factor=1.0),
            NonlinearState(np.array([0.0, 2.0]), load_factor=2.0, material_state={"history": [0.1]}),
            np.array([0]),
        ),
        (
            NonlinearState(np.array([0.0, 1.0]), load_factor=1.0),
            NonlinearState(np.array([0.0, 2.0]), load_factor=2.0, contact_state={"active": True}),
            np.array([0]),
        ),
        (
            NonlinearState(np.array([0.0, 1.0]), load_factor=1.0),
            NonlinearState(np.array([0.0, 2.0]), load_factor=2.0),
            np.array([1]),
        ),
    ],
)
def test_secant_trial_refuses_stateful_or_inconsistent_history(previous, accepted, fixed):
    with pytest.raises(InputValidationError):
        secant_trial(previous, accepted, 3.0, fixed)
