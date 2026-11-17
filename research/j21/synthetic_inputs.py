"""Create small deterministic exact-system archives for supervisor cost tests."""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import ZIP_STORED, ZipFile, ZipInfo

import numpy as np


def _dense_system(structure: str, dimension: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    matrix = np.zeros((dimension, dimension), dtype=np.complex128)
    if structure == "diagonal":
        np.fill_diagonal(matrix, 2.0 + 0.5j)
    elif structure == "banded":
        np.fill_diagonal(matrix, 2.0)
        if dimension > 1:
            matrix[np.arange(dimension - 1), np.arange(1, dimension)] = -0.25
            matrix[np.arange(1, dimension), np.arange(dimension - 1)] = -0.25
    elif structure == "dense":
        matrix.fill(1.0 / 16.0)
        np.fill_diagonal(matrix, 2.0 + 1.0 / 16.0)
    else:
        raise ValueError(f"unsupported synthetic dense structure: {structure}")
    solution = np.ones(dimension, dtype=np.complex128)
    rhs = matrix @ solution
    return matrix, rhs, solution


def _duplicate_csr(dimension: int) -> dict[str, np.ndarray]:
    data: list[complex] = []
    indices: list[int] = []
    indptr = [0]
    rhs = np.empty(dimension, dtype=np.complex128)
    for row in range(dimension):
        data.extend((2.0 + 0.0j, 0.5 + 0.25j, -0.5 - 0.25j))
        indices.extend((row, row, row))
        value = 2.0 + 0.0j
        if row + 1 < dimension:
            data.append(0.25 + 0.0j)
            indices.append(row + 1)
            value += 0.25
        rhs[row] = value
        indptr.append(len(data))
    solution = np.ones(dimension, dtype=np.complex128)
    return {
        "matrix_storage": np.asarray("csr"),
        "csr_data_real": np.asarray(data, dtype=np.complex128).real,
        "csr_data_imag": np.asarray(data, dtype=np.complex128).imag,
        "csr_indices": np.asarray(indices, dtype=np.int32),
        "csr_indptr": np.asarray(indptr, dtype=np.int32),
        "matrix_shape": np.asarray([dimension, dimension], dtype=np.int64),
        "rhs_real": rhs.real,
        "rhs_imag": rhs.imag,
        "x_unscaled_real": solution.real,
        "x_unscaled_imag": solution.imag,
    }


def build_archive_payload(structure: str, dimension: int) -> dict[str, Any]:
    if isinstance(dimension, bool) or not isinstance(dimension, int) or dimension <= 0 or dimension > 128:
        raise ValueError("synthetic dimensions must be between 1 and 128")
    if structure == "duplicate_csr":
        return _duplicate_csr(dimension)
    matrix, rhs, solution = _dense_system(structure, dimension)
    return {
        "matrix_storage": np.asarray("dense"),
        "impedance_real": matrix.real,
        "impedance_imag": matrix.imag,
        "rhs_real": rhs.real,
        "rhs_imag": rhs.imag,
        "x_unscaled_real": solution.real,
        "x_unscaled_imag": solution.imag,
    }


def write_archive(path: Path, structure: str, dimension: int) -> Path:
    path = Path(path)
    if path.exists():
        raise FileExistsError("synthetic input already exists; refusing to overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, mode="x", compression=ZIP_STORED) as archive:
        for name, array in build_archive_payload(structure, dimension).items():
            npy_buffer = BytesIO()
            np.lib.format.write_array(npy_buffer, np.asarray(array), allow_pickle=False)
            member = ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            member.compress_type = ZIP_STORED
            member.external_attr = 0o600 << 16
            archive.writestr(member, npy_buffer.getvalue())
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", required=True, type=Path)
    args = parser.parse_args(argv)
    output = args.output_directory
    output.mkdir(parents=True, exist_ok=True)
    specifications = (
        ("diagonal_16", "diagonal", 16),
        ("banded_32", "banded", 32),
        ("banded_64", "banded", 64),
        ("dense_24", "dense", 24),
        ("duplicate_csr_32", "duplicate_csr", 32),
    )
    for filename, structure, dimension in specifications:
        path = output / f"{filename}.npz"
        if path.exists():
            expected = build_archive_payload(structure, dimension)
            with np.load(path, allow_pickle=False) as archive:
                if set(archive.files) != set(expected) or any(
                    not np.array_equal(archive[name], value) for name, value in expected.items()
                ):
                    raise FileExistsError(f"existing synthetic archive differs from its specification: {path}")
            continue
        write_archive(path, structure, dimension)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
