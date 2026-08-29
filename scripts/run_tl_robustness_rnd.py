"""Run isolated, opt-in robustness experiments for the existing TL driver."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

from run_tl_boundary_study import _mesh_quality  # noqa: E402
from run_tl_failure_isolation import _external, _fixed_indices, _model  # noqa: E402
from solveur.core.analyses.geometric_nonlinear import _newton_dead_load  # noqa: E402
from solveur.core.assembly.geometric import build_total_lagrangian_assembly  # noqa: E402
from solveur.core.errors import NumericalConvergenceError  # noqa: E402
from solveur.core.nonlinear.controls import AdaptiveLoadControls  # noqa: E402
from solveur.core.nonlinear.robustness import NonlinearRobustnessOptions  # noqa: E402
from scipy.sparse.linalg import eigsh  # noqa: E402
from tl_robustness_rnd_support import (  # noqa: E402
    MECHANISMS,
    PERSISTENT_IDS,
    LightRecordingAssembly,
    experiment_cases,
    git_dirty,
    git_head,
)


OUTPUT = _ROOT / "qualification" / "0_2_6" / "tl_robustness_rnd"
TOLERANCE = 1.0e-8
MAX_ITERATIONS = 100
def _controls(increments: int, overrides: dict[str, Any] | None) -> AdaptiveLoadControls:
    initial = 1.0 / increments
    parameters: dict[str, Any] = {
        "initial_load_increment": initial,
        "min_load_increment": 1.0e-4,
        "max_load_increment": initial,
        "cutback_factor": 0.5,
        "growth_factor": 1.0,
        "max_cutbacks": 8,
    }
    if overrides:
        parameters.update(overrides)
    return AdaptiveLoadControls.from_parameters(
        parameters,
        load_steps=increments,
        max_iterations=MAX_ITERATIONS,
    )


def _safe_state_metrics(
    model: Any,
    assembly: Any,
    displacement: np.ndarray,
    fixed: np.ndarray,
    external: np.ndarray,
) -> dict[str, Any]:
    try:
        return _sparse_state_metrics(model, assembly, displacement, fixed, external)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _sparse_extreme_eigenvalues(matrix: Any) -> tuple[float, float]:
    """Estimate tangent extremes without densifying the reduced system."""
    symmetric = 0.5 * (matrix + matrix.T)
    size = symmetric.shape[0]
    if size == 0:
        raise ValueError("Reduced tangent has no free degrees of freedom.")
    if size <= 2:
        values = np.linalg.eigvalsh(symmetric.toarray())
        return float(values[0]), float(values[-1])
    eigen_options = {"return_eigenvectors": False, "tol": 1.0e-6, "maxiter": 500}
    minimum = eigsh(symmetric.tocsr(), k=1, which="SA", **eigen_options)[0]
    maximum = eigsh(symmetric.tocsr(), k=1, which="LA", **eigen_options)[0]
    return float(minimum), float(maximum)


def _sparse_tangent_metrics(assembly: Any, fixed: np.ndarray) -> dict[str, Any]:
    zero = np.zeros(assembly.ndof, dtype=float)
    _, tangent = assembly.assemble(zero)
    free = np.setdiff1d(np.arange(assembly.ndof), fixed)
    reduced = tangent[free][:, free].tocsr()
    try:
        minimum, maximum = _sparse_extreme_eigenvalues(reduced)
    except Exception as exc:
        return {
            "condition_number": None,
            "minimum_eigenvalue": None,
            "maximum_eigenvalue": None,
            "diagnostic_status": "UNAVAILABLE",
            "diagnostic_error": f"{type(exc).__name__}: {exc}",
        }
    condition = float("inf") if minimum == 0.0 else abs(maximum / minimum)
    return {
        "condition_number": condition,
        "minimum_eigenvalue": minimum,
        "maximum_eigenvalue": maximum,
    }


def _sparse_state_metrics(
    model: Any,
    assembly: Any,
    displacement: np.ndarray,
    fixed: np.ndarray,
    external: np.ndarray,
) -> dict[str, Any]:
    internal, tangent = assembly.assemble(displacement)
    free = np.setdiff1d(np.arange(assembly.ndof), fixed)
    residual = external - internal
    reduced = tangent[free][:, free].tocsr()
    try:
        minimum, maximum = _sparse_extreme_eigenvalues(reduced)
        condition = float("inf") if minimum == 0.0 else abs(maximum / minimum)
        eigen_status = "PASS"
        eigen_error = None
    except Exception as exc:
        minimum = None
        maximum = None
        condition = None
        eigen_status = "UNAVAILABLE"
        eigen_error = f"{type(exc).__name__}: {exc}"
    determinants = assembly.deformation_determinants(displacement)
    return {
        "displacement_norm": float(np.linalg.norm(displacement)),
        "displacement_max": float(np.max(np.abs(displacement))),
        "displacement_sha256": hashlib.sha256(np.asarray(displacement).tobytes()).hexdigest(),
        "free_residual_norm": float(np.linalg.norm(residual[free])),
        "total_residual_norm": float(np.linalg.norm(residual)),
        "reaction_norm": float(np.linalg.norm(residual[fixed])),
        "strain_energy": float(assembly.strain_energy(displacement)),
        "det_f_min": float(np.min(determinants)),
        "det_f_max": float(np.max(determinants)),
        "tangent_condition_number": condition,
        "tangent_min_eigenvalue": minimum,
        "tangent_max_eigenvalue": maximum,
        "tangent_eigen_diagnostic_status": eigen_status,
        "tangent_eigen_diagnostic_error": eigen_error,
    }


def _diagnostic_digest(diagnostics: dict[str, Any]) -> str:
    payload = _jsonable(diagnostics)
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        return value.item()
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    return value


_RUNTIME_DIAGNOSTIC_KEYS = {
    "assembly_seconds",
    "linear_solve_seconds",
    "line_search_seconds",
}


def _deterministic_value(value: Any) -> Any:
    """Remove runtime measurements before comparing repeated outcomes."""
    if isinstance(value, dict):
        return {
            str(key): _deterministic_value(item)
            for key, item in value.items()
            if key not in _RUNTIME_DIAGNOSTIC_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_deterministic_value(item) for item in value]
    return _jsonable(value)


def _deterministic_signature(row: dict[str, Any]) -> str:
    """Digest numerical/status outcomes while excluding wall-clock timing."""
    payload = {
        "status": row["status"],
        "failure_reason": row.get("failure_reason"),
        "displacement_sha256": row.get("displacement_sha256"),
        "diagnostics": _deterministic_value(row.get("diagnostics", {})),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _run_variant(
    definition: dict[str, Any],
    mechanism: str,
    adaptive: bool,
) -> dict[str, Any]:
    configuration = MECHANISMS[mechanism]
    model, _, _, _, _ = _model(
        definition["family"],
        definition["cells"],
        definition["mode"],
        definition["load_scale"],
        definition["increments"],
        distortion=definition["distortion"],
        angle=definition["angle"],
        aspect=definition["aspect"],
    )
    dofs = model.dof_manager()
    fixed = _fixed_indices(model, dofs)
    external = _external(model, dofs)
    assembly = build_total_lagrangian_assembly(model)
    recorder = LightRecordingAssembly(assembly)
    parameters = dict(configuration.get("parameters", {}))
    options = NonlinearRobustnessOptions.from_parameters(parameters)
    controls = (
        _controls(definition["increments"], configuration.get("adaptive_parameters"))
        if adaptive
        else None
    )
    row: dict[str, Any] = {
        "id": definition["id"],
        "mechanism": mechanism,
        "variant": "adaptive" if adaptive else "fixed",
        "definition": definition,
        "configuration": configuration,
        "quality": _mesh_quality(model),
        "initial_tangent": _sparse_tangent_metrics(assembly, fixed),
    }
    try:
        displacement, diagnostics = _newton_dead_load(
            recorder,
            external,
            fixed,
            increments=definition["increments"],
            tolerance=TOLERANCE,
            max_iterations=MAX_ITERATIONS,
            determinant_assembly=assembly,
            adaptive_controls=controls,
            robustness_options=options,
        )
        row.update(
            {
                "status": "SUCCESS",
                "failure_reason": None,
                "displacement": displacement,
                "final_state": _safe_state_metrics(model, assembly, displacement, fixed, external),
                "diagnostics": diagnostics,
            }
        )
    except NumericalConvergenceError as exc:
        displacement = recorder.last_successful_displacement
        if displacement is None:
            displacement = np.zeros(assembly.ndof, dtype=float)
        row.update(
            {
                "status": "FAILURE",
                "failure_reason": exc.reason.value if exc.reason is not None else type(exc).__name__,
                "displacement": displacement,
                "final_state": _safe_state_metrics(model, assembly, displacement, fixed, external),
                "diagnostics": exc.diagnostics,
                "message": str(exc),
            }
        )
    diagnostics = row["diagnostics"]
    row.update(
        {
            "diagnostic_digest": _diagnostic_digest(diagnostics),
            "assembly_call_count": len(recorder.calls),
            "failed_assembly_calls": sum(item["status"] == "EXCEPTION" for item in recorder.calls),
            "assembly_history": [
                {key: value for key, value in item.items() if key != "displacement"}
                for item in recorder.calls
            ],
        }
    )
    row["displacement_sha256"] = hashlib.sha256(np.asarray(row["displacement"]).tobytes()).hexdigest()
    return row


def _public_result(row: dict[str, Any]) -> dict[str, Any]:
    diagnostics = row["diagnostics"]
    increments = diagnostics.get("increments", []) if isinstance(diagnostics, dict) else []
    residual_history = [
        float(value)
        for item in increments
        for value in item.get("residual_history", [])
        if np.isfinite(float(value))
    ]
    return {
        key: row.get(key)
        for key in (
            "id",
            "mechanism",
            "variant",
            "definition",
            "configuration",
            "status",
            "failure_reason",
            "quality",
            "initial_tangent",
            "final_state",
            "diagnostics",
            "diagnostic_digest",
            "assembly_call_count",
            "failed_assembly_calls",
            "assembly_history",
            "displacement_sha256",
        )
    } | {"residual_history": residual_history}


def _reference_record(row: dict[str, Any]) -> dict[str, Any]:
    """Keep only comparison data after a completed run is written/released."""
    return {
        "id": row["id"],
        "variant": row["variant"],
        "status": row["status"],
        "failure_reason": row["failure_reason"],
        "final_state": row.get("final_state", {}),
        "displacement_sha256": row.get("displacement_sha256"),
    }


def _comparison(reference: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    base_state = reference.get("final_state", {})
    candidate_state = candidate.get("final_state", {})
    metrics = (
        "displacement_norm",
        "displacement_max",
        "free_residual_norm",
        "reaction_norm",
        "strain_energy",
        "det_f_min",
        "det_f_max",
    )
    differences: dict[str, float | None] = {}
    for metric in metrics:
        left = base_state.get(metric)
        right = candidate_state.get(metric)
        if left is None or right is None:
            differences[metric] = None
        else:
            differences[metric] = float(right) - float(left)
    return {
        "variant": candidate.get("variant"),
        "reference_status": reference.get("status"),
        "candidate_status": candidate.get("status"),
        "status_preserved": reference.get("status") == candidate.get("status"),
        "recovered_from_reference_failure": (
            reference.get("status") == "FAILURE" and candidate.get("status") == "SUCCESS"
        ),
        "regressed_from_reference_success": (
            reference.get("status") == "SUCCESS" and candidate.get("status") == "FAILURE"
        ),
        "reference_failure_reason": reference.get("failure_reason"),
        "candidate_failure_reason": candidate.get("failure_reason"),
        "reference_displacement_sha256": reference.get("displacement_sha256"),
        "candidate_displacement_sha256": candidate.get("displacement_sha256"),
        "state_differences_candidate_minus_reference": differences,
    }


def _evaluate(
    results: list[dict[str, Any]],
    baseline: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    comparisons = []
    for row in results:
        if row["mechanism"] == "baseline":
            continue
        reference = baseline[(row["id"], row["variant"])]
        comparisons.append(_comparison(reference, row))
    return {
        "candidate_runs": len(results),
        "recovered_failures": sum(item["recovered_from_reference_failure"] for item in comparisons),
        "regressions": sum(item["regressed_from_reference_success"] for item in comparisons),
        "status_changes": sum(not item["status_preserved"] for item in comparisons),
        "comparisons": comparisons,
    }


def _evaluation_with_breakdown(
    mechanism_rows: list[dict[str, Any]],
    baseline_rows: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    evaluation = _evaluate(mechanism_rows, baseline_rows)
    evaluation["variant_breakdown"] = {
        variant: {
            "regressions": sum(
                item["regressed_from_reference_success"]
                for item in evaluation["comparisons"]
                if item["variant"] == variant
            ),
            "recoveries": sum(
                item["recovered_from_reference_failure"]
                for item in evaluation["comparisons"]
                if item["variant"] == variant
            ),
        }
        for variant in ("fixed", "adaptive")
    }
    evaluation["fixed_regressions"] = evaluation["variant_breakdown"]["fixed"]["regressions"]
    evaluation["adaptive_regressions"] = evaluation["variant_breakdown"]["adaptive"]["regressions"]
    evaluation["fixed_recoveries"] = evaluation["variant_breakdown"]["fixed"]["recoveries"]
    evaluation["adaptive_recoveries"] = evaluation["variant_breakdown"]["adaptive"]["recoveries"]
    return evaluation


def _load_baseline(output: Path, cases: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    path = output / "baseline.json"
    if not path.exists():
        raise FileNotFoundError(f"Cannot resume without baseline evidence: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = {
        (item["id"], item["variant"]): item
        for item in payload.get("results", [])
        if item.get("id") in {case["id"] for case in cases}
    }
    expected = {(case["id"], variant) for case in cases for variant in ("fixed", "adaptive")}
    if rows.keys() != expected:
        missing = sorted(expected - rows.keys())
        raise ValueError(f"Baseline evidence is incomplete; missing {missing}")
    return rows


def _load_previous_mechanism(
    output: Path,
    mechanism: str,
    baseline_rows: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    path = output / f"{mechanism}.json"
    if not path.exists():
        raise FileNotFoundError(f"Cannot resume mechanism without evidence: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    selected_ids = {case_id for case_id, _ in baseline_rows}
    rows = [item for item in payload.get("results", []) if item.get("id") in selected_ids]
    return {
        "description": MECHANISMS[mechanism]["description"],
        "configuration": MECHANISMS[mechanism],
        "evaluation": _evaluation_with_breakdown(rows, baseline_rows)
        if mechanism != "baseline"
        else {},
        "repeat_checks": payload.get("repeat_checks", []),
        "evidence_file": path.name,
    }


def _repeat_signatures(rows: list[dict[str, Any]], repeats: int) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        if row["id"] not in PERSISTENT_IDS or repeats < 2:
            continue
        output.append(
            {
                "id": row["id"],
                "mechanism": row["mechanism"],
                "variant": row["variant"],
                "run": 1,
                "status": row["status"],
                "failure_reason": row["failure_reason"],
                "displacement_sha256": row["displacement_sha256"],
                "diagnostic_digest": row["diagnostic_digest"],
            }
        )
    return output


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TL Robustness Extension R&D",
        "",
        "Status: `DIAGNOSTIC_ONLY`; mechanisms are opt-in experiments and do not alter the default TL path.",
        "",
        f"- Source SHA: `{report['source_sha']}`",
        f"- Worktree dirty at capture: `{report['dirty']}`",
        f"- Cases: `{report['case_count']}`; mechanisms: `{len(report['mechanisms'])}`",
        f"- Generated: `{report['timestamp_utc']}`",
        "",
        "## Scope and guardrails",
        "",
        "The baseline is the exact de7633a boundary reproduction. No formulation, material tangent, convergence tolerance or default solver path is changed. State differences are reported as measurements; no new acceptance threshold is introduced by this report.",
        "",
        "## Mechanisms",
        "",
        "| Mechanism | Description | Fixed status changes | Adaptive status changes | Recovered reference failures |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for mechanism, details in report["mechanisms"].items():
        evaluation = details.get("evaluation", {})
        lines.append(
            f"| `{mechanism}` | {details['description']} | {evaluation.get('fixed_regressions', 0)} | {evaluation.get('adaptive_regressions', 0)} | {evaluation.get('recovered_failures', 0)} |"
        )
    lines.extend(
        [
            "",
            "## Persistent failure preservation",
            "",
            "The four baseline persistent HEX8 compression cases remain in the experiment corpus and failure zoo. A mechanism is not retained merely because it changes a status; physical state, residual, determinant and energy measurements must be reviewed together.",
            "",
            "| Case | Baseline fixed | Baseline adaptive |",
            "| --- | --- | --- |",
        ]
    )
    for case in report["cases"]:
        if case["id"] not in PERSISTENT_IDS:
            continue
        base = report["baseline_summary"][case["id"]]
        lines.append(f"| `{case['id']}` | {base['fixed_status']} | {base['adaptive_status']} |")
    lines.extend(
        [
            "",
            "## Decision policy",
            "",
            "`ACCEPT_FOR_FULL_REPLAY` requires no nominal status regression, deterministic repeated signatures, and no unexplained physical-state difference. `REJECT_FOR_FULL_REPLAY` means the targeted experiment did not provide sufficient evidence; it is not a claim that the mechanism is mathematically impossible. All mechanisms remain experimental until the full 150-case replay is completed.",
            "",
            "## Passive eigenvalue diagnostics",
            "",
            "Initial and last-available tangent condition/eigenvalue diagnostics are recorded for every run. They are observational only and are not converted into a universal cutoff.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--mechanisms", nargs="+", choices=tuple(MECHANISMS), default=None)
    parser.add_argument("--case-ids", nargs="+", default=None)
    args = parser.parse_args(argv)
    if args.repeats < 1:
        raise SystemExit("--repeats must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    cases = experiment_cases()
    if args.case_ids:
        selected_ids = set(args.case_ids)
        cases = [case for case in cases if case["id"] in selected_ids]
        if not cases:
            raise SystemExit("--case-ids did not select a known experiment case")
    baseline_rows: dict[tuple[str, str], dict[str, Any]] = {}
    mechanism_reports: dict[str, dict[str, Any]] = {}
    selected_mechanisms = list(args.mechanisms or MECHANISMS)
    if "baseline" not in selected_mechanisms:
        baseline_rows = _load_baseline(args.output, cases)
    for mechanism, configuration in MECHANISMS.items():
        if mechanism not in selected_mechanisms:
            mechanism_reports[mechanism] = _load_previous_mechanism(args.output, mechanism, baseline_rows)
            continue
        print(f"[mechanism] {mechanism}", flush=True)
        mechanism_rows: list[dict[str, Any]] = []
        repeat_checks: list[dict[str, Any]] = []
        for definition in cases:
            repeat_count = args.repeats if definition["id"] in PERSISTENT_IDS else 1
            for adaptive in (False, True):
                repeated: list[dict[str, Any]] = []
                for run_number in range(repeat_count):
                    print(
                        f"  {definition['id']} {'adaptive' if adaptive else 'fixed'} repeat={run_number + 1}/{repeat_count}",
                        flush=True,
                    )
                    row = _run_variant(definition, mechanism, adaptive)
                    row["repeat"] = run_number + 1
                    repeated.append(row)
                    if run_number == 0:
                        mechanism_rows.append(row)
                        if mechanism == "baseline":
                            baseline_rows[(definition["id"], row["variant"])] = _reference_record(row)
                # Keep repeat equality as an explicit diagnostic, not a hidden pass criterion.
                if len(repeated) > 1:
                    signatures = [_deterministic_signature(item) for item in repeated]
                    repeat_checks.append(
                        {
                            "id": definition["id"],
                            "variant": "adaptive" if adaptive else "fixed",
                            "signatures_equal": len(set(signatures)) == 1,
                            "signatures": signatures,
                        }
                    )
        evaluation = (
            _evaluation_with_breakdown(mechanism_rows, baseline_rows)
            if mechanism != "baseline"
            else {}
        )
        mechanism_reports[mechanism] = {
            "description": configuration["description"],
            "configuration": configuration,
            "evaluation": evaluation,
            "repeat_checks": repeat_checks,
            "evidence_file": f"{mechanism}.json",
        }
        (args.output / f"{mechanism}.json").write_text(
            json.dumps(
                _jsonable(
                    {
                        "status": "DIAGNOSTIC_ONLY",
                        "source_sha": git_head(),
                        "mechanism": mechanism,
                        "description": configuration["description"],
                        "configuration": configuration,
                        "results": [_public_result(row) for row in mechanism_rows],
                        "repeat_checks": repeat_checks,
                    }
                ),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    baseline_summary = {
        case["id"]: {
            "fixed_status": baseline_rows[(case["id"], "fixed")]["status"],
            "adaptive_status": baseline_rows[(case["id"], "adaptive")]["status"],
            "fixed_failure_reason": baseline_rows[(case["id"], "fixed")]["failure_reason"],
            "adaptive_failure_reason": baseline_rows[(case["id"], "adaptive")]["failure_reason"],
        }
        for case in cases
    }
    report: dict[str, Any] = {
        "status": "DIAGNOSTIC_ONLY",
        "source_sha": git_head(),
        "dirty": git_dirty(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "case_count": len(cases),
        "cases": cases,
        "mechanisms": mechanism_reports,
        "baseline_summary": baseline_summary,
        "persistent_failure_ids": sorted(PERSISTENT_IDS),
        "repeat_policy": "persistent failures repeated twice; nominal references once",
        "diagnostics_only": True,
        "formulation_changed": False,
        "tangent_changed": False,
        "default_path_changed": False,
        "no_new_thresholds": True,
    }
    serializable = _jsonable(report)
    (args.output / "tl_robustness_rnd.json").write_text(
        json.dumps(serializable, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = {
        key: serializable[key]
        for key in (
            "status",
            "source_sha",
            "dirty",
            "case_count",
            "cases",
            "mechanisms",
            "baseline_summary",
            "persistent_failure_ids",
            "repeat_policy",
            "formulation_changed",
            "tangent_changed",
            "default_path_changed",
        )
    }
    (args.output / "tl_robustness_rnd_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output / "tl_robustness_rnd.md").write_text(_markdown(serializable), encoding="utf-8")
    print(
        json.dumps(
            {
                "source_sha": serializable["source_sha"],
                "dirty": serializable["dirty"],
                "case_count": serializable["case_count"],
                "mechanisms": list(serializable["mechanisms"]),
                "baseline": serializable["baseline_summary"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
