"""Contract checks for the BEAM2 modal Code_Aster campaign."""

from solveur.verification.code_aster_beam2_modal import _commands, _qf_model


def test_beam2_modal_oracle_deck_uses_dynamic_mass_and_six_modes() -> None:
    deck = _commands()
    assert 'MODELISATION="POU_D_E"' in deck
    assert 'OPTION="MASS_MECA"' in deck
    assert 'NMAX_FREQ=6' in deck
    assert 'RHO=7800.0' in deck


def test_beam2_modal_qf_model_has_density_and_clamped_root() -> None:
    model = _qf_model()
    assert model["analysis"] == {"type": "modal", "method": "eigh", "modes": 6}
    assert model["materials"]["beam"]["density"] == 7800.0
    assert len(model["fixed_dofs"][0]["dofs"]) == 6
