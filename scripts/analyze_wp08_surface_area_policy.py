"""Recompute WP08 R3 surface-area accounting without running a solve."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

DEFAULT_OUTPUT = ROOT / (
    "qualification/0_2_9/wp08_surface_stiffness_remediation/"
    "surface_area_policy_diagnostic_r1.json"
)
EXPECTED_KAPPA = 2_666_700.0
EXPECTED_AREAS = {"M1": 1.5, "M2": 1.75, "M3": 1.875}


def compare_area_policies(
    *, physical_area_m2: float, eligible_area_m2: float, kappa_n_per_m3: float
) -> dict[str, float]:
    """Compare current excluded-share and hypothetical normalized measures.

    The normalized result is arithmetic only. It is not an approved contact
    law and is never passed to the production solver by this module.
    """
    values = (physical_area_m2, eligible_area_m2, kappa_n_per_m3)
    if not all(math.isfinite(value) and value > 0.0 for value in values):
        raise ValueError("areas and kappa must be finite and positive")
    if eligible_area_m2 > physical_area_m2 * (1.0 + 1.0e-12):
        raise ValueError("eligible area cannot exceed the physical patch area")
    current = kappa_n_per_m3 * eligible_area_m2
    normalized = kappa_n_per_m3 * physical_area_m2
    return {
        "physical_area_m2": physical_area_m2,
        "eligible_area_m2": eligible_area_m2,
        "excluded_area_share_m2": physical_area_m2 - eligible_area_m2,
        "current_integrated_stiffness_N_per_m": current,
        "hypothetical_full_area_stiffness_N_per_m": normalized,
        "hypothetical_multiplier": physical_area_m2 / eligible_area_m2,
        "hypothetical_increase_percent": (normalized / current - 1.0) * 100.0,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_verified_archive(archive_root: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS_LOCAL_ARCHIVE_HASHES_VERIFIED":
        raise ValueError("R3 archive manifest is not verified")
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise ValueError("archive manifest has no file inventory")
    expected_paths = {entry["path"] for entry in entries}
    observed_paths = {
        path.relative_to(archive_root).as_posix()
        for path in archive_root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    if observed_paths != expected_paths:
        raise ValueError("archive inventory has missing or unmanifested files")
    for entry in entries:
        path = archive_root / entry["path"]
        if not path.is_file() or path.stat().st_size != entry["size_bytes"]:
            raise ValueError(f"archive file missing or size mismatch: {entry['path']}")
        if _sha256(path) != entry["sha256"]:
            raise ValueError(f"archive SHA-256 mismatch: {entry['path']}")
    return manifest


def analyze(archive_root: Path, archive_manifest: Path) -> dict[str, Any]:
    from scripts.prepare_wp08d_structural_reference import MESH_LEVELS, generate_mesh
    from solveur.contact.measures import reference_surface_areas

    archive_root = archive_root.resolve(strict=True)
    manifest = _load_verified_archive(archive_root, archive_manifest.resolve(strict=True))
    contract = json.loads((archive_root / "diagnostic_contract.json").read_text(encoding="utf-8"))
    final_record = json.loads((archive_root / "final.json").read_text(encoding="utf-8"))
    summary_path = ROOT / "qualification/0_2_9/wp08_surface_stiffness_remediation/surface_diagnostic_r3_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if contract.get("status") != "OWNER_AUTHORIZED_EXPERIMENTAL_DIAGNOSTIC_NOT_FORMAL":
        raise ValueError("unexpected R3 diagnostic contract status")
    if contract.get("physical_law", {}).get("excluded_x0_tributary_area_redistributed") is not False:
        raise ValueError("R3 does not declare the expected no-redistribution rule")
    kappa = float(contract["physical_law"]["tangential_stiffness_density_N_per_m3"])
    if kappa != EXPECTED_KAPPA:
        raise ValueError("R3 kappa differs from the Owner-authorized experimental value")
    if final_record.get("contract_sha256") != _sha256(archive_root / "diagnostic_contract.json"):
        raise ValueError("R3 final record does not bind the archived diagnostic contract")
    if final_record.get("source_bundle_sha256") != contract.get("source_bundle_sha256"):
        raise ValueError("R3 source bundle binding differs between contract and final record")
    if summary.get("campaign_final_json_sha256") != _sha256(archive_root / "final.json"):
        raise ValueError("compact R3 summary does not bind the archived final record")
    if summary.get("source_bundle_sha256") != contract.get("source_bundle_sha256"):
        raise ValueError("R3 source bundle binding differs between compact summary and contract")

    expected_sha = {entry["path"]: entry["sha256"] for entry in manifest["files"]}
    results: dict[str, Any] = {}
    for level in MESH_LEVELS:
        mesh = generate_mesh(level)
        areas = reference_surface_areas(mesh.nodes, mesh.bottom_faces)
        full_area = float(sum(areas.values()))
        eligible_area = float(sum(areas[node] for node in mesh.slave_nodes))
        expected_area = EXPECTED_AREAS[level.name]
        if not math.isclose(eligible_area, expected_area, rel_tol=1.0e-12, abs_tol=1.0e-14):
            raise ValueError(f"{level.name} eligible area differs from the recorded R3 value")
        if not math.isclose(full_area, 2.0, rel_tol=1.0e-12, abs_tol=1.0e-14):
            raise ValueError(f"{level.name} full reference patch area is not 2 m^2")

        result_path = f"{level.name}/production/result.json"
        result_file = archive_root / result_path
        if result_path not in expected_sha or _sha256(result_file) != expected_sha[result_path]:
            raise ValueError(f"{level.name} primary result is not bound by the archive manifest")
        result = json.loads(result_file.read_text(encoding="utf-8"))
        if result.get("status") != "PASS" or result.get("policy_digest") != contract.get("policy_digest"):
            raise ValueError(f"{level.name} primary status or policy digest mismatch")
        if result.get("source_bundle_sha256") != contract.get("source_bundle_sha256"):
            raise ValueError(f"{level.name} primary source bundle binding mismatch")
        contacts = result.get("contact", {}).get("contacts", [])
        active_rows = [row for row in contacts if row.get("active") is True]
        active_ids = [int(row["slave_node"]) for row in active_rows]
        active_coordinates = np.asarray([mesh.nodes[node] for node in active_ids], dtype=float)
        if len(active_coordinates) <= 1:
            support_dimension = max(len(active_coordinates) - 1, 0)
        else:
            centered = active_coordinates - np.mean(active_coordinates, axis=0)
            singular = np.linalg.svd(centered, compute_uv=False)
            tolerance = max(centered.shape) * np.finfo(float).eps * max(float(singular[0]), 1.0)
            support_dimension = int(np.count_nonzero(singular > tolerance))
        support_label = (
            "OPEN_NO_CONTACT" if not active_ids else "POINT_SAMPLE" if support_dimension == 0
            else "LINE_SAMPLE" if support_dimension == 1 else "NONCOLLINEAR_NODAL_SAMPLE_NOT_CONTINUUM_AREA"
        )
        results[level.name] = {
            "total_node_count": len(mesh.nodes),
            "body_node_count": len(mesh.nodes) - 4,
            "element_count": len(mesh.elements),
            "physical_bottom_patch_area_m2": full_area,
            "eligible_slave_area_m2": eligible_area,
            "excluded_x0_area_share_m2": full_area - eligible_area,
            "current_policy": compare_area_policies(
                physical_area_m2=full_area,
                eligible_area_m2=eligible_area,
                kappa_n_per_m3=kappa,
            ),
            "active_slave_nodes": active_ids,
            "active_slave_coordinates_m": active_coordinates.tolist(),
            "active_node_cloud_dimension": support_dimension,
            "active_support_interpretation": support_label,
        }

    if final_record.get("status") != "EXPERIMENTAL_ALL_GATES_PASS_CANDIDATE":
        raise ValueError("R3 campaign final record has an unexpected execution status")
    return {
        "schema_version": 1,
        "artifact_id": "QF-029-WP08-SURFACE-AREA-POLICY-DIAGNOSTIC-R1",
        "status": "PASS_READ_ONLY_AREA_DIAGNOSTIC_OWNER_DECISION_REQUIRED",
        "archive_manifest_sha256": _sha256(archive_manifest.resolve()),
        "archive_file_count": manifest["file_count"],
        "archive_total_bytes": manifest["total_bytes"],
        "r3_contract_sha256": _sha256(archive_root / "diagnostic_contract.json"),
        "r3_final_sha256": _sha256(archive_root / "final.json"),
        "r3_compact_summary_sha256": _sha256(summary_path),
        "policy_digest": contract["policy_digest"],
        "kappa_N_per_m3": kappa,
        "structural_solves_run": False,
        "reference_solves_run": False,
        "replays_run": False,
        "production_mechanics_modified": False,
        "thresholds_modified": False,
        "area_policy_choice": "HYPOTHETICAL_NORMALIZATION_ONLY_NOT_EXECUTED",
        "mesh_results": results,
        "hypothetical_normalized_total_stiffness_N_per_m": kappa * 2.0,
        "refinement_diagnostic": summary.get("m2_to_m3_diagnostic_refinement", {}),
        "owner_decision_required_before_any_mechanical_change": True,
        "formal_qualification": False,
        "points_awarded": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--archive-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "qualification/0_2_9/wp08_surface_stiffness_remediation"):
        raise ValueError("diagnostic output must remain in the dedicated WP08 evidence directory")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing diagnostic: {output}")
    report = analyze(args.archive_root, args.archive_manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
    print(json.dumps({"status": report["status"], "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
