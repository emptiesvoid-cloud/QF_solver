"""Contract checks for the discrete Code_Aster correlation deck."""

from solveur.verification.code_aster_discrete import (
    _commands,
    _qf_modal_model,
    _qf_static_model,
    _qf_transient_model,
    _qf_harmonic_model,
)


def test_discrete_oracle_deck_contains_static_modal_and_newmark_discrete_terms() -> None:
    deck = _commands()
    assert 'MODELISATION="DIS_T"' in deck
    assert 'CARA="K_T_D_N"' in deck
    assert 'CARA="M_T_D_N"' in deck
    assert 'CARA="M_T_D_N", VALE=10.0' in deck
    assert 'NMAX_FREQ=1' in deck
    assert 'TYPE_CALCUL="TRAN"' in deck
    assert 'SCHEMA="NEWMARK", BETA=0.25, GAMMA=0.5' in deck
    assert 'TYPE_CALCUL="HARM"' in deck


def test_discrete_qf_models_share_spring_mass_data() -> None:
    static = _qf_static_model()
    modal = _qf_modal_model()
    transient = _qf_transient_model()
    harmonic = _qf_harmonic_model()
    assert static["springs"] == modal["springs"]
    assert static["springs"] == transient["springs"]
    assert static["springs"] == harmonic["springs"]
    assert static["concentrated_masses"] == modal["concentrated_masses"]
    assert static["concentrated_masses"] == transient["concentrated_masses"]
    assert static["loads"][0]["value"] == 25.0
    assert transient["analysis"]["newmark_beta"] == 0.25
    assert harmonic["analysis"]["frequencies_hz"] == [0.25, 0.75, 1.25, 2.25]
