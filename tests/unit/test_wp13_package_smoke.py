"""Synthetic tests for the installed-package smoke contract; no FEM is run."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from scripts.wp13_package_smoke import ContractError, append_reservation, evaluate_oracle


def test_package_smoke_oracles_and_one_shot_reservation_are_fail_closed(tmp_path: Path) -> None:
    ledger = tmp_path / "attempts.jsonl"
    reservation = {
        "event": "RESERVED",
        "reservation_key": "a" * 64,
        "manifest_sha256": "b" * 64,
        "case_id": "SYNTHETIC-NO-FEM",
        "artifact_id": "synthetic-child",
    }
    append_reservation(ledger, reservation)
    with pytest.raises(ContractError, match="retries are prohibited"):
        append_reservation(ledger, reservation)

    static_oracle = {
        "ux_m": 2.1224489795918369e-8,
        "ux_relative_tolerance": 1e-12,
        "von_mises_pa": 3428.5714285714284,
        "stress_relative_tolerance": 1e-12,
        "free_relative_residual_max": 1e-9,
        "reaction_resultant_x_n": -1000.0,
        "reaction_absolute_tolerance_n": 1e-10,
        "force_balance_relative_error_max": 1e-12,
        "linear_energy_identity_relative_error_max": 1e-9,
    }
    static_payload = {
        "status": "PASS",
        "analysis": "linear_static",
        "displacements": [{"node": 1, "dofs": {"UX": static_oracle["ux_m"]}}],
        "element_results": [{"von_mises": static_oracle["von_mises_pa"]}],
        "audit": {
            "equilibrium": {
                "free_relative_residual": 1e-12,
                "reaction_resultant": [-1000.0, 0.0, 0.0],
                "force_balance_relative_error": 1e-15,
                "linear_energy_identity_relative_error": 1e-15,
            }
        },
    }
    assert evaluate_oracle("STATIC-01", static_payload, static_oracle)["passed"]

    modal_oracle = {
        "first_frequency_hz": 1619.5553821068941,
        "frequency_relative_tolerance": 1e-12,
        "max_relative_eigen_residual": 1e-10,
        "mass_orthogonality_error_max": 1e-10,
        "stiffness_diagonal_error_max": 1e-10,
    }
    modal_payload = {
        "status": "PASS",
        "analysis": "modal",
        "modes": [
            {"frequency_hz": modal_oracle["first_frequency_hz"]},
            {"frequency_hz": 1619.5553821068941},
            {"frequency_hz": 3270.0},
        ],
        "solver": {
            "max_relative_residual": 1e-12,
            "mass_orthogonality_error": 1e-12,
            "stiffness_diagonal_error": 1e-12,
        },
    }
    assert evaluate_oracle("MODAL-01", modal_payload, modal_oracle)["passed"]

    dynamic_oracle = {
        "stiffness_n_per_m": 200.0,
        "mass_kg": 1.0 / 6.0,
        "initial_displacement_m": 0.001,
        "initial_velocity_m_s": 0.0,
        "expected_energy_j": 0.0001,
        "energy_relative_tolerance": 1e-10,
        "first_record_time_s": 0.001,
        "history_index": 39,
        "history_step": 40,
        "final_time_s": 0.04,
        "history_energy_consistency_absolute_tolerance_j": 1e-14,
        "relative_energy_drift_absolute_tolerance": 1e-10,
        "dynamic_residual_norm_max": 1e-10,
        "free_relative_residual_max": 1e-10,
    }
    final_velocity = math.sqrt(2.0 * dynamic_oracle["expected_energy_j"] / dynamic_oracle["mass_kg"])
    dynamic_payload = {
        "status": "PASS",
        "analysis": "transient_dynamic",
        "method": "newmark",
        "displacements": [{"node": 1, "dofs": {"UX": 0.0}}],
        "velocities": [{"node": 1, "dofs": {"UX": final_velocity}}],
        "solver": {
            "time_history": [
                {"step": step, "time": step * 0.001, "total_energy": 0.0001, "dynamic_residual_norm": 0.0}
                for step in range(1, 41)
            ]
        },
        "audit": {"equilibrium": {"free_relative_residual": 0.0}},
    }
    assert evaluate_oracle("DYNAMIC-01", dynamic_payload, dynamic_oracle)["passed"]

    static_payload["displacements"][0]["dofs"]["UX"] *= 1.01
    assert not evaluate_oracle("STATIC-01", static_payload, static_oracle)["passed"]
