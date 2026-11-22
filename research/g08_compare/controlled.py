"""Bindings and archive checks for the recorded one-shot G08 development runs."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
G08_POLICY = HERE / "policy.json"
INVENTORY = HERE / "source-inventory.json"
G08_IDS = {"g08-tet10-before", "g08-tet10-after", "g08-tet10-before-retry-001"}
WORKTREE_IDS = {"g08_before": "g08-tet10-before", "g08_after": "g08-tet10-after"}


class G08IdentityError(ValueError):
    """A source, input, policy, or run identity did not match the frozen contract."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_policy() -> dict[str, Any]:
    value = json.loads(G08_POLICY.read_text(encoding="utf-8"))
    if value.get("schema") != "qf-g08-comparison-policy-v1":
        raise G08IdentityError("unsupported G08 comparison policy")
    if value.get("status") not in {
        "DEVELOPMENT_AUTONOMOUS_AUTHORIZED",
        "DEVELOPMENT_ATTEMPTS_CONSUMED",
    }:
        raise G08IdentityError("G08 policy is not bound to a recognized development status")
    scopes = value.get("scopes")
    expected_scope_ids = [
        "g08-tet10-before",
        "g08-tet10-after",
        "g08-tet10-before-retry-001",
    ]
    if not isinstance(scopes, list) or [item.get("id") for item in scopes] != expected_scope_ids:
        raise G08IdentityError("G08 must preserve both original scopes and append the single before retry")
    if any(item.get("attempts") != 1 for item in scopes):
        raise G08IdentityError("each G08 scope is limited to one attempt")
    contract_sha256 = value.get("contract_sha256")
    if not isinstance(contract_sha256, str) or sha256_file(HERE / "contract.json") != contract_sha256:
        raise G08IdentityError("G08 contract SHA-256 differs from the registered policy")

    summary_relative = "results/controlled-ab-retry-2026-11-22.json"
    summary_sha256 = value.get("comparison_summary_sha256")
    summary_path = HERE / summary_relative
    if (
        value.get("comparison_summary") != summary_relative
        or not isinstance(summary_sha256, str)
        or len(summary_sha256) != 64
        or not summary_path.is_file()
        or sha256_file(summary_path) != summary_sha256
    ):
        raise G08IdentityError("G08 A/B summary is missing or differs from its registered digest")
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise G08IdentityError("G08 A/B summary is unreadable") from exc

    before, after, retry = scopes
    before_result = summary.get("before_retry", {})
    after_result = summary.get("after", {})
    historical = summary.get("historical_before_attempt", {})
    comparison = summary.get("comparison", {})
    if (
        summary.get("schema") != "qf-g08-controlled-ab-retry-summary-v1"
        or summary.get("classification") != "DEVELOPMENT_AUTONOMOUS"
        or summary.get("qualification") != "NOT_APPLICABLE_DEVELOPMENT_ONLY"
        or comparison.get("status") != "VALID_DEVELOPMENT_OBSERVATION_NOT_QUALIFICATION"
        or historical.get("runner_status") != "PYTEST_FAILED"
        or historical.get("preserved_without_rewrite") is not True
        or retry.get("source") != before.get("source")
        or retry.get("inputs") != before.get("inputs")
        or retry.get("mesh") != before.get("mesh")
        or retry.get("source") != before_result.get("source_commit")
        or retry.get("inputs") != before_result.get("inputs_sha256")
        or retry.get("preflight_sha256") != before_result.get("preflight", {}).get("sha256")
        or retry.get("ledger_sha256") != before_result.get("ledger_sha256")
        or retry.get("run_sha256") != before_result.get("run_sha256")
        or retry.get("result_sha256") != before_result.get("result_sha256")
        or retry.get("verdict") != "G08_RESULT_ARCHIVED"
        or after.get("source") != after_result.get("source_commit")
        or after.get("inputs") != after_result.get("inputs_sha256")
        or after_result.get("first_mode_status") != "FIRST_MODE_NOT_ESTABLISHED"
        or before_result.get("first_mode_status") != "FIRST_MODE_NOT_ESTABLISHED"
    ):
        raise G08IdentityError("G08 summary identity or historical verdict differs from the policy")
    return value


def scope_for(scope_id: str, policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if scope_id not in G08_IDS:
        raise G08IdentityError(f"unknown G08 scope: {scope_id}")
    policy = read_policy() if policy is None else policy
    matches = [scope for scope in policy["scopes"] if scope["id"] == scope_id]
    if len(matches) != 1:
        raise G08IdentityError("G08 scope identity is missing or duplicated")
    return dict(matches[0])


def scope_id_for_worktree(worktree_id: str) -> str:
    try:
        return WORKTREE_IDS[worktree_id]
    except KeyError as exc:
        raise G08IdentityError(f"unknown G08 worktree ID: {worktree_id}") from exc


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        raise G08IdentityError(f"Git identity command failed: {args[0]}")
    return completed.stdout.strip()


def _worktree_for_branch(branch: str) -> Path:
    output = _git(ROOT, "worktree", "list", "--porcelain")
    matches: list[Path] = []
    current_path: Path | None = None
    for line in output.splitlines() + [""]:
        if line.startswith("worktree "):
            current_path = Path(line.removeprefix("worktree ")).resolve()
        elif line.startswith("branch ") and line.removeprefix("branch ") == f"refs/heads/{branch}":
            if current_path is not None:
                matches.append(current_path)
        elif not line:
            current_path = None
    if len(matches) != 1:
        raise G08IdentityError(f"expected one registered source worktree for branch {branch}")
    return matches[0]


def source_identity(scope: Mapping[str, Any]) -> dict[str, Any]:
    root = _worktree_for_branch(str(scope["source_branch"]))
    branch = _git(root, "branch", "--show-current")
    commit = _git(root, "rev-parse", "HEAD")
    tree = _git(root, "rev-parse", "HEAD^{tree}")
    src_tree = _git(root, "rev-parse", "HEAD:src")
    status = _git(root, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise G08IdentityError("registered G08 source worktree is not clean")
    if branch != scope["source_branch"] or commit != scope["source"]:
        raise G08IdentityError("registered G08 source branch or commit differs from policy")
    if tree != scope["source_tree"] or src_tree != scope["solver_tree"]:
        raise G08IdentityError("registered G08 Git tree differs from policy")
    actual_inventory = _source_inventory(root, commit)
    frozen_inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    expected_inventory = frozen_inventory.get("scopes", {}).get(scope["id"])
    if actual_inventory != expected_inventory:
        raise G08IdentityError("registered G08 source inventory differs from the frozen inventory")
    return {
        "root": str(root),
        "branch": branch,
        "commit": commit,
        "tree": tree,
        "solver_tree": src_tree,
        "inventory_sha256": sha256_bytes(
            json.dumps(actual_inventory, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ),
    }


def _source_inventory(root: Path, commit: str) -> dict[str, Any]:
    listing = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-r", "-z", commit, "--", "src", "scripts/run_g08_high_order_analytical.py"],
        check=False,
        capture_output=True,
    )
    if listing.returncode:
        raise G08IdentityError("cannot enumerate the registered G08 source inventory")
    files: list[dict[str, str]] = []
    for raw in listing.stdout.split(b"\0"):
        if not raw:
            continue
        metadata, raw_path = raw.split(b"\t", 1)
        mode, kind, blob = metadata.decode("ascii").split()
        path = raw_path.decode("utf-8")
        if kind == "blob" and (path.startswith("src/") or path == "scripts/run_g08_high_order_analytical.py"):
            files.append({"path": path, "mode": mode, "blob": blob})
    return {
        "commit": commit,
        "file_count": len(files),
        "files_sha256": sha256_bytes(
            json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ),
        "generator_blob": next(
            (item["blob"] for item in files if item["path"] == "scripts/run_g08_high_order_analytical.py"),
            None,
        ),
    }


def case_receipt(scope: Mapping[str, Any], source_root: Path) -> dict[str, Any]:
    case_path = HERE / "case.py"
    command = [os.fspath(Path(os.sys.executable)), "-B", str(case_path), str(source_root), str(scope["id"])]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        check=False,
        timeout=30,
        env={
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONPATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"}
        },
    )
    if completed.returncode or len(completed.stdout) > 1_048_576 or len(completed.stderr) > 1_048_576:
        raise G08IdentityError("G08 input preflight failed or exceeded its output cap")
    try:
        receipt = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise G08IdentityError("G08 input preflight did not return a JSON receipt") from exc
    expected = {
        "scope": scope["id"],
        "source": scope["source"],
        "solver_tree": scope["solver_tree"],
        "generator_blob": scope["generator_blob"],
        "mesh_sha256": scope["mesh"],
        "inputs_sha256": scope["inputs"],
        "common_sha256": read_policy()["paired_inputs_sha256"],
        "compatibility": "SUPPORTED_ROUTE",
        "nodes": scope["nodes"],
        "elements": scope["elements"],
        "bodies_executed": False,
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise G08IdentityError("G08 source input receipt differs from the registered contract")
    if not isinstance(receipt.get("free_dofs"), int) or receipt["free_dofs"] != scope["free_dofs"]:
        raise G08IdentityError("G08 free-degree-of-freedom count differs from the contract")
    return receipt


def validate_archive(
    result_root: Path,
    *,
    scope: Mapping[str, Any],
    receipt: Mapping[str, Any],
    pytest_status: str,
) -> dict[str, Any]:
    """Validate a result or an archived solve exception without inferring success."""
    result_path = result_root / "result.json"
    failure_path = result_root / "failure.json"
    expected_identity = {
        "scope": scope["id"],
        "source": scope["source"],
        "inputs_sha256": scope["inputs"],
    }
    if failure_path.is_file() and not result_path.exists():
        try:
            failure = json.loads(failure_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return _invalid("failure.json is unreadable")
        if any(failure.get(key) != value for key, value in expected_identity.items()):
            return _invalid("failure archive identity differs from the registered inputs")
        if not isinstance(failure.get("exception_type"), str) or not isinstance(failure.get("message"), str):
            return _invalid("failure archive is incomplete")
        return {
            "archive_validation": "FAILURE_ARCHIVED",
            "archive_errors": [],
            "archive_files": _inventory(result_root),
            "preload_status": "NOT_REPORTED",
            "spectral_status": "SOLVER_EXCEPTION",
            "solver_status": "EXCEPTION",
            "screen_status": "NOT_EVALUATED",
            "first_mode_status": "FIRST_MODE_NOT_ESTABLISHED",
            "failure": {"exception_type": failure["exception_type"], "message": failure["message"]},
            "pytest_status": pytest_status,
        }
    if not result_path.is_file():
        return _invalid("result.json is absent")
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _invalid("result.json is unreadable")
    if not isinstance(result, dict) or any(result.get(key) != value for key, value in expected_identity.items()):
        return _invalid("result identity differs from the registered inputs")
    if result.get("mode_rank") != "NOT_ESTABLISHED":
        return _invalid("result changed the unqualified first-mode status")
    diagnostics = result.get("diagnostics")
    if not isinstance(diagnostics, dict):
        return _invalid("solver diagnostics are absent or malformed")
    solver_status = result.get("solver_status")
    if not isinstance(solver_status, str):
        return _invalid("solver status is absent")
    preload_status = _preload_status(diagnostics)
    if solver_status != "PASS":
        return {
            "archive_validation": "VALID_SOLVER_NON_PASS",
            "archive_errors": [],
            "archive_files": _inventory(result_root),
            "preload_status": preload_status,
            "spectral_status": "SOLVER_NON_PASS",
            "solver_status": solver_status,
            "screen_status": "NOT_EVALUATED",
            "first_mode_status": "FIRST_MODE_NOT_ESTABLISHED",
            "pytest_status": pytest_status,
            "diagnostics": diagnostics,
        }
    mode_path = result_root / "mode.npy"
    if not mode_path.is_file() or result.get("mode_sha256") != sha256_file(mode_path):
        return _invalid("mode.npy is absent or its SHA-256 differs")
    try:
        mode = np.load(mode_path, allow_pickle=False)
    except (OSError, ValueError):
        return _invalid("mode.npy cannot be read without pickle")
    if mode.size != int(scope["nodes"]) * 3 or not np.isfinite(mode).all():
        return _invalid("mode.npy has an invalid shape or non-finite entries")
    try:
        factor = float(result["factor"])
        signed_load = float(result["signed_load"])
        magnitude = float(result["magnitude"])
        residual = float(result["residual"])
        euler_error = float(result["euler_relative_error"])
        diag_factor = float(diagnostics["critical_factor"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return _invalid("critical spectral metrics are missing or malformed")
    if not all(math.isfinite(value) for value in (factor, signed_load, magnitude, residual, euler_error, diag_factor)):
        return _invalid("critical spectral metrics contain non-finite values")
    if factor <= 0 or residual < 0 or euler_error < 0 or factor != diag_factor:
        return _invalid("critical spectral metrics violate the registered result contract")
    bracket = diagnostics.get("critical_bracket")
    if not isinstance(bracket, dict) or not isinstance(bracket.get("method"), str) or not diagnostics.get("backend"):
        return _invalid("spectral method or bracket is not archived")
    try:
        diagnostic_residual = float(diagnostics["critical_mode_residual_relative"])
        bracket_lower = float(bracket["lower"])
        bracket_upper = float(bracket["upper"])
        contract = json.loads((HERE / "contract.json").read_text(encoding="utf-8"))
        euler_reference = float(contract["evaluation"]["euler_reference_force"])
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError, OverflowError):
        return _invalid("spectral residual, bracket, or registered Euler reference is missing")
    if (
        not all(math.isfinite(value) for value in (diagnostic_residual, bracket_lower, bracket_upper, euler_reference))
        or diagnostic_residual < 0
        or bracket_lower < 0
        or bracket_upper < bracket_lower
        or euler_reference <= 0
    ):
        return _invalid("spectral residual or bracket is malformed")
    if not math.isclose(residual, diagnostic_residual, rel_tol=1e-12, abs_tol=1e-15):
        return _invalid("archived residual differs from the solver diagnostic")
    bracket_tolerance = max(abs(factor), 1.0) * 1e-10
    if factor < bracket_lower - bracket_tolerance or factor > bracket_upper + bracket_tolerance:
        return _invalid("critical factor is outside its archived bracket")
    expected_load = float(receipt["resultant_ux"]) * factor
    if not math.isclose(signed_load, expected_load, rel_tol=1e-12, abs_tol=1e-12):
        return _invalid("signed critical load does not match the registered unit-resultant load")
    if not math.isclose(magnitude, abs(expected_load), rel_tol=1e-12, abs_tol=1e-12):
        return _invalid("critical-load magnitude does not match the signed load")
    expected_euler_error = abs(magnitude - euler_reference) / euler_reference
    if not math.isclose(euler_error, expected_euler_error, rel_tol=1e-12, abs_tol=1e-12):
        return _invalid("Euler relative error differs from the registered reference and critical load")
    return {
        "archive_validation": "VALID",
        "archive_errors": [],
        "archive_files": _inventory(result_root),
        "preload_status": preload_status,
        "spectral_status": "COMPUTED",
        "solver_status": solver_status,
        "critical_factor": factor,
        "critical_load_signed": signed_load,
        "critical_load_magnitude": magnitude,
        "critical_mode_residual_relative": residual,
        "euler_relative_error": euler_error,
        "screen_status": "SCREEN_PASS" if residual <= 1e-7 and euler_error <= 0.10 else "SCREEN_OUTSIDE_BAND",
        "eigen_backend": diagnostics.get("backend"),
        "eigen_formulation": diagnostics.get("eigen_formulation"),
        "critical_bracket": diagnostics["critical_bracket"],
        "preload_diagnostics": diagnostics.get("preload_diagnostics"),
        "mode_sha256": result["mode_sha256"],
        "mode_rank": "NOT_ESTABLISHED",
        "first_mode_status": "FIRST_MODE_NOT_ESTABLISHED",
        "pytest_status": pytest_status,
    }


def _preload_status(diagnostics: Mapping[str, Any]) -> str:
    preload = diagnostics.get("preload_diagnostics")
    if not isinstance(preload, dict) or not isinstance(preload.get("increments"), list):
        return "NOT_REPORTED"
    increments = preload["increments"]
    if preload.get("converged") is not True or len(increments) != 4:
        return "NON_CONVERGED"
    try:
        factors = [float(item["load_factor"]) for item in increments]
        residuals = [float(item["relative_residual"]) for item in increments]
    except (KeyError, TypeError, ValueError, OverflowError):
        return "NON_CONVERGED"
    expected = [0.25, 0.5, 0.75, 1.0]
    if any(not math.isclose(a, b, rel_tol=0, abs_tol=1e-12) for a, b in zip(factors, expected, strict=True)):
        return "NON_CONVERGED"
    if any(not math.isfinite(value) or value < 0 or value > 1e-8 for value in residuals):
        return "NON_CONVERGED"
    return "CONVERGED"


def _inventory(directory: Path) -> list[dict[str, Any]]:
    return [
        {"path": path.name, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in sorted(directory.iterdir())
        if path.is_file()
    ]


def _invalid(error: str) -> dict[str, Any]:
    return {
        "archive_validation": "INVALID",
        "archive_errors": [error],
        "archive_files": [],
        "preload_status": "NOT_REPORTED",
        "spectral_status": "NOT_REPORTED",
        "solver_status": "NOT_REPORTED",
        "screen_status": "NOT_EVALUATED",
        "first_mode_status": "FIRST_MODE_NOT_ESTABLISHED",
    }
