"""Run the independent MITC3+ stiffness quadrature audit."""

from __future__ import annotations

import argparse

from solveur.verification.mitc3_stiffness_quadrature_audit import write_mitc3_stiffness_quadrature_audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    summary = write_mitc3_stiffness_quadrature_audit(args.output)
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_INDEPENDENT_QUADRATURE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
