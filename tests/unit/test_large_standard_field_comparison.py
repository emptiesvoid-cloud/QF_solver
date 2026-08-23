from __future__ import annotations

import json

from scripts.compare_large_standard_fields import run_campaign


def test_large_standard_field_comparison_preserves_mechanics(tmp_path) -> None:
    output = tmp_path / "field_comparison.json"
    report = run_campaign([100], output, decomposition="centered", chunk_size=64)

    assert report["acceptance"]["all_cases_pass"] is True
    assert report["sizes"][0]["displacement"]["relative_l2"] < 1.0e-7
    assert report["sizes"][0]["strain"]["relative_l2"] < 1.0e-7
    assert report["sizes"][0]["stress"]["relative_l2"] < 1.0e-7
    assert json.loads(output.read_text(encoding="utf-8"))["campaign"].startswith("qf-solver-tet4")
