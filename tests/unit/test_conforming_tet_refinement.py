"""Topology regression for the Cartesian tetrahedral verification generator."""

from collections import defaultdict
from itertools import combinations

import numpy as np

from solveur.elements.solid.tet4 import Tet4Element
from solveur.elements.solid.tet10 import Tet10Element
from solveur.verification.robustness_mesh import mesh_refinement_mesh


_EDGES = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))


def test_tet_refinement_shares_complete_internal_faces():
    for family in ("TET4", "TET10"):
        for cells in (1, 2, 3, 4):
            nodes, elements = mesh_refinement_mesh(family, cells)
            faces = defaultdict(list)
            edge_mids = {}
            signed_volumes = []
            for index, element in enumerate(elements):
                corners = element[:4]
                signed_volumes.append(Tet4Element.signed_volume(nodes[corners]))
                local_mids = {}
                if family == "TET10":
                    for (a, b), mid in zip(_EDGES, element[4:], strict=True):
                        edge = tuple(sorted((corners[a], corners[b])))
                        assert edge_mids.setdefault(edge, mid) == mid
                        local_mids[edge] = mid
                        np.testing.assert_allclose(nodes[mid], nodes[list(edge)].mean(axis=0), atol=1e-14, rtol=0)
                    assert np.all(Tet10Element.jacobian_determinants(nodes[element]) > 0)
                for face in combinations(sorted(corners), 3):
                    mids = tuple(local_mids[edge] for edge in combinations(face, 2)) if local_mids else ()
                    faces[face].append((index, mids))

            neighbors = [set() for _ in elements]
            for face, uses in faces.items():
                assert len(uses) in (1, 2)
                if len(uses) == 1:
                    xyz = nodes[list(face)]
                    assert any(np.all(xyz[:, axis] == bound) for axis in range(3) for bound in (0, 1)), (
                        family, cells, xyz,
                    )
                else:
                    (left, left_mids), (right, right_mids) = uses
                    assert left_mids == right_mids
                    neighbors[left].add(right)
                    neighbors[right].add(left)

            visited = {0}
            frontier = [0]
            while frontier:
                new = neighbors[frontier.pop()] - visited
                visited.update(new)
                frontier.extend(new)
            assert len(visited) == len(elements)
            assert min(signed_volumes) > 0
            np.testing.assert_allclose(sum(signed_volumes), 1.0, atol=1e-13, rtol=0)
            if family == "TET10":
                assert len(set(edge_mids.values())) == len(edge_mids)
