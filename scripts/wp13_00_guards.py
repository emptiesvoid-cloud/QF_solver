"""Fail-closed WP13-00 baseline and separation guards."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

try:
    from scripts.wp13_common import CONTRACT_FIELDS
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from wp13_common import CONTRACT_FIELDS


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "qualification/0_2_8/wp13_00_baseline.json"
CONTRACT_SCHEMA = ROOT / "qualification/0_2_8/wp13_vnv_contract.json"
EVIDENCE_SCHEMA = ROOT / "qualification/0_2_8/wp13_evidence_pack_schema.json"
CONSOLIDATED = ROOT / "qualification/0_2_8/consolidated_registry.json"
# PP03 froze the public 0.2.7 documentation view after replacing site-relative
# evidence links with immutable Git blobs.  The machine-readable 0.2.7 evidence
# remains protected by the start-SHA tree below; this separate projection avoids
# treating later public-documentation work as a rewrite of that evidence.
DOCS_027_HISTORICAL_VIEW_FREEZE_SHA = "4db743129738fa2b7fa752e143fd92cc61b54e6a"
DOCS_027_HISTORICAL_VIEW_TREE = "ab1a16f2a141834570bdb67336a6471251d94f12"


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def validate_baseline() -> list[str]:
    errors: list[str] = []
    baseline = _read(BASELINE)
    consolidated = _read(CONSOLIDATED)
    counts = consolidated["combination_registry"]["state_counts"]
    if baseline["start_sha_wp13"] != _git("rev-parse", "30bff8d585b3988befaff9cc21e881098ff1b2df"):
        errors.append("baseline start SHA is not present in Git")
    if baseline["maturity"]["element_analysis_registry"]["total"] != 46:
        errors.append("baseline does not declare 46 element-analysis combinations")
    if baseline["maturity"]["element_analysis_registry"]["state_counts"] != counts:
        errors.append("baseline maturity counts differ from consolidated registry")
    if counts != {"QUALIFIED_BOUNDED": 32, "EXPERIMENTAL": 14, "NOT_QUALIFIED": 0}:
        errors.append("consolidated registry state counts are not 32/14/0")
    if len(baseline["mixed_workflow_registry"]["records"]) != 3:
        errors.append("mixed workflow records are missing or collapsed into the 46 registry")
    if not baseline["deferred_p2"]:
        errors.append("P2 deferred list is empty")
    for path in (CONTRACT_SCHEMA, EVIDENCE_SCHEMA):
        if not path.is_file():
            errors.append(f"missing WP13 schema: {path}")
    schema = _read(CONTRACT_SCHEMA)
    if tuple(schema["required_fields"]) != CONTRACT_FIELDS:
        errors.append("contract schema required fields drifted")
    current_qualification_tree = _git("rev-parse", "HEAD:qualification/0_2_7")
    if current_qualification_tree != baseline["immutability"]["qualification_0_2_7"]["git_tree_at_start_sha"]:
        errors.append("qualification/0_2_7 tree changed")
    frozen_docs_tree = _git(
        "rev-parse", f"{DOCS_027_HISTORICAL_VIEW_FREEZE_SHA}:docs/verification/0_2_7"
    )
    if frozen_docs_tree != DOCS_027_HISTORICAL_VIEW_TREE:
        errors.append("0.2.7 historical documentation freeze cannot be resolved")
    docs_view_matches_freeze = (
        subprocess.run(
            [
                "git",
                "diff",
                "--quiet",
                DOCS_027_HISTORICAL_VIEW_FREEZE_SHA,
                "--",
                "docs/verification/0_2_7",
            ],
            cwd=ROOT,
            check=False,
        ).returncode
        == 0
    )
    if not docs_view_matches_freeze:
        errors.append("docs/verification/0_2_7 tree differs from its frozen public view")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate the WP13-00 baseline")
    args = parser.parse_args()
    if not args.check:
        parser.error("--check is required")
    errors = validate_baseline()
    if errors:
        for error in errors:
            print(f"WP13-00 guard: FAIL: {error}")
        return 1
    print("WP13-00 guards: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
