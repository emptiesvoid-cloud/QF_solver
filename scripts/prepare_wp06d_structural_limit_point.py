"""Phase-0 guard and metadata helpers for the WP06-D contract.

This module deliberately cannot launch a structural or external solve.  The
Phase-1 harness will consume the frozen JSON contract after Owner
authorization and governing-branch integration.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


STRUCTURAL_SOLVES_ENABLED = False
EXTERNAL_SOLVER_ENABLED = False
ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification" / "0_2_9" / "wp06d_structural_limit_point_contract.json"
BASE_NODES = np.asarray(
    [
        [-1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, -0.05, 0.20],
        [0.0, 0.05, 0.20],
        [0.0, 0.0, 0.25],
    ],
    dtype=float,
)
BASE_ELEMENTS = ((0, 2, 3, 4), (1, 3, 2, 4))
TARGET_RESULTANT = np.asarray([0.0, 0.0, -1.0], dtype=float)
LOAD_NODE = 4
MESH_LEVELS = {"M1": 0, "M2": 1, "M3": 2}


def _signed_volume(nodes: np.ndarray, element: tuple[int, int, int, int]) -> float:
    points = nodes[np.asarray(element, dtype=int)]
    return float(np.linalg.det((points[1:] - points[0]).T) / 6.0)


def _orient_positive(nodes: np.ndarray, element: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    volume = _signed_volume(nodes, element)
    if volume == 0.0:
        raise ValueError("WP06-D refinement produced a zero-volume TET4.")
    return element if volume > 0.0 else (element[0], element[1], element[3], element[2])


def refine_tet4_mesh(
    nodes: np.ndarray,
    elements: tuple[tuple[int, int, int, int], ...],
) -> tuple[np.ndarray, tuple[tuple[int, int, int, int], ...]]:
    """Apply the frozen global sorted-edge 8-subtet refinement once."""
    base_nodes = np.asarray(nodes, dtype=float)
    edge_keys = sorted(
        {
            tuple(sorted(edge))
            for element in elements
            for edge in (
                (element[0], element[1]),
                (element[0], element[2]),
                (element[0], element[3]),
                (element[1], element[2]),
                (element[1], element[3]),
                (element[2], element[3]),
            )
        }
    )
    midpoint_ids = {edge: base_nodes.shape[0] + index for index, edge in enumerate(edge_keys)}
    midpoints = np.asarray(
        [(base_nodes[a] + base_nodes[b]) * 0.5 for a, b in edge_keys],
        dtype=float,
    )
    refined_nodes = np.vstack((base_nodes, midpoints))
    refined_elements: list[tuple[int, int, int, int]] = []
    for a, b, c, d in elements:
        ab, ac, ad = midpoint_ids[tuple(sorted((a, b)))], midpoint_ids[tuple(sorted((a, c)))], midpoint_ids[
            tuple(sorted((a, d)))
        ]
        bc, bd, cd = midpoint_ids[tuple(sorted((b, c)))], midpoint_ids[tuple(sorted((b, d)))], midpoint_ids[
            tuple(sorted((c, d)))
        ]
        children = (
            (a, ab, ac, ad),
            (b, ab, bc, bd),
            (c, ac, bc, cd),
            (d, ad, bd, cd),
            (ab, ac, ad, cd),
            (ab, ac, bc, cd),
            (ab, ad, bd, cd),
            (ab, bc, bd, cd),
        )
        refined_elements.extend(_orient_positive(refined_nodes, child) for child in children)
    return refined_nodes, tuple(refined_elements)


def generate_mesh(level: str) -> tuple[np.ndarray, tuple[tuple[int, int, int, int], ...]]:
    """Generate one frozen WP06-D mesh without assembling or solving mechanics."""
    if level not in MESH_LEVELS:
        raise ValueError(f"Unknown WP06-D mesh level: {level}")
    nodes = BASE_NODES.copy()
    elements = tuple(_orient_positive(nodes, element) for element in BASE_ELEMENTS)
    for _ in range(MESH_LEVELS[level]):
        nodes, elements = refine_tet4_mesh(nodes, elements)
    return nodes, elements


def symmetry_face_nodes(nodes: np.ndarray) -> tuple[int, ...]:
    """Return nodes on the closed parent face (2, 3, 4), deterministically."""
    face = nodes[np.asarray((2, 3, 4), dtype=int)]
    edge_a = face[1] - face[0]
    edge_b = face[2] - face[0]
    gram = np.asarray([[edge_a @ edge_a, edge_a @ edge_b], [edge_a @ edge_b, edge_b @ edge_b]])
    selected: list[int] = []
    for index, point in enumerate(nodes):
        coefficients = np.linalg.solve(gram, np.asarray([edge_a @ (point - face[0]), edge_b @ (point - face[0])]))
        barycentric = (1.0 - coefficients.sum(), coefficients[0], coefficients[1])
        if abs(point[0]) <= 1.0e-14 and min(barycentric) >= -1.0e-14 and abs(point[2] - (0.20 + 0.05 * barycentric[2])) <= 1.0e-14:
            selected.append(index)
    return tuple(selected)


def assemble_reference_load(nodes: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Assemble the fixed geometric point load and return resultant/moment."""
    loads = np.zeros_like(nodes)
    loads[LOAD_NODE] = TARGET_RESULTANT
    resultant = loads.sum(axis=0)
    moment = np.cross(nodes, loads).sum(axis=0)
    return loads, resultant, moment


def load_contract() -> dict[str, Any]:
    """Load the machine-readable frozen contract without executing mechanics."""
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def assert_phase0_guard(*, owner_authorized: bool = False) -> None:
    """Fail closed for any attempted Phase-1 execution from this module."""
    if not owner_authorized or not STRUCTURAL_SOLVES_ENABLED or not EXTERNAL_SOLVER_ENABLED:
        raise RuntimeError(
            "WP06-D is Phase-0 preparation only: structural and external execution are disabled."
        )


def validate_contract() -> dict[str, Any]:
    """Return basic contract metadata; no mesh or solver work is performed."""
    contract = load_contract()
    required = {
        "record_id",
        "benchmark",
        "mesh_series",
        "continuation_policy",
        "reference_path",
        "failure_classifications",
        "execution_guard",
    }
    missing = sorted(required.difference(contract))
    if missing:
        raise ValueError(f"WP06-D contract is missing required sections: {missing}")
    execution_guard = contract["execution_guard"]
    if not isinstance(execution_guard, dict) or any(
        (
            execution_guard.get("structural_solves_enabled") is not False,
            execution_guard.get("reference_solver_enabled") is not False,
            execution_guard.get("external_solver_enabled") is not False,
            execution_guard.get("phase") != "PHASE_0_PREPARATION",
        )
    ):
        raise ValueError("WP06-D Phase-0 execution guard is not fail-closed.")
    return {
        "record_id": contract["record_id"],
        "mesh_levels": [row["level"] for row in contract["mesh_series"]],
        "structural_solves_enabled": STRUCTURAL_SOLVES_ENABLED,
        "external_solver_enabled": EXTERNAL_SOLVER_ENABLED,
    }


if __name__ == "__main__":
    print(json.dumps(validate_contract(), sort_keys=True))
