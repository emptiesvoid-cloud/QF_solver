from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[2]
POLICY = ROOT / "qualification" / "stress_observable_policy_0_2_1.json"
EVIDENCE = ROOT / "qualification" / "maturity_evidence_0_2_1"


def test_tet10_stress_policy_declares_bounded_observables() -> None:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["interior_probe"]["minimum_margin_fraction"] == 0.2
    assert policy["interior_probe"]["minimum_probe_count"] == 3
    assert "pointwise_peak_at_true_singularity" in policy["informative_only_observables"]
    assert policy["acceptance_thresholds"]["reference_relative_error"] == 0.1


def test_tet10_stress_evidence_matches_policy() -> None:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    limit = policy["acceptance_thresholds"]["reference_relative_error"]
    for relative_path in policy["current_evidence"]:
        summary = json.loads((ROOT / relative_path).read_text(encoding="utf-8"))
        assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
        observable = summary["observable"]
        assert len(observable["probe_element_indices"]) >= policy["interior_probe"]["minimum_probe_count"]
        assert observable["probe_margin_fraction"] >= policy["interior_probe"]["minimum_margin_fraction"]
        assert observable["singular_boundaries_excluded"] is True
        assert observable["relative_l2_difference"] <= limit
