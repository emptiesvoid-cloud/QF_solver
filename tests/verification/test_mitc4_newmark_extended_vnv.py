from solveur.verification.mitc4_newmark_extended import Mitc4NewmarkDampedForcedStudy


def test_mitc4_newmark_damped_and_forced_histories_converge_quadratically() -> None:
    summary = Mitc4NewmarkDampedForcedStudy(
        steps_per_period=(20, 40, 80),
        periods=2,
    ).run()

    assert summary["status"] == "PASS"
    assert all(summary["checks"].values())
    assert min(summary["damped_observed_orders"]) > 1.9
    assert min(summary["forced_observed_orders"]) > 1.9
    assert summary["damped_points"][-1]["normalized_rms_error"] < 0.003
    assert summary["forced_points"][-1]["normalized_rms_error"] < 0.004
