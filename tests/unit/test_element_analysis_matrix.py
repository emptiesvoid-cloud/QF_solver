from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "qualification" / "element_analysis_matrix.json"
CLOSURE_REGISTER = ROOT / "qualification" / "reviews" / "linear_dynamic_closure_register.json"


def test_element_analysis_matrix_is_complete_and_references_existing_evidence() -> None:
    data = json.loads(MATRIX.read_text(encoding="utf-8"))
    expected = {"TET4", "TET10", "MITC4", "MITC3", "BEAM2", "SPRING_MASS", "CONTACT"}
    assert set(data["families"]) == expected
    statuses = set(data["status_values"])
    for family in data["families"].values():
        for analysis, coverage in family.items():
            if analysis == "evidence":
                for relative in coverage:
                    assert (ROOT / relative).exists(), relative
                continue
            assert coverage["status"] in statuses
            if coverage["status"] == "unsupported":
                assert coverage["scope"] is None


def test_element_analysis_matrix_matches_current_owner_promotions_and_limits() -> None:
    families = json.loads(MATRIX.read_text(encoding="utf-8"))["families"]
    assert families["MITC4"]["modal"]["status"] == "stable"
    assert families["MITC3"]["modal"]["status"] == "stable"
    assert families["TET10"]["harmonic"]["status"] == "stable"
    # The public checkout deliberately excludes generated/private V&V folders.
    # Keep this assertion on the tracked promotion dossier instead of an
    # ignored local summary that cannot be reproduced from a fresh clone.
    assert "docs/verification/tet10_stable_promotion_owner_review_0_2_1.md" in families["TET10"]["evidence"]
    assert families["BEAM2"]["transient_newmark"]["status"] == "stable"
    assert families["SPRING_MASS"]["harmonic"]["status"] == "stable"
    assert families["TET4"]["nonlinear_dynamic"]["status"] == "unsupported"
    assert families["MITC4"]["material_nonlinear_static"]["status"] == "unsupported"


def test_mitc3_static_owner_review_is_final_and_bounded() -> None:
    review = json.loads(
        (ROOT / "qualification" / "reviews" / "mitc3_linear_static_2026-08-01.json").read_text(
            encoding="utf-8"
        )
    )
    assert review["decision"] == "accepted_for_bounded_engineering_use"
    assert review["decision_date"] == "2026-08-01"
    assert review["blocking_items"] == []
    assert "nonlinear_dynamic" not in review["accepted_domain"]
    assert any("modal" in item for item in review["excluded_domain"])


def test_linear_dynamic_closure_register_references_real_evidence() -> None:
    register = json.loads(CLOSURE_REGISTER.read_text(encoding="utf-8"))
    assert register["status"] == "owner_decisions_recorded"
    assert (ROOT / register["owner_review_template"]).is_file()
    assert (ROOT / register["owner_review_dossier"]).is_file()
    for entry in register["reviews"]:
        assert (ROOT / entry["evidence"]).is_file()
    discrete = next(entry for entry in register["reviews"] if entry["scope"] == "discrete-linear-dynamics")
    assert discrete["status"] == "owner_accepted"
    assert discrete["remaining"] == []
