"""Level-0 constitutive checks for the common small-strain J2 contract."""

import numpy as np
import pytest

from solveur.materials.solid import VonMisesElastoplasticMaterial


@pytest.fixture
def j2_material() -> VonMisesElastoplasticMaterial:
    return VonMisesElastoplasticMaterial(E=1000.0, nu=0.25, yield_stress=5.0, hardening_modulus=100.0)


def test_hydrostatic_loading_does_not_activate_j2(j2_material: VonMisesElastoplasticMaterial) -> None:
    response = j2_material.evaluate(np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0]), j2_material.initial_state())

    assert response.diagnostics["elastic"] is True
    assert response.trial_state["equivalent_plastic_strain"] == 0.0
    assert response.trial_state["yield_function"] == pytest.approx(-5.0)


def test_pure_shear_activates_j2_and_returns_to_the_surface(
    j2_material: VonMisesElastoplasticMaterial,
) -> None:
    response = j2_material.evaluate(np.array([0.0, 0.0, 0.0, 0.1, 0.0, 0.0]), j2_material.initial_state())

    assert response.diagnostics["elastic"] is False
    assert response.trial_state["equivalent_plastic_strain"] > 0.0
    assert response.trial_state["yield_function"] == pytest.approx(0.0)
    assert np.all(np.isfinite(response.tangent))


def test_constitutive_evaluation_is_repeatable_from_the_same_committed_state(
    j2_material: VonMisesElastoplasticMaterial,
) -> None:
    strain = np.array([0.08, 0.005, -0.002, 0.01, -0.004, 0.006])
    committed = j2_material.initial_state()
    first = j2_material.evaluate(strain, committed)
    second = j2_material.evaluate(strain, committed)

    assert np.array_equal(first.stress, second.stress)
    assert np.array_equal(first.tangent, second.tangent)
    assert first.trial_state == second.trial_state
    assert committed == j2_material.initial_state()
