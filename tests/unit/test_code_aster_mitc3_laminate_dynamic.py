"""Contracts for the MITC3+ laminate dynamics Code_Aster deck."""

from solveur.verification.code_aster_mitc3_laminate_dynamic import (
    CodeAsterMitc3LaminateDynamicsCampaign,
    _modal_analysis,
    _pulse_table,
    code_aster_dynamic_comm,
)


def test_code_aster_mitc3_laminate_dynamic_deck_has_the_required_paths() -> None:
    deck = code_aster_dynamic_comm(4, _pulse_table(1.0e-4, 8), [10.0, 20.0])
    assert "DEFI_COMPOSITE" in deck
    assert "ELAS_ORTH" in deck
    assert 'MODELISATION="DST"' in deck
    assert "CALC_MODES" in deck
    assert 'TYPE_CALCUL="TRAN"' in deck
    assert 'TYPE_CALCUL="HARM"' in deck


def test_mitc3_laminate_model_keeps_triangles_layup_and_total_tip_load() -> None:
    campaign = CodeAsterMitc3LaminateDynamicsCampaign("unused", nx=4, ny=1)
    modal, triangles, root, tip = campaign._model(_modal_analysis(), transverse_force=0.0)
    loaded, _, _, _ = campaign._model(_modal_analysis(), transverse_force=-1.0)
    assert len(modal.elements) == 8
    assert triangles.shape == (8, 3)
    assert len(modal.materials["skin"]["plies"]) == 4
    assert sum(load.value for load in loaded.loads) == -1.0
    assert root.size == tip.size == 2
