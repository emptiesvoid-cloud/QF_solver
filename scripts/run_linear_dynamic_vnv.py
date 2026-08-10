"""Run reproducible modal, Newmark and harmonic V&V by element family."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.dynamic_family_campaign import (
    SUPPORTED_FAMILIES,
    LinearDynamicFamilyCampaign,
)


def main() -> int:
    """Run one family or all supported linear dynamic families."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=(*SUPPORTED_FAMILIES, "all"), default="all")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("qualification") / "vnv" / "linear_dynamic_families",
    )
    args = parser.parse_args()
    families = SUPPORTED_FAMILIES if args.family == "all" else (args.family,)
    exit_code = 0
    for family in families:
        summary = LinearDynamicFamilyCampaign(family, args.output / family.lower()).run()
        print(f"{family}: {summary['status']}")
        exit_code |= int(summary["status"] != "PASS")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
