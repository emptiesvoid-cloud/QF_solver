"""Run the controlled standard sparse-linear-method comparison."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from solveur.verification.linear_solver_comparison import write_linear_solver_comparison


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/VNV-LINEAR-SOLVERS-001"))
    args = parser.parse_args(argv)
    report = write_linear_solver_comparison(args.output)
    print(f"LINEAR SOLVER VNV: {report['status']} ({args.output})")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
