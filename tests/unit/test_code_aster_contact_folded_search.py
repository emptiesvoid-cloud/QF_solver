"""Static contracts for the autonomous folded-surface Code_Aster study."""

from solveur.verification.code_aster_contact_folded_search import _commands


def test_folded_search_oracle_uses_autonomous_frictionless_surface_contact() -> None:
    deck = _commands()

    assert 'FORMULATION="CONTINUE"' in deck
    assert 'FROTTEMENT="SANS"' in deck
    assert 'REAC_GEOM="AUTOMATIQUE"' in deck
    assert 'GROUP_MA_MAIT="MASTER"' in deck
    assert 'GROUP_MA_ESCL="SLAVE"' in deck
