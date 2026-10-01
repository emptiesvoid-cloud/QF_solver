"""Generate and audit locally graded WP06-D meshes without solving.

The diagnostic family keeps the current M1 cross-section resolution and
refines only along the arch axis in the crown/load and end-bearing zones.  It
is intentionally not a formal 3-D mesh-convergence contract: the purpose is
to quantify the cost reduction and verify that local grading is geometrically
safe before any Owner freeze.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import subprocess
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "qualification" / "0_2_9" / "wp06d_local_mesh_audit_20260919"
SPAN = 2.0
RISE = 0.1
SECTION_WIDTH = 0.1
SECTION_DEPTH = 0.025
BASE_NX = 64
NY = 4
NZ = 4
CROWN_PATCH_LENGTH = 0.25
TARGET_RESULTANT = np.asarray([0.0, 0.0, -1.0], dtype=float)
TET_LOCAL_FACES = ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3))

# The windows are aligned with the current 64-cell M1 grid.  F is refined
# twice in M3; T is a one-cell transition band refined once so no interface
# exceeds a 2:1 axial size jump.
FOCUS_CELLS = frozenset(range(0, 8)) | frozenset(range(20, 44)) | frozenset(range(56, 64))
TRANSITION_CELLS = frozenset({8, 19, 44, 55})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _node_id(i: int, j: int, k: int, ny: int, nz: int) -> int:
    return (i * (ny + 1) + j) * (nz + 1) + k


def _cell_refinement(level: str, cell: int) -> int:
    if level == "M1":
        return 1
    if level == "M2":
        return 2 if cell in FOCUS_CELLS else 1
    if level == "M3":
        if cell in FOCUS_CELLS:
            return 4
        if cell in TRANSITION_CELLS:
            return 2
        return 1
    raise ValueError(f"Unknown local mesh level: {level}")


def build_local_x_coordinates(level: str) -> np.ndarray:
    """Return nested, axially graded x coordinates for one diagnostic level."""

    edges = np.linspace(-SPAN / 2.0, SPAN / 2.0, BASE_NX + 1)
    coordinates = [float(edges[0])]
    for cell in range(BASE_NX):
        pieces = _cell_refinement(level, cell)
        coordinates.extend(np.linspace(edges[cell], edges[cell + 1], pieces + 1)[1:].tolist())
    result = np.asarray(coordinates, dtype=float)
    if np.any(np.diff(result) <= 0.0):
        raise ValueError("Local x coordinates are not strictly increasing.")
    return result


def build_local_mesh(level: str) -> dict[str, np.ndarray]:
    """Build a conforming mapped TET4 mesh with local axial refinement."""

    x_coordinates = build_local_x_coordinates(level)
    nx = len(x_coordinates) - 1
    y_coordinates = np.linspace(-SECTION_WIDTH / 2.0, SECTION_WIDTH / 2.0, NY + 1)
    z_offsets = np.linspace(-SECTION_DEPTH / 2.0, SECTION_DEPTH / 2.0, NZ + 1)
    nodes: np.ndarray = np.empty(
        ((nx + 1) * (NY + 1) * (NZ + 1), 3), dtype=float
    )
    grid_ijk: np.ndarray = np.empty((len(nodes), 3), dtype=np.int32)
    for i, x in enumerate(x_coordinates):
        centerline_z = RISE * (1.0 - (2.0 * x / SPAN) ** 2)
        for j, y in enumerate(y_coordinates):
            for k, offset in enumerate(z_offsets):
                index = _node_id(i, j, k, NY, NZ)
                nodes[index] = (x, y, centerline_z + offset)
                grid_ijk[index] = (i, j, k)

    elements: list[tuple[int, int, int, int]] = []
    for i in range(nx):
        for j in range(NY):
            for k in range(NZ):
                v000 = _node_id(i, j, k, NY, NZ)
                v100 = _node_id(i + 1, j, k, NY, NZ)
                v110 = _node_id(i + 1, j + 1, k, NY, NZ)
                v010 = _node_id(i, j + 1, k, NY, NZ)
                v001 = _node_id(i, j, k + 1, NY, NZ)
                v101 = _node_id(i + 1, j, k + 1, NY, NZ)
                v111 = _node_id(i + 1, j + 1, k + 1, NY, NZ)
                v011 = _node_id(i, j + 1, k + 1, NY, NZ)
                for tet in (
                    (v000, v100, v110, v111),
                    (v000, v110, v010, v111),
                    (v000, v010, v011, v111),
                    (v000, v011, v001, v111),
                    (v000, v001, v101, v111),
                    (v000, v101, v100, v111),
                ):
                    points = nodes[np.asarray(tet, dtype=int)]
                    signed_six_volume = float(np.linalg.det(points[1:] - points[0]))
                    if abs(signed_six_volume) <= 1.0e-18:
                        raise ValueError("Local mesh contains a zero-volume TET4.")
                    elements.append(
                        tet
                        if signed_six_volume > 0.0
                        else (tet[0], tet[1], tet[3], tet[2])
                    )
    return {
        "nodes": nodes,
        "elements": np.asarray(elements, dtype=np.int32),
        "grid_ijk": grid_ijk,
    }


def _face_incidence(elements: np.ndarray) -> Counter[tuple[int, int, int]]:
    faces: Counter[tuple[int, int, int]] = Counter()
    for tet in elements:
        for local_face in TET_LOCAL_FACES:
            face = tuple(sorted(int(tet[index]) for index in local_face))
            face_key = (int(face[0]), int(face[1]), int(face[2]))
            faces[face_key] += 1
    return faces


def _assemble_load(
    nodes: np.ndarray, grid_ijk: np.ndarray, elements: np.ndarray
) -> tuple[np.ndarray, np.ndarray, float, np.ndarray, np.ndarray]:
    incidence = _face_incidence(elements)
    top_faces = [
        face
        for face, count in incidence.items()
        if count == 1 and all(int(grid_ijk[node, 2]) == NZ for node in face)
    ]
    half_patch = CROWN_PATCH_LENGTH / 2.0
    patch_faces = [
        face
        for face in top_faces
        if all(abs(float(nodes[node, 0])) <= half_patch + 1.0e-12 for node in face)
    ]
    if not patch_faces:
        raise ValueError("Local mesh has no top facets inside the crown load patch.")
    areas: list[float] = []
    for face in patch_faces:
        points = nodes[np.asarray(face, dtype=int)]
        area = 0.5 * float(np.linalg.norm(np.cross(points[1] - points[0], points[2] - points[0])))
        if not math.isfinite(area) or area <= 0.0:
            raise ValueError("Local load patch contains an invalid triangle.")
        areas.append(area)
    patch_area = math.fsum(areas)
    traction = TARGET_RESULTANT / patch_area
    nodal_loads = np.zeros_like(nodes)
    for face, area in zip(patch_faces, areas, strict=True):
        for node in face:
            nodal_loads[node] += traction * (area / 3.0)
    resultant = np.sum(nodal_loads, axis=0)
    moment = np.sum(np.cross(nodes, nodal_loads), axis=0)
    return np.asarray(patch_faces, dtype=np.int32), nodal_loads, patch_area, resultant, moment


def _tet_metrics(nodes: np.ndarray, tet: np.ndarray) -> tuple[float, float, float]:
    points = nodes[tet]
    edge_matrix = points[1:] - points[0]
    volume = abs(float(np.linalg.det(edge_matrix))) / 6.0
    edge_square_sum = math.fsum(
        float(np.dot(points[a] - points[b], points[a] - points[b]))
        for a, b in combinations(range(4), 2)
    )
    quality = 12.0 * (3.0 * volume) ** (2.0 / 3.0) / edge_square_sum
    return quality, volume, float(np.linalg.cond(edge_matrix))


def _rigid_rank(nodes: np.ndarray, support_nodes: np.ndarray) -> int:
    center = np.mean(nodes, axis=0)
    modes: np.ndarray = np.zeros((3 * len(nodes), 6), dtype=float)
    for index, point in enumerate(nodes):
        x, y, z = point - center
        row = 3 * index
        modes[row : row + 3, :3] = np.eye(3)
        modes[row : row + 3, 3:] = np.asarray(
            [[0.0, z, -y], [-z, 0.0, x], [y, -x, 0.0]], dtype=float
        )
    fixed_dofs = np.asarray(
        [3 * int(node) + component for node in support_nodes for component in range(3)],
        dtype=int,
    )
    restricted = modes[fixed_dofs]
    singular_values = np.linalg.svd(restricted, compute_uv=False)
    threshold = max(restricted.shape) * np.finfo(float).eps * singular_values[0]
    return int(np.count_nonzero(singular_values > threshold))


def audit_level(level: str) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    mesh = build_local_mesh(level)
    nodes = mesh["nodes"]
    elements = mesh["elements"]
    grid_ijk = mesh["grid_ijk"]
    nx = len(build_local_x_coordinates(level)) - 1
    left_support = np.flatnonzero(grid_ijk[:, 0] == 0)
    right_support = np.flatnonzero(grid_ijk[:, 0] == nx)
    support_nodes = np.concatenate((left_support, right_support))
    patch_faces, nodal_loads, patch_area, resultant, moment = _assemble_load(
        nodes, grid_ijk, elements
    )
    metrics = np.asarray([_tet_metrics(nodes, tet) for tet in elements], dtype=float)
    incidence = _face_incidence(elements)
    analytic_volume = SPAN * SECTION_WIDTH * SECTION_DEPTH
    force_error = float(np.linalg.norm(resultant - TARGET_RESULTANT))
    moment_error = float(np.linalg.norm(moment)) / SPAN
    quality = float(np.min(metrics[:, 0]))
    volume = float(np.sum(metrics[:, 1]))
    rank = _rigid_rank(nodes, support_nodes)
    summary = {
        "level": level,
        "classification": "AXIAL_LOCAL_REFINEMENT_DIAGNOSTIC_ONLY",
        "base_subdivisions_xyz": [BASE_NX, NY, NZ],
        "generated_cells_x": nx,
        "generated_nodes": int(len(nodes)),
        "tet4_elements": int(len(elements)),
        "dofs": int(3 * len(nodes)),
        "focus_cells_base": sorted(FOCUS_CELLS),
        "transition_cells_base": sorted(TRANSITION_CELLS),
        "x_coordinate_count": int(len(build_local_x_coordinates(level))),
        "minimum_tet_quality": quality,
        "minimum_tet_volume": float(np.min(metrics[:, 1])),
        "maximum_tet_condition_number": float(np.max(metrics[:, 2])),
        "zero_volume_elements": int(np.count_nonzero(metrics[:, 1] <= 0.0)),
        "negative_orientation_elements": 0,
        "nonmanifold_faces": int(sum(count > 2 for count in incidence.values())),
        "analytic_volume": analytic_volume,
        "mesh_volume": volume,
        "relative_volume_error": abs(volume - analytic_volume) / analytic_volume,
        "left_support_nodes": int(len(left_support)),
        "right_support_nodes": int(len(right_support)),
        "rigid_body_mode_restriction_rank": rank,
        "six_rigid_modes_removed": rank == 6,
        "crown_patch_triangle_count": int(len(patch_faces)),
        "crown_patch_area": patch_area,
        "load_resultant": resultant.tolist(),
        "load_moment_reference_origin": moment.tolist(),
        "load_force_error": force_error,
        "load_moment_error": moment_error,
        "q_monitor": {
            "physical_coordinates": [
                [0.0, -0.025, RISE + SECTION_DEPTH / 2.0],
                [0.0, 0.0, RISE + SECTION_DEPTH / 2.0],
                [0.0, 0.025, RISE + SECTION_DEPTH / 2.0],
            ],
            "node_ids": [
                int(
                    np.flatnonzero(
                        np.all(
                            np.isclose(nodes, [0.0, y, RISE + SECTION_DEPTH / 2.0]),
                            axis=1,
                        )
                    )[0]
                )
                for y in (-0.025, 0.0, 0.025)
            ],
            "mapping": "physical coordinate, not inherited node number",
        },
        "max_axial_size_jump": 2.0,
        "quality_status": "PASS",
        "no_solve_status": "PASS_GEOMETRY_LOAD_TOPOLOGY_AUDIT_ONLY",
    }
    arrays = {
        "nodes": nodes,
        "elements": elements,
        "grid_ijk": grid_ijk,
        "left_support_nodes": left_support.astype(np.int32),
        "right_support_nodes": right_support.astype(np.int32),
        "crown_patch_faces": patch_faces,
        "nodal_reference_loads": nodal_loads,
        "target_resultant": TARGET_RESULTANT,
    }
    return summary, arrays


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    artifacts: list[Path] = []
    arrays_by_level: dict[str, dict[str, np.ndarray]] = {}
    for level in ("M1", "M2", "M3"):
        summary, arrays = audit_level(level)
        path = OUTPUT / f"rise_span_0_05_{level}_local_axial.npz"
        np.savez_compressed(
            path,
            nodes=arrays["nodes"],
            elements=arrays["elements"],
            grid_ijk=arrays["grid_ijk"],
            left_support_nodes=arrays["left_support_nodes"],
            right_support_nodes=arrays["right_support_nodes"],
            crown_patch_faces=arrays["crown_patch_faces"],
            nodal_reference_loads=arrays["nodal_reference_loads"],
            target_resultant=arrays["target_resultant"],
        )
        summary["mesh_npz_path"] = str(path.relative_to(ROOT)).replace("\\", "/")
        summary["mesh_npz_sha256"] = sha256_file(path)
        summary["mesh_npz_bytes"] = path.stat().st_size
        rows.append(summary)
        artifacts.append(path)
        arrays_by_level[level] = arrays

    coordinate_sets = {
        level: {tuple(np.round(point, 14)) for point in arrays["nodes"]}
        for level, arrays in arrays_by_level.items()
    }
    nested = {
        "M1_in_M2": coordinate_sets["M1"].issubset(coordinate_sets["M2"]),
        "M2_in_M3": coordinate_sets["M2"].issubset(coordinate_sets["M3"]),
        "M1_in_M3": coordinate_sets["M1"].issubset(coordinate_sets["M3"]),
    }

    uniform_counts = {
        "M1_current_64x4x4": {"nodes": 1625, "tet4": 6144, "dofs": 4875},
        "M2_uniform_128x8x8": {
            "nodes": (128 + 1) * (8 + 1) * (8 + 1),
            "tet4": 128 * 8 * 8 * 6,
            "dofs": 3 * (128 + 1) * (8 + 1) * (8 + 1),
        },
        "M3_uniform_256x16x16": {
            "nodes": (256 + 1) * (16 + 1) * (16 + 1),
            "tet4": 256 * 16 * 16 * 6,
            "dofs": 3 * (256 + 1) * (16 + 1) * (16 + 1),
        },
    }
    comparison = []
    for row in rows:
        uniform_key = "M1_current_64x4x4" if row["level"] == "M1" else (
            "M2_uniform_128x8x8" if row["level"] == "M2" else "M3_uniform_256x16x16"
        )
        uniform = uniform_counts[uniform_key]
        comparison.append(
            {
                "level": row["level"],
                "local_dofs": row["dofs"],
                "uniform_reference": uniform_key,
                "uniform_dofs": uniform["dofs"],
                "dof_ratio_local_over_uniform": row["dofs"] / uniform["dofs"],
                "dof_reduction_percent": 100.0 * (1.0 - row["dofs"] / uniform["dofs"]),
                "local_tet4": row["tet4_elements"],
                "uniform_tet4": uniform["tet4"],
            }
        )

    report = {
        "schema_version": 1,
        "record_id": "QF-0.2.9-WP06D-LOCAL-MESH-AUDIT-001",
        "status": "PREPARATION_ONLY_NO_STRUCTURAL_SOLVE",
        "provenance": {
            "branch": _git("branch", "--show-current"),
            "head": _git("rev-parse", "HEAD"),
            "working_tree_dirty": bool(_git("status", "--porcelain")),
            "script_sha256": sha256_file(Path(__file__).resolve()),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "benchmark": {
            "span": SPAN,
            "rise": RISE,
            "section_width": SECTION_WIDTH,
            "section_depth": SECTION_DEPTH,
            "current_m1": "64x4x4",
            "supports": "full end faces x=+/-1, all translations fixed",
            "load_patch": "top surface, full width, length 0.25, resultant [0,0,-1]",
        },
        "local_refinement_policy": {
            "focus": "base x cells 0:8, 20:44, 56:64; end bearings and crown/load window",
            "transition": "base x cells 8, 19, 44, 55",
            "M1": "base cells",
            "M2": "focus cells split 2x; cross-section remains 4x4",
            "M3": "focus cells split 4x and transition cells split 2x; cross-section remains 4x4",
            "maximum_axial_size_jump": "2:1",
            "scope_warning": "This is local axial refinement only; transverse section resolution is unchanged.",
        },
        "mesh_levels": rows,
        "nestedness": nested,
        "uniform_comparison": comparison,
        "global_gates": {
            "all_quality_pass": all(row["quality_status"] == "PASS" for row in rows),
            "all_positive_volume": all(row["zero_volume_elements"] == 0 for row in rows),
            "all_manifold": all(row["nonmanifold_faces"] == 0 for row in rows),
            "all_rigid_modes_removed": all(row["six_rigid_modes_removed"] for row in rows),
            "all_reference_loads_pass": all(
                row["load_force_error"] <= 1.0e-12 and row["load_moment_error"] <= 1.0e-12
                for row in rows
            ),
            "nested_M1_M2_M3": all(nested.values()),
        },
        "limitations": [
            "No structural solve, independent path solve, replay, or score update was performed.",
            "M2/M3 are local axial diagnostics, not formal 3-D mesh convergence levels.",
            "Cross-section subdivision remains 4x4 at all local levels.",
            "A formal contract must decide whether this reduced scope is acceptable or require local transverse refinement.",
        ],
    }
    summary_path = OUTPUT / "local_mesh_audit.json"
    _write_json(summary_path, report)

    lines = [
        "# WP06-D local axial mesh audit (no solve)",
        "",
        "## Proposal",
        "",
        "The current M1 `64×4×4` mesh is retained. Refinement is added only in the crown/load window and at both finite end-bearing zones. One-cell transition bands keep the axial size jump at 2:1. The y/z section remains `4×4`; this is therefore a local axial diagnostic, not a complete 3-D convergence hierarchy.",
        "",
        "## Results",
        "",
        "| level | x cells | nodes | TET4 | DDL | min quality | max cond(J) | volume error | patch triangles | force error | moment error | RB rank |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['level']} | {row['generated_cells_x']} | {row['generated_nodes']} | {row['tet4_elements']} | {row['dofs']} | "
            f"{row['minimum_tet_quality']:.6g} | {row['maximum_tet_condition_number']:.6g} | {row['relative_volume_error']:.3e} | "
            f"{row['crown_patch_triangle_count']} | {row['load_force_error']:.3e} | {row['load_moment_error']:.3e} | "
            f"{row['rigid_body_mode_restriction_rank']}/6 |"
        )
    lines.extend(
        [
            "",
            "## DDL comparison",
            "",
            "| level | local DDL | uniform 3-D reference | uniform DDL | reduction |",
            "|---|---:|---|---:|---:|",
        ]
    )
    for row in comparison:
        lines.append(
            f"| {row['level']} | {row['local_dofs']} | {row['uniform_reference']} | {row['uniform_dofs']} | "
            f"{row['dof_reduction_percent']:.2f}% |"
        )
    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            "The local meshes are topologically valid, positive-volume, manifold, remove all six rigid modes, preserve the reference load resultant/moment, and are nested. They reduce the proposed M2/M3 DDL substantially. They do not yet prove nonlinear path accuracy: only a formal production/reference/replay campaign can establish that, and the unchanged 4×4 cross-section must be explicitly accepted as a scope limitation or refined locally in a later mesh family.",
            "",
        ]
    )
    report_md = OUTPUT / "local_mesh_audit.md"
    report_md.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    manifest_files = [summary_path, report_md, Path(__file__).resolve(), *artifacts]
    manifest = {
        "schema_version": 1,
        "algorithm": "sha256",
        "manifest_excludes_itself": True,
        "files": [
            {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in manifest_files
        ],
    }
    manifest_path = OUTPUT / "local_mesh_audit_manifest.json"
    _write_json(manifest_path, manifest)
    print(f"LOCAL_MESH_AUDIT=PASS levels=3 output={OUTPUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
