"""Build non-executable QF model templates from prepared meshes; no FEM execution."""
from __future__ import annotations

from experiments.wp12_vv3d_adaptive.oracle import E_PA, NU


def build_template(mesh: dict) -> dict:
    """Build geometry/material/zero-BC data; the variable load is deliberately missing.

    The returned wrapper is not a solver model or an authorization. It deliberately
    lacks a usable load vector and cannot establish the manufactured problem.
    """
    if mesh.get("schema") != "qf-wp12-vv3d-mesh-v1":
        raise ValueError("unsupported prepared mesh schema")
    family=mesh["family"]
    if family not in {"TET4","TET10","HEX8","HEX20"}:
        raise ValueError("unsupported element family")
    denominator=mesh["integer_coordinate_denominator"]
    if isinstance(denominator, bool) or not isinstance(denominator,int) or denominator <= 0:
        raise ValueError("invalid coordinate scale")
    return {"status": "INCOMPLETE_VARIABLE_BODY_FORCE_NOT_ASSEMBLED", "executable": False,
        "missing": ["consistent body-force vector", "registered nodeid", "authorized manifest", "controller binding"],
        "model_template": {"nodes": [[v/denominator for v in point] for point in mesh["nodes_integer"]],
            "elements": [{"type":family,"nodes":cell,"material":"mms"} for cell in mesh["connectivity_zero_based"]],
            "materials": {"mms":{"type":"isotropic_3d","E":E_PA,"nu":NU}},
            "fixed_dofs": [{"node":node,"dofs":["UX","UY","UZ"]}
                           for node in mesh["fixed_node_ids_all_components"]],
            "loads": None, "analysis":"linear_static", "units":{"length":"m","force":"N","stress":"Pa"}}}
