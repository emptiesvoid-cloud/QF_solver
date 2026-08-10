from solveur.verification.mitc4_modal import Mitc4ModalCantileverStudy


def test_mitc4_modal_cantilever_converges_to_slender_beam_reference() -> None:
    summary = Mitc4ModalCantileverStudy(meshes=((4, 1), (8, 2), (16, 4))).run()

    assert summary["status"] == "PASS"
    assert summary["checks"] == {
        "frequency": True,
        "mode_shape": True,
        "residual": True,
        "mass_orthogonality": True,
        "convergence": True,
    }
    final = summary["points"][-1]
    assert final["relative_frequency_error"] < 0.02
    assert final["mode_assurance_criterion"] > 0.999
