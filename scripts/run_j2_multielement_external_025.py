"""Run the opt-in Code_Aster multi-element J2 correlation for 0.2.5a0."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from solveur.verification.j2_multielement_external import run_campaign


def exit_code(summary: dict[str, object]) -> int:
    """Return failure for an unclosed external correlation."""
    return 0 if summary.get("status") == "PASS_EXTERNAL_CORRELATION" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/vnv_0_2_5/j2_multielement_code_aster"),
    )
    args = parser.parse_args()
    summary = run_campaign(args.output)
    print(json.dumps({"status": summary["status"], "checks": len(summary["checks"])}, indent=2))
    return exit_code(summary)


if __name__ == "__main__":
    raise SystemExit(main())
