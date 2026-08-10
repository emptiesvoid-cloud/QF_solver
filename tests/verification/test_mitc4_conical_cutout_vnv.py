"""Regression checks for the complex curved static MITC4 geometry."""

from __future__ import annotations

import json

import numpy as np

from solveur.api import check_mesh
from solveur.verification.mitc4_conical_cutout import Mitc4ConicalCutoutStudy, build_conical_cutout_model


def test_conical_cutout_facets_are_planar_and_mesh_is_accepted() -> None:
    model, probe = build_conical_cutout_model(8, 24)
    assert check_mesh(model).status == "PASS"
    assert 0 < probe < model.node_count
    for element in model.elements:
        points = model.nodes[np.asarray(element.nodes, dtype=int)]
        normal = np.cross(points[1] - points[0], points[2] - points[0])
        assert abs(float(np.dot(normal, points[3] - points[0]))) < 1.0e-12


def test_conical_cutout_campaign_publishes_convergence_evidence(tmp_path) -> None:
    summary = Mitc4ConicalCutoutStudy(tmp_path).run()
    assert summary["status"] == "PASS_TECHNICAL_VERIFICATION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert len(summary["convergence"]) == 3
    for name in (
        "summary.json", "report.md", "fine_model.json", "fine_results.json", "fine_deformation.vtu",
        "conical_cutout_geometry_deformation.png", "conical_cutout_convergence.png", "vnv_manifest.json",
    ):
        assert (tmp_path / name).is_file()
        assert (tmp_path / name).stat().st_size > 0
    manifest = json.loads((tmp_path / "vnv_manifest.json").read_text(encoding="utf-8"))
    assert manifest["study_id"] == Mitc4ConicalCutoutStudy.study_id
