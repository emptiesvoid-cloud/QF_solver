"""Contracts for the bounded MITC4 laminate dynamics Code_Aster deck."""

from solveur.verification.code_aster_mitc4_laminate_dynamic import (
    CodeAsterMitc4LaminateDynamicsCampaign,
    _modal_analysis,
    _pulse_table,
    code_aster_dynamic_comm,
)


def test_code_aster_laminate_dynamic_deck_has_all_three_analysis_paths() -> None:
    deck = code_aster_dynamic_comm(4, 1.0e-4, _pulse_table(1.0e-4, 8), [10.0, 20.0])
    assert "DEFI_COMPOSITE" in deck
    assert "ELAS_ORTH" in deck
    assert "CALC_MODES" in deck
    assert 'TYPE_CALCUL="TRAN"' in deck
    assert 'TYPE_CALCUL="HARM"' in deck
    assert "COQUE_NCOU=4" in deck


def test_campaign_model_keeps_the_laminate_layup_and_tip_loads() -> None:
    campaign = CodeAsterMitc4LaminateDynamicsCampaign("unused", nx=4, ny=1)
    modal, nodes = campaign._model(_modal_analysis())
    loaded, _ = campaign._model(_modal_analysis(), total_load=-1.0)
    assert len(modal.elements) == 4
    assert len(modal.materials["laminate"]["plies"]) == 4
    assert sum(item.value for item in loaded.loads) == -1.0
    assert nodes.shape == (10, 3)
