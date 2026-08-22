"""Publish the fixed 48x48 MITC4 modal refinement as controlled evidence."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.version import DISPLAY_NAME


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results" / "VNV-MITC4-MODAL-REFINEMENT-048"
TARGET = ROOT / "qualification" / "vnv" / "external" / "code_aster_modal_refinement_048" / "reference"
PDF = ROOT / "output" / "pdf" / "mitc4_modal_refinement_owner_review.pdf"
STUDY_ID = "VNV-MITC4-MODAL-REFINEMENT-048"


def main() -> int:
    summary = json.loads((SOURCE / "summary.json").read_text(encoding="utf-8"))
    if summary["status"] != "PASS_EXTERNAL_CORRELATION":
        raise RuntimeError(f"Unexpected modal status: {summary['status']}")
    max_error = max(summary["metrics"]["qf_code_aster_frequency_differences"])
    if max_error > 0.01:
        raise RuntimeError(f"Modal refinement remains above the 1 percent rule: {max_error:.6%}")
    TARGET.mkdir(parents=True, exist_ok=True)
    names = (
        "summary.json",
        "code_aster_modal_raw.json",
        f"{summary['study_id']}-frequencies.png",
        f"{summary['study_id']}-modes.png",
        f"{summary['study_id']}.md",
    )
    for name in names:
        shutil.copy2(SOURCE / name, TARGET / name)
    report = _report(summary)
    (TARGET / "report.md").write_text(report, encoding="utf-8")
    write_json_file(
        TARGET / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "purpose": "controlled MITC4 modal refinement for the 1 percent V&V rule",
            "source": _source_state(),
            "files": discovered_file_entries(TARGET, lambda _: "mitc4_modal_refinement"),
        },
    )
    print(f"Published: {TARGET}")
    print(f"max_frequency_error={max_error:.12%}")
    return 0


def _source_state() -> dict[str, Any]:
    state = git_source_state(ROOT)
    state["repository"] = DISPLAY_NAME
    return state


def _report(summary: dict[str, Any]) -> str:
    errors = summary["metrics"]["qf_code_aster_frequency_differences"]
    rows = []
    for index, (order, qf, code_aster, error) in enumerate(
        zip(
            summary["mode_orders"],
            summary["frequencies_hz"]["qf_solver"],
            summary["frequencies_hz"]["code_aster"],
            errors,
            strict=True,
        ),
        start=1,
    ):
        rows.append(
            f"| {index} | ({order[0]},{order[1]}) | {qf:.6f} | {code_aster:.6f} | {error * 100:.6f} % |"
        )
    max_error = max(errors)
    return "\n".join(
        [
            "# MITC4 modal refinement - 48x48",
            "",
            f"Study ID: `{STUDY_ID}`  ",
            "Status: `PASS_EXTERNAL_CORRELATION`  ",
            "Reference: Code_Aster 18.1.0 DKQ, same mesh and boundary conditions  ",
            "",
            "## Decision-relevant result",
            "",
            f"The maximum QF_solver/Code_Aster frequency difference is **{max_error * 100:.6f} %**, "
            "below the mandatory 1 % limit for a stable promotion candidate.",
            "The result is evidence only: the maturity matrix is not modified until a dated Owner Review explicitly targets `stable`.",
            "",
            "## Numerical controls",
            "",
            f"- Mesh: `{summary['model']['mesh'][0]} x {summary['model']['mesh'][1]}` QUAD4.",
            f"- Modes compared: `{summary['model']['compared_mode_count']}`.",
            f"- Maximum QF modal residual: `{summary['metrics']['qf_max_relative_residual']:.3e}`.",
            f"- Mass orthogonality error: `{summary['metrics']['qf_mass_orthogonality_error']:.3e}`.",
            f"- Stiffness orthogonality error: `{summary['metrics']['qf_stiffness_orthogonality_error']:.3e}`.",
            "",
            "## Frequencies",
            "",
            "| Mode | Family | QF_solver [Hz] | Code_Aster [Hz] | Difference |",
            "|---:|:---:|---:|---:|---:|",
            *rows,
            "",
            "## Limits",
            "",
            "This comparison is for a thin, flat, isotropic, simply supported plate. It does not close free-free rigid modes, curved shells, damping, nonlinear dynamics or laminates.",
            "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
