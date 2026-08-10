import numpy as np

from solveur.verification.mitc4_modal_plate import (
    Mitc4SimplySupportedPlateStudy,
    _subspace_mac_min,
)


def test_repeated_modes_are_compared_as_an_invariant_subspace() -> None:
    reference = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]])
    rotation = np.array([[1.0, 1.0], [-1.0, 1.0]]) / np.sqrt(2.0)

    np.testing.assert_allclose(
        _subspace_mac_min(reference @ rotation, reference),
        1.0,
        atol=1.0e-14,
    )


def test_mitc4_plate_first_four_modes_converge_to_navier_reference() -> None:
    summary = Mitc4SimplySupportedPlateStudy(meshes=(4, 8, 12)).run()

    assert summary["status"] == "PASS"
    assert all(summary["checks"].values())
    final = summary["points"][-1]
    assert max(final["relative_frequency_errors"]) < 0.035
    assert final["first_mode_mac"] > 0.999
    assert final["repeated_mode_subspace_mac"] > 0.999
    assert final["fourth_mode_mac"] > 0.999
