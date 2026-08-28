from __future__ import annotations

import numpy as np
import pytest

from solveur.core.material_state import MaterialStateSession, StateTransaction, state_digest
from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear_contracts import NonlinearFailureReason


def test_generic_state_transaction_rolls_back_without_mutating_committed_state() -> None:
    committed = {"contact": {"active": [1, 2]}, "multipliers": np.array([0.0, 1.0])}
    original_digest = state_digest(committed)
    transaction = StateTransaction(committed)

    trial = transaction.begin_trial()
    trial["contact"]["active"].append(3)
    trial["multipliers"][0] = 9.0

    assert transaction.committed_digest == original_digest
    assert transaction.trial_digest != original_digest
    transaction.rollback()
    assert transaction.committed_digest == original_digest
    assert committed["contact"]["active"] == [1, 2]
    np.testing.assert_array_equal(committed["multipliers"], [0.0, 1.0])


def test_generic_state_transaction_commits_in_place() -> None:
    committed = {"active": []}
    identity = id(committed)
    transaction = StateTransaction(committed)
    transaction.begin_trial()["active"].append(4)
    transaction.commit()

    assert id(committed) == identity
    assert committed == {"active": [4]}


def test_generic_state_transaction_commits_numpy_state_in_place() -> None:
    committed = np.asarray([[1.0, 2.0]])
    transaction = StateTransaction(committed)
    trial = transaction.begin_trial()
    trial[0, 0] = 9.0
    transaction.commit()
    assert committed[0, 0] == 9.0
    assert transaction.trial is None


def test_generic_state_transaction_rejects_committed_state_corruption() -> None:
    committed = {"active": [1], "multiplier": np.array([0.0])}
    transaction = StateTransaction(committed)
    transaction.begin_trial()
    committed["active"].append(2)

    with pytest.raises(NumericalConvergenceError) as error:
        transaction.rollback()

    assert error.value.reason is NonlinearFailureReason.STATE_CORRUPTION
    assert error.value.diagnostics["transaction"] == "generic"
    assert error.value.diagnostics["committed_digest_before_trial"] != error.value.diagnostics[
        "committed_digest_observed"
    ]


def test_material_state_session_rejects_committed_state_corruption() -> None:
    committed = {0: [{"equivalent_plastic_strain": 0.0}]}
    session = MaterialStateSession(committed)
    session.begin_trial()
    committed[0][0]["equivalent_plastic_strain"] = 1.0

    with pytest.raises(NumericalConvergenceError) as error:
        session.rollback()

    assert error.value.reason is NonlinearFailureReason.STATE_CORRUPTION
    assert error.value.diagnostics["transaction"] == "material"
