"""Static contracts for the folded-facet Code_Aster correlation."""

from solveur.verification.code_aster_contact_folded import CodeAsterFoldedContactCampaign, _commands


def test_folded_oracle_imposes_the_final_tilted_normal_constraint() -> None:
    deck = _commands(CodeAsterFoldedContactCampaign._normal, 0.18371173070873836)

    assert 'MODELISATION="DIS_T"' in deck
    assert 'CARA="K_T_D_N"' in deck
    assert 'GROUP_NO=("SLAVE_X", "SLAVE_Y", "SLAVE_Z")' in deck
    assert 'DDL=("DX", "DY", "DZ")' in deck
    assert "LIAISON_DDL" in deck
