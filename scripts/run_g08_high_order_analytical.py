"""Run an independent Euler screen for the high-order solid buckling routes.

This is a verification harness only. It uses the public linear-buckling route
with a fixed-free solid column and compares the first critical load with the
declared Euler reference. A negative result remains evidence of a limitation;
the harness never changes solver policies or promotes a family automatically.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
# ruff: noqa: E402

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import runtime_fingerprint, sha256, write_json_file
from solveur.verification.robustness_mesh import mesh_refinement_mesh


GATE = "026-G08"
STUDY_ID = "VNV-G08-HIGH-ORDER-EULER-001"
FAMILIES = ("TET10", "HEX8", "HEX20")
MESH_LEVELS = (1, 2, 3)
EULER_RELATIVE_TOLERANCE = 0.10
EIGENPAIR_RESIDUAL_PASS = 1.0e-7
REPEATABILITY_ABSOLUTE_TOLERANCE = 1.0e-12
YOUNG = 1.0e6
POISSON = 0.3
LENGTH = 4.0
WIDTH = 0.5
HEIGHT = 0.5
REFERENCE_LOAD = 1.0


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _git_state() -> tuple[str, bool]:
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()
    )
    return sha, dirty


def _euler_reference() -> float:
    inertia = WIDTH * HEIGHT**3 / 12.0
    return float(math.pi**2 * YOUNG * inertia / (4.0 * LENGTH**2))


def _model(family: str, cells: int) -> tuple[FiniteElementModel, dict[str, Any]]:
    nodes, elements = mesh_refinement_mesh(family, cells)
    scaled = nodes.copy()
    scaled[:, 0] *= LENGTH
    scaled[:, 1] *= WIDTH
    scaled[:, 2] *= HEIGHT
    fixed_nodes = np.flatnonzero(np.isclose(scaled[:, 0], 0.0))
    loaded_nodes = np.flatnonzero(np.isclose(scaled[:, 0], LENGTH))
    model = FiniteElementModel.from_raw(
        nodes=scaled.tolist(),
        elements=[{"type": family, "nodes": item, "material": "solid"} for item in elements],
        materials={"solid": {"type": "isotropic_3d", "E": YOUNG, "nu": POISSON}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=[
            {"node": int(node), "dof": "UX", "value": REFERENCE_LOAD / len(loaded_nodes)}
            for node in loaded_nodes
        ],
        analysis={
            "type": "linear_buckling",
            "method": "eigsh",
            "preload_factor": 1.0,
            "load_increments": 4,
            "maximum_factor": 1.0e8,
            "eigensolver_tolerance": 1.0e-8,
            "factor_tolerance": 1.0e-4,
        },
    )
    return model, {
        "cells_x": cells,
        "length": LENGTH,
        "width": WIDTH,
        "height": HEIGHT,
        "slenderness_length_over_height": LENGTH / HEIGHT,
        "node_count": int(len(scaled)),
        "element_count": int(len(elements)),
    }


def _row(family: str, metadata: dict[str, Any], result: Any) -> dict[str, Any]:
    solver = result.solver
    factor = float(solver["critical_factor"])
    residual = float(solver["critical_mode_residual_relative"])
    reference = _euler_reference()
    error = abs(factor * REFERENCE_LOAD - reference) / max(abs(reference), 1.0e-15)
    mode_norm = float(solver["critical_mode_norm"])
    return {
        "family": family,
        **metadata,
        "status": "PASS" if result.status == "PASS" and np.isfinite(factor) else "FAIL",
        "critical_load_qf": factor * REFERENCE_LOAD,
        "euler_reference": reference,
        "euler_relative_error": error,
        "euler_status": "PASS" if error <= EULER_RELATIVE_TOLERANCE else "FAIL",
        "critical_factor": factor,
        "eigenpair_residual_relative": residual,
        "eigenpair_residual_status": (
            "PASS" if np.isfinite(residual) and residual <= EIGENPAIR_RESIDUAL_PASS else "FAIL"
        ),
        "critical_mode_norm": mode_norm,
        "mode_finite_unit_status": "PASS"
        if np.isfinite(mode_norm) and abs(mode_norm - 1.0) <= 1.0e-12
        else "FAIL",
        "eigen_backend": solver.get("backend"),
        "eigen_formulation": solver.get("eigen_formulation"),
        "critical_bracket": solver.get("critical_bracket"),
        "preload_residual_max": max(
            (
                float(step.get("relative_residual", np.nan))
                for step in solver.get("preload_diagnostics", {}).get("increments", [])
            ),
            default=float("nan"),
        ),
    }


def _run_case(family: str, cells: int) -> dict[str, Any]:
    model, metadata = _model(family, cells)
    try:
        return _row(family, metadata, solve_model(model, enforce_policy=False))
    except Exception as exc:
        return {
            "family": family,
            **metadata,
            "status": "FAIL",
            "failure_type": type(exc).__name__,
            "failure_message": str(exc),
            "euler_status": "NOT_EVALUATED",
        }


def _artifact_digests(root: Path) -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "g08_high_order_analytical_summary.json"
    }


def _write_plots(output: Path, rows: list[dict[str, Any]], reference: float) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(8.0, 4.8))
    for family in FAMILIES:
        family_rows = [row for row in rows if row["family"] == family and row["status"] == "PASS"]
        axis.plot(
            [row["cells_x"] for row in family_rows],
            [row["critical_load_qf"] for row in family_rows],
            "o-",
            label=family,
        )
    axis.axhline(reference, color="#bc4749", linestyle="--", label="Euler")
    axis.set_xlabel("Lengthwise mesh level (cells)")
    axis.set_ylabel("Critical load")
    axis.set_title("High-order solid buckling screen")
    axis.grid(True, alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output / "euler_high_order_comparison.png", dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(8.0, 4.8))
    for family in FAMILIES:
        family_rows = [row for row in rows if row["family"] == family and row["status"] == "PASS"]
        axis.plot(
            [row["cells_x"] for row in family_rows],
            [100.0 * row["euler_relative_error"] for row in family_rows],
            "o-",
            label=family,
        )
    axis.axhline(100.0 * EULER_RELATIVE_TOLERANCE, color="#bc4749", linestyle="--", label="10% policy")
    axis.set_xlabel("Lengthwise mesh level (cells)")
    axis.set_ylabel("Euler relative error (%)")
    axis.grid(True, alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output / "euler_high_order_error.png", dpi=180)
    plt.close(figure)


def _render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# G08 High-order analytical Euler evidence",
        "",
        f"Status: **{summary['status']}**. Official G08 status remains **{summary['gate_status_unchanged']}**.",
        "",
        f"Execution source SHA: `{summary['source_sha']}`; dirty: `{summary['source_dirty']}`.",
        "",
        "## Declared benchmark",
        "",
        "The benchmark is a homogeneous isotropic fixed-free solid column with a conservative "
        "axial nodal dead load distributed over the loaded end face. Euler is used as an "
        "independent screening oracle under the declared slender-column assumptions; this is "
        "not a general 3D-solid validation oracle.",
        "",
        f"- `Pcr = pi^2 E I / (4 L^2)`; `E={YOUNG:g}`, `nu={POISSON:g}`, `L={LENGTH:g}`, "
        f"`b={WIDTH:g}`, `h={HEIGHT:g}`, `I={WIDTH * HEIGHT**3 / 12.0:.12g}`.",
        f"- Euler reference: `{summary['euler_reference']:.12g}`; declared error tolerance: `{EULER_RELATIVE_TOLERANCE:.0%}`.",
        "- Fixed-free conditions: all translations fixed at `x=0`; axial load distributed over all nodes at `x=L`.",
        "- Mesh refinement changes only the lengthwise partition; one solid layer is retained through each transverse direction.",
        "",
        "## Results",
        "",
        "| Family | Cells | Elements | QF critical load | Euler error | Eigen residual | Mode norm | Route | Euler screen |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in summary["rows"]:
        if row["status"] != "PASS":
            lines.append(
                f"| {row['family']} | {row['cells_x']} | {row.get('element_count', '-')} | - | - | - | - | FAIL | {row.get('failure_type', 'FAIL')} |"
            )
            continue
        lines.append(
            f"| {row['family']} | {row['cells_x']} | {row['element_count']} | {row['critical_load_qf']:.8g} | "
            f"{row['euler_relative_error']:.3%} | {row['eigenpair_residual_relative']:.3e} | "
            f"{row['critical_mode_norm']:.6g} | {row['status']} | {row['euler_status']} |"
        )
    lines.extend(
        [
            "",
            "![QF versus Euler](euler_high_order_comparison.png)",
            "",
            "![Euler error](euler_high_order_error.png)",
            "",
            "## Interpretation",
            "",
            "The Euler screen is evaluated independently for each family and level. A failed "
            "Euler screen is retained as a diagnostic result and is not repaired by changing "
            "the solver, eigensolver, mesh policy or tolerance. Mode norms and residuals are "
            "route checks; they do not establish physical mode-shape agreement by themselves.",
            "",
            "No family is promoted automatically by this study. The result must be read together "
            "with the existing G08 mesh, external-correlation and first-mode evidence.",
        ]
    )
    return "\n".join(lines) + "\n"


def run(output: Path, evidence_dir: Path) -> dict[str, Any]:
    source_sha, source_dirty = _git_state()
    if source_dirty:
        raise RuntimeError("High-order analytical evidence requires a clean source worktree.")
    output.mkdir(parents=True, exist_ok=True)
    rows = [_run_case(family, cells) for family in FAMILIES for cells in MESH_LEVELS]
    successful = [row for row in rows if row["status"] == "PASS"]
    for family in FAMILIES:
        family_rows = [row for row in successful if row["family"] == family]
        for previous, current in zip(family_rows, family_rows[1:]):
            current["critical_load_relative_change"] = abs(
                current["critical_load_qf"] - previous["critical_load_qf"]
            ) / max(abs(current["critical_load_qf"]), 1.0e-15)
    replay_rows = [_run_case(family, MESH_LEVELS[-1]) for family in FAMILIES]
    replay_deltas = {
        family: abs(
            next(row["critical_load_qf"] for row in replay_rows if row["family"] == family)
            - next(
                row["critical_load_qf"]
                for row in successful
                if row["family"] == family and row["cells_x"] == MESH_LEVELS[-1]
            )
        )
        for family in FAMILIES
        if any(row["family"] == family and row["status"] == "PASS" for row in replay_rows)
        and any(row["family"] == family and row["cells_x"] == MESH_LEVELS[-1] for row in successful)
    }
    all_route_pass = len(successful) == len(rows)
    all_euler_pass = all(row.get("euler_status") == "PASS" for row in successful) and all_route_pass
    all_replay_pass = len(replay_deltas) == len(FAMILIES) and all(
        delta <= REPEATABILITY_ABSOLUTE_TOLERANCE for delta in replay_deltas.values()
    )
    status = "PASS_ANALYTICAL_BOUNDED" if all_euler_pass and all_replay_pass else "PARTIAL_ANALYTICAL_SCREEN"
    family_candidates = {}
    for family in FAMILIES:
        family_rows = [row for row in rows if row["family"] == family]
        family_candidates[family] = (
            "QUALIFIED_BOUNDED"
            if len(family_rows) == len(MESH_LEVELS)
            and all(row.get("status") == "PASS" and row.get("euler_status") == "PASS" for row in family_rows)
            else "MORE_EVIDENCE_REQUIRED"
        )
    summary: dict[str, Any] = {
        "schema_version": 1,
        "evidence_id": "026-G08-HIGH-ORDER-EULER-001",
        "study_id": STUDY_ID,
        "gate": GATE,
        "status": status,
        "gate_status_unchanged": "PASS_WITH_LIMITATIONS",
        "source_sha": source_sha,
        "source_dirty": source_dirty,
        "captured_at_utc": _utc_now(),
        "solver_version": "0.2.6a0",
        "runtime": runtime_fingerprint(),
        "command": "python scripts/run_g08_high_order_analytical.py --output results/vnv_026_g08_high_order_analytical --evidence-dir qualification/0_2_6",
        "policies": {
            "euler_relative_tolerance": EULER_RELATIVE_TOLERANCE,
            "eigenpair_residual_pass": EIGENPAIR_RESIDUAL_PASS,
            "repeatability_absolute_tolerance": REPEATABILITY_ABSOLUTE_TOLERANCE,
            "tolerance_source": "Existing G08 Owner-approved bounded policy; declared before execution.",
        },
        "benchmark": {
            "formula": "pi^2 E I / (4 L^2)",
            "boundary_condition": "fixed-free",
            "young": YOUNG,
            "poisson": POISSON,
            "length": LENGTH,
            "width": WIDTH,
            "height": HEIGHT,
            "inertia": WIDTH * HEIGHT**3 / 12.0,
            "reference_load": REFERENCE_LOAD,
            "euler_reference": _euler_reference(),
            "load": "uniformly distributed nodal axial dead load on x=L",
            "assumptions": [
                "slender fixed-free column screening problem",
                "homogeneous isotropic linear elasticity",
                "first linearized tangent-instability factor",
            ],
        },
        "euler_reference": _euler_reference(),
        "families": list(FAMILIES),
        "mesh_levels": list(MESH_LEVELS),
        "rows": rows,
        "replay_final_level_absolute_deltas": replay_deltas,
        "replay_final_level_status": "PASS" if all_replay_pass else "FAIL",
        "artifact_digests": {},
        "limitations": [
            "The screening mesh retains one solid layer through each transverse direction; it is not a universal 3D Euler convergence proof.",
            "A failed analytical screen remains a diagnostic limitation and does not trigger solver changes.",
            "Only the first linearized factor and first mode route are considered; no post-buckling or multi-mode claim is made.",
            "This numerical correlation is not physical validation.",
        ],
        "promotion": {
            "automatic": False,
            "owner_review_required": True,
            "family_candidates": family_candidates,
        },
    }
    _write_plots(output, rows, summary["benchmark"]["euler_reference"])
    report_path = output / "g08_high_order_analytical_report.md"
    summary_path = output / "g08_high_order_analytical_summary.json"
    report_path.write_text(_render_report(summary), encoding="utf-8")
    summary["artifact_digests"] = _artifact_digests(output)
    summary["report_sha256"] = sha256(report_path)
    write_json_file(summary_path, summary)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    archived_report = evidence_dir / "g08_high_order_analytical_evidence.md"
    archived_json = evidence_dir / "g08_high_order_analytical_evidence.json"
    archived_report.write_text(_render_report(summary), encoding="utf-8")
    summary["artifact_digests"]["qualification/0_2_6/g08_high_order_analytical_evidence.md"] = sha256(archived_report)
    write_json_file(archived_json, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/vnv_026_g08_high_order_analytical"))
    parser.add_argument("--evidence-dir", type=Path, default=Path("qualification/0_2_6"))
    args = parser.parse_args()
    summary = run(args.output.resolve(), args.evidence_dir.resolve())
    print(
        json.dumps(
            {
                "gate": GATE,
                "status": summary["status"],
                "source_sha": summary["source_sha"],
                "source_dirty": summary["source_dirty"],
                "family_candidates": summary["promotion"]["family_candidates"],
                "replay_final_level_absolute_deltas": summary["replay_final_level_absolute_deltas"],
            },
            indent=2,
        )
    )
    return 0 if summary["status"] == "PASS_ANALYTICAL_BOUNDED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
