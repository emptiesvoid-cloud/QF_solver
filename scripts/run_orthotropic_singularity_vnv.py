"""Run the controlled orthotropic stress-concentration V&V campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from solveur.verification.orthotropic_singularity_vnv import OrthotropicSingularityStressCampaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("qualification/vnv/orthotropic_singular_stress/reference"),
    )
    parser.add_argument(
        "--digest",
        type=Path,
        default=Path(
            "qualification/external_reference_digests/"
            "orthotropic_singular_stress_h8.json"
        ),
    )
    parser.add_argument(
        "--reuse-existing",
        action="store_true",
        help="Reapply the acceptance policy to existing numerical evidence.",
    )
    arguments = parser.parse_args()
    campaign = OrthotropicSingularityStressCampaign(arguments.output)
    summary = campaign.reassess_existing() if arguments.reuse_existing else campaign.run()
    manifest = arguments.output.resolve() / "vnv_manifest.json"
    digest = {
        key: summary[key]
        for key in (
            "study_id",
            "status",
            "maturity",
            "acceptance_basis",
            "stress_recovery",
            "acceptance_policy_revision",
            "blocking_external_oracle",
            "diagnostic_external_oracle",
            "limitations",
        )
    }
    digest["cases"] = [
        {
            "id": case["id"],
            "classification": case["classification"],
            "levels": len(case["levels"]),
            "fine_mesh": {
                "mesh_size": case["levels"][-1]["mesh_size"],
                "nodes": case["levels"][-1]["nodes"],
                "elements": case["levels"][-1]["elements"],
            },
            "assessment": case["assessment"],
            "fine_code_aster_check": case["same_mesh_code_aster_checks"][-1],
            "fine_calculix_nodal_check": case["secondary_calculix_nodal_checks"][-1],
        }
        for case in summary["cases"]
    ]
    digest["evidence_manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    arguments.digest.parent.mkdir(parents=True, exist_ok=True)
    arguments.digest.write_text(
        json.dumps(digest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"{summary['study_id']}: {summary['status']}")
    print(f"digest: {arguments.digest.resolve()}")
    return 0 if summary["status"] == "PASS_STRESS_ACCEPTANCE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
