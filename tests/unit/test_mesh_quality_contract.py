"""Targeted WP06 tests for common mesh quality diagnostics."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from solveur.compatibility import preflight_model
from solveur.core.model import FiniteElementModel
from solveur.mesh.quality_contract import (
    INVALID,
    VALID,
    VALID_WITH_WARNING,
    assess_element,
    assess_model,
    wedge6_quality_contract,
)
from solveur.verification.v2 import load_cases


CASES = Path(__file__).resolve().parents[2] / "qualification" / "0_2_7" / "vnv_v2" / "mesh_quality_cases.json"


TET4 = np.asarray(((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)), dtype=float)
HEX8 = np.asarray(
    ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)),
    dtype=float,
)
TET10 = np.asarray(
    (
        (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1),
        (0.5, 0, 0), (0.5, 0.5, 0), (0, 0.5, 0),
        (0, 0, 0.5), (0.5, 0, 0.5), (0, 0.5, 0.5),
    ),
    dtype=float,
)
HEX20 = np.asarray(
    (
        *HEX8.tolist(),
        (0.5, 0, 0), (0, 0.5, 0), (0, 0, 0.5),
        (1, 0.5, 0), (1, 0, 0.5), (0.5, 1, 0),
        (1, 1, 0.5), (0, 1, 0.5), (0.5, 0, 1),
        (0, 0.5, 1), (1, 0.5, 1), (0.5, 1, 1),
    ),
    dtype=float,
)


@pytest.mark.parametrize(
    "family, coords",
    (("TET4", TET4), ("TET10", TET10), ("HEX8", HEX8), ("HEX20", HEX20)),
)
def test_common_contract_covers_existing_solid_families(family: str, coords: np.ndarray) -> None:
    assessment = assess_element(1, family, coords)

    assert assessment.classification == VALID
    assert assessment.metrics["orientation_state"] == "POSITIVE"
    assert assessment.metrics["jacobian_sign_consistent"] is True
    assert assessment.metrics["volume"] > 0.0
    assert assessment.metrics["min_jacobian_determinant"] > 0.0
    assert assessment.metrics["max_jacobian_determinant"] >= assessment.metrics["min_jacobian_determinant"]
    assert "conditioning" in assessment.provenance


def test_legacy_tetra_quality_warning_is_explicit_and_not_a_new_universal_cutoff() -> None:
    stretched = TET4.copy()
    stretched[1] = (20.0, 0.0, 0.0)

    assessment = assess_element(2, "TET4", stretched)

    assert assessment.classification == VALID_WITH_WARNING
    assert assessment.metrics["aspect_ratio"] > 1.0
    assert "legacy" in assessment.provenance["thresholds"]


def test_near_degenerate_positive_geometry_is_reported_without_being_falsely_fatal() -> None:
    near_degenerate = TET4.copy()
    near_degenerate[3] = (1.0e-8, 1.0e-8, 1.0e-8)

    assessment = assess_element(8, "TET4", near_degenerate)

    assert assessment.metrics["signed_volume"] > 0.0
    assert assessment.classification == VALID_WITH_WARNING
    assert assessment.warnings


@pytest.mark.parametrize("family, coords", (("TET4", TET4), ("HEX8", HEX8)))
def test_quality_is_invariant_under_rigid_transform_and_dimensionless_scale(
    family: str, coords: np.ndarray
) -> None:
    rotation = np.asarray(((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)))
    baseline = assess_element(3, family, coords)
    transformed = assess_element(3, family, (coords @ rotation.T) + (4.0, -2.0, 7.0))
    scaled = assess_element(3, family, coords * 1.0e-9)

    assert transformed.classification == baseline.classification
    assert scaled.classification == baseline.classification
    assert transformed.metrics["aspect_ratio"] == pytest.approx(baseline.metrics["aspect_ratio"])
    assert scaled.metrics["aspect_ratio"] == pytest.approx(baseline.metrics["aspect_ratio"])
    assert transformed.metrics["jacobian_determinant_ratio"] == pytest.approx(
        baseline.metrics["jacobian_determinant_ratio"]
    )
    assert scaled.metrics["jacobian_determinant_ratio"] == pytest.approx(
        baseline.metrics["jacobian_determinant_ratio"]
    )


@pytest.mark.parametrize(
    "family, coords, permutation",
    (("TET4", TET4, (0, 2, 1, 3)), ("HEX8", HEX8, (0, 3, 2, 1, 4, 7, 6, 5))),
)
def test_inverted_geometry_is_invalid(family: str, coords: np.ndarray, permutation: tuple[int, ...]) -> None:
    assessment = assess_element(4, family, coords[list(permutation)])

    assert assessment.classification == INVALID
    assert "JACOBIAN_ORIENTATION_INVALID" in assessment.fatal_findings


def test_duplicate_nodes_and_unknown_wedge_are_fail_closed_without_implementation() -> None:
    duplicate = assess_element(5, "TET4", np.vstack((TET4[:3], TET4[0])))

    assert duplicate.classification == INVALID
    assert "COINCIDENT_ELEMENT_NODES" in duplicate.fatal_findings
    assert wedge6_quality_contract()["implemented"] is False
    with pytest.raises(ValueError, match="planned but not implemented"):
        assess_element(6, "WEDGE6", np.zeros((6, 3)))


def test_model_quality_and_preflight_reject_invalid_geometry() -> None:
    model = FiniteElementModel.from_raw(
        nodes=TET4.tolist(),
        elements=[{"type": "TET4", "nodes": [0, 2, 1, 3], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1.0, "nu": 0.3}},
        fixed_dofs=[{"node": 0, "dofs": ["UX", "UY", "UZ"]}],
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
        analysis="linear_static",
    )

    quality = assess_model(model)
    report = preflight_model(model)

    assert quality.classification == INVALID
    assert report.ok is False
    assert report.mesh_quality is not None
    assert report.mesh_quality.classification == INVALID
    assert any(result.reason == "MESH_GEOMETRY_INVALID" for result in report.results)


def test_quality_aggregation_leaves_non_solid_legacy_families_to_their_own_contract() -> None:
    model = type(
        "LegacyModel",
        (),
        {
            "nodes": np.zeros((4, 3)),
            "elements": [type("LegacyElement", (), {"type": "MITC4", "nodes": (0, 1, 2, 3)})()],
        },
    )()

    assessment = assess_model(model)

    assert assessment.classification == VALID
    assert assessment.elements == ()


def test_quality_serialization_is_deterministic() -> None:
    assessment = assess_element(7, "HEX8", HEX8)

    assert assessment.to_dict() == assess_element(7, "HEX8", HEX8).to_dict()


def test_mesh_quality_cases_are_registered_in_the_vnv_v2_schema() -> None:
    cases = load_cases(CASES)

    assert len(cases) == 4
    assert all(case.requirement_id == "027-REQ-007" for case in cases)
    assert {case.oracle.type for case in cases} == {"INTERNAL_INVARIANT", "FAILURE_EXPECTATION"}
