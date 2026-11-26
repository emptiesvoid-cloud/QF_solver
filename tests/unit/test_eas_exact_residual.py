import numpy as np
import pytest

from solveur.experimental.eas_residual.exact_residual import exact_check


def check(data, indices, ptr, b, x, threshold=0.5, **kwargs):
    return exact_check(np.asarray(data, dtype=np.float64), np.asarray(indices, dtype=np.int64),
                       np.asarray(ptr, dtype=np.int64), (len(b), len(b)),
                       np.asarray(b, dtype=np.float64), np.asarray(x, dtype=np.float64), threshold, **kwargs)


def test_boundary_and_adjacent_binary64_values():
    assert check([1], [0], [0, 1], [1], [0.5])["decision"] == "PASS"
    assert check([1], [0], [0, 1], [1], [np.nextafter(0.5, 0.0)])["decision"] == "FAIL"
    assert check([1], [0], [0, 1], [1], [np.nextafter(0.5, 1.0)])["decision"] == "PASS"


def test_extreme_cancellation_and_scales():
    assert check([1e300, -1e300, 1e-300], [0, 1, 1], [0, 2, 3], [0, 1e-300], [1, 1])["decision"] == "PASS"


@pytest.mark.parametrize("data,idx,ptr,b,x", [
    ([1, 2], [0, 0], [0, 2], [1], [1]),
    ([1], [1], [0, 1], [1], [1]),
    ([float('nan')], [0], [0, 1], [1], [1]),
    ([1], [0], [0, 1], [0], [0]),
    ([1], [0], [1, 1], [1], [1]),
])
def test_invalid_data_refused(data, idx, ptr, b, x):
    with pytest.raises(ValueError):
        check(data, idx, ptr, b, x)


def test_budget_and_incompatible_dtype_refused():
    with pytest.raises(ValueError, match="budget"):
        check([1], [0], [0, 1], [1], [1], max_nnz=0)
    with pytest.raises(ValueError, match="binary64"):
        exact_check(np.array([1], dtype=np.float32), np.array([0]), np.array([0, 1]), (1, 1), np.ones(1), np.ones(1), 0.5)
