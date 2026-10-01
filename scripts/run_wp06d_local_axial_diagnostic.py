"""Run the audited local-axial WP06-D meshes as diagnostics only.

M1 is reused only for the existing free-DOF arc-length normalization.  The
runner executes local M2 and then local M3 sequentially, consumes only the
audited NPZ meshes, and never claims formal WP06-D evidence.  M3 is not
started when M2 has a pre-solve/solve failure or an envelope failure.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
LOCAL_AUDIT_ROOT = ROOT / "qualification/0_2_9/wp06d_local_mesh_audit_20260919"
INPUT_ROOT = ROOT / "qualification/0_2_9/wp06d_local_mesh_runner_inputs_20260919"
OUT = ROOT / "qualification/0_2_9/wp06d_local_axial_diagnostic_20260919"
BASE_RUNNER = ROOT / "scripts/run_wp06d_low_strain_exploratory.py"
GEOMETRY = "rise_span_0_05"
RATIO = 0.05
LEVELS = ("M2", "M3")
CASE_ORDER = tuple((GEOMETRY, RATIO, level) for level in LEVELS)
TOP_Z = 0.1 + 0.025 / 2.0
Q_POINTS = ((0.0, -0.025, TOP_Z), (0.0, 0.0, TOP_Z), (0.0, 0.025, TOP_Z))


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _write_json(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
    temporary.replace(path)


def _import_base() -> Any:
    spec = importlib.util.spec_from_file_location("wp06d_local_axial_base", BASE_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {BASE_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _prepare_input_aliases() -> None:
    """Create immutable-name aliases for the already audited local NPZ files."""

    if not LOCAL_AUDIT_ROOT.is_dir():
        raise FileNotFoundError(LOCAL_AUDIT_ROOT)
    INPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for level in ("M1", "M2", "M3"):
        source = LOCAL_AUDIT_ROOT / f"rise_span_0_05_{level}_local_axial.npz"
        target = INPUT_ROOT / f"{GEOMETRY}_{level}.npz"
        if not source.is_file():
            raise FileNotFoundError(source)
        if target.exists():
            if _hash(target) != _hash(source):
                raise RuntimeError(f"Refusing to reuse divergent local input alias: {target}")
        else:
            shutil.copy2(source, target)
    manifest_source = LOCAL_AUDIT_ROOT / "local_mesh_audit_manifest.json"
    manifest_target = INPUT_ROOT / "candidate_mesh_audit_manifest.json"
    if manifest_target.exists():
        if _hash(manifest_target) != _hash(manifest_source):
            raise RuntimeError("Refusing to reuse divergent local mesh manifest alias.")
    else:
        shutil.copy2(manifest_source, manifest_target)


def _q_nodes(mesh: dict[str, np.ndarray]) -> tuple[int, ...]:
    nodes = np.asarray(mesh["nodes"], dtype=float)
    result: list[int] = []
    for point in Q_POINTS:
        matches = np.flatnonzero(np.all(np.isclose(nodes, point, rtol=0.0, atol=1.0e-13), axis=1))
        if matches.size != 1:
            raise RuntimeError(f"Local q point is not unique: {point}")
        result.append(int(matches[0]))
    return tuple(result)


def _configure_base(base: Any) -> None:
    base.MESH_ROOT = INPUT_ROOT
    base.OUT = OUT
    base.CASE_DIR = OUT
    base.GEOMETRIES = ((GEOMETRY, RATIO),)
    base.LEVELS = LEVELS
    base.CASE_ORDER = CASE_ORDER
    base.MAX_ACCEPTED_STEPS = 160
    base.REFERENCE_FREE_DOFS.clear()

    original_state_metrics = base._state_metrics

    def state_metrics(
        mesh: dict[str, np.ndarray],
        displacement: np.ndarray,
        load_factor: float,
        constrained: np.ndarray,
        center_node: int,
    ) -> dict[str, Any]:
        state = original_state_metrics(
            mesh, displacement, load_factor, constrained, center_node
        )
        node_ids = _q_nodes(mesh)
        vector = np.asarray(displacement, dtype=float).reshape((-1, 3))
        q_mean = -float(np.mean(vector[list(node_ids), 2]))
        if not np.isfinite(q_mean):
            raise RuntimeError("Local mean-crown q is non-finite.")
        state["q_control_centerline_crown"] = state["q_centerline_crown"]
        state["q_mean_crown_nodes_2_3_4"] = q_mean
        state["q_centerline_crown"] = q_mean
        return state

    base._state_metrics = state_metrics


def _metadata(base: Any) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "study": "WP06-D local axial M2/M3 diagnostic",
        "classification": "DIAGNOSTIC_ONLY_NOT_FORMAL_REQUALIFICATION",
        "launch_authorization": "Explicit user instruction in current conversation",
        "branch": _git("branch", "--show-current"),
        "head_sha": _git("rev-parse", "HEAD"),
        "working_tree_dirty_at_start": bool(_git("status", "--porcelain")),
        "runner_sha256": _hash(Path(__file__).resolve()),
        "base_runner_sha256": _hash(BASE_RUNNER),
        "local_mesh_audit_manifest_sha256": _hash(
            LOCAL_AUDIT_ROOT / "local_mesh_audit_manifest.json"
        ),
        "benchmark": {
            "span": 2.0,
            "rise": 0.1,
            "section_width": 0.1,
            "section_depth": 0.025,
            "supports": "full end faces x=+/-1, all translational DOFs fixed",
            "load_resultant": [0.0, 0.0, -1.0],
        },
        "levels_and_order": list(LEVELS),
        "m1_role": "M1 local mesh is used only for free-DOF normalization; it is not rerun here.",
        "q_observable": {
            "name": "q_mean_crown_nodes_2_3_4",
            "formula": "-mean(UZ at physical crown points x=0, y=-0.025/0/0.025, top surface)",
            "physical_coordinates": [list(point) for point in Q_POINTS],
        },
        "solver": {
            "method": "arc_length",
            "linear_method": "direct",
            "max_accepted_steps": 160,
            "newton_tolerance": 1.0e-8,
            "fallback": "no explicit fallback enabled",
            "single_blas_thread": True,
        },
        "formal_contract_or_ledger_modified": False,
        "production_mechanics_changed": False,
        "thresholds_changed": False,
        "reference_path_solve": False,
        "replay": False,
        "m3_policy": "start only after M2 completes numerically and passes its archived envelope gate",
        "base_module": str(base.__file__),
    }


def _patch_case_result(case_path: Path, mesh_level: str) -> dict[str, Any]:
    case = json.loads(case_path.read_text(encoding="utf-8"))
    case["geometry"]["section"] = [0.1, 0.025]
    case["q_observable"] = {
        "name": "q_mean_crown_nodes_2_3_4",
        "formula": "-mean(UZ at physical crown points x=0, y=-0.025/0/0.025, top surface)",
        "physical_coordinates": [list(point) for point in Q_POINTS],
        "mesh_level": mesh_level,
    }
    case["formal_qualification_claimed"] = False
    _write_json(case_path, case)
    return case


def _write_manifest() -> None:
    files = sorted(
        path
        for path in OUT.rglob("*")
        if path.is_file() and path.name != "integrity_manifest.json"
    )
    files.extend(
        [
            Path(__file__).resolve(),
            BASE_RUNNER,
            LOCAL_AUDIT_ROOT / "local_mesh_audit_manifest.json",
        ]
    )
    _write_json(
        OUT / "integrity_manifest.json",
        {
            "schema_version": 1,
            "algorithm": "sha256",
            "manifest_excludes_itself": True,
            "files": {
                str(path.relative_to(ROOT)).replace("\\", "/"): _hash(path)
                for path in files
            },
        },
    )


def main() -> int:
    if _git("branch", "--show-current") != "codex/wp06-score-requalification":
        raise SystemExit("Refusing diagnostic run outside the isolated WP06 branch.")
    if _git("status", "--porcelain", "--", "src/solveur"):
        raise SystemExit("Refusing diagnostic run with dirty production solver source.")
    if OUT.exists():
        raise SystemExit(f"Refusing to overwrite diagnostic output: {OUT}")

    _prepare_input_aliases()
    base = _import_base()
    _configure_base(base)
    for geometry, _ratio in base.GEOMETRIES:
        base.REFERENCE_FREE_DOFS[geometry] = base._free_dof_count(
            base._load_mesh(geometry, "M1")
        )
    base._validate_models()

    OUT.mkdir(parents=True, exist_ok=False)
    metadata = _metadata(base)
    _write_json(OUT / "study_metadata.json", metadata)
    _write_json(
        OUT / "progress.json",
        {
            "status": "RUNNING",
            "completed_cases": 0,
            "total_cases": len(CASE_ORDER),
            "updated_utc": datetime.now(timezone.utc).isoformat(),
        },
    )

    cases: list[dict[str, Any]] = []
    with base.threadpool_limits(limits=1):
        for index, (geometry, ratio, level) in enumerate(CASE_ORDER):
            try:
                case = base._run_case(geometry, ratio, level, index)
                case = _patch_case_result(OUT / f"{geometry}_{level}/case_result.json", level)
            except Exception as error:
                case = {
                    "case_id": f"{geometry}_{level}",
                    "case_status": "PRECHECK_OR_POSTPROCESS_FAILED",
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
                _write_json(OUT / f"{geometry}_{level}_runner_error.json", case)
            cases.append(case)
            _write_json(
                OUT / "study_partial.json",
                {"metadata": metadata, "completed_cases": cases},
            )
            _write_json(
                OUT / "progress.json",
                {
                    "status": "RUNNING",
                    "completed_cases": len(cases),
                    "total_cases": len(CASE_ORDER),
                    "last_case": case.get("case_id"),
                    "last_case_status": case.get("case_status"),
                    "updated_utc": datetime.now(timezone.utc).isoformat(),
                },
            )
            if level == "M2" and (
                case.get("case_status") != "COMPLETED"
                or case.get("full_path_envelope_pass") is not True
            ):
                break

    all_completed = len(cases) == len(CASE_ORDER) and all(
        case.get("case_status") == "COMPLETED" for case in cases
    )
    final = {
        "schema_version": 1,
        "status": "COMPLETED_DIAGNOSTIC_ONLY" if all_completed else "INCOMPLETE_DIAGNOSTIC",
        "metadata": metadata,
        "cases": cases,
        "m2_to_m3_gate": {
            "m3_started": len(cases) == 2,
            "m3_requires_m2_completed_and_envelope_pass": True,
        },
        "formal_qualification_claimed": False,
        "reference_path_solve": False,
        "replay": False,
        "interpretation_limits": [
            "Local axial refinement only; transverse section resolution remains 4x4.",
            "This is diagnostic evidence and cannot award WP06-D points.",
            "The standalone M1 observable recomputation is not an independent path solve.",
        ],
    }
    _write_json(OUT / "study_final.json", final)
    _write_json(
        OUT / "progress.json",
        {
            "status": final["status"],
            "completed_cases": len(cases),
            "total_cases": len(CASE_ORDER),
            "updated_utc": datetime.now(timezone.utc).isoformat(),
        },
    )
    _write_manifest()
    print(f"LOCAL_AXIAL_DIAGNOSTIC_END status={final['status']} cases={len(cases)}", flush=True)
    return 0 if all_completed else 2


if __name__ == "__main__":
    raise SystemExit(main())
