"""Dry-run/execute the controlled QF Solver 0.2.5a0 readiness chain.

The chain is deliberately separate from publication. It never creates a tag,
pushes a branch or uploads an artifact; those actions remain Owner-controlled.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.git_tools import git_command


ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "0.2.5a0"
OUTPUT_DIR = ".tmp_release_readiness_025"
GENERATED_EVIDENCE_PREFIXES = (
    "docs/generated/",
    "docs/assets/generated/",
    f"{OUTPUT_DIR}/",
    ".tmp_smoke_install_025/",
)
MANDATORY_GATE_IDS = tuple(f"025-G{index:02d}" for index in (*range(0, 7), *range(8, 13)))
CLOSED_GATE_STATUSES = {
    "PASS",
}
TARGETED_TESTS = (
    "tests/unit/test_analysis_features.py",
    "tests/unit/test_nonlinear_constitutive_vv.py",
    "tests/unit/test_nonlinear_element_contracts.py",
    "tests/unit/test_nonlinear_state_transaction_contract.py",
    "tests/unit/test_nonlinear_cyclic.py",
    "tests/unit/test_nonlinear_load_path.py",
    "tests/unit/test_nonlinear_load_step_sensitivity.py",
    "tests/unit/test_nonlinear_iteration_sparse.py",
    "tests/unit/test_total_lagrangian_j2.py",
    "tests/unit/test_total_lagrangian_hex8.py",
    "tests/unit/test_nonlinear_assembly_plan.py",
    "tests/unit/test_nonlinear_composite_assembly.py",
    "tests/unit/test_nonlinear_multielement.py",
    "tests/unit/test_nonlinear_contact_composition.py",
    "tests/unit/test_contact_finite_sliding.py",
    "tests/unit/test_linear_buckling.py",
    "tests/unit/test_calculix_buckling_025.py",
    "tests/unit/test_nonlinear_failure_modes.py",
    "tests/unit/test_nonlinear_failure_campaign.py",
    "tests/unit/test_nonlinear_benchmark.py",
    "tests/unit/test_nonlinear_performance.py",
    "tests/unit/test_j2_multielement_external.py",
    "tests/documentation/test_docs_generation.py",
    "tests/documentation/test_engineering_page_contracts.py",
    "tests/documentation/test_docs_fields.py",
    "tests/unit/test_public_document_audit.py",
)


@dataclass(frozen=True)
class PipelineStep:
    name: str
    command: tuple[str, ...]


def _gate_command() -> tuple[str, ...]:
    code = (
        "OPEN_GATES=''; "
        "from scripts.release_readiness_pipeline_025 import _run_gate_check; "
        "raise SystemExit(_run_gate_check())"
    )
    return (sys.executable, "-c", code)


def _gate_statuses(path: str | Path = ROOT / "docs/verification/0_2_5/0_2_5_gate_matrix.md") -> dict[str, str]:
    """Parse the controlled gate table without treating malformed rows as closed."""
    statuses: dict[str, str] = {}
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, OSError):
        return statuses
    for line in lines:
        if not line.startswith("| 025-G"):
            continue
        fields = [field.strip() for field in line.split("|")]
        if len(fields) < 4:
            continue
        gate_id, status = fields[1], fields[-2]
        if gate_id.startswith("025-G"):
            statuses[gate_id] = status
    return statuses


def _run_gate_check(path: str | Path = ROOT / "docs/verification/0_2_5/0_2_5_gate_matrix.md") -> int:
    """Fail closed when mandatory gates are missing, malformed or not closed."""
    statuses = _gate_statuses(path)
    missing = [gate_id for gate_id in MANDATORY_GATE_IDS if gate_id not in statuses]
    open_gates = [
        f"{gate_id}:{statuses[gate_id]}"
        for gate_id in MANDATORY_GATE_IDS
        if gate_id in statuses and statuses[gate_id] not in CLOSED_GATE_STATUSES
    ]
    print("OPEN_GATES=" + ",".join(open_gates))
    print("MISSING_GATES=" + ",".join(missing))
    print("GATE_STATUS=" + ("PASS" if not missing and not open_gates else "FAIL"))
    return 0 if not missing and not open_gates else 4


def _smoke_command() -> tuple[str, ...]:
    code = (
        "from pathlib import Path; import subprocess, sys; "
        "wheel=next(Path('.tmp_release_readiness_025').glob('*.whl')); "
        "target=Path('.tmp_smoke_install_025'); target.mkdir(exist_ok=True); "
        "subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--no-deps', '--target', str(target), str(wheel)]); "
        "sys.path.insert(0, str(target)); import solveur; print('SMOKE_IMPORT=' + getattr(solveur, '__version__', 'ok'))"
    )
    return (sys.executable, "-c", code)


def _twine_command() -> tuple[str, ...]:
    code = (
        "from pathlib import Path; import subprocess, sys; "
        "artifacts=[str(path) for path in Path('.tmp_release_readiness_025').glob('*') if path.suffix in {'.whl', '.gz'}]; "
        "raise SystemExit(subprocess.call([sys.executable, '-m', 'twine', 'check', *artifacts]))"
    )
    return (sys.executable, "-c", code)


def _sha_consistency_command() -> tuple[str, ...]:
    """Return a fail-closed provenance check for the candidate source tree."""
    code = (
        "from scripts.release_readiness_pipeline_025 import _run_sha_consistency; "
        "raise SystemExit(_run_sha_consistency())"
    )
    return (sys.executable, "-c", code)


def check_candidate_provenance(
    root: str | Path = ROOT, *, require_evidence: bool = False
) -> dict[str, object]:
    """Inspect the candidate revision and fail closed for a dirty tree."""
    return _check_candidate_provenance(root, require_evidence=require_evidence)


def _check_candidate_provenance(
    root: str | Path = ROOT, *, require_evidence: bool = False
) -> dict[str, object]:
    """Inspect source provenance and optionally match a generated evidence manifest.

    Generated documentation is evidence produced *from* the candidate source;
    it is not part of the source revision it identifies.  Consequently, changes
    below the generated-evidence prefixes do not make the source tree dirty and
    the manifest is matched through its explicit ``source_sha`` field.  This
    avoids the impossible requirement that a tracked manifest contain the SHA
    of the commit that contains that same manifest.
    """
    base = Path(root).resolve()
    try:
        revision_result = subprocess.run(
            [git_command(), "rev-parse", "HEAD"],
            cwd=base,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        status_result = subprocess.run(
            [git_command(), "status", "--porcelain", "--untracked-files=all"],
            cwd=base,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        return {
            "status": "FAIL",
            "revision": "unknown",
            "tree_clean": False,
            "evidence_sha_match": False if require_evidence else None,
            "detail": f"Git provenance unavailable: {error}",
        }
    revision = revision_result.stdout.strip()
    tree_clean = status_result.returncode == 0 and not _source_changes(status_result.stdout)
    evidence_sha_match: bool | None = None
    if require_evidence:
        manifest_path = base / "docs" / "generated" / "docs_manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            source = manifest.get("source", {})
            source_sha = manifest.get("source_sha")
            if not isinstance(source_sha, str) or not source_sha:
                source_sha = source.get("revision") if isinstance(source, dict) else None
            evidence_sha_match = (
                source_sha == revision
                and isinstance(source, dict)
                and source.get("dirty") is False
            )
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            evidence_sha_match = False
    passed = (
        revision_result.returncode == 0
        and bool(revision)
        and tree_clean
        and (evidence_sha_match is not False)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "revision": revision or "unknown",
        "tree_clean": tree_clean,
        "evidence_sha_match": evidence_sha_match,
        "detail": "candidate revision is committed and the tree is clean"
        if passed
        else (
            "candidate evidence does not match the committed revision"
            if evidence_sha_match is False and tree_clean
            else "candidate requires a resolvable commit and a clean tree"
        ),
    }


def _source_changes(status_output: str) -> list[str]:
    """Return status rows that change source, not generated evidence outputs."""
    changes: list[str] = []
    for row in status_output.splitlines():
        if not row.strip():
            continue
        path = row[3:].strip() if len(row) >= 3 else row.strip()
        paths = path.split(" -> ")
        normalized = [item.replace("\\", "/") for item in paths]
        if all(
            any(item == prefix.rstrip("/") or item.startswith(prefix) for prefix in GENERATED_EVIDENCE_PREFIXES)
            for item in normalized
        ):
            continue
        changes.append(row)
    return changes


def _run_sha_consistency() -> int:
    """Print the provenance result for the pipeline child process."""
    result = _check_candidate_provenance(require_evidence=True)
    print("FINAL_SHA=" + str(result["revision"]))
    print("TREE_CLEAN=" + str(result["tree_clean"]).lower())
    print("EVIDENCE_SHA_MATCH=" + str(result["evidence_sha_match"]).lower())
    print("SHA_STATUS=" + str(result["status"]))
    return 0 if result["status"] == "PASS" else 4


def steps(profile: str = "targeted") -> tuple[PipelineStep, ...]:
    """Return the ordered, non-publishing readiness steps."""

    if profile not in {"targeted", "full"}:
        raise ValueError("profile must be 'targeted' or 'full'.")
    selected = TARGETED_TESTS if profile == "targeted" else ("tests",)
    result = [PipelineStep("tests", (sys.executable, "-m", "pytest", *selected, "-q"))]
    if profile == "full":
        result.extend(
            (
                PipelineStep(
                    "coverage",
                    (
                        sys.executable,
                        "-m",
                        "pytest",
                        "tests/unit",
                        "tests/integration",
                        "--cov=solveur",
                        "--cov-branch",
                        "--cov-report=json:coverage-025.json",
                        "--cov-fail-under=80",
                        "-q",
                    ),
                ),
                PipelineStep(
                    "external_vnv",
                    (sys.executable, "scripts/run_j2_multielement_external_025.py"),
                ),
            )
        )
    result.extend(
        (
            PipelineStep("docs", (sys.executable, "scripts/build_docs.py", "--profile", "engineering")),
            PipelineStep("gate_check", _gate_command()),
            PipelineStep("sha_consistency", _sha_consistency_command()),
            PipelineStep(
                "build",
                (sys.executable, "-m", "build", "--wheel", "--sdist", "--outdir", OUTPUT_DIR),
            ),
            PipelineStep("twine_check", _twine_command()),
            PipelineStep("smoke_install", _smoke_command()),
        )
    )
    return tuple(result)


def run_pipeline(root: str | Path = ROOT, *, profile: str = "targeted", execute: bool = False) -> dict[str, Any]:
    """Run or describe the readiness chain and return a JSON report."""

    base = Path(root).resolve()
    report: dict[str, Any] = {
        "version": TARGET_VERSION,
        "profile": profile,
        "dry_run": not execute,
        "status": "PLANNED" if not execute else "PASS",
        "steps": [],
        "publication": "OWNER_ONLY",
        "forbidden_actions": ["git tag", "git push", "twine upload"],
    }
    for step in steps(profile):
        item: dict[str, Any] = {
            "name": step.name,
            "command": list(step.command),
            "status": "PLANNED" if not execute else "PASS",
        }
        if execute:
            completed = subprocess.run(step.command, cwd=base, text=True, capture_output=True, check=False)
            item.update(
                {
                    "returncode": completed.returncode,
                    "stdout_tail": completed.stdout[-2000:],
                    "stderr_tail": completed.stderr[-2000:],
                }
            )
            if completed.returncode != 0:
                item["status"] = "FAIL"
                report["status"] = "NOT_READY"
                report.setdefault("blocking_steps", []).append(step.name)
                report.setdefault("blocking_step", step.name)
                report["steps"].append(item)
                # An open gate blocks release, but packaging checks remain useful
                # evidence and do not publish anything. Other failures stop the chain.
                if step.name != "gate_check":
                    break
                continue
        report["steps"].append(item)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("targeted", "full"), default="targeted")
    parser.add_argument("--execute", action="store_true", help="Execute commands; otherwise print a dry-run report.")
    parser.add_argument("--output", type=Path, default=Path("release_readiness_025.json"))
    args = parser.parse_args()
    report = run_pipeline(ROOT, profile=args.profile, execute=args.execute)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"RELEASE READINESS {TARGET_VERSION}: {report['status']}")
    return 0 if report["status"] in {"PLANNED", "PASS"} else 4


if __name__ == "__main__":
    raise SystemExit(main())
