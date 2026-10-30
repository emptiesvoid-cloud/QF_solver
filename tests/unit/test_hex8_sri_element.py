from __future__ import annotations

import numpy as np
import pytest

from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.hex8_sri import Hex8SRIElement
from solveur.materials.solid import SolidMaterial


def unit_hex() -> np.ndarray:
    return np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
        ],
        dtype=float,
    )


def test_center_volumetric_rule_integrates_constant_over_reference_hex() -> None:
    material = SolidMaterial(E=1000.0, nu=0.3)
    coords = unit_hex()
    element = Hex8SRIElement(material)
    affine_dilatation = coords.reshape(-1)

    actual_energy = 0.5 * affine_dilatation @ (
        element.volumetric_stiffness(coords) @ affine_dilatation
    )
    bulk_modulus = material.E / (3.0 * (1.0 - 2.0 * material.nu))
    expected_energy = 0.5 * bulk_modulus * 3.0**2 * 1.0

    assert actual_energy == pytest.approx(expected_energy, rel=1.0e-12)


def center_inverted_hex() -> np.ndarray:
    return np.asarray(
        [
            [0.3786118303375649, 0.33794365221195466, 0.42655401680348193],
            [-0.3784613861721142, 0.23266423658200627, -0.46164984395051095],
            [0.5703521393625628, 0.3485196872041926, 0.14807991765051115],
            [0.9642045631424035, 1.8110152497489849, -0.7116112995267161],
            [0.66292296728633, 0.02186840147346807, 0.35707393090155326],
            [1.0933314534817564, -0.08061677568154567, 0.09426787951530469],
            [0.3526626589583648, 0.7837013591758539, 1.0261007409838427],
            [-0.2534111525347905, 0.900011663794658, 1.3762072460440296],
        ],
        dtype=float,
    )


def test_sri_affine_field_has_constant_strain_at_all_integration_points() -> None:
    coords = unit_hex()
    gradient = np.asarray(
        [[0.01, 0.02, 0.03], [0.04, 0.05, 0.06], [0.07, 0.08, 0.09]]
    )
    offset = np.asarray([0.3, -0.2, 0.7])
    displacement = np.concatenate([gradient @ point + offset for point in coords])
    expected_strain = np.asarray(
        [
            gradient[0, 0],
            gradient[1, 1],
            gradient[2, 2],
            gradient[0, 1] + gradient[1, 0],
            gradient[1, 2] + gradient[2, 1],
            gradient[0, 2] + gradient[2, 0],
        ]
    )
    points = (*Hex8Element.integration_points, (0.0, 0.0, 0.0))

    for point in points:
        b_matrix, _ = Hex8SRIElement.b_matrix(coords, point)
        np.testing.assert_allclose(b_matrix @ displacement, expected_strain, rtol=1.0e-13, atol=1.0e-14)


def test_sri_volumetric_weight_matches_analytic_and_standard_hex8_energy() -> None:
    coords = unit_hex()
    displacement = coords.reshape(-1)
    young_modulus = 1000.0

    for poisson_ratio in (0.3, 0.495, 0.4999):
        material = SolidMaterial(E=young_modulus, nu=poisson_ratio)
        sri = Hex8SRIElement(material)
        standard = Hex8Element(material)
        expected_energy = 4.5 * young_modulus / (3.0 * (1.0 - 2.0 * poisson_ratio))
        sri_energy = 0.5 * displacement @ (sri.stiffness(coords) @ displacement)
        standard_energy = 0.5 * displacement @ (standard.stiffness(coords) @ displacement)

        _, volumetric = sri._constitutive_split(material)
        b_center, determinant_center = sri.b_matrix(coords, (0.0, 0.0, 0.0))
        historical_unweighted_stiffness = determinant_center * (
            b_center.T @ volumetric @ b_center
        )
        historical_energy = 0.5 * displacement @ (
            historical_unweighted_stiffness @ displacement
        )

        assert sri.volumetric_integration_weight == 8.0
        assert np.isfinite(sri_energy)
        assert sri_energy == pytest.approx(expected_energy, rel=1.0e-12)
        assert standard_energy == pytest.approx(expected_energy, rel=1.0e-12)
        assert historical_energy == pytest.approx(expected_energy / 8.0, rel=1.0e-12)
        np.testing.assert_allclose(
            sum(sri._constitutive_split(material)),
            material.elasticity_matrix,
            rtol=1.0e-14,
            atol=1.0e-14,
        )


def test_sri_constitutive_split_remains_stable_near_incompressibility() -> None:
    for poisson_ratio in (0.3, 0.4999, 0.499999999):
        material = SolidMaterial(E=1000.0, nu=poisson_ratio)
        deviatoric, volumetric = Hex8SRIElement._constitutive_split(material)
        shear_modulus = material.E / (2.0 * (1.0 + material.nu))
        expected_deviatoric = np.zeros((6, 6), dtype=float)
        expected_deviatoric[:3, :3] = 2.0 * shear_modulus * (
            np.eye(3) - np.ones((3, 3)) / 3.0
        )
        expected_deviatoric[3:, 3:] = shear_modulus * np.eye(3)

        np.testing.assert_allclose(deviatoric, expected_deviatoric, rtol=1.0e-14, atol=1.0e-12)
        np.testing.assert_allclose(
            deviatoric + volumetric,
            material.elasticity_matrix,
            rtol=1.0e-14,
            atol=1.0e-12,
        )


def test_sri_stiffness_has_six_rigid_modes_and_balanced_internal_force() -> None:
    coords = unit_hex()
    stiffness = Hex8SRIElement(SolidMaterial(E=1000.0, nu=0.3)).stiffness(coords)
    stiffness_scale = np.linalg.norm(stiffness, ord=np.inf)

    np.testing.assert_array_equal(stiffness, stiffness.T)
    rigid_modes = []
    for axis in range(3):
        mode = np.zeros(24)
        mode[axis::3] = 1.0
        rigid_modes.append(mode)
    for axis in np.eye(3):
        mode = np.zeros(24)
        for node, point in enumerate(coords):
            mode[3 * node : 3 * node + 3] = np.cross(axis, point)
        rigid_modes.append(mode)
    assert max(
        np.linalg.norm(stiffness @ mode, ord=np.inf)
        / (stiffness_scale * np.linalg.norm(mode, ord=np.inf))
        for mode in rigid_modes
    ) < 1.0e-12

    assert np.linalg.matrix_rank(stiffness) == 18

    displacement = np.linspace(-0.01, 0.02, 24)
    internal_force = (stiffness @ displacement).reshape((8, 3))
    resultant = np.sum(internal_force, axis=0)
    moment = np.sum(np.cross(coords, internal_force), axis=0)
    force_scale = np.sum(np.linalg.norm(internal_force, axis=1))
    moment_scale = np.max(np.linalg.norm(coords, axis=1)) * force_scale
    assert np.linalg.norm(resultant) / force_scale < 1.0e-12
    assert np.linalg.norm(moment) / moment_scale < 1.0e-12


def test_sri_rejects_negative_central_jacobian_missed_by_full_rule() -> None:
    coords = center_inverted_hex()
    gauss_determinants = [
        Hex8Element.jacobian_determinant(coords, point)
        for point in Hex8Element.integration_points
    ]
    center_determinant = Hex8Element.jacobian_determinant(coords, (0.0, 0.0, 0.0))

    assert min(gauss_determinants) > 0.0
    assert center_determinant < 0.0
    Hex8Element.validate_geometry(coords)
    with pytest.raises(ValueError, match="Invalid HEX8-SRI Jacobian determinant"):
        Hex8SRIElement.validate_geometry(coords)


def test_sri_rejects_nonfinite_geometry_coordinates() -> None:
    coords = unit_hex()
    coords[0, 0] = np.nan

    with pytest.raises(ValueError, match="coordinates must be finite"):
        Hex8SRIElement.validate_geometry(coords)


def test_hex8_and_sri_geometry_validation_scales_with_element_size() -> None:
    material = SolidMaterial(E=1000.0, nu=0.3)
    standard = Hex8Element(material)
    sri = Hex8SRIElement(material)
    for scale in (1.0e-6, 1.0, 1.0e6):
        coords = scale * unit_hex()

        Hex8Element.validate_geometry(coords)
        Hex8SRIElement.validate_geometry(coords)
        assert np.all(np.isfinite(standard.stiffness(coords)))
        assert np.all(np.isfinite(sri.stiffness(coords)))

        near_degenerate = unit_hex()
        near_degenerate[:, 2] *= 1.0e-15
        near_degenerate *= scale
        with pytest.raises(ValueError, match="Invalid HEX8 Jacobian determinant"):
            Hex8Element.validate_geometry(near_degenerate)
        with pytest.raises(ValueError, match="Invalid HEX8-SRI Jacobian determinant"):
            Hex8SRIElement.validate_geometry(near_degenerate)


def test_standard_hex8_rejects_nonfinite_geometry_coordinates() -> None:
    coords = unit_hex()
    coords[0, 0] = np.nan

    with pytest.raises(ValueError, match="Invalid HEX8 Jacobian determinant"):
        Hex8Element.validate_geometry(coords)
