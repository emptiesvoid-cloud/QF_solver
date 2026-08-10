from __future__ import annotations

import numpy as np
import pytest

from solveur.core.model import FiniteElementModel
from solveur.core.assembler import GlobalAssembler
from solveur.elements.solid.tet10 import Tet10Element
from solveur.elements.solid.tet4 import Tet4Element
from solveur.io.json_reader import JsonModelReader
from solveur.materials.factory import MaterialFactory
from solveur.materials.orthotropic import OrthotropicSolidMaterial, material_orientation
from solveur.materials.solid import SolidMaterial
from solveur.post.stress import StressPostProcessor


def orthotropic_material(*, orientation: np.ndarray | None = None) -> OrthotropicSolidMaterial:
    return OrthotropicSolidMaterial(
        E1=135.0e9,
        E2=10.0e9,
        E3=8.0e9,
        nu12=0.28,
        nu13=0.22,
        nu23=0.35,
        G12=5.2e9,
        G13=4.1e9,
        G23=3.3e9,
        density=1580.0,
        orientation=np.eye(3) if orientation is None else orientation,
    )


def tet4_coords() -> np.ndarray:
    return np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])


def tet10_coords() -> np.ndarray:
    corners = tet4_coords()
    edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
    return np.vstack((corners, [0.5 * (corners[a] + corners[b]) for a, b in edges]))


def affine_displacement(coords: np.ndarray, gradient: np.ndarray) -> np.ndarray:
    return (np.asarray(coords) @ np.asarray(gradient).T).reshape(-1)


def engineering_strain(gradient: np.ndarray) -> np.ndarray:
    return np.array(
        [
            gradient[0, 0],
            gradient[1, 1],
            gradient[2, 2],
            gradient[0, 1] + gradient[1, 0],
            gradient[1, 2] + gradient[2, 1],
            gradient[0, 2] + gradient[2, 0],
        ]
    )


def test_orthotropic_compliance_is_symmetric_positive_and_reciprocal() -> None:
    material = orthotropic_material()
    compliance = material.compliance_matrix
    assert np.allclose(compliance, compliance.T, rtol=0.0, atol=1.0e-18)
    assert np.min(np.linalg.eigvalsh(compliance)) > 0.0
    assert material.nu21 == pytest.approx(material.nu12 * material.E2 / material.E1)
    assert material.nu31 == pytest.approx(material.nu13 * material.E3 / material.E1)
    assert material.nu32 == pytest.approx(material.nu23 * material.E3 / material.E2)


@pytest.mark.parametrize("component", range(6))
def test_orthotropic_material_recovers_unit_stress_states(component: int) -> None:
    material = orthotropic_material()
    target_stress = np.zeros(6)
    target_stress[component] = 17.0e6
    strain = material.compliance_matrix @ target_stress
    stress, tangent = material.stress_tangent(strain)
    assert np.allclose(stress, target_stress, rtol=1.0e-12, atol=1.0e-7)
    assert np.allclose(tangent, tangent.T, rtol=0.0, atol=1.0e-5)


def test_rotated_material_preserves_energy_and_tensor_transformations() -> None:
    angle = np.deg2rad(31.0)
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]])
    material = orthotropic_material(orientation=rotation)
    global_strain = np.array([2.0e-4, -1.0e-4, 0.7e-4, 1.3e-4, -0.4e-4, 0.9e-4])
    global_stress = material.elasticity_matrix @ global_strain
    local_strain = material.strain_material_axes(global_strain)
    local_stress = material.stress_material_axes(global_stress)
    assert np.allclose(local_stress, material.material_elasticity_matrix @ local_strain, rtol=1.0e-12)
    assert 0.5 * global_stress @ global_strain == pytest.approx(
        0.5 * local_stress @ local_strain,
        rel=1.0e-12,
    )
    assert np.allclose(material.strain_global_axes(local_strain), global_strain, atol=1.0e-15)
    assert np.allclose(material.stress_global_axes(local_stress), global_stress, rtol=1.0e-12)


def test_isotropic_constants_are_orientation_invariant() -> None:
    young = 72.0e9
    poisson = 0.29
    shear = young / (2.0 * (1.0 + poisson))
    basis = material_orientation(e1=[1.0, 1.0, 0.3], e2_hint=[-0.2, 0.4, 1.0])
    orthotropic = OrthotropicSolidMaterial(
        young, young, young, poisson, poisson, poisson, shear, shear, shear, orientation=basis
    )
    isotropic = SolidMaterial(young, poisson)
    assert np.allclose(orthotropic.elasticity_matrix, isotropic.elasticity_matrix, rtol=2.0e-15, atol=2.0e-5)


def test_cylindrical_orientation_field_rotates_material_axes_between_curved_elements() -> None:
    data = {
        "type": "orthotropic_3d",
        "E1": 135.0e9,
        "E2": 10.0e9,
        "E3": 8.0e9,
        "nu12": 0.28,
        "nu13": 0.22,
        "nu23": 0.35,
        "G12": 5.2e9,
        "G13": 4.1e9,
        "G23": 3.3e9,
        "orientation_field": {"type": "cylindrical_tangent", "origin": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, 1.0]},
    }
    radial_x = np.array([[1.0, -0.1, 0.0], [1.0, 0.1, 0.0], [1.0, 0.0, 0.1], [1.0, 0.0, -0.1]])
    radial_y = np.array([[-0.1, 1.0, 0.0], [0.1, 1.0, 0.0], [0.0, 1.0, 0.1], [0.0, 1.0, -0.1]])
    material_x = MaterialFactory.create(data, coordinates=radial_x)
    material_y = MaterialFactory.create(data, coordinates=radial_y)
    assert isinstance(material_x, OrthotropicSolidMaterial)
    assert isinstance(material_y, OrthotropicSolidMaterial)
    assert np.allclose(material_x.orientation[:, 0], [0.0, 1.0, 0.0], atol=1.0e-14)
    assert np.allclose(material_y.orientation[:, 0], [-1.0, 0.0, 0.0], atol=1.0e-14)
    assert np.allclose(material_x.orientation[:, 1], [0.0, 0.0, 1.0], atol=1.0e-14)
    assert np.linalg.norm(material_x.elasticity_matrix - material_y.elasticity_matrix) > 1.0e6


def test_cylindrical_orientation_field_is_used_during_global_assembly() -> None:
    material = {
        "type": "orthotropic_3d",
        "E1": 135.0e9,
        "E2": 10.0e9,
        "E3": 8.0e9,
        "nu12": 0.28,
        "nu13": 0.22,
        "nu23": 0.35,
        "G12": 5.2e9,
        "G13": 4.1e9,
        "G23": 3.3e9,
        "orientation_field": {"type": "cylindrical_tangent", "origin": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, 1.0]},
    }
    first = tet4_coords() + np.array([2.0, 0.0, 0.0])
    second = tet4_coords() + np.array([0.0, 2.0, 0.0])
    model = FiniteElementModel.from_raw(
        nodes=np.vstack((first, second)).tolist(),
        elements=[
            {"type": "TET4", "nodes": [0, 1, 2, 3], "material": "ortho"},
            {"type": "TET4", "nodes": [4, 5, 6, 7], "material": "ortho"},
        ],
        materials={"ortho": material},
    )
    stiffness = GlobalAssembler().assemble_stiffness(model, model.dof_manager())
    assert stiffness.shape == (24, 24)
    assert np.all(np.isfinite(stiffness.data))
    assert np.allclose(stiffness.toarray(), stiffness.toarray().T, rtol=0.0, atol=1.0e-5)


@pytest.mark.parametrize("element_type", ["TET4", "TET10"])
def test_orthotropic_tetrahedra_reproduce_affine_patch(element_type: str) -> None:
    material = orthotropic_material(orientation=material_orientation(e1=[1.0, 1.0, 0.0], e2_hint=[0.0, 0.0, 1.0]))
    gradient = np.array([[2.0e-4, 3.0e-5, -2.0e-5], [4.0e-5, -1.0e-4, 5.0e-5], [1.0e-5, 6.0e-5, 0.5e-4]])
    coords = tet4_coords() if element_type == "TET4" else tet10_coords()
    element = Tet4Element(material) if element_type == "TET4" else Tet10Element(material)
    displacement = affine_displacement(coords, gradient)
    expected = engineering_strain(gradient)
    assert np.allclose(element.strain(coords, displacement), expected, rtol=0.0, atol=1.0e-15)
    assert np.allclose(element.stress(coords, displacement), material.elasticity_matrix @ expected, rtol=1.0e-12)
    stiffness = element.stiffness(coords)
    assert np.allclose(stiffness, stiffness.T, rtol=0.0, atol=1.0e-5)


def test_json_factory_and_postprocessing_preserve_material_axes() -> None:
    raw_material = {
        "type": "orthotropic_3d",
        "E1": 135.0e9,
        "E2": 10.0e9,
        "E3": 8.0e9,
        "nu12": 0.28,
        "nu13": 0.22,
        "nu23": 0.35,
        "G12": 5.2e9,
        "G13": 4.1e9,
        "G23": 3.3e9,
        "e1": [1.0, 1.0, 0.0],
        "e2_hint": [0.0, 0.0, 1.0],
    }
    model = FiniteElementModel.from_raw(
        nodes=tet4_coords().tolist(),
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "ortho"}],
        materials={"ortho": raw_material},
    )
    material = MaterialFactory.create(raw_material)
    assert isinstance(material, OrthotropicSolidMaterial)
    displacement = affine_displacement(tet4_coords(), np.diag([1.0e-4, 2.0e-4, -0.5e-4]))
    result = StressPostProcessor().element_results(model, model.dof_manager(), displacement)[0]
    assert len(result["material_stress"]) == 6
    assert len(result["material_strain"]) == 6
    assert np.asarray(result["material_orientation"]).shape == (3, 3)


def test_schema_rejects_incomplete_or_conflicting_orientation() -> None:
    base = {
        "type": "orthotropic_3d",
        "E1": 10.0,
        "E2": 8.0,
        "E3": 6.0,
        "nu12": 0.2,
        "nu13": 0.1,
        "nu23": 0.15,
        "G12": 3.0,
        "G13": 2.5,
        "G23": 2.0,
        "e1": [1.0, 0.0, 0.0],
    }
    with pytest.raises(ValueError, match="e1 and e2_hint"):
        JsonModelReader().from_dict(
            {
                "nodes": tet4_coords().tolist(),
                "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "ortho"}],
                "materials": {"ortho": base},
            }
        )
    field_conflict = {
        **base,
        "e2_hint": [0.0, 1.0, 0.0],
        "orientation_field": {"type": "cylindrical_tangent", "origin": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, 1.0]},
    }
    with pytest.raises(ValueError, match="only one of orientation"):
        JsonModelReader().from_dict(
            {
                "nodes": tet4_coords().tolist(),
                "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "ortho"}],
                "materials": {"ortho": field_conflict},
            }
        )


def test_material_rejects_non_positive_compliance_and_left_handed_basis() -> None:
    with pytest.raises(ValueError, match="positive definite"):
        OrthotropicSolidMaterial(10.0, 1.0, 1.0, 4.0, 0.1, 0.1, 1.0, 1.0, 1.0)
    with pytest.raises(ValueError, match="right-handed"):
        orthotropic_material(orientation=np.diag([1.0, 1.0, -1.0]))


def test_homogenized_composite_requires_and_preserves_provenance() -> None:
    data = {
        "type": "composite_orthotropic_3d",
        "E1": 50.0,
        "E2": 20.0,
        "E3": 15.0,
        "nu12": 0.2,
        "nu13": 0.15,
        "nu23": 0.25,
        "G12": 8.0,
        "G13": 7.0,
        "G23": 6.0,
    }
    with pytest.raises(ValueError, match="requires provenance"):
        MaterialFactory.create(data)
    data.update({"homogenization": "periodic_RVE", "provenance": {"dataset": "coupon-v1"}})
    material = MaterialFactory.create(data)
    assert isinstance(material, OrthotropicSolidMaterial)
    assert material.material_type == "composite_orthotropic_3d"
    assert material.metadata["homogenization"] == "periodic_RVE"
