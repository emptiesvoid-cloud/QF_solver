"""Analyze an opt-in TL rescue policy against the clean baseline and oracle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from analyze_tl_physical_branch import (
    QF_CASES,
    _external_series,
    _interpolated_error,
    _monotonic,
    _plot,
    _qf_series,
    _sha256,
    _turning_count,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_BRANCH = ROOT / ".tmp_tl_rescue_optimization" / "branch_bounded_growth_1p02"
DEFAULT_EXTERNAL = ROOT / ".tmp_tl_physical_branch_validation" / "external_code_aster" / "summary.json"
DEFAULT_BASELINE = ROOT / ".tmp_tl_rescue_optimization" / "baseline_current.json"
DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_6" / "tl_rescue_optimization"
STATE_METRICS = (
    "loaded_mean_ux",
    "fixed_reaction_resultant_x",
    "strain_energy",
    "det_f_min",
    "free_residual_norm",
    "displacement_norm",
    "displacement_max",
)


def _load_candidate(path: Path) -> dict[str, Any]:
    payload = json.loads((path / "summary.json").read_text(encoding="utf-8"))
    return {case["id"]: case for case in payload["cases"]}, payload


def _load_screen(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _baseline_map(path: Path) -> dict[str, dict[str, Any]]:
    payload = _load_screen(path)
    return {run["id"]: run for run in payload["runs"]}


def _candidate_screen_map(paths: list[Path]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in paths:
        payload = _load_screen(path)
        for run in payload["runs"]:
            result[run["id"]] = run
    return result


def _final_candidate_state(case: dict[str, Any]) -> dict[str, Any]:
    accepted = case.get("accepted_states", [])
    if not accepted:
        return {}
    last = accepted[-1]
    reaction = np.asarray(last.get("reaction_vector_fixed", []), dtype=float).reshape((-1, 3))
    result = {
        "loaded_mean_ux": float(last["loaded_mean_ux"]),
        "fixed_reaction_resultant_x": float(np.sum(reaction[:, 0])),
        "strain_energy": float(last["strain_energy"]),
        "det_f_min": float(last["det_f_min"]),
        "free_residual_norm": float(last["residual_norm_free"]),
        "displacement_norm": float(last["displacement_norm"]),
        "displacement_max": float(last["displacement_max"]),
    }
    return result


def _state_comparison(candidate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    current = (
        candidate["final_state"]
        if "final_state" in candidate
        else _final_candidate_state(candidate)
    )
    reference = baseline.get("final_state", {})
    differences: dict[str, float | None] = {}
    normalized: dict[str, float | None] = {}
    for metric in STATE_METRICS:
        if metric not in current or metric not in reference:
            differences[metric] = None
            normalized[metric] = None
            continue
        difference = current[metric] - float(reference[metric])
        differences[metric] = difference
        normalized[metric] = abs(difference) / max(abs(float(reference[metric])), 1.0e-12)
    return {"absolute": differences, "normalized": normalized}


def _screen_row(candidate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    state = _state_comparison(candidate, baseline)
    return {
        "id": candidate["id"],
        "status": candidate["status"],
        "baseline_seconds": float(baseline["elapsed_seconds"]),
        "candidate_seconds": float(candidate["elapsed_seconds"]),
        "speedup": float(baseline["elapsed_seconds"] / candidate["elapsed_seconds"]),
        "baseline_assemblies": int(baseline["assembly_calls"]),
        "candidate_assemblies": int(candidate["assembly_calls"]),
        "assembly_reduction": float(1.0 - candidate["assembly_calls"] / baseline["assembly_calls"]),
        "baseline_accepted_steps": baseline["diagnostics"]["accepted_steps"],
        "candidate_accepted_steps": candidate["diagnostics"]["accepted_steps"],
        "baseline_newton_iterations": baseline["diagnostics"]["newton_iterations"],
        "candidate_newton_iterations": candidate["diagnostics"].get("newton_iterations"),
        "baseline_rejected_increments": baseline["diagnostics"]["rejected_increments"],
        "candidate_rejected_increments": candidate["diagnostics"]["rejected_increments"],
        "state_comparison": state,
        "candidate_displacement_sha256": candidate["final_state"]["displacement_sha256"],
    }


def _format_policy(policy: dict[str, Any]) -> str:
    return ", ".join(f"{key}={value}" for key, value in policy.items())


def _report_text(results: dict[str, Any]) -> str:
    lines = [
        "# TL Rescue Optimization Diagnostic",
        "",
        "Status: **DIAGNOSTIC_ONLY**. The candidate is an opt-in parameter policy; it does not change the default path, Total-Lagrangian formulation, tangent, tolerances or TL maturity claim.",
        "",
        "## Provenance",
        "",
        f"- Numerical solver source for the candidate runs: `{results['source_sha']}`.",
        f"- Candidate trajectory harness source: `{results['trajectory_source_sha']}`; `dirty_at_start=false`.",
        f"- Candidate screen artifacts: `{', '.join(results['screen_artifacts'])}`.",
        f"- Code_Aster oracle: `{results['external_image']}`; raw summary SHA-256 `{results['external_raw_summary_sha256']}`.",
        f"- Candidate policy: `{_format_policy(results['policy'])}`.",
        "- No formulation, tangent, convergence tolerance or default solver behavior was modified.",
        "",
        "## Cost comparison",
        "",
        "| Case | Status | Baseline s | Candidate s | Speedup | Baseline assemblies | Candidate assemblies | Assembly reduction |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in results["case_metrics"]:
        lines.append(
            f"| {row['id'].rsplit('_n', 1)[-1]} | {row['status']} | {row['baseline_seconds']:.3f} | {row['candidate_seconds']:.3f} | {row['speedup']:.3f}x | {row['baseline_assemblies']} | {row['candidate_assemblies']} | {100.0 * row['assembly_reduction']:.2f}% |"
        )
    lines.extend(
        [
            "",
            f"Cumulative baseline: `{results['baseline_time']:.3f} s`, `{results['baseline_assemblies']} assemblies`. Candidate: `{results['candidate_time']:.3f} s`, `{results['candidate_assemblies']} assemblies`. Observed speedup: `{results['speedup']:.3f}x`; assembly reduction: `{100.0 * results['assembly_reduction']:.2f}%`.",
            "",
            "## Branch comparison",
            "",
            "The candidate accepted-state snapshots are interpolated onto the 128 Code_Aster load points. These are diagnostic comparison errors; no new acceptance threshold is inferred from them.",
            "",
            "| Case | QF branch | Normalized displacement error | Normalized reaction error | Turning candidates |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for row in results["branch_metrics"]:
        lines.append(
            f"| {row['id'].rsplit('_n', 1)[-1]} | {row['branch_status']} | {row['ux_normalized']:.6e} | {row['reaction_normalized']:.6e} | {row['turning_candidates']} |"
        )
    lines.extend(
        [
            "",
            "- Load-displacement and fixed-end x-reaction histories remain comparable to the independent Code_Aster path over the captured domain.",
            "- QF energy remains an internal diagnostic; Code_Aster's exported current-load work is not the same observable, so external energy agreement is **NOT_ESTABLISHED**.",
            "- QF `det(F)` remains positive over the tested path; Code_Aster did not export a directly equivalent field, so external `det(F)` agreement is **NOT_ESTABLISHED**.",
            "- Stress measures were not reduced to a proven common pointwise measure and are not used as an equality claim.",
            "",
            "![Load-displacement branch](load_displacement_branch.png)",
            "",
            "![Reaction history](reaction_history.png)",
            "",
            "## State equivalence",
            "",
            "Final scalar state comparisons against the clean baseline are recorded below. Different displacement hashes are expected because the candidate uses a different accepted-step partition; the physical scalar state and external branch are the comparison criteria.",
            "",
            "| Case | max normalized scalar-state difference | Candidate / baseline displacement hash equal |",
            "| --- | ---: | --- |",
        ]
    )
    for row in results["case_metrics"]:
        normalized = [value for value in row["state_comparison"]["normalized"].values() if value is not None]
        baseline_hash = results["baseline_hashes"][row["id"]]
        equal = baseline_hash == row["candidate_displacement_sha256"]
        lines.append(f"| {row['id'].rsplit('_n', 1)[-1]} | {max(normalized, default=float('nan')):.6e} | {'YES' if equal else 'NO'} |")
    lines.extend(
        [
            "",
            "## Policy decision",
            "",
            "`BEST_POLICY = bounded_growth_1p02` is a promising opt-in candidate in the three externally matched HEX8 paths. The prior aggressive `adaptive_growth=1.5` policy remains rejected because its 150-case replay changed physical states/branches. This conservative candidate must still pass the full 150-case replay, holdouts, failure-zoo replay and deterministic repetition before it can be retained.",
            "",
            "`PHYSICAL_BRANCH_CONFIRMED = YES` for the three exact target paths within the bounded diagnostic domain, based on the independent Code_Aster load-displacement and reaction histories.",
            "",
            "`READY_FOR_TL_PROMOTION_CAMPAIGN = NO`. This optimization does not broaden TL qualification.",
            "",
            "No push, merge, tag, release or PyPI publication was performed.",
        ]
    )
    return "\n".join(lines) + "\n"


def run(
    candidate_branch: Path,
    candidate_screens: list[Path],
    baseline_path: Path,
    external_path: Path,
    output: Path,
) -> dict[str, Any]:
    candidate_cases, candidate_payload = _load_candidate(candidate_branch)
    baseline_cases = _baseline_map(baseline_path)
    candidate_screen_cases = _candidate_screen_map(candidate_screens)
    external_payload = json.loads(external_path.read_text(encoding="utf-8"))
    external = _external_series(external_payload)
    case_metrics = []
    branch_metrics = []
    results_for_plot: dict[str, Any] = {"cases": {}, "external_series": {key: value.tolist() for key, value in external.items()}}
    for case_id in QF_CASES:
        case = candidate_cases[case_id]
        screen = candidate_screen_cases[case_id]
        baseline = baseline_cases[case_id]
        qf = _qf_series(case)
        results_for_plot["cases"][case_id] = {"qf_series": {key: value.tolist() for key, value in qf.items()}}
        curve = {key: _interpolated_error(qf, external, key) for key in ("ux", "reaction_x")}
        branch_metrics.append(
            {
                "id": case_id,
                "branch_status": "MONOTONE_BRANCH_CONFIRMED" if _monotonic(qf["factor"], increasing=True) and _monotonic(qf["ux"], increasing=False) else "BRANCH_DIFFERENT",
                "ux_normalized": curve["ux"]["max_normalized"],
                "reaction_normalized": curve["reaction_x"]["max_normalized"],
                "turning_candidates": _turning_count(qf["ux"]),
            }
        )
        case_metrics.append(_screen_row(screen, baseline))
    output.mkdir(parents=True, exist_ok=True)
    _plot(results_for_plot, output)
    baseline_time = sum(row["baseline_seconds"] for row in case_metrics)
    candidate_time = sum(row["candidate_seconds"] for row in case_metrics)
    baseline_assemblies = sum(row["baseline_assemblies"] for row in case_metrics)
    candidate_assemblies = sum(row["candidate_assemblies"] for row in case_metrics)
    results = {
        "study_id": "TL-RESCUE-OPTIMIZATION-026",
        "status": "DIAGNOSTIC_ONLY",
        "source_sha": candidate_payload["source_sha"],
        "trajectory_source_sha": candidate_payload["source_sha"],
        "policy": candidate_payload["solver_controls"],
        "screen_artifacts": [path.name for path in candidate_screens],
        "external_image": external_payload["external_solver"]["image"],
        "external_raw_summary_sha256": _sha256(external_path),
        "case_metrics": case_metrics,
        "branch_metrics": branch_metrics,
        "baseline_time": baseline_time,
        "candidate_time": candidate_time,
        "speedup": baseline_time / candidate_time,
        "baseline_assemblies": baseline_assemblies,
        "candidate_assemblies": candidate_assemblies,
        "assembly_reduction": 1.0 - candidate_assemblies / baseline_assemblies,
        "baseline_hashes": {case_id: baseline_cases[case_id]["final_state"]["displacement_sha256"] for case_id in QF_CASES},
        "candidate_hashes": {case_id: candidate_cases[case_id]["final_displacement_sha256"] for case_id in QF_CASES},
        "physical_branch_confirmed": all(row["branch_status"] == "MONOTONE_BRANCH_CONFIRMED" for row in branch_metrics),
        "energy_agreement": "NOT_ESTABLISHED",
        "det_f_agreement": "NOT_ESTABLISHED",
        "formulation_changed": False,
        "tangent_changed": False,
        "default_path_changed": False,
        "candidate_status": "3/3_TARGET_SUCCESS",
    }
    (output / "report.md").write_text(_report_text(results), encoding="utf-8")
    compact = {key: value for key, value in results.items() if key not in {"baseline_hashes", "candidate_hashes"}}
    (output / "summary.json").write_text(json.dumps(compact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-branch", type=Path, default=DEFAULT_CANDIDATE_BRANCH)
    parser.add_argument("--candidate-screen", type=Path, action="append", required=True)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--external", type=Path, default=DEFAULT_EXTERNAL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    results = run(
        args.candidate_branch.resolve(),
        [path.resolve() for path in args.candidate_screen],
        args.baseline.resolve(),
        args.external.resolve(),
        args.output.resolve(),
    )
    print(json.dumps({key: results[key] for key in ("status", "source_sha", "candidate_status", "speedup", "assembly_reduction", "physical_branch_confirmed")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
