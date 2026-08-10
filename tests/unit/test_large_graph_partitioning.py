from __future__ import annotations

import numpy as np
import pytest

from solveur.large.partitioning import _face_groups, element_row_owner, face_owner, tet4_faces


def test_tet4_faces_are_sorted_and_shared_face_is_identical() -> None:
    connectivity = np.asarray([[0, 1, 2, 3], [0, 2, 1, 4]], dtype=np.int64)

    faces = tet4_faces(connectivity)

    assert faces.shape == (8, 3)
    assert np.all(faces[:, 1:] >= faces[:, :-1])
    shared = np.count_nonzero(np.all(faces == np.asarray([0, 1, 2]), axis=1))
    assert shared == 2


def test_face_owner_is_deterministic_and_bounded() -> None:
    faces = np.asarray([[0, 1, 2], [10, 20, 30], [0, 1, 2]], dtype=np.int64)

    owners = face_owner(faces, 4)

    assert np.array_equal(owners[[0, 2]], [owners[0], owners[0]])
    assert np.all((owners >= 0) & (owners < 4))
    with pytest.raises(ValueError, match="positive"):
        face_owner(faces, 0)


def test_element_row_owner_matches_partition_ranges_when_count_is_not_divisible() -> None:
    element_ids = np.arange(17, dtype=np.int64)

    owners = element_row_owner(element_ids, global_element_count=17, size=4)

    assert np.array_equal(owners, np.asarray([0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 3]))
    with pytest.raises(ValueError, match="positive"):
        element_row_owner(element_ids, global_element_count=17, size=0)


def test_face_groups_collect_equal_signatures() -> None:
    records = np.asarray(
        [
            [3, 4, 5, 8],
            [0, 1, 2, 3],
            [3, 4, 5, 9],
            [6, 7, 8, 10],
        ],
        dtype=np.int64,
    )

    groups = _face_groups(records)

    assert [stop - start for start, stop in groups] == [1, 2, 1]
    assert np.array_equal(records[1:3, :3], np.asarray([[3, 4, 5], [3, 4, 5]]))


def test_tet4_faces_rejects_invalid_connectivity() -> None:
    with pytest.raises(ValueError, match="shape"):
        tet4_faces(np.zeros((2, 3), dtype=np.int64))
