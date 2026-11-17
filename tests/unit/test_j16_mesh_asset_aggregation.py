"""Pure validation tests for the J16 multi-mesh site-asset builder."""

from __future__ import annotations

import pytest

from research.j16.aggregate_harmonic_mesh_study import validate_mesh_data


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
