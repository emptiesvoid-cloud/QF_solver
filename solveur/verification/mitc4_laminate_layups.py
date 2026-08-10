"""Three-layup external dynamic correlation for the MITC4 laminate scope."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_mitc4_laminate_dynamic import (
    CodeAsterMitc4LaminateDynamicsCampaign,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-021"
LAYUP_CASES = (
    {"id": "cross_ply_0_90", "layup_deg": (0.0, 90.0, 90.0, 0.0), "damping_ratio": 0.0},
    {"id": "angle_ply_45", "layup_deg": (45.0, -45.0, -45.0, 45.0), "damping_ratio": 0.0},
    {"id": "off_axis_0_45_damped", "layup_deg": (0.0, 45.0, 45.0, 0.0), "damping_ratio": 0.03},
)


class Mitc4LaminateLayupCorrelationCampaign:
    """Run common modal, Newmark and harmonic checks for three laminate layups."""

    study_id = STUDY_ID

    def __init__(self, output_dir: str | Path, *, nx: int = 12, ny: int = 3) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.nx, self.ny = int(nx), int(ny)

    def run(self) -> dict[str, Any]:
        """Execute all same-mesh external correlations and collect their evidence."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        cases: list[dict[str, Any]] = []
        for definition in LAYUP_CASES:
            target = self.output_dir / str(definition["id"])
            campaign = CodeAsterMitc4LaminateDynamicsCampaign(
                target,
                nx=self.nx,
                ny=self.ny,
                layup=tuple(definition["layup_deg"]),
                damping_ratio=float(definition["damping_ratio"]),
                publish_reference=False,
            )
            result = campaign.run()
            cases.append(
                {
                    "id": definition["id"],
                    "layup_deg": list(definition["layup_deg"]),
                    "damping_ratio": float(definition["damping_ratio"]),
                    "summary": result,
                    "result_directory": str(target.relative_to(self.output_dir)),
                }
            )
        checks = _checks(cases)
        summary = {
            "study_id": STUDY_ID,
            "status": "PASS_EXTERNAL_CORRELATION" if all(row["status"] == "PASS" for row in checks) else "FAIL",
            "scope": "Planar symmetric MITC4 laminates with common Code_Aster DST dynamic correlation.",
            "common_properties": {
                "mesh": [self.nx, self.ny],
                "quad4_elements": self.nx * self.ny,
                "plies_per_case": 4,
                "ply_thickness_m": 0.0025,
                "total_thickness_m": 0.01,
                "material": "identical orthotropic carbon/epoxy ply properties for every case",
            },
            "cases": cases,
            "checks": checks,
            "limitations": [
                "All layups are planar and symmetric; coupling B is not exercised.",
                "The damped case uses mass-proportional Rayleigh damping targeted at 3 percent on mode 1.",
                "The campaign does not validate curved laminate dynamics, damping calibration from tests, damage or delamination.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(summary)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, STUDY_ID)
        return summary

    def _plot(self, summary: dict[str, Any]) -> None:
        figure, axes = plt.subplots(1, 2, figsize=(11.5, 4.1))
        for case in summary["cases"]:
            details = case["summary"]
            label = "/".join(f"{angle:g}" for angle in case["layup_deg"])
            frequencies = details["modal"]["qf_frequencies_hz"]
            axes[0].plot(range(1, len(frequencies) + 1), frequencies, "o-", label=label)
            history = details["newmark"]["qf_tip_uz_m"]
            step = details["newmark"]["time_step_s"]
            axes[1].plot([index * step for index in range(len(history))], history, label=label)
        axes[0].set(title="Frequences QF_solver", xlabel="Mode", ylabel="Frequence [Hz]")
        axes[1].set(title="Reponse Newmark QF_solver", xlabel="Temps [s]", ylabel="UZ moyen pointe [m]")
        for axis in axes:
            axis.grid(alpha=0.25)
            axis.legend(fontsize=8)
        figure.tight_layout()
        figure.savefig(self.output_dir / "mitc4_laminate_layups_comparison.png", dpi=180)
        plt.close(figure)


def _checks(cases: list[dict[str, Any]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for case in cases:
        details = case["summary"]
        for check in details["checks"]:
            rows.append(
                {
                    "id": f"{case['id']}::{check['id']}",
                    "value": float(check["value"]),
                    "limit": float(check["limit"]),
                    "status": str(check["status"]),
                }
            )
    return rows


def _report(summary: dict[str, Any]) -> str:
    lines = [
        f"# {STUDY_ID}",
        "",
        f"Statut automatise : **{summary['status']}**.",
        "",
        "Trois bandes MITC4 sont comparees a Code_Aster DST avec le meme maillage, "
        "les memes proprietes de pli, blocages, chargements et protocoles modal/Newmark/harmonique.",
        "",
        "| Cas | Empilement [deg] | Amortissement modal cible | Verdict |",
        "| --- | --- | ---: | --- |",
    ]
    for case in summary["cases"]:
        details = case["summary"]
        layup = "/".join(f"{angle:g}" for angle in case["layup_deg"])
        lines.append(
            f"| {case['id']} | [{layup}] | {100.0 * case['damping_ratio']:.1f} % | {details['status']} |"
        )
    lines.extend(["", "| Controle | Valeur | Seuil | Verdict |", "| --- | ---: | ---: | --- |"])
    for check in summary["checks"]:
        lines.append(
            f"| {check['id']} | {check['value']:.4e} | {check['limit']:.4e} | {check['status']} |"
        )
    lines.extend(["", "![Comparaison des trois empilements](mitc4_laminate_layups_comparison.png)", ""])
    return "\n".join(lines)
