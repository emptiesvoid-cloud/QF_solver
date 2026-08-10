"""Static contracts for the active TET4-master Code_Aster oracle."""

from solveur.verification.code_aster_contact_tet4 import _commands, _qf_model


def test_tet4_master_oracle_uses_same_tetra_and_active_barycentric_constraint() -> None:
    deck = _commands()
    assert 'MODELISATION="3D"' in deck
    assert 'MODELISATION="DIS_T"' in deck
    assert 'CARA="K_T_D_N"' in deck
    assert 'GROUP_NO=("SLAVE", "N1_GROUP", "N2_GROUP", "N3_GROUP")' in deck
    assert 'COEF_MULT=(1.0, -0.5, -0.25, -0.25)' in deck
    assert 'COEF_IMPO=-0.1' in deck


def test_tet4_master_qf_model_has_one_tetra_and_one_contact_pair() -> None:
    model = _qf_model()
    assert model["elements"] == [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "elastic"}]
    assert model["contacts"] == [{"name": "tet4_master", "slave_node": 4, "master_nodes": [0, 2, 1]}]
