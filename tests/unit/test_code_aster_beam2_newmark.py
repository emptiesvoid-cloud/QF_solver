"""Contract tests for the BEAM2 Code_Aster Newmark deck."""

from solveur.verification.code_aster_beam2_newmark import (
    _commands,
    _transient_model,
)


def test_beam2_newmark_deck_declares_consistent_dynamic_operators() -> None:
    deck = _commands()
    assert 'MODELISATION="POU_D_E"' in deck
    assert 'OPTION="MASS_MECA"' in deck
    assert 'TYPE_CALCUL="TRAN"' in deck
    assert 'SCHEMA="NEWMARK", BETA=0.25, GAMMA=0.5' in deck
    assert 'TYPE_CALCUL="HARM"' in deck


def test_beam2_newmark_qf_model_declares_a_traceable_axial_probe() -> None:
    transient = _transient_model()
    assert transient["elements"][0]["type"] == "BEAM2"
    assert transient["materials"]["beam"]["density"] == 7800.0
    assert transient["analysis"]["history_probes"][0]["dof"] == "UX"
