"""Tests for vectorized total-Lagrangian TET4 assembly."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.elements.solid.tet4_total_lagrangian import TotalLagrangianTet4Kernel
from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.materials.solid import SolidMaterial
from solveur.verification.tet4_total_lagrangian_assembly import _element_dofs, _structured_tet4_mesh


def test_vectorized_assembly_matches_scalar_kernel():
    nodes, elements = _structured_tet4_mesh(2, 1, 1, 2.0, 0.5, 0.5)
    material = SolidMaterial(E=3.0e6, nu=0.27)
    assembly = TotalLagrangianTet4Assembly(nodes, elements, material)
    kernel = TotalLagrangianTet4Kernel(material)
    rng = np.random.default_rng(20260718)
    displacement = 2.0e-3 * rng.standard_normal(assembly.ndof)

    force, tangent = assembly.assemble(displacement)
    expected_force = np.zeros(assembly.ndof)
    expected_tangent = np.zeros((assembly.ndof, assembly.ndof))
    for element in elements:
        dofs = _element_dofs(element)
        local_force, local_tangent = kernel.internal_force_and_tangent(nodes[element], displacement[dofs])
        expected_force[dofs] += local_force
        expected_tangent[np.ix_(dofs, dofs)] += local_tangent

    assert tangent is not None
    np.testing.assert_allclose(force, expected_force, rtol=2.0e-13, atol=1.0e-9)
    np.testing.assert_allclose(tangent.toarray(), expected_tangent, rtol=2.0e-13, atol=1.0e-8)


def test_vectorized_energy_and_determinants_match_scalar_kernel():
    nodes, elements = _structured_tet4_mesh(2, 1, 1, 2.0, 0.5, 0.5)
    material = SolidMaterial(E=1.0e6, nu=0.3)
    assembly = TotalLagrangianTet4Assembly(nodes, elements, material)
    kernel = TotalLagrangianTet4Kernel(material)
    deformation = np.array([[1.03, 0.02, 0.0], [0.01, 0.98, 0.0], [0.0, 0.01, 1.01]])
    displacement = (nodes @ (deformation - np.eye(3)).T).reshape(-1)
    expected_energy = sum(
        kernel.strain_energy(nodes[element], displacement[_element_dofs(element)]) for element in elements
    )

    np.testing.assert_allclose(assembly.strain_energy(displacement), expected_energy, rtol=1.0e-13)
    np.testing.assert_allclose(assembly.deformation_determinants(displacement), np.linalg.det(deformation))


def test_element_states_match_finite_strain_identities():
    nodes, elements = _structured_tet4_mesh(2, 1, 1, 2.0, 0.5, 0.5)
    material = SolidMaterial(E=1.0e6, nu=0.3)
    assembly = TotalLagrangianTet4Assembly(nodes, elements, material)
    deformation = np.array([[1.08, 0.04, 0.0], [0.01, 0.97, 0.02], [0.0, 0.0, 1.03]])
    displacement = (nodes @ (deformation - np.eye(3)).T).reshape(-1)
    states = assembly.element_states(displacement)
    green = 0.5 * (deformation.T @ deformation - np.eye(3))
    lam, mu = assembly.lame_constants
    second_piola = lam * np.trace(green) * np.eye(3) + 2.0 * mu * green
    cauchy = deformation @ second_piola @ deformation.T / np.linalg.det(deformation)

    count = elements.shape[0]
    np.testing.assert_allclose(
        states["deformation_gradient"], np.broadcast_to(deformation, (count, 3, 3)), rtol=1.0e-14
    )
    np.testing.assert_allclose(
        states["green_lagrange_strain"], np.broadcast_to(green, (count, 3, 3)), rtol=1.0e-14
    )
    np.testing.assert_allclose(
        states["second_piola_stress"], np.broadcast_to(second_piola, (count, 3, 3)), rtol=1.0e-13
    )
    np.testing.assert_allclose(
        states["cauchy_stress"], np.broadcast_to(cauchy, (count, 3, 3)), rtol=1.0e-13
    )
    np.testing.assert_allclose(
        states["strain_energy_density"], 0.5 * np.sum(green * second_piola), rtol=1.0e-13
    )
    np.testing.assert_allclose(states["det_f"], np.linalg.det(deformation), rtol=1.0e-14)


def test_vectorized_force_only_matches_full_assembly():
    nodes, elements = _structured_tet4_mesh(2, 1, 1, 2.0, 0.5, 0.5)
    assembly = TotalLagrangianTet4Assembly(nodes, elements, SolidMaterial(E=1.0e6, nu=0.3))
    displacement = np.zeros(assembly.ndof)

    force_only, absent_tangent = assembly.assemble(displacement, tangent_required=False)
    force_full, _ = assembly.assemble(displacement)

    np.testing.assert_array_equal(force_only, force_full)
    assert absent_tangent is None


@pytest.mark.parametrize(
    ("nodes", "elements", "message"),
    [
        (np.zeros((4, 2)), np.array([[0, 1, 2, 3]]), "nodes"),
        (np.zeros((4, 3)), np.array([[0, 1, 2, 4]]), "node index"),
        (np.zeros((4, 3)), np.array([[0, 1, 1, 3]]), "distinct"),
    ],
)
def test_vectorized_assembly_rejects_invalid_mesh(nodes, elements, message):
    with pytest.raises(ValueError, match=message):
        TotalLagrangianTet4Assembly(nodes, elements, SolidMaterial(E=1.0e6, nu=0.3))
