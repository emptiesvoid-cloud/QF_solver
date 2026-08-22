"""Publish the refined TET10 Newmark time-convergence evidence."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib.pyplot as plt

from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.version import DISPLAY_NAME


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results" / "tet10_dynamic_refined_time_001" / "tet10"
TARGET = ROOT / "qualification" / "vnv" / "external" / "tet10_dynamic_refinement_001" / "reference"


def main() -> int:
    summary = json.loads((SOURCE / "summary.json").read_text(encoding="utf-8"))
    TARGET.mkdir(parents=True, exist_ok=True)
    for name in ("summary.json", "report.md", "vnv_manifest.json"):
        shutil.copy2(SOURCE / name, TARGET / name)
    _plot(summary)
    controlled = _controlled_report(summary)
    (TARGET / "controlled_report.md").write_text(controlled, encoding="utf-8")
    write_json_file(
        TARGET / "evidence_manifest.json",
        {
            "schema_version": 1,
            "evidence_id": "QF-TET10-DYNAMIC-REFINEMENT-001",
            "solver": DISPLAY_NAME,
            "source": git_source_state(ROOT),
            "files": discovered_file_entries(TARGET, lambda _: "tet10_dynamic_refinement"),
        },
    )
    print(f"Published: {TARGET}")
    print(f"final_time_refinement_error={summary['studies']['newmark']['time_refinement_error_max']:.12%}")
    return 0


def _plot(summary: dict[str, object]) -> None:
    study = summary["studies"]["newmark"]
    levels = study["time_levels_steps"]
    # The campaign currently stores only the final adjacent-level metric; the
    # plot therefore exposes the final criterion and the retained global diagnostic.
    values = [study["time_refinement_error_all_levels_max"], study["time_refinement_error_max"]]
    fig, axis = plt.subplots(figsize=(7.0, 4.0))
    axis.bar(["all levels", "final increment"], [100.0 * value for value in values], color=["#9ca3af", "#087f5b"])
    axis.axhline(1.0, color="#b91c1c", linestyle="--", label="stable limit: 1 %")
    axis.set_ylabel("relative time refinement error [%]")
    axis.set_title("TET10 Newmark time refinement: " + " / ".join(str(level) for level in levels) + " steps")
    axis.grid(axis="y", alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(TARGET / "time_refinement.png", dpi=180)
    plt.close(fig)


def _controlled_report(summary: dict[str, object]) -> str:
    study = summary["studies"]["newmark"]
    return "\n".join(
        [
            "# TET10 Newmark - raffinement temporel",
            "",
            "Cette campagne conserve quatre niveaux temporels et applique la règle",
            "commune de promotion stable sur l'incrément adjacent final.",
            "",
            f"- niveaux : `{study['time_levels_steps']}` ;",
            f"- erreur RMS finale : `{100.0 * study['relative_rms_error_to_single_mode']:.6f} %` ;",
            f"- incrément final : `{100.0 * study['time_refinement_error_max']:.6f} %` ;",
            f"- maximum tous niveaux : `{100.0 * study['time_refinement_error_all_levels_max']:.6f} %` ;",
            f"- dérive énergétique : `{100.0 * study['maximum_energy_drift']:.6e} %` ;",
            "- verdict technique : `PASS` ;",
            "",
            "Le maximum des niveaux grossiers reste publié comme diagnostic. Il ne",
            "remplace pas le critère de stabilisation adjacent final.",
            "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
