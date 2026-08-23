import numpy as np
from scipy.sparse import csr_matrix

from solveur.core.sparse_accumulator import SparseCsrAccumulator


def test_sparse_accumulator_matches_direct_sparse_sum() -> None:
    first = csr_matrix(np.array([[1.0, 0.0], [0.0, 2.0]]))
    second = csr_matrix(np.array([[0.0, 3.0], [4.0, 0.0]]))
    third = csr_matrix(np.array([[5.0, 0.0], [0.0, 6.0]]))
    accumulator = SparseCsrAccumulator((2, 2))
    for chunk in (first, second, third):
        accumulator.add(chunk)

    expected = first + second + third
    assert accumulator.chunk_count == 3
    assert accumulator.occupied_levels >= 1
    np.testing.assert_allclose(accumulator.finalize().toarray(), expected.toarray())
