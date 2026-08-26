"""Unit contracts for the bounded CalculiX buckling correlation."""

from __future__ import annotations

import json

import pytest

from solveur.verification.calculix_buckling_025 import (
    CALCULIX_TYPES,
    run_campaign,
    write_buckling_input,
)
from solveur.verification.robustness_nonlinear_solids import _buckling_mesh_model


def test_calculix_decks_cover_all_solid_families(tmp_path) -> None:
    expected = {"TET4": "C3D4", "TET10": "C3D10", "HEX8": "C3D8", "HEX20": "C3D20"}
    for family, keyword in expected.items():
        model = _buckling_mesh_model(family, 1)
        path = write_buckling_input(tmp_path / family / "buckling.inp", model, family)
        text = path.read_text(encoding="ascii")
        assert CALCULIX_TYPES[family] == keyword
        assert f"*ELEMENT,TYPE={keyword},ELSET=EALL" in text
        assert "*BUCKLE" in text
        expected_vectors = "11" if family in {"TET4", "HEX8"} else "30"
        assert f"1,0.001,{expected_vectors},1000" in text
        assert "*BOUNDARY" in text
        assert "FIXED,1,3,0." in text
        assert "*NSET,NSET=FIXED" in text
        assert "*CLOAD" in text


def test_hex20_deck_maps_qf_edges_to_calculix_order(tmp_path) -> None:
    model = _buckling_mesh_model("HEX20", 1)
    path = write_buckling_input(tmp_path / "hex20.inp", model, "HEX20")
    lines = path.read_text(encoding="ascii").splitlines()
    element_start = lines.index("*ELEMENT,TYPE=C3D20,ELSET=EALL") + 1
    element_line = lines[element_start] + lines[element_start + 1]
    expected = [
        str(index + 1)
        for index in (0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 13, 9, 16, 18, 19, 17, 10, 12, 14, 15)
    ]
    assert element_line.split(",")[1:] == expected


def test_planned_campaign_writes_traceable_rows(tmp_path) -> None:
    summary = run_campaign(tmp_path, element_types=("TET4", "HEX20"), cells=1, execute=False)
    assert summary["status"] == "PLANNED"
    assert [row["status"] for row in summary["rows"]] == ["PLANNED", "PLANNED"]
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "buckling_external_comparison.png").exists()
    persisted = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert persisted["scope"]["same_qf_model"] is True
    assert persisted["release_claim"] is False
    assert len(persisted["provenance"]["sha"]) == 40
    assert persisted["provenance"]["worktree_dirty"] in {True, False, None}
    assert all(len(row["deck_sha256"]) == 64 for row in persisted["rows"])
    assert persisted["rows"][0]["free_equation_count"] == 12
    assert persisted["rows"][0]["lanczos_vectors"] == 11


def test_provenance_reads_git_head_when_git_subprocess_is_unavailable(monkeypatch) -> None:
    from solveur.verification import calculix_buckling_025 as module

    def unavailable(*args, **kwargs):
        raise FileNotFoundError("git unavailable")

    monkeypatch.setattr(module.subprocess, "run", unavailable)
    provenance = module._git_provenance()

    assert len(provenance["sha"]) == 40
    assert provenance["worktree_dirty"] is None


def test_buckling_deck_rejects_invalid_mode_count(tmp_path) -> None:
    model = _buckling_mesh_model("HEX8", 1)
    with pytest.raises(ValueError, match="modes"):
        write_buckling_input(tmp_path / "buckling.inp", model, "HEX8", modes=0)


def test_campaign_records_external_execution_failure_without_false_pass(monkeypatch, tmp_path) -> None:
    from solveur.verification import calculix_buckling_025 as module

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic CalculiX failure")

    monkeypatch.setattr(module, "_run_calculix", fail)
    summary = run_campaign(tmp_path, element_types=("HEX20",), cells=1, modes=1)
    assert summary["status"] == "BLOCKED_EXTERNAL_TOOL"
    assert summary["rows"][0]["status"] == "BLOCKED_EXTERNAL_TOOL"
    assert "synthetic CalculiX failure" in summary["rows"][0]["error"]
    assert "synthetic CalculiX failure" in (tmp_path / "report.md").read_text(encoding="utf-8")
