"""Synthetic-only tests for the HEX8 research mesh geometry utility."""

from __future__ import annotations

import numpy as np
import pytest

from experiments.hex8_sri_equilibrium.mesh_quality import mesh_quality_metrics, structured_hex8_mesh


def test_regular_mesh_counts_and_sampled_quality_are_consistent() -> None:
    nodes, connectivity = structured_hex8_mesh((4, 2, 2))
    metrics = mesh_quality_metrics(nodes, connectivity)

    assert nodes.shape == (45, 3)
    assert connectivity.shape == (16, 8)
    assert metrics["dof_count"] == 135
    assert metrics["jacobian_positivity_status"] == "SAMPLED_POSITIVE"
    assert metrics["positivity_certification"] == "NOT_CERTIFIED_BETWEEN_SAMPLES"
    assert metrics["minimum_scaled_jacobian"] == pytest.approx(1.0)
    assert metrics["maximum_directional_aspect_ratio"] == pytest.approx(10.0)


def test_seeded_geometry_is_reproducible_and_changes_only_the_geometry_digest() -> None:
    first_nodes, first_cells = structured_hex8_mesh((4, 2, 2), distortion="seeded", seed=17)
    second_nodes, second_cells = structured_hex8_mesh((4, 2, 2), distortion="seeded", seed=17)
    other_nodes, other_cells = structured_hex8_mesh((4, 2, 2), distortion="seeded", seed=18)

    first = mesh_quality_metrics(first_nodes, first_cells)
    second = mesh_quality_metrics(second_nodes, second_cells)
    other = mesh_quality_metrics(other_nodes, other_cells)

    assert np.array_equal(first_nodes, second_nodes)
    assert np.array_equal(first_cells, second_cells)
    assert first["geometry_sha256"] == second["geometry_sha256"]
    assert first["geometry_sha256"] != other["geometry_sha256"]
    assert first["jacobian_positivity_status"] == "SAMPLED_POSITIVE"


def test_shear_and_flattened_families_remain_sampled_positive_but_are_distinct() -> None:
    regular_nodes, cells = structured_hex8_mesh((4, 2, 2))
    shear_nodes, shear_cells = structured_hex8_mesh((4, 2, 2), distortion="severe_shear")
    flat_nodes, flat_cells = structured_hex8_mesh((4, 2, 2), distortion="near_degenerate")

    regular = mesh_quality_metrics(regular_nodes, cells)
    shear = mesh_quality_metrics(shear_nodes, shear_cells)
    flattened = mesh_quality_metrics(flat_nodes, flat_cells)

    assert shear["jacobian_positivity_status"] == "SAMPLED_POSITIVE"
    assert shear["minimum_scaled_jacobian"] < regular["minimum_scaled_jacobian"]
    assert flattened["jacobian_positivity_status"] == "SAMPLED_POSITIVE"
    assert flattened["minimum_sampled_detJ_m3"] == pytest.approx(0.05 * regular["minimum_sampled_detJ_m3"])


def test_mesh_quality_rejects_malformed_connectivity_without_calling_fem() -> None:
    nodes, connectivity = structured_hex8_mesh((1, 1, 1))

    with pytest.raises(ValueError, match="out-of-range"):
        mesh_quality_metrics(nodes, np.asarray([[0, 1, 2, 3, 4, 5, 6, 99]]))

    with pytest.raises(ValueError, match=r"shape \(m, 8\)"):
        mesh_quality_metrics(nodes, connectivity[:, :7])


def test_inverted_geometry_is_reported_as_sampled_invalid() -> None:
    nodes, connectivity = structured_hex8_mesh((1, 1, 1))
    inverted = connectivity.copy()
    inverted[0, 0], inverted[0, 1] = inverted[0, 1], inverted[0, 0]

    metrics = mesh_quality_metrics(nodes, inverted)

    assert metrics["jacobian_positivity_status"] == "SAMPLED_INVALID"
    assert metrics["minimum_sampled_detJ_m3"] < 0.0
