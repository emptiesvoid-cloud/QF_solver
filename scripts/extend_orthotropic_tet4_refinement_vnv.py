"""Extend an existing orthotropic TET4 refinement campaign by one level."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from solveur.io.manifest import write_json_file
from solveur.verification.orthotropic_convergence import OrthotropicStructuralConvergenceCampaign, _relative
from solveur.verification.vnv_manifest import write_vnv_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--mesh-size", type=float, default=0.02)
    parser.add_argument("--study-id", default="VNV-ORTHOTROPIC-SOLID-CONVERGENCE-006")
    parser.add_argument(
        "--solver-method",
        choices=("direct", "cg", "large_cg"),
        default="direct",
        help="Linear solver for the added TET4 level; large_cg uses vectorized TET4 assembly.",
    )
    args = parser.parse_args()
    campaign_dir = args.campaign.resolve()
    summary_path = campaign_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    campaign = OrthotropicStructuralConvergenceCampaign(campaign_dir, solver_method=args.solver_method)
    campaign.study_id = args.study_id
    campaign.full_result_element_limit = int(summary["problem"]["full_result_element_limit"])
    row = campaign._solve("TET4", args.mesh_size, f"tet4_h{len(summary['families']['TET4']) + 1}")
    reference = summary["reference"]
    row["tip_error"] = _relative(float(row["tip_uz_m"]), float(reference["tip_uz_m"]))
    row["energy_error"] = _relative(float(row["strain_energy_j"]), float(reference["strain_energy_j"]))
    summary["study_id"] = args.study_id
    summary["families"]["TET4"].append(row)
    summary["checks"] = campaign._checks(summary["families"])
    summary["status"] = "PASS_TECHNICAL_VERIFICATION" if all(check["status"] == "PASS" for check in summary["checks"]) else "FAIL"
    summary["problem"]["tet4_extended_targets"] = "approximately 5,000, 10,000 and finer summary-only levels including h=0.020 m"
    write_json_file(summary_path, summary)
    campaign._plot(summary)
    campaign._write_report(summary)
    write_vnv_manifest(campaign_dir, args.study_id)
    print(f"{args.study_id}: {summary['status']}")
    print(f"TET4 h={args.mesh_size}: tip_error={100 * row['tip_error']:.6f}% energy_error={100 * row['energy_error']:.6f}%")
    return 0 if summary["status"] == "PASS_TECHNICAL_VERIFICATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
