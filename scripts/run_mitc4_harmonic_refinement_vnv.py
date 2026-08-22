"""Run a reproducible MITC4 harmonic mesh-refinement campaign."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.verification.mitc4_harmonic_nafems import Mitc4Nafems13HStudy


ROOT = Path(__file__).resolve().parents[1]
STUDY_ID = "VNV-MITC4-HARMONIC-REFINEMENT-005"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mesh-sizes", nargs="+", type=int, default=[8, 12, 16])
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for mesh_size in args.mesh_sizes:
        summary = Mitc4Nafems13HStudy(mesh_size=mesh_size).run()
        rows.append(_row(summary))
    result = {
        "study_id": STUDY_ID,
        "status": "PASS_TECHNICAL_VERIFICATION" if all(row["max_primary_error"] <= 0.01 for row in rows) else "WARNING",
        "reference": "Kirchhoff-Love Navier theory and published NAFEMS 13H scalar values",
        "mesh_sizes": list(args.mesh_sizes),
        "rows": rows,
        "acceptance": {
            "primary_error_max": 0.01,
            "primary_observables": ["peak_displacement", "peak_frequency", "peak_stress_outside_singularity"],
        },
        "limitations": [
            "The comparison uses a flat, isotropic, simply supported square plate.",
            "The center stress is a face stress away from the point load and is not a singularity observable.",
            "This is a refinement/theory campaign; it does not replace an external same-mesh Code_Aster run.",
        ],
    }
    write_json_file(output / "summary.json", result)
    _write_report(output / f"{STUDY_ID}.md", result)
    _plot(output / f"{STUDY_ID}-convergence.png", result)
    write_json_file(
        output / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "source": git_source_state(ROOT),
            "files": discovered_file_entries(output, lambda _: "mitc4_harmonic_refinement", exclude_names=("vnv_manifest.json",)),
        },
    )
    print(f"{STUDY_ID}: {result['status']}")
    for row in rows:
        print(f"mesh={row['mesh_size']} max_primary_error={row['max_primary_error']:.6%}")
    return 0 if result["status"] == "PASS_TECHNICAL_VERIFICATION" else 1


def _row(summary: dict[str, Any]) -> dict[str, Any]:
    theory = summary["classical_plate_theory"]["qf_relative_differences"]
    return {
        "mesh_size": summary["model"]["mesh"][0],
        "element_count": summary["model"]["element_count"],
        "peak_displacement_error": float(theory["displacement"]),
        "peak_frequency_error": float(theory["frequency"]),
        "peak_stress_error": float(theory["stress"]),
        "max_primary_error": max(float(value) for value in theory.values()),
        "peak": summary["peak"],
        "residual": summary["peak"]["max_relative_residual"],
    }


def _write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        f"# {STUDY_ID}",
        "",
        "Cette campagne vérifie le raffinement harmonique MITC4 sur une plaque carrée isotrope.",
        "La règle de fermeture impose une erreur primaire finale inférieure ou égale à 1 %.",
        "",
        "| Maillage | Éléments | Erreur déplacement | Erreur fréquence | Erreur contrainte | Maximum |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["rows"]:
        lines.append(
            f"| {row['mesh_size']}x{row['mesh_size']} | {row['element_count']} | "
            f"{row['peak_displacement_error'] * 100:.6f} % | {row['peak_frequency_error'] * 100:.6f} % | "
            f"{row['peak_stress_error'] * 100:.6f} % | {row['max_primary_error'] * 100:.6f} % |"
        )
    lines.extend(["", f"Statut technique : `{result['status']}`.", "", "## Limites", "", *[f"- {item}" for item in result["limitations"]], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _plot(path: Path, result: dict[str, Any]) -> None:
    rows = result["rows"]
    x = np.asarray([row["element_count"] for row in rows], dtype=float)
    figure, axis = plt.subplots(figsize=(8.0, 4.8))
    for key, label, color in (
        ("peak_displacement_error", "déplacement", "#0072B2"),
        ("peak_frequency_error", "fréquence", "#D55E00"),
        ("peak_stress_error", "contrainte", "#009E73"),
    ):
        axis.loglog(x, [row[key] * 100 for row in rows], "o-", label=label, color=color)
    axis.axhline(1.0, color="#CC3311", linestyle="--", label="limite 1 %")
    axis.set(xlabel="Nombre d'éléments", ylabel="Erreur relative [%]", title="MITC4 harmonique : convergence primaire")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


if __name__ == "__main__":
    raise SystemExit(main())
