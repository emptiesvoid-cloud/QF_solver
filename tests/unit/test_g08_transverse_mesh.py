"""Geometry and input regressions for the G08 transverse Euler screen."""

from collections import defaultdict
from itertools import combinations
import math

import numpy as np
import pytest

from scripts import run_g08_high_order_analytical as g08
from solveur.elements.solid.tet4 import Tet4Element
from solveur.elements.solid.tet10 import Tet10Element


TET_EDGES = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))


@pytest.mark.parametrize("family", ["TET4", "TET10"])
@pytest.mark.parametrize(
    "axial, transverse, axes",
    [(1, 2, (0, 1, 2)), (2, 2, (1, 2, 0)), (2, 3, (2, 0, 1)), (3, 4, (0, 1, 2))],
)
def test_g08_transverse_tetrahedra_share_complete_faces(family, axial, transverse, axes):
    model, _ = g08._model(family, axial, transverse)
    nodes = model.nodes[:, axes]
    lower, upper = nodes.min(axis=0), nodes.max(axis=0)
    faces = defaultdict(list)
    edge_mids = {}
    signed_volumes = []
    for index, element in enumerate(model.elements):
        corners = element.nodes[:4]
        signed_volumes.append(Tet4Element.signed_volume(nodes[list(corners)]))
        mids = {}
        if family == "TET10":
            for (i, j), mid in zip(TET_EDGES, element.nodes[4:], strict=True):
                edge = tuple(sorted((corners[i], corners[j])))
                assert edge_mids.setdefault(edge, mid) == mid
                mids[edge] = mid
                np.testing.assert_allclose(nodes[mid], nodes[list(edge)].mean(axis=0), rtol=0, atol=1e-13)
            assert np.all(Tet10Element.jacobian_determinants(nodes[list(element.nodes)]) > 0)
        for face in combinations(sorted(corners), 3):
            face_mids = tuple(mids[edge] for edge in combinations(face, 2)) if mids else ()
            opposite = next(node for node in corners if node not in face)
            faces[face].append((index, face_mids, opposite))

    neighbors = [set() for _ in model.elements]
    boundary_count = 0
    for face, uses in faces.items():
        assert len(uses) in (1, 2)
        triangle = nodes[list(face)]
        if len(uses) == 1:
            assert np.any(np.all(triangle == lower, axis=0) | np.all(triangle == upper, axis=0)), triangle
            boundary_count += 1
        else:
            (left, left_mids, a), (right, right_mids, b) = uses
            assert left_mids == right_mids
            normal = np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
            assert (normal @ (nodes[a] - triangle[0])) * (normal @ (nodes[b] - triangle[0])) < 0
            neighbors[left].add(right)
            neighbors[right].add(left)

    seen, pending = {0}, [0]
    while pending:
        new = neighbors[pending.pop()] - seen
        seen.update(new)
        pending.extend(new)
    assert len(seen) == len(model.elements)
    assert boundary_count == 4 * (transverse**2 + 2 * axial * transverse)
    assert len(edge_mids) == len(set(edge_mids.values()))
    assert min(signed_volumes) > 0.0
    assert math.fsum(signed_volumes) == pytest.approx(g08.LENGTH * g08.WIDTH * g08.HEIGHT)


@pytest.mark.parametrize("family,degree", [("TET4", 1), ("TET10", 2)])
@pytest.mark.parametrize("transverse", [2, 3])
def test_g08_transverse_model_keeps_axial_column_boundary_data(family, degree, transverse):
    model, metadata = g08._model(family, 2, transverse)
    nodes = model.nodes
    assert model.analysis.type == "linear_buckling"
    assert model.analysis.method == "eigsh"
    assert model.materials == {"solid": {"type": "isotropic_3d", "E": g08.YOUNG, "nu": g08.POISSON}}
    np.testing.assert_array_equal(nodes.min(axis=0), [0, 0, 0])
    np.testing.assert_array_equal(nodes.max(axis=0), [g08.LENGTH, g08.WIDTH, g08.HEIGHT])
    fixed = model.fixed_dofs
    loads = model.loads
    count = (degree * transverse + 1) ** 2
    assert len(fixed) == len(loads) == metadata["loaded_node_count"] == count
    assert {bc.node for bc in fixed} == set(np.flatnonzero(nodes[:, 0] == 0))
    assert {load.node for load in loads} == set(np.flatnonzero(nodes[:, 0] == g08.LENGTH))
    assert all(set(bc.dofs) == {"UX", "UY", "UZ"} for bc in fixed)
    assert all(load.dof == "UX" and load.value == g08.REFERENCE_LOAD / count for load in loads)
    assert math.fsum(load.value for load in loads) == pytest.approx(g08.REFERENCE_LOAD)
    assert metadata["reference_total_load"] == pytest.approx(g08.REFERENCE_LOAD)
    for end in (fixed, loads):
        coords = nodes[[entry.node for entry in end], 1:]
        expected = np.array([
            (y, z)
            for y in np.linspace(0, g08.WIDTH, degree * transverse + 1)
            for z in np.linspace(0, g08.HEIGHT, degree * transverse + 1)
        ])
        np.testing.assert_allclose(sorted(map(tuple, coords)), expected, rtol=0, atol=1e-13)
