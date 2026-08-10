"""Deck-level checks for the reproducible Code_Aster normal-contact oracle."""

from solveur.verification.code_aster_contact import single_node_mesh, unilateral_contact_comm


def test_code_aster_unilateral_contact_deck_declares_the_same_normal_problem() -> None:
    mesh = single_node_mesh()
    commands = unilateral_contact_comm(-200.0)

    assert "POI1" in mesh
    assert "GROUP_NO\nSLAVE" in mesh
    assert 'FORMULATION="LIAISON_UNIL"' in commands
    assert 'NOM_CMP="DZ"' in commands
    assert "COEF_IMPO=gap" in commands
    assert "COEF_MULT=multiplier" in commands
    assert "FZ=-200" in commands
