"""Small controlled source tree for V&V benchmark-import tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_cantilever_benchmark_source(root: Path) -> Path:
    """Write four tiny TET4 benchmark levels with a second-order error trend."""
    source = root / "BM-SOL-CANTILEVER-001"
    source.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for level, (size, error) in enumerate(((0.4, 0.16), (0.2, 0.04), (0.1, 0.01), (0.05, 0.0025)), start=1):
        prefix = f"tet4_h{level}"
        tip = -(1.0 - error)
        _write_json(source / f"{prefix}.model.json", _model())
        _write_json(source / f"{prefix}.json", _result(tip))
        (source / f"{prefix}.vtu").write_text("<VTKFile type=\"UnstructuredGrid\"/>", encoding="utf-8")
        rows.append(
            {
                "level": level,
                "mesh_size": size,
                "node_count": 4,
                "element_count": 1,
                "tip_uz": tip,
                "relative_error": error,
                "free_relative_residual": 1.0e-12,
            }
        )
    _write_json(
        source / "benchmark_summary.json",
        {
            "benchmark": {"identifier": "BM-SOL-CANTILEVER-001"},
            "metrics": {"reference_tip_uz": -1.0, "tet4_h_convergence": rows},
        },
    )
    return source


def build_torsion_benchmark_source(root: Path) -> Path:
    """Write four tiny torsion levels with monotone first-order twist errors."""
    source = root / "BM-SOL-TET4-TORSION-001"
    source.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    reference_twist = 1.0
    model = _torsion_model()
    for level, (size, error) in enumerate(((0.4, 0.16), (0.2, 0.08), (0.1, 0.04), (0.05, 0.02)), start=1):
        prefix = f"h{level}"
        twist = reference_twist * (1.0 - error)
        _write_json(source / f"{prefix}.model.json", model)
        _write_json(source / f"{prefix}.json", {"status": "ok"})
        _write_json(source / f"{prefix}.setup.json", {"analysis": {"type": "linear_static"}})
        (source / f"{prefix}.msh").write_text("$MeshFormat\n4.1 0 8\n$EndMeshFormat\n", encoding="utf-8")
        _write_tiny_vtu(source / f"{prefix}.vtu", model, twist)
        rows.append(
            {
                "level": level,
                "mesh_size": size,
                "node_count": 4,
                "element_count": 1,
                "twist_angle": twist,
                "reference_twist_angle": reference_twist,
                "relative_twist_error": error,
                "relative_stress_l2_error": 0.8 * error**0.5,
                "applied_torque": 1000.0,
                "resultant_force_norm": 1.0e-12,
                "free_relative_residual": 1.0e-12,
            }
        )
    _write_json(
        source / "benchmark_summary.json",
        {
            "benchmark": {"identifier": "BM-SOL-TET4-TORSION-001"},
            "metrics": {
                "reference_twist_angle": reference_twist,
                "shear_modulus": 1.0,
                "polar_moment": 1.0,
                "torsion_h_convergence": rows,
            },
        },
    )
    return source


def _model() -> dict[str, Any]:
    return {
        "nodes": [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
    }


def _torsion_model() -> dict[str, Any]:
    return {
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.5, 0.0], [1.0, 0.0, 0.5], [0.0, 0.3, 0.2]],
        "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
    }


def _write_tiny_vtu(path: Path, model: dict[str, Any], twist: float) -> None:
    nodes = model["nodes"]
    displacement: list[float] = []
    for x, y, z in nodes:
        angle = twist * x
        displacement.extend((0.0, -angle * z, angle * y))
    vectors = " ".join(str(value) for value in displacement)
    coordinates = " ".join(str(value) for node in nodes for value in node)
    path.write_text(
        "<?xml version=\"1.0\"?>\n"
        "<VTKFile type=\"UnstructuredGrid\"><UnstructuredGrid>"
        "<Piece NumberOfPoints=\"4\" NumberOfCells=\"1\">"
        f"<Points><DataArray NumberOfComponents=\"3\">{coordinates}</DataArray></Points>"
        f"<PointData><DataArray Name=\"Displacement\" NumberOfComponents=\"3\">{vectors}</DataArray></PointData>"
        "<Cells><DataArray Name=\"connectivity\">0 1 2 3</DataArray>"
        "<DataArray Name=\"offsets\">4</DataArray><DataArray Name=\"types\">10</DataArray></Cells>"
        "</Piece></UnstructuredGrid></VTKFile>\n",
        encoding="utf-8",
    )


def _result(tip: float) -> dict[str, Any]:
    return {
        "ndof": 12,
        "displacements": [
            {"node": 0, "dofs": {"UX": 0.0, "UY": 0.0, "UZ": 0.0}},
            {"node": 1, "dofs": {"UX": 0.0, "UY": 0.0, "UZ": tip}},
            {"node": 2, "dofs": {"UX": 0.0, "UY": 0.0, "UZ": 0.0}},
            {"node": 3, "dofs": {"UX": 0.0, "UY": 0.0, "UZ": 0.0}},
        ],
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")
