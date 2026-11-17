"""Bounded J19 replay of SHA-pinned archived NAFEMS 13H systems."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
import sys
import time
import warnings
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import MatrixRankWarning, spsolve

from research.j17.exact_residual import evaluate_exact_residual
from research.j19.checkpoint import write_atomic_json
from solveur.core.errors import NumericalConvergenceError
from solveur.core.solvers.linear import (
    LinearSystemSolver,
    relative_residual_ratio,
    stable_l2_norm,
)


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "research" / "j19" / "contracts" / "harmonic_replay_001.json"
INPUT_ROOT = ROOT / "research" / "j17" / "inputs" / "guard_resolution_001"
OUTPUT = ROOT / "research" / "j19" / "results" / "harmonic_replay_001"
CHECKPOINT = OUTPUT / "replay.json"
TOLERANCE = 1.0e-7


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _json_exact_result(result: Any) -> dict[str, Any]:
    def fraction_value(value: Any) -> dict[str, str] | None:
        if value is None:
            return None
        return {"numerator": str(value.numerator), "denominator": str(value.denominator)}

    return {
        "status": result.status,
        "reason": result.reason,
        "dimension": result.dimension,
        "nonzero_stored_terms": result.nonzero_entries,
        "stored_entries": result.stored_entries,
        "residual_squared": fraction_value(result.residual_squared),
        "reference_squared": fraction_value(result.reference_squared),
        "relative_residual_squared": fraction_value(result.relative_residual_squared),
        "threshold_binary64": fraction_value(result.threshold_binary64),
        "residual_l2_display_only": result.residual_l2_display,
        "relative_residual_display_only": result.relative_residual_display,
    }


def _write_csv(rows: list[dict[str, Any]]) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT / ".replay.csv.tmp"
    fields = (
        "frequency_hz",
        "amplitude_mm",
        "phase_degrees",
        "float64_relative_residual",
        "guard_outcome",
        "guard_upper_bound",
        "exact_status",
        "exact_reason",
        "record_state",
    )
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            exact = row.get("exact_represented_system", {})
            writer.writerow(
                {
                    "frequency_hz": row.get("frequency_hz"),
                    "amplitude_mm": row.get("center_uz_amplitude_mm"),
                    "phase_degrees": row.get("center_uz_phase_degrees"),
                    "float64_relative_residual": row.get("float64_relative_residual"),
                    "guard_outcome": row.get("current_guard_outcome", "PENDING"),
                    "guard_upper_bound": row.get("current_guard_diagnostics", {}).get(
                        "relative_residual_upper_bound"
                    ),
                    "exact_status": exact.get("status", "PENDING"),
                    "exact_reason": exact.get("reason", ""),
                    "record_state": row.get("record_state"),
                }
            )
        stream.flush()
    temporary.replace(OUTPUT / "replay.csv")


def _plot_results(rows: list[dict[str, Any]]) -> None:
    complete = [row for row in rows if row.get("record_state") == "COMPLETE"]
    if not complete:
        return
    frequencies = [float(row["frequency_hz"]) for row in complete]
    amplitudes = [float(row["center_uz_amplitude_mm"]) for row in complete]
    phases = [float(row["center_uz_phase_degrees"]) for row in complete]
    colors = {"GUARD_ACCEPTED": "#19734b", "GUARD_REJECTED": "#b04719"}
    markers = {"GUARD_ACCEPTED": "o", "GUARD_REJECTED": "x"}
    fig, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    for row in complete:
        outcome = str(row["current_guard_outcome"])
        exact_status = str(row["exact_represented_system"].get("status", "INCONCLUSIVE"))
        label = f"{outcome.replace('GUARD_', 'G-')} / exact {exact_status}"
        style = {
            "color": colors.get(outcome, "#666666"),
            "marker": markers.get(outcome, "s"),
            "linestyle": "none",
            "markersize": 8,
        }
        axes[0].plot([row["frequency_hz"]], [row["center_uz_amplitude_mm"]], label=label, **style)
        axes[1].plot([row["frequency_hz"]], [row["center_uz_phase_degrees"]], label=label, **style)
    axes[0].set_ylabel("Centre UZ amplitude (mm)")
    axes[1].set_ylabel("Centre UZ phase (degrees)")
    axes[1].set_xlabel("Frequency (Hz)")
    axes[0].set_title("Archived NAFEMS 13H systems — guard and exact residual statuses")
    for axis in axes:
        axis.grid(True, alpha=0.25)
        axis.legend(fontsize=7, loc="best")
    fig.text(
        0.5,
        0.01,
        "Discrete archived matrix points; published NAFEMS/Abaqus peaks are context only, not pointwise references.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(OUTPUT / "amplitude_phase.png", dpi=160)
    plt.close(fig)


def run_replay() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("state") != "FROZEN_BEFORE_EXECUTION":
        raise RuntimeError("J19 replay contract is not frozen")
    if OUTPUT.exists() and any(OUTPUT.iterdir()):
        raise RuntimeError("J19 output already exists; refusing to overwrite a prior attempt")
    expected_inventory = contract["source_inventory_sha256"]
    inventory = ROOT / contract["source_inventory"]
    if sha256(inventory) != expected_inventory:
        raise RuntimeError("J17 source inventory SHA-256 mismatch")
    for relative, expected in contract["input_sha256"].items():
        if sha256(ROOT / relative) != expected:
            raise RuntimeError(f"input SHA-256 mismatch: {relative}")
    if sha256(ROOT / contract["reference_digest_path"]) != contract["reference_digest_sha256"]:
        raise RuntimeError("external reference digest SHA-256 mismatch")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    journal: dict[str, Any] = {
        "schema": "qfsolver-j19-harmonic-replay-v1",
        "contract_id": contract["contract_id"],
        "attempt_id": contract["attempt_id"],
        "source_code_commit": contract["source_code_commit"],
        "execution_source_commit": _git_head(),
        "run_state": "RUNNING",
        "classification": "ARCHIVED_MATRIX_SOLVES_NO_FEM_ASSEMBLY",
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
        },
        "threshold_binary64": TOLERANCE,
        "phase_convention": "u(t)=Re(U*exp(i*omega*t))",
        "center_reduced_uz_dof": contract["center_reduced_uz_dof"],
        "results": [],
    }
    write_atomic_json(CHECKPOINT, journal)

    for item in contract["frequencies"]:
        frequency = float(item["frequency_hz"])
        archive_path = ROOT / item["archive_path"]
        record: dict[str, Any] = {
            "frequency_hz": frequency,
            "archive_path": item["archive_path"],
            "input_sha256": item["sha256"],
            "record_state": "IN_PROGRESS",
            "current_guard_outcome": "PENDING",
            "exact_represented_system": {"status": "INCONCLUSIVE", "reason": "not evaluated yet"},
        }
        journal["results"].append(record)
        write_atomic_json(CHECKPOINT, journal)

        load_started = time.perf_counter()
        with np.load(archive_path, allow_pickle=False) as archive:
            impedance = np.asarray(archive["impedance_real"], dtype=np.float64) + 1j * np.asarray(
                archive["impedance_imag"], dtype=np.float64
            )
            rhs = np.asarray(archive["rhs_real"], dtype=np.float64) + 1j * np.asarray(
                archive["rhs_imag"], dtype=np.float64
            )
            archived_solution = np.asarray(archive["x_unscaled_real"], dtype=np.float64) + 1j * np.asarray(
                archive["x_unscaled_imag"], dtype=np.float64
            )
        load_seconds = time.perf_counter() - load_started

        matrix = csr_matrix(impedance, dtype=np.complex128)
        if matrix.shape != (175, 175) or matrix.nnz != 3607 or not np.array_equal(matrix.toarray(), impedance):
            record.update(record_state="INCONCLUSIVE", reason="matrix shape, stored entries, or values differ")
            write_atomic_json(CHECKPOINT, journal)
            continue
        if rhs.shape != (175,) or archived_solution.shape != (175,):
            record.update(record_state="INCONCLUSIVE", reason="RHS or archived solution shape differs")
            write_atomic_json(CHECKPOINT, journal)
            continue

        matrix_hash = hashlib.sha256(np.ascontiguousarray(matrix.data).view(np.uint8).tobytes()).hexdigest()
        rhs_hash = hashlib.sha256(np.ascontiguousarray(rhs).view(np.uint8).tobytes()).hexdigest()
        solve_started = time.perf_counter()
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", MatrixRankWarning)
                solution = np.asarray(spsolve(matrix.tocsc(), rhs), dtype=np.complex128)
        except Exception as exc:
            record.update(
                record_state="INCONCLUSIVE",
                reason=f"linear solve raised {type(exc).__name__}: {exc}",
                timing_seconds={"archive_load": load_seconds, "solve": time.perf_counter() - solve_started},
            )
            write_atomic_json(CHECKPOINT, journal)
            continue
        solve_seconds = time.perf_counter() - solve_started
        if not np.all(np.isfinite(solution)):
            record.update(record_state="INCONCLUSIVE", reason="sparse solve returned non-finite values")
            write_atomic_json(CHECKPOINT, journal)
            continue

        product = matrix @ solution
        raw_residual = product - rhs
        raw_relative = relative_residual_ratio(
            stable_l2_norm(raw_residual), max(stable_l2_norm(rhs), stable_l2_norm(product))
        )
        center_uz = complex(solution[contract["center_reduced_uz_dof"]])
        archived_scale = float(np.max(np.abs(archived_solution), initial=0.0))
        solution_delta = float(
            np.max(np.abs(solution - archived_solution), initial=0.0)
            / max(archived_scale, np.finfo(float).tiny)
        )
        record.update(
            record_state="SOLUTION_CHECKPOINTED",
            matrix_values_sha256=matrix_hash,
            rhs_values_sha256=rhs_hash,
            matrix_shape=list(matrix.shape),
            csr_stored_entries=int(matrix.nnz),
            rhs_norm=float(stable_l2_norm(rhs)),
            float64_residual_norm=float(stable_l2_norm(raw_residual)),
            float64_relative_residual=float(raw_relative),
            center_uz_real_mm=float(1000.0 * center_uz.real),
            center_uz_imag_mm=float(1000.0 * center_uz.imag),
            center_uz_amplitude_mm=float(1000.0 * abs(center_uz)),
            center_uz_phase_degrees=float(np.degrees(np.angle(center_uz))),
            solution_real=solution.real.tolist(),
            solution_imag=solution.imag.tolist(),
            relative_solution_difference_inf_vs_archived_unscaled=solution_delta,
            matrix_rank_warnings=[str(item.message) for item in caught],
            current_guard_outcome="PENDING",
            exact_represented_system={"status": "INCONCLUSIVE", "reason": "pending exact evaluation"},
            timing_seconds={"archive_load": load_seconds, "solve": solve_seconds},
        )
        write_atomic_json(CHECKPOINT, journal)

        guard_started = time.perf_counter()
        try:
            guard_residual, guard_relative = LinearSystemSolver._validated_residual_metrics(
                matrix, rhs, solution, "j19_archived_direct_frequency", {"residual_failure_tolerance": TOLERANCE}
            )
            guard_outcome = "GUARD_ACCEPTED"
            guard_diagnostics: dict[str, Any] = {
                "residual_norm": guard_residual,
                "relative_residual": guard_relative,
                "relative_residual_upper_bound": guard_relative,
                "residual_failure_tolerance": TOLERANCE,
            }
        except NumericalConvergenceError as exc:
            guard_outcome = "GUARD_REJECTED"
            guard_diagnostics = dict(exc.diagnostics or {})
            guard_diagnostics["message"] = str(exc)
        guard_seconds = time.perf_counter() - guard_started
        record.update(
            record_state="GUARD_CHECKPOINTED",
            current_guard_outcome=guard_outcome,
            current_guard_diagnostics=guard_diagnostics,
        )
        record["timing_seconds"]["current_guard_recheck"] = guard_seconds
        write_atomic_json(CHECKPOINT, journal)

        exact_started = time.perf_counter()
        exact = evaluate_exact_residual(
            matrix,
            rhs,
            solution,
            tolerance=TOLERANCE,
            max_dimension=contract["exact_limits"]["max_dimension"],
            max_nonzero_entries=contract["exact_limits"]["max_sparse_stored_entries"],
            max_fraction_bits=contract["exact_limits"]["max_fraction_bits"],
            max_elapsed_seconds=contract["exact_limits"]["max_seconds_per_frequency"],
        )
        record["timing_seconds"]["exact_rational_evaluation"] = time.perf_counter() - exact_started
        record["exact_represented_system"] = _json_exact_result(exact)
        record["record_state"] = "COMPLETE"
        write_atomic_json(CHECKPOINT, journal)

    required_frequencies = [float(item["frequency_hz"]) for item in contract["frequencies"]]
    present = [float(row["frequency_hz"]) for row in journal["results"]]
    journal["run_state"] = "COMPLETE" if present == required_frequencies and all(
        row["record_state"] == "COMPLETE" for row in journal["results"]
    ) else "COMPLETED_WITH_INCONCLUSIVE_POINTS"
    journal["duration_seconds"] = time.perf_counter() - started
    journal["published_peak_context"] = contract["published_peak_context"]
    journal["limitations"] = contract["limitations"]
    write_atomic_json(CHECKPOINT, journal)
    _write_csv(journal["results"])
    _plot_results(journal["results"])
    _write_readme(journal)
    _write_manifest()
    return journal


def _write_readme(journal: dict[str, Any]) -> None:
    lines = [
        "# J19 — bounded archived NAFEMS 13H harmonic replay",
        "",
        f"Contract: {journal['contract_id']}.",
        "",
        "Five SHA-pinned J16 impedance/RHS archives were solved again. No FEM assembly or local Abaqus execution was performed.",
        "The JSON is atomically updated at each frequency and retains the solved vector before guard/exact post-processing.",
        "Guard and exact represented-system statuses are separate; this is not a qualification of assembly or physical accuracy.",
        "",
        "See replay.csv and replay.json for frequencies, amplitudes, phases, input hashes, residual statuses and timings.",
        "The figure uses only discrete archived points; published NAFEMS/Abaqus peaks are peak-only context.",
        "",
    ]
    (OUTPUT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def _write_manifest() -> None:
    files = {}
    for path in sorted(OUTPUT.iterdir()):
        if path.is_file() and path.name not in {"artifact_manifest.json", ".replay.csv.tmp"}:
            raw = path.read_bytes()
            files[path.name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps(
            {
                "schema": "qfsolver-j19-harmonic-artifact-manifest-v1",
                "contract_id": json.loads(CONTRACT.read_text(encoding="utf-8"))["contract_id"],
                "files": files,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    run_replay()
