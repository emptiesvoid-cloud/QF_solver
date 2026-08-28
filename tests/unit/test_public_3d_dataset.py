from pathlib import Path

from scripts.public_3d_dataset import (
    LICENSE_NAME,
    _is_closed_surface,
    _parse_obj,
    select_models,
)


def test_parse_obj_triangulates_faces_and_supports_negative_indices(tmp_path: Path) -> None:
    source = tmp_path / "mesh.obj"
    source.write_text(
        "v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf -4 -3 -2 -1\n",
        encoding="utf-8",
    )

    vertices, faces = _parse_obj(source)

    assert len(vertices) == 4
    assert faces == [(0, 1, 2), (0, 2, 3)]


def test_closed_surface_detection_requires_two_incident_faces_per_edge() -> None:
    tetrahedron = [(0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0)]
    open_surface = tetrahedron[:-1]

    assert _is_closed_surface(tetrahedron)
    assert not _is_closed_surface(open_surface)


def test_selection_rejects_unlicensed_and_excluded_models() -> None:
    models = [
        {"name": "chair", "license_name": LICENSE_NAME, "categories": ["Furniture"]},
        {"name": "engine", "license_name": LICENSE_NAME, "categories": ["Mechanical"]},
        {"name": "unknown", "license_name": "All rights reserved", "categories": ["Other"]},
    ]

    selected, rejected = select_models(models, limit=3)

    assert [model["name"] for model in selected] == ["chair"]
    assert {model["name"] for model in rejected} == {"engine", "unknown"}


def test_selection_round_robins_categories_for_diversity() -> None:
    models = [
        {"name": "a1", "license_name": LICENSE_NAME, "categories": ["A"]},
        {"name": "a2", "license_name": LICENSE_NAME, "categories": ["A"]},
        {"name": "b1", "license_name": LICENSE_NAME, "categories": ["B"]},
    ]

    selected, rejected = select_models(models, limit=3)

    assert [model["name"] for model in selected] == ["a1", "b1", "a2"]
    assert rejected == []
