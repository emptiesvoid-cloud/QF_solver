"""Verify the authorized terminology-only migration, not a new qualification."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Sequence

if __package__:
    from scripts.git_tools import git_blob
    from scripts.review_vocabulary import FORBIDDEN_TERMS, review_vocabulary_audit
else:
    from git_tools import git_blob  # type: ignore[no-redef]
    from review_vocabulary import FORBIDDEN_TERMS, review_vocabulary_audit  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_SOURCE_SHA = "0c7ecfaee74c1f0bb362afb1f0ac8bc45686c0ba"
DEFAULT_MANIFEST = Path("qualification/0_2_9/wp14/wp14_analyzer_terminology_migration_20260927.json")
MIGRATED_PATHS = (
    "docs/verification/0_2_9/wp06f-closure-contract.md",
    "qualification/0_2_9/wp06f_closure_contract.json",
)


def expected_migration(path: str, original: bytes) -> bytes:
    """Permit exactly one label replacement, without reformatting any bytes."""
    old_term = FORBIDDEN_TERMS[0].encode("ascii")
    if path == MIGRATED_PATHS[0]:
        before, after = old_term + b"-readable report;", b"analyzer report;"
    elif path == MIGRATED_PATHS[1]:
        before, after = old_term.upper() + b"_READABLE_REPORT", b"ANALYZER_REPORT"
    else:
        raise ValueError("The path is outside the authorized migration.")
    if original.count(before) != 1:
        raise ValueError("The original label is not present exactly once.")
    return original.replace(before, after)


def verify_review_terminology_migration(
    root: Path = ROOT, manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Verify old Git identity, both hashes and the entire byte-level delta."""
    errors: list[str] = []
    verified: list[dict[str, str]] = []
    try:
        manifest = json.loads((manifest_path or root / DEFAULT_MANIFEST).read_text(encoding="utf-8"))
        if manifest["classification"] != "OWNER_AUTHORIZED_TERMINOLOGY_ONLY_MIGRATION":
            raise ValueError("Migration authorization classification differs.")
        if manifest["original_source_sha"] != ORIGINAL_SOURCE_SHA:
            raise ValueError("Original source SHA differs.")
        entries = manifest["files"]
        if len(entries) != len(MIGRATED_PATHS) or {row["path"] for row in entries} != set(MIGRATED_PATHS):
            raise ValueError("The exact two-file migration scope is required.")
        for row in entries:
            path = row["path"]
            blob, original = git_blob(ORIGINAL_SOURCE_SHA, path, cwd=root)
            original_digest = hashlib.sha256(original).hexdigest()
            current = (root / path).read_bytes()
            current_digest = hashlib.sha256(current).hexdigest()
            if blob != row["original_git_blob"] or original_digest != row["original_sha256"]:
                errors.append(f"{path}: ORIGINAL_IDENTITY_MISMATCH")
            if current_digest != row["migrated_sha256"]:
                errors.append(f"{path}: MIGRATED_HASH_MISMATCH")
            if current != expected_migration(path, original):
                errors.append(f"{path}: CHANGE_OUTSIDE_TERMINOLOGY_AUTHORIZATION")
            verified.append({"path": path, "original_sha256": original_digest, "migrated_sha256": current_digest})
        vocabulary = review_vocabulary_audit(root, list(MIGRATED_PATHS))
        if vocabulary["status"] != "PASS":
            errors.append("MIGRATED_VOCABULARY_INVALID")
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        errors.append(f"MIGRATION_EVIDENCE_INVALID: {type(exc).__name__}: {exc}")
    return {
        "status": "FAIL_CLOSED" if errors else "PASS",
        "classification": "TERMINOLOGY_ONLY_BYTE_DELTA_VERIFIED",
        "verified_files": verified,
        "errors": errors,
        "new_numerical_qualification": False,
        "historical_execution_digests_rebound": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args(argv)
    report = verify_review_terminology_migration(args.root, args.manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
