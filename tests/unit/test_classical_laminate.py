import numpy as np
import pytest

from solveur.materials import ClassicalLaminate, LaminaPly, OrthotropicLamina


@pytest.fixture
def material() -> OrthotropicLamina:
    return OrthotropicLamina(E1=135.0e9, E2=10.0e9, nu12=0.3, G12=5.0e9, density=1600.0)


def laminate(material: OrthotropicLamina, angles: list[float], thickness: float = 0.125e-3) -> ClassicalLaminate:
    return ClassicalLaminate(tuple(LaminaPly(material, thickness, angle, f"ply-{index + 1}") for index, angle in enumerate(angles)))


def test_single_ply_matches_closed_form_abd(material: OrthotropicLamina):
    thickness = 0.8e-3
    stack = laminate(material, [0.0], thickness)
    q = material.reduced_stiffness
    assert np.allclose(stack.interfaces, [-thickness / 2.0, thickness / 2.0])
    assert np.allclose(stack.extensional_matrix, q * thickness)
    assert np.allclose(stack.coupling_matrix, 0.0)
    assert np.allclose(stack.bending_matrix, q * thickness**3 / 12.0)
    assert stack.is_symmetric()
    assert stack.is_balanced()


def test_symmetric_cross_ply_has_zero_coupling(material: OrthotropicLamina):
    stack = laminate(material, [0.0, 90.0, 90.0, 0.0])
    assert stack.is_symmetric()
    assert stack.is_balanced()
    assert np.linalg.norm(stack.coupling_matrix) <= 1.0e-12
    assert np.allclose(stack.extensional_matrix, stack.extensional_matrix.T)
    assert np.all(np.linalg.eigvalsh(stack.stiffness_matrix) > 0.0)


def test_balanced_angle_ply_cancels_extensional_shear_coupling(material: OrthotropicLamina):
    stack = laminate(material, [45.0, -45.0, -45.0, 45.0])
    assert stack.is_symmetric()
    assert stack.is_balanced()
    assert np.linalg.norm(stack.extensional_matrix[:2, 2]) <= 1.0e-9


def test_unsymmetric_cross_ply_retains_membrane_bending_coupling(material: OrthotropicLamina):
    stack = laminate(material, [0.0, 90.0])
    assert not stack.is_symmetric()
    assert stack.is_balanced()
    assert np.linalg.norm(stack.coupling_matrix) > 0.0


def test_resultants_and_generalized_strains_are_inverse(material: OrthotropicLamina):
    stack = laminate(material, [0.0, 45.0, -45.0, 90.0])
    epsilon0 = np.array([2.0e-4, -0.5e-4, 0.8e-4])
    curvature = np.array([0.2, -0.1, 0.05])
    membrane, moment = stack.resultants(epsilon0, curvature)
    recovered_strain, recovered_curvature = stack.generalized_strains(membrane, moment)
    assert np.allclose(recovered_strain, epsilon0, rtol=1.0e-12, atol=1.0e-15)
    assert np.allclose(recovered_curvature, curvature, rtol=1.0e-12, atol=1.0e-15)


def test_ply_results_follow_linear_through_thickness_kinematics(material: OrthotropicLamina):
    stack = laminate(material, [0.0, 90.0])
    epsilon0 = np.array([1.0e-4, 2.0e-4, 0.0])
    curvature = np.array([0.3, -0.1, 0.2])
    results = stack.ply_results(epsilon0, curvature)
    assert len(results) == 6
    assert [result.location for result in results[:3]] == ["lower", "middle", "upper"]
    for result in results:
        assert np.allclose(result.strain_element, epsilon0 + result.z * curvature)
        assert np.allclose(result.stress_element, stack.plies[result.ply_index].transformed_stiffness @ result.strain_element)
        local_energy = 0.5 * result.strain_material @ result.stress_material
        global_energy = 0.5 * result.strain_element @ result.stress_element
        assert global_energy == pytest.approx(local_energy, rel=1.0e-13)


def test_membrane_bending_resultants_include_b_coupling(material: OrthotropicLamina):
    stack = laminate(material, [0.0, 90.0])
    epsilon0 = np.array([1.0e-4, 0.0, 0.0])
    curvature = np.zeros(3)
    membrane, moment = stack.resultants(epsilon0, curvature)
    assert np.allclose(membrane, stack.extensional_matrix @ epsilon0)
    assert np.allclose(moment, stack.coupling_matrix @ epsilon0)
    assert np.linalg.norm(moment) > 0.0


@pytest.mark.parametrize(
    "builder,error",
    [
        (lambda material: ClassicalLaminate(()), "at least one"),
        (lambda material: ClassicalLaminate((object(),)), "LaminaPly"),
        (lambda material: LaminaPly(material, 0.0, 0.0), "thickness"),
        (lambda material: LaminaPly(material, 1.0, float("nan")), "angle"),
        (lambda material: LaminaPly(object(), 1.0, 0.0), "OrthotropicLamina"),
    ],
)
def test_invalid_layups_are_rejected(material: OrthotropicLamina, builder, error: str):
    with pytest.raises((TypeError, ValueError), match=error):
        builder(material)


def test_invalid_generalized_vectors_are_rejected(material: OrthotropicLamina):
    stack = laminate(material, [0.0])
    with pytest.raises(ValueError, match="midplane_strain"):
        stack.resultants(np.zeros(2), np.zeros(3))
    with pytest.raises(ValueError, match="moment"):
        stack.generalized_strains(np.zeros(3), np.array([0.0, np.nan, 0.0]))
