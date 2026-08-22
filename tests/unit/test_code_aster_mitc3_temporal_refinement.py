"""Unit tests for the external MITC3+ temporal diagnostic aggregator."""

from __future__ import annotations

import json

from solveur.verification.code_aster_mitc3_temporal_refinement import _checks, _row


def _summary(steps: int, modal: float, newmark: float, harmonic: float) -> dict:
    return {
        "status": "PASS_EXTERNAL_CORRELATION",
        "comparison_basis": {"steps_per_period": steps},
        "newmark": {"time_step_s": 1.0 / steps},
        "checks": [
            {"id": "modal_frequencies", "value": modal},
            {"id": "newmark_tip_history", "value": newmark},
            {"id": "newmark_forced_history", "value": 0.003},
            {"id": "newmark_free_history", "value": 0.026},
            {"id": "harmonic_tip_response", "value": harmonic},
            {"id": "qf_modal_residual", "value": 1.0e-9},
            {"id": "qf_dynamic_residual", "value": 1.0e-10},
        ],
    }


def test_temporal_external_diagnostic_detects_persistent_formulation_gap() -> None:
    rows = [_row(_summary(steps, 0.039, 0.0232, 0.0134)) for steps in (80, 160, 320)]

    checks = _checks(rows, 0.01, 1.0e-7)

    assert all(item["status"] == "PASS" for item in checks)
    assert next(item for item in checks if item["id"] == "newmark_external_persistent_over_one_percent")["value"] > 0.01


def test_temporal_external_row_is_serializable() -> None:
    row = _row(_summary(80, 0.039, 0.0232, 0.0134))

    json.dumps(row)
    assert row["steps_per_period"] == 80
    assert row["newmark_error"] == 0.0232
