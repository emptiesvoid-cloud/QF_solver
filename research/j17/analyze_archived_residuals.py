"""Recompute archived J16 residual diagnostics without assembling or solving FEM."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
import sys
import threading
import time
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mpmath as mp
import numpy as np
import psutil
import scipy
from scipy.sparse import csr_matrix

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
import solveur
from research.j17.exact_residual import evaluate_exact_residual, exact_fraction
from solveur.core.errors import NumericalConvergenceError
from solveur.core.solvers.linear import LinearSystemSolver

CONTRACT_PATH = ROOT / "research/j17/contracts/archived_exact_recheck_002.json"
INVENTORY_PATH = ROOT / "research/j17/inputs/source_inventory.json"
INPUT_ROOT = ROOT / "research/j17/inputs/guard_resolution_001"
SITE_INPUT = ROOT / "research/j17/inputs/mesh_site_assets_004"
OUTPUT = ROOT / "research/j17/results/archived_exact_recheck_002"
FREQUENCIES = {
    "guard_frequency_2p300000000.npz": 2.3,
    "guard_frequency_2p375818178.npz": 2.375818178440047,
    "guard_frequency_2p417000000.npz": 2.417,
    "guard_frequency_2p418000000.npz": 2.418,
    "guard_frequency_2p450000000.npz": 2.45,
}
VARIANTS = {"spsolve_unscaled": "unscaled", "spsolve_row_column_equilibrated": "scaled", "splu_two_refinements": "refined"}
TOL = 1.0e-7


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify() -> tuple[dict[str, Any], dict[str, Any]]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "J17-NAFEMS13H-ARCHIVED-EXACT-RECHECK-002" or contract.get("state") != "FROZEN_BEFORE_EXECUTION":
        raise ValueError("unexpected or unfrozen J17 archive-recheck contract")
    ancestry = subprocess.run(["git", "merge-base", "HEAD", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    if ancestry != contract["baseline"]["main_commit"]:
        raise ValueError("worktree baseline ancestry differs from contract")
    for rel, expected in contract["source_sha256"].items():
        if sha256(ROOT / rel) != expected:
            raise ValueError(f"source SHA mismatch: {rel}")
    inventory_sha = sha256(INVENTORY_PATH)
    if inventory_sha != contract["inputs"]["inventory_sha256"]:
        raise ValueError("copied input inventory SHA mismatch")
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    for item in inventory["artifacts"]:
        path = ROOT / "research/j17/inputs" / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise ValueError(f"copied input hash/size mismatch: {item['path']}")

    original_manifest_path = INPUT_ROOT / "artifact_manifest.json"
    current_manifest_sha = sha256(original_manifest_path)
    if current_manifest_sha != contract["inputs"]["original_guard_manifest_sha256_current"]:
        raise ValueError("current J16 source-manifest SHA differs from contract")
    source_provenance = inventory["source_j16"]
    if source_provenance["manifest_sha256_frozen_by_j16_contract"] != contract["inputs"]["j16_frozen_manifest_sha256"]:
        raise ValueError("recorded J16 contract manifest SHA differs from inventory")
    original = json.loads(original_manifest_path.read_text(encoding="utf-8"))
    verified, mismatched = [], []
    for entry in original["artifacts"]:
        name = entry["path"]
        path = INPUT_ROOT / name
        good = bool(path.is_file() and path.stat().st_size == entry["bytes"] and sha256(path) == entry["sha256_raw"])
        (verified if good else mismatched).append(name)
    expected_counts = contract["inputs"]["upstream_manifest_observation"]
    if len(verified) != expected_counts["verified_selected_artifact_count"] or len(mismatched) != expected_counts["mismatched_selected_artifact_count"]:
        raise ValueError("J16 source-manifest verification counts differ from contract")

    site_manifest = json.loads((SITE_INPUT / "artifact_manifest.json").read_text(encoding="utf-8"))
    site_items = {item["path"]: item for item in site_manifest["artifacts"]}
    for name in ("mesh_comparison_amplitude_phase.png", "mesh_comparison_frequency_response.csv", "mesh_comparison_summary.json"):
        entry, path = site_items.get(name), SITE_INPUT / name
        if entry is None or path.stat().st_size != entry["bytes"] or sha256(path) != entry["sha256"]:
            raise ValueError(f"J16 gallery asset failed source-manifest validation: {name}")
    return contract, {
        "inventory_sha256": inventory_sha,
        "upstream_manifest_sha256_current": current_manifest_sha,
        "j16_frozen_manifest_sha256": source_provenance["manifest_sha256_frozen_by_j16_contract"],
        "j16_output_recorded_manifest_sha256": source_provenance["manifest_sha256_recorded_by_j16_output"],
        "j16_manifest_hash_reconciled": current_manifest_sha == source_provenance["manifest_sha256_frozen_by_j16_contract"],
        "verified_selected_upstream_artifacts": verified,
        "mismatched_selected_upstream_artifacts": mismatched,
    }


def _complex(real: np.ndarray, imag: np.ndarray) -> np.ndarray:
    value = np.empty(real.shape, dtype=np.complex128)
    value.real = np.asarray(real, dtype=np.float64)
    value.imag = np.asarray(imag, dtype=np.float64)
    return value


def _mp(value: Any) -> mp.mpf:
    numerator, denominator = float(value).as_integer_ratio()
    return mp.mpf(numerator) / denominator


def _mpz(value: Any) -> mp.mpc:
    return mp.mpc(_mp(value.real), _mp(value.imag))


def _mp_metrics(a: np.ndarray, b: np.ndarray, x: np.ndarray) -> dict[str, mp.mpf]:
    with mp.workdps(100):
        aa = [[_mpz(a[i, j]) for j in range(a.shape[1])] for i in range(a.shape[0])]
        bb = [_mpz(v) for v in b]
        xx = [_mpz(v) for v in x]
        ax = [mp.fsum([aa[i][j] * xx[j] for j in range(len(xx))]) for i in range(len(xx))]
        residual = [ax[i] - bb[i] for i in range(len(bb))]
        r2 = mp.sqrt(mp.fsum([abs(v) ** 2 for v in residual]))
        b2 = mp.sqrt(mp.fsum([abs(v) ** 2 for v in bb]))
        ax2 = mp.sqrt(mp.fsum([abs(v) ** 2 for v in ax]))
        rel = r2 / max(b2, ax2) if max(b2, ax2) else mp.mpf("0")
        anorm = max([mp.fsum([abs(v) for v in row]) for row in aa], default=mp.mpf("0"))
        xnorm = max([abs(v) for v in xx], default=mp.mpf("0"))
        bnorm = max([abs(v) for v in bb], default=mp.mpf("0"))
        rnorm = max([abs(v) for v in residual], default=mp.mpf("0"))
        eta = rnorm / (anorm * xnorm + bnorm) if anorm * xnorm + bnorm else mp.mpf("0")
        return {"relative_residual": +rel, "backward_error_eta_inf": +eta}


def _guard(a: np.ndarray, b: np.ndarray, x: np.ndarray) -> dict[str, Any]:
    try:
        residual, relative = LinearSystemSolver._validated_residual_metrics(
            csr_matrix(a), b, x, "direct_frequency", {"residual_failure_tolerance": TOL}
        )
        return {"outcome": "WITHIN_GUARD", "relative": relative, "residual": residual, "diagnostics": {}}
    except NumericalConvergenceError as exc:
        details = getattr(exc, "diagnostics", {})
        if "relative_residual_upper_bound" not in details:
            raise ValueError(f"guard rejection was not caused by its roundoff bound: {exc}") from exc
        return {"outcome": "GUARD_REJECTED", "relative": details["relative_residual"], "residual": details["residual_norm"], "diagnostics": details}


def _run(contract: dict[str, Any], input_check: dict[str, Any]) -> dict[str, Any]:
    old_guard = json.loads((INPUT_ROOT / "guard_resolution_summary.json").read_text(encoding="utf-8"))
    old_exact = json.loads((INPUT_ROOT / "guard_exact_residual_summary.json").read_text(encoding="utf-8"))
    guard_records = {r["matrix_archive"]: r for r in old_guard["frequencies"]}
    exact_records = {r["input_matrix_archive"]: r for r in old_exact["records"]}
    records = []
    for archive_name, frequency in FREQUENCIES.items():
        with np.load(INPUT_ROOT / archive_name, allow_pickle=False) as data:
            a = _complex(data["impedance_real"], data["impedance_imag"])
            b = _complex(data["rhs_real"], data["rhs_imag"])
            if a.shape != (175, 175) or b.shape != (175,) or not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
                raise ValueError(f"invalid archived matrix/RHS in {archive_name}")
            condition = float(np.linalg.cond(a, p=2))
            g_record, hp_record = guard_records[archive_name], exact_records[archive_name]
            if abs(float(g_record["frequency_hz"]) - frequency) > 1.0e-12 or g_record["historical_qf_status"] != "QF_GUARD_REJECTED":
                raise ValueError(f"unexpected frequency or historical status in {archive_name}")
            for variant, suffix in VARIANTS.items():
                x = _complex(data[f"x_{suffix}_real"], data[f"x_{suffix}_imag"])
                exact = evaluate_exact_residual(a, b, x, tolerance=TOL)
                if exact.status == "INCONCLUSIVE":
                    raise ValueError(f"exact evaluation inconclusive for {archive_name}/{variant}: {exact.reason}")
                current = _guard(a, b, x)
                mpm = _mp_metrics(a, b, x)
                mpm_text = mp.nstr(mpm["relative_residual"], n=80)
                old_mp = next(v for v in hp_record["variants"] if v["variant"] == variant)
                old_value = Decimal(old_mp["high_precision_relative_residual_l2"])
                with localcontext() as ctx:
                    ctx.prec = 100
                    now_value = Decimal(mpm_text)
                    delta = abs(now_value - old_value) / max(abs(now_value), Decimal("1e-100"))
                    exact_value = (Decimal(exact.relative_residual_squared.numerator) / Decimal(exact.relative_residual_squared.denominator)).sqrt()
                    exact_mp_delta = abs(exact_value - now_value) / max(abs(exact_value), Decimal("1e-100"))
                if delta > Decimal(contract["criteria"]["maximum_relative_delta_vs_j16_mpmath"]):
                    raise ValueError(f"recomputed mpmath check differs from stored J16 value: {archive_name}/{variant}")
                source = g_record["variants"][variant]["guard_recheck"]["diagnostics"]["relative_residual_upper_bound"]
                details = current["diagnostics"]
                records.append({
                    "frequency_hz": frequency,
                    "archive": archive_name,
                    "variant": variant,
                    "condition_number_2_recomputed": condition,
                    "exact_residual_status": exact.status,
                    "residual_l2_exact_squared": exact_fraction(exact.residual_squared),
                    "reference_l2_exact_squared": exact_fraction(exact.reference_squared),
                    "relative_residual_exact_squared": exact_fraction(exact.relative_residual_squared),
                    "threshold_binary64_exact": exact_fraction(exact.threshold_binary64),
                    "residual_l2_display_only": exact.residual_l2_display,
                    "relative_residual_l2_display_only": str(exact_value),
                    "qf_float64_relative_residual_recomputed": current["relative"],
                    "qf_roundoff_bound_norm_recomputed": details.get("matvec_roundoff_bound"),
                    "qf_relative_upper_bound_recomputed": details.get("relative_residual_upper_bound"),
                    "source_guard_upper_bound_comparison_only": source,
                    "guard_bound_delta_vs_source_report": details.get("relative_residual_upper_bound", 0.0) - source,
                    "mpmath_relative_residual_recomputed": mpm_text,
                    "mpmath_backward_error_eta_inf_recomputed": mp.nstr(mpm["backward_error_eta_inf"], n=80),
                    "exact_vs_mpmath_relative_delta": str(exact_mp_delta),
                    "j16_mpmath_reported_relative_residual_comparison_only": str(old_value),
                    "current_qf_guard_outcome": current["outcome"],
                    "historical_qf_route_status": "QF_GUARD_REJECTED",
                })
    if len(records) != 15:
        raise ValueError(f"expected 15 records, got {len(records)}")
    return {
        "schema": "qfsolver-j17-archived-exact-residual-recheck-v1",
        "classification": "EXACT_ARCHIVED_MATRIX_POSTPROCESSING_NO_FEM_OR_SOLVE",
        "contract_id": contract["contract_id"],
        "contract_sha256": sha256(CONTRACT_PATH),
        "source_git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip(),
        "source_sha256": contract["source_sha256"],
        "input_integrity": input_check,
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "mpmath": mp.__version__, "matplotlib": matplotlib.__version__},
        "method": {
            "primary": "Exact Fraction arithmetic over represented binary values; squared L2 residual ratio compared exactly with the square of the unchanged binary64 threshold.",
            "formula": "||A*x-b||2 / max(||b||2, ||A*x||2)",
            "guard": "Re-evaluate the current main branch _validated_residual_metrics on stored A, b, and x. No solver or assembly call.",
            "crosscheck": "Recompute a 100-digit mpmath residual and infinity-norm backward error from exact integer-ratio conversions.",
            "interpretation_limit": "Exact arithmetic has zero arithmetic uncertainty for the represented arrays and formula. It does not bound binary64 input quantization, assembly error, physical model error, or forward error of x."
        },
        "guard_threshold_binary64": TOL,
        "record_count": len(records),
        "exact_status_counts": {s: sum(r["exact_residual_status"] == s for r in records) for s in ("PASS", "FAIL", "INCONCLUSIVE")},
        "current_guard_status_counts": {s: sum(r["current_qf_guard_outcome"] == s for r in records) for s in ("WITHIN_GUARD", "GUARD_REJECTED")},
        "historical_qf_status_counts": {"QF_GUARD_REJECTED": len(records)},
        "records": records,
        "status_policy": "These exact statuses characterize only the archived represented systems. J15/J16 route statuses and historical attempts are unchanged.",
        "resources_observed": {},
    }


def _write(result: dict[str, Any]) -> None:
    if OUTPUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUTPUT}")
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "exact_residual_summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    names = ["frequency_hz", "variant", "condition_number_2_recomputed", "exact_residual_status", "relative_residual_l2_display_only", "qf_float64_relative_residual_recomputed", "qf_relative_upper_bound_recomputed", "current_qf_guard_outcome", "historical_qf_route_status"]
    with (OUTPUT / "exact_residual_points.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=names)
        writer.writeheader()
        writer.writerows({name: row.get(name) for name in names} for row in result["records"])
    colors = {"spsolve_unscaled": "#176b87", "spsolve_row_column_equilibrated": "#b05d21", "splu_two_refinements": "#4b8b3b"}
    fig, axis = plt.subplots(figsize=(10, 6), constrained_layout=True)
    for variant, color in colors.items():
        rows = [row for row in result["records"] if row["variant"] == variant]
        xs = [row["frequency_hz"] for row in rows]
        exact = [float(row["relative_residual_l2_display_only"]) for row in rows]
        bound = [float(row["qf_relative_upper_bound_recomputed"]) for row in rows]
        axis.semilogy(xs, exact, marker="o", color=color, label=f"{variant}: exact represented residual")
        axis.semilogy(xs, bound, marker="x", linestyle="--", color=color, alpha=0.75, label=f"{variant}: guard upper bound")
    axis.axhline(TOL, color="#333333", linestyle=":", label="unchanged tolerance 1e-7")
    axis.set_xlabel("Frequency (Hz)")
    axis.set_ylabel("Relative residual")
    axis.set_title("J17 archived 8x8 systems: exact residual vs recomputed current-guard bound")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend(fontsize=8, ncol=2)
    fig.text(0.5, -0.025, "Exact PASS applies only to stored matrix values; historical QF routes remain rejected.", ha="center", fontsize=9)
    fig.savefig(OUTPUT / "exact_residual_vs_guard_bound.png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    (OUTPUT / "README.md").write_text(
        "# J17 archived residual recheck\n\n"
        "Offline post-processing of five archived 8x8 reduced systems and three stored vectors per frequency. No FEM assembly or solve was run.\n\n"
        "The primary decision compares exact rational squared L2 values with the squared binary64 limit. Decimal norms are display-only. The current QF guard was recomputed from stored matrices, RHS vectors, and solutions. No route result was promoted.\n\n"
        "The current J16 manifest SHA differs from the SHA recorded in the J16 high-precision contract. The five NPZ files used here match their current source-manifest entries; five per-frequency JSON files and the old guard summary do not. Those text records are comparison-only; guard metrics were recalculated.\n",
        encoding="utf-8",
    )
    output_files = [OUTPUT / name for name in ("exact_residual_summary.json", "exact_residual_points.csv", "exact_residual_vs_guard_bound.png", "README.md")]
    manifest = {"schema": "qfsolver-j17-output-manifest-v1", "contract_sha256": result["contract_sha256"], "input_inventory_sha256": result["input_integrity"]["inventory_sha256"], "artifacts": [{"path": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)} for p in output_files]}
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run() -> dict[str, Any]:
    if Path(solveur.__file__).resolve() != (SRC / "solveur" / "__init__.py").resolve():
        raise RuntimeError(f"wrong solveur import origin: {solveur.__file__}")
    proc = psutil.Process()
    peak = [proc.memory_info().rss]
    stop = threading.Event()
    def sample() -> None:
        while not stop.wait(0.1):
            try:
                peak[0] = max(peak[0], proc.memory_info().rss)
            except psutil.Error:
                return
    monitor = threading.Thread(target=sample, daemon=True)
    monitor.start()
    start = time.perf_counter()
    try:
        contract, input_check = _verify()
        result = _run(contract, input_check)
        result["resources_observed"] = {"elapsed_seconds": time.perf_counter() - start, "peak_rss_bytes_sampled": peak[0], "process_count_sampled": 1, "rss_sample_interval_seconds": 0.1, "qualification": "NOT_APPLICABLE_DEVELOPMENT_ONLY"}
        _write(result)
        return result
    finally:
        stop.set()
        monitor.join(timeout=2.0)


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
