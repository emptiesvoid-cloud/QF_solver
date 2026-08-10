"""Pure-data checks for the Docker PETSc/SciPy comparison campaign."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.verification.large_petsc_scipy import _read_mpi_binary_displacement, _relative_difference


def test_relative_difference_is_zero_for_identical_displacements() -> None:
    values = np.arange(12, dtype=float).reshape((4, 3))
    assert _relative_difference(values, values.copy()) == pytest.approx(0.0)


def test_mpi_binary_reader_preserves_node_component_order(tmp_path) -> None:
    expected = np.arange(12, dtype=float).reshape((4, 3))
    path = tmp_path / "displacements.bin"
    expected.tofile(path)

    assert np.array_equal(_read_mpi_binary_displacement(path, 4), expected)


def test_mpi_binary_reader_rejects_truncated_output(tmp_path) -> None:
    path = tmp_path / "displacements.bin"
    np.arange(11, dtype=float).tofile(path)

    with pytest.raises(ValueError, match="contains 11 values"):
        _read_mpi_binary_displacement(path, 4)
