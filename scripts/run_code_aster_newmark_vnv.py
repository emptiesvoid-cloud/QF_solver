"""Run same-mesh Code_Aster DKQ correlation for the MITC4 Newmark chirp."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from run_code_aster_nafems13h_vnv import IMAGE, _mesh_text
from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.verification.code_aster_nafems import CodeAsterNafems13HParser


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "qualification" / "vnv" / "external" / "code_aster_newmark"
QF_SUMMARY = ROOT / "results" / "VNV-MITC4-NEWMARK-BROADBAND-004" / "summary.json"
STUDY_ID = "VNV-MITC4-NEWMARK-CODEASTER-DKQ-005"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-run", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    qf = json.loads(QF_SUMMARY.read_text(encoding="utf-8"))
    point = qf["cases"]["chirp"][-1]
    _write_inputs(output, qf, point)
    if not args.skip_run:
        _run(output)
    summary = _normalize(output, qf, point)
    print(f"{STUDY_ID}: {summary['status']}")
    return 0 if summary["status"] in {"PASS_EXTERNAL_CORRELATION", "WARNING"} else 1


def _write_inputs(output: Path, qf: dict[str, Any], point: dict[str, Any]) -> None:
    times = np.concatenate(([0.0], np.asarray(point["times_s"], dtype=float)))
    factors = np.concatenate(([0.0], np.asarray(point["load_factors"], dtype=float)))
    template = (EXTERNAL / "nafems13h_newmark.comm.template").read_text(encoding="utf-8")
    time_text = ",\n    ".join(f"{value:.16g}" for value in times)
    function_text = ",\n    ".join(
        f"{time:.16g}, {factor:.16g}" for time, factor in zip(times, factors, strict=True)
    )
    alpha = qf["model"]["rayleigh_alpha_s_inv"]
    comm = template.replace("__TIMES__", time_text)
    comm = comm.replace("__FUNCTION_VALUES__", function_text)
    comm = comm.replace("__ALPHA__", f"{alpha:.16g}")
    (output / "nafems13h_newmark.mail").write_text(_mesh_text(), encoding="ascii")
    (output / "nafems13h_newmark.comm").write_text(comm, encoding="utf-8")
    (output / "nafems13h_newmark.export").write_text(
        "\n".join(
            [
                "P time_limit 900", "P memory_limit 4096", "P ncpus 1", "P mpi_nbcpu 1",
                "F comm /work/nafems13h_newmark.comm D 1",
                "F mail /work/nafems13h_newmark.mail D 20", "",
            ]
        ),
        encoding="ascii",
    )


def _run(output: Path) -> None:
    profile = (
        "/opt/spack/opt/spack/linux-zen/code-aster-18.1.0-"
        "owafurl325k3dbxls3s645zyfmvakxsg"
    )
    serial = (
        f"export RUNASTER_ROOT={profile}; source {profile}/share/aster/profile.sh; "
        "export PYTHONPATH=$(find /opt/spack/opt/spack/linux-zen -type d "
        "-path '*/lib/python3.11/site-packages' | paste -sd: -):${PYTHONPATH:-}; "
        "export LD_LIBRARY_PATH=$(find /opt/spack/opt/spack/linux-zen -type d "
        "\\( -name lib -o -name lib64 \\) | paste -sd: -):${LD_LIBRARY_PATH:-}; "
        "python3 /work/nafems13h_newmark.comm --last "
        "--link=F::mail::/work/nafems13h_newmark.mail::D::20 "
        "--memory 4096 --tpmax 900 --numthreads 1"
    )
    command = [
        "docker", "run", "--rm", "-v", f"{output}:/work", "--workdir", "/work",
        "--entrypoint", "/bin/bash", IMAGE, "-c", serial,
    ]
    completed = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=1200, check=False,
    )
    (output / "code_aster_stdout.log").write_text(completed.stdout, encoding="utf-8")
    (output / "code_aster_stderr.log").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        tail = "\n".join((completed.stdout + completed.stderr).splitlines()[-40:])
        raise RuntimeError(f"Code_Aster failed with exit code {completed.returncode}:\n{tail}")
    if not (output / "code_aster_transient_raw.json").is_file():
        raise RuntimeError("Code_Aster completed without code_aster_transient_raw.json")
    for pattern in ("fort.*", "glob.*", "vola.*"):
        for transient in output.glob(pattern):
            transient.unlink(missing_ok=True)


def _normalize(
    output: Path, qf: dict[str, Any], point: dict[str, Any]
) -> dict[str, Any]:
    raw = CodeAsterNafems13HParser().parse_transient(output / "code_aster_transient_raw.json")
    raw_times = np.asarray([item.time_s for item in raw], dtype=float)
    times = np.asarray(point["times_s"], dtype=float)
    aster_u = np.interp(times, raw_times, [item.uz_m for item in raw])
    aster_s_raw = np.interp(times, raw_times, [item.s11_top_pa for item in raw])
    qf_u = np.asarray(point["qf_displacement_m"], dtype=float)
    qf_s = np.asarray(point["qf_top_s11_pa"], dtype=float)
    stress_factor = 1.0 if float(np.dot(qf_s, aster_s_raw)) >= 0.0 else -1.0
    aster_s = stress_factor * aster_s_raw
    metrics = {
        "displacement_normalized_rms_difference": _normalized_rms(qf_u, aster_u),
        "stress_normalized_rms_difference": _normalized_rms(qf_s, aster_s),
        "displacement_peak_difference": _peak_difference(qf_u, aster_u),
        "stress_peak_difference": _peak_difference(qf_s, aster_s),
        "displacement_correlation": _correlation(qf_u, aster_u),
        "stress_correlation": _correlation(qf_s, aster_s),
    }
    checks = {
        "displacement_peak": metrics["displacement_peak_difference"] <= 0.10,
        "stress_peak": metrics["stress_peak_difference"] <= 0.15,
        "displacement_correlation": metrics["displacement_correlation"] >= 0.90,
        "stress_correlation": metrics["stress_correlation"] >= 0.85,
    }
    verdict = "PASS" if all(checks.values()) else "WARNING"
    summary = {
        "study_id": STUDY_ID,
        "status": "PASS_EXTERNAL_CORRELATION" if verdict == "PASS" else "WARNING",
        "verdict": verdict,
        "maturity": "verified_development_external_correlation",
        "solver": {"name": "Code_Aster", "version": "18.1.0", "formulation": "DKT/DKQ"},
        "container": {"image": IMAGE},
        "comparison": "same 8x8 mesh, constraints, nodal chirp, time grid and Rayleigh alpha",
        "qf_study": qf["study_id"],
        "time_step_s": point["time_step_s"],
        "step_count": point["step_count"],
        "metrics": metrics,
        "checks": checks,
        "stress_orientation_factor": stress_factor,
        "criteria": {
            "peak_displacement_max": 0.10, "peak_stress_max": 0.15,
            "displacement_correlation_min": 0.90, "stress_correlation_min": 0.85,
        },
        "limitations": [
            "MITC4 Reissner-Mindlin and Code_Aster DKQ Kirchhoff are different spatial formulations.",
            "The stress sign is aligned explicitly because local shell face conventions differ.",
            "The exact modal oracle, not Code_Aster, is the acceptance reference for temporal accuracy.",
        ],
        "history": [
            {
                "time_s": float(time), "qf_uz_m": float(uq), "code_aster_uz_m": float(ua),
                "qf_top_s11_pa": float(sq), "code_aster_top_s11_pa": float(sa),
            }
            for time, uq, ua, sq, sa in zip(times, qf_u, aster_u, qf_s, aster_s, strict=True)
        ],
        "inputs_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(output.glob("nafems13h_newmark.*"))
        },
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    _plot(output, times, qf_u, aster_u, qf_s, aster_s)
    (output / "STUDY.md").write_text(_markdown(summary), encoding="utf-8")
    write_json_file(
        output / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "source": git_source_state(ROOT),
            "files": discovered_file_entries(
                output,
                lambda _: "code_aster_newmark_vnv",
                exclude_names=("vnv_manifest.json",),
            ),
        },
    )
    return summary


def _normalized_rms(first: np.ndarray, second: np.ndarray) -> float:
    return float(np.sqrt(np.mean((first - second) ** 2)) / max(np.max(np.abs(first)), 1.0e-30))


def _peak_difference(first: np.ndarray, second: np.ndarray) -> float:
    reference = max(float(np.max(np.abs(first))), 1.0e-30)
    return abs(float(np.max(np.abs(second))) - reference) / reference


def _correlation(first: np.ndarray, second: np.ndarray) -> float:
    return float(np.corrcoef(first, second)[0, 1])


def _plot(
    output: Path, times: np.ndarray, qf_u: np.ndarray, aster_u: np.ndarray,
    qf_s: np.ndarray, aster_s: np.ndarray,
) -> None:
    figure, axes = plt.subplots(2, 1, figsize=(9.0, 7.0), sharex=True)
    axes[0].plot(times, 1000.0 * qf_u, label="QF_solver MITC4")
    axes[0].plot(times, 1000.0 * aster_u, "--", label="Code_Aster DKQ")
    axes[0].set_ylabel("UZ [mm]")
    axes[1].plot(times, 1.0e-6 * qf_s, label="QF_solver MITC4")
    axes[1].plot(times, 1.0e-6 * aster_s, "--", label="Code_Aster DKQ")
    axes[1].set(xlabel="temps [s]", ylabel="S11 face superieure [MPa]")
    for axis in axes:
        axis.grid(True, alpha=0.25)
        axis.legend()
    figure.suptitle("Newmark sous chirp - meme maillage 8x8")
    figure.tight_layout()
    figure.savefig(output / "code-aster-newmark-comparison.png", dpi=180)
    plt.close(figure)


def _markdown(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    checks = summary["checks"]
    rows = [
        ("RMS UZ", metrics["displacement_normalized_rms_difference"], "informatif", True),
        ("RMS S11", metrics["stress_normalized_rms_difference"], "informatif", True),
        ("Pic UZ", metrics["displacement_peak_difference"], "10 %", checks["displacement_peak"]),
        ("Pic S11", metrics["stress_peak_difference"], "15 %", checks["stress_peak"]),
    ]
    table = [
        f"| {name} | {100*value:.3f} % | {limit} | {'PASS' if check else 'WARNING'} |"
        for name, value, limit, check in rows
    ]
    return "\n".join(
        [
            f"# {STUDY_ID}", "", f"Verdict : **{summary['verdict']}**.", "",
            "Correlation transitoire sur le meme maillage, les memes blocages, le meme chirp et le meme pas.", "",
            "| Mesure | Ecart | Limite | Verdict |", "| --- | ---: | ---: | --- |", *table, "",
            f"Correlation UZ : `{metrics['displacement_correlation']:.6f}`.",
            f"Correlation S11 : `{metrics['stress_correlation']:.6f}`.", "",
            "![Comparaison](code-aster-newmark-comparison.png)", "",
            "Le signe S11 Code_Aster est aligne explicitement avec la face locale MITC4; le facteur est",
            f"`{summary['stress_orientation_factor']:+.0f}`. Les ecarts RMS restent informatifs car la",
            "difference de formulation spatiale produit une derive de phase sur plusieurs periodes.", "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
