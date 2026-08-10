"""Execute and normalize the Code_Aster DKQ correlation for NAFEMS 13H."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from solveur.verification.code_aster_nafems import (
    CodeAsterNafems13HParser,
    complex_polar,
    relative_difference,
)

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "qualification" / "vnv" / "external" / "code_aster_nafems13h"
QF_SUMMARY = ROOT / "results" / "VNV-MITC4-HARMONIC-NAFEMS13H-004" / "summary.json"
CALCULIX_SUMMARY = ROOT / "results" / "VNV-MITC4-HARMONIC-CALCULIX13H-S8R-006" / "summary.json"
IMAGE = "simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-run", action="store_true", help="Normalize an existing raw result.")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    frequencies = np.linspace(0.1, 4.16, 200)
    _write_inputs(output, frequencies)
    if not args.skip_run:
        _run_code_aster(output)
    summary = _normalize(output)
    print(f"Code_Aster NAFEMS 13H DKQ: {summary['verdict']}")
    return 0 if summary["verdict"] in {"PASS", "WARNING"} else 1


def _write_inputs(output: Path, frequencies: np.ndarray) -> None:
    (output / "nafems13h_code_aster.mail").write_text(_mesh_text(), encoding="ascii")
    template = (EXTERNAL / "nafems13h_code_aster.comm.template").read_text(encoding="utf-8")
    freq_text = ",\n    ".join(f"{value:.12g}" for value in frequencies)
    (output / "nafems13h_code_aster.comm").write_text(
        template.replace("__FREQUENCIES__", freq_text), encoding="utf-8"
    )
    (output / "nafems13h_code_aster.export").write_text(
        "\n".join(
            [
                "P time_limit 900",
                "P memory_limit 4096",
                "P ncpus 1",
                "P mpi_nbcpu 1",
                "P mpi_nbnoeud 1",
                "F comm /work/nafems13h_code_aster.comm D 1",
                "F mail /work/nafems13h_code_aster.mail D 20",
                "",
            ]
        ),
        encoding="ascii",
    )


def _mesh_text() -> str:
    lines = ["TITRE", "NAFEMS 13H - QF_solver external Code_Aster correlation", "FINSF", "COOR_3D"]
    for j in range(9):
        for i in range(9):
            node = j * 9 + i + 1
            lines.append(f"N{node} {1.25 * i:.12g} {1.25 * j:.12g} 0.0")
    lines.extend(["FINSF", "QUAD4"])
    for j in range(8):
        for i in range(8):
            element = j * 8 + i + 1
            n1 = j * 9 + i + 1
            lines.append(f"M{element} N{n1} N{n1 + 1} N{n1 + 10} N{n1 + 9}")
    lines.extend(["FINSF", "GROUP_MA", "PLATE"])
    lines.extend(f"M{i}" for i in range(1, 65))
    groups = {
        "NALL": list(range(1, 82)),
        "EDGE": sorted(set(range(1, 10)) | set(range(73, 82)) | set(range(1, 82, 9)) | set(range(9, 82, 9))),
        "BOT": list(range(1, 10)),
        "TOP": list(range(73, 82)),
        "LEFT": list(range(1, 82, 9)),
        "RIGHT": list(range(9, 82, 9)),
        "NMID": [41],
        "CENTER": [31, 32, 33, 40, 41, 42, 49, 50, 51],
    }
    lines.extend(["FINSF", "FINSF"])
    for name, nodes in groups.items():
        lines.extend(["GROUP_NO", name, *(f"N{node}" for node in nodes), "FINSF"])
    lines.append("FIN")
    return "\n".join(lines) + "\n"


def _run_code_aster(output: Path) -> None:
    mount = f"{output}:/work"
    profile = (
        "/opt/spack/opt/spack/linux-zen/code-aster-18.1.0-"
        "owafurl325k3dbxls3s645zyfmvakxsg"
    )
    serial_command = (
        f"export RUNASTER_ROOT={profile}; source {profile}/share/aster/profile.sh; "
        "export PYTHONPATH=$(find /opt/spack/opt/spack/linux-zen -type d "
        "-path '*/lib/python3.11/site-packages' | paste -sd: -):${PYTHONPATH:-}; "
        "export LD_LIBRARY_PATH=$(find /opt/spack/opt/spack/linux-zen -type d "
        "\\( -name lib -o -name lib64 \\) | paste -sd: -):${LD_LIBRARY_PATH:-}; "
        "python3 /work/nafems13h_code_aster.comm --last "
        "--link=F::mail::/work/nafems13h_code_aster.mail::D::20 "
        "--memory 4096 --tpmax 900 --numthreads 1"
    )
    command = [
        "docker", "run", "--rm", "-v", mount, "--workdir", "/work",
        "--entrypoint", "/bin/bash", IMAGE, "-c", serial_command,
    ]
    completed = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=1200,
        check=False,
    )
    (output / "code_aster_stdout.log").write_text(completed.stdout, encoding="utf-8")
    (output / "code_aster_stderr.log").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        tail = "\n".join((completed.stdout + completed.stderr).splitlines()[-30:])
        raise RuntimeError(f"Code_Aster failed with exit code {completed.returncode}:\n{tail}")
    if not (output / "code_aster_raw.json").is_file():
        raise RuntimeError("Code_Aster completed without code_aster_raw.json")
    for pattern in ("fort.*", "glob.*", "vola.*"):
        for transient in output.glob(pattern):
            transient.unlink(missing_ok=True)


def _normalize(output: Path) -> dict[str, Any]:
    points = CodeAsterNafems13HParser().parse(output / "code_aster_raw.json")
    peak = max(points, key=lambda point: abs(point.uz_m))
    qf = json.loads(QF_SUMMARY.read_text(encoding="utf-8"))
    qf_peak = _qf_peak(qf)
    references = {
        "QF_solver MITC4": qf_peak,
        "Navier": {"frequency_hz": 2.37672, "uz_mm": 45.4125, "s11_mpa": 32.0127},
        "NAFEMS": {"frequency_hz": 2.377, "uz_mm": 45.39, "s11_mpa": 30.03},
        "Abaqus S4": {"frequency_hz": 2.41999, "uz_mm": 44.93, "s11_mpa": 31.26},
        "Abaqus S4R": {"frequency_hz": 2.405, "uz_mm": 45.43, "s11_mpa": 30.37},
    }
    if CALCULIX_SUMMARY.is_file():
        calc = json.loads(CALCULIX_SUMMARY.read_text(encoding="utf-8"))
        references["CalculiX S8R"] = {
            "frequency_hz": calc["peak"]["frequency_hz"],
            "uz_mm": calc["peak"]["center_uz_amplitude_mm"],
            "s11_mpa": calc["peak"]["center_top_s11_amplitude_mpa"],
        }
    current = {
        "frequency_hz": peak.frequency_hz,
        "uz_mm": 1000.0 * abs(peak.uz_m),
        "s11_mpa": 1.0e-6 * abs(peak.s11_top_pa),
    }
    differences = {
        name: {key: relative_difference(current[key], value[key]) for key in current}
        for name, value in references.items()
    }
    qf_diff = differences["QF_solver MITC4"]
    verdict = "PASS" if max(qf_diff.values()) <= 5.0 else "WARNING"
    summary = {
        "study_id": "VNV-MITC4-HARMONIC-CODEASTER13H-DKQ-007",
        "verdict": verdict,
        "solver": {"name": "Code_Aster", "version": "18.1.0", "formulation": "DKT/DKQ"},
        "container": {"image": IMAGE, "runtime": "Docker Desktop"},
        "mesh": {"elements": 64, "nodes": 81, "pattern": "8x8 QUAD4", "element_size_m": 1.25},
        "peak": {
            "frequency_hz": peak.frequency_hz,
            "uz_mm": complex_polar(1000.0 * peak.uz_m),
            "s11_top_mpa": complex_polar(1.0e-6 * peak.s11_top_pa),
        },
        "references": references,
        "relative_differences_percent": differences,
        "criteria": {"maximum_qf_difference_percent": 5.0, "status": verdict},
        "stress_reconstruction": {
            "source": "Code_Aster complex nodal DRX/DRY",
            "method": "bilinear center curvature, four central elements averaged, z=+t/2",
            "equation": "S11=E*t/(2*(1-nu^2))*(kappa_x+nu*kappa_y)",
            "qualification_note": "independent transparent post-processing; not Code_Aster native shell stress output",
        },
        "frequency_points": [
            {
                "frequency_hz": point.frequency_hz,
                "uz_mm": complex_polar(1000.0 * point.uz_m),
                "s11_top_mpa": complex_polar(1.0e-6 * point.s11_top_pa),
            }
            for point in points
        ],
        "inputs_sha256": {path.name: _sha256(path) for path in sorted(output.glob("nafems13h_code_aster.*"))},
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    _plot(output, points, references, peak)
    (output / "STUDY.md").write_text(_markdown(summary), encoding="utf-8")
    return summary


def _qf_peak(payload: dict[str, Any]) -> dict[str, float]:
    peak = payload["peak_response"] if "peak_response" in payload else payload["peak"]
    if "peak_frequency_hz" in peak:
        return {
            "frequency_hz": float(peak["peak_frequency_hz"]),
            "uz_mm": float(peak["peak_displacement_mm"]),
            "s11_mpa": float(peak["peak_stress_n_mm2"]),
        }

    def amplitude(value: Any) -> float:
        return float(value["amplitude"] if isinstance(value, dict) else value)
    return {
        "frequency_hz": float(peak["frequency_hz"]),
        "uz_mm": amplitude(peak.get("center_uz_mm", peak.get("uz_mm"))),
        "s11_mpa": amplitude(peak.get("center_s11_top_mpa", peak.get("s11_top_mpa"))),
    }


def _plot(output: Path, points: list[Any], references: dict[str, dict[str, float]], peak: Any) -> None:
    freq = np.asarray([point.frequency_hz for point in points])
    uz = np.asarray([1000.0 * abs(point.uz_m) for point in points])
    stress = np.asarray([1.0e-6 * abs(point.s11_top_pa) for point in points])
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4))
    axes[0].plot(freq, uz, color="#0b7285", linewidth=2, label="Code_Aster DKQ")
    axes[1].plot(freq, stress, color="#b02a37", linewidth=2, label="Code_Aster DKQ")
    for name, value in references.items():
        axes[0].scatter(value["frequency_hz"], value["uz_mm"], s=28, label=name)
        axes[1].scatter(value["frequency_hz"], value["s11_mpa"], s=28, label=name)
    axes[0].set(title="Déplacement complexe au centre", xlabel="Fréquence [Hz]", ylabel="|UZ| [mm]")
    axes[1].set(title="Contrainte face supérieure au centre", xlabel="Fréquence [Hz]", ylabel="|S11| [MPa]")
    for axis in axes:
        axis.grid(True, alpha=0.3)
        axis.legend(fontsize=7)
    fig.suptitle(f"NAFEMS 13H - Code_Aster DKQ - pic {peak.frequency_hz:.6f} Hz")
    fig.tight_layout()
    fig.savefig(output / "code-aster-comparison.png", dpi=180)
    plt.close(fig)


def _markdown(summary: dict[str, Any]) -> str:
    peak = summary["peak"]
    rows = []
    for name, values in summary["references"].items():
        diff = summary["relative_differences_percent"][name]
        rows.append(
            f"| {name} | {values['frequency_hz']:.6f} | {values['uz_mm']:.6f} | {values['s11_mpa']:.6f} | "
            f"{diff['frequency_hz']:.3f} | {diff['uz_mm']:.3f} | {diff['s11_mpa']:.3f} |"
        )
    return "\n".join(
        [
            "# Corrélation Code_Aster - NAFEMS 13H",
            "",
            f"Verdict: **{summary['verdict']}**.",
            "",
            "Code_Aster 18.1.0 est exécuté dans le conteneur épinglé indiqué dans `summary.json`.",
            "Le modèle `DKT` appliqué aux QUAD4 utilise la formulation quadrilatérale DKQ.",
            "",
            "## Pic Code_Aster",
            "",
            f"- fréquence: `{peak['frequency_hz']:.9f} Hz`;",
            f"- `|UZ|`: `{peak['uz_mm']['amplitude']:.9f} mm`, phase `{peak['uz_mm']['phase_deg']:.3f} deg`;",
            f"- `|S11|` face supérieure: `{peak['s11_top_mpa']['amplitude']:.9f} MPa`, phase `{peak['s11_top_mpa']['phase_deg']:.3f} deg`.",
            "",
            "## Écarts",
            "",
            "| Référence | f [Hz] | UZ [mm] | S11 [MPa] | écart f [%] | écart UZ [%] | écart S11 [%] |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            *rows,
            "",
            "![Comparaison Code_Aster](code-aster-comparison.png)",
            "",
            "## Convention de contrainte",
            "",
            "La contrainte est reconstruite indépendamment à partir des rotations complexes nodales Code_Aster:",
            "`S11 = E t / (2 (1-nu^2)) (kappa_x + nu kappa_y)`.",
            "Les courbures bilinéaires sont évaluées au centre des quatre éléments centraux puis moyennées.",
            "Cette méthode est transparente et testable, mais elle ne remplace pas encore une extraction native Code_Aster.",
            "",
            "## Conclusion bornée",
            "",
            "Cette étude compare un MITC4 Reissner-Mindlin à un DKQ Kirchhoff sur une plaque mince.",
            "Un accord inférieur à 5 % confirme la compétitivité numérique sur ce benchmark précis; il ne prouve pas une équivalence générale des solveurs.",
            "",
        ]
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
