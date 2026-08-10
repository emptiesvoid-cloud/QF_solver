from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_tet4_total_lagrangian_v2_review_is_bounded_and_traceable() -> None:
    review_path = (
        ROOT
        / "qualification"
        / "reviews"
        / "tet4_total_lagrangian_structural_v2_2026-07-18.json"
    )
    review = json.loads(review_path.read_text(encoding="utf-8"))

    assert review["scope"] == "tet4-total-lagrangian-structural-v2"
    assert review["decision"] == "accepted_with_recommendations"
    assert review["decision_date"] == "2026-07-18"
    assert review["validator"]["name"] == "Quentin Farinazzo"
    assert review["review_mode"] == "self_review"
    assert review["independence"] == "not_independent"
    assert review["certification_claim"] == "none"
    assert set(review["evidence"]) >= {
        "VNV-TET4-TL-STRESS-005",
        "VNV-TET4-TL-BUCKLING-EULER-006",
        "VNV-TET4-TL-POSTBUCKLING-007",
        "VNV-TET4-TL-CALCULIX-STRUCTURAL-008",
        "VNV-TET4-TL-CODEASTER-STRUCTURAL-009",
        "VNV-TET4-TL-BUCKLING-H5-010",
    }
    assert any("qualification externe" in item for item in review["excluded_domain"])


def test_tet4_total_lagrangian_v2_review_document_exists() -> None:
    review_path = (
        ROOT
        / "qualification"
        / "reviews"
        / "tet4_total_lagrangian_structural_v2_2026-07-18.json"
    )
    review = json.loads(review_path.read_text(encoding="utf-8"))

    assert (ROOT / review["review_document"]).is_file()
