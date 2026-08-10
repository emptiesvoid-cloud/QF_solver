"""Run Code_Aster correlations for the three additional contact models."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from solveur.verification.code_aster_contact_additional import (
    CodeAsterAdditionalContactCampaign,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="results/VNV-CONTACT-CODEASTER-ADDITIONAL-009",
    )
    parser.add_argument(
        "--digest",
        default="qualification/external_reference_digests/contact_code_aster_additional.json",
    )
    parser.add_argument("--tet4-grid", nargs=3, type=int, metavar=("NX", "NY", "NZ"), default=(8, 4, 4))
    parser.add_argument("--study-id", default=None)
    parser.add_argument("--reuse-existing", action="store_true")
    arguments = parser.parse_args()
    output = Path(arguments.output).resolve()
    if arguments.reuse_existing:
        summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    else:
        summary = CodeAsterAdditionalContactCampaign(
            output,
            tet4_grid=tuple(arguments.tet4_grid),
            study_id=arguments.study_id,
        ).run()
    digest = {
        "study_id": summary["study_id"],
        "status": summary["status"],
        "maturity": summary["maturity"],
        "external_solver": summary["external_solver"],
        "diagnostic_solver": summary["diagnostic_solver"],
        "load_factors": summary["load_factors"],
        "cases": [
            {
                key: case[key]
                for key in (
                    "id",
                    "nodes",
                    "elements",
                    "channels",
                    "displacement_curve_error",
                    "gap_curve_error",
                    "diagnostics",
                    "checks",
                )
            }
            for case in summary["cases"]
        ],
        "checks": summary["checks"],
        "limitations": summary["limitations"],
        "evidence_manifest_sha256": hashlib.sha256(
            (output / "vnv_manifest.json").read_bytes()
        ).hexdigest(),
    }
    digest_path = Path(arguments.digest)
    digest_path.parent.mkdir(parents=True, exist_ok=True)
    digest_path.write_text(
        json.dumps(digest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    published_name = (
        "contact_code_aster_additional_h10k_curves.png"
        if "H10K" in str(summary["study_id"])
        else "contact_code_aster_additional_curves.png"
    )
    shutil.copy2(
        output / "contact_code_aster_curves.png",
        ROOT / "docs" / "assets" / "reviews" / published_name,
    )
    print(f"{summary['study_id']}: {summary['status']}")
    return (
        0
        if summary["status"]
        in {"PASS_EXTERNAL_CORRELATION", "PASS_WITH_EXTERNAL_WARNING"}
        else 3
    )


if __name__ == "__main__":
    raise SystemExit(main())
