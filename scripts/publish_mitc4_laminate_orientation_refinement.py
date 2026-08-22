"""Publish the 192x96 oblique laminate refinement as controlled evidence."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.version import DISPLAY_NAME


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results" / "VNV-COMP-CURVED-ORIENTATION-008-R1-192"
TARGET = ROOT / "qualification" / "vnv" / "external" / "calculix_curved_orientation_refinement_192" / "reference"


def main() -> int:
    summary = json.loads((SOURCE / "summary.json").read_text(encoding="utf-8"))
    TARGET.mkdir(parents=True, exist_ok=True)
    for name in ("summary.json", "report.md", "curved_orientation_correlation.png", "curved_orientation_deformation.png"):
        shutil.copy2(SOURCE / name, TARGET / name)
    report = _report(summary)
    (TARGET / "controlled_report.md").write_text(report, encoding="utf-8")
    write_json_file(
        TARGET / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": summary["study_id"] + "-R1-192",
            "purpose": "oblique curved laminate refinement; values above 1 percent remain a stable gate blocker",
            "source": _source_state(),
            "files": discovered_file_entries(TARGET, lambda _: "mitc4_laminate_orientation_refinement", exclude_names=("vnv_manifest.json",)),
        },
    )
    print(f"Published: {TARGET}")
    print(f"fine_vector_difference={summary['rows'][-1]['vector_difference']:.12%}")
    return 0


def _source_state() -> dict[str, Any]:
    state = git_source_state(ROOT)
    state["repository"] = DISPLAY_NAME
    return state


def _report(summary: dict[str, Any]) -> str:
    lines = [
        "# MITC4 oblique curved laminate refinement",
        "",
        "The 192x96 refinement is retained as a negative result for stable promotion.",
        "The final QF_solver/CalculiX vector difference remains above 1 percent, so the scope stays bounded.",
        "",
        "| Mesh | Elements | Vector difference | UZ difference | QF increment | CalculiX increment |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["rows"]:
        lines.append(
            f"| {row['nx']}x{row['ny']} | {row['elements']} | {row['vector_difference'] * 100:.6f} % | "
            f"{row['uz_difference'] * 100:.6f} % | {row.get('qf_final_mesh_increment', '')} | {row.get('calculix_final_mesh_increment', '')} |"
        )
    lines.extend([
        "",
        f"Final vector difference: `{summary['rows'][-1]['vector_difference'] * 100:.6f} %`.",
        "The value is not treated as a primary stable candidate because it exceeds the mandatory 1 percent limit.",
        "",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
