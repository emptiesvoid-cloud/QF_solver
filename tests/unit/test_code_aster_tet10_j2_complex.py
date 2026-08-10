from __future__ import annotations

from solveur.verification.code_aster_tet10_j2_complex import _aster_commands, _normalized_rms


def test_complex_code_aster_deck_contains_combined_load_and_tetra10() -> None:
    class Campaign:
        young = 210.0e9
        poisson = 0.3
        yield_stress = 250.0e6
        hardening = 50.0e9
        force_x = 60.0e6
        force_y = -120.0e6
        load_factors = (0.25, 0.5, 0.75, 1.0, 1.1)

    deck = _aster_commands(Campaign(), __import__("numpy").array([0, 4]))
    assert "GROUP_MA=\"SOLID\"" in deck
    assert "VMIS_ISOT_LINE" in deck
    assert "FX=" in deck and "FY=" in deck
    assert 'getValuesWithDescription("DX", ["TIP"])' in deck


def test_normalized_rms_is_zero_for_identical_paths() -> None:
    import numpy as np

    path = np.array([[1.0, 2.0], [3.0, 4.0]])
    assert _normalized_rms(path, path) == 0.0
