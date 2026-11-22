"""Tests for the non-certifying G08 matrix spectral screen."""

import numpy as np
import pytest

from research.g08_compare.spectral_diagnostic import SpectralInputError, screen_matrices


def _screen(k0, kg, *, factor=4.0, bracket=None, mode=None):
    dimension = np.asarray(k0).shape[0]
    full_dof_count = dimension + 1
    candidate_mode = np.ones(full_dof_count) if mode is None else np.asarray(mode, dtype=float)
    return screen_matrices(
        np.asarray(k0, dtype=float),
        np.asarray(kg, dtype=float),
        candidate_factor=factor,
        candidate_bracket=bracket or {"lower": factor - 0.01, "upper": factor + 0.01},
        candidate_mode=candidate_mode,
        free_dof_indices=np.arange(1, full_dof_count),
        full_dof_count=full_dof_count,
    )


def test_known_spd_pencil_reports_numeric_rank_without_establishing_first_mode():
    result = _screen(np.diag([4.0, 9.0]), -np.eye(2), factor=9.0)

    assert result["K0_status"] == "POSITIVE_DOUBLE_PRECISION_SCREEN"
    assert result["candidate_root_rank_numeric"] == 2
    assert result["root_rank_status"] == "NOT_RANK_1_NUMERICAL_SCREEN"
    assert result["positivity_and_inertia_certified"] is False
    assert result["first_mode_status"] == "FIRST_MODE_NOT_ESTABLISHED"


def test_candidate_at_smallest_numeric_root_still_is_not_a_proof():
    result = _screen(np.diag([4.0, 9.0]), -np.eye(2), factor=4.0)

    assert result["candidate_root_rank_numeric"] == 1
    assert result["root_rank_status"] == "RANK_1_NUMERICAL_SCREEN"
    assert result["first_mode_status"] == "FIRST_MODE_NOT_ESTABLISHED"


def test_indefinite_k0_does_not_evaluate_candidate_rank():
    result = _screen(np.diag([-1.0, 9.0]), -np.eye(2), factor=1.0)

    assert result["K0_status"] == "K0_POSITIVITY_INDETERMINATE"
    assert result["root_rank_status"] == "NOT_EVALUATED_K0_POSITIVITY_INDETERMINATE"
    assert "candidate_root_rank_numeric" not in result


def test_nonsymmetric_matrices_are_not_silently_symmetrized():
    result = _screen(np.asarray([[2.0, 0.5], [0.0, 3.0]]), -np.eye(2))

    assert result["K0_status"] == "K0_SYMMETRY_OUTSIDE_SCREEN"
    assert result["root_rank_status"] == "NOT_EVALUATED"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"factor": 0.0},
        {"bracket": {"lower": 2.0, "upper": 1.0}},
        {"mode": np.zeros(3)},
    ],
)
def test_invalid_factor_bracket_or_zero_candidate_mode_is_rejected(kwargs):
    with pytest.raises(SpectralInputError):
        _screen(np.eye(2), -np.eye(2), **kwargs)
