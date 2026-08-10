from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_controlled_tet10_structural_convergence_evidence_passes() -> None:
    reference = ROOT / "qualification" / "vnv" / "tet10_structural_convergence" / "reference"
    summary = json.loads((reference / "summary.json").read_text(encoding="utf-8"))

    assert summary["study_id"] == "VNV-TET10-STRUCTURAL-CONVERGENCE-012"
    assert summary["status"] == "PASS_TECHNICAL_VERIFICATION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert summary["bending"]["families"]["TET10"]["finest_response_error"] < 0.02
    assert summary["torsion"]["families"]["TET10"]["levels"][-1]["stress_error"] < 0.02
    assert (reference / "tet10_structural_convergence.png").stat().st_size > 1000
