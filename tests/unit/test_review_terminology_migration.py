import hashlib
import json
from pathlib import Path

import pytest

from scripts import verify_review_terminology_migration as migration
from scripts.review_vocabulary import FORBIDDEN_TERMS


@pytest.fixture
def migration_fixture(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    term = FORBIDDEN_TERMS[0]
    originals = {
        migration.MIGRATED_PATHS[0]: ("3. " + term + "-readable report;\n").encode(),
        migration.MIGRATED_PATHS[1]: json.dumps({
            "authority_order": ["RAW_NUMERIC_EVIDENCE", term.upper() + "_READABLE_REPORT"],
            "threshold": 1e-8,
        }).encode(),
    }
    def fake_blob(revision: str, path: str, *, cwd: Path) -> tuple[str, bytes]:
        assert revision == migration.ORIGINAL_SOURCE_SHA
        return "f" * 40, originals[path]
    monkeypatch.setattr(migration, "git_blob", fake_blob)
    entries = []
    for relative, original in originals.items():
        current = migration.expected_migration(relative, original)
        path = tmp_path / relative
        path.parent.mkdir(parents=True)
        path.write_bytes(current)
        entries.append({
            "path": relative, "original_git_blob": "f" * 40,
            "original_sha256": hashlib.sha256(original).hexdigest(),
            "migrated_sha256": hashlib.sha256(current).hexdigest(),
        })
    manifest = tmp_path / "migration.json"
    manifest.write_text(json.dumps({
        "classification": "OWNER_AUTHORIZED_TERMINOLOGY_ONLY_MIGRATION",
        "original_source_sha": migration.ORIGINAL_SOURCE_SHA,
        "files": entries,
    }), encoding="utf-8")
    return tmp_path, manifest


def test_exact_migration_passes_without_numeric_requalification(migration_fixture) -> None:
    root, manifest = migration_fixture
    report = migration.verify_review_terminology_migration(root, manifest)
    assert report["status"] == "PASS"
    assert len(report["verified_files"]) == 2
    assert report["new_numerical_qualification"] is False
    assert report["historical_execution_digests_rebound"] is False


@pytest.mark.parametrize("field", ["original_git_blob", "original_sha256", "migrated_sha256"])
def test_false_hashes_fail_closed(migration_fixture, field: str) -> None:
    root, path = migration_fixture
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["files"][0][field] = "0" * 64
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert migration.verify_review_terminology_migration(root, path)["status"] == "FAIL_CLOSED"


def test_numeric_change_cannot_pass_even_with_a_rehashed_manifest(migration_fixture) -> None:
    root, path = migration_fixture
    manifest = json.loads(path.read_text(encoding="utf-8"))
    relative = migration.MIGRATED_PATHS[1]
    current = (root / relative).read_bytes().replace(b"1e-08", b"1e-06")
    (root / relative).write_bytes(current)
    manifest["files"][1]["migrated_sha256"] = hashlib.sha256(current).hexdigest()
    path.write_text(json.dumps(manifest), encoding="utf-8")
    report = migration.verify_review_terminology_migration(root, path)
    assert report["status"] == "FAIL_CLOSED"
    assert any("CHANGE_OUTSIDE_TERMINOLOGY" in error for error in report["errors"])


@pytest.mark.parametrize("change", ["missing_entry", "wrong_source", "unauthorized"])
def test_incomplete_or_wrong_scope_fails_closed(migration_fixture, change: str) -> None:
    root, path = migration_fixture
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if change == "missing_entry":
        manifest["files"].pop()
    elif change == "wrong_source":
        manifest["original_source_sha"] = "0" * 40
    else:
        manifest["classification"] = "UNAUTHORIZED"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert migration.verify_review_terminology_migration(root, path)["status"] == "FAIL_CLOSED"


def test_missing_current_file_fails_closed(migration_fixture) -> None:
    root, path = migration_fixture
    (root / migration.MIGRATED_PATHS[0]).unlink()
    assert migration.verify_review_terminology_migration(root, path)["status"] == "FAIL_CLOSED"


def test_actual_two_file_migration_is_exact() -> None:
    assert migration.verify_review_terminology_migration()["status"] == "PASS"
