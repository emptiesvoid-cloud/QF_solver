"""Command-line interface for the local V&V workflow."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .execution import run_case, validate_all_cases, validate_manifest_file
from .manifest import LocalVVError, load_json, sha256_bytes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="verify identities and the local Python/import environment only")
    validate.add_argument("--manifest", required=True, type=Path)
    run = commands.add_parser("run", help="run one exact Owner-approved case from a frozen manifest")
    run.add_argument("--manifest", required=True, type=Path)
    run.add_argument("--decision", required=True, type=Path)
    run.add_argument("--case-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest, raw, errors = validate_manifest_file(args.manifest.resolve(strict=True))
        if errors:
            raise LocalVVError("manifest validation failed: " + "; ".join(errors))
        if args.command == "validate":
            preflight = validate_all_cases(manifest)
            print(
                json.dumps(
                    {
                        "status": "VALIDATED_NOT_AUTHORIZED",
                        "manifest_sha256": sha256_bytes(raw),
                        "case_count": len(manifest["cases"]),
                        **preflight,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        decision, decision_raw = load_json(args.decision.resolve(strict=True))
        case = next((item for item in manifest["cases"] if item.get("case_id") == args.case_id), None)
        if case is None:
            raise LocalVVError("DENY_EXECUTION: case_id is not listed in the frozen manifest")
        result = run_case(manifest, raw, decision, case, decision_raw)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "PYTEST_PASS_ONLY" else 1
    except (OSError, ValueError, KeyError, LocalVVError, subprocess.TimeoutExpired) as exc:
        print(f"DENY_EXECUTION/INFRA_ERROR: {exc}", file=sys.stderr)
        return 2
