"""Run the orthotropic TET4 modal and Newmark verification campaign."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.orthotropic_modal_dynamic import OrthotropicModalDynamicCampaign


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results" / "VNV-ORTHOTROPIC-MODAL-NEWMARK-010"
REFERENCE = ROOT / "qualification" / "vnv" / "orthotropic_modal_newmark" / "reference"
DOCS_ASSETS = ROOT / "docs" / "assets" / "reviews"


def main() -> int:
    """Run the reproducible campaign and promote its files to controlled evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--skip-code-aster",
        action="store_true",
        help="Run only analytical and QF_solver checks; do not launch the external Docker oracle.",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    summary = OrthotropicModalDynamicCampaign(output).run(
        run_code_aster_external=not args.skip_code_aster
    )
    REFERENCE.mkdir(parents=True, exist_ok=True)
    for source in output.iterdir():
        if source.is_file():
            shutil.copy2(source, REFERENCE / source.name)
    DOCS_ASSETS.mkdir(parents=True, exist_ok=True)
    for source_name, target_name in (
        ("modal_convergence.png", "orthotropic_modal_convergence.png"),
        ("newmark_convergence.png", "orthotropic_newmark_convergence.png"),
        ("code_aster_newmark.png", "orthotropic_code_aster_newmark.png"),
    ):
        shutil.copy2(output / source_name, DOCS_ASSETS / target_name)
    print(f"{summary['study_id']}: {summary['status']} -> {output}")
    return 0 if summary["status"] == "PASS_TECHNICAL_VERIFICATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
