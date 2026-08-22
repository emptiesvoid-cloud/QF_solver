"""Run the independent MITC3 laminate A/B/D audit."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from solveur.verification.mitc3_laminate_abd_audit import write_mitc3_laminate_abd_audit


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("qualification/vnv/mitc3_laminate_abd_audit_2026-08-21"))
    args = parser.parse_args(argv)
    report = write_mitc3_laminate_abd_audit(args.output)
    print(f"MITC3 ABD AUDIT: {report['status']} ({args.output})")
    return 0 if report["status"] == "PASS_INDEPENDENT_ABD" else 1


if __name__ == "__main__":
    raise SystemExit(main())
