from __future__ import annotations

import numpy as np
import pytest

from mitc4.material import ShellMaterial

from solveur.elements.shell.mitc3 import (
    EXPANDED_DOF_COUNT,
    RETAINED_DOF_COUNT,
    Mitc3ShellElement,
    triangle_rule_7,
)
from solveur.elements.shell.mitc3_condensation import condense_matrix, condensation_transform
from solveur.materials.composite import OrthotropicLamina
from solveur.materials.laminate import ClassicalLaminate, LaminaPly, LaminateShellMaterial


COORDS = np.array([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.2, 1.0, 0.0]])


def material(*, thickness: float = 0.02, density: float = 2700.0) -> ShellMaterial:
    return ShellMaterial(E=70.0e9, nu=0.3, t=thickness, density=density)


def test_shapes_partition_unity_and_bubble_vanishes_on_edges() -> None:
    element = Mitc3ShellElement(material())
    values, derivatives = element.shape_functions(0.2, 0.3)
    rotations, rotation_derivatives = element.rotation_shape_functions(0.2, 0.3)
    assert np.sum(values) == pytest.approx(1.0)
    assert np.sum(derivatives, axis=0) == pytest.approx([0.0, 0.0])
    assert np.sum(rotations) == pytest.approx(1.0)
    assert np.sum(rotation_derivatives, axis=0) == pytest.approx([0.0, 0.0])
    for point in ((0.0, 0.2), (0.4, 0.0), (0.4, 0.6)):
        edge_rotations, _ = element.rotation_shape_functions(*point)
        assert edge_rotations[3] == pytest.approx(0.0, abs=1.0e-14)


def test_seven_point_rule_integrates_reference_area_and_quadratic() -> None:
    rule = triangle_rule_7()
    assert len(rule) == 7
    assert sum(weight for _, _, weight in rule) == pytest.approx(0.5)
    integral_r2 = sum(weight * r**2 for r, _, weight in rule)
    assert integral_r2 == pytest.approx(1.0 / 12.0)


def test_stiffness_is_symmetric_finite_and_has_six_rigid_modes() -> None:
    stiffness = Mitc3ShellElement(material()).stiffness(COORDS)
    assert stiffness.shape == (RETAINED_DOF_COUNT, RETAINED_DOF_COUNT)
    assert np.all(np.isfinite(stiffness))
    assert stiffness == pytest.approx(stiffness.T, rel=0.0, abs=1.0e-8)
    eigenvalues = np.linalg.eigvalsh(stiffness)
    scale = float(np.max(np.abs(eigenvalues)))
    assert np.count_nonzero(np.abs(eigenvalues) <= 1.0e-10 * scale) == 6
    assert eigenvalues[6] > 0.0


def test_rigid_translation_and_rotation_produce_no_internal_force() -> None:
    element = Mitc3ShellElement(material())
    stiffness = element.stiffness(COORDS)
    displacement = np.zeros(18)
    translation = np.array([0.2, -0.1, 0.4])
    omega = np.array([0.03, -0.02, 0.04])
    for node, position in enumerate(COORDS):
        displacement[6 * node : 6 * node + 3] = translation + np.cross(omega, position)
        displacement[6 * node + 3 : 6 * node + 6] = omega
    residual = stiffness @ displacement
    assert np.linalg.norm(residual) <= 2.0e-12 * np.linalg.norm(stiffness) * np.linalg.norm(displacement)


def test_membrane_affine_field_is_recovered_exactly() -> None:
    element = Mitc3ShellElement(material())
    displacement = np.zeros(18)
    for node, (x, y, _) in enumerate(COORDS):
        displacement[6 * node] = 2.0e-4 * x - 3.0e-4 * y
        displacement[6 * node + 1] = 5.0e-4 * x + 7.0e-4 * y
    strains = element.generalized_strains(COORDS, displacement)
    assert strains["membrane"] == pytest.approx([2.0e-4, 7.0e-4, 2.0e-4], abs=1.0e-14)
    assert strains["curvature"] == pytest.approx(np.zeros(3), abs=1.0e-14)


@pytest.mark.parametrize(
    "curvature",
    ([2.0e-4, 0.0, 0.0], [0.0, -3.0e-4, 0.0], [0.0, 0.0, 4.0e-4]),
)
def test_expanded_operator_reproduces_constant_bending_exactly(
    curvature: list[float],
) -> None:
    element = Mitc3ShellElement(material())
    _, local = element.project_to_local_midplane(COORDS)
    displacement = np.zeros(EXPANDED_DOF_COUNT)
    rx_values = []
    ry_values = []
    for node, (x, y) in enumerate(local):
        rx = -curvature[1] * y - 0.5 * curvature[2] * x
        ry = curvature[0] * x + 0.5 * curvature[2] * y
        displacement[6 * node + 3] = rx
        displacement[6 * node + 4] = ry
        rx_values.append(rx)
        ry_values.append(ry)
    displacement[18] = float(np.mean(rx_values))
    displacement[19] = float(np.mean(ry_values))
    for r, s in ((1.0 / 3.0, 1.0 / 3.0), (0.1, 0.2), (0.6, 0.1)):
        matrices = element.strain_matrices_local(local, r, s)
        assert matrices.bending @ displacement == pytest.approx(
            curvature,
            rel=0.0,
            abs=2.0e-13,
        )


@pytest.mark.parametrize("shear", ([2.0e-4, 0.0], [0.0, -3.0e-4], [2.0e-4, -3.0e-4]))
def test_assumed_operator_reproduces_constant_transverse_shear_exactly(
    shear: list[float],
) -> None:
    element = Mitc3ShellElement(material())
    _, local = element.project_to_local_midplane(COORDS)
    displacement = np.zeros(EXPANDED_DOF_COUNT)
    for node, (x, y) in enumerate(local):
        displacement[6 * node + 2] = shear[0] * x + shear[1] * y
    for r, s in ((1.0 / 3.0, 1.0 / 3.0), (0.1, 0.2), (0.6, 0.1)):
        matrices = element.strain_matrices_local(local, r, s)
        assert matrices.shear @ displacement == pytest.approx(
            shear,
            rel=0.0,
            abs=2.0e-13,
        )


def test_condensation_matches_full_stationary_energy() -> None:
    element = Mitc3ShellElement(material())
    _, coords_2d = element.project_to_local_midplane(COORDS)
    expanded = element._expanded_stiffness_components(coords_2d, element.material)
    full = sum(expanded.values(), start=np.zeros((EXPANDED_DOF_COUNT, EXPANDED_DOF_COUNT)))
    transform = condensation_transform(full)
    condensed = condense_matrix(full, transform)
    retained = np.linspace(-0.2, 0.3, RETAINED_DOF_COUNT)
    complete = transform @ retained
    assert retained @ condensed @ retained == pytest.approx(complete @ full @ complete, rel=1.0e-12)
    assert np.linalg.norm(full[RETAINED_DOF_COUNT:, :] @ complete) <= 1.0e-10 * np.linalg.norm(full)


def test_consistent_mass_preserves_total_translation_mass_and_is_positive_semidefinite() -> None:
    shell = material()
    mass = Mitc3ShellElement(shell).mass(COORDS)
    area = 1.0
    for component in range(3):
        rigid = np.zeros(18)
        rigid[component::6] = 1.0
        assert rigid @ mass @ rigid == pytest.approx(shell.density * shell.t * area, rel=1.0e-12)
    eigenvalues = np.linalg.eigvalsh(mass)
    assert np.min(eigenvalues) >= -1.0e-12 * np.max(eigenvalues)
    assert np.count_nonzero(np.abs(eigenvalues) <= 1.0e-12 * np.max(eigenvalues)) == 3


def test_rotation_of_geometry_preserves_stiffness_energy() -> None:
    element = Mitc3ShellElement(material())
    angle = np.deg2rad(37.0)
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
    )
    rotated_coords = COORDS @ rotation.T
    local = np.linspace(-1.0e-4, 2.0e-4, 18)
    nodal_rotation = np.zeros((18, 18))
    for node in range(3):
        nodal_rotation[6 * node : 6 * node + 3, 6 * node : 6 * node + 3] = rotation
        nodal_rotation[6 * node + 3 : 6 * node + 6, 6 * node + 3 : 6 * node + 6] = rotation
    rotated_displacement = nodal_rotation @ local
    original_energy = local @ element.stiffness(COORDS) @ local
    rotated_energy = rotated_displacement @ element.stiffness(rotated_coords) @ rotated_displacement
    assert rotated_energy == pytest.approx(original_energy, rel=2.0e-12)


def test_laminate_material_produces_coupled_symmetric_stiffness() -> None:
    lamina = OrthotropicLamina(
        E1=130.0e9,
        E2=9.0e9,
        nu12=0.28,
        G12=5.0e9,
        G13=4.0e9,
        G23=3.5e9,
        density=1550.0,
    )
    laminate = LaminateShellMaterial(
        ClassicalLaminate(
            (
                LaminaPly(lamina, 0.001, 0.0, "zero"),
                LaminaPly(lamina, 0.002, 45.0, "forty-five"),
            )
        )
    )
    components = Mitc3ShellElement(laminate).stiffness_components(COORDS)
    assert "coupling" in components
    stiffness = sum(components.values(), start=np.zeros((18, 18)))
    assert np.linalg.norm(components["coupling"]) > 0.0
    assert stiffness == pytest.approx(stiffness.T, rel=0.0, abs=1.0e-7)


@pytest.mark.parametrize(
    "coords",
    [
        np.zeros((3, 3)),
        np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]]),
    ],
)
def test_degenerate_triangles_are_rejected(coords: np.ndarray) -> None:
    with pytest.raises(ValueError, match="Degenerate"):
        Mitc3ShellElement(material()).stiffness(coords)


def test_reversed_triangle_is_valid_but_reverses_the_director() -> None:
    element = Mitc3ShellElement(material())
    reversed_coords = COORDS[[0, 2, 1]]
    assert element.local_frame(reversed_coords)[2] == pytest.approx(-element.local_frame(COORDS)[2])
    assert np.all(np.isfinite(element.stiffness(reversed_coords)))
