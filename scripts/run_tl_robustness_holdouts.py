"""Run non-development TL holdouts for an opt-in robustness policy."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

from run_tl_boundary_study import _case_corpus  # noqa: E402
from run_tl_robustness_rnd import (  # noqa: E402
    _deterministic_signature,
    _run_variant,
)
from tl_robustness_rnd_support import git_dirty, git_head  # noqa: E402


OUTPUT = _ROOT / "qualification" / "0_2_6" / "tl_robustness_rnd" / "holdouts.json"
MECHANISM = "adaptive_cutback_extended"
HOLDOUT_IDS = (
    "TET4_m2_a4_traction_l0.2_n16_d0.12",
    "TET4_m3_a7_bending_z_l0.2_n16_d0.12",
    "TET4_m3_a10_compression_l0.2_n16_d0.12",
    "TET4_m4_a6_bending_z_l0.2_n16_d0.12",
    "HEX8_m2_a4_bending_z_l0.2_n16_d0.12",
    "HEX8_m3_a7_traction_l0.2_n16_d0.12",
    "HEX8_m3_a10_compression_l0.2_n16_d0.12",
    "HEX8_m4_a9_compression_l0.2_n16_d0.12",
)
STATE_METRICS = (
    "displacement_norm",
    "displacement_max",
    "free_residual_norm",
    "reaction_norm",
    "strain_energy",
    "det_f_min",
    "det_f_max",
)


def _compact(row: dict[str, Any]) -> dict[str, Any]:
    state = row.get("final_state", {})
    diagnostics = row.get("diagnostics", {})
    return {
        "status": row.get("status"),
        "failure_reason": row.get("failure_reason"),
        "final_state": {key: state.get(key) for key in STATE_METRICS},
        "displacement_sha256": row.get("displacement_sha256"),
        "diagnostic_digest": row.get("diagnostic_digest"),
        "deterministic_signature": _deterministic_signature(row),
        "newton_iterations": diagnostics.get("newton_iterations"),
        "accepted_steps": len(diagnostics.get("increments", [])),
        "rejected_increments": diagnostics.get("rejected_increments", 0),
        "assembly_call_count": row.get("assembly_call_count"),
    }


def _comparison(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    baseline_state = baseline.get("final_state", {})
    candidate_state = candidate.get("final_state", {})
    differences = {
        metric: (
            None
            if baseline_state.get(metric) is None or candidate_state.get(metric) is None
            else float(candidate_state[metric]) - float(baseline_state[metric])
        )
        for metric in STATE_METRICS
    }
    return {
        "baseline_status": baseline.get("status"),
        "candidate_status": candidate.get("status"),
        "status_preserved": baseline.get("status") == candidate.get("status"),
        "recovered_from_failure": (
            baseline.get("status") == "FAILURE" and candidate.get("status") == "SUCCESS"
        ),
        "regressed_from_success": (
            baseline.get("status") == "SUCCESS" and candidate.get("status") != "SUCCESS"
        ),
        "state_differences_candidate_minus_baseline": differences,
    }


def _select_cases() -> list[dict[str, Any]]:
    corpus = {case["id"]: case for case in _case_corpus()}
    missing = [case_id for case_id in HOLDOUT_IDS if case_id not in corpus]
    if missing:
        raise ValueError(f"Holdout IDs are not in the controlled corpus: {missing}")
    return [dict(corpus[case_id]) for case_id in HOLDOUT_IDS]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    results: list[dict[str, Any]] = []
    for index, definition in enumerate(_select_cases(), start=1):
        print(f"[{index}/{len(HOLDOUT_IDS)}] {definition['id']} baseline", flush=True)
        baseline = _run_variant(definition, "baseline", adaptive=True)
        print(f"[{index}/{len(HOLDOUT_IDS)}] {definition['id']} candidate", flush=True)
        candidate = _run_variant(definition, MECHANISM, adaptive=True)
        results.append(
            {
                "id": definition["id"],
                "definition": definition,
                "baseline_adaptive": _compact(baseline),
                "candidate": _compact(candidate),
                "comparison": _comparison(baseline, candidate),
            }
        )

    report = {
        "status": "DIAGNOSTIC_ONLY",
        "source_sha": git_head(),
        "dirty_at_start": git_dirty(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mechanism": MECHANISM,
        "case_count": len(results),
        "holdout_ids": list(HOLDOUT_IDS),
        "results": results,
        "baseline_successes": sum(
            item["baseline_adaptive"]["status"] == "SUCCESS" for item in results
        ),
        "candidate_successes": sum(item["candidate"]["status"] == "SUCCESS" for item in results),
        "recoveries": sum(item["comparison"]["recovered_from_failure"] for item in results),
        "regressions": sum(item["comparison"]["regressed_from_success"] for item in results),
        "status_changes": sum(not item["comparison"]["status_preserved"] for item in results),
        "formulation_changed": False,
        "tangent_changed": False,
        "default_path_changed": False,
        "no_new_thresholds": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "source_sha": report["source_sha"],
                "dirty_at_start": report["dirty_at_start"],
                "case_count": report["case_count"],
                "baseline_successes": report["baseline_successes"],
                "candidate_successes": report["candidate_successes"],
                "recoveries": report["recoveries"],
                "regressions": report["regressions"],
                "status_changes": report["status_changes"],
                "artifact_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
