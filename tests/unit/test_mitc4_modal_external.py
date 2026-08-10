from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.run_code_aster_modal_vnv import _mesh_text
from solveur.api import solve_model
from solveur.verification.mitc4_modal_external import (
    CodeAsterModalParser,
    Mitc4CodeAsterModalStudy,
    build_modal_correlation_model,
)


ROOT = Path(__file__).resolve().parents[2]


def test_code_aster_modal_parser_requires_ten_finite_modes(tmp_path) -> None:
    path = tmp_path / "modal.json"
    path.write_text(
        json.dumps(
            {
                "modes": [
                    {"frequency_hz": float(index + 1), "uz": [0.0, float(index)]}
                    for index in range(10)
                ]
            }
        ),
        encoding="utf-8",
    )
    points = CodeAsterModalParser().parse(path, node_count=2)
    assert [point.frequency_hz for point in points] == list(np.arange(1.0, 11.0))
    path.write_text(json.dumps({"modes": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="at least 10"):
        CodeAsterModalParser().parse(path, node_count=2)


def test_modal_correlation_model_and_aster_mesh_have_matching_counts() -> None:
    model, quads = build_modal_correlation_model(4)
    text = _mesh_text(4)
    assert model.node_count == 25
    assert quads.shape == (16, 4)
    element_block = text.split("QUAD4\n", 1)[1].split("FINSF", 1)[0]
    assert len(element_block.strip().splitlines()) == 16
    assert "GROUP_NO\nEDGE" in text
    assert sum(1 for condition in model.fixed_dofs if "UZ" in condition.dofs) == 16


def test_same_mesh_modal_comparison_accepts_identical_external_modes(tmp_path) -> None:
    model, _ = build_modal_correlation_model(4)
    result = solve_model(model, enforce_policy=False)
    uz = np.asarray([result.dofs.index(node, "UZ") for node in range(model.node_count)])
    raw = {
        "modes": [
            {
                "frequency_hz": float(result.frequencies_hz[index]),
                "uz": np.asarray(result.modes[uz, index], dtype=float).tolist(),
            }
            for index in range(10)
        ]
    }
    path = tmp_path / "modal.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    study = Mitc4CodeAsterModalStudy(mesh_size=4)
    study.navier_error_limit = 1.0e6
    study.mac_limit = 0.0
    summary = study.run(path)
    assert summary["status"] == "PASS"
    assert max(summary["metrics"]["qf_code_aster_frequency_differences"]) < 1.0e-14
    assert min(summary["metrics"]["qf_code_aster_mac"].values()) > 1.0 - 1.0e-12


def test_controlled_code_aster_modal_reference_passes() -> None:
    raw = (
        ROOT
        / "qualification"
        / "vnv"
        / "external"
        / "code_aster_modal"
        / "reference"
        / "code_aster_modal_raw.json"
    )
    summary = Mitc4CodeAsterModalStudy(mesh_size=32).run(raw)
    assert summary["status"] == "PASS"
    assert max(summary["metrics"]["qf_code_aster_frequency_differences"]) < 0.03
    assert min(summary["metrics"]["qf_code_aster_mac"].values()) > 0.999998
