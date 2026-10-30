"""Synthetic checks for prospective WP12-V2 H1 diagnostic helpers.

These tests use only fake matrices/operators and do not import ``solveur``.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest


def _load_h1_test_module() -> Any:
    source = Path(__file__).resolve().parents[1] / "unit" / "test_wp12_v2_tet4_operator_audit.py"
    spec = importlib.util.spec_from_file_location("wp12_v2_r3_h1_test_helpers", source)
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load the prospective H1 test helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_contribution_extraction_handles_scalar_lists_and_batch_arrays() -> None:
    module = _load_h1_test_module()
    matrices = np.asarray(
        [
            [[1.125, 2.5], [3.75, 4.25]],
            [[5.125, 6.5], [7.75, 8.25]],
            [[9.125, 10.5], [11.75, 12.25]],
        ],
        dtype=np.float64,
    )
    scalar_local = [matrix.copy() for matrix in matrices]
    dof_maps = [[14, 22], [22, 14], [14, 22]]

    expected_upper = [
        {"element": 0, "binary64_hex": float(2.5).hex()},
        {"element": 1, "binary64_hex": float(7.75).hex()},
        {"element": 2, "binary64_hex": float(10.5).hex()},
    ]
    expected_lower = [
        {"element": 0, "binary64_hex": float(3.75).hex()},
        {"element": 1, "binary64_hex": float(6.5).hex()},
        {"element": 2, "binary64_hex": float(11.75).hex()},
    ]

    assert module._pair_contribution_records(scalar_local, dof_maps, 14, 22) == expected_upper
    assert module._pair_contribution_records(scalar_local, dof_maps, 22, 14) == expected_lower
    assert module._pair_contribution_records(matrices, dof_maps, 14, 22) == expected_upper
    assert module._pair_contribution_records(matrices, dof_maps, 22, 14) == expected_lower


def test_matrix_free_column_helper_visits_every_canonical_vector_once() -> None:
    module = _load_h1_test_module()
    size = 24
    reference = np.arange(1, size * size + 1, dtype=np.float64).reshape(size, size)

    class FakeOperator:
        def __init__(self) -> None:
            self.columns: list[int] = []

        def __matmul__(self, vector: Any) -> np.ndarray:
            nonzero = np.flatnonzero(vector)
            assert nonzero.size == 1
            column = int(nonzero[0])
            assert vector[column] == 1.0
            self.columns.append(column)
            return reference @ vector

    operator = FakeOperator()
    actual = module._canonical_operator_columns(operator, size, np)

    assert operator.columns == list(range(size))
    assert np.array_equal(actual, reference)


def test_result_emission_is_json_safe_and_nonfinite_values_are_detected(capsys: pytest.CaptureFixture[str]) -> None:
    module = _load_h1_test_module()
    payload = {
        "schema": "synthetic-h1-result-v1",
        "metrics": {"column_count": 24, "operator_error": 0.0},
        "status": "INCONCLUSIVE",
    }

    module._emit(payload)
    emitted = capsys.readouterr().out.strip()
    assert emitted.startswith(module.RESULT_MARKER)
    assert json.loads(emitted[len(module.RESULT_MARKER) :]) == payload
    assert module._all_finite(np.asarray([0.0, 1.0]))
    assert not module._all_finite(np.asarray([0.0, np.nan]))

    with pytest.raises(ValueError, match="Out of range float values"):
        module._emit({"metric": float("nan")})
