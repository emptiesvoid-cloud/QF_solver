from solveur.verification.mitc4_newmark import Mitc4NewmarkFreeVibrationStudy


def test_mitc4_newmark_converges_at_second_order_on_verified_mode() -> None:
    summary = Mitc4NewmarkFreeVibrationStudy(
        steps_per_period=(20, 40, 80),
        periods=2,
    ).run()

    assert summary["status"] == "PASS"
    assert all(summary["checks"].values())
    assert min(summary["observed_orders"]) > 1.9
    assert summary["points"][-1]["normalized_rms_error"] < 0.003
    assert summary["points"][-1]["maximum_relative_energy_drift"] < 1.0e-8
