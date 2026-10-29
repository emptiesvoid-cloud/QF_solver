"""WP12 VV3D prepared case nodes; all FEM entries remain disabled."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experiments.wp12_vv3d_adaptive import case_harness


@pytest.mark.parametrize(
    "case_id",
    [
        "VV3D-TET4-L1", "VV3D-TET4-L2", "VV3D-TET4-L3",
        "VV3D-TET10-L1", "VV3D-TET10-L2", "VV3D-TET10-L3",
        "VV3D-HEX8-L1", "VV3D-HEX8-L2", "VV3D-HEX8-L3",
        "VV3D-HEX20-L1", "VV3D-HEX20-L2", "VV3D-HEX20-L3",
    ],
)
def test_prepared_fem_case(case_id: str) -> None:
    """Stable prospective nodeid; deliberately skipped before any FEM call."""
    pytest.skip(f"{case_id}: PREPARED_NOT_AUTHORIZED; controller and manifests not integrated")


@pytest.mark.parametrize(
    "case_id",
    [f"VV3D-ADAPT-{family}-{kind}" for family in ("TET4", "TET10", "HEX8", "HEX20")
     for kind in ("H1", "QLOAD")],
)
def test_prepared_adaptive_fem_case(case_id: str) -> None:
    """Prospective adaptive FEM identities; no execution before official registration."""
    pytest.skip(f"{case_id}: PREPARED_NOT_AUTHORIZED; adaptive execution is not integrated")


@pytest.mark.parametrize("family", ["TET4", "TET10", "HEX8", "HEX20"])
def test_prepared_archived_postprocess_case(family: str) -> None:
    """Prospective archived-field postprocessing only; never performs an FEM solve."""
    pytest.skip(f"VV3D-ADAPT-{family}-QPOST: PREPARED_NOT_AUTHORIZED; archived-state path is not integrated")


def test_synthetic_inventory_hashes_and_execution_gate() -> None:
    cases = case_harness.load_prepared_cases()
    assert len(cases) == 12
    for case in cases:
        assert case["execution_authorized"] is False
        assert case["nodeid_status"] == "NOT_IMPLEMENTED_NOT_REGISTERED"
        with pytest.raises(PermissionError, match="PREPARED_NOT_AUTHORIZED"):
            case_harness.require_authorized_execution(case["case_id"])


def test_synthetic_sidecar_is_written_before_observable_assertions(tmp_path) -> None:
    case_id = "VV3D-TET4-L1"
    receipt = case_harness.write_synthetic_sidecar(tmp_path / "evidence", case_id, "SYNTHETIC-001")
    sidecar = Path(receipt["path"])
    saved = json.loads(sidecar.read_bytes())

    # This comparison runs only after persistence; actual measurements remain absent.
    assert hashlib.sha256(sidecar.read_bytes()).hexdigest() == receipt["sha256"]
    assert saved["case_state"] == "PREPARED_NOT_AUTHORIZED"
    assert saved["execution"] == {"status": "NOT_AUTHORIZED", "attempt_reserved": False, "fem_started": False}
    assert all(value == {"status": "NOT_EXPOSED"} for value in saved["observables"].values())
    assert all(value == {"status": "NOT_ASSESSED"} for value in saved["criteria"].values())


def test_synthetic_nonfinite_values_are_explicitly_preserved() -> None:
    result = case_harness.sanitize_for_evidence({"u": [1.0, float("nan"), float("inf")]})
    assert result["u"][0] == 1.0
    assert result["u"][1] == {"status": "NONFINITE", "representation": "nan"}
    assert result["u"][2] == {"status": "NONFINITE", "representation": "inf"}
    assert json.loads(json.dumps(result, allow_nan=False)) == result
