import numpy as np
import pytest

from solveur.core.model import FiniteElementModel
from solveur.io.schema import JsonSchemaValidator
from solveur.materials.composite import OrthotropicLamina
from solveur.materials.factory import MaterialFactory
from solveur.mesh.validation import MeshValidator


def lamina() -> OrthotropicLamina:
    return OrthotropicLamina(E1=135.0e9, E2=10.0e9, nu12=0.3, G12=5.0e9, density=1600.0)


def test_reduced_stiffness_matches_orthotropic_plane_stress_formula():
    material = lamina()
    denominator = 1.0 - material.nu12 * material.nu21
    expected = np.array(
        [
            [material.E1 / denominator, material.nu12 * material.E2 / denominator, 0.0],
            [material.nu12 * material.E2 / denominator, material.E2 / denominator, 0.0],
            [0.0, 0.0, material.G12],
        ]
    )
    assert material.nu21 == pytest.approx(material.nu12 * material.E2 / material.E1)
    assert np.allclose(material.reduced_stiffness, expected)
    assert np.all(np.linalg.eigvalsh(material.reduced_stiffness) > 0.0)


def test_qbar_at_zero_and_ninety_degrees_has_expected_axes():
    material = lamina()
    q0 = material.transformed_stiffness(0.0)
    q90 = material.transformed_stiffness(90.0)
    assert np.allclose(q0, material.reduced_stiffness, rtol=0.0, atol=1.0e-5)
    assert q90[0, 0] == pytest.approx(q0[1, 1])
    assert q90[1, 1] == pytest.approx(q0[0, 0])
    assert q90[0, 1] == pytest.approx(q0[0, 1])
    assert q90[2, 2] == pytest.approx(q0[2, 2])
    assert np.linalg.norm(q90[[0, 1], 2]) <= 1.0e-5


def test_plus_minus_45_degrees_reverse_only_extension_shear_couplings():
    material = lamina()
    plus = material.transformed_stiffness(45.0)
    minus = material.transformed_stiffness(-45.0)
    assert np.allclose(plus[:2, :2], minus[:2, :2])
    assert plus[2, 2] == pytest.approx(minus[2, 2])
    assert plus[0, 2] == pytest.approx(-minus[0, 2])
    assert plus[1, 2] == pytest.approx(-minus[1, 2])


@pytest.mark.parametrize("angle", [0.0, 17.0, 45.0, 90.0, -33.0])
def test_transformed_law_preserves_strain_energy(angle: float):
    material = lamina()
    strain = np.array([2.0e-4, -0.8e-4, 1.3e-4])
    local_strain = material.strain_in_material_axes(strain, angle)
    global_stress = material.stress_in_element_axes(strain, angle)
    local_energy = 0.5 * local_strain @ material.reduced_stiffness @ local_strain
    global_energy = 0.5 * strain @ global_stress
    assert global_energy == pytest.approx(local_energy, rel=1.0e-13)
    assert np.allclose(material.transformed_stiffness(angle), material.transformed_stiffness(angle).T)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"E1": 0.0},
        {"E2": -1.0},
        {"G12": 0.0},
        {"density": -1.0},
        {"nu12": float("nan")},
        {"E1": 1.0, "E2": 10.0, "nu12": 1.0},
    ],
)
def test_invalid_lamina_constants_are_rejected(kwargs: dict[str, float]):
    data = {"E1": 135.0e9, "E2": 10.0e9, "nu12": 0.3, "G12": 5.0e9, "density": 0.0}
    data.update(kwargs)
    with pytest.raises(ValueError):
        OrthotropicLamina(**data)


def test_factory_and_strict_schema_accept_the_experimental_material_definition():
    definition = {
        "type": "orthotropic_lamina",
        "E1": 135.0e9,
        "E2": 10.0e9,
        "nu12": 0.3,
        "G12": 5.0e9,
        "density": 1600.0,
    }
    assert isinstance(MaterialFactory.create(definition), OrthotropicLamina)
    model = {
        "nodes": [[0.0, 0.0, 0.0]],
        "elements": [{"type": "MITC4", "nodes": [0, 0, 0, 0], "material": "ply"}],
        "materials": {"ply": definition},
    }
    JsonSchemaValidator().validate(model)


def test_invalid_angle_and_strain_are_rejected():
    material = lamina()
    with pytest.raises(ValueError, match="angle"):
        material.transformed_stiffness(float("inf"))
    with pytest.raises(ValueError, match="strain"):
        material.stress_in_element_axes(np.zeros(2), 0.0)


def test_mitc4_rejects_lamina_until_multilayer_element_is_available():
    model = FiniteElementModel.from_raw(
        nodes=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]],
        elements=[{"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "ply"}],
        materials={
            "ply": {
                "type": "orthotropic_lamina",
                "E1": 135.0e9,
                "E2": 10.0e9,
                "nu12": 0.3,
                "G12": 5.0e9,
            }
        },
    )
    report = MeshValidator().validate(model)
    assert report.status == "FAIL"
    assert any("orthotropic_lamina" in error and "shell_isotropic" in error for error in report.errors)
