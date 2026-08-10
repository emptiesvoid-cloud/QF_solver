"""Run two additional orthotropic stress-field studies."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from solveur.verification.orthotropic_additional_stress import AdditionalOrthotropicStressCampaign


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/VNV-ORTHOTROPIC-ADDITIONAL-STRESS-006"),
    )
    parser.add_argument(
        "--digest",
        type=Path,
        default=Path("qualification/external_reference_digests/orthotropic_additional_stress.json"),
    )
    parser.add_argument("--reuse-existing", action="store_true")
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    if arguments.reuse_existing:
        summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    else:
        summary = AdditionalOrthotropicStressCampaign(output).run()
    digest = {
        "campaign_id": summary["campaign_id"],
        "status": summary["status"],
        "maturity": summary["maturity"],
        "observable": summary["observable"],
        "blocking_oracle": summary["blocking_oracle"],
        "cases": [
            {
                "id": case["id"],
                "levels": case["levels"],
                "assessment": case["assessment"],
                "same_mesh_code_aster_status": case["same_mesh_code_aster_status"],
            }
            for case in summary["cases"]
        ],
        "limitations": summary["limitations"],
        "evidence_manifest_sha256": hashlib.sha256((output / "vnv_manifest.json").read_bytes()).hexdigest(),
    }
    arguments.digest.parent.mkdir(parents=True, exist_ok=True)
    arguments.digest.write_text(json.dumps(digest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for name in ("additional_stress_convergence.png", "additional_stress_fields.png"):
        shutil.copy2(output / name, ROOT / "docs" / "assets" / "reviews" / name)
    print(f"{summary['campaign_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_STRESS_ACCEPTANCE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
