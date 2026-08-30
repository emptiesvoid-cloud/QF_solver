"""Run the controlled HEX20/C3D20 buckling-correlation rescue study.

The study records a narrowly scoped verification-harness correction and then
replays one- and two-cell HEX20 models against CalculiX. It does not change
the QF Solver buckling formulation or close the 026-G08 gate.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
# ruff: noqa: E402

import numpy as np

from solveur.api import solve_model
from solveur.io.manifest import runtime_fingerprint, sha256, write_json_file
from solveur.verification.calculix_buckling_025 import CORRELATION_TOLERANCE, run_campaign
from solveur.verification.calculix_total_lagrangian import parse_last_frd_displacement
from solveur.verification.robustness_nonlinear_solids import _buckling_mesh_model


GATE = "026-G08"
STUDY_ID = "VNV-G08-HEX20-CALCULIX-RESCUE-001"
IMAGE = "qf-solver/calculix-nafems13h:2.20"
CELLS = (1, 2)
REPLAY_ABSOLUTE_TOLERANCE = 1.0e-12


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


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _mode_comparison(model: Any, qf_result: Any, frd_path: Path) -> dict[str, Any]:
    qf_mode = np.asarray(qf_result.displacements, dtype=float).reshape((-1, 3))
    calculix_mode = parse_last_frd_displacement(frd_path, model.node_count)
    qf_vector = qf_mode.reshape(-1)
    calculix_vector = calculix_mode.reshape(-1)
    qf_norm = float(np.linalg.norm(qf_vector))
    calculix_norm = float(np.linalg.norm(calculix_vector))
    if not np.isfinite(qf_norm) or not np.isfinite(calculix_norm) or qf_norm <= 0.0 or calculix_norm <= 0.0:
        raise ValueError("HEX20 mode comparison requires two finite non-zero mode vectors.")
    cosine = float(np.dot(qf_vector, calculix_vector) / (qf_norm * calculix_norm))
    return {
        "status": "RECORDED_NO_OWNER_MAC_THRESHOLD",
        "raw_cosine": cosine,
        "sign_alignment": "SAME" if cosine >= 0.0 else "OPPOSITE_ARBITRARY_EIGENVECTOR_SIGN",
        "sign_aligned_cosine": abs(cosine),
        "mac": cosine * cosine,
        "qf_norm": qf_norm,
        "calculix_norm": calculix_norm,
        "reference": "CalculiX first eigenmode from the final FRD DISP block",
        "policy": "The G08 contract defines MAC only when a compatible reference exists; no external MAC threshold is invented here.",
    }


def _run_level(output: Path, cells: int) -> dict[str, Any]:
    model = _buckling_mesh_model("HEX20", cells)
    qf_result = solve_model(model, enforce_policy=False)
    summary = run_campaign(output, element_types=("HEX20",), cells=cells, modes=1, execute=True)
    row = summary["rows"][0]
    level: dict[str, Any] = {
        "cells": cells,
        "node_count": model.node_count,
        "element_count": len(model.elements),
        "qf_critical_factor": float(row["qf_critical_factor"]),
        "qf_mode_residual_relative": float(row["qf_mode_residual_relative"]),
        "calculix_critical_factor": row.get("calculix_critical_factor"),
        "relative_difference": row.get("relative_difference"),
        "correlation_tolerance": CORRELATION_TOLERANCE,
        "status": row["status"],
        "deck_sha256": row["deck_sha256"],
        "provenance": summary["provenance"],
        "calculix_summary": _relative(output / "summary.json"),
        "deck": _relative(output / "hex20" / "buckling.inp"),
        "dat": _relative(output / "hex20" / "buckling.dat"),
        "frd": _relative(output / "hex20" / "buckling.frd"),
        "calculix_log": _relative(output / "hex20" / "calculix.log"),
    }
    if row["status"] != "PASS":
        level["error_type"] = row.get("error_type")
        level["error"] = row.get("error")
        level["mode_comparison"] = {"status": "NOT_AVAILABLE_EXTERNAL_EXECUTION_NOT_PASS"}
        return level
    level["mode_comparison"] = _mode_comparison(model, qf_result, output / "hex20" / "buckling.frd")
    return level


def _artifact_digests(root: Path) -> dict[str, str]:
    return {
        _relative(path): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "g08_hex20_calculix_rescue_summary.json"
    }


def _render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# G08 HEX20 CalculiX Rescue Evidence",
        "",
        f"Status: **{summary['status']}**; official G08 status remains **{summary['gate_status_unchanged']}**.",
        "",
        f"Execution source SHA: `{summary['source_sha']}`; dirty: `{summary['source_dirty']}`.",
        "",
        "## Root-cause correction",
        "",
        "The buckling deck writer emitted a C3D20 continuation line with a leading empty field. "
        "The corrected writer starts the continuation with the next node, matching the existing "
        "HEX20 static writer and CalculiX input contract. No FEM formulation, eigensolver or "
        "numerical solver code was changed.",
        "",
        "| Mesh | QF factor | CalculiX factor | Relative difference | Replay difference | Correlation |",
        "|---:|---:|---:|---:|---:|---|",
    ]
    for item in summary["mesh_levels"]:
        first = item["first"]
        replay = item["replay"]
        lines.append(
            f"| {first['cells']} | {first['qf_critical_factor']:.10g} | "
            f"{first['calculix_critical_factor']:.10g} | {first['relative_difference']:.6%} | "
            f"{item['replay_factor_absolute_difference']:.3e} | {first['status']} |"
        )
        if replay["status"] != "PASS":
            lines.append(f"| {first['cells']} replay | - | - | - | - | {replay['status']} |")
    lines.extend(
        [
            "",
            "## Mode comparison",
            "",
            "The FRD first eigenmode is compared after arbitrary eigenvector sign alignment. "
            "The G08 contract has no external MAC acceptance threshold, so these values are "
            "reported diagnostically and are not converted into an invented PASS criterion.",
            "",
            "| Mesh | Raw cosine | Sign-aligned cosine | MAC | Status |",
            "|---:|---:|---:|---:|---|",
        ]
    )
    for item in summary["mesh_levels"]:
        mode = item["first"]["mode_comparison"]
        lines.append(
            f"| {item['cells']} | {mode['raw_cosine']:.9f} | {mode['sign_aligned_cosine']:.9f} | "
            f"{mode['mac']:.9f} | {mode['status']} |"
        )
    lines.extend(
        [
            "",
            "## Scope and limitations",
            "",
            "- Same QF HEX20 mesh factory, C3D20 mapping, homogeneous isotropic material and nodal dead load.",
            "- One-cell and two-cell meshes were executed, each with a deterministic replay.",
            "- The existing 10% correlation band was declared before execution and is reused unchanged.",
            "- This is numerical external correlation only; it is not physical validation.",
            "- The official G08 family decision and gate remain unchanged pending Owner review.",
            "- No post-buckling, multi-mode or general high-order qualification claim is added.",
        ]
    )
    return "\n".join(lines) + "\n"


def run(output: Path, evidence_dir: Path) -> dict[str, Any]:
    source_sha, source_dirty = _git_state()
    if source_dirty:
        raise RuntimeError("HEX20 CalculiX rescue requires a clean source worktree before execution.")
    output.mkdir(parents=True, exist_ok=True)
    mesh_levels: list[dict[str, Any]] = []
    for cells in CELLS:
        first = _run_level(output / f"cells{cells}", cells)
        replay = _run_level(output / f"cells{cells}_replay", cells)
        first_factor = first.get("calculix_critical_factor")
        replay_factor = replay.get("calculix_critical_factor")
        repeat_difference = (
            abs(float(first_factor) - float(replay_factor))
            if first_factor is not None and replay_factor is not None
            else None
        )
        mesh_levels.append(
            {
                "cells": cells,
                "first": first,
                "replay": replay,
                "replay_factor_absolute_difference": repeat_difference,
                "replay_within_tolerance": repeat_difference is not None
                and repeat_difference <= REPLAY_ABSOLUTE_TOLERANCE,
            }
        )
    first_rows = [item["first"] for item in mesh_levels]
    replay_rows = [item["replay"] for item in mesh_levels]
    all_pass = all(row["status"] == "PASS" for row in [*first_rows, *replay_rows])
    all_reproducible = all(item["replay_within_tolerance"] for item in mesh_levels)
    status = "PASS_EXTERNAL_CORRELATION_BOUNDED" if all_pass and all_reproducible else "BLOCKED_EXTERNAL_TOOL"
    summary: dict[str, Any] = {
        "schema_version": 1,
        "evidence_id": "026-G08-HEX20-CALCULIX-RESCUE-001",
        "study_id": STUDY_ID,
        "gate": GATE,
        "status": status,
        "gate_status_unchanged": "PASS_WITH_LIMITATIONS",
        "source_sha": source_sha,
        "source_dirty": source_dirty,
        "captured_at_utc": _utc_now(),
        "solver_version": "0.2.6a0",
        "runtime": runtime_fingerprint(),
        "command": "python scripts/run_g08_hex20_calculix_rescue.py --output results/vnv_026_g08_hex20_calculix_rescue --evidence-dir qualification/0_2_6",
        "root_cause": {
            "classification": "DECK_GENERATION",
            "defect": "C3D20 continuation line started with an empty field.",
            "correction": "Continuation now starts with the next node, matching CalculiX input syntax and the existing HEX20 static writer.",
            "functional_solver_code_changed": False,
            "verification_infrastructure_changed": True,
        },
        "external_solver": {"name": "CalculiX", "version": "2.20", "image": IMAGE, "element": "C3D20"},
        "policies": {
            "correlation_tolerance": CORRELATION_TOLERANCE,
            "correlation_tolerance_source": "Existing CORRELATION_TOLERANCE in calculix_buckling_025.py; unchanged.",
            "replay_absolute_tolerance": REPLAY_ABSOLUTE_TOLERANCE,
            "mode_policy": "Diagnostic sign-aligned comparison; no external MAC threshold exists in the G08 contract.",
        },
        "scope": {
            "families": ["HEX20"],
            "calculix_element": "C3D20",
            "analysis": "first linearized tangent-instability factor and first mode",
            "material": "homogeneous isotropic linear elasticity",
            "loads": "nodal dead loads",
            "route": "same QF model factory and CalculiX external deck",
            "mesh_levels": list(CELLS),
        },
        "mesh_levels": mesh_levels,
        "external_result": "PASS_EXTERNAL_CORRELATION_BOUNDED" if status.startswith("PASS") else status,
        "limitations": [
            "This rescue corrects only external HEX20 C3D20 deck generation.",
            "The historical G08 Owner closeout is not rewritten and the official gate remains PASS_WITH_LIMITATIONS.",
            "HEX20 mesh sensitivity and the existing bounded family decision remain subject to Owner review.",
            "No independent high-order analytical oracle or Code_Aster equivalent is added by this study.",
            "No post-buckling, multi-mode or physical-validation claim is made.",
        ],
    }
    summary_path = output / "g08_hex20_calculix_rescue_summary.json"
    report_path = output / "g08_hex20_calculix_rescue_report.md"
    write_json_file(summary_path, summary)
    report_path.write_text(_render_report(summary), encoding="utf-8")
    summary["artifact_digests"] = _artifact_digests(output)
    summary["report_sha256"] = sha256(report_path)
    write_json_file(summary_path, summary)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    archived_report = evidence_dir / "g08_hex20_calculix_rescue_evidence.md"
    archived_json = evidence_dir / "g08_hex20_calculix_rescue_evidence.json"
    archived_report.write_text(_render_report(summary), encoding="utf-8")
    summary["artifact_digests"]["qualification/0_2_6/g08_hex20_calculix_rescue_evidence.md"] = sha256(archived_report)
    write_json_file(archived_json, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/vnv_026_g08_hex20_calculix_rescue"))
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
                "mesh_levels": [
                    {
                        "cells": item["cells"],
                        "relative_difference": item["first"]["relative_difference"],
                        "replay_difference": item["replay_factor_absolute_difference"],
                    }
                    for item in summary["mesh_levels"]
                ],
            },
            indent=2,
        )
    )
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION_BOUNDED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
