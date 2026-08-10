import json
from pathlib import Path

from solveur.verification.mitc4_modal_extended import (
    CurvedDistortedShellStudy,
    FoldedShellFreeFreeStudy,
    SparseModalScalingStudy,
)


ROOT = Path(__file__).resolve().parents[2]


def test_folded_shell_has_six_correlated_rigid_modes() -> None:
    summary = FoldedShellFreeFreeStudy().run()
    assert summary["status"] == "PASS"
    assert summary["checks"]["exactly_six_rigid_modes"] is True
    assert min(summary["metrics"]["rigid_subspace_principal_mac"]) > 0.999999


def test_curved_distorted_shell_modal_invariants_pass() -> None:
    summary = CurvedDistortedShellStudy().run()
    assert summary["status"] == "PASS"
    assert max(summary["metrics"]["distorted_frequency_differences"]) < 0.01
    assert max(summary["metrics"]["rotated_frequency_differences"]) < 1.0e-8


def test_sparse_modal_solver_matches_dense_and_scales() -> None:
    summary = SparseModalScalingStudy().run()
    assert summary["status"] == "PASS"
    assert summary["large_sparse"]["retained_dof_count"] >= 5000
    assert summary["large_sparse"]["dense_conversion_used"] is False
    assert max(summary["medium_crosscheck"]["relative_frequency_differences"]) < 1.0e-8


def test_independent_review_stays_unsigned_until_an_external_reviewer_acts() -> None:
    template = json.loads(
        (
            ROOT
            / "qualification"
            / "reviews"
            / "mitc4_modal_independent_review_template.json"
        ).read_text(encoding="utf-8")
    )
    assert template["status"] == "pending"
    assert template["reviewer"] is None
    assert template["decision"] is None
    assert template["required_independence"] == "reviewer_not_author_or_implementer"
