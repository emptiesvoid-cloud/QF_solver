"""Command line interface for the MITC4 package."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from mitc4.benchmarks import CantileverPlateBenchmark, ScordelisLoBenchmark, ShearLockingStudy
from mitc4.verification import MechanicalVerifier, print_results_table
from solveur.version import __version__


def command_verify(args: argparse.Namespace) -> int:
    results = MechanicalVerifier().run(include_benchmark=not args.quick, png=args.png)
    print_results_table(results)
    return 0 if all(result.passed for result in results) else 1


def command_scordelis(args: argparse.Namespace) -> int:
    result = ScordelisLoBenchmark(args.nx, args.ny).run(show=args.show, png=args.png, scale=args.scale)
    values = result.values
    print("\nScordelis-Lo roof")
    print(f"mesh                 : {args.nx} x {args.ny}")
    print(f"edge center Uz       : {values['w_edge_center']:.8e} m")
    print(f"opposite edge Uz     : {values['w_opposite_edge_center']:.8e} m")
    print(f"reference Uz         : {values['reference']:.8e} m")
    print(f"relative error       : {values['error_percent']:.4f} %")
    print(f"symmetry error       : {values['symmetry_error_percent']:.4f} %")
    if args.png is not None:
        print(f"figure saved         : {args.png}")
    return 0 if values["error_percent"] < args.max_error else 1


def command_cantilever(args: argparse.Namespace) -> int:
    result = CantileverPlateBenchmark(
        args.nx,
        args.ny,
        length=args.length,
        width=args.width,
        thickness=args.thickness,
        force=args.force,
        E=args.E,
        nu=args.nu,
    ).run(show=args.show, png=args.png, scale=args.scale)
    values = result.values
    print("\nCantilever plate")
    print(f"mesh                 : {args.nx} x {args.ny}")
    print(f"tip Uz               : {values['tip_w']:.8e} m")
    print(f"EB/Kirchhoff check   : {values['reference']:.8e} m")
    print(f"relative difference  : {values['error_percent']:.4f} %")
    if args.png is not None:
        print(f"figure saved         : {args.png}")
    return 0


def command_shear_study(args: argparse.Namespace) -> int:
    result = ShearLockingStudy(args.nx, args.ny).run()
    print("\nTransverse shear / shear-locking study")
    for key, value in result.values.items():
        print(f"{key:24s}: {value:.8e}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MITC4 flat-shell solver and verification suite.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    verify = sub.add_parser("verify", help="run mechanical verification tests")
    verify.add_argument("--quick", action="store_true", help="skip Scordelis-Lo benchmark")
    verify.add_argument("--png", type=Path, default=Path("results/scordelis_verification.png"), help="benchmark figure path")
    verify.set_defaults(func=command_verify)

    scordelis = sub.add_parser("scordelis", help="solve the Scordelis-Lo roof benchmark")
    scordelis.add_argument("--nx", type=int, default=24)
    scordelis.add_argument("--ny", type=int, default=24)
    scordelis.add_argument("--scale", type=float, default=20.0)
    scordelis.add_argument("--show", action="store_true")
    scordelis.add_argument("--png", type=Path, default=Path("results/scordelis.png"))
    scordelis.add_argument("--max-error", type=float, default=1.5)
    scordelis.set_defaults(func=command_scordelis)

    cantilever = sub.add_parser("cantilever", help="solve a clamped rectangular plate")
    cantilever.add_argument("--nx", type=int, default=16)
    cantilever.add_argument("--ny", type=int, default=4)
    cantilever.add_argument("--length", type=float, default=1.0)
    cantilever.add_argument("--width", type=float, default=0.2)
    cantilever.add_argument("--thickness", type=float, default=0.01)
    cantilever.add_argument("--force", type=float, default=-1000.0)
    cantilever.add_argument("--E", type=float, default=210.0e9)
    cantilever.add_argument("--nu", type=float, default=0.3)
    cantilever.add_argument("--scale", type=float, default=None)
    cantilever.add_argument("--show", action="store_true")
    cantilever.add_argument("--png", type=Path, default=Path("results/cantilever.png"))
    cantilever.set_defaults(func=command_cantilever)

    shear = sub.add_parser("shear-study", help="compare MITC and full Q4 transverse shear behavior")
    shear.add_argument("--nx", type=int, default=8)
    shear.add_argument("--ny", type=int, default=2)
    shear.set_defaults(func=command_shear_study)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        args = parser.parse_args(["verify"])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
