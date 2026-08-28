import numpy as np
import pytest

from solveur.core.model import FiniteElementModel
from solveur.elements.solid.tet10 import Tet10Element
from solveur.elements.solid.quadrature import tetra_duffy_rule
from solveur.elements.solid.tet4 import Tet4Element
from solveur.materials.solid import NonlinearSolidMaterial, SolidMaterial, VonMisesElastoplasticMaterial
from solveur.post.stress import StressPostProcessor


def unit_tet10_coords():
    return np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.5, 0.0, 0.0],
            [0.5, 0.5, 0.0],
            [0.0, 0.5, 0.0],
            [0.0, 0.0, 0.5],
            [0.5, 0.0, 0.5],
            [0.0, 0.5, 0.5],
        ],
        dtype=float,
    )


def curved_tet10_coords(scale: float = 1.0) -> np.ndarray:
    coords = unit_tet10_coords()
    offsets = np.zeros_like(coords)
    offsets[4] = [0.0, 0.04, 0.01]
    offsets[5] = [0.02, 0.02, 0.03]
    offsets[6] = [0.03, 0.0, 0.01]
    offsets[7] = [0.03, 0.01, 0.0]
    offsets[8] = [0.01, 0.03, 0.02]
    offsets[9] = [0.02, 0.01, 0.03]
    return coords + scale * offsets


def test_tet10_stiffness_is_symmetric():
    element = Tet10Element(SolidMaterial(E=210.0e9, nu=0.3))
    stiffness = element.stiffness(unit_tet10_coords())
    assert stiffness.shape == (30, 30)
    assert np.allclose(stiffness, stiffness.T)


def test_tet10_has_six_rigid_body_modes():
    element = Tet10Element(SolidMaterial(E=210.0e9, nu=0.3))
    coords = unit_tet10_coords()
    stiffness = element.stiffness(coords)
    norm = max(np.linalg.norm(stiffness, ord=np.inf), 1.0)
    modes = []
    for axis in range(3):
        mode = np.zeros(30)
        mode[axis::3] = 1.0
        modes.append(mode)
    for axis in np.eye(3):
        mode = np.zeros(30)
        for i, point in enumerate(coords):
            mode[3 * i : 3 * i + 3] = np.cross(axis, point)
        modes.append(mode)
    residual = max(np.linalg.norm(stiffness @ mode, ord=np.inf) / norm for mode in modes)
    assert residual < 1.0e-10


def test_tet10_mass_and_stress_recovery():
    element = Tet10Element(SolidMaterial(E=210.0e9, nu=0.3, density=7800.0))
    coords = unit_tet10_coords()
    mass = element.mass(coords)
    assert mass.shape == (30, 30)
    assert np.allclose(mass, mass.T)
    assert np.isclose(mass.sum(), 3.0 * 7800.0 / 6.0)
    assert np.min(np.linalg.eigvalsh(mass)) > 0.0
    assert np.linalg.norm(mass[:3, 3:6]) > 0.0
    displacement = np.zeros(30)
    displacement[12] = 1.0e-4
    stress = element.stress(coords, displacement)
    assert stress.shape == (6,)
    assert Tet10Element.von_mises(stress) > 0.0


def test_tet10_curved_consistent_mass_matches_high_order_volume():
    density = 7800.0
    coords = curved_tet10_coords()
    element = Tet10Element(SolidMaterial(E=210.0e9, nu=0.3, density=density))
    mass = element.mass(coords)
    reference_volume = sum(
        weight * np.linalg.det(element.shape_derivatives_reference(point).T @ coords)
        for point, weight in tetra_duffy_rule(8)
    )

    assert np.sum(mass) / 3.0 == pytest.approx(density * reference_volume, rel=1.0e-12)
    assert np.min(np.linalg.eigvalsh(mass)) > 0.0


def test_tet10_post_processing_outputs_invariants():
    model = FiniteElementModel.from_raw(
        nodes=unit_tet10_coords().tolist(),
        elements=[{"type": "TET10", "nodes": list(range(10)), "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
    )
    dofs = model.dof_manager()
    displacement = np.zeros(dofs.ndof)
    for node, (x, _, _) in enumerate(model.nodes):
        displacement[dofs.index(node, "UX")] = 1.0e-4 * x
    result = StressPostProcessor().element_results(model, dofs, displacement)[0]
    assert result["type"] == "TET10"
    assert len(result["principal_stress"]) == 3
    assert len(result["deviatoric_stress"]) == 6
    assert result["von_mises"] > 0.0
    assert len(result["integration_points"]) == 4
    assert all(point["von_mises"] >= 0.0 for point in result["integration_points"])
    assert len(result["nodal_results"]) == 10
    assert result["nodal_results"][0]["method"] == "linear_extrapolation_from_hammer"


def test_tet10_sampled_jacobian_is_constant_for_straight_element():
    determinants = Tet10Element.jacobian_determinants(unit_tet10_coords())
    assert determinants.size == 35
    np.testing.assert_allclose(determinants, np.ones(35), rtol=0.0, atol=1.0e-14)


def test_tet10_auto_quadrature_selects_straight_and_curved_rules():
    straight_rule = Tet10Element.stiffness_integration_rule(unit_tet10_coords())
    curved_rule = Tet10Element.stiffness_integration_rule(curved_tet10_coords())

    assert len(straight_rule) == 4
    assert len(curved_rule) == 64
    assert np.isclose(sum(weight for _, weight in straight_rule), 1.0 / 6.0)
    assert np.isclose(sum(weight for _, weight in curved_rule), 1.0 / 6.0)


def test_tet10_curved_auto_quadrature_matches_high_order_reference():
    element = Tet10Element(SolidMaterial(E=1000.0, nu=0.25))
    coords = curved_tet10_coords()

    automatic = element.stiffness(coords)
    reference = element.stiffness(coords, quadrature_order=8)
    hammer = _tet10_stiffness_from_rule(element, coords, element.hammer_integration_rule())
    automatic_error = np.linalg.norm(automatic - reference) / np.linalg.norm(reference)
    hammer_error = np.linalg.norm(hammer - reference) / np.linalg.norm(reference)

    assert automatic_error < 1.0e-5
    assert hammer_error > 1.0e-3
    assert automatic_error < hammer_error / 100.0


def test_tet10_rejects_curved_geometry_with_nonpositive_sampled_jacobian():
    element = Tet10Element(SolidMaterial(E=1000.0, nu=0.25))
    coords = curved_tet10_coords(scale=8.0)

    with pytest.raises(ValueError, match="sampled jacobian"):
        element.stiffness(coords)


def test_tet10_patch_test_reproduces_affine_strain_and_energy():
    material = SolidMaterial(E=210.0e9, nu=0.3)
    element = Tet10Element(material)
    coords = unit_tet10_coords()
    gradient = np.array([[1.0e-3, 2.0e-4, -1.0e-4], [3.0e-4, -4.0e-4, 5.0e-5], [2.0e-4, 1.0e-4, 6.0e-4]])
    translation = np.zeros(3)
    displacement = np.concatenate([translation + gradient @ point for point in coords])
    expected = np.array(
        [gradient[0, 0], gradient[1, 1], gradient[2, 2], gradient[0, 1] + gradient[1, 0],
         gradient[1, 2] + gradient[2, 1], gradient[0, 2] + gradient[2, 0]]
    )
    for point in element.integration_points:
        b_matrix, _ = element.b_matrix(coords, point)
        np.testing.assert_allclose(b_matrix @ displacement, expected, rtol=1.0e-12, atol=1.0e-14)
    numerical_energy = 0.5 * displacement @ (element.stiffness(coords) @ displacement)
    analytic_energy = 0.5 * (1.0 / 6.0) * expected @ (material.elasticity_matrix @ expected)
    assert np.isclose(numerical_energy, analytic_energy, rtol=1.0e-11)


def test_tet10_patch_test_is_invariant_on_oblique_tetrahedron():
    element = Tet10Element(SolidMaterial(E=210.0e9, nu=0.3))
    transform = np.array([[1.2, 0.4, -0.2], [0.3, 0.9, 0.25], [0.1, -0.15, 1.1]])
    coords = unit_tet10_coords() @ transform.T + np.array([2.0, -1.0, 0.5])
    gradient = np.array([[1.0e-3, 2.0e-4, -1.0e-4], [3.0e-4, -4.0e-4, 5.0e-5], [2.0e-4, 1.0e-4, 6.0e-4]])
    displacement = np.concatenate([gradient @ point for point in coords])
    expected = np.array(
        [
            gradient[0, 0],
            gradient[1, 1],
            gradient[2, 2],
            gradient[0, 1] + gradient[1, 0],
            gradient[1, 2] + gradient[2, 1],
            gradient[0, 2] + gradient[2, 0],
        ]
    )
    for point in element.integration_points:
        b_matrix, _ = element.b_matrix(coords, point)
        np.testing.assert_allclose(b_matrix @ displacement, expected, rtol=1.0e-11, atol=1.0e-14)


def test_tet10_nodal_extrapolation_recovers_linear_stress_field():
    material = SolidMaterial(E=1000.0, nu=0.25)
    model = FiniteElementModel.from_raw(
        nodes=unit_tet10_coords().tolist(),
        elements=[{"type": "TET10", "nodes": list(range(10)), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": material.E, "nu": material.nu}},
    )
    dofs = model.dof_manager()
    displacement = np.zeros(dofs.ndof)
    for node, (x, _, _) in enumerate(model.nodes):
        displacement[dofs.index(node, "UX")] = x**2
    result = StressPostProcessor().element_results(model, dofs, displacement)[0]
    for row, (x, _, _) in zip(result["nodal_results"], model.nodes):
        expected = material.elasticity_matrix @ np.array([2.0 * x, 0.0, 0.0, 0.0, 0.0, 0.0])
        np.testing.assert_allclose(row["stress"], expected, rtol=1.0e-12, atol=1.0e-12)


def test_tet10_curved_recovery_preserves_affine_stress_field():
    coords = curved_tet10_coords()
    material = SolidMaterial(E=1000.0, nu=0.25)
    model = FiniteElementModel.from_raw(
        nodes=coords.tolist(),
        elements=[{"type": "TET10", "nodes": list(range(10)), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": material.E, "nu": material.nu}},
    )
    gradient = np.array(
        [[1.0e-3, 2.0e-4, 0.0], [1.0e-4, -4.0e-4, 3.0e-4], [0.0, 2.0e-4, 5.0e-4]]
    )
    displacement = np.concatenate([gradient @ point for point in coords])
    expected_strain = np.array([1.0e-3, -4.0e-4, 5.0e-4, 3.0e-4, 5.0e-4, 0.0])
    expected_stress = material.elasticity_matrix @ expected_strain

    result = StressPostProcessor().element_results(model, model.dof_manager(), displacement)[0]

    assert len(result["integration_points"]) == 64
    assert result["nodal_results"][0]["method"] == "linear_barycentric_least_squares"
    for row in result["nodal_results"]:
        np.testing.assert_allclose(row["stress"], expected_stress, rtol=1.0e-11, atol=1.0e-8)


def test_tet10_quadratic_field_outperforms_tet4_under_refinement():
    material = SolidMaterial(E=1000.0, nu=0.25)
    tet10 = Tet10Element(material)
    tet4_errors = []
    for size in (1.0, 0.5, 0.25):
        corner_coords = unit_tet10_coords()[:4] * size
        corner_u = np.zeros(12)
        corner_u[0::3] = corner_coords[:, 0] ** 2
        tet4_strain = Tet4Element(material).strain(corner_coords, corner_u)
        exact_centroid_strain = 0.5 * size
        tet4_errors.append(abs(tet4_strain[0] - exact_centroid_strain))

        quadratic_coords = unit_tet10_coords() * size
        quadratic_u = np.zeros(30)
        quadratic_u[0::3] = quadratic_coords[:, 0] ** 2
        tet10_strain = tet10.strain(quadratic_coords, quadratic_u)
        assert np.isclose(tet10_strain[0], exact_centroid_strain, rtol=0.0, atol=1.0e-13)
    np.testing.assert_allclose(np.asarray(tet4_errors[:-1]) / tet4_errors[1:], [2.0, 2.0])


def test_tet10_nonlinear_internal_force_and_tangent():
    element = Tet10Element(NonlinearSolidMaterial(E=1000.0, nu=0.25, hardening=1.0e6))
    coords = unit_tet10_coords()
    displacement = np.zeros(30)
    displacement[12] = 1.0e-2
    internal, tangent = element.internal_force_and_tangent(coords, displacement)
    assert internal.shape == (30,)
    assert tangent.shape == (30, 30)
    assert np.allclose(tangent, tangent.T)
    assert np.linalg.norm(internal) > 0.0


def test_tet10_code_aster_nonlinear_rule_is_explicit_and_stateful():
    element = Tet10Element(
        VonMisesElastoplasticMaterial(E=1000.0, nu=0.25, yield_stress=5.0, hardening_modulus=100.0),
        nonlinear_quadrature="code_aster_5",
    )
    rule = element.nonlinear_integration_rule()

    assert len(rule) == 5
    assert element.nonlinear_integration_point_count == 5
    assert np.isclose(sum(weight for _, weight in rule), 1.0 / 6.0)
    assert rule[0][0] == (0.25, 0.25, 0.25, 0.25)

    internal, tangent, states = element.internal_force_tangent_state(
        unit_tet10_coords(), np.zeros(30)
    )
    assert internal.shape == (30,)
    assert tangent.shape == (30, 30)
    assert len(states) == 5


def test_tet10_rejects_unknown_nonlinear_quadrature():
    with pytest.raises(ValueError, match="Unsupported TET10 nonlinear quadrature"):
        Tet10Element(SolidMaterial(E=1000.0, nu=0.25), nonlinear_quadrature="unknown")


def test_tet10_rejects_inverted_element():
    element = Tet10Element(SolidMaterial(E=210.0e9, nu=0.3))
    coords = unit_tet10_coords()
    with pytest.raises(ValueError):
        element.stiffness(coords[[0, 2, 1, 3, 6, 5, 4, 7, 9, 8]])


def _tet10_stiffness_from_rule(
    element: Tet10Element,
    coords: np.ndarray,
    rule: tuple[tuple[tuple[float, float, float, float], float], ...],
) -> np.ndarray:
    stiffness = np.zeros((30, 30), dtype=float)
    for point, weight in rule:
        b_matrix, determinant = element.b_matrix(coords, point)
        stiffness += weight * determinant * (
            b_matrix.T @ element.material.elasticity_matrix @ b_matrix
        )
    return stiffness
