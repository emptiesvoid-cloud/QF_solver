from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_tet4_internal_review_is_bounded_and_traceable() -> None:
    path = ROOT / "qualification" / "reviews" / "tet4_linear_isotropic_2026-07-14.json"
    review = json.loads(path.read_text(encoding="utf-8"))

    assert review["decision"] == "accepted"
    assert review["decision_date"] == "2026-07-14"
    assert review["use_class"] == "engineering_internal"
    assert review["project_visibility_at_decision"] == "private"
    assert review["review_mode"] == "self_review"
    assert review["independence"] == "not_independent"
    assert review["certification_claim"] == "none"
    assert set(review["evidence"]) >= {
        "BM-SOL-TET4-PATCH-001",
        "BM-SOL-TET4-MEMBRANE-001",
        "BM-SOL-CANTILEVER-001",
        "BM-SOL-TET4-TORSION-001",
        "VNV-TET4-TORSION-ANALYTIC-001",
        "VNV-TET4-TORSION-STRESS-H9-001",
    }
    assert review["convergence_summary"]["flexion_mesh_levels"] == 6
    assert review["convergence_summary"]["torsion_mesh_levels"] == 8
    assert review["convergence_summary"]["traction_mesh_levels"] == 5
    assert review["convergence_summary"]["compression_mesh_levels"] == 5
    assert review["review_revision"] == 2
    assert review["convergence_summary"]["torsion_stress_probe_elements"] == 105_529
    assert review["convergence_summary"]["torsion_stress_probe_relative_stress_l2_error"] < 0.20
    assert "pointwise_torsion_stress_peaks" in review["explicit_exclusions"]
