from __future__ import annotations

import numpy as np

from research.j17.exact_residual import evaluate_exact_residual


class _IntegerWithBrokenFloatConversion(int):
    def __float__(self) -> float:
        raise TypeError("injected scalar conversion failure")


def test_exact_residual_returns_inconclusive_when_numeric_conversion_raises_type_error() -> None:
    matrix = np.array([[1.0]])
    vector = np.array([1.0])
    for parameter in ("tolerance", "max_elapsed_seconds"):
        result = evaluate_exact_residual(
            matrix,
            vector,
            vector,
            **{parameter: _IntegerWithBrokenFloatConversion(1)},
        )
        assert result.status == "INCONCLUSIVE"
        assert "scalar" in result.reason
