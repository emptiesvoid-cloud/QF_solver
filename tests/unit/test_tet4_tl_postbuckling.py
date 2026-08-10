"""Tests for sparse arc length and postbuckling evidence."""

from __future__ import annotations

import json

import numpy as np
import pytest

from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.materials.solid import SolidMaterial
from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh
from solveur.verification.tet4_total_lagrangian_postbuckling import load_mesh_critical_load
from solveur.verification.total_lagrangian_structural import trace_sparse_arc_length


def test_load_mesh_critical_load_reads_controlled_level(tmp_path):
    path = tmp_path / "summary.json"
    path.write_text(
        json.dumps(
            {
                "status": "PASS_BUCKLING_RESEARCH",
                "levels": [{"elements": 192, "critical_load": 12.5}],
            }
        ),
        encoding="utf-8",
    )
    assert load_mesh_critical_load(path, 192) == pytest.approx(12.5)


def test_load_mesh_critical_load_rejects_unaccepted_summary(tmp_path):
    path = tmp_path / "summary.json"
    path.write_text(json.dumps({"status": "FAIL", "levels": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="PASS_BUCKLING_RESEARCH"):
        load_mesh_critical_load(path, 192)


def test_sparse_arc_length_tracks_finite_imperfect_path():
    length = 2.0
    nodes, elements = _structured_tet4_mesh(4, 1, 1, length, 0.5, 0.5)
    nodes[:, 2] += 0.005 * (1.0 - np.cos(0.5 * np.pi * nodes[:, 0] / length))
    assembly = TotalLagrangianTet4Assembly(nodes, elements, SolidMaterial(E=1.0e6, nu=0.3))
    left = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    tip = np.flatnonzero(np.isclose(nodes[:, 0], length))
    fixed = (3 * left[:, None] + np.arange(3)).reshape(-1)
    load = np.zeros(assembly.ndof)
    load[3 * tip] = -100.0 / tip.size

    displacement, history = trace_sparse_arc_length(
        assembly, load, fixed, tip, steps=12, initial_load_increment=0.02
    )

    assert len(history) == 12
    assert np.all(np.isfinite(displacement))
    assert max(point.relative_residual for point in history) < 1.0e-7
    assert min(point.minimum_det_f for point in history) > 0.99
    assert history[-1].load_factor > history[0].load_factor
