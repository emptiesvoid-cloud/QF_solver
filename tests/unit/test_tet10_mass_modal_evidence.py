from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_controlled_tet10_mass_modal_load_evidence_passes() -> None:
    reference = ROOT / "qualification" / "vnv" / "tet10_mass_modal_loads" / "reference"
    summary = json.loads((reference / "summary.json").read_text(encoding="utf-8"))

    assert summary["study_id"] == "VNV-TET10-MASS-MODAL-LOADS-013"
    assert summary["status"] == "PASS_TECHNICAL_VERIFICATION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert summary["modal"]["maximum_frequency_error"] < 0.01
    assert summary["curved_pressure"]["relative_moment_error"] < 1.0e-12
    assert summary["curved_stress_recovery"]["relative_stress_error"] < 1.0e-12
    assert (reference / "tet10_modal_mode1.png").stat().st_size > 1000
