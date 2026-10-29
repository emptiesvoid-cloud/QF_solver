"""Create deterministic affine mesh descriptions; never imports or assembles a solver."""
from __future__ import annotations

from collections import Counter
from itertools import product

FORMULATIONS = ("TET4", "TET10", "HEX8", "HEX20")
LEVELS = (2, 4, 8)
HEX_CORNERS = ((0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1))
HEX_EDGES = ((0,1),(0,3),(0,4),(1,2),(1,5),(3,2),(2,6),(3,7),(4,5),(4,7),(5,6),(7,6))
TET_EDGES = ((0,1),(1,2),(2,0),(0,3),(1,3),(2,3))
# Six conforming tetrahedra around the 0-to-6 cube diagonal.
TETS = ((0,1,2,6),(0,2,3,6),(0,3,7,6),(0,7,4,6),(0,4,5,6),(0,5,1,6))


def _det(a: tuple[int, ...], b: tuple[int, ...], c: tuple[int, ...], d: tuple[int, ...]) -> int:
    x, y, z = ([p[i]-a[i] for i in range(3)] for p in (b,c,d))
    return x[0]*(y[1]*z[2]-y[2]*z[1])-x[1]*(y[0]*z[2]-y[2]*z[0])+x[2]*(y[0]*z[1]-y[1]*z[0])


def generate(family: str, n: int) -> dict:
    """Unit cube, dyadic integer coordinates, positive affine cells, exact shared edge nodes."""
    if family not in FORMULATIONS or n not in LEVELS:
        raise ValueError("family/level outside prepared matrix")
    high = family in ("TET10", "HEX20")
    tet = family.startswith("TET")
    nodes: list[tuple[int, int, int]] = []
    nodeids: dict[tuple[int, int, int], int] = {}
    cells: list[list[int]] = []
    det_values: list[int] = []

    def insert(p: tuple[int, int, int]) -> int:
        if p not in nodeids:
            nodeids[p] = len(nodes)
            nodes.append(p)
        return nodeids[p]

    for i,j,k in product(range(n), repeat=3):
        cube = [tuple(2*(v+offset) for v,offset in zip((i,j,k), corner)) for corner in HEX_CORNERS]
        local_cells = ([cube[t] for t in pattern] for pattern in TETS) if tet else (cube,)
        for corners in local_cells:
            if tet:
                determinant = _det(*corners)
                if determinant <= 0:
                    raise ValueError("nonpositive affine tetrahedron orientation")
                det_values.append(determinant)
            else:
                det_values.append(8)  # unit reference [-1,1]^3, physical det=1/(8*n^3)
            ids = [insert(p) for p in corners]
            if high:
                edges = TET_EDGES if tet else HEX_EDGES
                for a,b in edges:
                    midpoint = tuple((corners[a][q]+corners[b][q])//2 for q in range(3))
                    ids.append(insert(midpoint))
            cells.append(ids)
    boundary = [idx for idx,p in enumerate(nodes) if any(q in (0,2*n) for q in p)]
    # For affine hex: detJ = h^3/8. For tet: detJ = h^3.
    det_j = 1.0 / (n**3 * (1 if tet else 8))
    return {"schema": "qf-wp12-vv3d-mesh-v1", "family": family, "divisions": [n,n,n],
            "coordinate_unit": "m", "integer_coordinate_denominator": 2*n, "nodes_integer": nodes,
            "connectivity_zero_based": cells, "fixed_node_ids_all_components": boundary,
            "summary": {"elements": len(cells), "nodes": len(nodes), "dofs": 3*len(nodes),
                        "fixed_dofs": 3*len(boundary), "free_dofs": 3*(len(nodes)-len(boundary)),
                        "affine_jacobian_min_m3": det_j, "affine_jacobian_max_m3": det_j,
                        "node_incidence_min": min(Counter(q for cell in cells for q in cell).values()),
                        "geometry": "straight-sided affine cells", "status": "PREPARED_NOT_AUTHORIZED"}}
