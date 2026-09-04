"""T1-R3 tests for the inactive WEDGE6 certificate and external contract."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from solveur.mesh.quality_contract import (
    INVALID,
    VALID,
    VALID_WITH_WARNING,
    wedge6_jacobian_certificate,
)
from solveur.verification.v2 import DuplicateJsonKeyError, load_json_strict


ROOT = Path(__file__).resolve().parents[2]
REFERENCE_NODES = np.asarray(
    ((0, 0, -1), (1, 0, -1), (0, 1, -1), (0, 0, 1), (1, 0, 1), (0, 1, 1)),
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


def test_certificate_accepts_nominal_and_affine_skewed_prisms() -> None:
    fixture = load_json_strict(ROOT / "qualification/0_2_7/wedge6_mapping_fixture.json")
    skewed = np.asarray([fixture["coordinates"][str(i)] for i in range(1, 7)], dtype=float)

    assert wedge6_jacobian_certificate(REFERENCE_NODES)["classification"] == VALID
    assert wedge6_jacobian_certificate(skewed)["classification"] == VALID


def test_certificate_rejects_terra_adversarial_interior_inversion() -> None:
    certificate = wedge6_jacobian_certificate(TERRA_ADVERSARIAL_NODES)

    assert certificate["classification"] == INVALID
    assert certificate["minimum_detJ"] < 0.0
    assert any(0.0 < item["t"] < 1.0 for item in certificate["candidates"])


def test_certificate_classifies_near_degenerate_and_inverted_prisms() -> None:
    near_degenerate = REFERENCE_NODES.copy()
    near_degenerate[3, 2] = -1.0 + 1.0e-12
    inverted = REFERENCE_NODES[[0, 2, 1, 3, 5, 4]]

    assert wedge6_jacobian_certificate(near_degenerate)["classification"] == VALID_WITH_WARNING
    assert wedge6_jacobian_certificate(inverted)["classification"] == INVALID


def test_certificate_is_rigid_transform_and_scale_invariant() -> None:
    rotation = np.asarray(((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)))
    baseline = wedge6_jacobian_certificate(REFERENCE_NODES)
    transformed = wedge6_jacobian_certificate((REFERENCE_NODES @ rotation.T) + (4.0, -2.0, 7.0))
    scaled = wedge6_jacobian_certificate(REFERENCE_NODES * 1.0e-9)

    assert transformed["classification"] == baseline["classification"]
    assert scaled["classification"] == baseline["classification"]
    assert transformed["minimum_to_scale_ratio"] == pytest.approx(baseline["minimum_to_scale_ratio"])
    assert scaled["minimum_to_scale_ratio"] == pytest.approx(baseline["minimum_to_scale_ratio"])


def test_external_contract_has_unique_tolerance_categories() -> None:
    contract = load_json_strict(ROOT / "qualification/0_2_7/external_oracles/wedge6/contract.json")
    policy = contract["comparability_contract"]["tolerance_policy"]

    assert contract["comparability_contract"]["primary_observables"] == [
        "displacement",
        "total_reaction",
        "strain_energy",
    ]
    assert policy["categories"]["AFFINE_SAME_MESH"]["relative_tolerance"] == pytest.approx(1.0e-6)
    assert policy["categories"]["NON_AFFINE_DISTORTED_REFINEMENT"]["relative_tolerance"] is None
    assert policy["post_observation_retuning"].startswith("FORBIDDEN")


def test_duplicate_json_keys_fail_closed(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"a": 1, "a": 2}', encoding="utf-8")

    with pytest.raises(DuplicateJsonKeyError, match="Duplicate JSON key 'a'"):
        load_json_strict(duplicate)
