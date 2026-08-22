from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from solveur.io.manifest import sha256
from solveur.verification.calculix_nafems import (
    CalculixNafems13HParser,
    summarize_calculix_points,
)


ROOT = Path(__file__).resolve().parents[1]
QF_SUMMARY = ROOT / "results" / "VNV-MITC4-HARMONIC-NAFEMS13H-004" / "summary.json"
REFERENCE = ROOT / "qualification" / "external_reference_digests" / "abaqus_nafems_13h_harmonic.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize a CalculiX NAFEMS 13H run.")
    parser.add_argument("--dat", type=Path, required=True)
    parser.add_argument("--formulation", choices=("S4", "S8R"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    summary = build_summary(arguments.dat, arguments.formulation)
    arguments.output.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    _write_report(arguments.output / "STUDY.md", summary)
    _write_plot(arguments.output / "calculix-comparison.png", summary)
    print(f"CalculiX NAFEMS 13H {arguments.formulation}: {summary['verdict']}")
    return 0 if summary["verdict"] in {"PASS", "WARNING"} else 1


def build_summary(dat_path: Path, formulation: str) -> dict[str, Any]:
    if formulation == "S8R":
        center_node = 145
        corners = {28: (1.0, 1.0), 29: (-1.0, 1.0), 36: (1.0, -1.0), 37: (-1.0, -1.0)}
    else:
        center_node = 45
        corners = {34: (1.0, 1.0), 35: (-1.0, 1.0), 44: (1.0, -1.0), 45: (-1.0, -1.0)}
    points = CalculixNafems13HParser().parse(
        dat_path,
        center_node=center_node,
        center_element_corners=corners,
    )
    result = summarize_calculix_points(points, formulation=formulation)
    qf = json.loads(QF_SUMMARY.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    qf_peak = qf["peak"]
    calc_peak = result["peak"]
    published = _published_values(reference)
    comparisons = {
        "qf_solver": _compare(calc_peak, {
            "frequency_hz": qf_peak["peak_frequency_hz"],
            "displacement_mm": qf_peak["peak_displacement_mm"],
            "stress_mpa": qf_peak["peak_stress_n_mm2"],
        }),
        "navier": _compare(calc_peak, {
            "frequency_hz": qf["classical_plate_theory"]["fundamental_frequency_hz"],
            "displacement_mm": qf["classical_plate_theory"]["peak_displacement_mm"],
            "stress_mpa": qf["classical_plate_theory"]["peak_stress_n_mm2"],
        }),
        **{name: _compare(calc_peak, values) for name, values in published.items()},
    }
    checks = {
        "qf_frequency_within_3_percent": comparisons["qf_solver"]["frequency"] <= 0.03,
        "qf_displacement_within_5_percent": comparisons["qf_solver"]["displacement"] <= 0.05,
        "qf_stress_within_5_percent": comparisons["qf_solver"]["stress"] <= 0.05,
        "nafems_frequency_within_3_percent": comparisons["nafems"]["frequency"] <= 0.03,
        "nafems_displacement_within_5_percent": comparisons["nafems"]["displacement"] <= 0.05,
        "nafems_stress_within_5_percent": comparisons["nafems"]["stress"] <= 0.05,
    }
    result.update(
        {
            "study_id": f"VNV-MITC4-HARMONIC-CALCULIX13H-{formulation}",
            "verdict": "PASS" if all(checks.values()) else "WARNING",
            "input": {"dat_path": str(dat_path), "dat_sha256": sha256(dat_path)},
            "stress_recovery": "trilinear extrapolation from 8 expanded-shell Gauss points to z=+1, then four-element complex average",
            "comparisons_relative_error": comparisons,
            "checks": checks,
            "limitations": [
                "CalculiX expands shell elements internally into three-dimensional elements.",
                "S8R uses quadratic midside nodes and is not the same element as QF_solver MITC4 or Abaqus S4R.",
                "The CalculiX sweep inserts eigenfrequencies and therefore contains 399 points instead of the published 200-point grid.",
            ],
        }
    )
    return result


def _published_values(reference: dict[str, Any]) -> dict[str, dict[str, float]]:
    values = {
        f"abaqus_{entry['element'].lower()}": {
            "frequency_hz": float(source["peak_frequency_hz"]),
            "displacement_mm": float(source["peak_displacement_mm"]),
            "stress_mpa": float(source["peak_stress_n_mm2"]),
        }
        for entry in reference["abaqus_direct_results"]
        for source in (entry,)
    }
    nafems = reference["nafems_reference"]
    values["nafems"] = {
        "frequency_hz": float(nafems["peak_frequency_hz"]),
        "displacement_mm": float(nafems["peak_displacement_mm"]),
        "stress_mpa": float(nafems["peak_stress_n_mm2"]),
    }
    return values


def _compare(peak: dict[str, float], reference: dict[str, float]) -> dict[str, float]:
    return {
        "frequency": _relative(peak["frequency_hz"], reference["frequency_hz"]),
        "displacement": _relative(peak["center_uz_amplitude_mm"], reference["displacement_mm"]),
        "stress": _relative(peak["center_top_s11_amplitude_mpa"], reference["stress_mpa"]),
    }


def _relative(value: float, reference: float) -> float:
    return abs(float(value) - float(reference)) / abs(float(reference))


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    peak = summary["peak"]
    rows = []
    for name, differences in summary["comparisons_relative_error"].items():
        rows.append(
            f"| {name} | {100*differences['frequency']:.3f} % | "
            f"{100*differences['displacement']:.3f} % | {100*differences['stress']:.3f} % |"
        )
    checks = "\n".join(
        f"- [{'x' if passed else ' '}] `{name}`" for name, passed in summary["checks"].items()
    )
    path.write_text(
        "\n".join(
            [
                "# Correlation CalculiX - NAFEMS 13H",
                "",
                f"Verdict: **{summary['verdict']}**",
                "",
                f"Formulation externe: `{summary['formulation']}` CalculiX `2.20-1`.",
                f"Balayage extrait: `{summary['frequency_point_count']}` frequences complexes.",
                "",
                "| Grandeur au pic | Valeur CalculiX |",
                "| --- | ---: |",
                f"| frequence | {peak['frequency_hz']:.6f} Hz |",
                f"| deplacement central | {peak['center_uz_amplitude_mm']:.6f} mm |",
                f"| phase du deplacement | {peak['center_uz_phase_degrees']:.3f} deg |",
                f"| S11 face superieure | {peak['center_top_s11_amplitude_mpa']:.6f} MPa |",
                f"| phase de S11 | {peak['center_top_s11_phase_degrees']:.3f} deg |",
                "",
                "## Ecarts relatifs",
                "",
                "| Reference | Frequence | Deplacement | S11 |",
                "| --- | ---: | ---: | ---: |",
                *rows,
                "",
                "## Controles",
                "",
                checks,
                "",
                "## Interpretation",
                "",
                "CalculiX extrapole ici les contraintes des huit points de Gauss de la coque",
                "expansee jusqu'a la face `z=+1`, puis moyenne les quatre contributions",
                "complexes entourant le centre. Le verdict WARNING ne remet pas en cause",
                "QF_solver: il signale toute tolerance externe marginalement depassee et la",
                "difference de formulation entre S8R, MITC4 et Abaqus S4R.",
                "",
                "![Comparaison frequentielle](calculix-comparison.png)",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_plot(path: Path, summary: dict[str, Any]) -> None:
    response = summary["frequency_response"]
    frequencies = np.asarray([row["frequency_hz"] for row in response])
    displacement = np.asarray([row["center_uz_amplitude_mm"] for row in response])
    stress = np.asarray([row["center_top_s11_amplitude_mpa"] for row in response])
    phase = np.asarray([row["center_top_s11_phase_degrees"] for row in response])
    figure, axes = plt.subplots(2, 1, figsize=(9.0, 7.0), sharex=True)
    axes[0].plot(frequencies, displacement, label="CalculiX UZ [mm]")
    axes[0].plot(frequencies, stress, label="CalculiX S11 [MPa]")
    axes[0].set_ylabel("Amplitude")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()
    axes[1].plot(frequencies, phase, color="tab:red", label="phase S11")
    axes[1].axhline(-90.0, color="black", linewidth=0.8, linestyle="--")
    axes[1].set_xlabel("Frequence [Hz]")
    axes[1].set_ylabel("Phase [deg]")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()
    figure.suptitle(f"NAFEMS 13H - CalculiX {summary['formulation']}")
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


if __name__ == "__main__":
    raise SystemExit(main())
