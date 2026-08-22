"""Aggregate same-mesh Code_Aster temporal probes for MITC3+ dynamics.

The external solver is rerun at several time resolutions while the spatial
mesh, material, supports and load definition remain fixed.  The campaign is a
diagnostic: it tests whether the QF_solver/Code_Aster gap is controlled by the
time step.  It does not silently convert a non-equivalent DST comparison into
an acceptance criterion.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

from solveur.io.manifest import write_json_file

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.verification.vnv_manifest import write_vnv_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[4]
STUDY_ID = "VNV-MITC3-LAMINATE-CODEASTER-TEMPORAL-REFINEMENT-001"


class CodeAsterMitc3TemporalRefinementStudy:
    """Aggregate completed external runs at fixed spatial resolution."""

    persistent_error_limit = 1.0e-2
    residual_limit = 1.0e-7

    def __init__(self, source_dirs: tuple[str | Path, ...], output_dir: str | Path) -> None:
        if len(source_dirs) < 3:
            raise ValueError("at least three external temporal levels are required")
        self.source_dirs = tuple(Path(path).resolve() for path in source_dirs)
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        for source in self.source_dirs:
            summary = self._read_summary(source)
            row = _row(summary)
            rows.append(row)
            level_dir = self.output_dir / f"steps_{row['steps_per_period']}"
            level_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / "summary.json", level_dir / "summary.json")
        rows.sort(key=lambda row: row["steps_per_period"])
        checks = _checks(rows, self.persistent_error_limit, self.residual_limit)
        summary = {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "status": "PASS_DIAGNOSTIC" if all(item["status"] == "PASS" for item in checks) else "FAIL",
            "maturity": "verified_development",
            "scope": "fixed 12x3 planar MITC3+ laminate, Code_Aster DST temporal diagnostic",
            "spatial_mesh": [12, 3],
            "time_level_count": len(rows),
            "time_levels": rows,
            "checks": checks,
        "interpretation": (
                "The external discrepancies remain above one percent and nearly "
                "unchanged when the common time step is refined. The internal "
                "Newmark temporal error is therefore not the primary cause; the "
                "remaining difference is attributed to the non-equivalent MITC3+ "
                "and DST K/M operators and to phase sensitivity."
            ),
            "stable_gate_status": "BLOCKED_OVER_1_PERCENT",
            "limitations": [
                "This is a causal diagnostic, not a stable-promotion gate.",
                "Code_Aster uses DST/TRIA3, while QF_solver uses MITC3+.",
                "Only the planar symmetric [0/90/90/0] laminate and the 12x3 spatial mesh are covered.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        _plot(self.output_dir / "temporal_external_comparison.png", summary)
        write_vnv_manifest(self.output_dir, STUDY_ID)
        return summary

    @staticmethod
    def _read_summary(source: Path) -> dict[str, Any]:
        path = source / "summary.json"
        if not path.is_file():
            raise FileNotFoundError(f"missing external summary: {path}")
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "PASS_EXTERNAL_CORRELATION":
            raise ValueError(f"external run is not successful: {path}")
        return payload


def _row(summary: dict[str, Any]) -> dict[str, Any]:
    checks = {str(item["id"]): item for item in summary["checks"]}
    return {
        "steps_per_period": int(summary["comparison_basis"]["steps_per_period"]),
        "time_step_s": float(summary["newmark"]["time_step_s"]),
        "modal_error": float(checks["modal_frequencies"]["value"]),
        "newmark_error": float(checks["newmark_tip_history"]["value"]),
        "newmark_forced_error": float(checks["newmark_forced_history"]["value"]),
        "newmark_free_error": float(checks["newmark_free_history"]["value"]),
        "harmonic_error": float(checks["harmonic_tip_response"]["value"]),
        "qf_modal_residual": float(checks["qf_modal_residual"]["value"]),
        "qf_dynamic_residual": float(checks["qf_dynamic_residual"]["value"]),
    }


def _checks(rows: list[dict[str, Any]], error_limit: float, residual_limit: float) -> list[dict[str, Any]]:
    fine = rows[-1]
    return [
        _check("three_temporal_levels", len(rows), 3, operator=">=") ,
        _check("fine_modal_error_above_one_percent", fine["modal_error"], error_limit, operator=">"),
        _check("fine_newmark_error_above_one_percent", fine["newmark_error"], error_limit, operator=">"),
        _check("fine_harmonic_error_above_one_percent", fine["harmonic_error"], error_limit, operator=">"),
        _check("fine_qf_modal_residual", fine["qf_modal_residual"], residual_limit),
        _check("fine_qf_dynamic_residual", fine["qf_dynamic_residual"], residual_limit),
        _check("newmark_external_persistent_over_one_percent", min(row["newmark_error"] for row in rows), error_limit, operator=">"),
        _check("harmonic_external_persistent_over_one_percent", min(row["harmonic_error"] for row in rows), error_limit, operator=">"),
        _check("modal_external_persistent_over_one_percent", min(row["modal_error"] for row in rows), error_limit, operator=">"),
        _check("newmark_external_spread", max(row["newmark_error"] for row in rows) - min(row["newmark_error"] for row in rows), 1.0e-3),
    ]


def _check(identifier: str, value: float, limit: float, *, operator: str = "<=") -> dict[str, Any]:
    if operator == ">=":
        passed = value >= limit
    elif operator == ">":
        passed = value > limit
    else:
        passed = np.isfinite(value) and value <= limit
    return {"id": identifier, "value": float(value), "limit": float(limit), "operator": operator, "status": "PASS" if passed else "FAIL"}


def _report(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        "Diagnostic Code_Aster DST/QF_solver MITC3+ a maillage spatial fixe `12x3`.",
        "",
        "| Pas/periode | dt (s) | Modal | Newmark RMS | Newmark force | Newmark libre | Harmonique |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["time_levels"]:
        lines.append(
            f"| {row['steps_per_period']} | {row['time_step_s']:.6e} | {100*row['modal_error']:.4f} % | "
            f"{100*row['newmark_error']:.4f} % | {100*row['newmark_forced_error']:.4f} % | "
            f"{100*row['newmark_free_error']:.4f} % | {100*row['harmonic_error']:.4f} % |"
        )
    lines.extend(["", "## Conclusion", "", summary["interpretation"], "", "## Checks", "", "| Identifiant | Valeur | Limite | Operateur | Statut |", "| --- | ---: | ---: | --- | --- |"])
    lines.extend(f"| {item['id']} | {item['value']:.6g} | {item['limit']:.6g} | {item['operator']} | {item['status']} |" for item in summary["checks"])
    lines.extend(["", "![Comparaison temporelle externe](temporal_external_comparison.png)", "", "## Limites", ""])
    lines.extend(f"- {item}" for item in summary["limitations"])
    return "\n".join(lines) + "\n"


def _plot(path: Path, summary: dict[str, Any]) -> None:
    rows = summary["time_levels"]
    x = [row["steps_per_period"] for row in rows]
    figure, axes = plt.subplots(1, 3, figsize=(12.0, 4.0))
    for axis, key, label, color in zip(
        axes,
        ("modal_error", "newmark_error", "harmonic_error"),
        ("modal", "Newmark RMS", "harmonique"),
        ("#1f77b4", "#d62728", "#2ca02c"),
        strict=True,
    ):
        axis.plot(x, [100.0 * row[key] for row in rows], "o-", color=color)
        axis.axhline(1.0, color="#111111", linestyle="--", linewidth=0.9)
        axis.set(xlabel="pas par periode", ylabel="ecart [%]", title=label)
        axis.grid(alpha=0.25)
    figure.suptitle("MITC3+ / Code_Aster DST : effet du pas de temps")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
