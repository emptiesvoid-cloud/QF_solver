"""Aggregate the Code_Aster and CalculiX axial curved MITC3 diagnostics."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.mitc3_curved_axial_audit import write_axial_audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-aster", type=Path, required=True)
    parser.add_argument("--calculix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = write_axial_audit(args.code_aster, args.calculix, args.output)
    print(f"{summary['study_id']}: {summary['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
