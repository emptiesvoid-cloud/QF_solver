"""Run the pinned Docker PETSc versus host SciPy TET4 agreement campaign."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.large_petsc_scipy import LargePetscScipyCorrelation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results") / LargePetscScipyCorrelation.study_id)
    parser.add_argument("--ranks", type=int, default=2)
    args = parser.parse_args()
    summary = LargePetscScipyCorrelation(args.output, ranks=args.ranks).run()
    print(f"{summary['study_id']}: {summary['status']}")
    print(f"evidence: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
