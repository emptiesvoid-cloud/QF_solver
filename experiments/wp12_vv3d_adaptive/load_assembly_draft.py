"""Prospective consistent volume-load integration for affine VV3D meshes.

The numerical path is implemented, but it remains unreachable unless a caller
provides a permit validator bound to the official runner's validated execution
context. This module does not implement or authenticate that controller.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from experiments.wp12_vv3d_adaptive import basis, mesh as mesh_tools, oracle, quadrature


_CORNER_COUNTS = {"TET4": 4, "TET10": 4, "HEX8": 8, "HEX20": 8}
_NODE_COUNTS = {"TET4": 4, "TET10": 10, "HEX8": 8, "HEX20": 20}


def assemble_body_load(
    prepared_mesh: dict,
    *,
    order: int,
    execution_context: Mapping[str, str] | None = None,
    permit_validator: Callable[[Mapping[str, str]], bool] | None = None,
) -> list[float]:
    """Integrate the analytic body force only after an external gate validates it.

    The official runner must supply a validator that checks its actual signed or
    source-bound permit and exact case context. A boolean flag or environment
    variable is deliberately insufficient. There is no default validator, and
    this research module does not claim to authenticate the Owner/controller.
    This FEM load assembly function has not been called in this preparation.
    """
    required = {"campaign_id", "case_id", "nodeid", "manifest_sha256",
                "scientific_fingerprint", "controller_fingerprint"}
    if (not isinstance(execution_context, Mapping) or set(execution_context) != required
            or any(not isinstance(value, str) or not value for value in execution_context.values())
            or permit_validator is None or not callable(permit_validator)):
        raise PermissionError("VV3D load assembly requires a validated controller permit")
    if permit_validator(execution_context) is not True:
        raise PermissionError("VV3D controller rejected the execution permit")
    return _candidate_integrate_body_load_DO_NOT_EXECUTE(prepared_mesh, order)


def _affine_cell_geometry(family: str, cell: list[int] | tuple[int, ...],
                          coordinates: list[tuple[int, int, int]] | tuple[tuple[int, int, int], ...],
                          denominator: int) -> tuple[tuple[float, float, float],
                                                     tuple[tuple[float, float, float], ...], float]:
    """Describe a positive straight-sided affine cell without assembling a load.

    Returns the physical image of the reference origin, the Jacobian with columns
    corresponding to reference r/s/t, and det(J). Coordinates are integer encoded.
    High-order families are accepted only when every midside node is the exact
    geometric midpoint of its edge; curved mappings are outside this adapter.
    """
    if family not in _NODE_COUNTS or len(cell) != _NODE_COUNTS[family]:
        raise ValueError("family/connectivity node count mismatch")
    if not isinstance(denominator, int) or denominator <= 0:
        raise ValueError("invalid integer coordinate denominator")
    if len(set(cell)) != len(cell) or any(not isinstance(i, int) or i < 0 or i >= len(coordinates) for i in cell):
        raise ValueError("invalid cell node indices")
    points = [coordinates[i] for i in cell]
    if any(len(p) != 3 or any(not isinstance(v, int) for v in p) for p in points):
        raise ValueError("coordinates must be integer triples")
    corner_count = _CORNER_COUNTS[family]
    corners = points[:corner_count]
    if family.startswith("TET"):
        a, b, c, d = corners
        cols = tuple(tuple((p[k] - a[k]) / denominator for k in range(3)) for p in (b, c, d))
        # The rows of J are physical axes and columns are reference coordinates.
        jacobian = tuple(tuple(cols[j][i] for j in range(3)) for i in range(3))
        origin = tuple(a[i] / denominator for i in range(3))
        determinant = mesh_tools._det(a, b, c, d) / denominator**3
    else:
        a, b, _c, d, e, _f, _g, _h = corners
        # Affine HEX corner ordering: x = origin + (1+r)/2*u + (1+s)/2*v + (1+t)/2*w.
        edge_vectors = tuple(tuple((p[k] - a[k]) / (2 * denominator) for k in range(3)) for p in (b, d, e))
        jacobian = tuple(tuple(edge_vectors[j][i] for j in range(3)) for i in range(3))
        origin = tuple((a[i] + b[i] + d[i] + e[i] + corners[2][i] + corners[5][i] + corners[6][i] + corners[7][i])
                       / (8 * denominator) for i in range(3))
        determinant = _det3(jacobian)
        for index, signs in enumerate(mesh_tools.HEX_CORNERS):
            expected = tuple(origin[i] + sum(jacobian[i][axis] * (2 * signs[axis] - 1) for axis in range(3))
                             for i in range(3))
            actual = tuple(corners[index][i] / denominator for i in range(3))
            if any(abs(actual[i] - expected[i]) > 1e-12 for i in range(3)):
                raise ValueError("hexahedron corners are not an affine parallelepiped")
    if family in {"TET10", "HEX20"}:
        edges = mesh_tools.TET_EDGES if family == "TET10" else mesh_tools.HEX_EDGES
        for offset, (left, right) in enumerate(edges, corner_count):
            expected = tuple((corners[left][axis] + corners[right][axis]) / 2 for axis in range(3))
            if any(points[offset][axis] != expected[axis] for axis in range(3)):
                raise ValueError("quadratic cell is not straight-sided affine")
    if not math.isfinite(determinant) or determinant <= 0:
        raise ValueError("invalid affine Jacobian")
    return origin, jacobian, determinant


def _det3(matrix: tuple[tuple[float, float, float], ...]) -> float:
    a, b, c = matrix
    return a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])


def _candidate_integrate_body_load_DO_NOT_EXECUTE(prepared_mesh: dict, order: int) -> list[float]:
    """Form ``f_e = integral N^T f dV`` and scatter over affine cells.

    This performs FEM load-vector assembly, even though it does not construct a
    stiffness matrix or solve. It must only be entered through
    :func:`assemble_body_load` with an official validator. Affine straight-sided
    cells only; curved high-order mappings are rejected.
    """
    family = prepared_mesh["family"]
    coordinates = prepared_mesh["nodes_integer"]
    denominator = prepared_mesh["integer_coordinate_denominator"]
    tet = family in {"TET4", "TET10"}
    if family not in {"TET4", "TET10", "HEX8", "HEX20"}:
        raise ValueError("unsupported element")
    if order not in {4, 8, 12}:
        raise ValueError("load integration supports only the prepared 4, 8 or 12 point rules")
    rule = quadrature.tetrahedron_duffy_rule(order) if tet else quadrature.hexahedron_rule(order)
    out = [0.0] * (3 * len(coordinates))
    for cell in prepared_mesh["connectivity_zero_based"]:
        origin, jacobian, determinant = _affine_cell_geometry(family, cell, coordinates, denominator)
        for r,s,t,w in rule:
            reference = (r,s,t)
            physical = tuple(origin[axis] + sum(jacobian[axis][q] * reference[q] for q in range(3))
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
