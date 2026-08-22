"""Multi-level Code_Aster correlation for the bounded MITC3+ dynamics scopes.

The campaign deliberately reuses the same physical problem and varies only the
spatial mesh.  Each level is solved independently by QF_solver and by the
pinned Code_Aster DKT reference, so the evidence does not infer convergence
from a single mesh.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_mitc3_dynamic import CodeAsterMitc3DynamicsCampaign
from solveur.verification.vnv_manifest import write_vnv_manifest


CAMPAIGN_ID = "VNV-MITC3-DYNAMICS-REFINEMENT-CODEASTER-DKT-026"
DEFAULT_LEVELS: tuple[tuple[int, int], ...] = ((8, 2), (16, 4), (24, 6))


class CodeAsterMitc3DynamicRefinementCampaign:
    """Run and aggregate the three-level MITC3+ dynamic correlation."""

    def __init__(
        self,
        output_dir: str | Path,
        *,
        levels: tuple[tuple[int, int], ...] = DEFAULT_LEVELS,
    ) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.levels = tuple((int(nx), int(ny)) for nx, ny in levels)
        if len(self.levels) < 3:
            raise ValueError("MITC3 dynamic refinement requires at least three mesh levels.")
        if any(nx < 4 or ny < 1 for nx, ny in self.levels):
            raise ValueError("MITC3 dynamic refinement requires nx >= 4 and ny >= 1.")

    def run(self) -> dict[str, Any]:
        """Execute every level and write one machine-readable aggregate ledger."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        level_summaries = []
        for nx, ny in self.levels:
            level_dir = self.output_dir / f"mesh_{nx}x{ny}"
            level_summaries.append(
                CodeAsterMitc3DynamicsCampaign(level_dir, nx=nx, ny=ny).run()
            )
        summary = self._aggregate(level_summaries)
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(_render_report(summary), encoding="utf-8")
        _plot(summary, self.output_dir / "mesh_frequency_refinement.png")
        write_vnv_manifest(self.output_dir, CAMPAIGN_ID)
        return summary

    def _aggregate(self, levels: list[dict[str, Any]]) -> dict[str, Any]:
        rows = [_level_row(level) for level in levels]
        modal_increments = _increments([row["qf_first_frequency_hz"] for row in rows])
        external_increments = _increments([row["code_aster_first_frequency_hz"] for row in rows])
        final = rows[-1]
        checks = [
            _check("mesh_level_count", float(len(rows)), 3.0, minimum=True),
            _check("fine_modal_external_error", final["modal_error_max"], 0.10),
            _check("fine_newmark_external_error", final["newmark_error"], 0.10),
            _check("fine_harmonic_external_error", final["harmonic_error"], 0.10),
            _check("fine_qf_frequency_increment", modal_increments[-1], 0.10),
            _check("fine_code_aster_frequency_increment", external_increments[-1], 0.10),
        ]
        return {
            "schema_version": 1,
            "study_id": CAMPAIGN_ID,
            "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "WARNING",
            "maturity": "experimental",
            "scope": ["mitc3-modal", "mitc3-transient-dynamic", "mitc3-harmonic-response"],
            "external_solver": levels[-1]["external_solver"],
            "comparison_basis": {
                "same_geometry": True,
                "same_material": True,
                "same_boundary_conditions": True,
                "same_time_and_frequency_protocol_per_level": True,
                "spatial_levels": [[row["nx"], row["ny"]] for row in rows],
            },
            "mesh_levels": rows,
            "refinement": {
                "qf_first_frequency_increments": modal_increments,
                "code_aster_first_frequency_increments": external_increments,
            },
            "checks": checks,
            "promotion_gap": {
                "status": "PENDING_OWNER_REVIEW",
                "reason": "La preuve technique est complete; la promotion de maturite reste une decision Owner explicite.",
            },
            "limitations": [
                "MITC3+ QF_solver est compare a DKT/TRIA3 Code_Aster, formulations distinctes.",
                "La campagne porte sur une coque isotrope plane, sans amortissement ni non-linearite.",
                "Les contraintes, le contact, les grandes rotations et les stratifies ne sont pas couverts par ce ledger.",
                "La preuve ne vaut pas promotion automatique vers stable.",
            ],
            "artifacts": [
                "summary.json",
                "report.md",
                "mesh_frequency_refinement.png",
                *[f"mesh_{row['nx']}x{row['ny']}/summary.json" for row in rows],
                *[f"mesh_{row['nx']}x{row['ny']}/comparison.png" for row in rows],
            ],
        }


def _level_row(summary: dict[str, Any]) -> dict[str, Any]:
    modal = summary["modal"]
    checks = {str(item["id"]): item for item in summary["checks"]}
    return {
        "nx": int(summary["model"]["mesh"][0]),
        "ny": int(summary["model"]["mesh"][1]),
        "triangles": int(summary["model"]["triangles"]),
        "qf_first_frequency_hz": float(modal["qf_frequencies_hz"][0]),
        "code_aster_first_frequency_hz": float(modal["code_aster_frequencies_hz"][0]),
        "modal_error_max": float(checks["modal_frequencies"]["value"]),
        "newmark_error": float(checks["newmark_tip_history"]["value"]),
        "harmonic_error": float(checks["harmonic_tip_response"]["value"]),
        "status": summary["status"],
        "external_solver": summary["external_solver"],
    }


def _increments(values: list[float]) -> list[float]:
    return [
        abs(values[index] - values[index - 1]) / max(abs(values[index]), 1.0e-30)
        for index in range(1, len(values))
    ]


def _check(identifier: str, value: float, limit: float, *, minimum: bool = False) -> dict[str, Any]:
    passed = value >= limit if minimum else value <= limit
    return {
        "id": identifier,
        "value": value,
        "limit": limit,
        "operator": ">=" if minimum else "<=",
        "status": "PASS" if np.isfinite(value) and passed else "FAIL",
    }


def _render_report(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut automatise : **{summary['status']}**.",
        "",
        "La campagne reprend le meme porte-a-faux isotrope, les memes conditions limites et les memes protocoles dynamiques a chaque niveau. Seul le maillage spatial change.",
        "",
        "| Maillage | Triangles | f1 QF [Hz] | f1 Code_Aster [Hz] | erreur modale | erreur Newmark | erreur harmonique |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["mesh_levels"]:
        lines.append(
            f"| {row['nx']}x{row['ny']} | {row['triangles']} | {row['qf_first_frequency_hz']:.6g} | {row['code_aster_first_frequency_hz']:.6g} | {100 * row['modal_error_max']:.4g} % | {100 * row['newmark_error']:.4g} % | {100 * row['harmonic_error']:.4g} % |"
        )
    lines.extend(["", "| Controle | Valeur | Limite | Statut |", "| --- | ---: | ---: | --- |"])
    for check in summary["checks"]:
        lines.append(f"| {check['id']} | {check['value']:.6g} | {check['operator']} {check['limit']:.6g} | {check['status']} |")
    lines.extend(["", "![Raffinement frequence-maillage](mesh_frequency_refinement.png)", ""])
    lines.extend(f"- {item}" for item in summary["limitations"])
    return "\n".join(lines) + "\n"


def _plot(summary: dict[str, Any], output: Path) -> None:
    rows = summary["mesh_levels"]
    triangles = [row["triangles"] for row in rows]
    figure, axes = plt.subplots(1, 2, figsize=(11.0, 4.0))
    axes[0].plot(triangles, [row["qf_first_frequency_hz"] for row in rows], "o-", label="QF_solver")
    axes[0].plot(triangles, [row["code_aster_first_frequency_hz"] for row in rows], "s--", label="Code_Aster DKT")
    axes[0].set(xlabel="Elements TRI3", ylabel="Premiere frequence [Hz]", title="Raffinement modal")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(fontsize=8)
    axes[1].plot(triangles, [100 * row["modal_error_max"] for row in rows], "o-", label="Modal")
    axes[1].plot(triangles, [100 * row["newmark_error"] for row in rows], "s-", label="Newmark")
    axes[1].plot(triangles, [100 * row["harmonic_error"] for row in rows], "^-", label="Harmonique")
    axes[1].set(xlabel="Elements TRI3", ylabel="Ecart QF / Code_Aster [%]", title="Correlation par niveau")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output, dpi=180)
    plt.close(figure)


def load_refinement_summary(path: str | Path) -> dict[str, Any]:
    """Load an aggregate ledger for tests and promotion criteria."""
    return json.loads(Path(path).read_text(encoding="utf-8"))
