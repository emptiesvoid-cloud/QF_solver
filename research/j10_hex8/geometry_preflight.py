"""Geometry-only preflight for the J10 J7-matched HEX8-SRI sweep."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
import sys

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from solveur.elements.solid.hex8 import Hex8Element  # noqa: E402

CONTRACT_PATH = ROOT / "research/j10_hex8/contracts/geometry_preflight_contract.json"
INPUT_STATE_PATH = ROOT / "research/j8_hex8/inputs/near_degenerate_nu0495_nx4_state.npz"
CASE_SPEC_PATH = ROOT / "research/j8_hex8/inputs/j7_hex8_sri_global_cases.json"
ALPHA_LEVELS = (0.0, 0.05, 0.10, 0.15)
LENGTH_M = 20.0
MID_PLANE_Y_M = 0.5
MID_PLANE_Z_M = 0.02
LOCAL_THICKNESS_M = 0.04


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(bytes((13, 10)), bytes((10,)))).hexdigest()


def _warped_coordinates(coordinates: np.ndarray, interior_nodes: np.ndarray, alpha: float) -> np.ndarray:
    warped = np.asarray(coordinates, dtype=np.float64).copy()
    x = warped[interior_nodes, 0]
    warped[interior_nodes, 2] += alpha * LOCAL_THICKNESS_M * np.sin(np.pi * x / LENGTH_M)
    return warped


def run_preflight(output_path: Path | None = None) -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    for item in contract["source_identity"]:
        if _canonical_sha256(ROOT / item["path"]) != item["sha256"]:
            raise RuntimeError(f"Geometry preflight source differs from frozen identity: {item['path']}")
    if _sha256(INPUT_STATE_PATH) != contract["input"]["sha256"]:
        raise RuntimeError("Archived J7 state differs from the frozen geometry-preflight input")
    if _canonical_sha256(CASE_SPEC_PATH) != contract["input"]["case_spec_canonical_sha256"]:
        raise RuntimeError("Archived J7 case definition differs from the frozen geometry-preflight input")
    with np.load(INPUT_STATE_PATH, allow_pickle=False) as archive:
        coordinates = np.asarray(archive["coordinates_m"], dtype=np.float64)
        connectivity = np.asarray(archive["connectivity"], dtype=np.int64)

    interior = (
        (coordinates[:, 0] > 0.0)
        & (coordinates[:, 0] < LENGTH_M)
        & np.isclose(coordinates[:, 1], MID_PLANE_Y_M, rtol=0.0, atol=1.0e-12)
        & np.isclose(coordinates[:, 2], MID_PLANE_Z_M, rtol=0.0, atol=1.0e-12)
    )
    interior_nodes = np.flatnonzero(interior)
    if interior_nodes.size != 3:
        raise RuntimeError(f"Expected the three strictly interior J7 logical nodes; found {interior_nodes.size}")
    boundary_nodes = np.flatnonzero(~interior)
    boundary_before = coordinates[boundary_nodes].copy()
    z_extent_before = [float(np.min(coordinates[:, 2])), float(np.max(coordinates[:, 2]))]
    rows: list[dict[str, Any]] = []
    for alpha in ALPHA_LEVELS:
        warped = _warped_coordinates(coordinates, interior_nodes, alpha)
        determinants = np.asarray([
            Hex8Element.jacobian_determinant(warped[row], point)
            for row in connectivity
            for point in Hex8Element.integration_points
        ], dtype=np.float64)
        unchanged_boundary = bool(np.array_equal(warped[boundary_nodes], boundary_before))
        z_extent_after = [float(np.min(warped[:, 2])), float(np.max(warped[:, 2]))]
        rows.append({
            "alpha": alpha,
            "maximum_interior_shift_m": float(np.max(np.abs(warped[interior_nodes, 2] - coordinates[interior_nodes, 2]))),
            "minimum_gauss_jacobian_m3": float(np.min(determinants)),
            "maximum_gauss_jacobian_m3": float(np.max(determinants)),
            "all_gauss_jacobians_positive": bool(np.isfinite(determinants).all() and np.all(determinants > 0.0)),
            "exterior_node_coordinates_unchanged": unchanged_boundary,
            "z_bounding_box_m": z_extent_after,
            "z_bounding_box_unchanged": bool(np.array_equal(np.asarray(z_extent_after), np.asarray(z_extent_before))),
        })
    result = {
        "schema": "qf-j10-hex8-geometry-preflight-v1",
        "classification": "GEOMETRY_ONLY_PRECHECK_NOT_FEM",
        "input_path": "research/j8_hex8/inputs/near_degenerate_nu0495_nx4_state.npz",
        "input_sha256": _sha256(INPUT_STATE_PATH),
        "contract_sha256": _canonical_sha256(CONTRACT_PATH),
        "mesh": {"node_count": int(len(coordinates)), "element_count": int(len(connectivity)), "interior_node_ids": interior_nodes.tolist()},
        "normalization": {
            "local_thickness_scale_m": LOCAL_THICKNESS_M,
            "interpretation": "top-to-bottom coordinate difference at fixed x,y; the J7 bounding-box z extent is 0.046 m because the outer surface is also skewed",
            "z_bounding_box_m": z_extent_before,
        },
        "criteria": {
            "positive_finite_gauss_jacobians": "required for every candidate",
            "all_exterior_node_coordinates_bitwise_unchanged": "required for every candidate",
            "no_matrix_assembly_or_solve": True,
        },
        "levels": rows,
        "preflight_status": "PASS_GEOMETRY_ONLY" if all(
            row["all_gauss_jacobians_positive"] and row["exterior_node_coordinates_unchanged"] for row in rows
        ) else "REVISE_CANDIDATES_BEFORE_FEM",
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    target = ROOT / "research/j10_hex8/geometry_preflight_result.json"
    print(json.dumps(run_preflight(target), indent=2, sort_keys=True))
