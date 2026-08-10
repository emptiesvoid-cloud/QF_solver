"""Run refined MITC3+ Scordelis-Lo and pinched-cylinder benchmarks."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.mitc3_refined import Mitc3RefinedShellCampaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results") / "VNV-MITC3-REFINED-SHELL-H20K",
    )
    args = parser.parse_args()
    summary = Mitc3RefinedShellCampaign(args.output).run()
    print(f"MITC3+ refined shell V&V: {summary['status']}")
    for key, case in summary["cases"].items():
        print(
            f"{key}: elements={case['mesh']['elements']} "
            f"error={100.0 * case['relative_error']:.6f}% "
            f"elapsed={case['solve_elapsed_seconds']:.2f}s"
        )
    print(f"evidence: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
