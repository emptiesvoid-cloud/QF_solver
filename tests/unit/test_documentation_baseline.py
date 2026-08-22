from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_p0_documentation_baseline_declares_automatic_evidence_and_owner_review_blockers() -> None:
    baseline = json.loads(
        (ROOT / "qualification" / "baselines" / "documentation_baseline_p0.json").read_text(
            encoding="utf-8"
        )
    )

    assert baseline["status"] == "technical_documentation_closed"
    assert baseline["certification_claim"] == "none"
    assert baseline["owner_review_blockers"]
    for path in baseline["automated_evidence"].values():
        assert (ROOT / path).is_file(), path
    review_path = ROOT / baseline["external_reference_policy"]["accepted_review"]
    review = json.loads(review_path.read_text(encoding="utf-8"))
    assert review["decision"] == "accepted_with_recommendations"
    assert review["certification_claim"] == "none"

    policy = json.loads((ROOT / "qualification" / "external_oracle_policy.json").read_text(encoding="utf-8"))
    assert {item["name"] for item in policy["active_oracles"]} >= {"Code_Aster", "CalculiX"}
    assert policy["commercial_tools"]["Abaqus"] == "historical_published_reference_only"
