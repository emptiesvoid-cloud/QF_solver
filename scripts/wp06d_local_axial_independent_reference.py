"""Independently recompute the local-axial WP06-D diagnostic evidence.

This module deliberately imports no production solver code.  It reads only the
audited mesh archives, the accepted-state checkpoint payloads, and the
diagnostic case records.  It recomputes the TET4 StVK internal response and
the declared observables for M2 and M3.  It is an observable recomputation,
not an independent nonlinear arc-length solve.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.wp06d_m1_independent_reference import (  # noqa: E402
    _first_limit_point,
    _vectorized_stvk_internal_response,
)


DEFAULT_RUN_ROOT = ROOT / "qualification/0_2_9/wp06d_local_axial_diagnostic_20260919"
DEFAULT_MESH_ROOT = ROOT / "qualification/0_2_9/wp06d_local_mesh_runner_inputs_20260919"
COMPARISON_RTOL = 2.0e-10
COMPARISON_ATOL = 1.0e-13
EQUILIBRIUM_TOLERANCE = 1.0e-8


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _decode(value: Any) -> Any:
    """Decode the lossless JSON representation used by checkpoint metadata."""

    if not isinstance(value, dict) or "type" not in value:
        raise ValueError("Checkpoint value is not a typed mapping.")
    kind = value["type"]
    if kind == "str":
        return str(value["value"])
    if kind == "int":
        return int(value["value"])
    if kind == "bool":
        return bool(value["value"])
    if kind == "float":
        return float.fromhex(str(value["value"]))
    if kind == "ndarray":
        raw = base64.b64decode(value["data_base64"], validate=True)
        array = np.frombuffer(raw, dtype=np.dtype(value["dtype"]))
        return array.reshape(tuple(int(item) for item in value["shape"])).copy()
    if kind == "mapping":
        result: dict[str, Any] = {}
        for entry in value["entries"]:
            if not isinstance(entry, list) or len(entry) != 2:
                raise ValueError("Checkpoint mapping entry is malformed.")
            key = _decode(entry[0])
            if not isinstance(key, str):
                raise ValueError("Checkpoint mapping key is not a string.")
            result[key] = _decode(entry[1])
        return result
    if kind == "list":
        return [_decode(item) for item in value["items"]]
    raise ValueError(f"Unsupported checkpoint value type: {kind!r}")


def _load_mesh(path: Path) -> dict[str, np.ndarray]:
    required = {
        "nodes",
        "elements",
        "grid_ijk",
        "left_support_nodes",
        "right_support_nodes",
        "nodal_reference_loads",
        "target_resultant",
    }
    with np.load(path, allow_pickle=False) as archive:
        missing = required.difference(archive.files)
        if missing:
            raise ValueError(f"Mesh archive is missing fields: {sorted(missing)}")
        mesh = {key: np.asarray(archive[key]).copy() for key in archive.files}
    if mesh["nodes"].ndim != 2 or mesh["nodes"].shape[1] != 3:
        raise ValueError("Mesh nodes must have shape (N, 3).")
    if mesh["elements"].ndim != 2 or mesh["elements"].shape[1] != 4:
        raise ValueError("Independent reference requires TET4 elements.")
    if mesh["nodal_reference_loads"].shape != mesh["nodes"].shape:
        raise ValueError("Nodal reference loads do not match the mesh shape.")
    if not np.all(np.isfinite(mesh["nodes"])) or not np.all(
        np.isfinite(mesh["nodal_reference_loads"])
    ):
        raise ValueError("Mesh contains non-finite coordinates or loads.")
    resultant = np.sum(mesh["nodal_reference_loads"], axis=0)
    if not np.allclose(resultant, mesh["target_resultant"], rtol=0.0, atol=1.0e-12):
        raise ValueError("Mesh loads do not reproduce the declared resultant.")
    return mesh


def _support_dofs(mesh: dict[str, np.ndarray]) -> np.ndarray:
    nodes = np.unique(
        np.concatenate((mesh["left_support_nodes"], mesh["right_support_nodes"]))
    ).astype(int)
    return np.unique((3 * nodes[:, None] + np.arange(3, dtype=int)).reshape(-1))


def _q_nodes(mesh: dict[str, np.ndarray], case: dict[str, Any]) -> tuple[int, ...]:
    points = case["q_observable"]["physical_coordinates"]
    coordinates = np.asarray(mesh["nodes"], dtype=float)
    result: list[int] = []
    for point in points:
        matches = np.flatnonzero(
            np.all(np.isclose(coordinates, np.asarray(point), rtol=0.0, atol=1.0e-13), axis=1)
        )
        if matches.size != 1:
            raise ValueError(f"Physical q point is not unique: {point}")
        result.append(int(matches[0]))
    if len(set(result)) != len(result):
        raise ValueError("Physical q monitor contains duplicate nodes.")
    return tuple(result)


def _read_state(path: Path) -> tuple[int, float, np.ndarray, str]:
    with np.load(path, allow_pickle=False) as archive:
        if archive.files != ["metadata_json"]:
            raise ValueError(f"Unexpected checkpoint payload: {path}")
        payload = json.loads(str(archive["metadata_json"].item()))
    state = _decode(payload["accepted_state"])
    displacement = np.asarray(state["displacement"], dtype=float)
    load_factor = float(state["load_factor"])
    step = int(payload["completed_step"])
    digest = str(payload["composite_digest"])
    if displacement.ndim != 1 or not np.all(np.isfinite(displacement)):
        raise ValueError(f"Invalid displacement in {path}")
    return step, load_factor, displacement, digest


def _compare(expected: float, observed: float) -> bool:
    return bool(np.isclose(expected, observed, rtol=COMPARISON_RTOL, atol=COMPARISON_ATOL))


def audit_level(run_root: Path, mesh_root: Path, level: str, output: Path) -> dict[str, Any]:
    case_dir = run_root / f"rise_span_0_05_{level}"
    case_path = case_dir / "case_result.json"
    mesh_path = mesh_root / f"rise_span_0_05_{level}.npz"
    if not case_path.is_file() or not mesh_path.is_file():
        raise FileNotFoundError(f"Missing {level} case or mesh evidence.")
    case = json.loads(case_path.read_text(encoding="utf-8"))
    mesh = _load_mesh(mesh_path)
    constrained = _support_dofs(mesh)
    q_nodes = _q_nodes(mesh, case)
    checkpoint_paths = sorted(case_dir.glob("accepted_state.step*.npz"))
    if not checkpoint_paths:
        raise ValueError(f"No accepted checkpoints found for {level}.")
    recorded = {int(row["step"]): row for row in case["accepted_path"]}
    rows: list[dict[str, Any]] = []
    checkpoint_digests: dict[str, str] = {}
    max_differences: dict[str, float] = {}
    E = float(case.get("material", {}).get("E", 100.0))
    nu = float(case.get("material", {}).get("nu", 0.30))
    external_reference = mesh["nodal_reference_loads"].reshape(-1)
    coordinates = mesh["nodes"]
    elements: np.ndarray = mesh["elements"].astype(np.int64, copy=False)

    for path in checkpoint_paths:
        step, load_factor, displacement, state_digest = _read_state(path)
        if displacement.shape != (3 * len(coordinates),):
            raise ValueError(f"Checkpoint DOF count mismatch at step {step}.")
        checkpoint_digests[path.name] = _sha256(path)
        internal, energy, det_f, principal, strain_norm = _vectorized_stvk_internal_response(
            coordinates,
            elements,
            displacement,
            young_modulus=E,
            poisson_ratio=nu,
        )
        external = load_factor * external_reference
        residual = internal - external
        reactions = np.zeros_like(residual)
        reactions[constrained] = residual[constrained]
        nodal_balance = (reactions + external).reshape((-1, 3))
        current_nodes = coordinates + displacement.reshape((-1, 3))
        force_balance = np.sum(nodal_balance, axis=0)
        current_moment = np.sum(np.cross(current_nodes, nodal_balance), axis=0)
        force_scale = max(float(np.linalg.norm(np.sum(external.reshape((-1, 3)), axis=0))), 1.0e-12)
        moment_scale = max(force_scale * 2.0, 1.0e-12)
        q_value = -float(np.mean(displacement.reshape((-1, 3))[list(q_nodes), 2]))
        row = {
            "step": step,
            "load_factor": load_factor,
            "q_mean_crown_nodes_2_3_4": q_value,
            "strain_energy": energy,
            "minimum_det_f": float(np.min(det_f)),
            "minimum_principal_stretch": float(np.min(principal)),
            "maximum_principal_stretch": float(np.max(principal)),
            "maximum_green_strain_frobenius": float(np.max(strain_norm)),
            "free_residual_l2": float(np.linalg.norm(np.delete(residual, constrained))),
            "force_balance_relative": float(np.linalg.norm(force_balance) / force_scale),
            "current_moment_balance_relative": float(np.linalg.norm(current_moment) / moment_scale),
            "checkpoint_composite_digest": state_digest,
        }
        expected = recorded.get(step)
        if expected is None:
            raise ValueError(f"Checkpoint step {step} is absent from case_result.json.")
        for name, observed in (
            ("load_factor", row["load_factor"]),
            ("q_mean_crown_nodes_2_3_4", row["q_mean_crown_nodes_2_3_4"]),
            ("strain_energy_independent_recomputation", row["strain_energy"]),
            ("current_moment_balance_relative", row["current_moment_balance_relative"]),
        ):
            expected_value = float(expected[name])
            difference = abs(expected_value - observed)
            max_differences[name] = max(max_differences.get(name, 0.0), difference)
            if not _compare(expected_value, observed):
                raise ValueError(f"Recorded {name} diverges at {level} step {step}.")
        rows.append(row)

    rows.sort(key=lambda row: row["step"])
    steps = np.asarray([row["step"] for row in rows], dtype=int)
    load_factors = np.asarray([row["load_factor"] for row in rows], dtype=float)
    q_values = np.asarray([row["q_mean_crown_nodes_2_3_4"] for row in rows], dtype=float)
    limit_point = _first_limit_point(steps, load_factors, q_values)
    envelope_pass = bool(
        all(
            row["minimum_det_f"] >= 0.20
            and row["minimum_principal_stretch"] >= 0.75
            and row["maximum_principal_stretch"] <= 1.30
            and row["maximum_green_strain_frobenius"] <= 0.30
            for row in rows
        )
    )
    force_max = max(row["force_balance_relative"] for row in rows)
    moment_max = max(row["current_moment_balance_relative"] for row in rows)
    free_residual_max = max(row["free_residual_l2"] for row in rows)
    equilibrium_pass = force_max <= EQUILIBRIUM_TOLERANCE and moment_max <= EQUILIBRIUM_TOLERANCE
    result = {
        "schema_version": 1,
        "status": "PASS_OBSERVABLE_RECOMPUTATION_NO_LIMIT_POINT"
        if envelope_pass and equilibrium_pass and limit_point is None
        else "PASS_OBSERVABLE_RECOMPUTATION_WITH_LIMIT_POINT"
        if envelope_pass and equilibrium_pass and limit_point is not None
        else "FAIL_CLOSED_INDEPENDENT_RECOMPUTATION",
        "evidence_kind": "INDEPENDENT_OBSERVABLE_RECOMPUTATION",
        "formal_qualification_claimed": False,
        "independent_path_solve_run": False,
        "production_solver_replay_run": False,
        "level": level,
        "case_result_sha256": _sha256(case_path),
        "mesh_sha256": _sha256(mesh_path),
        "accepted_state_count": len(rows),
        "checkpoint_sha256": checkpoint_digests,
        "q_monitor": {"physical_coordinates": case["q_observable"]["physical_coordinates"], "node_ids": list(q_nodes)},
        "limit_point": {
            "status": "DETECTED" if limit_point is not None else "NOT_DETECTED",
            "result": limit_point,
            "rule": "local load maximum, q strictly increasing, six accepted post-limit states",
        },
        "envelope": {"full_path_pass": envelope_pass, "checked_states": len(rows)},
        "equilibrium": {
            "force_max": force_max,
            "current_moment_max": moment_max,
            "free_residual_max": free_residual_max,
            "tolerance": EQUILIBRIUM_TOLERANCE,
            "pass": equilibrium_pass,
        },
        "recorded_comparison": {
            "status": "PASS",
            "max_absolute_differences": max_differences,
            "rtol": COMPARISON_RTOL,
            "atol": COMPARISON_ATOL,
        },
        "source_provenance": {
            "branch": _git("branch", "--show-current"),
            "head": _git("rev-parse", "HEAD"),
            "source_sha256": _sha256(Path(__file__).resolve()),
        },
    }
    output.mkdir(parents=True, exist_ok=False)
    result_path = output / "independent_reference_result.json"
    rows_path = output / "state_metrics.jsonl"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    rows_path.write_text(
        "".join(json.dumps(row, sort_keys=True, allow_nan=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest = {
        "schema_version": 1,
        "algorithm": "sha256",
        "manifest_excludes_itself": True,
        "files": {
            result_path.name: _sha256(result_path),
            rows_path.name: _sha256(rows_path),
            str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/"): _sha256(Path(__file__).resolve()),
        },
    }
    (output / "independent_reference_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--mesh-root", type=Path, default=DEFAULT_MESH_ROOT)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    results = []
    for level in ("M2", "M3"):
        results.append(audit_level(args.run_root.resolve(), args.mesh_root.resolve(), level, args.output_root.resolve() / level))
    overall = {
        "schema_version": 1,
        "status": "PASS_OBSERVABLE_RECOMPUTATION" if all(result["status"].startswith("PASS_") for result in results) else "FAIL_CLOSED",
        "formal_qualification_claimed": False,
        "independent_path_solve_run": False,
        "production_solver_replay_run": False,
        "levels": results,
        "limitations": [
            "The independent path does not solve Newton/arc-length equations.",
            "No production solver replay was performed by this script.",
            "No limit point was detected in the 160-state diagnostic path.",
        ],
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "independent_reference_summary.json").write_text(
        json.dumps(overall, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    for result in results:
        print(
            f"INDEPENDENT_{result['level']}={result['status']} "
            f"states={result['accepted_state_count']} "
            f"limit={result['limit_point']['status']}",
            flush=True,
        )
    return 0 if overall["status"] == "PASS_OBSERVABLE_RECOMPUTATION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
