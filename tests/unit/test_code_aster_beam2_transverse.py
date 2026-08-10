"""Contract tests for the transverse BEAM2 Code_Aster deck."""

from solveur.verification.code_aster_beam2_transverse import (
    _commands,
    _model,
    _newmark_analysis,
    _shear_correction,
)


def test_transverse_deck_declares_bending_dynamic_operators() -> None:
    deck = _commands()
    assert 'MODELISATION="POU_D_E"' in deck
    assert 'FORCE_NODALE=_F(GROUP_NO="TIP", FY=1000)' in deck
    assert 'getValuesWithDescription("DY", ["TIP"])' in deck
    assert 'TYPE_CALCUL="TRAN"' in deck
    assert 'TYPE_CALCUL="HARM"' in deck


def test_transverse_qf_model_has_traceable_tip_observable() -> None:
    model = _model(_newmark_analysis())
    assert model["loads"] == [{"node": 1, "dof": "UY", "value": 1000.0}]
    assert model["analysis"]["history_probes"] == [{"node": 1, "dof": "UY", "label": "tip_uy"}]
    assert _shear_correction() < 1.0e-3
