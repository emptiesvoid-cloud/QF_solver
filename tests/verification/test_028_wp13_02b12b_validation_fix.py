"""Targeted WP13-02B12b validation-fix guards."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from scripts.git_tools import git_blob

ROOT = Path(__file__).parents[2]
EVIDENCE = ROOT / "qualification/0_2_8/wp13_02b12b_contract_compliance/manifest.json"
SCHEMA = ROOT / "qualification/0_2_8/wp13_02b12b_evidence.schema.json"
B12 = ROOT / "qualification/0_2_8/wp13_02b12_contract_compliance/manifest.json"
B12_SHA = "5f32831e3b29f216b103d7f52792cbbe1b71cd35153bf64235390392da87bb2c"
B12_RELATIVE = "qualification/0_2_8/wp13_02b12_contract_compliance/manifest.json"
B12_FREEZE_COMMIT = "a6fcc1da7aaba6ae39a993728c1a25fb84aa9f16"
B12_CANONICAL_SHA = "e9d173fe7a2d8db99d66fda0d7ccf1c9701deed037c66fb61a3972e9d412785f"


def test_b12b_manifest_is_valid_and_distinct() -> None:
    manifest = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(manifest)
    assert manifest["record_id"] == "QF-028-WP13-02B12B-VALIDATION-FIX"
    assert manifest["contract_unchanged"] is True
    assert manifest["gates_unchanged"] is True
    assert manifest["historical_integrity"]["b12_unchanged"] is True


def test_b12b_three_blockers_and_valid_controls_pass() -> None:
    manifest = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    blockers = manifest["targeted_cases"]
    assert set(blockers) == {
        "unsupported_damping_unknown_model",
        "invalid_initial_conditions_nonzero_fixed_state",
        "invalid_mixed_interface_family_missing",
    }
    assert all(item["executed"] and item["pass"] and item["status"] == "REJECTED" for item in blockers.values())
    assert all(item["pass"] and item["status"] == "VALID" for item in manifest["valid_controls"].values())
    assert manifest["failure_contract"]["variants_required"] == 27
    assert manifest["failure_contract"]["variants_executed"] == 27
    assert manifest["failure_contract"]["variants_pass"] == 27
    assert manifest["decision"]["status"] == "PASS_27_OF_27"


def test_b12_historical_manifest_is_unchanged() -> None:
    # B12_SHA is the historical Windows-worktree digest retained in the B12b
    # evidence.  Validate the immutable Git content for cross-platform CI;
    # otherwise a clean LF checkout is incorrectly reported as changed from
    # the original CRLF worktree.
    frozen_blob, frozen_content = git_blob(B12_FREEZE_COMMIT, B12_RELATIVE, cwd=ROOT)
    current_blob, current_content = git_blob("HEAD", B12_RELATIVE, cwd=ROOT)
    assert current_blob == frozen_blob
    assert hashlib.sha256(frozen_content).hexdigest() == B12_CANONICAL_SHA
    assert current_content == frozen_content
    assert B12.read_bytes().replace(b"\r\n", b"\n") == frozen_content
    b12b = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert b12b["historical_integrity"]["b12_manifest_sha256_before"] == B12_SHA
    assert b12b["historical_integrity"]["b12_manifest_sha256_after"] == B12_SHA
