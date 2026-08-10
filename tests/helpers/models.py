"""Reusable model writers for integration tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_model(path: Path) -> None:
    _write(path, _tet4_static_model())


def write_low_quality_model(path: Path) -> None:
    model = _tet4_static_model()
    model["nodes"] = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0.01]]
    _write(path, model)


def write_iterative_model(path: Path) -> None:
    model = _tet4_static_model()
    model["analysis"] = {"type": "linear_static", "method": "bicgstab", "preconditioner": "jacobi"}
    _write(path, model)


def write_modal_model(path: Path) -> None:
    model = _tet4_static_model()
    model["analysis"] = {"type": "modal", "method": "eigh", "modes": 2}
    model["materials"]["steel"]["density"] = 7800.0
    model.pop("loads")
    _write(path, model)


def tet10_nodes() -> list[list[float]]:
    return [
        [0, 0, 0],
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
        [0.5, 0, 0],
        [0.5, 0.5, 0],
        [0, 0.5, 0],
        [0, 0, 0.5],
        [0.5, 0, 0.5],
        [0, 0.5, 0.5],
    ]


def tet10_fixed_face() -> list[dict[str, object]]:
    return [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in [0, 2, 3, 6, 7, 9]]


def write_tet10_model(path: Path) -> None:
    _write(
        path,
        {
            "analysis": "linear_static",
            "nodes": tet10_nodes(),
            "elements": [{"type": "TET10", "nodes": list(range(10)), "material": "steel"}],
            "materials": {"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}},
            "fixed_dofs": tet10_fixed_face(),
            "loads": [{"node": 1, "dof": "UX", "value": 1000.0}],
        },
    )


def write_tet10_modal_model(path: Path) -> None:
    _write(
        path,
        {
            "analysis": {"type": "modal", "method": "eigh", "modes": 3},
            "nodes": tet10_nodes(),
            "elements": [{"type": "TET10", "nodes": list(range(10)), "material": "steel"}],
            "materials": {"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}},
            "fixed_dofs": tet10_fixed_face(),
        },
    )


def write_tet10_nonlinear_model(path: Path) -> None:
    _write(
        path,
        {
            "analysis": _nonlinear_analysis("newton_line_search"),
            "nodes": tet10_nodes(),
            "elements": [{"type": "TET10", "nodes": list(range(10)), "material": "rubber"}],
            "materials": _rubber_material(),
            "fixed_dofs": tet10_fixed_face(),
            "loads": [{"node": 1, "dof": "UX", "value": 10.0}],
        },
    )


def write_nonlinear_model(path: Path) -> None:
    model = _tet4_nonlinear_model("newton_raphson")
    _write(path, model)


def write_arc_length_model(path: Path) -> None:
    model = _tet4_nonlinear_model("arc_length")
    model["analysis"]["max_arc_steps"] = 12
    model["analysis"]["target_load_factor"] = 1.0
    _write(path, model)


def write_shell_model(path: Path) -> None:
    _write(
        path,
        {
            "analysis": "linear_static",
            "nodes": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]],
            "elements": [{"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "skin"}],
            "materials": {"skin": {"type": "shell_isotropic", "E": 1000.0, "nu": 0.25, "t": 0.1}},
            "fixed_dofs": [
                {"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]},
                {"node": 3, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]},
            ],
            "loads": [
                {"node": 1, "dof": "UX", "value": 1.0},
                {"node": 2, "dof": "UX", "value": 1.0},
            ],
        },
    )


def _tet4_static_model() -> dict[str, Any]:
    return {
        "analysis": "linear_static",
        "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        "materials": {"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
        "fixed_dofs": [
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        "loads": [{"node": 1, "dof": "UX", "value": 1000.0}],
    }


def _tet4_nonlinear_model(method: str) -> dict[str, Any]:
    return {
        "analysis": _nonlinear_analysis(method),
        "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "rubber"}],
        "materials": _rubber_material(),
        "fixed_dofs": [
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        "loads": [{"node": 1, "dof": "UX", "value": 10.0}],
    }


def _nonlinear_analysis(method: str) -> dict[str, Any]:
    return {
        "type": "nonlinear_static",
        "method": method,
        "load_steps": 5,
        "max_iterations": 50,
        "tolerance": 1.0e-9,
    }


def _rubber_material() -> dict[str, dict[str, float | str]]:
    return {"rubber": {"type": "nonlinear_isotropic_3d", "E": 1000.0, "nu": 0.25, "hardening": 1.0e6}}


def _write(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")
