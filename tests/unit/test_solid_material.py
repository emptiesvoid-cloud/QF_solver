import numpy as np
import pytest

from solveur.materials.solid import NonlinearSolidMaterial, SolidMaterial, VonMisesElastoplasticMaterial


def test_solid_material_elasticity_matrix_is_symmetric():
    material = SolidMaterial(E=210.0e9, nu=0.3)
    matrix = material.elasticity_matrix
    assert matrix.shape == (6, 6)
    assert np.allclose(matrix, matrix.T)
    assert np.all(np.linalg.eigvalsh(matrix) > 0.0)


def test_solid_material_reuses_elasticity_matrix():
    material = SolidMaterial(E=210.0e9, nu=0.3)
    first = material.elasticity_matrix
    second = material.elasticity_matrix
    assert first is second
    assert first.shape == (6, 6)


def test_solid_material_rejects_invalid_values():
    with pytest.raises(ValueError):
        SolidMaterial(E=0.0, nu=0.3)
    with pytest.raises(ValueError):
        SolidMaterial(E=1.0, nu=0.5)


def test_nonlinear_solid_material_returns_state_dependent_tangent():
    material = NonlinearSolidMaterial(E=1000.0, nu=0.25, hardening=1.0e6)
    strain = np.array([1.0e-2, 0.0, 0.0, 0.0, 0.0, 0.0])
    stress, tangent = material.stress_tangent(strain)
    linear_stress = material.elasticity_matrix @ strain
    assert stress[0] > linear_stress[0]
    assert tangent.shape == (6, 6)
    assert np.allclose(tangent, tangent.T)


def test_von_mises_elastoplastic_material_stays_elastic_below_yield():
    material = VonMisesElastoplasticMaterial(E=1000.0, nu=0.25, yield_stress=100.0, hardening_modulus=50.0)
    strain = np.array([1.0e-4, 0.0, 0.0, 0.0, 0.0, 0.0])
    stress, tangent = material.stress_tangent(strain)
    state = material.internal_state(strain)
    assert state["elastic"] is True
    assert state["equivalent_plastic_strain"] == 0.0
    assert np.allclose(stress, material.elasticity_matrix @ strain)
    assert np.allclose(tangent, material.elasticity_matrix)


def test_von_mises_elastoplastic_material_returns_plastic_state():
    material = VonMisesElastoplasticMaterial(E=1000.0, nu=0.25, yield_stress=5.0, hardening_modulus=100.0)
    strain = np.array([8.0e-2, 0.0, 0.0, 0.0, 0.0, 0.0])
    stress, tangent = material.stress_tangent(strain)
    state = material.internal_state(strain)
    assert state["elastic"] is False
    assert state["equivalent_plastic_strain"] > 0.0
    assert state["plastic_multiplier"] > 0.0
    assert state["yield_function"] == 0.0
    assert np.linalg.norm(stress) < np.linalg.norm(material.elasticity_matrix @ strain)
    assert tangent.shape == (6, 6)
    assert np.allclose(tangent, tangent.T)


def test_von_mises_elastoplastic_material_accumulates_path_state():
    material = VonMisesElastoplasticMaterial(E=1000.0, nu=0.25, yield_stress=5.0, hardening_modulus=100.0)
    first_strain = np.array([4.0e-2, 0.0, 0.0, 0.0, 0.0, 0.0])
    second_strain = np.array([8.0e-2, 0.0, 0.0, 0.0, 0.0, 0.0])
    _, _, first = material.stress_tangent_state(first_strain, material.initial_state())
    _, _, second = material.stress_tangent_state(second_strain, first)
    assert second["equivalent_plastic_strain"] > first["equivalent_plastic_strain"]
    assert second["yield_stress"] > first["yield_stress"]
    assert np.linalg.norm(second["plastic_strain"]) > np.linalg.norm(first["plastic_strain"])
