"""Recompute N08 force-work/energy bookkeeping from archived fields only.

This diagnostic does not import the FEM solver, assemble a matrix, or run a
model. It validates the N08 archive inventory and reads only its JSON records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def recompute(archive: Path) -> dict[str, Any]:
    integrity_path = archive / "archive_integrity_manifest.json"
    integrity = _load_json(integrity_path)
    entries = integrity.get("files")
    if not isinstance(entries, list) or integrity.get("file_count") != len(entries):
        raise ValueError("archive integrity manifest has an invalid file inventory")
    for entry in entries:
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe archive-relative path: {relative}")
        source = archive / relative
        if not source.is_file() or source.stat().st_size != entry["size_bytes"]:
            raise ValueError(f"archived file missing or size mismatch: {relative}")
        if _sha256(source) != entry["sha256"]:
            raise ValueError(f"archived file hash mismatch: {relative}")

    levels: dict[str, Any] = {}
    for level in ("m4", "m5"):
        diagnostic_path = archive / f"{level}_diagnostics.json"
        record = _load_json(diagnostic_path)
        fields = record.get("field_values", {})
        diagnostics = record.get("diagnostics", {})
        nodes = fields.get("contact_node_ids")
        multipliers = fields.get("contact_multipliers_n")
        displacements = fields.get("body_displacements_m_node_major_xyz")
        if not (isinstance(nodes, list) and isinstance(multipliers, list) and isinstance(displacements, list)):
            raise ValueError(f"{level.upper()} lacks archived contact or displacement fields")
        if len(nodes) != len(multipliers):
            raise ValueError(f"{level.upper()} contact IDs and forces have different lengths")
        contact_work = 0.0
        for node, force in zip(nodes, multipliers):
            if isinstance(node, bool) or not isinstance(node, int) or not 0 <= node < len(displacements):
                raise ValueError(f"{level.upper()} has invalid contact node ID {node!r}")
            xyz = displacements[node]
            if not isinstance(xyz, list) or len(xyz) != 3:
                raise ValueError(f"{level.upper()} has invalid node-major XYZ displacement")
            contact_work += float(force) * float(xyz[2])
        recorded_work = float(diagnostics["production_contact_work_j"])
        if not math.isclose(contact_work, recorded_work, rel_tol=0.0, abs_tol=1.0e-10):
            raise ValueError(f"{level.upper()} recomputed contact work disagrees with archive diagnostic")
        old_energy = float(diagnostics["strain_energy_j"])
        quadrature_energy = float(diagnostics["fe_integrated_strain_energy_j"])
        # This endpoint product supports the algebraic energy correction; it
        # does not infer the path integral of contact forces.
        corrected_energy = old_energy + 0.5 * contact_work
        levels[level.upper()] = {
            "diagnostic_sha256": _sha256(diagnostic_path),
            "archived_contact_work_j": recorded_work,
            "recomputed_contact_work_j": contact_work,
            "archived_matrix_energy_misinterpreted_as_elastic_j": old_energy,
            "corrected_elastic_energy_j_offline": corrected_energy,
            "quadrature_elastic_energy_j_archived": quadrature_energy,
            "old_matrix_quadrature_error_j": abs(old_energy - quadrature_energy),
            "corrected_matrix_quadrature_error_j_offline": abs(corrected_energy - quadrature_energy),
            "raw_production_internal_force_archived": False,
            "production_stationarity_status": "NOT_EVALUATED",
        }
    return {
        "status": "OFFLINE_DIAGNOSTIC_ONLY",
        "archive_directory_name": archive.name,
        "archive_integrity_manifest_sha256": _sha256(integrity_path),
        "archive_file_count_validated": len(entries),
        "formula": "U_el = U_old + 0.5 C_contact; U_old=0.5 u.(K u-P), C_contact=u.P, production internal=K u-P",
        "contact_work_interpretation": "endpoint force-displacement product used in the AR identity; no physical path-integrated contact work is inferred",
        "no_fem_or_matrix_assembly_performed": True,
        "missing_evidence": [
            "raw production internal_force vector",
            "raw production residual vector",
            "production stiffness matrix/vector K u",
        ],
        "production_stationarity": "NOT_EVALUATED because the archived raw force/residual vectors are absent",
        "levels": levels,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {args.output}")
    result = recompute(args.archive.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "status": result["status"], "levels": result["levels"]}, indent=2))


if __name__ == "__main__":
    main()
