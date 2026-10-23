#!/usr/bin/env python3
"""Reconcile C03 inventory metadata from frozen proof outputs; never rerun J2."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from archive_inputs import (
    ADAPTER_REPO_DEFAULT,
    HEX8_DEFAULT,
    PROBE_DEFAULT,
    SNAPSHOT_COMMIT,
    SNAPSHOT_DEFAULT,
    SNAPSHOT_TREE,
    safe_inventory,
    sha256,
    source_identity,
)
from integrate_proofs import EXPECTED_ACTION_POINTS, action_proof_status, build_final_inventory, write


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _checked_path(root: Path, name: str) -> Path:
    path = (root / name).resolve(strict=True)
    if path.parent != root.resolve():
        raise ValueError(f"proof artifact path is not a direct child: {name}")
    return path


def _path_key(value: Any) -> str:
    return os.path.normcase(os.path.normpath(str(value)))


def validate_inventory_provenance_links(
    expected_inventory: dict[str, Any],
    observed_archive_rows: list[dict[str, Any]],
    observed_source_files: dict[str, str],
    observed_adapter_rows: list[dict[str, Any]],
) -> None:
    """Bind current rechecks to the extraction-stage identities being preserved."""
    expected_archives = expected_inventory.get("archives")
    if not isinstance(expected_archives, list) or len(expected_archives) != 2:
        raise ValueError("baseline inventory does not contain exactly two archive identities")
    expected_archive_by_path = {_path_key(row.get("path")): row for row in expected_archives}
    observed_archive_by_path = {_path_key(row.get("path")): row for row in observed_archive_rows}
    if len(expected_archive_by_path) != 2 or expected_archive_by_path.keys() != observed_archive_by_path.keys():
        raise ValueError("current archive paths differ from the preserved inventory identities")
    for path_key, expected in expected_archive_by_path.items():
        observed = observed_archive_by_path[path_key]
        for field in ("manifest", "verified_files", "campaign_status"):
            if observed.get(field) != expected.get(field):
                raise ValueError(f"current archive {field} differs from preserved identity: {expected.get('path')}")
        if str(observed.get("manifest_sha256", "")).lower() != str(expected.get("manifest_sha256", "")).lower():
            raise ValueError(f"current archive manifest digest differs from preserved identity: {expected.get('path')}")

    expected_sources = expected_inventory.get("historical_source_files")
    if not isinstance(expected_sources, dict) or expected_sources != observed_source_files:
        raise ValueError("historical source file hashes differ from the preserved inventory identities")

    expected_adapters = expected_inventory.get("capture_source_commits")
    if not isinstance(expected_adapters, list) or len(expected_adapters) != 2:
        raise ValueError("baseline inventory does not contain exactly two adapter identities")
    expected_adapter_by_path = {_path_key(row.get("archive")): row for row in expected_adapters}
    observed_adapter_by_path = {_path_key(row.get("archive")): row for row in observed_adapter_rows}
    if len(expected_adapter_by_path) != 2 or expected_adapter_by_path.keys() != observed_adapter_by_path.keys():
        raise ValueError("current adapter archive paths differ from the preserved identities")
    for path_key, expected in expected_adapter_by_path.items():
        observed = observed_adapter_by_path[path_key]
        if observed.get("commit") != expected.get("commit") or observed.get("tree") != expected.get("tree"):
            raise ValueError(f"adapter commit/tree differs from preserved identity: {expected.get('archive')}")
        expected_hashes = {key: str(value).lower() for key, value in expected.get("file_sha256", {}).items()}
        observed_hashes = {key: str(value).lower() for key, value in observed.get("file_sha256", {}).items()}
        if observed_hashes != expected_hashes:
            raise ValueError(f"adapter file hashes differ from preserved identity: {expected.get('archive')}")


def verify_frozen_provenance(expected_inventory: dict[str, Any]) -> dict[str, Any]:
    """Rehash archives, 29 pins, adapter captures, and the historical checkout."""
    probe_files = safe_inventory(PROBE_DEFAULT, "archive_integrity.json")
    hex_files = safe_inventory(HEX8_DEFAULT, "artifact_inventory.json", "artifacts")
    source = source_identity(SNAPSHOT_DEFAULT)
    if source["commit"] != SNAPSHOT_COMMIT or source["tree"] != SNAPSHOT_TREE or source["clean"] is not True:
        raise ValueError("historical snapshot identity or cleanliness changed")

    results = [
        (PROBE_DEFAULT, read_json(PROBE_DEFAULT / "campaign_result.json")),
        (HEX8_DEFAULT, read_json(HEX8_DEFAULT / "campaign_result.json")),
    ]
    observed_archive_rows = [
        {
            "path": str(PROBE_DEFAULT),
            "manifest": "archive_integrity.json",
            "manifest_sha256": sha256(PROBE_DEFAULT / "archive_integrity.json"),
            "verified_files": len(probe_files),
            "campaign_status": results[0][1].get("status"),
        },
        {
            "path": str(HEX8_DEFAULT),
            "manifest": "artifact_inventory.json",
            "manifest_sha256": sha256(HEX8_DEFAULT / "artifact_inventory.json"),
            "verified_files": len(hex_files),
            "campaign_status": results[1][1].get("status"),
        },
    ]
    common_pin_map: dict[str, str] | None = None
    adapter_checks = []
    observed_adapter_rows = []
    for archive, result in results:
        historical = result["historical_snapshot"]
        if historical.get("commit") != SNAPSHOT_COMMIT or historical.get("tree") != SNAPSHOT_TREE:
            raise ValueError(f"campaign snapshot identity differs: {archive}")
        pins = historical.get("production_pin_sha256", {})
        if historical.get("production_pin_count") != 29 or len(pins) != 29:
            raise ValueError(f"historical production pin count differs: {archive}")
        for rel, expected in pins.items():
            if sha256(SNAPSHOT_DEFAULT / rel).lower() != expected.lower():
                raise ValueError(f"historical production pin hash differs: {rel}")
        if common_pin_map is None:
            common_pin_map = pins
        elif pins != common_pin_map:
            raise ValueError("TET4 and HEX8 archives bind different production pin sets")
        for rel, expected in historical.get("historical_file_sha256", {}).items():
            if sha256(SNAPSHOT_DEFAULT / rel).lower() != expected.lower():
                raise ValueError(f"historical source file hash differs: {rel}")

        adapter = result["adapter"]
        commit, tree = adapter["commit"], adapter["tree"]
        observed_tree = subprocess.check_output(
            ["git", "rev-parse", f"{commit}^{{tree}}"], cwd=ADAPTER_REPO_DEFAULT, text=True
        ).strip()
        if observed_tree != tree:
            raise ValueError(f"adapter tree identity differs: {commit}")
        adapter_hashes = {}
        for rel, expected in result.get("adapter_file_sha256", {}).items():
            content = subprocess.check_output(["git", "show", f"{commit}:{rel}"], cwd=ADAPTER_REPO_DEFAULT)
            if hashlib.sha256(content).hexdigest().lower() != expected.lower():
                raise ValueError(f"adapter capture hash differs: {commit}:{rel}")
            adapter_hashes[rel] = hashlib.sha256(content).hexdigest().lower()
        observed_adapter_rows.append({"archive": str(archive), "commit": commit, "tree": tree, "file_sha256": adapter_hashes})
        adapter_checks.append({"commit": commit, "tree": tree, "files_verified": len(adapter_hashes)})

    if common_pin_map is None or len(common_pin_map) != 29:
        raise ValueError("the common 29-pin set was not verified")
    validate_inventory_provenance_links(
        expected_inventory,
        observed_archive_rows,
        source["source_files"],
        observed_adapter_rows,
    )
    return {
        "snapshot_commit": source["commit"],
        "snapshot_tree": source["tree"],
        "historical_checkout_clean": True,
        "production_pins_verified_per_archive": 29,
        "production_pin_set_identical_across_archives": True,
        "probe_archive_files_verified": len(probe_files),
        "hex8_archive_files_verified": len(hex_files),
        "adapter_captures": adapter_checks,
    }


def _manifest_hashes(proof_dir: Path) -> dict[str, str]:
    baseline = read_json(proof_dir / "artifact_manifest.pre_metadata_fix.json")
    return {entry["path"]: entry["sha256"] for entry in baseline["files_excluding_this_manifest"]}


def _verify_baseline_file(proof_dir: Path, baseline_hashes: dict[str, str], baseline_name: str, current_path: Path) -> None:
    expected = baseline_hashes.get(baseline_name)
    if expected is None:
        raise ValueError(f"baseline manifest has no identity for {baseline_name}")
    if sha256(current_path).lower() != expected.lower():
        raise ValueError(f"baseline identity mismatch for {baseline_name}")


def load_verified_proofs(proof_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    baseline_hashes = _manifest_hashes(proof_dir)
    baseline_inventory_path = proof_dir / "archive_inventory.pre_metadata_fix.json"
    _verify_baseline_file(proof_dir, baseline_hashes, "archive_inventory.json", baseline_inventory_path)
    summary_path = proof_dir / "proof_action_summary.json"
    _verify_baseline_file(proof_dir, baseline_hashes, "proof_action_summary.json", summary_path)
    extraction_inventory = read_json(baseline_inventory_path)
    if extraction_inventory.get("snapshot_commit") != SNAPSHOT_COMMIT or extraction_inventory.get("snapshot_tree") != SNAPSHOT_TREE:
        raise ValueError("baseline inventory scientific snapshot differs from the frozen contract")
    action_rows = extraction_inventory.get("actions", [])
    if {item.get("action_id") for item in action_rows} != set(EXPECTED_ACTION_POINTS) or len(action_rows) != 8:
        raise ValueError("baseline extraction inventory action identities differ from the frozen contract")
    action_rows_by_id = {item["action_id"]: item for item in action_rows}
    proof_summary = read_json(summary_path)
    if proof_summary.get("technical_aggregate_verdict") != "PASS":
        raise ValueError("frozen proof summary is not the previously recorded PASS")
    if proof_summary.get("action_count") != 8 or proof_summary.get("point_count") != 304:
        raise ValueError("frozen proof summary does not identify eight actions and 304 points")
    entries = proof_summary.get("summary")
    if not isinstance(entries, list) or len(entries) != 8:
        raise ValueError("frozen proof summary does not contain exactly eight action records")
    if {item.get("action_id") for item in entries} != set(EXPECTED_ACTION_POINTS):
        raise ValueError("frozen proof summary action identities differ from the C03 contract")

    action_results = []
    verified_summaries = []
    for entry in entries:
        action_id = entry["action_id"]
        input_name = action_rows_by_id[action_id].get("proof_input_path")
        result_name = entry.get("proof_result_path")
        input_path = _checked_path(proof_dir, input_name)
        result_path = _checked_path(proof_dir, result_name)
        _verify_baseline_file(proof_dir, baseline_hashes, input_name, input_path)
        _verify_baseline_file(proof_dir, baseline_hashes, result_name, result_path)
        if sha256(input_path).lower() != entry.get("proof_input_sha256", "").lower():
            raise ValueError(f"proof input digest differs for {entry['action_id']}")
        if sha256(result_path).lower() != entry.get("proof_result_sha256", "").lower():
            raise ValueError(f"proof result digest differs for {entry['action_id']}")
        proof_input = read_json(input_path)
        proof_result = read_json(result_path)
        expected_count = EXPECTED_ACTION_POINTS[action_id]
        if action_rows_by_id[action_id].get("sha256") != entry.get("proof_input_sha256"):
            raise ValueError(f"extraction inventory input digest differs for {action_id}")
        if action_rows_by_id[action_id].get("point_count") != expected_count:
            raise ValueError(f"extraction inventory point count differs for {action_id}")
        if proof_input.get("action_id") != action_id or proof_result.get("action_id") != action_id:
            raise ValueError(f"proof input/result action identity differs for {action_id}")
        if proof_result.get("proof_input_sha256") != entry.get("proof_input_sha256"):
            raise ValueError(f"proof result does not bind its input for {action_id}")
        points = proof_input.get("points")
        if proof_input.get("number_of_points") != expected_count or not isinstance(points, list) or len(points) != expected_count:
            raise ValueError(f"proof input point count differs for {action_id}")
        for point in points:
            segment = point.get("segment_s_m", {})
            lower = segment.get("lo", {})
            upper = segment.get("hi", {})
            if lower != {"numerator": "-1", "denominator": "10000"} or upper != {"numerator": "1", "denominator": "10000"}:
                raise ValueError(f"frozen segment differs for {action_id}:{point.get('point_id')}")
        if proof_result.get("point_count") != expected_count or len(proof_result.get("points", [])) != expected_count:
            raise ValueError(f"proof result point count differs for {action_id}")
        if proof_input.get("provenance_valid") is not True or proof_input.get("source_identity_valid") is not True:
            raise ValueError(f"proof input provenance gates are incomplete for {action_id}")
        result_points = proof_result["points"]
        by_point_id = {item.get("point_id"): item for item in result_points}
        if len(by_point_id) != expected_count:
            raise ValueError(f"proof result has missing or duplicate point IDs for {action_id}")
        for input_point in points:
            proof_point = by_point_id.get(input_point.get("point_id"))
            if proof_point is None:
                raise ValueError(f"proof result point is not bound to its input for {action_id}")
            if proof_point.get("expected_branch_from_archive") != input_point.get("expected_branch"):
                raise ValueError(f"proof branch expectation differs from its input for {action_id}:{input_point.get('point_id')}")
            if proof_point.get("production_branch_archived") != input_point.get("production_base_branch_archived"):
                raise ValueError(f"archived production branch differs from its input for {action_id}:{input_point.get('point_id')}")
        if proof_result.get("action_verdict") != entry.get("action_verdict"):
            raise ValueError(f"proof result verdict differs from action summary for {action_id}")
        for key in ("action_verdict", "point_count", "mathematical_point_pass_count", "production_point_pass_count"):
            if proof_result.get(key) != entry.get(key):
                raise ValueError(f"proof result field differs from summary for {action_id}: {key}")
        if proof_result.get("production_branch_linkage_valid") is not entry.get("production_gates_complete"):
            raise ValueError(f"production linkage summary differs for {action_id}")
        if action_proof_status(proof_result) != "PASS":
            raise ValueError(f"serialized branch proof gates do not pass for {action_id}")
        if proof_result.get("production_point_pass_count") != expected_count or proof_result.get("mathematical_point_pass_count") != expected_count:
            raise ValueError(f"per-point proof pass counts differ for {action_id}")
        action_results.append(proof_result)
        verified_summaries.append(entry)

    return extraction_inventory, action_results, verified_summaries, {
        "baseline_manifest_sha256": sha256(proof_dir / "artifact_manifest.pre_metadata_fix.json"),
        "baseline_inventory_sha256": sha256(baseline_inventory_path),
        "baseline_summary_sha256": sha256(summary_path),
        "proof_input_result_hashes_verified": True,
        "verified_action_count": len(action_results),
        "verified_point_count": sum(len(item["points"]) for item in action_results),
    }


def finalize(proof_dir: Path) -> dict[str, Any]:
    extraction, action_results, summaries, proof_check = load_verified_proofs(proof_dir)
    provenance = verify_frozen_provenance(extraction)
    final_inventory = build_final_inventory(extraction, action_results, summaries)
    final_inventory["metadata_finalization"] = {
        "mode": "METADATA_ONLY_FROM_FROZEN_PROOF_OUTPUTS",
        "scientific_recalculation": False,
        "provenance_recheck": provenance,
        "proof_output_recheck": proof_check,
    }
    write(proof_dir / "archive_inventory.json", final_inventory)
    return {
        "technical_aggregate_verdict": final_inventory["technical_aggregate_verdict"],
        "strict_action_proofs_ready": final_inventory["strict_action_proofs_ready"],
        "action_count": final_inventory["action_count"],
        "point_count": final_inventory["candidate_point_count"],
        "reason": final_inventory["reason"],
        "archive_inventory_sha256": sha256(proof_dir / "archive_inventory.json"),
        "proof_input_result_hashes_verified": proof_check["proof_input_result_hashes_verified"],
        "production_pins_verified_per_archive": provenance["production_pins_verified_per_archive"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proof-dir", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    report = finalize(args.proof_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
