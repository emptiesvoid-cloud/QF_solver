"""Contract tests for the curved orthotropic MITC4 Code_Aster deck."""

from solveur.verification.code_aster_mitc4_laminate_dynamic import code_aster_dynamic_comm


def test_curved_dynamic_deck_uses_selected_transverse_probe() -> None:
    deck = code_aster_dynamic_comm(
        5,
        1.0e-3,
        [{"time": 0.0, "factor": 0.0}, {"time": 1.0e-3, "factor": 1.0}],
        [0.0, 10.0],
        layup=(0.0,),
        ply_thickness=1.0e-2,
        probe_dof="UY",
    )

    assert "FY=-0.2" in deck
    assert 'getValuesWithDescription("DY", ["TIP"])' in deck
    assert '"tip_uy_m": history' in deck
    assert '"harmonic_tip_uy_m": harmonic_values' in deck
