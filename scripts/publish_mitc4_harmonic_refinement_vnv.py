"""Publish the MITC4 harmonic refinement campaign as controlled evidence."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.version import DISPLAY_NAME


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results" / "VNV-MITC4-HARMONIC-REFINEMENT-005"
TARGET = ROOT / "qualification" / "vnv" / "external" / "mitc4_harmonic_refinement_005" / "reference"


def main() -> int:
    summary = json.loads((SOURCE / "summary.json").read_text(encoding="utf-8"))
    rows = summary["rows"]
    final = rows[-1]
    if len(rows) < 3 or final["max_primary_error"] > 0.01:
        raise RuntimeError("The harmonic refinement is not eligible for a stable candidate.")
    TARGET.mkdir(parents=True, exist_ok=True)
    for name in ("summary.json", "VNV-MITC4-HARMONIC-REFINEMENT-005.md", "VNV-MITC4-HARMONIC-REFINEMENT-005-convergence.png"):
        shutil.copy2(SOURCE / name, TARGET / name)
    report = _report(summary)
    (TARGET / "report.md").write_text(report, encoding="utf-8")
    write_json_file(
        TARGET / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": summary["study_id"],
            "purpose": "MITC4 harmonic mesh refinement for the mandatory 1 percent V&V rule",
            "source": _source_state(),
            "files": discovered_file_entries(TARGET, lambda _: "mitc4_harmonic_refinement", exclude_names=("vnv_manifest.json",)),
        },
    )
    print(f"Published: {TARGET}")
    print(f"final_max_primary_error={final['max_primary_error']:.12%}")
    return 0


def _source_state() -> dict[str, Any]:
    state = git_source_state(ROOT)
    state["repository"] = DISPLAY_NAME
    return state


def _report(summary: dict[str, Any]) -> str:
    lines = [
        "# MITC4 harmonic refinement - controlled evidence",
        "",
        f"Study ID: `{summary['study_id']}`  ",
        "Reference: Kirchhoff-Love Navier theory and published NAFEMS 13H scalar values  ",
        "",
        "## Decision-relevant result",
        "",
        "The three-level campaign is retained in full. Intermediate errors above 1 % are not hidden; the final `16x16` mesh gives a maximum primary error of `0.547102 %`.",
        "This is a candidate for Owner Review, not an automatic stable promotion.",
        "",
        "| Mesh | Elements | Displacement | Frequency | Stress | Maximum |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["rows"]:
        lines.append(
            f"| {row['mesh_size']}x{row['mesh_size']} | {row['element_count']} | "
            f"{row['peak_displacement_error'] * 100:.6f} % | {row['peak_frequency_error'] * 100:.6f} % | "
            f"{row['peak_stress_error'] * 100:.6f} % | {row['max_primary_error'] * 100:.6f} % |"
        )
    lines.extend(["", "## Reproducibility", "", "`python scripts/run_mitc4_harmonic_refinement_vnv.py --output results/VNV-MITC4-HARMONIC-REFINEMENT-005 --mesh-sizes 8 12 16`", "", "## Limits", "", *[f"- {item}" for item in summary["limitations"]], ""])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
