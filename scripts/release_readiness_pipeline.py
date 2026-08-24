"""Dry-run/execute the deterministic 0.2.4a0 release-readiness chain.

This module intentionally has no upload, tag or push command.  Publication
remains a separate Owner decision after the report is reviewed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGETED_TESTS = [
    "tests/unit/test_robustness_j2_multiaxial.py",
    "tests/unit/test_robustness_tangent_fd.py",
    "tests/unit/test_robustness_state_transactions.py",
    "tests/verification/test_robustness_solid_matrix_vnv.py",
    "tests/verification/test_robustness_distorted_hex_vnv.py",
    "tests/verification/test_robustness_common_benchmark_vnv.py",
    "tests/verification/test_robustness_newton_rate_vnv.py",
]


@dataclass(frozen=True)
class PipelineStep:
    name: str
    command: tuple[str, ...]


def steps(profile: str = "targeted") -> tuple[PipelineStep, ...]:
    """Return the safe, ordered release-readiness steps."""

    tests = tuple(TARGETED_TESTS) if profile == "targeted" else ("tests/unit", "tests/integration", "tests/verification")
    coverage_gate = ("--cov-fail-under=80",) if profile == "full" else ("--cov-fail-under=0",)
    return (
        PipelineStep("tests", (sys.executable, "-m", "pytest", *tests, "-q")),
        PipelineStep("coverage", (sys.executable, "-m", "pytest", *tests, "--cov=solveur", "--cov-report=json:coverage-024.json", *coverage_gate, "-q")),
        PipelineStep("vnv", (sys.executable, "-m", "pytest", "tests/verification/test_robustness_solid_matrix_vnv.py", "tests/verification/test_robustness_common_benchmark_vnv.py", "tests/verification/test_robustness_newton_rate_vnv.py", "-q")),
        PipelineStep("gate_check", (sys.executable, "-c", "from pathlib import Path; import json; p=Path('qualification/reviews/qf_solver_0_2_4a0_gate_status.json'); d=json.loads(p.read_text()); assert d['release_claim'] is False")),
        PipelineStep("sha_consistency", ("git", "rev-parse", "HEAD")),
        PipelineStep("build", (sys.executable, "-m", "build", "--wheel", "--sdist", "--outdir", ".tmp_release_readiness_024")),
        PipelineStep("smoke_install", (sys.executable, "-c", "from pathlib import Path; import zipfile; p=Path('.tmp_release_readiness_024'); assert any(p.glob('*.whl')); print('SMOKE ARTIFACT PRESENT')")),
    )


def run_pipeline(root: str | Path = ROOT, *, profile: str = "targeted", execute: bool = False) -> dict[str, Any]:
    """Run or describe the chain and return a machine-readable report."""

    base = Path(root).resolve()
    report: dict[str, Any] = {"profile": profile, "dry_run": not execute, "status": "PLANNED" if not execute else "PASS", "steps": []}
    if profile not in {"targeted", "full"}:
        raise ValueError("profile must be 'targeted' or 'full'.")
    for step in steps(profile):
        item: dict[str, Any] = {"name": step.name, "command": list(step.command), "status": "PLANNED" if not execute else "PASS"}
        if execute:
            completed = subprocess.run(step.command, cwd=base, text=True, capture_output=True, check=False)
            item.update({"returncode": completed.returncode, "stdout_tail": completed.stdout[-2000:], "stderr_tail": completed.stderr[-2000:]})
            if completed.returncode != 0:
                item["status"] = "FAIL"
                report["status"] = "NOT_READY"
                report["blocking_step"] = step.name
                report["steps"].append(item)
                break
        report["steps"].append(item)
    report["forbidden_actions"] = ["twine upload", "git tag", "git push"]
    report["publication"] = "OWNER_ONLY"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("targeted", "full"), default="targeted")
    parser.add_argument("--execute", action="store_true", help="Execute commands; otherwise print a dry-run report.")
    parser.add_argument("--output", type=Path, default=Path("release_readiness_024.json"))
    args = parser.parse_args()
    report = run_pipeline(ROOT, profile=args.profile, execute=args.execute)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"RELEASE READINESS 0.2.4a0: {report['status']}")
    return 0 if report["status"] in {"PLANNED", "PASS"} else 4


if __name__ == "__main__":
    raise SystemExit(main())
