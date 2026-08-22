"""Run one structured TET4 flexion probe in a PETSc-enabled environment."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.tet4_structured_petsc import run_tet4_petsc_probe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = run_tet4_petsc_probe(args.input, args.output)
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS" else 4


if __name__ == "__main__":
    raise SystemExit(main())
