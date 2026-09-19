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
from pathlib import PurePosixPath
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


def _git_bytes(cwd: Path, *args: str) -> bytes:
    """Read exact committed blob bytes, independent of checkout line endings."""

    try:
        completed = subprocess.run(
            ["git", *args], cwd=cwd, check=True, capture_output=True
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PermissionError("Unable to independently inspect committed WP06-D bytes.") from exc
    return completed.stdout


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_policy_binding(repo_root: Path, contract: dict[str, Any], head: str) -> tuple[str, str]:
    """Recompute the frozen policy digest from exact Git blobs in its source commit."""

    binding = contract.get("solver_policy_binding")
    if not isinstance(binding, dict):
        raise PermissionError("WP06-D contract has no independently verifiable solver policy binding.")
    source_sha = binding.get("source_sha")
    file_hashes = binding.get("source_file_sha256")
    expected_digest = binding.get("policy_digest")
    if not isinstance(source_sha, str) or len(source_sha) != 40:
        raise PermissionError("WP06-D policy source SHA is missing or malformed.")
    try:
        int(source_sha, 16)
    except ValueError as exc:
        raise PermissionError("WP06-D policy source SHA is not hexadecimal.") from exc
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", source_sha, head],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PermissionError("WP06-D policy source is not an ancestor of the execution HEAD.") from exc
    if not isinstance(file_hashes, dict) or not file_hashes:
        raise PermissionError("WP06-D policy source file digest map is missing.")
    observed: dict[str, str] = {}
    for raw_path, expected_hash in sorted(file_hashes.items()):
        if not isinstance(raw_path, str) or not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise PermissionError("WP06-D policy file digest entry is malformed.")
        path = PurePosixPath(raw_path)
        if path.is_absolute() or ".." in path.parts or not path.parts or "\\" in raw_path or ":" in raw_path:
            raise PermissionError("WP06-D policy source paths must be safe repository-relative paths.")
        try:
            int(expected_hash, 16)
            blob = _git_bytes(repo_root, "show", f"{source_sha}:{path.as_posix()}")
        except (ValueError, PermissionError) as exc:
            raise PermissionError(f"WP06-D policy source blob is unavailable: {raw_path}") from exc
        observed[raw_path] = _sha256(blob)
        if observed[raw_path] != expected_hash:
            raise PermissionError(f"WP06-D policy source digest mismatch for {raw_path}.")
        execution_blob = _git_bytes(repo_root, "show", f"{head}:{path.as_posix()}")
        if _sha256(execution_blob) != expected_hash:
            raise PermissionError(f"WP06-D execution source differs from frozen policy for {raw_path}.")
    canonical = json.dumps(observed, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    digest = _sha256(canonical)
    if expected_digest != digest:
        raise PermissionError("WP06-D solver policy digest does not match the committed source blobs.")
    return source_sha, digest


def _validate_parent_contract_binding(repo_root: Path, contract: dict[str, Any], head: str) -> None:
    """Verify the R1 parent contract by its exact governing Git blob."""

    parent = contract.get("parent_r1")
    if not isinstance(parent, dict):
        raise PermissionError("WP06-D R2 contract has no immutable R1 parent binding.")
    provenance = contract.get("provenance")
    governing_sha = (
        provenance.get("governing_policy_source_sha") if isinstance(provenance, dict) else None
    )
    raw_path = parent.get("contract_path")
    expected_sha256 = parent.get("contract_sha256_at_execution")
    expected_blob_oid = parent.get("contract_git_blob_at_governing_source")
    if not isinstance(governing_sha, str) or len(governing_sha) != 40:
        raise PermissionError("WP06-D R1 parent governing source SHA is missing or malformed.")
    try:
        int(governing_sha, 16)
    except ValueError as exc:
        raise PermissionError("WP06-D R1 parent governing source SHA is not hexadecimal.") from exc
    if not isinstance(raw_path, str) or not isinstance(expected_sha256, str) or not isinstance(expected_blob_oid, str):
        raise PermissionError("WP06-D R1 parent contract digest binding is incomplete.")
    path = PurePosixPath(raw_path)
    if path.is_absolute() or ".." in path.parts or "\\" in raw_path or ":" in raw_path:
        raise PermissionError("WP06-D R1 parent contract path is not a safe repository-relative path.")
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", governing_sha, head],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        blob = _git_bytes(repo_root, "show", f"{governing_sha}:{path.as_posix()}")
        blob_oid = _git(repo_root, "rev-parse", f"{governing_sha}:{path.as_posix()}")
    except (OSError, subprocess.CalledProcessError, PermissionError) as exc:
        raise PermissionError("WP06-D R1 parent contract blob is unavailable or not ancestral.") from exc
    if _sha256(blob) != expected_sha256 or blob_oid != expected_blob_oid:
        raise PermissionError("WP06-D R1 parent contract digest does not match its governing Git blob.")


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
        "r2_contract": "PREPARATION_ONLY_OWNER_REVIEW_DRAFTED",
        "r2_q_continuity_interpretation": "OWNER_APPROVED_FOR_EXPLORATION_ONLY_NOT_FORMAL_CONTRACT_ACCEPTANCE",
        "r2_static_contract_audit": "OWNER_DECISION_REQUIRED_FOR_SYMMETRY_COMPONENT_AND_MOMENT_CONFIGURATION",
        "independent_reference": "STVK_TET4_ELEMENT_AND_GLOBAL_ASSEMBLY_KERNELS_IMPLEMENTED_NO_PATH_SOLVER",
        "r2_runner": "NOT_CREATED",
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

    contract_blob = _git_bytes(repo_root, "show", f"HEAD:{contract_relative.as_posix()}")
    contract_digest = _sha256(contract_blob)
    _validate_parent_contract_binding(repo_root, contract, actual_source_sha)
    policy_source_sha, policy_digest = _validate_policy_binding(
        repo_root, contract, actual_source_sha
    )
    expected_levels = ["M1", "M2", "M3"]
    required_authorization = {
        "status": "AUTHORIZED",
        "owner_authorized": True,
        "contract_revision": "WP06D-R2",
        "branch": actual_branch,
        "source_sha": actual_source_sha,
        "contract_sha256": contract_digest,
        "policy_source_sha": policy_source_sha,
        "solver_policy_digest": policy_digest,
        "authorized_operations": ["PRODUCTION_STRUCTURAL", "INDEPENDENT_REFERENCE", "REPLAY"],
        "authorized_levels": expected_levels,
        "m3_conditional_on_m1_m2_reference_replay": True,
    }
    for key, expected in required_authorization.items():
        if authorization.get(key) != expected:
            raise PermissionError(f"WP06-D Owner authorization mismatch for {key}.")
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
