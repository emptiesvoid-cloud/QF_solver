"""Record targeted development checks; never run a qualification campaign."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    "src/solveur/contact/measures.py",
    "src/solveur/contact/entities.py",
    "src/solveur/contact/support.py",
    "src/solveur/contact/evaluation.py",
    "src/solveur/core/model.py",
    "src/solveur/io/contact_schema.py",
    "src/solveur/io/model_writer.py",
    "scripts/analyze_wp08d_r2_2_diagnostic.py",
    "scripts/wp08d_refinement_metrics.py",
    "scripts/wp08d_phase1_common.py",
    "scripts/run_wp08d_contact_requalification.py",
    "scripts/run_wp08d_independent_reference.py",
    "scripts/run_wp08_surface_stiffness_diagnostic.py",
    "scripts/validate_wp08_surface_remediation.py",
]
TESTS = [
    "tests/unit/test_contact_surface_tangential_stiffness.py",
    "tests/unit/test_wp08d_r2_2_preparation.py",
    "tests/unit/test_wp08d_phase1_runner.py",
    "tests/unit/test_frictional_contact.py",
    "tests/unit/test_contact_surface_lumped_penalty.py",
    "tests/unit/test_wp07b_contact_evaluation_restart.py",
    "tests/unit/test_contact_requalification_process_audit.py",
    "tests/unit/test_wp08d_independent_reference.py",
    "tests/unit/test_wp08_surface_stiffness_campaign.py",
    "tests/unit/test_wp08b_frictional_identities_rollback.py",
    "tests/unit/test_wp08c_friction_tangent_dissipation.py",
    "tests/unit/test_wp08d_mixed_open_active_slip.py",
    "tests/unit/test_wp08d_active_set_remediation.py",
    "tests/unit/test_frictionless_contact.py",
    "tests/unit/test_nonlinear_contact_composition.py",
    "tests/unit/test_schema_entity_validation_paths.py",
    "tests/unit/test_schema_validation_paths.py",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to(ROOT / "qualification/0_2_9/wp08_surface_stiffness_remediation"):
        raise ValueError("validation output must stay in the dedicated development evidence directory")
    output.mkdir(parents=True, exist_ok=False)
    source_hashes = {path: sha256(ROOT / path) for path in SOURCES + TESTS}
    checks = [
        ("pytest", [sys.executable, "-m", "pytest", "-q", *TESTS, "--junitxml=" + str(output / "junit.xml")]),
        ("ruff", [sys.executable, "-m", "ruff", "check", *SOURCES, *TESTS]),
        ("mypy", [sys.executable, "-m", "mypy", *SOURCES, TESTS[0], TESTS[1]]),
        ("compileall", [sys.executable, "-m", "compileall", "-q", *SOURCES, *TESTS]),
        ("diff_check", ["git", "diff", "--check"]),
    ]
    records = []
    for label, command in checks:
        log = output / (label + ".log")
        started = utc()
        with log.open("xb") as stream:
            child = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
            code = child.wait()
        records.append(
            {
                "check": label,
                "command": command,
                "started_utc": started,
                "ended_utc": utc(),
                "pid": child.pid,
                "exit_code": code,
                "log": log.relative_to(ROOT).as_posix(),
                "log_sha256": sha256(log),
            }
        )
        print(f"{label}: exit={code}", flush=True)
    stable = source_hashes == {path: sha256(ROOT / path) for path in SOURCES + TESTS}
    report = {
        "status": "PASS_DEVELOPMENT_CHECKS" if stable and all(r["exit_code"] == 0 for r in records) else "FAIL_CLOSED",
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        "working_tree_clean": not bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        ),
        "executed_state": "UNCOMMITTED_DEVELOPMENT_SOURCE_BOUND_BY_FILE_HASHES_NOT_FORMAL_EXECUTION_SHA",
        "source_hashes": source_hashes,
        "source_stable_during_validation": stable,
        "commands": records,
        "junit_sha256": sha256(output / "junit.xml") if (output / "junit.xml").is_file() else None,
        "formal_qualification": False,
        "wp08_m1_m2_m3_campaign_run": False,
        "unit_test_solvers_run": True,
        "points_awarded": False,
        "full_suite_run": False,
    }
    with (output / "validation.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return 0 if report["status"] == "PASS_DEVELOPMENT_CHECKS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
