from __future__ import annotations

import pytest

from solveur.verification.singularity_stress import SingularityStressAssessor, StressPathSample


def _sample(mesh_size: float, values: tuple[float, float], band: float) -> StressPathSample:
    return StressPathSample(mesh_size, (0.04, 0.08), values, band)


def test_true_singularity_uses_paths_and_bands_not_the_point_peak() -> None:
    result = SingularityStressAssessor().assess(
        (
            _sample(0.02, (100.0, 80.0), 85.0),
            _sample(0.01, (104.0, 82.0), 87.0),
            _sample(0.005, (106.0, 83.0), 88.0),
        ),
        true_singularity=True,
        reference_values=(108.0, 84.0),
        reference_band_average=89.0,
        reference_kind="code_aster",
    )

    assert result["status"] == "PASS"
    assert result["point_peak_rule"] == "informative_only_true_singularity"
    assert all(check["status"] == "PASS" for check in result["checks"])


def test_finite_concentration_requires_a_resolved_sampling_path() -> None:
    result = SingularityStressAssessor().assess(
        (
            _sample(0.02, (94.0, 76.0), 80.0),
            _sample(0.01, (97.0, 78.0), 82.0),
            _sample(0.005, (98.5, 79.0), 83.0),
        ),
        true_singularity=False,
        reference_values=(100.0, 80.0),
        reference_band_average=84.0,
        reference_kind="analytic",
    )

    assert result["status"] == "PASS"
    assert result["point_peak_rule"] == "eligible_only_after_finite_radius_convergence"


def test_rejects_inconsistent_sampling_distances() -> None:
    assessor = SingularityStressAssessor()
    with pytest.raises(ValueError, match="identical physical sampling distances"):
        assessor.assess(
            (
                _sample(0.02, (100.0, 80.0), 85.0),
                StressPathSample(0.01, (0.03, 0.08), (104.0, 82.0), 87.0),
                _sample(0.005, (106.0, 83.0), 88.0),
            ),
            true_singularity=True,
            reference_values=(108.0, 84.0),
            reference_band_average=89.0,
            reference_kind="calculix",
        )
