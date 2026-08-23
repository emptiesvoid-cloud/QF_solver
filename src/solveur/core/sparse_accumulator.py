"""Memory-aware accumulation of sparse matrix chunks."""

from __future__ import annotations

from scipy.sparse import csr_matrix


class SparseCsrAccumulator:
    """Merge CSR chunks pairwise instead of reallocating a global CSR matrix.

    Pairwise merging keeps only logarithmically many partial matrices alive.
    It is not a substitute for a preallocated solver-native matrix, but it is
    a safer SciPy baseline for chunked assembly than repeated global addition.
    """

    def __init__(self, shape: tuple[int, int]) -> None:
        self.shape = shape
        self.levels: list[csr_matrix | None] = []
        self.chunk_count = 0

    def add(self, matrix: csr_matrix) -> None:
        """Add one CSR chunk and combine occupied levels pairwise."""
        carry = matrix.tocsr()
        level = 0
        while level < len(self.levels) and self.levels[level] is not None:
            carry = (self.levels[level] + carry).tocsr()
            self.levels[level] = None
            level += 1
        if level == len(self.levels):
            self.levels.append(carry)
        else:
            self.levels[level] = carry
        self.chunk_count += 1

    def finalize(self) -> csr_matrix:
        """Return one CSR matrix, preserving the accumulator shape."""
        result = csr_matrix(self.shape, dtype=float)
        for matrix in self.levels:
            if matrix is not None:
                result = (result + matrix).tocsr()
        result.sum_duplicates()
        result.eliminate_zeros()
        return result

    @property
    def occupied_levels(self) -> int:
        """Return the number of live partial matrices before finalization."""
        return sum(matrix is not None for matrix in self.levels)
