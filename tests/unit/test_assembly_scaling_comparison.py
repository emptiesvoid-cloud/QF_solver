from __future__ import annotations

import json

import pytest

from scripts.compare_assembly_scaling import compare_reports


def _report(seconds: float, nnz: int = 10) -> dict[str, object]:
    return {
        "sizes": [
            {
                "dofs": 100,
                "elements": 8,
                "nnz": nnz,
                "assembly_seconds": seconds,
                "assembly_diagnostics": {
                    "assembly_phase_seconds": {"chunk_build": seconds, "chunk_fusion": 0.1}
                },
            }
        ]
    }


def test_comparison_checks_invariants_and_records_candidate_method(tmp_path) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    baseline.write_text(json.dumps(_report(10.0)), encoding="utf-8")
    payload = _report(9.8)
    payload["sizes"][0]["assembly_diagnostics"]["sparse_conversion_method"] = "csr_constructor"
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    result = compare_reports(baseline, candidate, tmp_path / "comparison.json")

    assert result["numerical_identity"] == "PASS"
    assert result["performance_interpretation"] == "no_material_change"
    assert result["sizes"][0]["candidate_conversion_method"] == "csr_constructor"
    assert (tmp_path / "comparison.json").is_file()


def test_comparison_rejects_changed_nnz(tmp_path) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    baseline.write_text(json.dumps(_report(1.0, nnz=10)), encoding="utf-8")
    candidate.write_text(json.dumps(_report(1.0, nnz=11)), encoding="utf-8")

    with pytest.raises(ValueError, match="invariant"):
        compare_reports(baseline, candidate)


def test_comparison_rejects_different_sizes(tmp_path) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    baseline.write_text(json.dumps(_report(1.0)), encoding="utf-8")
    changed = _report(1.0)
    changed["sizes"][0]["dofs"] = 200
    candidate.write_text(json.dumps(changed), encoding="utf-8")

    with pytest.raises(ValueError, match="same DDL"):
        compare_reports(baseline, candidate)
