"""Plan an explicit package scope from Git blobs; never publish or waive gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 compatibility.
    import tomli as tomllib

if __package__:
    from scripts.audit_release_archive import _scan_member
    from scripts.git_tools import git_run
    from scripts.review_vocabulary import FORBIDDEN_TERMS, TEXT_SUFFIXES
else:
    from audit_release_archive import _scan_member  # type: ignore[no-redef]
    from git_tools import git_run  # type: ignore[no-redef]
    from review_vocabulary import FORBIDDEN_TERMS, TEXT_SUFFIXES  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]


def _relative_path(value: str, *, prefix: bool = False) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("A portable relative path is required.")
    if prefix and not value.endswith("/"):
        raise ValueError("Directory prefixes must end with '/'.")
    normalized = value[:-1] if prefix else value
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in ("", ".", "..") for part in normalized.split("/")):
        raise ValueError("Absolute, empty and traversing paths are forbidden.")
    if path.as_posix() != normalized:
        raise ValueError("The path is not canonical.")
    return value


def select_paths(tree: dict[str, tuple[str, str]], selection: dict[str, Any]) -> list[str]:
    """Select exact Git paths, rejecting missing, ambiguous or unsafe entries."""
    exact = [_relative_path(value) for value in selection["include_exact"]]
    prefixes = [_relative_path(value, prefix=True) for value in selection["include_prefixes"]]
    excluded = [_relative_path(value) for value in selection["exclude_exact"]]
    forbidden = [_relative_path(value, prefix=True) for value in selection["forbid_prefixes"]]
    for values in (exact, prefixes, excluded, forbidden):
        if len(values) != len(set(values)):
            raise ValueError("Duplicate scope entries are forbidden.")
    missing = sorted(set(exact) - tree.keys())
    if missing:
        raise ValueError(f"Required files are absent: {missing}")
    for prefix in prefixes:
        if not any(path.startswith(prefix) for path in tree):
            raise ValueError(f"Required prefix is empty: {prefix}")
    paths = set(exact)
    paths.update(path for path in tree if path.startswith(tuple(prefixes)))
    if not set(excluded).issubset(paths):
        raise ValueError("Every exclusion must identify a selected existing file.")
    paths.difference_update(excluded)
    if not paths:
        raise ValueError("The public package selection is empty.")
    seen: set[str] = set()
    for path in sorted(paths):
        _relative_path(path)
        if path.startswith(tuple(forbidden)):
            raise ValueError(f"A forbidden prefix was selected: {path}")
        if tree[path][0] not in ("100644", "100755"):
            raise ValueError(f"Symlinks and non-regular Git entries are forbidden: {path}")
        key = path.casefold()
        if key in seen:
            raise ValueError("Selected paths collide on a case-insensitive filesystem.")
        seen.add(key)
    return sorted(paths)


def scan_selected_payloads(payloads: dict[str, bytes]) -> dict[str, Any]:
    """Use existing strict release scans, with no historical vocabulary waiver."""
    findings: list[dict[str, Any]] = []
    for path, payload in sorted(payloads.items()):
        findings.extend(_scan_member(path, payload))
        if Path(path).suffix.lower() in TEXT_SUFFIXES:
            content = payload.decode("utf-8", errors="replace").casefold()
            if any(term in content for term in FORBIDDEN_TERMS):
                findings.append({"identifier": "review_vocabulary", "path": path, "line": 0})
    return {
        "status": "FAIL" if findings else "PASS",
        "scanned_files": len(payloads),
        "findings": findings,
    }


def package_input_gaps(
    payloads: dict[str, bytes], *, source_paths: Sequence[str] | None = None,
) -> list[str]:
    """Check selected package metadata inputs without importing the solver."""
    if "pyproject.toml" not in payloads:
        return ["pyproject.toml"]
    metadata = tomllib.loads(payloads["pyproject.toml"].decode("utf-8"))
    project = metadata["project"]
    required = list(project.get("license-files", []))
    readme = project.get("readme")
    if isinstance(readme, str):
        required.append(readme)
    elif isinstance(readme, dict) and "file" in readme:
        required.append(readme["file"])
    data_files = metadata.get("tool", {}).get("setuptools", {}).get("data-files", {})
    required.extend(path for paths in data_files.values() for path in paths)
    available = set(payloads) if source_paths is None else set(source_paths)
    gaps: set[str] = set()
    for pattern in required:
        _relative_path(pattern)
        parts = pattern.split("/")
        if "**" in parts:
            raise ValueError("Recursive package globs require an explicit coverage rule.")
        matches = {
            path for path in available
            if len(path.split("/")) == len(parts)
            and all(fnmatchcase(value, part) for value, part in zip(path.split("/"), parts))
        }
        if not matches:
            gaps.add(pattern)
        else:
            gaps.update(matches - payloads.keys())
    return sorted(gaps)


def plan_public_package(root: Path, contract_path: Path) -> dict[str, Any]:
    """Read a preparation contract and map every selected immutable source blob.

    A successful scan is not package-build evidence, a release approval, or a
    replacement for the existing whole-repository audits. Nothing is written.
    """
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    if contract["status"] != "PREPARATION_ONLY":
        raise ValueError("This planner accepts preparation contracts only, not execution authorizations.")
    source = contract["source_sha"]
    if not isinstance(source, str) or not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("An exact source commit SHA is required.")
    resolved = git_run(["rev-parse", "--verify", f"{source}^{{commit}}"], cwd=root, check=True, text=True)
    if resolved.stdout.strip() != source:
        raise ValueError("Source identity mismatch.")
    raw_tree = git_run(["ls-tree", "-r", "-z", source], cwd=root, check=True).stdout
    tree: dict[str, tuple[str, str]] = {}
    for entry in raw_tree.split(b"\0"):
        if not entry:
            continue
        metadata, path_bytes = entry.split(b"\t", 1)
        mode, kind, blob = metadata.decode("ascii").split()
        # Keep non-regular entries visible so selection cannot silently omit them.
        tree[path_bytes.decode("utf-8")] = (mode if kind == "blob" else kind, blob)
    paths = select_paths(tree, contract["selection"])
    payloads: dict[str, bytes] = {}
    mapping: list[dict[str, Any]] = []
    for path in paths:
        mode, blob = tree[path]
        payload = git_run(["cat-file", "blob", blob], cwd=root, check=True).stdout
        payloads[path] = payload
        mapping.append({
            "path": path, "mode": mode, "git_blob": blob,
            "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload),
        })
    scan = scan_selected_payloads(payloads)
    gaps = package_input_gaps(payloads, source_paths=list(tree))
    metadata = tomllib.loads(payloads["pyproject.toml"].decode("utf-8")) if "pyproject.toml" in payloads else {}
    return {
        "schema_version": 1,
        "status": "PREPARATION_ONLY" if scan["status"] == "PASS" and not gaps else "FAIL_CLOSED_PREPARATION",
        "source_sha": source,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "selected_files": len(mapping),
        "mapping": mapping,
        "public_source_scan": scan,
        "missing_package_inputs": gaps,
        "package_version": metadata.get("project", {}).get("version"),
        "formal_execution_authorized": False,
        "whole_repository_gates_changed": False,
        "publication_performed": False,
        "next_step": "Freeze a separate prospective execution contract, then stage/build/test the selected package.",
    }


def preview_public_package_worktree(root: Path, contract_path: Path) -> dict[str, Any]:
    """Scan the selected current bytes without claiming a frozen execution SHA.

    This additive preview never replaces the immutable-source planner, a wheel
    build, the whole-repository audits, or a separate Owner scope decision.
    """
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    if contract["status"] != "PREPARATION_ONLY":
        raise ValueError("A worktree preview accepts preparation contracts only.")
    source = contract["source_sha"]
    if not isinstance(source, str) or not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("An exact preparation baseline SHA is required.")
    resolved = git_run(["rev-parse", "--verify", f"{source}^{{commit}}"], cwd=root, check=True, text=True)
    if resolved.stdout.strip() != source:
        raise ValueError("Preparation baseline identity mismatch.")
    baseline: dict[str, tuple[str, str]] = {}
    raw_tree = git_run(["ls-tree", "-r", "-z", source], cwd=root, check=True).stdout
    for entry in raw_tree.split(b"\0"):
        if not entry:
            continue
        metadata, relative = entry.split(b"\t", 1)
        mode, kind, blob = metadata.decode("ascii").split()
        baseline[relative.decode("utf-8")] = (mode if kind == "blob" else kind, blob)
    current_paths = git_run(
        ["ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root, check=True,
    ).stdout.decode("utf-8").split("\0")
    current: dict[str, tuple[str, str]] = {}
    for path in sorted(set(current_paths) - {""}):
        candidate = root / path
        mode = "120000" if candidate.is_symlink() else baseline.get(path, ("100644", ""))[0]
        current[path] = (mode, baseline.get(path, ("", ""))[1])
    paths = select_paths(current, contract["selection"])
    payloads: dict[str, bytes] = {}
    mapping: list[dict[str, Any]] = []
    for path in paths:
        candidate = root / path
        actual = candidate.resolve(strict=True)
        if not actual.is_relative_to(root.resolve()) or not actual.is_file() or candidate.is_symlink():
            raise ValueError(f"A selected current path is not a regular file within the root: {path}")
        payload = actual.read_bytes()
        payloads[path] = payload
        # Source repos bound by a 40-character commit SHA use Git SHA-1 objects.
        current_blob = hashlib.sha1(b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()
        base_blob = baseline.get(path, ("", ""))[1] or None
        mapping.append({
            "path": path, "preparation_baseline_git_blob": base_blob,
            "worktree_sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload), "matches_baseline_blob_bytes": current_blob == base_blob,
            "absent_from_preparation_baseline": base_blob is None,
        })
    scan = scan_selected_payloads(payloads)
    gaps = package_input_gaps(payloads, source_paths=list(current))
    encoded_mapping = json.dumps(mapping, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "schema_version": 1,
        "status": "PASS_PREPARATION_WORKTREE_PREVIEW" if scan["status"] == "PASS" and not gaps else "FAIL_CLOSED_PREPARATION_PREVIEW",
        "evidence_kind": "CURRENT_BYTES_PREVIEW_NOT_FORMAL_EXECUTION",
        "preparation_baseline_sha": source,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "selected_files": len(mapping), "mapping": mapping,
        "mapping_sha256": hashlib.sha256(encoded_mapping).hexdigest(),
        "changed_or_new_selected_files": [row["path"] for row in mapping if not row["matches_baseline_blob_bytes"]],
        "public_source_scan": scan, "missing_package_inputs": gaps,
        "formal_execution_authorized": False, "whole_repository_gates_changed": False,
        "archive_or_package_build_performed": False, "publication_performed": False,
        "next_step": "Commit and prospectively freeze the selected source, then attest its actual build/install/CLI/archive gates before Owner review.",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--worktree-preview", action="store_true", help="Scan current selected bytes; no frozen execution identity or release claim.")
    args = parser.parse_args(argv)
    try:
        report = preview_public_package_worktree(args.root, args.contract) if args.worktree_preview else plan_public_package(args.root, args.contract)
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"PREPARATION_ONLY", "PASS_PREPARATION_WORKTREE_PREVIEW"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
