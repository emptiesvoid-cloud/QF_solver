"""Run the TET10 cantilever interior stress probe correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_tet10_stress_probe import (
    CodeAsterTet10CantileverStressProbeCampaign,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("qualification")
        / "maturity_evidence_0_2_1"
        / "tet10_stress_probe_cantilever_code_aster",
    )
    args = parser.parse_args()
    summary = CodeAsterTet10CantileverStressProbeCampaign(args.output).run()
    print(f"{summary['study_id']}: {summary['status']}")
    print(f"evidence: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())

