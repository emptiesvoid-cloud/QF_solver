"""Audit a prospectively frozen public package and documentation surface only."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

try:
    from scripts.audit_release_archive import PDF_SUFFIXES, TEXT_SUFFIXES as RELEASE_TEXT_SUFFIXES
    from scripts.git_tools import git_run
    from scripts.plan_public_package import package_input_gaps, scan_selected_payloads, select_paths
except ModuleNotFoundError:
    from audit_release_archive import PDF_SUFFIXES, TEXT_SUFFIXES as RELEASE_TEXT_SUFFIXES  # type: ignore[no-redef]
    from git_tools import git_run  # type: ignore[no-redef]
    from plan_public_package import package_input_gaps, scan_selected_payloads, select_paths  # type: ignore[no-redef]


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_STATUS = "FROZEN_CANDIDATE_BUILD"
SCANNABLE_SUFFIXES = frozenset(RELEASE_TEXT_SUFFIXES | PDF_SUFFIXES)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_tree(root: Path, revision: str) -> dict[str, tuple[str, str]]:
    raw_tree = git_run(["ls-tree", "-r", "-z", revision], cwd=root, check=True).stdout
    result: dict[str, tuple[str, str]] = {}
    for entry in raw_tree.split(b"\0"):
        if not entry:
            continue
        metadata, path_bytes = entry.split(b"\t", 1)
        mode, kind, blob = metadata.decode("ascii").split()
        result[path_bytes.decode("utf-8")] = (mode if kind == "blob" else kind, blob)
    return result


def changed_bound_paths(
    source_tree: dict[str, tuple[str, str]],
    execution_tree: dict[str, tuple[str, str]],
    bound_paths: Sequence[str],
) -> list[str]:
    """Compare frozen path entries without building an oversized Git argv."""
    return sorted(path for path in bound_paths if source_tree.get(path) != execution_tree.get(path))


def select_document_paths(
    tree: dict[str, tuple[str, str]], selection: dict[str, Any],
) -> list[str]:
    """Select tracked documentation text/PDF inputs without traversing other roots."""
    prefixes = selection.get("include_prefixes")
    suffixes = selection.get("suffixes")
    if (
        not isinstance(prefixes, list)
        or not prefixes
        or any(not isinstance(prefix, str) or not prefix.startswith("docs/") or not prefix.endswith("/") for prefix in prefixes)
        or len(prefixes) != len(set(prefixes))
    ):
        raise ValueError("Documentation scope must use unique canonical docs/ prefixes only.")
    if (
        not isinstance(suffixes, list)
        or not suffixes
        or any(not isinstance(suffix, str) or suffix.lower() not in SCANNABLE_SUFFIXES for suffix in suffixes)
        or len(suffixes) != len(set(suffix.lower() for suffix in suffixes))
    ):
        raise ValueError("Documentation scope must enumerate unique supported scan suffixes.")
    excluded_prefixes = selection.get("exclude_prefixes", [])
    if (
        not isinstance(excluded_prefixes, list)
        or any(
            not isinstance(prefix, str)
            or not prefix.startswith("docs/")
            or not prefix.endswith("/")
            or ".." in Path(prefix).parts
            for prefix in excluded_prefixes
        )
        or len(excluded_prefixes) != len(set(excluded_prefixes))
    ):
        raise ValueError("Documentation exclusions must use unique canonical docs/ prefixes only.")
    allowed = {suffix.lower() for suffix in suffixes}
    candidates = sorted(
        path for path in tree
        if path.startswith(tuple(prefixes))
        and not path.startswith(tuple(excluded_prefixes))
        and Path(path).suffix.lower() in allowed
    )
    if not candidates:
        raise ValueError("The frozen documentation scope selected no tracked files.")
    exact_scope = {
        "include_exact": candidates,
        "include_prefixes": [],
        "exclude_exact": [],
        "forbid_prefixes": [],
    }
    return select_paths(tree, exact_scope)


def validate_documentation_publication_policy(
    selection: dict[str, Any], policy: dict[str, Any], config_payload: bytes,
) -> None:
    """Bind the excluded source prefix to the frozen MkDocs publication policy."""
    source_prefix = policy.get("excluded_source_prefix")
    pattern = policy.get("mkdocs_exclude_pattern")
    config_path = policy.get("config_path")
    if (
        not isinstance(source_prefix, str)
        or not source_prefix.startswith("docs/")
        or not source_prefix.endswith("/")
        or not isinstance(pattern, str)
        or not isinstance(config_path, str)
        or source_prefix != selection.get("exclude_prefixes", [None])[0]
        or pattern != source_prefix.removeprefix("docs/") + "**"
        or b"exclude_docs: |" not in config_payload
        or pattern.encode("utf-8") not in config_payload
    ):
        raise ValueError("The documentation scan exclusion is not bound to the frozen MkDocs policy.")


def _mapping(
    root: Path,
    tree: dict[str, tuple[str, str]],
    paths: list[str],
) -> tuple[dict[str, bytes], list[dict[str, Any]]]:
    payloads: dict[str, bytes] = {}
    records: list[dict[str, Any]] = []
    for path in paths:
        mode, blob = tree[path]
        payload = git_run(["cat-file", "blob", blob], cwd=root, check=True).stdout
        payloads[path] = payload
        records.append({
            "path": path,
            "mode": mode,
            "git_blob": blob,
            "sha256": sha256(payload),
            "bytes": len(payload),
        })
    return payloads, records


def _redact_findings(scan: dict[str, Any]) -> dict[str, Any]:
    """Keep finding identity and location while omitting potentially private excerpts."""
    return {
        "status": scan["status"],
        "scanned_files": scan["scanned_files"],
        "finding_count": len(scan["findings"]),
        "findings": [
            {key: finding[key] for key in ("identifier", "path", "line") if key in finding}
            for finding in scan["findings"]
        ],
    }


def audit_frozen_public_scope(root: Path, contract_path: Path, output_path: Path) -> dict[str, Any]:
    started_utc = utc_now()
    root = root.resolve(strict=True)
    contract_path = contract_path.resolve(strict=True)
    output_path = output_path.resolve()
    if output_path.is_relative_to(root) or root.is_relative_to(output_path) or output_path.exists():
        raise ValueError("Use a new external output path; the repository and existing evidence are never overwritten.")
    relative_contract = contract_path.relative_to(root).as_posix()
    head = git_run(["rev-parse", "HEAD"], cwd=root, check=True, text=True).stdout.strip()
    committed_contract = git_run(["show", f"{head}:{relative_contract}"], cwd=root, check=True).stdout
    contract_bytes = contract_path.read_bytes()
    if contract_bytes != committed_contract and contract_bytes.replace(b"\r\n", b"\n") != committed_contract:
        raise ValueError("The frozen scope contract differs from its committed bytes.")
    if git_run(["status", "--porcelain", "--untracked-files=all"], cwd=root, check=True).stdout.strip():
        raise ValueError("The frozen public-scope checkout must be clean before scanning.")

    contract = json.loads(committed_contract)
    if contract.get("status") != CONTRACT_STATUS:
        raise ValueError("The contract does not authorize a frozen candidate package scan.")
    if any(contract.get(key) != value for key, value in {
        "package_build_allowed": True,
        "publication_allowed": False,
        "structural_solves_allowed": False,
        "numeric_threshold_changes_allowed": False,
        "whole_repository_gate_waivers_allowed": False,
    }.items()):
        raise ValueError("The contract broadens scope beyond a non-publishing public-surface audit.")
    source = contract.get("source_sha")
    if not isinstance(source, str) or not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("An exact frozen source SHA is required.")
    contract_commit = git_run(
        ["log", "-1", "--format=%H", head, "--", relative_contract], cwd=root, check=True, text=True,
    ).stdout.strip()
    if not contract_commit or git_run(
        ["merge-base", "--is-ancestor", contract_commit, head], cwd=root,
    ).returncode:
        raise ValueError("The frozen contract commit is not an ancestor of the execution commit.")
    if source == contract_commit or git_run(
        ["merge-base", "--is-ancestor", source, contract_commit], cwd=root,
    ).returncode:
        raise ValueError("The contract was not frozen prospectively after its exact source commit.")

    source_tree = git_tree(root, source)
    package_paths = select_paths(source_tree, contract["selection"])
    documentation_selection = contract["documentation_selection"]
    all_docs_paths = select_document_paths(
        source_tree, {**documentation_selection, "exclude_prefixes": []},
    )
    docs_paths = select_document_paths(source_tree, documentation_selection)
    publication_policy = contract.get("documentation_publication_policy", {})
    publication_config_path = publication_policy.get("config_path")
    if not isinstance(publication_config_path, str) or publication_config_path not in source_tree:
        raise ValueError("The frozen public documentation configuration is missing.")
    publication_config_payload = git_run(
        ["cat-file", "blob", source_tree[publication_config_path][1]], cwd=root, check=True,
    ).stdout
    if sha256(publication_config_payload) != publication_policy.get("config_sha256"):
        raise ValueError("The frozen MkDocs configuration hash does not match the contract.")
    validate_documentation_publication_policy(
        documentation_selection, publication_policy, publication_config_payload,
    )
    excluded_docs_count = len(all_docs_paths) - len(docs_paths)
    bound_paths = sorted(set([
        *package_paths,
        *docs_paths,
        *[path for path in all_docs_paths if path.startswith(tuple(documentation_selection["exclude_prefixes"]))],
        *contract["tool_bindings"],
        "scripts/audit_wp14_public_scope.py",
        publication_config_path,
    ]))
    execution_tree = git_tree(root, head)
    changed_after_source = changed_bound_paths(source_tree, execution_tree, bound_paths)
    if changed_after_source:
        raise ValueError(f"Frozen public-surface inputs changed after source: {changed_after_source}")
    package_payloads, package_mapping = _mapping(root, source_tree, package_paths)
    docs_payloads, docs_mapping = _mapping(root, source_tree, docs_paths)
    package_scan = scan_selected_payloads(package_payloads)
    docs_scan = scan_selected_payloads(docs_payloads)
    package_gaps = package_input_gaps(package_payloads, source_paths=list(source_tree))

    public_tool_sha = contract.get("scope_scan_tool_sha256")
    scanner_blob = git_run(["show", f"{source}:scripts/audit_wp14_public_scope.py"], cwd=root, check=True).stdout
    if sha256(scanner_blob) != public_tool_sha:
        raise ValueError("The public-scope scan tool differs from its frozen source binding.")
    for path, expected_sha in contract["tool_bindings"].items():
        payload = git_run(["show", f"{source}:{path}"], cwd=root, check=True).stdout
        if sha256(payload) != expected_sha:
            raise ValueError(f"Frozen package tool binding mismatch: {path}")

    passed = package_scan["status"] == "PASS" and docs_scan["status"] == "PASS" and not package_gaps
    report = {
        "schema_version": 1,
        "record_id": "QF-029-WP14-G03-BOUNDED-PUBLIC-SURFACE-SCAN",
        "status": "PASS_BOUNDED_PUBLIC_SURFACES" if passed else "FAIL_CLOSED_BOUNDED_PUBLIC_SURFACES",
        "provenance": {
            "branch": git_run(["branch", "--show-current"], cwd=root, check=True, text=True).stdout.strip(),
            "source_sha": source,
            "contract_commit": contract_commit,
            "execution_sha": head,
            "contract_path": relative_contract,
            "contract_sha256": sha256(committed_contract),
            "scope_scan_tool_sha256": public_tool_sha,
            "started_utc": started_utc,
        },
        "surfaces": {
            "selected_package_sources": {
                "file_count": len(package_mapping),
                "mapping": package_mapping,
                "strict_scan": _redact_findings(package_scan),
                "missing_package_inputs": package_gaps,
            },
            "tracked_documentation_text_and_pdf": {
                "file_count": len(docs_mapping),
                "excluded_from_publication_file_count": excluded_docs_count,
                "excluded_from_publication_prefixes": documentation_selection["exclude_prefixes"],
                "publication_policy": publication_policy,
                "scope": contract["documentation_selection"],
                "mapping": docs_mapping,
                "strict_scan": _redact_findings(docs_scan),
            },
        },
        "controls": {
            "whole_repository_scanned": False,
            "historical_whole_repository_g03_status_changed": False,
            "thresholds_changed": False,
            "package_built_by_this_scan": False,
            "publication_performed": False,
            "ledger_changed": False,
            "points_awarded": False,
            "wp14_closed": False,
        },
        "limitations": [
            "This report covers only the prospectively frozen selected package sources and tracked documentation files with the enumerated suffixes under docs/.",
            "It does not scan scripts/, tests/, the rest of qualification/, or the complete repository/history.",
            "A passing source scan is not a wheel/sdist build result, release approval, or WP14 closure.",
        ],
        "ended_utc": utc_now(),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = audit_frozen_public_scope(args.root, args.contract, args.output)
    except (OSError, ValueError, KeyError) as exc:
        print(f"FAIL_CLOSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": report["status"], "package_files": report["surfaces"]["selected_package_sources"]["file_count"],
                      "package_findings": report["surfaces"]["selected_package_sources"]["strict_scan"]["finding_count"],
                      "documentation_files": report["surfaces"]["tracked_documentation_text_and_pdf"]["file_count"],
                      "documentation_findings": report["surfaces"]["tracked_documentation_text_and_pdf"]["strict_scan"]["finding_count"],
                      "report": str(args.output)}, ensure_ascii=False))
    return 0 if report["status"] == "PASS_BOUNDED_PUBLIC_SURFACES" else 1


if __name__ == "__main__":
    raise SystemExit(main())
