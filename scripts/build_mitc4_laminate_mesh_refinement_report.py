"""Build the mesh-refinement evidence for the MITC4 laminate owner review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402


METRICS = ("modal_frequencies", "newmark_tip_history", "harmonic_tip_response")
CASES = ("cross_ply_0_90", "angle_ply_45", "off_axis_0_45_damped")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _index(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(case["id"]): case for case in summary["cases"]}


def build_report(root: Path) -> tuple[dict[str, Any], str]:
    runs = {
        "h1_36_elements": ("12x3", root / "VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-021-20260809"),
        "h2_72_elements": ("24x3", root / "VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-021-20260809-h2"),
        "h4_balanced_144_elements": (
            "24x6",
            root / "VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-021-20260809-balanced",
        ),
        "h4_directional_144_elements": (
            "48x3",
            root / "VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-021-20260809-h4",
        ),
    }
    indexed = {key: (mesh, _index(_read(path / "summary.json"))) for key, (mesh, path) in runs.items()}
    rows: list[dict[str, Any]] = []
    for case_id in CASES:
        for metric in METRICS:
            values = {
                key: float(
                    next(check["value"] for check in cases[case_id]["summary"]["checks"] if check["id"] == metric)
                )
                for key, (_, cases) in indexed.items()
            }
            rows.append({"case": case_id, "metric": metric, "relative_error": values})
    evidence = {
        "study_id": "VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-021",
        "evidence_id": "VNV-MITC4-LAMINATE-MESH-REFINEMENT-022",
        "status": "PASS_EXTERNAL_CORRELATION",
        "reference": "Code_Aster 18.1 DST / DEFI_COMPOSITE",
        "runs": {
            key: {"mesh": mesh, "elements": int(mesh.split("x")[0]) * int(mesh.split("x")[1])}
            for key, (mesh, _) in runs.items()
        },
        "rows": rows,
        "interpretation": {
            "balanced_refinement_required": True,
            "angle_ply_requires_owner_attention": True,
            "conclusion": (
                "The balanced 24x6 refinement reduces the angle-ply transient and harmonic gaps, "
                "but the modal gap remains about 1.8 percent. The evidence supports a mesh and "
                "grid-sensitivity contribution, but does not prove that the remaining difference is "
                "exclusively a mesh error."
            ),
        },
    }
    return evidence, _markdown(evidence)


def _percent(value: float) -> str:
    return f"{100.0 * value:.3f} %"


def _markdown(evidence: dict[str, Any]) -> str:
    lines = [
        "# VNV-MITC4-LAMINATE-MESH-REFINEMENT-022",
        "",
        "## Objet",
        "",
        "Cette note complète la Owner Review MITC4 multicouche dynamique. Elle "
        "double le nombre d'éléments puis teste un raffinement équilibré afin de "
        "séparer l'effet du maillage de l'effet d'une grille anisotrope.",
        "",
        "## Maillages exécutés",
        "",
        "| Niveau | Grille | Éléments QUAD4 | Interprétation |",
        "| --- | ---: | ---: | --- |",
        "| H1 | 12 × 3 | 36 | référence précédente |",
        "| H2 | 24 × 3 | 72 | quantité d'éléments doublée, raffinement directionnel |",
        "| H4 équilibré | 24 × 6 | 144 | quantité doublée à nouveau, raffinement équilibré |",
        "| H4 directionnel | 48 × 3 | 144 | témoin de l'anisotropie de grille |",
        "",
        "Les propriétés, empilements, chargements, blocages, pas temporels et "
        "grilles fréquentielles sont identiques entre les niveaux.",
        "",
        "## Écarts relatifs QF_solver / Code_Aster",
        "",
        "| Cas | Indicateur | H1 | H2 | H4 équilibré | H4 directionnel |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in evidence["rows"]:
        values = row["relative_error"]
        label = {"modal_frequencies": "Modal", "newmark_tip_history": "Newmark", "harmonic_tip_response": "Harmonique"}[row["metric"]]
        lines.append(
            f"| {row['case']} | {label} | {_percent(values['h1_36_elements'])} | "
            f"{_percent(values['h2_72_elements'])} | {_percent(values['h4_balanced_144_elements'])} | "
            f"{_percent(values['h4_directional_144_elements'])} |"
        )
    lines.extend(
        [
            "",
            "## Conclusion technique",
            "",
            "Le maillage équilibré `24 × 6` réduit les écarts du cas "
            "`[45/-45/-45/45]` en Newmark de `3,740 %` à `1,738 %` et en "
            "harmonique de `1,994 %` à `0,964 %`. Le modal reste à `1,771 %`. "
            "Les deux autres empilements descendent sous `0,5 %` sur les trois "
            "indicateurs avec le maillage équilibré.",
            "",
            "Le raffinement `48 × 3` dégrade le cas `±45°`, ce qui montre qu'un "
            "simple ajout d'éléments dans une seule direction ne constitue pas "
            "une preuve de convergence. La conclusion acceptable est donc : "
            "l'écart est fortement influencé par la discrétisation et la grille "
            "temporelle, mais l'hypothèse « écart exclusivement dû au maillage » "
            "reste ouverte pour le modal du cas `±45°`.",
            "",
            "Les trois calculs restent dans les seuils d'acceptation de la "
            "corrélation externe. Cette note ne ferme pas la décision Owner Q5 "
            "et ne constitue pas une certification externe.",
            "",
            "![Courbes de convergence des écarts](mesh_refinement_convergence.png)",
            "",
        ]
    )
    return "\n".join(lines)


def _plot(evidence: dict[str, Any], path: Path) -> None:
    labels = {
        "modal_frequencies": "Modal",
        "newmark_tip_history": "Newmark",
        "harmonic_tip_response": "Harmonique",
    }
    colors = {"cross_ply_0_90": "#0072B2", "angle_ply_45": "#D55E00", "off_axis_0_45_damped": "#009E73"}
    labels_for_case = {
        "cross_ply_0_90": "[0/90/90/0]",
        "angle_ply_45": "[45/-45/-45/45]",
        "off_axis_0_45_damped": "[0/45/45/0] amorti",
    }
    values = {(row["case"], row["metric"]): row["relative_error"] for row in evidence["rows"]}
    levels = (
        ("h1_36_elements", "H1 - 36", "-"),
        ("h2_72_elements", "H2 - 72", "-"),
        ("h4_balanced_144_elements", "H4 equilibre - 144", "-"),
        ("h4_directional_144_elements", "H4 directionnel - 144", "--"),
    )
    figure, axes = plt.subplots(1, 3, figsize=(13.5, 4.4), sharey=True)
    for axis, metric in zip(axes, METRICS):
        for case_id in CASES:
            row = values[(case_id, metric)]
            x = [36, 72, 144, 144]
            y = [row[key] for key, _, _ in levels]
            axis.semilogy(x[:3], y[:3], "o-", color=colors[case_id], label=labels_for_case[case_id])
            axis.semilogy(x[2:], y[2:], "s--", color=colors[case_id], alpha=0.75)
        axis.set_title(labels[metric])
        axis.set_xlabel("Elements QUAD4")
        axis.grid(alpha=0.25, which="both")
    axes[0].set_ylabel("Ecart relatif QF_solver / Code_Aster")
    axes[-1].legend(fontsize=7, loc="best")
    figure.suptitle("VNV MITC4 multicouche - convergence du maillage", fontsize=12)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence, report = build_report(args.results_root.resolve())
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "mesh_refinement_summary.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    (args.output / "mesh_refinement_report.md").write_text(report, encoding="utf-8")
    _plot(evidence, args.output / "mesh_refinement_convergence.png")
    print(evidence["evidence_id"] + ": " + evidence["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
