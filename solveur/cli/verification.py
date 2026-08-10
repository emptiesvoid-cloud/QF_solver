"""Verification and qualification CLI commands."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mitc4.cli import main as mitc4_main

from solveur.api.public import qualification_readiness, run_contact_verification, run_qualification_campaign, save_result, verify_evidence
from solveur.core.errors import ExitCode
from solveur.core.qualification import verification_profile
from solveur.io.manifest import write_json_file
from solveur.verification.tet10 import Tet10MechanicalVerifier


def command_verify(args: argparse.Namespace) -> int:
    argv = ["verify"]
    if args.quick:
        argv.append("--quick")
    return int(ExitCode.ACCEPTED if mitc4_main(argv) == 0 else ExitCode.QUALIFICATION_REJECTED)


def command_verify_tet10(args: argparse.Namespace) -> int:
    report = Tet10MechanicalVerifier().run()
    if args.json_report is not None:
        write_json_file(args.json_report, report)
    print("TET10 mechanical verification")
    for check in report["checks"]:
        print(f"{check['status']:>4}  {check['name']:<40} value={check['value']:.6e} limit={check['limit']:.6e}")
    print(f"GLOBAL STATUS: {report['status']}")
    return int(ExitCode.ACCEPTED if report["status"] == "PASS" else ExitCode.QUALIFICATION_REJECTED)


def command_verify_contact(args: argparse.Namespace) -> int:
    summary = run_contact_verification(args.output)
    if args.json_report is not None:
        write_json_file(args.json_report, summary)
    print("CONTACT V1 verification")
    for study in summary["studies"]:
        print(f"{study['status']:>13}  {study['campaign_id']:<40} {study['scope']}")
    print(f"GLOBAL STATUS: {summary['status']}")
    return int(ExitCode.ACCEPTED if summary["status"] == "PASS_INTERNAL" else ExitCode.QUALIFICATION_REJECTED)


def command_verify_all(args: argparse.Namespace) -> int:
    profile = verification_profile(args.profile)
    commands = _verify_all_commands(profile.name, args.scope)
    records: list[dict[str, Any]] = []
    for index, command in enumerate(commands, start=1):
        print("VERIFY-ALL RUN:", " ".join(command))
        completed = subprocess.run(command, cwd=Path(__file__).resolve().parents[2], check=False)
        records.append({"index": index, "command": command, "return_code": completed.returncode})
        if completed.returncode != 0:
            print(f"VERIFY-ALL FAIL: {' '.join(command)} returned {completed.returncode}")
            result = _verify_all_result(profile.name, args.scope, records, "FAIL")
            _write_verify_all_report(args, result)
            if completed.returncode in {
                int(ExitCode.INPUT_OR_MESH),
                int(ExitCode.NUMERICAL_FAILURE),
                int(ExitCode.INFRASTRUCTURE_FAILURE),
            }:
                return completed.returncode
            return int(ExitCode.QUALIFICATION_REJECTED)
    print(f"VERIFY-ALL PASS: profile={profile.name}")
    _write_verify_all_report(args, _verify_all_result(profile.name, args.scope, records, "PASS"))
    return 0


def _verify_all_result(profile: str, scope: str, commands: list[dict[str, Any]], status: str) -> dict[str, Any]:
    """Build a persistent, machine-readable record of one verification run."""
    return {
        "status": status,
        "profile": profile,
        "scope": scope,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "commands": commands,
        "passed_command_count": sum(record["return_code"] == 0 for record in commands),
        "command_count": len(commands),
    }


def _write_verify_all_report(args: argparse.Namespace, result: dict[str, Any]) -> None:
    path = getattr(args, "json_report", None)
    if path is not None:
        write_json_file(path, result)
        print(f"VERIFY-ALL REPORT: {path}")


def command_qualification_readiness(args: argparse.Namespace) -> int:
    report = qualification_readiness(args.scope, args.registry)
    if args.json_report is not None:
        save_result(report, args.json_report)
    print(f"QUALIFICATION READINESS: {report.status}")
    print(f"scope: {report.scope}")
    print(f"scope status: {report.scope_status}")
    print(f"requirements: {report.covered_requirement_count}/{report.requirement_count}")
    print(f"formulas: {report.covered_formula_count}/{report.formula_count}")
    for check in report.checks:
        if check.status == "FAIL":
            print(f"FAIL: {check.identifier} {check.detail}")
    return int(ExitCode.ACCEPTED if report.status == "PASS" else ExitCode.QUALIFICATION_REJECTED)


def command_qualify(args: argparse.Namespace) -> int:
    summary = run_qualification_campaign(args.manifest, args.output)
    print(f"QUALIFICATION CAMPAIGN STATUS: {summary['status']}")
    print(f"cases: {summary['passed_count']}/{summary['case_count']} passed")
    print(f"summary: {Path(args.output) / 'qualification_campaign_summary.json'}")
    return int(ExitCode.ACCEPTED if summary["status"] == "PASS" else ExitCode.QUALIFICATION_REJECTED)


def command_verify_evidence(args: argparse.Namespace) -> int:
    report = verify_evidence(args.input)
    if args.json_report is not None:
        save_result(report, args.json_report)
    print(f"EVIDENCE VERIFY STATUS: {report.status}")
    print(f"manifest: {report.manifest_path}")
    print(f"checked files: {report.checked_file_count}")
    if args.json_report is not None:
        print(f"json report: {args.json_report}")
    for message in report.errors:
        print(f"ERROR: {message}")
    for message in report.warnings:
        print(f"WARNING: {message}")
    return int(ExitCode.ACCEPTED if report.status == "PASS" else ExitCode.QUALIFICATION_REJECTED)


def _verify_all_commands(profile: str, scope: str) -> list[list[str]]:
    commands: list[list[str]] = []
    if profile in {"strict", "qualification"}:
        commands.append([sys.executable, "-m", "ruff", "check", "solveur", "mitc4", "tests", "scripts"])
    if profile == "qualification":
        commands.extend(
            [
                [
                    sys.executable,
                    "-m",
                    "mypy",
                    "solveur/core/errors.py",
                    "solveur/core/qualification.py",
                    "solveur/io/manifest.py",
                    "solveur/verification/traceability.py",
                ],
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "--cov=solveur",
                    "--cov=mitc4",
                    "--cov-branch",
                    "--cov-report=json:coverage.json",
                    "--cov-fail-under=84",
                    "--ignore=tests/documentation",
                    "-m",
                    "not benchmark and not large",
                ],
                [sys.executable, "scripts/check_p0_coverage.py", "coverage.json"],
            ]
        )
    elif profile in {"engineering", "strict"}:
        commands.append(
            [
                sys.executable,
                "-m",
                "pytest",
                "--ignore=tests/documentation",
                "-m",
                "not benchmark and not large",
            ]
        )
    commands.extend(
        [
            [
                sys.executable,
                "-m",
                "compileall",
                "-q",
                "solveur",
                "mitc4",
                "scripts",
                "tests",
                "qf_solver.py",
                "main_solveur.py",
                "mitc4_solver.py",
            ],
            [sys.executable, "qf_solver.py", "verify", "--quick"],
            [sys.executable, "mitc4_solver.py", "verify", "--quick"],
            [sys.executable, "qf_solver.py", "verify-tet10"],
        ]
    )
    if profile == "qualification":
        commands.extend(
            [
                [sys.executable, "qf_solver.py", "verify"],
                [
                    sys.executable,
                    "qf_solver.py",
                    "qualification-readiness",
                    "--scope",
                    scope,
                ],
                [
                    sys.executable,
                    "qf_solver.py",
                    "qualify",
                    "--manifest",
                    "qualification/campaign.json",
                    "--output",
                    "results/qualification_campaign_verify_all",
                ],
            ]
        )
    return commands
