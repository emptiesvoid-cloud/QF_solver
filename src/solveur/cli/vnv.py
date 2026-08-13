"""CLI command for controlled V&V comparison studies."""

from __future__ import annotations

import argparse

from solveur.api import import_cantilever_vnv_study, import_torsion_vnv_study, run_vnv_study
from solveur.core.errors import ExitCode


def command_vnv_compare(args: argparse.Namespace) -> int:
    """Compare QF_solver outputs to normalized references and write Markdown evidence."""
    run = run_vnv_study(args.study, args.output)
    print(f"VNV {run.status}: {run.study.identifier} - {run.study.title}")
    print(f"automated verdict: {run.automated_verdict}")
    print(f"human decision: {run.human_decision}")
    print(f"report: {args.output.resolve() / run.files['report']}")
    if run.automated_verdict == "FAIL" or run.human_decision == "rejected":
        return int(ExitCode.QUALIFICATION_REJECTED)
    if args.require_approval and run.human_decision not in {"accepted", "accepted_with_reservations"}:
        return int(ExitCode.QUALIFICATION_REJECTED)
    return int(ExitCode.ACCEPTED)


def command_vnv_import_benchmark(args: argparse.Namespace) -> int:
    """Build a controlled analytic TET4 study from benchmark evidence."""
    importers = {
        "BM-SOL-CANTILEVER-001": import_cantilever_vnv_study,
        "BM-SOL-TET4-TORSION-001": import_torsion_vnv_study,
    }
    importer = importers.get(args.case)
    if importer is None:
        raise ValueError(f"Unsupported V&V benchmark import {args.case!r}.")
    study = importer(args.output, source_dir=args.source, overwrite=args.overwrite)
    print(f"VNV STUDY CREATED: {study}")
    reference = "Reference analytique Timoshenko" if args.case == "BM-SOL-CANTILEVER-001" else "Saint-Venant"
    print(f"reference: {reference}")
    print("png: results/h*_qf_deformation.png and references/*_deformation.png")
    return int(ExitCode.ACCEPTED)
