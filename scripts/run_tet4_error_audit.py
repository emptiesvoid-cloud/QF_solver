"""Run the archived causal error audit for the linear TET4 scopes."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from solveur.verification.tet4_error_audit import write_tet4_error_audit


ROOT = Path(__file__).resolve().parents[1]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "qualification/vnv/tet4_error_audit_2026-08-21",
    )
    args = parser.parse_args(argv)
    report = write_tet4_error_audit(
        ROOT / "qualification/maturity_evidence_0_2_1/tet4_linear_static.json",
        ROOT / "qualification/maturity_evidence_0_2_1/tet4_linear_dynamics.json",
        ROOT / "qualification/vnv/external/code_aster_tet4_static/reference/summary.json",
        ROOT / "qualification/vnv/tet4_tet10_corrected_reference_002/summary.json",
        args.output,
    )
    print(f"TET4 ERROR AUDIT: {report['status']} ({args.output})")
    return 0 if report["status"] == "PASS_DIAGNOSTIC" else 1


if __name__ == "__main__":
    raise SystemExit(main())
