"""Fail-closed preparation plan for a future WP06-D requalification.

This module intentionally contains no execution path in the current task.
Owner authorization and CPU availability are required before a future runner
may bind the frozen M1/M2/M3 campaign to the governing branch.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def _git(cwd: Path, *args: str) -> str:
    """Read Git state from disk rather than trusting execution-caller values."""

    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PermissionError("Unable to independently inspect WP06-D Git provenance.") from exc
    return completed.stdout.strip()


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def build_requalification_plan() -> dict[str, Any]:
    """Return the future sequence and its fail-closed gate dependencies."""

    return {
        "execution": "PREPARED_NOT_EXECUTED",
        "owner_authorization_required": True,
        "current_r1_execution_contract": "PHASE_0_PREPARATION_ONLY",
        "legacy_r1_runner": "QUARANTINED_STALE_MONITOR_AND_SHARED_OUTPUT_PATHS",
        "r2_contract": "REQUIRED_NOT_CREATED",
        "r2_owner_authorization": "REQUIRED_NOT_PRESENT",
        "provenance_validation": "GUARD_QUERIES_GIT_BRANCH_HEAD_AND_DIRTY_STATE",
        "owner_grant_storage": "EXTERNAL_TO_REPOSITORY",
        "levels": ["M1", "M2", "M3"],
        "m3_gate": "M3 runs only after M1 and M2 pass all frozen gates",
        "monitor": "mean crown UZ at frozen nodes (2,3,4)",
        "accepted_state_archive": "every accepted state, lossless displacement plus diagnostics",
        "equilibrium": "independent vector force/moment reconstruction per accepted state",
        "physics": "reuse frozen WP06-D R1 geometry/material/load/thresholds",
        "execution_policy": "governing integrated 0.2.9 policy, bound by SHA/digest",
        "output_safety": "new source-and-contract-specific directory; refuse existing output",
        "provenance_gate": "clean tree and exact branch/SHA/contract/policy digest match",
        "no_undeclared_m4": True,
    }


def require_owner_authorization(owner_authorized: bool) -> None:
    """Refuse all future execution unless explicit authorization is supplied."""

    if not owner_authorized:
        raise PermissionError("WP06-D requalification requires explicit Owner authorization.")


def validate_phase1_authorization(
    *,
    contract_path: str | Path,
    authorization_path: str | Path,
    output_root: str | Path,
    source_sha: str,
    branch: str,
    working_tree_clean: bool,
) -> dict[str, Any]:
    """Validate a committed, exact-scope Owner grant before any structural solve.

    The historical R1 contract is preparation-only and intentionally cannot
    satisfy this gate. The authorization binds the exact current source,
    branch, contract bytes, policy digest, and conditional M1/M2/M3 sequence.
    """

    contract_file = Path(contract_path)
    authorization_file = Path(authorization_path)
    destination_input = Path(output_root)
    if not contract_file.is_file():
        raise PermissionError("No frozen WP06-D Phase-1 R2 execution contract is present.")
    if not authorization_file.is_file():
        raise PermissionError("No explicit Owner authorization artifact is present.")

    contract_file = contract_file.resolve()
    authorization_file = authorization_file.resolve()
    try:
        repo_root = Path(_git(contract_file.parent, "rev-parse", "--show-toplevel")).resolve()
        contract_relative = contract_file.relative_to(repo_root)
    except (OSError, ValueError, PermissionError) as exc:
        raise PermissionError("WP06-D contract is not inside a discoverable Git worktree.") from exc

    if not destination_input.is_absolute():
        destination_input = repo_root / destination_input

    actual_branch = _git(repo_root, "branch", "--show-current")
    actual_source_sha = _git(repo_root, "rev-parse", "HEAD")
    actual_dirty = bool(_git(repo_root, "status", "--porcelain=v1", "--untracked-files=all"))
    if not actual_branch or branch != actual_branch:
        raise PermissionError("WP06-D supplied branch does not match the current Git branch.")
    if not source_sha or source_sha != actual_source_sha:
        raise PermissionError("WP06-D supplied source_sha does not match Git HEAD.")

    if _is_relative_to(authorization_file, repo_root):
        raise PermissionError("Owner authorization must be supplied outside the repository.")

    frozen_output_root = (repo_root / "qualification" / "0_2_9" / "wp06d_r2_runs").resolve()
    if destination_input.is_symlink():
        raise PermissionError("WP06-D output path must not be a symbolic link.")
    destination = destination_input.resolve()
    if not _is_relative_to(destination, frozen_output_root) or destination == frozen_output_root:
        raise PermissionError("WP06-D output must be a new child of qualification/0_2_9/wp06d_r2_runs.")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Refusing to reuse or overwrite WP06-D evidence directory: {destination}")

    if not working_tree_clean or actual_dirty:
        raise PermissionError("WP06-D execution requires a clean working tree.")
    try:
        _git(repo_root, "ls-files", "--error-unmatch", contract_relative.as_posix())
    except PermissionError as exc:
        raise PermissionError("WP06-D execution contract must be committed at Git HEAD.") from exc

    try:
        contract = json.loads(contract_file.read_text(encoding="utf-8"))
        authorization = json.loads(authorization_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PermissionError("WP06-D contract or Owner authorization is unreadable.") from exc
    if not isinstance(contract, dict) or not isinstance(authorization, dict):
        raise PermissionError("WP06-D contract and Owner authorization must be JSON objects.")

    execution = contract.get("execution_guard", {})
    if (
        contract.get("contract_revision") != "WP06D-R2"
        or contract.get("phase") != "PHASE_1_EXECUTION"
        or contract.get("status") != "FROZEN_FOR_EXECUTION"
        or not isinstance(execution, dict)
        or execution.get("structural_solves_enabled") is not True
    ):
        raise PermissionError("WP06-D contract is not frozen and enabled for Phase-1 structural execution.")

    contract_digest = hashlib.sha256(contract_file.read_bytes()).hexdigest()
    policy_digest = contract.get("solver_policy_digest")
    expected_levels = ["M1", "M2", "M3"]
    required_authorization = {
        "status": "AUTHORIZED",
        "owner_authorized": True,
        "contract_revision": "WP06D-R2",
        "branch": actual_branch,
        "source_sha": actual_source_sha,
        "contract_sha256": contract_digest,
        "solver_policy_digest": policy_digest,
        "authorized_levels": expected_levels,
        "m3_conditional_on_m1_m2_reference_replay": True,
    }
    for key, expected in required_authorization.items():
        if authorization.get(key) != expected:
            raise PermissionError(f"WP06-D Owner authorization mismatch for {key}.")
    if not isinstance(policy_digest, str) or len(policy_digest) != 64:
        raise PermissionError("WP06-D frozen solver policy digest is missing or malformed.")
    try:
        int(policy_digest, 16)
    except ValueError as exc:
        raise PermissionError("WP06-D frozen solver policy digest is not hexadecimal.") from exc

    return {
        "status": "AUTHORIZED_PREFLIGHT_PASS",
        "branch": actual_branch,
        "source_sha": actual_source_sha,
        "repo_root": str(repo_root),
        "contract_sha256": contract_digest,
        "solver_policy_digest": policy_digest,
        "authorized_levels": expected_levels,
        "output_root": str(destination),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(build_requalification_plan(), sort_keys=True))
