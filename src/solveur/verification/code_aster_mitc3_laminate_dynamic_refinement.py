"""Strict refinement campaign for the MITC3+ laminate dynamic scope."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_mitc3_laminate_dynamic import (
    CodeAsterMitc3LaminateDynamicsCampaign,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


CAMPAIGN_ID = "VNV-MITC3-LAMINATE-DYNAMICS-REFINEMENT-CODEASTER-DST-020"
DEFAULT_LEVELS = ((8, 2), (12, 3), (16, 4), (24, 6))


class Mitc3LaminateDynamicRefinementCampaign:
    """Run and aggregate same-mesh laminate dynamic correlations."""

    def __init__(
        self,
        output_dir: str | Path,
        *,
        levels: tuple[tuple[int, int], ...] = DEFAULT_LEVELS,
        campaign_id: str = CAMPAIGN_ID,
        modelisation: str = "DST",
    ) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.levels = tuple((int(nx), int(ny)) for nx, ny in levels)
        self.campaign_id = str(campaign_id)
        self.modelisation = str(modelisation).upper()
        if self.modelisation not in {"DST", "DKT"}:
            raise ValueError("modelisation must be DST or DKT.")
        if len(self.levels) < 3:
            raise ValueError("At least three MITC3 laminate dynamic levels are required.")

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        for nx, ny in self.levels:
            level_dir = self.output_dir / f"mesh_{nx}x{ny}"
            summary = CodeAsterMitc3LaminateDynamicsCampaign(
                level_dir,
                nx=nx,
                ny=ny,
                publish_reference=False,
                modelisation=self.modelisation,
            ).run()
            rows.append(_row(summary))
        checks = _checks(rows)
        summary = {
            "schema_version": 1,
            "study_id": self.campaign_id,
            "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "WARNING",
            "execution_status": "PASS_EXTERNAL_CORRELATION",
            "maturity": "experimental",
            "scope": "MITC3+ [0/90/90/0] planar laminate dynamics",
            "external_solver": rows[-1]["external_solver"],
            "modelisation": self.modelisation,
            "mesh_level_count": len(rows),
            "comparison_basis": {
                "same_layup": True,
                "same_mesh_per_level": True,
                "same_time_and_frequency_protocol": True,
                "same_transverse_shear_correction": True,
                "same_tip_load_distribution": True,
                "shear_correction_factor": 5.0 / 6.0,
            },
            "mesh_levels": rows,
            "checks": checks,
            "stable_gate_status": "PASS_FOR_THIN_PLANAR_SUBSCOPE" if all(item["status"] == "PASS" for item in checks) else "BLOCKED_OVER_1_PERCENT",
            "promotion_gap": {
                "status": "BLOCKED_OVER_1_PERCENT" if any(item["status"] == "FAIL" for item in checks) else "PENDING_OWNER_REVIEW",
                "reason": "Strict one-percent gate is evaluated on the finest mesh; no maturity promotion is automatic.",
            },
            "limitations": [
                "Code_Aster DST and QF_solver MITC3+ are distinct formulations.",
                "The campaign covers one planar symmetric layup only.",
                "Curved dynamics, non-zero B coupling, damping calibration, damage and delamination are excluded.",
            ],
            "artifacts": [
                "summary.json",
                "report.md",
                "mitc3_laminate_dynamic_refinement.png",
                *[f"mesh_{row['nx']}x{row['ny']}/summary.json" for row in rows],
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        _plot(summary, self.output_dir / "mitc3_laminate_dynamic_refinement.png")
        write_vnv_manifest(self.output_dir, self.campaign_id)
        return summary


def _row(summary: dict[str, Any]) -> dict[str, Any]:
    checks = {str(item["id"]): item for item in summary["checks"]}
    model = summary["model"]
    return {
        "nx": int(model["mesh"][0]),
        "ny": int(model["mesh"][1]),
        "triangles": int(model["tria3_elements"]),
        "modal_error": float(checks["modal_frequencies"]["value"]),
        "newmark_error": float(checks["newmark_tip_history"]["value"]),
        "harmonic_error": float(checks["harmonic_tip_response"]["value"]),
        "qf_modal_residual": float(checks["qf_modal_residual"]["value"]),
        "qf_dynamic_residual": float(checks["qf_dynamic_residual"]["value"]),
        "external_solver": summary["external_solver"],
        "status": summary["status"],
    }


def _checks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fine = rows[-1]
    return [
        _check("fine_modal_error", fine["modal_error"], 0.01),
        _check("fine_newmark_error", fine["newmark_error"], 0.01),
        _check("fine_harmonic_error", fine["harmonic_error"], 0.01),
        _check("fine_qf_modal_residual", fine["qf_modal_residual"], 1e-7),
        _check("fine_qf_dynamic_residual", fine["qf_dynamic_residual"], 1e-7),
    ]


def _check(identifier: str, value: float, limit: float) -> dict[str, Any]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL"}


def _report(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut : **{summary['status']}**.",
        "",
        "| Maillage | Triangles | Modal | Newmark | Harmonique | Residu modal | Residu dynamique |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["mesh_levels"]:
        lines.append(
            f"| {row['nx']}x{row['ny']} | {row['triangles']} | {100*row['modal_error']:.4f} % | "
            f"{100*row['newmark_error']:.4f} % | {100*row['harmonic_error']:.4f} % | "
            f"{row['qf_modal_residual']:.3e} | {row['qf_dynamic_residual']:.3e} |"
        )
    lines.extend(["", "| Controle | Valeur | Limite | Statut |", "| --- | ---: | ---: | --- |"])
    for check in summary["checks"]:
        lines.append(f"| {check['id']} | {check['value']:.6g} | {check['limit']:.6g} | {check['status']} |")
    lines.extend(["", "![Refinement](mitc3_laminate_dynamic_refinement.png)", ""])
    lines.extend(f"- {item}" for item in summary["limitations"])
    return "\n".join(lines) + "\n"


def _plot(summary: dict[str, Any], output: Path) -> None:
    rows = summary["mesh_levels"]
    x = [row["triangles"] for row in rows]
    figure, axis = plt.subplots(figsize=(8.4, 4.5))
    for key, label, color in (("modal_error", "Modal", "#1f77b4"), ("newmark_error", "Newmark", "#d62728"), ("harmonic_error", "Harmonique", "#2ca02c")):
        axis.plot(x, [100 * row[key] for row in rows], "o-", label=label, color=color)
    axis.axhline(1.0, color="#111111", linestyle="--", linewidth=1.0, label="Limite stable 1 %")
    axis.set(xlabel="Elements TRI3", ylabel="Ecart QF / Code_Aster [%]", title="MITC3 multicouche - raffinement dynamique")
    axis.grid(alpha=0.25)
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output, dpi=180)
    plt.close(figure)
