"""Run the pinned MITC3+/Code_Aster DKT dynamic correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_mitc3_dynamic import CodeAsterMitc3DynamicsCampaign


def main() -> int:
    """Run the same-mesh modal, Newmark and harmonic correlation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results") / CodeAsterMitc3DynamicsCampaign.study_id,
    )
    parser.add_argument("--nx", type=int, default=16)
    parser.add_argument("--ny", type=int, default=4)
    args = parser.parse_args()
    summary = CodeAsterMitc3DynamicsCampaign(args.output, nx=args.nx, ny=args.ny).run()
    print(f"{summary['study_id']}: {summary['status']}")
    print(f"evidence: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
