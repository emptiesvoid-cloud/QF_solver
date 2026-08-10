"""Fixtures for controlled V&V study tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_vnv_study(
    root: Path,
    *,
    decision: str = "pending",
    qf_error_scale: float = 1.0,
    include_artifacts: bool = True,
    deformation_requirement: str = "all",
    qf_unit: str = "m",
    validation_mode: str = "self_review",
    validator_name: str = "Quentin Farinazzo",
) -> Path:
    """Write a complete three-level study with a second-order error series."""
    levels = []
    for index, size in enumerate((0.4, 0.2, 0.1), start=1):
        level = f"h{index}"
        qf_path = root / "results" / f"{level}_qf.json"
        reference_path = root / "references" / f"{level}_reference.json"
        qf_artifacts = _artifacts(qf_path.parent, f"{level}_qf") if include_artifacts else {}
        reference_artifacts = (
            _artifacts(reference_path.parent, f"{level}_reference") if include_artifacts else {}
        )
        reference_value = 10.0
        qf_value = reference_value * (1.0 + qf_error_scale * size**2)
        _write_json(
            qf_path,
            _result("QF_solver", "0.2.0", level, size, qf_value, qf_unit, qf_artifacts),
        )
        _write_json(
            reference_path,
            _result("Abaqus", "2024", level, size, reference_value, "m", reference_artifacts),
        )
        levels.append(
            {
                "id": level,
                "characteristic_size": size,
                "qf_result": qf_path.relative_to(root).as_posix(),
                "reference_result": reference_path.relative_to(root).as_posix(),
            }
        )
    date = "2026-07-13" if decision != "pending" else None
    study = {
        "schema_version": 1,
        "study_id": "VNV-TET4-TEST-001",
        "title": "Etude V&V TET4 de test",
        "scope": "tet4-linear-static",
        "subject": {"kind": "element", "name": "TET4", "maturity": "candidate"},
        "units_system": "SI",
        "author": {"name": "Quentin Farinazzo", "role": "auteur du solveur"},
        "validation": {
            "validator": {"name": validator_name, "role": "validateur mecanique"},
            "mode": validation_mode,
            "decision": decision,
            "date": date,
            "comments": "Revue de test" if date else "",
        },
        "reference": {
            "kind": "commercial_solver",
            "solver": "Abaqus",
            "version": "2024",
            "manual_citation": "Abaqus Verification Manual, controlled test case",
            "case": "TET4-CANTILEVER",
        },
        "quantities": [
            {
                "id": "tip_uz",
                "label": "Deplacement en bout",
                "metric": "relative_error",
                "limit": 0.2,
                "absolute_floor": 1.0e-15,
                "extraction": {"location": "node_set=TIP", "component": "UZ", "reduction": "average"},
            }
        ],
        "levels": levels,
        "convergence": [
            {
                "quantity": "tip_uz",
                "require_monotonic": True,
                "minimum_order": 1.5,
                "finest_error_limit": 0.02,
            }
        ],
        "acceptance": {"deformation_requirement": deformation_requirement},
    }
    path = root / "study.json"
    _write_json(path, study)
    return path


def _result(
    producer: str,
    version: str,
    level: str,
    size: float,
    value: float,
    unit: str,
    artifacts: dict[str, str],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "case_id": "VNV-TET4-TEST-001",
        "producer": {"name": producer, "version": version, "run_id": f"{producer}-{level}"},
        "units_system": "SI",
        "mesh": {"nodes": 10, "elements": 12, "dofs": 30, "characteristic_size": size},
        "quantities": {"tip_uz": {"value": value, "unit": unit}},
        "diagnostics": {"relative_residual": 1.0e-12},
        "visualization": {
            "deformation_scale": 10.0,
            "field": "displacement_magnitude",
            "view": "isometric_xyz",
            "undeformed_overlay": True,
        },
        "artifacts": artifacts,
    }


def _artifacts(root: Path, prefix: str) -> dict[str, str]:
    root.mkdir(parents=True, exist_ok=True)
    png = root / f"{prefix}.png"
    vtu = root / f"{prefix}.vtu"
    png.write_bytes(b"controlled-test-png")
    vtu.write_text("<VTKFile></VTKFile>", encoding="utf-8")
    return {"deformation_png": png.name, "deformation_vtu": vtu.name}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
