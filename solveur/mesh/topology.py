"""Canonical local face and edge topology shared by mesh and load modules."""

TET4_FACES = ((1, 2, 3), (0, 3, 2), (0, 1, 3), (0, 2, 1))
TET10_FACES = (
    (1, 2, 3, 5, 9, 8),
    (0, 3, 2, 7, 9, 6),
    (0, 1, 3, 4, 8, 7),
    (0, 2, 1, 6, 5, 4),
)
MITC4_EDGES = ((0, 1), (1, 2), (2, 3), (3, 0))
MITC3_EDGES = ((0, 1), (1, 2), (2, 0))
