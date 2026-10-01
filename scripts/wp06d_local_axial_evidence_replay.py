"""Replay and integrity-audit archived WP06-D local-axial evidence.

This is intentionally not a second structural solve.  It reads every
accepted checkpoint twice, verifies byte-identical state identities, and
checks that the independent-reference rows point to the same checkpoint
digests.  The result is therefore an evidence replay, not solver replay.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ROOT = ROOT / "qualification/0_2_9/wp06d_local_axial_diagnostic_20260919"


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


def _snapshot(case_dir: Path) -> list[dict[str, Any]]:
    snapshot: list[dict[str, Any]] = []
    for path in sorted(case_dir.glob("accepted_state.step*.npz")):
        raw = path.read_bytes()
        with np.load(path, allow_pickle=False) as archive:
            metadata_text = str(archive["metadata_json"].item())
            payload = json.loads(metadata_text)
        snapshot.append(
            {
                "path": path.name,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "metadata_sha256": hashlib.sha256(metadata_text.encode("utf-8")).hexdigest(),
                "completed_step": int(payload["completed_step"]),
                "composite_digest": str(payload["composite_digest"]),
            }
        )
    return snapshot


def _load_reference_rows(reference_path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with reference_path.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            rows[str(int(row["step"]))] = row
    return rows


def replay_level(run_root: Path, reference_root: Path, level: str) -> dict[str, Any]:
    case_dir = run_root / f"rise_span_0_05_{level}"
    reference_dir = reference_root / level
    result_path = case_dir / "case_result.json"
    reference_result_path = reference_dir / "independent_reference_result.json"
    rows_path = reference_dir / "state_metrics.jsonl"
    for path in (result_path, reference_result_path, rows_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    first = _snapshot(case_dir)
    second = _snapshot(case_dir)
    if first != second:
        raise ValueError(f"Checkpoint replay is not deterministic for {level}.")
    if not first:
        raise ValueError(f"No checkpoints available for {level}.")
    reference_rows = _load_reference_rows(rows_path)
    if len(reference_rows) != len(first):
        raise ValueError(f"Reference row count mismatch for {level}.")
    row_digests = {
        str(int(row["step"])): str(row["checkpoint_composite_digest"])
        for row in reference_rows.values()
    }
    for state in first:
        if row_digests.get(str(state["completed_step"])) != state["composite_digest"]:
            raise ValueError(f"Reference/checkpoint digest mismatch at {level} step {state['completed_step']}.")
    reference_result = json.loads(reference_result_path.read_text(encoding="utf-8"))
    case_result = json.loads(result_path.read_text(encoding="utf-8"))
    if case_result.get("case_status") != "COMPLETED":
        raise ValueError(f"Production diagnostic case is not complete for {level}.")
    if reference_result.get("recorded_comparison", {}).get("status") != "PASS":
        raise ValueError(f"Independent recorded comparison is not PASS for {level}.")
    return {
        "level": level,
        "status": "PASS_EVIDENCE_REPLAY_ONLY",
        "checkpoint_count": len(first),
        "first_checkpoint": first[0],
        "last_checkpoint": first[-1],
        "checkpoint_snapshot_sha256": hashlib.sha256(
            json.dumps(first, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "production_solver_replay_run": False,
        "independent_observable_recomputation": True,
        "recorded_comparison": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--reference-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    levels = [replay_level(args.run_root.resolve(), args.reference_root.resolve(), level) for level in ("M2", "M3")]
    result = {
        "schema_version": 1,
        "status": "PASS_EVIDENCE_REPLAY_ONLY" if all(item["status"].startswith("PASS_") for item in levels) else "FAIL_CLOSED",
        "production_solver_replay_run": False,
        "levels": levels,
        "provenance": {"branch": _git("branch", "--show-current"), "head": _git("rev-parse", "HEAD")},
        "limitations": [
            "This replay does not rerun Newton or arc-length production mechanics.",
            "It proves deterministic archival readback and reference-row/checkpoint identity only.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"EVIDENCE_REPLAY_STATUS={result['status']} levels={len(levels)}", flush=True)
    return 0 if result["status"] == "PASS_EVIDENCE_REPLAY_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
