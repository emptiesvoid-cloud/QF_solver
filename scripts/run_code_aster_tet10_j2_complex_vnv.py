"""Run the external complex TET10 J2 Code_Aster campaign."""

from __future__ import annotations

import argparse

from solveur.verification.code_aster_tet10_j2_complex import CodeAsterTet10J2ComplexCampaign


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate complex TET10 J2 Code_Aster evidence.")
    parser.add_argument("--output", default="results/VNV-TET10-J2-CODEASTER-COMPLEX-026")
    parser.add_argument("--mesh-size", type=float, default=0.32)
    parser.add_argument("--no-publish-reference", action="store_true")
    args = parser.parse_args()
    summary = CodeAsterTet10J2ComplexCampaign(
        args.output, mesh_size=args.mesh_size, publish_reference=not args.no_publish_reference
    ).run()
    print(f"TET10 J2 complex Code_Aster V&V: {summary['status']}")
    print(f"Output: {args.output}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 4


if __name__ == "__main__":
    raise SystemExit(main())
