"""Run the three additional bounded-contact models requested at Owner review."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from solveur.verification.contact_additional_models import AdditionalContactModelsCampaign


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/VNV-CONTACT-ADDITIONAL-MODELS-008"),
    )
    parser.add_argument(
        "--digest",
        type=Path,
        default=Path("qualification/external_reference_digests/contact_additional_models.json"),
    )
    parser.add_argument("--reuse-existing", action="store_true")
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    if arguments.reuse_existing:
        summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    else:
        summary = AdditionalContactModelsCampaign(output).run()
    digest = {
        "campaign_id": summary["campaign_id"],
        "status": summary["status"],
        "maturity": summary["maturity"],
        "cases": [
            {
                key: case[key]
                for key in (
                    "id",
                    "nodes",
                    "elements",
                    "contacts",
                    "gaps_m",
                    "pressures_n",
                    "selected_faces",
                    "max_displacement_m",
                    "checks",
                )
            }
            for case in summary["cases"]
        ],
        "checks": summary["checks"],
        "limitations": summary["limitations"],
        "evidence_manifest_sha256": hashlib.sha256((output / "vnv_manifest.json").read_bytes()).hexdigest(),
    }
    arguments.digest.parent.mkdir(parents=True, exist_ok=True)
    arguments.digest.write_text(json.dumps(digest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    published = ROOT / "docs" / "assets" / "reviews" / "contact_additional_models.png"
    shutil.copy2(output / "additional_contact_models.png", published)
    print(f"{summary['campaign_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_INTERNAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
