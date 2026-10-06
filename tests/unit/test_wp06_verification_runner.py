from scripts.run_wp06_verification import _summarize_mesh_convergence


def _frequency_comparison(relative_error: float) -> dict[str, float | str]:
    return {
        "coarse_frequency_hz": 100.0,
        "fine_frequency_hz": 100.0 * (1.0 - relative_error),
        "relative_error": relative_error,
        "status": "PASS",
    }


def test_mesh_summary_excludes_partial_coverage_counts_from_frequency_delta() -> None:
    summary = _summarize_mesh_convergence(
        [_frequency_comparison(0.0002), _frequency_comparison(0.0004)],
        [
            {"spin_speed_rad_s": 0.0, "compared_mode_count": 4, "status": "PASS"},
            {
                "spin_speed_rad_s": 100.0,
                "compared_mode_count": 2,
                "status": "PASS_WITH_RECORDED_AMBIGUITY",
            },
        ],
        0.005,
    )

    assert summary["observed_value"] == 0.0004
    assert summary["compared_tracked_frequencies"] == 2
    assert summary["partial_coverage_speeds_rad_s"] == [100.0]
    assert summary["status"] == "PASS"


def test_mesh_summary_fails_when_any_requested_speed_has_no_comparable_branch() -> None:
    summary = _summarize_mesh_convergence(
        [_frequency_comparison(0.0002)],
        [{"spin_speed_rad_s": 100.0, "compared_mode_count": 0, "status": "FAIL"}],
        0.005,
    )

    assert summary["status"] == "FAIL"
    assert summary["coverage_failure_count"] == 1


def test_mesh_summary_fails_on_tracked_branch_multiplicity_mismatch() -> None:
    summary = _summarize_mesh_convergence(
        [
            {
                "branch_id": "cluster-001",
                "expected_value": "same tracked branch multiplicity",
                "observed_value": [2, 1],
                "status": "FAIL",
            }
        ],
        [{"spin_speed_rad_s": 100.0, "compared_mode_count": 1, "status": "PASS_WITH_RECORDED_AMBIGUITY"}],
        0.005,
    )

    assert summary["status"] == "FAIL"
    assert summary["structural_mismatch_count"] == 1
