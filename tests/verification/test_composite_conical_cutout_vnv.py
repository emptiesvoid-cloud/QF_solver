"""Regression coverage for the complex curved laminate campaign."""

from __future__ import annotations

import json

import numpy as np

from solveur.api import check_mesh
from solveur.verification.composite_conical_cutout import CompositeConicalCutoutStudy, build_composite_conical_cutout_model


def test_composite_conical_cutout_has_projected_laminate_and_valid_mesh() -> None:
    model, _ = build_composite_conical_cutout_model(4, 16)
    assert check_mesh(model).status == "PASS"
    assert model.materials["laminate"]["reference_direction"] == [1.0, 0.0, 0.0]
    assert all(element.type == "MITC4" for element in model.elements)
    assert np.isclose(sum(float(load.value) for load in model.distributed_loads), 2500.0 * len(model.elements))


def test_composite_conical_cutout_campaign_publishes_evidence(tmp_path) -> None:
    summary = CompositeConicalCutoutStudy(tmp_path).run()
    assert summary["status"] == "PASS_TECHNICAL_VERIFICATION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert len(summary["convergence"]) == 3
    for name in ("summary.json", "report.md", "fine_model.json", "fine_results.json", "fine_deformation.vtu", "composite_conical_cutout_geometry.png", "composite_conical_cutout_convergence.png", "vnv_manifest.json"):
        assert (tmp_path / name).is_file()
    assert json.loads((tmp_path / "vnv_manifest.json").read_text(encoding="utf-8"))["study_id"] == CompositeConicalCutoutStudy.study_id
