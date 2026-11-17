"""Pure validation tests for the J16 multi-mesh site-asset builder."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research.j16.aggregate_harmonic_mesh_study import validate_mesh_data


def test_asset_contract_nests_input_hashes_and_preserves_failed_attempt() -> None:
    root = Path(__file__).resolve().parents[2]
    contract = json.loads(
        (root / "research/j16/contracts/nafems_13h_mesh_site_assets_002.json").read_text(
            encoding="utf-8"
        )
    )
    assert contract["contract_id"] == "J16-NAFEMS13H-MESH-SITE-ASSETS-002"
    assert "input_sha256" in contract["inputs"]
    assert contract["source"]["prior_attempt"]["state"] == "PYTHON_FAILED"


def _mesh_data(mesh_size: int) -> dict:
    return {
        "geometry_m": {"length": 10.0},
        "material": {"young_modulus_pa": 200e9},
        "pressure_pa": 100.0,
        "rayleigh_damping": {"alpha_s_inv": 0.299},
        "conditions": "same",
        "observable": "center UZ",
        "frequency_grid_hz": {"count": 62},
        "rows": [
            {"frequency_hz": float(i), "qf_route_status": "QF_GUARD_REJECTED"}
            for i in range(62)
        ],
        "mesh_size": mesh_size,
    }


def test_mesh_asset_validation_keeps_rejected_statuses() -> None:
    validate_mesh_data({mesh: _mesh_data(mesh) for mesh in (6, 8, 10)})


def test_mesh_asset_validation_rejects_inconsistent_support_setup() -> None:
    mesh_data = {mesh: _mesh_data(mesh) for mesh in (6, 8, 10)}
    mesh_data[10]["conditions"] = "different"
    with pytest.raises(ValueError, match="frozen model"):
        validate_mesh_data(mesh_data)
