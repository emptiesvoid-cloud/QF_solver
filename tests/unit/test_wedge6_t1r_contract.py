"""T1-R checks for the inactive WEDGE6 formulation and oracle contracts."""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pytest

from solveur.mesh.quality_contract import (
    INVALID,
    VALID,
    VALID_WITH_WARNING,
    wedge6_jacobian_certificate,
    wedge6_quality_contract,
)


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "qualification" / "0_2_7" / "wedge6_formulation_contract.json"
MAPPING_PATH = ROOT / "qualification" / "0_2_7" / "external_oracles" / "wedge6" / "mapping.json"
FIXTURE_PATH = ROOT / "qualification" / "0_2_7" / "wedge6_mapping_fixture.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


CONTRACT = read_json(CONTRACT_PATH)
MAPPING = read_json(MAPPING_PATH)
FIXTURE = read_json(FIXTURE_PATH)
REFERENCE_NODES = np.asarray([CONTRACT["reference_nodes"][str(i)] for i in range(1, 7)], dtype=float)
PHYSICAL_NODES = np.asarray([FIXTURE["coordinates"][str(i)] for i in range(1, 7)], dtype=float)

TERRA_ADVERSARIAL_NODES = np.asarray(
    (
        (0.66226, 0.05390, -1.15307),
        (1.11239, 0.25161, -1.17402),
        (-0.54385, 1.50167, -1.17947),
        (-0.18379, 1.01123, 1.43388),
        (1.18110, -0.62849, 1.14978),
        (0.30332, 0.93006, -0.04914),
    ),
    dtype=float,
)


def shape_values(r: float, s: float, t: float) -> np.ndarray:
    lower = 0.5 * (1.0 - t) * np.asarray([1.0 - r - s, r, s])
    upper = 0.5 * (1.0 + t) * np.asarray([1.0 - r - s, r, s])
    return np.concatenate((lower, upper))


def shape_gradients(r: float, s: float, t: float) -> np.ndarray:
    return np.asarray(
        [
            [-0.5 * (1.0 - t), -0.5 * (1.0 - t), -0.5 * (1.0 - r - s)],
            [0.5 * (1.0 - t), 0.0, -0.5 * r],
            [0.0, 0.5 * (1.0 - t), -0.5 * s],
            [-0.5 * (1.0 + t), -0.5 * (1.0 + t), 0.5 * (1.0 - r - s)],
            [0.5 * (1.0 + t), 0.0, 0.5 * r],
            [0.0, 0.5 * (1.0 + t), 0.5 * s],
        ]
    )


def jacobian(r: float, s: float, t: float) -> np.ndarray:
    return PHYSICAL_NODES.T @ shape_gradients(r, s, t)


def face_surface_vector(face_nodes: list[int]) -> np.ndarray:
    points = PHYSICAL_NODES[np.asarray(face_nodes) - 1]
    if len(points) == 3:
        return np.cross(points[1] - points[0], points[2] - points[0]) / 2.0
    return (
        np.cross(points[1] - points[0], points[2] - points[0])
        + np.cross(points[2] - points[0], points[3] - points[0])
    ) / 2.0


def integrate_face(face_nodes: list[int], pressure: float) -> tuple[np.ndarray, np.ndarray]:
    points = PHYSICAL_NODES[np.asarray(face_nodes) - 1]
    if len(points) == 3:
        surface_vector = np.cross(points[1] - points[0], points[2] - points[0]) / 2.0
        location = points.mean(axis=0)
        return pressure * surface_vector, np.cross(location, pressure * surface_vector)
    gauss = (-1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0))
    force = np.zeros(3)
    moment = np.zeros(3)
    for u in gauss:
        for v in gauss:
            shape = 0.25 * np.asarray([(1 - u) * (1 - v), (1 + u) * (1 - v), (1 + u) * (1 + v), (1 - u) * (1 + v)])
            d_du = 0.25 * np.asarray([-(1 - v), 1 - v, 1 + v, -(1 + v)])
            d_dv = 0.25 * np.asarray([-(1 - u), -(1 + u), 1 + u, 1 - u])
            location = shape @ points
            surface_vector = np.cross(d_du @ points, d_dv @ points)
            force += pressure * surface_vector
            moment += np.cross(location, pressure * surface_vector)
    return force, moment


def test_shape_functions_cover_declared_formulas_and_identities() -> None:
    assert len(CONTRACT["shape_functions"]) == 6
    assert CONTRACT["identities"]["partition_of_unity"] == "sum(Ni) = 1"
    points = [(0.0, 0.0, -1.0), (1.0, 0.0, -1.0), (0.0, 1.0, -1.0)]
    points += [(0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (0.0, 1.0, 1.0)]
    for index, point in enumerate(points):
        values = shape_values(*point)
        assert values[index] == pytest.approx(1.0)
        assert np.delete(values, index) == pytest.approx(0.0)
    for r, s, t in [(0.12, 0.23, -0.8), (0.2, 0.1, 0.0), (0.1, 0.7, 0.75)]:
        assert shape_values(r, s, t).sum() == pytest.approx(1.0)
        assert shape_gradients(r, s, t).sum(axis=0) == pytest.approx(0.0)


def test_affine_mapping_and_jacobian_are_reproduced() -> None:
    affine = np.asarray(FIXTURE["affine_map"]["matrix_rows"])
    offset = np.asarray(FIXTURE["affine_map"]["offset"])
    for r, s, t in [(0.15, 0.2, -0.7), (0.2, 0.3, 0.0), (0.05, 0.8, 0.9)]:
        mapped = shape_values(r, s, t) @ PHYSICAL_NODES
        assert mapped == pytest.approx(offset + affine @ np.asarray([r, s, t]))
        assert jacobian(r, s, t) == pytest.approx(affine)
        assert np.linalg.det(jacobian(r, s, t)) == pytest.approx(FIXTURE["affine_map"]["determinant"])


def test_jacobian_controls_are_not_integration_points_only() -> None:
    quality = wedge6_quality_contract()
    sampling = quality["jacobian_sampling"]
    assert sampling["integration_points_only"] is False
    assert "triangular reference vertex" in sampling["validity_controls"]
    controls = REFERENCE_NODES[:, :]
    determinants = [np.linalg.det(jacobian(r, s, t)) for r, s, t in controls]
    assert min(determinants) > 0.0
    inverted = PHYSICAL_NODES[[0, 2, 1, 3, 5, 4]]
    inverted_jacobian = inverted.T @ shape_gradients(1.0 / 6.0, 1.0 / 6.0, 0.0)
    assert np.linalg.det(inverted_jacobian) < 0.0


def test_wedge6_certificate_accepts_nominal_and_affine_skewed_prisms() -> None:
    nominal = wedge6_jacobian_certificate(REFERENCE_NODES)
    skewed = wedge6_jacobian_certificate(PHYSICAL_NODES)

    assert nominal["classification"] == VALID
    assert skewed["classification"] == VALID
    assert nominal["diagnostic_samples_are_certificate"] is False
    assert len(nominal["candidates"]) >= 6


def test_wedge6_certificate_rejects_interior_inversion_missed_by_sampling() -> None:
    certificate = wedge6_jacobian_certificate(TERRA_ADVERSARIAL_NODES)

    assert certificate["classification"] == INVALID
    assert certificate["valid"] is False
    assert certificate["minimum_detJ"] < 0.0
    assert any(0.0 < item["t"] < 1.0 for item in certificate["candidates"])


def test_wedge6_certificate_handles_near_degenerate_and_orientation_permutations() -> None:
    near_degenerate = REFERENCE_NODES.copy()
    near_degenerate[3, 2] = -1.0 + 1.0e-12
    near = wedge6_jacobian_certificate(near_degenerate)
    inverted = wedge6_jacobian_certificate(REFERENCE_NODES[[0, 2, 1, 3, 5, 4]])

    assert near["classification"] in {VALID_WITH_WARNING, INVALID}
    assert inverted["classification"] == INVALID


def test_wedge6_certificate_is_rigid_transform_and_scale_invariant() -> None:
    rotation = np.asarray(((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)))
    baseline = wedge6_jacobian_certificate(PHYSICAL_NODES)
    transformed = wedge6_jacobian_certificate((PHYSICAL_NODES @ rotation.T) + (4.0, -2.0, 7.0))
    scaled = wedge6_jacobian_certificate(PHYSICAL_NODES * 1.0e-9)

    assert transformed["classification"] == baseline["classification"]
    assert scaled["classification"] == baseline["classification"]
    assert transformed["minimum_to_scale_ratio"] == pytest.approx(baseline["minimum_to_scale_ratio"])
    assert scaled["minimum_to_scale_ratio"] == pytest.approx(baseline["minimum_to_scale_ratio"])


def test_selected_and_reference_quadrature_contracts_are_predeclared() -> None:
    selected = CONTRACT["quadrature"]["selected_rule"]
    reference = CONTRACT["quadrature"]["reference_rule"]
    assert selected["name"] == "TRI3_X_GAUSS2"
    assert selected["point_count"] == 6
    assert sum(point["weight"] for point in selected["triangle_points"]) == pytest.approx(0.5)
    assert sum(point["weight"] for point in selected["line_points"]) == pytest.approx(2.0)
    assert selected["scope"] == (
        "WP07 full-integration technical kernel; reduced integration is not implemented or qualified"
    )
    assert reference["name"] == "DUFFY_GAUSS5_X_GAUSS4"
    assert reference["point_count"] == 100
    assert CONTRACT["quadrature"]["owner_policy"].startswith("FIXED_BY_TERRA_REVIEW")


def test_node_order_is_replayed_against_asymmetric_external_decks() -> None:
    assert MAPPING["status"] == "CONTROLLED_VALIDATED_REFERENCE_MAPPING"
    assert MAPPING["validation_fixture"]["asymmetric"] is True
    assert MAPPING["validation_fixture"]["positive_jacobian"] is True
    assert MAPPING["primary_node_order"]["qf_future_wedge6"] == [1, 2, 3, 4, 5, 6]
    calculix = (ROOT / "qualification/0_2_7/external_oracles/wedge6/decks/calculix/WP05-A-affine-patch.inp").read_text()
    assert re.search(r"\*ELEMENT,TYPE=C3D6[^\n]*\n1,1,2,3,4,5,6", calculix)
    code_aster = (ROOT / "qualification/0_2_7/external_oracles/wedge6/decks/code_aster/WP05-A-penta6-affine.mail").read_text()
    assert "E1 N1 N2 N3 N4 N5 N6" in code_aster
    assert MAPPING["permutation_policy"]["automatic_repair"] is False


def test_all_faces_have_outward_normals_and_declared_pressure_checks() -> None:
    center = PHYSICAL_NODES.mean(axis=0)
    for face in MAPPING["face_mapping"]:
        nodes = face["oriented_reference_cycle"]
        vector = face_surface_vector(nodes)
        face_center = PHYSICAL_NODES[np.asarray(nodes) - 1].mean(axis=0)
        assert np.dot(vector, face_center - center) > 0.0
        assert np.linalg.norm(vector) > 0.0
    assert CONTRACT["face_contract"]["required_checks"] == ["area", "outward normal", "uniform-pressure resultant", "resultant moment"]


def test_uniform_pressure_resultant_and_moment_are_deterministic() -> None:
    pressure = 7.0
    for face in MAPPING["face_mapping"]:
        nodes = face["oriented_reference_cycle"]
        face_center = PHYSICAL_NODES[np.asarray(nodes) - 1].mean(axis=0)
        expected_force = pressure * face_surface_vector(nodes)
        force, moment = integrate_face(nodes, pressure)
        assert force == pytest.approx(expected_force)
        assert moment == pytest.approx(np.cross(face_center, expected_force))


def test_quality_contract_and_external_tolerances_remain_predeclared() -> None:
    quality = wedge6_quality_contract()
    assert quality["implemented"] is True
    assert quality["status"] == "CONTROLLED_TECHNICAL_KERNEL_CONTRACT"
    assert CONTRACT["external_comparability"]["no_qf_correlation"] is True
    assert CONTRACT["external_comparability"]["tolerance_policy"]["status"] == "PROPOSED_OWNER_REVIEW"
    assert CONTRACT["external_comparability"]["tolerance_policy"]["near_zero_rule"].startswith("use declared absolute reference scale")
