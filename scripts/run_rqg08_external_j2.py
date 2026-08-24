"""Run the reproducible external Code_Aster correlation for RQ-G08."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from solveur.verification.rqg08_external_j2 import run_campaign  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the RQ-G08 common external J2 correlation.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "qualification" / "vnv" / "external" / "rqg08_j2_common_024" / "reference",
    )
    args = parser.parse_args()
    summary = run_campaign(args.output)
    print(f"RQ-G08 external J2 correlation: {summary['status']}")
    print(json.dumps({"elements": [row["status"] for row in summary["rows"]]}, indent=2))
    print(f"output: {Path(args.output).resolve()}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
