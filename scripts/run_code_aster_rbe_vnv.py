"""Run the pinned Code_Aster RBE2 rigid-arm correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_rbe import CodeAsterRbe2Campaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="results/VNV-RBE2-CODEASTER-RIGID-ARM-001")
    args = parser.parse_args()
    summary = CodeAsterRbe2Campaign(Path(args.output)).run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 3


if __name__ == "__main__":
    raise SystemExit(main())
