"""J10 bounded modal-route smoke on one TET10 element."""

from __future__ import annotations

import math

from research.j10_modal.tet10_modal_smoke import MODE_COUNT, run_modal_route_smoke


def test_j10_tet10_modal_route_smoke() -> None:
    result = run_modal_route_smoke()
    assert result["execution_status"] == "COMPLETED_EXPLORATORY"
    assert result["contract_id"] == "J10-TET10-MODAL-ROUTE-SMOKE-CORRECTIVE-002"
    assert result["attempt_id"] == "J10-TET10-MODAL-ROUTE-SMOKE-ATTEMPT-002"
    assert result["development_attempt_number"] == 2
    assert result["model"]["free_dof_count"] == 12
    assert result["model"]["requested_modes"] == MODE_COUNT
    assert result["route"]["numerical_status"] in {"PASS", "INCONCLUSIVE", "FAIL"}
    assert result["route"]["returned_frequency_count"] == len(result["route"]["frequencies_hz"])
    assert result["reference"]["mode_count_compared"] == len(result["reference"]["relative_frequency_differences"])
    assert all(math.isfinite(value) and value > 0.0 for value in result["route"]["frequencies_hz"])
    assert all(math.isfinite(value) and value >= 0.0 for value in result["reference"]["relative_frequency_differences"])
    if result["route"]["numerical_status"] == "PASS":
        assert result["route"]["returned_frequency_count"] == MODE_COUNT
        assert result["route"]["frequency_payload_valid"] is True
        assert result["route"]["mode_payload_valid"] is True
        assert result["reference"]["mode_count_compared"] == MODE_COUNT
    assert result["reference"]["validates"].startswith("the modal route")
