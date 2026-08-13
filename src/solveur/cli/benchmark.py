"""CLI commands for the controlled meshed benchmark campaign."""

from __future__ import annotations

import argparse
import json

from solveur.api import list_benchmarks, run_benchmark
from solveur.core.errors import ExitCode


def command_benchmarks(args: argparse.Namespace) -> int:
    """List controlled benchmarks in text or JSON form."""
    descriptors = list_benchmarks()
    if args.json:
        print(json.dumps([item.to_dict() for item in descriptors], indent=2, ensure_ascii=True))
        return 0
    print("ID                         MATURITY                         FAMILY       TITLE")
    for item in descriptors:
        print(f"{item.identifier:<26} {item.maturity:<32} {item.family:<12} {item.title}")
    return 0


def command_benchmark(args: argparse.Namespace) -> int:
    """Execute one benchmark and report its machine-readable verdict."""
    run = run_benchmark(args.case, args.output, profile=args.verification_profile)
    case_dir = args.output.resolve() / run.descriptor.identifier
    print(f"BENCHMARK {run.status}: {run.descriptor.identifier} - {run.descriptor.title}")
    for check in run.checks:
        print(f"  {check['status']}: {check['id']} value={check['value']:.6e} limit={check['limit']:.6e}")
    print(f"artifacts: {case_dir}")
    if run.status == "FAIL":
        return int(ExitCode.QUALIFICATION_REJECTED)
    return 0

