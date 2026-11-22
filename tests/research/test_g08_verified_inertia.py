"""Synthetic tests for the stored-matrix verified-inertia research tool."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

pytest.importorskip("flint")

from research.g08_compare.verified_inertia import (  # noqa: E402
    VerifiedInertiaBackendUnavailable,
    VerifiedInertiaInputError,
    certify_indefinite_witnesses,
    certify_pencil_inertia,
    certify_symmetric_inertia,
    floating_ldl_crosscheck,
    refine_certified_root_bracket,
    residual_enclosure,
)


def test_certifies_positive_definite_and_repeated_eigenvalues() -> None:
    result = certify_symmetric_inertia(np.diag([1.0, 2.0, 2.0, 5.0]))

    assert result["status"] == "CERTIFIED"
    assert result["inertia"] == {"negative": 0, "zero": 0, "positive": 4}


def test_certifies_indefinite_two_by_two_structure_and_witnesses() -> None:
    matrix = np.array([[0.0, 1.0], [1.0, 0.0]])

    inertia = certify_symmetric_inertia(matrix)
    witnesses = certify_indefinite_witnesses(matrix)

    assert inertia["status"] == "CERTIFIED"
    assert inertia["inertia"] == {"negative": 1, "zero": 0, "positive": 1}
    assert witnesses["status"] == "CERTIFIED_INDEFINITE"


def test_singular_zero_and_low_precision_uncertainty_stay_indeterminate() -> None:
    singular = np.array([[1.0, 1.0], [1.0, 1.0]])

    result = certify_symmetric_inertia(singular, precision_bits=64)

    assert result["status"] == "INDETERMINATE_APPROXIMATE_DIAGONAL_HAS_ZERO"


def test_near_zero_positive_eigenvalue_can_be_certified_when_separated() -> None:
    epsilon = 2.0**-52
    matrix = np.array([[1.0, 1.0], [1.0, 1.0 + epsilon]])

    result = certify_symmetric_inertia(matrix, precision_bits=128)

    assert result["status"] == "CERTIFIED"
    assert result["inertia"] == {"negative": 0, "zero": 0, "positive": 2}


def test_pencil_endpoints_bracket_simple_positive_root() -> None:
    k0 = np.diag([2.0, 3.0])
    kg = np.diag([-1.0, 1.0])
    lower = certify_pencil_inertia(k0, kg, 1.9)
    upper = certify_pencil_inertia(k0, kg, 2.1)
    witnesses = certify_indefinite_witnesses(kg)

    assert lower["status"] == upper["status"] == "CERTIFIED"
    assert lower["inertia"] == {"negative": 0, "zero": 0, "positive": 2}
    assert upper["inertia"] == {"negative": 1, "zero": 0, "positive": 1}
    assert witnesses["status"] == "CERTIFIED_INDEFINITE"


def test_python_flint_inputs_are_exact_binary64_values() -> None:
    from flint import arb, arb_mat

    value = 0.1
    numerator, denominator = value.as_integer_ratio()
    exponent = -(denominator.bit_length() - 1)
    exact_binary64 = arb((numerator, exponent))

    assert arb(value).rad().is_zero()
    assert (arb(value) - exact_binary64).is_zero()
    assert (arb_mat([[value]])[0, 0] - exact_binary64).is_zero()


def test_floating_ldl_crosscheck_is_explicitly_noncertifying() -> None:
    result = floating_ldl_crosscheck(
        np.array([[0.0, 1.0], [1.0, 0.0]]),
        {"negative": 1, "zero": 0, "positive": 1},
    )

    assert result["status"] == "NUMERICAL_CROSSCHECK_MATCH"
    assert result["classification"] == "FLOATING_POINT_SCREEN_ONLY_NO_ERROR_BOUND"
    assert result["relative_infinity_reconstruction_residual"] < 1e-14


def test_certified_root_bracket_refines_only_from_inertia_counts() -> None:
    k0 = np.diag([2.123456, 3.0])
    kg = np.diag([-1.0, 0.0])

    result = refine_certified_root_bracket(k0, kg, 2.1, 2.2, max_steps=4)

    assert result["status"] == "REFINEMENT_LIMIT_REACHED"
    assert result["lower"] < 2.123456 < result["upper"]
    assert len(result["steps"]) == 4
    assert result["lower_inertia"]["inertia"]["negative"] == 0
    assert result["upper_inertia"]["inertia"]["negative"] == 1
    assert result["total_crossing_multiplicity_in_bracket"] == 1
    assert result["unique_simple_root_isolated"] is True


def test_first_root_bracket_requires_certified_positive_definite_k0() -> None:
    k0 = np.diag([1.0, -1.0])
    kg = np.diag([-1.0, 1.0])

    result = refine_certified_root_bracket(k0, kg, 1.0, 2.0)

    assert result["status"] == "K0_NOT_CERTIFIED_POSITIVE_DEFINITE"
    assert result["steps"] == []


def test_multiple_simultaneous_roots_are_not_mistaken_for_a_simple_crossing() -> None:
    k0 = np.diag([2.0, 4.0])
    kg = np.diag([-1.0, -2.0])

    at_root = certify_pencil_inertia(k0, kg, 2.0)
    above = certify_pencil_inertia(k0, kg, 2.1)
    bracket = refine_certified_root_bracket(k0, kg, 1.9, 2.1, max_steps=4)

    assert at_root["status"] == "INDETERMINATE_APPROXIMATE_DIAGONAL_HAS_ZERO"
    assert above["status"] == "CERTIFIED"
    assert above["inertia"] == {"negative": 2, "zero": 0, "positive": 0}
    assert bracket["root_bracket_certified"] is True
    assert bracket["status"] == "MIDPOINT_INERTIA_INDETERMINATE"
    assert bracket["total_crossing_multiplicity_in_bracket"] == 2
    assert bracket["unique_simple_root_isolated"] is False


def test_singular_upper_bound_does_not_certify_a_root_bracket() -> None:
    k0 = np.diag([2.0, 4.0])
    kg = np.diag([-1.0, -2.0])

    result = refine_certified_root_bracket(k0, kg, 1.9, 2.0)

    assert result["status"] == "INITIAL_BRACKET_NOT_CERTIFIED"
    assert result["root_bracket_certified"] is False
    assert result["upper_inertia"]["status"] == "INDETERMINATE_APPROXIMATE_DIAGONAL_HAS_ZERO"


def test_candidate_residual_is_enclosed_and_free_dof_map_is_checked() -> None:
    k0 = np.eye(2)
    kg = np.eye(2)
    mode = np.array([1.0, 2.0])

    result = residual_enclosure(k0, kg, 0.5, mode, np.array([0, 1]))

    assert result["status"] == "RESIDUAL_ENCLOSED"
    assert result["arb_residual_norm_upper_enclosure"]
    assert result["float64_solver_style_residual"] > 0.0
    with pytest.raises(VerifiedInertiaInputError):
        residual_enclosure(k0, kg, 0.5, mode, np.array([0.0, 1.5]))


def test_rejects_nonsymmetric_nonfinite_and_incompatible_matrices() -> None:
    with pytest.raises(VerifiedInertiaInputError, match="exactly symmetric"):
        certify_symmetric_inertia(np.array([[1.0, 1e-15], [0.0, 1.0]]))
    with pytest.raises(VerifiedInertiaInputError, match="finite"):
        certify_symmetric_inertia(np.array([[np.nan]]))
    with pytest.raises(VerifiedInertiaInputError, match="dimensions differ"):
        certify_pencil_inertia(np.eye(2), np.eye(3), 1.0)


def test_invalid_precision_and_missing_interval_backend_are_explicit() -> None:
    with pytest.raises(VerifiedInertiaInputError, match="between 64"):
        certify_symmetric_inertia(np.eye(1), precision_bits=32)

    with patch(
        "research.g08_compare.verified_inertia._flint_precision",
        side_effect=VerifiedInertiaBackendUnavailable("synthetic missing backend"),
    ):
        result = certify_symmetric_inertia(np.eye(2))

    assert result["status"] == "INDETERMINATE_BACKEND_UNAVAILABLE"
