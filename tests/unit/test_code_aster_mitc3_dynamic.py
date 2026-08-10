"""Deck and QF_solver contract checks for the MITC3+ DKT dynamics study."""

from __future__ import annotations

import numpy as np

from solveur.api import solve_model
from solveur.verification.code_aster_mitc3_dynamic import (
    CodeAsterMitc3DynamicsCampaign,
    _modal_analysis,
    _pulse_table,
    _tip_mean_history,
    code_aster_dynamic_comm,
)


def test_mitc3_dynamic_deck_declares_dkt_mass_modal_newmark_and_harmonic() -> None:
    text = code_aster_dynamic_comm(3, 0.001, 8, _pulse_table(0.001, 8), [1.0, 2.0])

    assert 'MODELISATION="DKT"' in text
    assert 'OPTION="MASS_MECA"' in text
    assert "CALC_MODES" in text
    assert 'TYPE_CALCUL="TRAN"' in text
    assert 'SCHEMA="NEWMARK", BETA=0.25, GAMMA=0.5' in text
    assert 'TYPE_CALCUL="HARM"' in text


def test_mitc3_dynamic_qf_model_has_same_resultant_and_tip_mean_probe() -> None:
    campaign = CodeAsterMitc3DynamicsCampaign("unused", nx=4, ny=2)
    modal_model, _, _, tip = campaign._model(_modal_analysis())
    modal = solve_model(modal_model, enforce_policy=False)
    step = 1.0 / float(modal.frequencies_hz[0]) / 40.0
    model, _, _, tip = campaign._model(
        {
            "type": "transient_dynamic",
            "method": "newmark",
            "time_step": step,
            "steps": 4,
            "newmark_beta": 0.25,
            "newmark_gamma": 0.5,
            "load_table": _pulse_table(step, 4),
            "history_probes": [
                {"node": int(node), "dof": "UZ", "label": f"tip_{node}"}
                for node in tip
            ],
        },
        total_load=-1.0,
    )
    result = solve_model(model, enforce_policy=False)

    assert np.sum([load.value for load in model.loads]) == -1.0
    average = _tip_mean_history(result.solver["time_history"], tip)
    assert average.shape == (4,)
    assert np.all(np.isfinite(average))
