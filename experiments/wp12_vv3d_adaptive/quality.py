"""Geometry-only quality checks for the prepared straight-sided meshes; never assembles FEM."""
from __future__ import annotations

from itertools import combinations
from experiments.wp12_vv3d_adaptive.mesh import HEX_CORNERS, HEX_EDGES, TET_EDGES, _det


def assess(mesh: dict) -> dict:
    family = mesh["family"]
    nodes = mesh["nodes_integer"]
    denom = mesh["integer_coordinate_denominator"]
    det_min = float("inf")
    det_max = 0.0
    quality_min = float("inf")
    quality_max = 0.0
    for cell in mesh["connectivity_zero_based"]:
        if family.startswith("TET"):
            points=[nodes[i] for i in cell[:4]]
            det=_det(*points)
            if det <= 0:
                raise ValueError("non-positive tetrahedron orientation")
            edge_sum=sum(sum((points[a][i]-points[b][i])**2 for i in range(3))
                         for a,b in combinations(range(4),2))
            quality=12*(det/2)**(2/3)/edge_sum
            physical_det=det/denom**3
        elif family in {"HEX8","HEX20"}:
            points=[nodes[i] for i in cell[:8]]
            lower=points[0]
            sizes=(points[1][0]-lower[0],points[3][1]-lower[1],points[4][2]-lower[2])
            if min(sizes) <= 0 or any(tuple(lower[i]+corner[i]*sizes[i] for i in range(3)) != tuple(point)
                                      for point,corner in zip(points,HEX_CORNERS)):
                raise ValueError("hexahedron is not a positively oriented axis-aligned affine brick")
            aspect=max(sizes)/min(sizes)
            quality=1/aspect
            physical_det=sizes[0]*sizes[1]*sizes[2]/(8*denom**3)
        else:
            raise ValueError("unsupported formulation")
        if family in {"TET10", "HEX20"}:
            corners = 4 if family == "TET10" else 8
            edges = TET_EDGES if family == "TET10" else HEX_EDGES
            if len(cell) != corners + len(edges):
                raise ValueError("quadratic element connectivity is incomplete")
            for index,(a,b) in enumerate(edges):
                midpoint = tuple((points[a][i]+points[b][i])/2 for i in range(3))
                if tuple(nodes[cell[corners+index]]) != midpoint:
                    raise ValueError("quadratic midside geometry is not affine")
        det_min=min(det_min,physical_det)
        det_max=max(det_max,physical_det)
        quality_min=min(quality_min,quality)
        quality_max=max(quality_max,quality)
    if not mesh["connectivity_zero_based"]:
        raise ValueError("empty mesh")
    return {"quality_kind": "tetra_mean_ratio" if family.startswith("TET") else "inverse_brick_aspect_ratio",
            "quality_min":quality_min,"quality_max":quality_max,"jacobian_det_min_m3":det_min,
            "jacobian_det_max_m3":det_max,"basis":"affine vertices; geometry-only, no FEM evaluation"}
