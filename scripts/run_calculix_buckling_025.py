"""Run the bounded 0.2.5 CalculiX solid-family buckling correlation."""

from __future__ import annotations

import argparse

from solveur.verification.calculix_buckling_025 import DEFAULT_IMAGE, run_campaign


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="results/vnv_0_2_5/calculix_buckling_solid_families")
    parser.add_argument("--families", nargs="+", default=["TET4", "TET10", "HEX8", "HEX20"])
    parser.add_argument("--cells", type=int, default=1)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--modes", type=int, default=1, help="Number of requested buckling modes (default: first mode only).")
    parser.add_argument("--no-execute", action="store_true")
    args = parser.parse_args()
    summary = run_campaign(
        args.output,
        element_types=tuple(args.families),
        cells=args.cells,
        image=args.image,
        modes=args.modes,
        execute=not args.no_execute,
    )
    print(f"{summary['study_id']}: {summary['status']}")
    for row in summary["rows"]:
        print(f"{row['element']}: {row['status']}")
    return 0 if summary["status"] in {"PASS_EXTERNAL_CORRELATION_BOUNDED", "PLANNED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
