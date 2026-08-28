from __future__ import annotations

import numpy as np

from solveur.materials.solid import VonMisesElastoplasticMaterial


def test_j2_state_tracks_strain_and_nonnegative_accumulated_plastic_dissipation() -> None:
    material = VonMisesElastoplasticMaterial(E=1000.0, nu=0.25, yield_stress=5.0, hardening_modulus=100.0)
    state = material.initial_state()

    for strain_value in (0.04, 0.08, 0.02, 0.10):
        _, _, state = material.stress_tangent_state(
            np.array([strain_value, 0.0, 0.0, 0.0, 0.0, 0.0]), state
        )
        assert np.asarray(state["strain"]).shape == (6,)
        assert float(state["plastic_dissipation"]) >= 0.0

    assert float(state["plastic_dissipation"]) > 0.0
