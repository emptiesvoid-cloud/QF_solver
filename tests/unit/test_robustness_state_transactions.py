from solveur.verification.robustness_nonlinear_solids import transaction_check


def test_failed_trial_does_not_contaminate_committed_state() -> None:
    result = transaction_check()

    assert result == {"status": "PASS", "rollback_untouched": True, "commit_changed": True}
