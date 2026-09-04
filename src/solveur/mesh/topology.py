"""Canonical local face and edge topology shared by mesh and load modules."""

TET4_FACES = ((1, 2, 3), (0, 3, 2), (0, 1, 3), (0, 2, 1))
TET10_FACES = (
    (1, 2, 3, 5, 9, 8),
    (0, 3, 2, 7, 9, 6),
    (0, 1, 3, 4, 8, 7),
    (0, 2, 1, 6, 5, 4),
)
HEX8_FACES = (
    (0, 3, 2, 1),
    (4, 5, 6, 7),
    (0, 1, 5, 4),
    (1, 2, 6, 5),
    (2, 3, 7, 6),
    (3, 0, 4, 7),
)
# Gmsh HEX20 ordering: four corner nodes followed by the four mid-edge nodes
# on each face, using the same oriented corner loops as HEX8.
HEX20_FACES = (
    (0, 3, 2, 1, 9, 13, 11, 8),
    (4, 5, 6, 7, 16, 18, 19, 17),
    (0, 1, 5, 4, 8, 12, 16, 10),
    (1, 2, 6, 5, 11, 14, 18, 12),
    (2, 3, 7, 6, 13, 15, 19, 14),
    (3, 0, 4, 7, 9, 10, 17, 15),
)
# WEDGE6 canonical faces follow the reviewed Prism6 orientation contract.
# The first two faces are the bottom/top triangles; the remaining faces are
# the three quadrilateral sides with outward normals for the canonical prism.
WEDGE6_FACES = (
    (0, 2, 1),
    (3, 4, 5),
    (0, 1, 4, 3),
    (1, 2, 5, 4),
    (2, 0, 3, 5),
)
MITC4_EDGES = ((0, 1), (1, 2), (2, 3), (3, 0))
MITC3_EDGES = ((0, 1), (1, 2), (2, 0))
