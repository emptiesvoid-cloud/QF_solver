"""Compare two refined TET10 J2 complex-geometry Code_Aster studies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from solveur.io.manifest import sha256, write_json_file


STUDY_ID = "VNV-TET10-J2-CODEASTER-COMPLEX-REFINEMENT-027"


def compare_refinement(
    coarse_dir: str | Path,
    fine_dir: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Build a machine-readable and graphical two-level refinement report."""
    coarse = _load_case(Path(coarse_dir))
    fine = _load_case(Path(fine_dir))
    rows = [coarse, fine]
    qf_displacements = np.asarray([row["qf_tip_displacement_m"] for row in rows])
    qf_peeq = np.asarray([row["qf_peeq_mean"] for row in rows])
    convergence = {
        "qf_tip_displacement_relative_increment": _relative_increment(qf_displacements),
        "qf_peeq_relative_increment": _relative_increment(qf_peeq),
    }
    status = "PASS_EXTERNAL_CORRELATION" if all(row["status"] == "PASS_EXTERNAL_CORRELATION" for row in rows) else "WARNING"
    summary: dict[str, Any] = {
        "study_id": STUDY_ID,
        "status": status,
        "maturity": "experimental",
        "reference": "Code_Aster 18.1.0 TETRA10 VMIS_ISOT_LINE on the same generated meshes",
        "cases": rows,
        "convergence": convergence,
        "checks": [
            {"id": "two_mesh_levels", "value": len(rows), "limit": 2, "status": "PASS"},
            {
                "id": "external_correlation_cases",
                "value": sum(row["status"] == "PASS_EXTERNAL_CORRELATION" for row in rows),
                "limit": len(rows),
                "status": "PASS" if status == "PASS_EXTERNAL_CORRELATION" else "WARNING",
            },
            {
                "id": "qf_residual_max",
                "value": max(row["qf_residual"] for row in rows),
                "limit": 1.0e-7,
                "status": "PASS" if max(row["qf_residual"] for row in rows) <= 1.0e-7 else "FAIL",
            },
        ],
        "limitations": [
            "Deux niveaux spatiaux etablissent une tendance de raffinement, mais ne constituent pas une etude de convergence asymptotique.",
            "La pointe rentrante reste exclue de l'acceptation des contraintes ponctuelles.",
            "La comparaison porte sur J2 isotrope en petites deformations avec chargement combine monotone; les cycles et la non-linearite geometrique restent hors de cette etude.",
        ],
    }
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    write_json_file(output / "summary.json", summary)
    (output / "report.md").write_text(_markdown(summary), encoding="utf-8")
    _plot(summary, output / "convergence.png")
    write_json_file(
        output / "source_digests.json",
        {
            "study_id": STUDY_ID,
            "inputs": [
                {"directory": str(Path(coarse_dir)), "summary_sha256": sha256(Path(coarse_dir) / "summary.json")},
                {"directory": str(Path(fine_dir)), "summary_sha256": sha256(Path(fine_dir) / "summary.json")},
            ],
        },
    )
    return summary


def _load_case(directory: Path) -> dict[str, Any]:
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    qf_rows = summary["qf_rows"]
    aster_rows = summary["code_aster_rows"]
    qf_final = next(row for row in qf_rows if np.isclose(row["load_factor"], 1.0))
    final_index = next(index for index, row in enumerate(qf_rows) if np.isclose(row["load_factor"], 1.0))
    aster_final = aster_rows[final_index]
    result = json.loads((directory / "results.json").read_text(encoding="utf-8"))
    steps = result.get("solver", {}).get("steps", [])
    work = steps[-1] if steps else {}
    checks = {item["id"]: item for item in summary["checks"]}
    return {
        "directory": directory.as_posix(),
        "mesh_size": float(summary["model"]["mesh_size"]),
        "nodes": int(summary["model"]["nodes"]),
        "elements": int(summary["model"]["elements"]),
        "status": str(summary["status"]),
        "qf_tip_displacement_m": float(np.hypot(qf_final["tip_ux_m"], qf_final["tip_uy_m"])),
        "code_aster_tip_displacement_m": float(np.hypot(aster_final["tip_ux_m"], aster_final["tip_uy_m"])),
        "qf_peeq_mean": float(qf_final["equivalent_plastic_strain_mean"]),
        "code_aster_peeq_mean": float(aster_final["equivalent_plastic_strain"]),
        "external_displacement_rms": float(checks["combined_tip_displacement_path_rms"]["value"]),
        "external_peeq_rms": float(checks["peeq_path_rms"]["value"]),
        "qf_residual": float(checks["qf_max_step_residual"]["value"]),
        "internal_work_j": float(work.get("incremental_internal_work", 0.0)),
        "external_work_j": float(work.get("incremental_external_work", 0.0)),
    }


def _relative_increment(values: np.ndarray) -> float:
    return float(abs(values[-1] - values[0]) / max(abs(values[-1]), 1.0e-30))


def _plot(summary: dict[str, Any], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cases = summary["cases"]
    elements = [case["elements"] for case in cases]
    figure, axes = plt.subplots(1, 2, figsize=(10, 4.5), constrained_layout=True)
    axes[0].plot(elements, [case["qf_tip_displacement_m"] for case in cases], "o-", color="#0072B2", label="QF_solver")
    axes[0].plot(elements, [case["code_aster_tip_displacement_m"] for case in cases], "s--", color="#D55E00", label="Code_Aster")
    axes[0].set(xlabel="Nombre d'elements TET10", ylabel="||u_tip|| [m]", title="Deplacement combine")
    axes[1].plot(elements, [case["qf_peeq_mean"] for case in cases], "o-", color="#009E73", label="QF_solver")
    axes[1].plot(elements, [case["code_aster_peeq_mean"] for case in cases], "s--", color="#CC79A7", label="Code_Aster")
    axes[1].set(xlabel="Nombre d'elements TET10", ylabel="PEEQ moyenne [-]", title="Plasticite cumulee")
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8)
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut automatise : **{summary['status']}**.",
        "",
        "Cette note compare deux maillages de la meme equerre 3D rentrante TET10 sous chargement combine. Les deux niveaux ont ete resolus par QF_solver et Code_Aster 18.1.0 sur des maillages identiques.",
        "",
        "| h Gmsh | Elements | Noeuds | ||u_tip|| QF | ||u_tip|| Code_Aster | PEEQ QF | PEEQ Code_Aster |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for case in summary["cases"]:
        lines.append(
            f"| {case['mesh_size']:.3f} | {case['elements']} | {case['nodes']} | {case['qf_tip_displacement_m']:.6e} | {case['code_aster_tip_displacement_m']:.6e} | {case['qf_peeq_mean']:.6e} | {case['code_aster_peeq_mean']:.6e} |"
        )
    lines.extend(
        [
            "",
            f"Increment relatif QF entre les deux niveaux : deplacement `{summary['convergence']['qf_tip_displacement_relative_increment']:.6e}`, PEEQ `{summary['convergence']['qf_peeq_relative_increment']:.6e}`.",
            "",
            "![Convergence TET10 J2](convergence.png)",
            "",
            "## Limites",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in summary["limitations"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coarse", default="tmp/code_aster/tet10_j2_complex_refined_h032")
    parser.add_argument("--fine", default="tmp/code_aster/tet10_j2_complex_refined_h022")
    parser.add_argument("--output", default="tmp/code_aster/tet10_j2_complex_refinement")
    args = parser.parse_args()
    summary = compare_refinement(args.coarse, args.fine, args.output)
    print(f"TET10 J2 refinement: {summary['status']}")
    print(f"Output: {args.output}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 4


if __name__ == "__main__":
    raise SystemExit(main())
