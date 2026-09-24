from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# This repository uses a src/ layout; make direct script execution work from
# the repository checkout without relying on an editable installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from solveur.verification.j2_multifamily_performance import J2MultiFamilyPerformanceCampaign  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the frozen WP13 R2 four-family J2 performance campaign.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("qualification/0_2_9/wp13_r2_multifamily/raw"),
    )
    args = parser.parse_args()
    result = J2MultiFamilyPerformanceCampaign(args.output_dir).run()
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS_INTERNAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
