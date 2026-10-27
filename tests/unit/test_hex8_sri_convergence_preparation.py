from __future__ import annotations

import itertools

import numpy as np
import pytest

from experiments.hex8_sri_equilibrium.campaign import mesh_data as historical_mesh_data
from experiments.hex8_sri_equilibrium.convergence import (
    consistent_end_face_load,
    structured_hex_mesh,
)
from experiments.hex8_sri_equilibrium.campaign_spec import (
    FORMULATIONS,
    MESH_LEVELS,
    POISSON_RATIOS,
    convergence_case_id,
    convergence_nodeid,
)


@pytest.mark.parametrize(
    ("divisions", "element_count", "node_count", "dof_count"),
    (
        ((4, 2, 2), 16, 45, 135),
        ((8, 4, 4), 128, 225, 675),
        ((16, 8, 8), 1024, 1377, 4131),
        ((32, 16, 16), 8192, 9537, 28611),
    ),
)
def test_structured_mesh_counts_match_campaign_matrix(
    divisions: tuple[int, int, int], element_count: int, node_count: int, dof_count: int
) -> None:
    mesh = structured_hex_mesh(*divisions)
    assert mesh.connectivity.shape == (element_count, 8)
    assert mesh.nodes_m.shape == (node_count, 3)
    assert mesh.nodes_m.shape[0] * 3 == dof_count


def test_historical_base_mesh_matches_generalized_generator_exactly() -> None:
    old_nodes, old_connectivity = historical_mesh_data()
    new_mesh = structured_hex_mesh(4, 2, 2)

    np.testing.assert_array_equal(new_mesh.nodes_m, old_nodes)
    np.testing.assert_array_equal(new_mesh.connectivity, old_connectivity)


def test_consistent_end_face_traction_has_declared_resultant_and_origin_moment() -> None:
    mesh = structured_hex_mesh(4, 2, 2)
    force, loaded_nodes, weights = consistent_end_face_load(mesh)
    nodal_force = force.reshape(-1, 3)

    assert len(loaded_nodes) == 9
    assert weights.sum() == pytest.approx(1.0)
    np.testing.assert_allclose(nodal_force.sum(axis=0), [0.0, 0.0, -1.0], atol=1.0e-15)
    np.testing.assert_allclose(np.cross(mesh.nodes_m, nodal_force).sum(axis=0), [-0.5, 20.0, 0.0], atol=1.0e-14)


def test_loaded_face_weights_compute_the_uniform_area_mean_for_affine_trace() -> None:
    mesh = structured_hex_mesh(4, 2, 2)
    _force, loaded_nodes, weights = consistent_end_face_load(mesh)
    y = mesh.nodes_m[loaded_nodes, 1]
    z = mesh.nodes_m[loaded_nodes, 2]
    trace = 3.0 + 2.0 * y - 4.0 * z

    assert weights @ trace == pytest.approx(2.0)


def test_first_campaign_nodeids_are_unique_and_have_expected_case_product() -> None:
    cases = [
        convergence_nodeid(formulation, nu, mesh)
        for formulation, nu, mesh in itertools.product(FORMULATIONS, POISSON_RATIOS, MESH_LEVELS)
    ]
    ids = [
        convergence_case_id(formulation, nu, mesh)
        for formulation, nu, mesh in itertools.product(FORMULATIONS, POISSON_RATIOS, MESH_LEVELS)
    ]

    assert len(cases) == len(set(cases)) == 24
    assert len(ids) == len(set(ids)) == 24
    assert cases[0] == (
        "tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p3-4x2x2]"
    )
