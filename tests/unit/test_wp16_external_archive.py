"""Boundary tests for operator-controlled, off-Git evidence archives."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from scripts.wp16_external_archive import (
    ArchiveError,
    _relative_path,
    assemble,
    pack,
    restore,
    split,
    verify,
    verify_parts,
)


def _bundle(tmp_path: Path) -> tuple[Path, Path, Path, dict]:
    source = tmp_path / "source"
    (source / "ACTIVE_SET" / "M1").mkdir(parents=True)
    (source / "ACTIVE_SET" / "M1" / "result.json").write_text('{"value": 42}\n', encoding="utf-8")
    (source / "ACTIVE_SET" / "M1" / "stdout.log").write_text("ok\n", encoding="utf-8")
    archive = tmp_path / "raw.zip"
    manifest_path = tmp_path / "manifest.json"
    manifest = pack(source, "qualification/0_2_9/wp07d/runs", archive, manifest_path, expected_count=2)
    return source, archive, manifest_path, manifest


def test_pack_verify_restore_and_parts(tmp_path: Path) -> None:
    source, archive, manifest_path, manifest = _bundle(tmp_path)
    assert manifest["status"] == "LOCAL_ARCHIVE_VERIFIED_PENDING_REMOTE"
    assert manifest["uncompressed_bytes"] == 19
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == manifest
    verify(archive, manifest)
    with pytest.raises(ArchiveError, match="overwrite"):
        pack(source, "qualification/0_2_9/wp07d/runs", archive, manifest_path)
    parts = tmp_path / "parts"
    receipt = split(archive, manifest, parts, 4 * 1024 * 1024)
    assert len(receipt["parts"]) == 1
    verify_parts(parts, receipt)
    reassembled = tmp_path / "reassembled.zip"
    assemble(parts, receipt, manifest, reassembled)
    assert reassembled.read_bytes() == archive.read_bytes()
    destination = tmp_path / "restored"
    restore(archive, manifest, destination)
    assert (destination / "ACTIVE_SET" / "M1" / "result.json").read_bytes() == (
        source / "ACTIVE_SET" / "M1" / "result.json"
    ).read_bytes()
    with pytest.raises(ArchiveError, match="existing"):
        restore(archive, manifest, destination)
    with pytest.raises(ArchiveError, match="overwrite"):
        assemble(parts, receipt, manifest, reassembled)


def test_rejects_changed_archive_and_part(tmp_path: Path) -> None:
    _, archive, _, manifest = _bundle(tmp_path)
    parts = tmp_path / "parts"
    receipt = split(archive, manifest, parts, 4 * 1024 * 1024)
    part = parts / receipt["parts"][0]["name"]
    part.write_bytes(part.read_bytes() + b"x")
    with pytest.raises(ArchiveError, match="Part byte mismatch"):
        verify_parts(parts, receipt)
    archive.write_bytes(archive.read_bytes() + b"x")
    with pytest.raises(ArchiveError, match="SHA-256 mismatch"):
        verify(archive, manifest)


@pytest.mark.parametrize("value", ["../escape", "a/../b", "/absolute", "a//b", "a/./b", "C:/drive", "a\\b"])
def test_rejects_unsafe_paths(value: str) -> None:
    with pytest.raises(ArchiveError):
        _relative_path(value)


def test_symlink_fails_closed_when_host_permits_symlinks(tmp_path: Path) -> None:
    source, _, _, _ = _bundle(tmp_path)
    try:
        (source / "pointer").symlink_to(source / "ACTIVE_SET", target_is_directory=True)
    except OSError:
        pytest.skip("Host does not permit symlink creation")
    with pytest.raises(ArchiveError, match="Unsupported source entry"):
        pack(source, "qualification/0_2_9/wp07d/runs", tmp_path / "second.zip", tmp_path / "second.json")


def test_zip_member_mismatch_fails_closed(tmp_path: Path) -> None:
    _, archive, _, manifest = _bundle(tmp_path)
    with zipfile.ZipFile(archive, "a") as target:
        target.writestr("unexpected.txt", "not declared")
    # The outer digest fails before the undeclared member can be accepted.
    with pytest.raises(ArchiveError, match="SHA-256 mismatch"):
        verify(archive, manifest)


def test_declared_totals_and_expected_count_are_checked(tmp_path: Path) -> None:
    source, archive, _, manifest = _bundle(tmp_path)
    with pytest.raises(ArchiveError, match="Expected 3 files"):
        pack(source, "qualification/0_2_9/wp07d/runs", tmp_path / "other.zip", tmp_path / "other.json", expected_count=3)
    manifest["uncompressed_bytes"] += 1
    with pytest.raises(ArchiveError, match="totals"):
        verify(archive, manifest)


def test_selected_source_roots_are_exact_and_bound_to_manifest(tmp_path: Path) -> None:
    source = tmp_path / "source"
    for root in ("r3_1", "r3_2", "r4"):
        (source / root).mkdir(parents=True)
        (source / root / "result.json").write_text(root, encoding="utf-8")
    archive = tmp_path / "selected.zip"
    manifest_path = tmp_path / "selected.json"
    manifest = pack(
        source,
        "qualification/0_2_9",
        archive,
        manifest_path,
        selected_roots=["r3_2", "r3_1"],
        expected_count=2,
    )
    assert manifest["selected_roots"] == ["r3_1", "r3_2"]
    assert {record["path"] for record in manifest["files"]} == {"r3_1/result.json", "r3_2/result.json"}
    verify(archive, manifest)
    restored = tmp_path / "restored"
    restore(archive, manifest, restored)
    assert (restored / "r3_1" / "result.json").read_text() == "r3_1"
    assert not (restored / "r4").exists()
    manifest["files"][0]["path"] = "r4/result.json"
    with pytest.raises(ArchiveError, match="outside selected"):
        verify(archive, manifest)


@pytest.mark.parametrize("selected", [["r3_1", "r3_1"], ["r3_1", "r3_1/child"], ["../escape"]])
def test_selected_source_roots_reject_overlap_or_unsafe_paths(tmp_path: Path, selected: list[str]) -> None:
    source = tmp_path / "source"
    (source / "r3_1").mkdir(parents=True)
    (source / "r3_1" / "result.json").write_text("ok", encoding="utf-8")
    with pytest.raises(ArchiveError):
        pack(
            source,
            "qualification/0_2_9",
            tmp_path / "selected.zip",
            tmp_path / "selected.json",
            selected_roots=selected,
        )


def test_drive_catalog_is_bound_to_local_manifests_and_frozen_provenance() -> None:
    root = Path(__file__).resolve().parents[2]
    catalog = json.loads(
        (root / "qualification/0_2_9/wp16_external_archive/drive_catalog_2026_09_29.json").read_text(
            encoding="utf-8"
        )
    )
    assert catalog["status"] == "OWNER_ACCEPTED_BOUNDED_ARCHIVE_WITH_LIMITATIONS_WP16_REMAINS_OPEN"
    assert catalog["owner_decision"] == {
        "path": "qualification/0_2_9/wp16_external_archive/owner_bounded_acceptance_2026_09_29.json",
        "decision": "ACCEPT_BOUNDED_ARCHIVE_WITH_LIMITATIONS",
        "wp16_closed": False,
        "qualification_points_awarded": 0,
        "wp14_global_status": "HOLD",
    }
    owner_decision = json.loads(
        (root / catalog["owner_decision"]["path"]).read_text(encoding="utf-8")
    )
    assert owner_decision["retention_policy"]["no_automatic_deletion_or_overwrite"] is True
    assert owner_decision["wp16_status"].endswith("WP16_REMAINS_OPEN_FOR_REMAINDER_INVENTORY_AND_GOVERNANCE")
    assert catalog["drive_folder_id"] == "1Aye0b1kcfK4Vm2gc01OaiIbZL9XdgHel"
    assert len(catalog["bundles"]) == 12
    seen_ids: set[str] = set()
    for bundle in catalog["bundles"]:
        path = root / bundle["manifest_path"]
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == bundle["manifest_sha256"]
        manifest = json.loads(data)
        assert _relative_path(bundle["source_relative_root"]).as_posix() == manifest["source_relative_root"]
        assert bundle["file_count"] == manifest["file_count"]
        assert bundle["uncompressed_bytes"] == manifest["uncompressed_bytes"]
        assert bundle["archive"] == manifest["archive"]
        if "selected_roots" in bundle:
            assert bundle["selected_roots"] == len(manifest["selected_roots"])
        remote_ids = [bundle["remote_manifest_file_id"]]
        if "remote_parts" in bundle:
            assert sum(part["size_bytes"] for part in bundle["remote_parts"]) == bundle["archive"]["size_bytes"]
            assert all(part["size_bytes"] <= 96 * 1024 * 1024 for part in bundle["remote_parts"])
            remote_ids.extend(part["id"] for part in bundle["remote_parts"])
            remote_ids.append(bundle["remote_parts_receipt_file_id"])
        else:
            remote_ids.append(bundle["remote_archive_file_id"])
        assert not seen_ids.intersection(remote_ids)
        seen_ids.update(remote_ids)
        assert "VERIFIED" in bundle["readback"]

    by_id = {bundle["id"]: bundle for bundle in catalog["bundles"]}
    wp07 = json.loads(
        (root / "qualification/0_2_9/wp07d_contact_requalification_r2/wp07_r2_5_integration_record.json").read_text(
            encoding="utf-8"
        )
    )
    assert by_id["WP07D_R2_5_RAW"]["file_count"] == wp07["raw_evidence"]["file_count"]
    assert by_id["WP07D_R2_5_RAW"]["uncompressed_bytes"] == wp07["raw_evidence"]["bytes"]
    assert by_id["WP07D_R2_TO_R2_4_HISTORY_RAW"]["historical_verdict"] == (
        "MIXED_R2_TO_R2_4_HISTORY_NOT_RECLASSIFIED"
    )
    assert by_id["WP07D_R2_TO_R2_4_HISTORY_RAW"]["selected_roots"] == 5
    assert by_id["WP04D_REPRODUCED_NPZ_AND_RECORDS"]["historical_verdict"] == (
        "REPRODUCED_FILES_NOT_HISTORICAL_ORIGINALS"
    )
    wp08 = json.loads(
        (root / "qualification/0_2_9/wp08d_contact_requalification_r2_1_final.json").read_text(encoding="utf-8")
    )
    assert by_id["WP08D_R2_RAW"]["historical_verdict"] == wp08["final_status"]
    wp12 = json.loads(
        (root / "qualification/0_2_9/wp12_external_vv_r4_gallery_summary.json").read_text(encoding="utf-8")
    )
    assert by_id["WP12_R4_GALLERY_RAW"]["file_count"] == wp12["provenance"]["manifested_raw_file_count"]
    assert by_id["WP12_R4_GALLERY_RAW"]["uncompressed_bytes"] == wp12["provenance"]["manifested_raw_bytes"]
    assert by_id["WP12_R3_DIAGNOSTIC_HISTORY_RAW"]["file_count"] == 8890
    assert by_id["WP12_R3_DIAGNOSTIC_HISTORY_RAW"]["historical_verdict"] == "MIXED_DIAGNOSTIC_HISTORY_NOT_RECLASSIFIED"
    wp13 = json.loads(
        (root / "qualification/0_2_9/wp13_r2_multifamily/wp13_r2_raw_evidence_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert by_id["WP13_R2_RAW"]["uncompressed_bytes"] == wp13["raw_total_bytes"]
    wp13_owner = json.loads(
        (root / "qualification/0_2_9/wp13_r2_multifamily/wp13_owner_acceptance_r2_1.json").read_text(
            encoding="utf-8"
        )
    )
    assert by_id["WP13_R2_RAW"]["historical_verdict"] == wp13_owner["status"]
    new_entries = {
        item["path"]: item for item in json.loads((root / by_id["WP13_R2_RAW"]["manifest_path"]).read_text())["files"]
    }
    prefix = wp13["raw_root"] + "/"
    for old in wp13["files"]:
        new = new_entries[old["path"].removeprefix(prefix)]
        assert (new["size_bytes"], new["sha256"]) == (old["size_bytes"], old["sha256"])
