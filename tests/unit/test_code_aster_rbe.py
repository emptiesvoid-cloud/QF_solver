"""Contract checks for the RBE2 Code_Aster correlation deck."""

from solveur.verification.code_aster_rbe import _commands, _qf_model


def test_rbe2_oracle_deck_uses_explicit_rigid_kinematics_and_rotational_support() -> None:
    deck = _commands()
    assert 'MODELISATION="DIS_TR"' in deck
    assert 'CARA="K_TR_D_N"' in deck
    assert "LIAISON_DDL=(" in deck
    assert 'DDL=("DX", "DX", "DRZ")' in deck
    assert 'COEF_MULT=(1.0, -1.0, 2.0)' in deck
    assert 'DRZ=0.0' in deck
    assert 'FORCE="REAC_NODA"' not in deck


def test_rbe2_qf_model_has_a_two_meter_rigid_arm_and_support() -> None:
    model = _qf_model()
    assert model["nodes"][1] == [0.0, 2.0, 0.0]
    assert model["rbe2"] == [{"name": "rigid_arm", "master": 0, "slaves": [1]}]
