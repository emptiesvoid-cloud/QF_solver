"""Draft consistent volumetric load adapter. Never call the private candidate integrator.

This module is NOT registered with the official controller and is NOT authorized.
Public assembly fails closed. The draft below is source for review only; it has not
been executed or validated against an independent element-force oracle.
"""
from __future__ import annotations

import math
from experiments.wp12_vv3d_adaptive import basis, mesh as mesh_tools, oracle, quadrature


def assemble_body_load(mesh: dict, *, order: int) -> list[float]:
    """Deny execution until a reviewed, source-bound official controller gate exists."""
    raise PermissionError("WP12-VV3D load assembly is PREPARED_NOT_AUTHORIZED and not registered")


def _candidate_integrate_body_load_DO_NOT_EXECUTE(prepared_mesh: dict, order: int) -> list[float]:
    """Unexecuted implementation draft for affine cells, independently reviewed before use.

    For each element, form f_e = integral N^T f dV with 4- or 8-point
    tensor-product reference quadrature and scatter to a global nodal vector.
    It explicitly performs FEM load assembly: running it needs Owner approval.
    """
    family = prepared_mesh["family"]
    coordinates = prepared_mesh["nodes_integer"]
    denominator = prepared_mesh["integer_coordinate_denominator"]
    tet = family in {"TET4", "TET10"}
    if family not in {"TET4", "TET10", "HEX8", "HEX20"}:
        raise ValueError("unsupported element")
    rule = quadrature.tetrahedron_duffy_rule(order) if tet else quadrature.hexahedron_rule(order)
    out = [0.0] * (3 * len(coordinates))
    for cell in prepared_mesh["connectivity_zero_based"]:
        corners = [coordinates[index] for index in cell[:4 if tet else 8]]
        if tet:
            determinant = mesh_tools._det(*corners) / denominator**3
        else:
            sizes = (corners[1][0]-corners[0][0], corners[3][1]-corners[0][1], corners[4][2]-corners[0][2])
            determinant = math.prod(sizes) / (8*denominator**3)
        if determinant <= 0 or not math.isfinite(determinant):
            raise ValueError("invalid affine Jacobian")
        for r,s,t,w in rule:
            reference = (r,s,t)
            linear = basis.shape_values("TET4" if tet else "HEX8", reference)
            physical = tuple(sum(linear[i]*corners[i][axis] for i in range(len(corners)))/denominator
                             for axis in range(3))
            density = oracle.field(physical)["body_force_n_m3"]
            shape = basis.shape_values(family, reference)
            factor = w*determinant
            for local,node in enumerate(cell):
                for axis in range(3):
                    out[3*node+axis] += factor*shape[local]*density[axis]
    if not all(math.isfinite(value) for value in out):
        raise ValueError("nonfinite assembled load")
    return out
