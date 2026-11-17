"""Validate and assemble privacy-safe J16 harmonic mesh-study site assets."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import psutil


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = PROJECT_ROOT / "research/j16/contracts/nafems_13h_mesh_site_assets_002.json"
RESULT_ROOT = PROJECT_ROOT / "research/j16/results/diagnostic-2026-11-17/mesh_study_003"
RUN_ROOT = PROJECT_ROOT / ".codex/development-runs/worktrees/j16_mesh_r3"
REFERENCE_PATH = PROJECT_ROOT / "qualification/external_reference_digests/abaqus_nafems_13h_harmonic.json"
ASSET_ROOT = PROJECT_ROOT / "research/j16/site_assets/nafems13h_mesh_study_003"
MESHES = (6, 8, 10)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_mesh_data(mesh_data: dict[int, dict[str, Any]]) -> None:
    """Check shared model/grid definitions and preserve every route status."""
    if tuple(sorted(mesh_data)) != MESHES:
        raise ValueError("mesh set must contain exactly 6x6, 8x8, and 10x10")
    first = mesh_data[MESHES[0]]
    common_keys = ("geometry_m", "material", "pressure_pa", "rayleigh_damping", "conditions", "observable", "frequency_grid_hz")
    for mesh, data in mesh_data.items():
        if any(data.get(key) != first.get(key) for key in common_keys):
            raise ValueError(f"mesh {mesh} does not share the frozen model and frequency grid")
        rows = data.get("rows", [])
        if len(rows) != 62 or len({row["frequency_hz"] for row in rows}) != 62:
            raise ValueError(f"mesh {mesh} must preserve 62 unique frequency records")
        if any(row.get("qf_route_status") not in {"QF_SOLVE_ACCEPTED", "QF_GUARD_REJECTED"} for row in rows):
            raise ValueError(f"mesh {mesh} contains a missing or harness-error route status")
    reference_frequencies = {row["frequency_hz"] for row in first["rows"]}
    if any({row["frequency_hz"] for row in data["rows"]} != reference_frequencies for data in mesh_data.values()):
        raise ValueError("mesh response grids do not match")


def summarize_mesh(
    data: dict[str, Any], run_record: dict[str, Any], reference: dict[str, Any]
) -> dict[str, Any]:
    rows = data["rows"]
    counts = Counter(row["qf_route_status"] for row in rows)
    reference_peak = data["navier_damped_peak_estimate_hz"]
    navier_probe = min(rows, key=lambda row: abs(row["frequency_hz"] - reference_peak))
    nafems_reference = reference["nafems_reference"]
    abaqus_s4r = next(
        item for item in reference["abaqus_direct_results"] if item["element"] == "S4R"
    )
    external_peak_hz = abaqus_s4r["peak_frequency_hz"]
    external_probe = min(rows, key=lambda row: abs(row["frequency_hz"] - external_peak_hz))
    raw_peak = data["raw_diagnostic_local_quadratic_peak_estimate"]
    qf_peak = data["raw_diagnostic_sampled_peak"]
    nodes = data["nodes"]
    return {
        "mesh_size_per_edge": data["mesh_size"],
        "element_count": data["mesh_size"] ** 2,
        "nodes": nodes,
        "full_dofs": data["full_dofs"],
        "free_dofs": data["free_dofs"],
        "fixed_dofs": data["fixed_dofs"],
        "qf_assembled_first_frequency_hz": data["modal_frequency_from_qf_assembled_KM_hz"],
        "qf_raw_sampled_peak": qf_peak,
        "qf_raw_local_quadratic_peak_estimate": raw_peak,
        "relative_peak_frequency_difference_vs_navier_percent": 100.0 * (raw_peak["frequency_hz"] - reference_peak) / reference_peak,
        "relative_peak_amplitude_difference_vs_nafems_percent": 100.0 * (raw_peak["amplitude_mm"] - nafems_reference["peak_displacement_mm"]) / nafems_reference["peak_displacement_mm"],
        "relative_peak_frequency_difference_vs_abaqus_s4r_direct_percent": 100.0 * (raw_peak["frequency_hz"] - external_peak_hz) / external_peak_hz,
        "relative_peak_amplitude_difference_vs_abaqus_s4r_direct_percent": 100.0 * (raw_peak["amplitude_mm"] - abaqus_s4r["peak_displacement_mm"]) / abaqus_s4r["peak_displacement_mm"],
        "at_navier_damped_peak_probe": {
            "frequency_hz": navier_probe["frequency_hz"],
            "qf_route_status": navier_probe["qf_route_status"],
            "raw_qf_amplitude_mm": navier_probe["raw_center_uz_amplitude_mm"],
            "raw_qf_phase_degrees": navier_probe["raw_center_uz_phase_degrees"],
            "navier_amplitude_mm": navier_probe["reference_center_uz_amplitude_mm"],
            "navier_phase_degrees": navier_probe["reference_center_uz_phase_degrees"],
            "normalized_complex_error_by_reference_band_peak": navier_probe["complex_error_normalized_by_reference_band_peak"],
        },
        "at_abaqus_s4r_peak_frequency": {
            "frequency_hz": external_probe["frequency_hz"],
            "qf_route_status": external_probe["qf_route_status"],
            "raw_qf_amplitude_mm": external_probe["raw_center_uz_amplitude_mm"],
            "raw_qf_phase_degrees": external_probe["raw_center_uz_phase_degrees"],
        },
        "qf_route_status_counts": dict(counts),
        "max_raw_relative_l2_residual": max(row["raw_reduced_relative_residual_l2"] for row in rows),
        "max_raw_backward_error_eta_inf": max(row["raw_reduced_backward_error_eta_inf"] for row in rows),
        "force_resultant_check": data["assembled_load_resultant"],
        "runner": {
            "state": run_record["state"],
            "elapsed_seconds": run_record["metrics"]["elapsed_seconds"],
            "peak_rss_bytes_sampled": run_record["metrics"]["peak_rss_bytes"],
            "max_process_count_sampled": run_record["metrics"]["peak_process_count"],
            "budget": run_record["metrics"]["budgets"],
            "qualification": run_record["qualification"],
        },
        "status_policy": "Diagnostic peak values come from raw vectors; near-peak points remain QF_GUARD_REJECTED and are not accepted QF results.",
    }


def _load_inputs(contract: dict[str, Any]) -> tuple[dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[str, Any]]:
    for rel, expected in contract["inputs"]["input_sha256"].items():
        actual = _sha256(PROJECT_ROOT / rel)
        if actual != expected:
            raise ValueError(f"input SHA mismatch for {rel}: {actual} != {expected}")
    mesh_data = {}
    runner_data = {}
    for mesh in MESHES:
        folder = f"mesh_{mesh:02d}"
        mesh_data[mesh] = json.loads((RESULT_ROOT / folder / "site_data.json").read_text(encoding="utf-8"))
        series = f"dev-j16-nafems13h-mesh-{mesh:02d}-003"
        run_path = RUN_ROOT / series / "attempt-0001" / "run.json"
        runner_data[mesh] = json.loads(run_path.read_text(encoding="utf-8"))
        expected_node = f"tests/verification/test_j16_harmonic_diagnostics.py::test_j16_nafems13h_mesh_{mesh:02d}"
        if runner_data[mesh].get("state") != "PASS" or runner_data[mesh].get("target") != [expected_node]:
            raise ValueError(f"mesh {mesh} runner record is not the expected completed diagnostic attempt")
        if runner_data[mesh].get("qualification") != "NOT_APPLICABLE_DEVELOPMENT_ONLY":
            raise ValueError(f"mesh {mesh} runner state must remain development-only")
    validate_mesh_data(mesh_data)
    external_reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    return mesh_data, runner_data, external_reference


def _plot_comparison(mesh_data: dict[int, dict[str, Any]], reference: dict[str, Any], path: Path) -> None:
    colors = {6: "#2468a2", 8: "#d77b00", 10: "#29855b"}
    fig, (amplitude_ax, phase_ax) = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
    reference_rows = sorted(mesh_data[6]["rows"], key=lambda row: row["frequency_hz"])
    frequency = np.asarray([row["frequency_hz"] for row in reference_rows])
    reference_amplitude = np.asarray([row["reference_center_uz_amplitude_mm"] for row in reference_rows])
    reference_phase = np.asarray([row["reference_center_uz_phase_degrees"] for row in reference_rows])
    amplitude_ax.plot(frequency, reference_amplitude, color="#1c5c78", linewidth=2.1, linestyle="--", label="Navier Kirchhoff–Love analytical series")
    phase_ax.plot(frequency, reference_phase, color="#1c5c78", linewidth=2.1, linestyle="--", label="Navier Kirchhoff–Love analytical series")

    for mesh, data in mesh_data.items():
        rows = sorted(data["rows"], key=lambda row: row["frequency_hz"])
        x = np.asarray([row["frequency_hz"] for row in rows])
        y_amp = np.asarray([row["raw_center_uz_amplitude_mm"] for row in rows])
        y_phase = np.asarray([row["raw_center_uz_phase_degrees"] for row in rows])
        accepted = np.asarray([row["qf_route_status"] == "QF_SOLVE_ACCEPTED" for row in rows])
        amplitude_ax.plot(x, y_amp, color=colors[mesh], linewidth=1.4, label=f"MITC4 {mesh}×{mesh} raw diagnostic")
        phase_ax.plot(x, y_phase, color=colors[mesh], linewidth=1.4, label=f"MITC4 {mesh}×{mesh} raw diagnostic")
        amplitude_ax.scatter(x[~accepted], y_amp[~accepted], marker="x", color=colors[mesh], s=25, linewidths=1.1)
        phase_ax.scatter(x[~accepted], y_phase[~accepted], marker="x", color=colors[mesh], s=25, linewidths=1.1)
        if np.any(accepted):
            amplitude_ax.scatter(x[accepted], y_amp[accepted], marker="o", facecolor=colors[mesh], edgecolor="black", s=28, linewidths=0.5)
            phase_ax.scatter(x[accepted], y_phase[accepted], marker="o", facecolor=colors[mesh], edgecolor="black", s=28, linewidths=0.5)

    nafems_reference = reference["nafems_reference"]
    abaqus_s4r = next(
        item for item in reference["abaqus_direct_results"] if item["element"] == "S4R"
    )
    navier_peak_hz = mesh_data[6]["navier_damped_peak_estimate_hz"]
    amplitude_ax.scatter(
        [nafems_reference["peak_frequency_hz"]],
        [nafems_reference["peak_displacement_mm"]],
        marker="*", color="#7b3294", s=125, zorder=10, label="NAFEMS published peak",
    )
    amplitude_ax.scatter(
        [abaqus_s4r["peak_frequency_hz"]],
        [abaqus_s4r["peak_displacement_mm"]],
        marker="D", color="black", s=45, zorder=10, label="Abaqus S4R direct table peak",
    )
    amplitude_ax.axvline(navier_peak_hz, color="#1c5c78", linestyle=":", linewidth=1.0)
    amplitude_ax.axvline(abaqus_s4r["peak_frequency_hz"], color="black", linestyle=":", linewidth=0.9)
    amplitude_ax.set_ylabel("Center |UZ| (mm)")
    amplitude_ax.set_title("NAFEMS 13H harmonic response; rejected QF points retain × markers")
    amplitude_ax.grid(True, alpha=0.25)
    amplitude_ax.legend(loc="upper left", fontsize=8, ncol=2)
    phase_ax.axvline(navier_peak_hz, color="#1c5c78", linestyle=":", linewidth=1.0, label="Navier damped peak")
    phase_ax.set_xlabel("Frequency (Hz)")
    phase_ax.set_ylabel("Center UZ phase (degrees; exp(+iωt))")
    phase_ax.grid(True, alpha=0.25)
    phase_ax.legend(loc="best", fontsize=8, ncol=2)
    fig.text(0.5, 0.008, "QF curves use archived raw spsolve vectors where the production guard rejected the point; markers show the per-point route status. No QF PASS is inferred.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _write_csv(mesh_data: dict[int, dict[str, Any]], path: Path) -> int:
    fields = [
        "mesh_size", "frequency_hz", "qf_route_status", "raw_center_uz_amplitude_mm",
        "raw_center_uz_phase_degrees", "reference_center_uz_amplitude_mm",
        "reference_center_uz_phase_degrees", "complex_error_normalized_by_reference_band_peak",
        "raw_reduced_relative_residual_l2", "raw_reduced_backward_error_eta_inf",
    ]
    count = 0
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for mesh, data in mesh_data.items():
            for row in data["rows"]:
                writer.writerow({"mesh_size": mesh, **{field: row.get(field) for field in fields if field != "mesh_size"}})
                count += 1
    return count


def assemble_site_assets() -> dict[str, Any]:
    started = time.perf_counter()
    process = psutil.Process()
    peak_rss = [process.memory_info().rss]
    stop_monitor = threading.Event()

    def sample_rss() -> None:
        while not stop_monitor.wait(0.1):
            try:
                peak_rss[0] = max(peak_rss[0], process.memory_info().rss)
            except psutil.Error:
                return

    monitor = threading.Thread(target=sample_rss, name="j16-site-assets-rss-monitor", daemon=True)
    monitor.start()
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "J16-NAFEMS13H-MESH-SITE-ASSETS-002" or contract.get("state") != "FROZEN_BEFORE_EXECUTION":
        raise ValueError("the mesh-study site-asset contract is missing or not frozen")
    for rel, expected in contract["source_sha256"].items():
        actual = _sha256(PROJECT_ROOT / rel)
        if actual != expected:
            raise ValueError(f"source SHA mismatch for {rel}: {actual} != {expected}")
    mesh_data, runner_data, reference = _load_inputs(contract)
    ASSET_ROOT.mkdir(parents=True, exist_ok=True)
    summaries = {}
    for mesh, data in mesh_data.items():
        out_dir = ASSET_ROOT / f"mesh_{mesh:02d}"
        out_dir.mkdir(parents=True, exist_ok=True)
        source_dir = RESULT_ROOT / f"mesh_{mesh:02d}"
        for name in ("site_data.json", "frequency_response.csv", "mesh_setup.png", "peak_deformation.png"):
            shutil.copyfile(source_dir / name, out_dir / name)
        summaries[str(mesh)] = summarize_mesh(data, runner_data[mesh], reference)
    _plot_comparison(mesh_data, reference, ASSET_ROOT / "mesh_comparison_amplitude_phase.png")
    total_rows = _write_csv(mesh_data, ASSET_ROOT / "mesh_comparison_frequency_response.csv")
    summary = {
        "schema": "qfsolver-j16-nafems13h-mesh-site-assets-v1",
        "classification": "EXPLORATORY_RESULTS_FOR_REVIEW_NOT_PUBLISHED",
        "contract_id": contract["contract_id"],
        "contract_sha256": _sha256(CONTRACT_PATH),
        "source_git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, check=True, capture_output=True, text=True).stdout.strip(),
        "source_mesh_contract_id": "J16-MITC4-NAFEMS13H-MESH-STUDY-003",
        "model_common_to_all_meshes": {
            "geometry_m": mesh_data[6]["geometry_m"],
            "material": mesh_data[6]["material"],
            "pressure_pa": mesh_data[6]["pressure_pa"],
            "rayleigh_damping": mesh_data[6]["rayleigh_damping"],
            "conditions": mesh_data[6]["conditions"],
            "observable": mesh_data[6]["observable"],
            "frequency_grid_hz": mesh_data[6]["frequency_grid_hz"],
        },
        "official_reference": {
            "source": reference["source"]["url"],
            "nafems_direct_peak": {"frequency_hz": 2.377, "center_displacement_mm": 45.42},
            "abaqus_s4r_direct_peak": {"frequency_hz": 2.405, "center_displacement_mm": 45.38},
            "published_phase_available": False,
            "abaqus_was_executed_locally": False,
        },
        "mesh_summaries": summaries,
        "frequency_row_count": total_rows,
        "status_policy": "The 6x6, 8x8, and 10x10 route counts are retained as run. Raw diagnostics at rejected frequencies are not promoted to accepted responses or a mechanics PASS.",
        "limitations": [
            "The thin Kirchhoff-Love Navier series is analytically independent but is not the MITC4/Reissner-Mindlin finite-thickness formulation.",
            "The official Abaqus table provides scalar direct peaks but no phase curve; Abaqus was not run locally.",
            "The mesh trend is exploratory: near-peak points are rejected by the unchanged QF residual guard for all 8x8 and 10x10 frequencies, and all but nine low-frequency 6x6 points.",
            "Only plan mesh density varies; this does not establish general convergence or verify all harmonic response routes."
        ],
    }
    summary_path = ASSET_ROOT / "mesh_comparison_summary.json"
    summary["resources_observed"] = {
        "elapsed_seconds": time.perf_counter() - started,
        "peak_rss_bytes_sampled": peak_rss[0],
        "sampling_interval_seconds": 0.1,
        "rss_limit_semantics": "sampled soft monitor; not an OS memory quota",
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    stop_monitor.set()
    monitor.join(timeout=2.0)
    summary["resources_observed"]["elapsed_seconds"] = time.perf_counter() - started
    summary["resources_observed"]["peak_rss_bytes_sampled"] = peak_rss[0]
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts = []
    for path in sorted(ASSET_ROOT.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            artifacts.append({"path": path.relative_to(ASSET_ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": _sha256(path)})
    manifest = {"schema": "qfsolver-j16-site-assets-manifest-v1", "artifact_count": len(artifacts), "artifacts": artifacts}
    (ASSET_ROOT / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    result = assemble_site_assets()
    print(json.dumps({
        "contract_id": result["contract_id"],
        "mesh_sizes": list(result["mesh_summaries"]),
        "frequency_rows": result["frequency_row_count"],
        "assets": "research/j16/site_assets/nafems13h_mesh_study_003",
    }, indent=2))
