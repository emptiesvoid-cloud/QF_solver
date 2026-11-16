"""Small controls for the deterministic J11 HEX8 archive key normalization."""

from __future__ import annotations

import numpy as np
import pytest

from research.j11_hex8.postprocess_archive import ALPHA_ZERO_REQUIRED_KEYS, normalize_alpha_zero_keys


def _archive_arrays() -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {"coordinates_alpha_0_m": np.asarray([[0.0, 0.0, 0.0]])}
    for prefix, suffix in (
        ("coordinates", "m"),
        ("global_stiffness", "n_per_m"),
        ("qf_sri_kernel_numpy_direct_displacement", "m"),
        ("scaled_displacement", "m"),
        ("scipy_displacement", "m"),
        ("qf_sri_numpy_direct_reactions", "n"),
        ("qf_sri_numpy_direct_free_residual", "n"),
        ("mpmath_displacement", "m"),
    ):
        arrays[f"{prefix}_alpha_134_{suffix}"] = np.asarray([134.0])
    arrays["coordinates_alpha_134_m"] = arrays["coordinates_alpha_0_m"].copy()
    del arrays["coordinates_alpha_134_m"]
    for alpha in (1, 2, 3):
        for prefix, suffix in (
            ("coordinates", "m"),
            ("global_stiffness", "n_per_m"),
            ("qf_sri_kernel_numpy_direct_displacement", "m"),
            ("scaled_displacement", "m"),
            ("scipy_displacement", "m"),
            ("qf_sri_numpy_direct_reactions", "n"),
            ("qf_sri_numpy_direct_free_residual", "n"),
        ):
            arrays[f"{prefix}_alpha_{alpha}_{suffix}"] = np.asarray([float(alpha)])
    return arrays


def test_alpha_134_keys_map_to_zero_and_identical_coordinate_collision_is_checked() -> None:
    arrays = _archive_arrays()
    arrays["coordinates_alpha_134_m"] = arrays["coordinates_alpha_0_m"].copy()
    normalized, metadata = normalize_alpha_zero_keys(arrays)

    assert set(ALPHA_ZERO_REQUIRED_KEYS) <= set(normalized)
    assert not any("_alpha_134_" in key for key in normalized)
    assert metadata["identical_collision_targets_preserved"] == ["coordinates_alpha_0_m"]
    assert np.array_equal(normalized["global_stiffness_alpha_0_n_per_m"], np.asarray([134.0]))


def test_alpha_zero_alias_collision_with_different_values_is_rejected() -> None:
    arrays = _archive_arrays()
    arrays["coordinates_alpha_134_m"] = np.asarray([[1.0, 0.0, 0.0]])

    with pytest.raises(ValueError, match="Alias collision has unequal values"):
        normalize_alpha_zero_keys(arrays)
