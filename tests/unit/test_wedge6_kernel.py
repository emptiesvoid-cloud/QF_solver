"""Targeted WP07 tests for the experimental WEDGE6 technical kernel."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from solveur.compatibility import check_compatibility, preflight_model
from solveur.core.model import FiniteElementModel
from solveur.elements.registry import ElementRegistry
from solveur.elements.solid.wedge6 import Wedge6Element
from solveur.materials.solid import SolidMaterial
from solveur.mesh.quality_contract import INVALID, VALID, VALID_WITH_WARNING, assess_element
from solveur.post.solid_results import wedge6_result
from solveur.verification.v2 import ExecutionOutput, VnvRunner, load_cases, replay_case


ROOT = Path(__file__).resolve().parents[2]
MATERIAL = SolidMaterial(E=210.0e9, nu=0.3)
REFERENCE_NODES = np.asarray(
    ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 1.0, 0.0),
     (0.0, 0.0, 3.0), (2.0, 0.0, 3.0), (0.0, 1.0, 3.0)),
    dtype=float,
)
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


def affine_displacement(coords: np.ndarray, matrix: np.ndarray, translation: np.ndarray | None = None) -> np.ndarray:
    shift = np.zeros(3) if translation is None else np.asarray(translation, dtype=float)
    return (np.asarray(coords) @ np.asarray(matrix, dtype=float).T + shift).reshape(-1)


def test_shape_function_identities_and_affine_mapping() -> None:
    element = Wedge6Element(MATERIAL)
    for index, node in enumerate(element.reference_nodes):
        values = element.shape_functions(tuple(node))
        assert values[index] == pytest.approx(1.0)
        assert np.delete(values, index) == pytest.approx(0.0)

    point = (0.21, 0.37, -0.23)
    shape = element.shape_functions(point)
    derivatives = element.shape_derivatives_reference(point)
    assert np.sum(shape) == pytest.approx(1.0)
    assert np.sum(derivatives, axis=0) == pytest.approx(0.0)

    transform = np.asarray(((2.0, 0.2, 0.1), (0.0, 1.5, 0.2), (0.1, 0.0, 3.0)))
    physical_nodes = element.reference_nodes @ transform.T + (1.0, -2.0, 0.5)
    expected = np.asarray(point) @ transform.T + (1.0, -2.0, 0.5)
    assert shape @ physical_nodes == pytest.approx(expected)


def test_production_and_reference_quadrature_are_declared_and_consistent() -> None:
    element = Wedge6Element(MATERIAL)
    assert len(element.integration_points) == 6
    assert len(element.reference_integration_points) == 100
    assert sum(element.integration_weights) == pytest.approx(1.0)
    assert sum(element.reference_integration_weights) == pytest.approx(1.0)

    production = element.stiffness(REFERENCE_NODES)
    reference = element.reference_stiffness(REFERENCE_NODES)
    relative_difference = np.linalg.norm(production - reference) / np.linalg.norm(reference)
    assert relative_difference < 1.0e-12
    assert production == pytest.approx(production.T, abs=1.0e-9)


def test_kernel_has_expected_rank_and_six_rigid_body_modes() -> None:
    element = Wedge6Element(MATERIAL)
    stiffness = element.stiffness(REFERENCE_NODES)
    scale = float(np.max(np.abs(stiffness)))
    assert np.linalg.matrix_rank(stiffness, tol=scale * 1.0e-10) == 12

    centroid = np.mean(REFERENCE_NODES, axis=0)
    rigid_vectors = [
        np.tile((1.0, 0.0, 0.0), 6),
        np.tile((0.0, 1.0, 0.0), 6),
        np.tile((0.0, 0.0, 1.0), 6),
    ]
    for axis in np.eye(3):
        rigid_vectors.append(np.cross(axis, REFERENCE_NODES - centroid).reshape(-1))
    for vector in rigid_vectors:
        assert np.linalg.norm(stiffness @ vector) / (scale * np.linalg.norm(vector)) < 1.0e-12


@pytest.mark.parametrize(
    "matrix",
    (
        np.diag((1.0e-4, 0.0, 0.0)),
        np.diag((-1.0e-4, 0.0, 0.0)),
        np.asarray(((0.0, 1.0e-4, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))),
    ),
)
def test_constant_strain_tension_compression_and_shear(matrix: np.ndarray) -> None:
    element = Wedge6Element(MATERIAL)
    displacement = affine_displacement(REFERENCE_NODES, matrix)
    expected = np.asarray((matrix[0, 0], matrix[1, 1], matrix[2, 2], matrix[0, 1] + matrix[1, 0], matrix[1, 2] + matrix[2, 1], matrix[0, 2] + matrix[2, 0]))
    strains = [element.strain_at(REFERENCE_NODES, displacement, point) for point in element.integration_points]
    assert np.asarray(strains) == pytest.approx(np.tile(expected, (6, 1)))


def test_bending_like_displacement_and_energy_are_finite() -> None:
    element = Wedge6Element(MATERIAL)
    displacement = np.zeros(18)
    displacement[0::3] = REFERENCE_NODES[:, 1] ** 2 * 1.0e-4
    internal, tangent = element.internal_force_and_tangent(REFERENCE_NODES, displacement)
    energy = 0.5 * float(displacement @ tangent @ displacement)
    assert np.isfinite(internal).all()
    assert np.isfinite(energy)
    assert energy >= 0.0


def test_quality_certificate_is_fail_closed_for_adversarial_and_inverted_prisms() -> None:
    nominal = assess_element(0, "WEDGE6", REFERENCE_NODES)
    assert nominal.classification == VALID

    skewed = REFERENCE_NODES @ np.asarray(((1.0, 0.25, 0.0), (0.0, 1.0, 0.15), (0.0, 0.0, 1.0))).T
    assert assess_element(1, "WEDGE6", skewed).classification == VALID

    near_degenerate = REFERENCE_NODES.copy()
    near_degenerate[3:, 2] = (1.0e-9, 3.0, 3.0)
    assert assess_element(2, "WEDGE6", near_degenerate).classification == VALID_WITH_WARNING

    inverted = REFERENCE_NODES[[0, 2, 1, 3, 5, 4]]
    inverted_assessment = assess_element(3, "WEDGE6", inverted)
    assert inverted_assessment.classification == INVALID
    assert "WEDGE6_JACOBIAN_CERTIFICATE_INVALID" in inverted_assessment.fatal_findings

    terra = assess_element(4, "WEDGE6", TERRA_ADVERSARIAL_NODES)
    assert terra.classification == INVALID
    assert "WEDGE6_JACOBIAN_CERTIFICATE_INVALID" in terra.fatal_findings


def test_quality_and_kernel_are_invariant_under_rigid_transform_and_scale() -> None:
    rotation = np.asarray(((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)))
    baseline = assess_element(5, "WEDGE6", REFERENCE_NODES)
    transformed = assess_element(5, "WEDGE6", REFERENCE_NODES @ rotation.T + (4.0, -2.0, 7.0))
    scaled = assess_element(5, "WEDGE6", REFERENCE_NODES * 1.0e-9)
    assert transformed.classification == baseline.classification
    assert scaled.classification == baseline.classification
    assert transformed.metrics["certified_detj_ratio"] == pytest.approx(baseline.metrics["certified_detj_ratio"])
    assert scaled.metrics["certified_detj_ratio"] == pytest.approx(baseline.metrics["certified_detj_ratio"])


def test_stress_recovery_returns_six_production_points() -> None:
    displacement = affine_displacement(REFERENCE_NODES, np.diag((1.0e-4, 0.0, 0.0)))
    result = wedge6_result(0, "WEDGE6", tuple(range(6)), MATERIAL, REFERENCE_NODES, displacement)
    assert len(result["integration_points"]) == 6
    assert len(result["nodal_results"]) == 6
    assert np.isfinite(np.asarray(result["stress"], dtype=float)).all()


def test_descriptor_registry_and_preflight_keep_wedge6_experimental_only() -> None:
    spec = ElementRegistry.get("WEDGE6")
    assert spec.node_count == 6
    assert check_compatibility("WEDGE6", "linear_static", "isotropic_3d").status == "EXPERIMENTAL_ROUTE"
    assert check_compatibility("WEDGE6", "modal", "isotropic_3d").status == "EXPERIMENTAL_ROUTE"
    assert check_compatibility("WEDGE6", "linear_static", "isotropic_3d", load_categories=("pressure",)).status == "EXPERIMENTAL_ROUTE"

    model = FiniteElementModel.from_raw(
        nodes=REFERENCE_NODES.tolist(),
        elements=[{"type": "WEDGE6", "nodes": list(range(6)), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
        analysis="linear_static",
    )
    report = preflight_model(model)
    assert report.ok
    assert report.status == "EXPERIMENTAL_ROUTE"
    assert report.mesh_quality is not None
    assert report.mesh_quality.classification == VALID


def test_wp07_catalog_runs_through_v2_and_replays_deterministically() -> None:
    catalog = ROOT / "qualification/0_2_7/vnv_v2/wp07_cases.json"
    cases = load_cases(catalog)
    assert len(cases) == 8
    source_sha = "69b7d01beb81263fc2b87cfacb83985db10e3a82"

    def execute(case):
        if case.expected_failure:
            raise ValueError(case.expected_failure)
        return ExecutionOutput({case.oracle.observable: case.oracle.expected})

    runner = VnvRunner(source_sha=source_sha, environment={"test": "wp07"})
    evidence = [runner.run(case, execute) for case in cases]
    assert [item.verdict for item in evidence].count("EXPECTED_FAILURE_PASS") == 1
    assert [item.verdict for item in evidence].count("PASS") == 7
    replayed, reason, current = replay_case(cases[0], execute, evidence[0], source_sha=source_sha, environment={"test": "wp07"})
    assert replayed
    assert reason == "PASS"
    assert current is not None
    rejected, reason, current = replay_case(cases[0], execute, evidence[0], source_sha="different-source")
    assert not rejected
    assert reason == "SOURCE_SHA_MISMATCH"
    assert current is None
