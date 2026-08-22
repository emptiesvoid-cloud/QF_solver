"""Audit the axial curved MITC3+ correlation against two external references."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.io.manifest import write_json_file
from solveur.verification.vnv_manifest import write_vnv_manifest


def build_axial_audit(code_aster: dict[str, Any], calculix: dict[str, Any]) -> dict[str, Any]:
    """Compare common axial levels and classify external disagreement."""
    code_rows = {(int(row["nx"]), int(row["ny"])): row for row in code_aster["rows"]}
    calculix_rows = {(int(row["nx"]), int(row["ny"])): row for row in calculix["rows"]}
    common = sorted(set(code_rows) & set(calculix_rows))
    if not common:
        raise ValueError("The axial audit requires at least one common mesh level.")

    rows: list[dict[str, Any]] = []
    for level in common:
        aster = code_rows[level]
        s6 = calculix_rows[level]
        qf_ux = float(aster["qf_ux"])
        qf_uz = float(aster["qf_uz"])
        qf_consistency = float(
            np.linalg.norm([qf_ux - float(s6["qf_ux"]), qf_uz - float(s6["qf_uz"])])
            / max(np.linalg.norm([qf_ux, qf_uz]), np.finfo(float).tiny)
        )
        aster_vector = np.asarray([float(aster["code_aster_ux"]), float(aster["code_aster_uz"])])
        s6_vector = np.asarray([float(s6["calculix_ux"]), float(s6["calculix_uz"])])
        rows.append(
            {
                "nx": level[0],
                "ny": level[1],
                "elements": int(aster.get("mitc3_elements", s6["mitc3_elements"])),
                "qf_ux": qf_ux,
                "qf_uz": qf_uz,
                "code_aster_ux": float(aster["code_aster_ux"]),
                "code_aster_uz": float(aster["code_aster_uz"]),
                "calculix_ux": float(s6["calculix_ux"]),
                "calculix_uz": float(s6["calculix_uz"]),
                "qf_cross_reference_relative_difference": qf_consistency,
                "code_aster_calculix_relative_difference": float(
                    np.linalg.norm(aster_vector - s6_vector)
                    / max(np.linalg.norm(aster_vector), np.finfo(float).tiny)
                ),
                "qf_code_aster_vector_difference": float(aster["vector_difference"]),
                "qf_calculix_vector_difference": float(s6["vector_difference"]),
            }
        )

    max_qf_consistency = max(row["qf_cross_reference_relative_difference"] for row in rows)
    max_external_spread = max(row["code_aster_calculix_relative_difference"] for row in rows)
    fine = rows[-1]
    return {
        "study_id": "VNV-MITC3-LAMINATE-CURVED-AXIAL-REFERENCE-AUDIT-001",
        "status": "PASS_DIAGNOSTIC",
        "scope": "axial load on one faceted cylindrical [0/90/90/0] laminate",
        "conclusion": (
            "The QF_solver response is reproducible between the Code_Aster and CalculiX input paths, "
            "but the two external shell formulations do not agree on the axial curved response. "
            "The residual stable gap is therefore not attributable to the time step and cannot be "
            "removed by claiming mesh convergence alone."
        ),
        "references": {
            "code_aster": code_aster.get("external_solver", {}),
            "calculix": calculix.get("external_solver", {}),
            "same_qf_model": True,
            "common_mesh_levels": [f"{row['nx']}x{row['ny']}" for row in rows],
        },
        "rows": rows,
        "checks": [
            {
                "id": "QF-CROSS-REFERENCE-CONSISTENCY",
                "value": max_qf_consistency,
                "limit": 1.0e-10,
                "status": "PASS" if max_qf_consistency <= 1.0e-10 else "FAIL",
            },
            {
                "id": "EXTERNAL-FORMULATION-SPREAD-REPORTED",
                "value": max_external_spread,
                "limit": None,
                "status": "INFORMATIONAL",
            },
            {
                "id": "FINE-QF-CODE-ASTER-UNDER-ONE-PERCENT",
                "value": fine["qf_code_aster_vector_difference"],
                "limit": 0.01,
                "status": "PASS" if fine["qf_code_aster_vector_difference"] <= 0.01 else "FAIL",
            },
            {
                "id": "FINE-QF-CALCULIX-UNDER-ONE-PERCENT",
                "value": fine["qf_calculix_vector_difference"],
                "limit": 0.01,
                "status": "PASS" if fine["qf_calculix_vector_difference"] <= 0.01 else "FAIL",
            },
        ],
        "stable_gate_status": "BLOCKED_EXTERNAL_FORMULATION_COMPARABILITY",
        "limitations": [
            "The diagnostic uses global displacement observables only.",
            "Code_Aster DST and CalculiX S6 are not matrix-identical to MITC3+.",
            "The result does not promote the general curved MITC3 laminate scope.",
            "Ply stresses, interlaminar stresses, damage and delamination remain excluded.",
        ],
    }


def write_axial_audit(code_aster_path: str | Path, calculix_path: str | Path, output: str | Path) -> dict[str, Any]:
    """Write JSON, Markdown, plot and manifest for the axial diagnostic."""
    code_aster = json.loads(Path(code_aster_path).read_text(encoding="utf-8"))
    calculix = json.loads(Path(calculix_path).read_text(encoding="utf-8"))
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = build_axial_audit(code_aster, calculix)
    write_json_file(target / "summary.json", summary)
    _plot(summary, target / "axial_external_comparison.png")
    (target / "report.md").write_text(_report(summary), encoding="utf-8")
    write_vnv_manifest(target, summary["study_id"])
    return summary


def _plot(summary: dict[str, Any], path: Path) -> None:
    rows = summary["rows"]
    elements = [row["elements"] for row in rows]
    figure, axes = plt.subplots(1, 2, figsize=(11.0, 4.4))
    for component, axis in (("ux", axes[0]), ("uz", axes[1])):
        axis.semilogx(elements, [abs(row[f"qf_{component}"]) for row in rows], "o-", label="QF_solver")
        axis.semilogx(elements, [abs(row[f"code_aster_{component}"]) for row in rows], "s--", label="Code_Aster DST")
        axis.semilogx(elements, [abs(row[f"calculix_{component}"]) for row in rows], "^:", label="CalculiX S6")
        axis.set(xlabel="Elements", ylabel=f"|{component.upper()}| [m]", title=f"Reponse axiale {component.upper()}")
        axis.grid(True, which="both", alpha=0.25)
        axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _report(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut : **{summary['status']}**.",
        "",
        summary["conclusion"],
        "",
        "| Maillage | QF UX | Code_Aster UX | CalculiX UX | QF UZ | Code_Aster UZ | CalculiX UZ | QF/CA | QF/S6 |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["rows"]:
        lines.append(
            f"| {row['nx']}x{row['ny']} | {row['qf_ux']:.6e} | {row['code_aster_ux']:.6e} | {row['calculix_ux']:.6e} | "
            f"{row['qf_uz']:.6e} | {row['code_aster_uz']:.6e} | {row['calculix_uz']:.6e} | "
            f"{100 * row['qf_code_aster_vector_difference']:.3f} % | {100 * row['qf_calculix_vector_difference']:.3f} % |"
        )
    lines.extend(
        [
            "",
            "![Comparaison axiale](axial_external_comparison.png)",
            "",
            "## Interprétation",
            "",
            "Le déplacement QF_solver est reproduit entre les deux chemins d'entrée. "
            "La divergence Code_Aster/CalculiX est donc une information sur la comparabilité des références externes, "
            "et non une preuve que le pas de temps ou le solveur QF_solver est en cause.",
            "",
            "## Gate",
            "",
            f"`{summary['stable_gate_status']}` : aucune promotion générale n'est effectuée sur la base de ce diagnostic.",
        ]
    )
    return "\n".join(lines) + "\n"
