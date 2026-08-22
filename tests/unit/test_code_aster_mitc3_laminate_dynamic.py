"""Contracts for the MITC3+ laminate dynamics Code_Aster deck."""

from solveur.verification.code_aster_mitc3_laminate_dynamic import (
    CodeAsterMitc3LaminateDynamicsCampaign,
    DEFAULT_STEPS_PER_PERIOD,
    _analytical_first_frequency_hz,
    _modal_analysis,
    _pulse_table,
    code_aster_dynamic_comm,
)
from solveur.verification.mitc3_models import LAMINATE_MATERIAL


def test_code_aster_mitc3_laminate_dynamic_deck_has_the_required_paths() -> None:
    deck = code_aster_dynamic_comm(4, _pulse_table(1.0e-4, 8), [10.0, 20.0])
    assert "DEFI_COMPOSITE" in deck
    assert "ELAS_ORTH" in deck
    assert 'MODELISATION="DST"' in deck
    assert "A_CIS=0.8333333333333334" in deck
    assert "CALC_MODES" in deck
    assert 'TYPE_CALCUL="TRAN"' in deck
    assert 'TYPE_CALCUL="HARM"' in deck
    assert 'GROUP_NO="TIP_0000"' in deck
    assert 'GROUP_NO="TIP_0003"' in deck
    assert 'FZ=-0.1666666666666667' in deck


def test_dynamic_external_deck_uses_the_qf_laminate_constants() -> None:
    deck = code_aster_dynamic_comm(1, _pulse_table(1.0e-4, 2), [10.0])
    assert f"E_L={LAMINATE_MATERIAL['E1']:.16g}" in deck
    assert f"E_T={LAMINATE_MATERIAL['E2']:.16g}" in deck
    assert f"G_LN={LAMINATE_MATERIAL['G13']:.16g}" in deck
    assert f"G_TN={LAMINATE_MATERIAL['G23']:.16g}" in deck
    assert f"RHO={LAMINATE_MATERIAL['density']:.16g}" in deck


def test_mitc3_laminate_model_keeps_triangles_layup_and_total_tip_load() -> None:
    campaign = CodeAsterMitc3LaminateDynamicsCampaign("unused", nx=4, ny=1)
    modal, triangles, root, tip = campaign._model(_modal_analysis(), transverse_force=0.0)
    loaded, _, _, _ = campaign._model(_modal_analysis(), transverse_force=-1.0)
    assert len(modal.elements) == 8
    assert triangles.shape == (8, 3)
    assert len(modal.materials["skin"]["plies"]) == 4
    assert sum(load.value for load in loaded.loads) == -1.0
    assert root.size == tip.size == 2


def test_dynamic_protocol_uses_an_independent_analytical_reference() -> None:
    campaign = CodeAsterMitc3LaminateDynamicsCampaign("unused", nx=4, ny=1)

    assert DEFAULT_STEPS_PER_PERIOD == 80
    assert campaign.steps_per_period == 80
    assert abs(_analytical_first_frequency_hz() - 13.9287082617) < 1.0e-8


def test_dynamic_protocol_rejects_a_temporal_resolution_below_one_percent_target() -> None:
    try:
        CodeAsterMitc3LaminateDynamicsCampaign("unused", nx=4, ny=1, steps_per_period=40)
    except ValueError as error:
        assert "80" in str(error)
    else:
        raise AssertionError("The external MITC3+ protocol must require at least 80 steps per period.")
