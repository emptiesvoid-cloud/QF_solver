"""Focused contracts for the distance-controlled composite ply-stress path."""

import numpy as np

from solveur.verification.calculix_composite_conical_ply_stress import (
    _path_elements,
    _relative_vectors,
)
from solveur.verification.calculix_composite_conical_cutout import build_loaded_qf_model


def test_controlled_path_excludes_the_free_and_clamped_boundaries() -> None:
    model, _ = build_loaded_qf_model(8, 24)
    selected = _path_elements(model, 0.5, 0.12)
    radii = [float(np.hypot(*np.mean(model.nodes[list(model.elements[index].nodes), :2], axis=0))) for index in selected]
    assert len(selected) == 48
    assert min(radii) > 0.20
    assert max(radii) < 0.75


def test_relative_vector_metric_is_explicit() -> None:
    assert _relative_vectors([1.0, 2.0], [1.0, 2.0]) == 0.0
