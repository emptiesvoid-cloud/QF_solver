from __future__ import annotations

import json
from pathlib import Path

from scripts.docs_content_closure import (
    finite_plot_data,
    load_and_validate_coverage,
    publish_technical_content_closure,
)


ROOT = Path(__file__).resolve().parents[2]


def test_every_implemented_element_analysis_pair_has_an_explicit_oracle_decision() -> None:
    payload = load_and_validate_coverage(ROOT)
    matrix = json.loads((ROOT / "qualification/element_analysis_matrix.json").read_text(encoding="utf-8"))
    expected = sum(
        declaration["status"] != "unsupported"
        for family in matrix["families"].values()
        for analysis, declaration in family.items()
        if analysis != "evidence"
    )
    assert len(payload["element_analysis_pairs"]) == expected


def test_documented_gaps_are_never_relabelled_as_mechanical_passes() -> None:
    payload = load_and_validate_coverage(ROOT)
    assert payload["policy"]["gap_documented_is_mechanical_pass"] is False
    gaps = [row for row in payload["element_analysis_pairs"] if row["oracle"]["kind"] == "gap_documented"]
    assert all(row["oracle"]["status"] == "gap_documented" for row in gaps)


def test_content_closure_publishes_tables_hashes_and_external_views(tmp_path: Path) -> None:
    generated = tmp_path / "generated"
    assets = tmp_path / "assets"
    report = publish_technical_content_closure(ROOT, generated, assets)
    assert report["status"] == "PASS_DOCUMENTATION"
    assert report["mechanical_pass_inferred_from_gaps"] is False
    assert report["pair_count"] >= 30
    assert len(report["artifacts"]) >= 10
    assert finite_plot_data(assets / "content_closure/beam2_code_aster_dynamic.png")
    assert finite_plot_data(assets / "content_closure/discrete_code_aster_dynamic.png")
    markdown = (generated / "technical_content_coverage.md").read_text(encoding="utf-8")
    assert "Couples element-analyse et oracles" in markdown
    assert "Ecarts V&V maintenus ouverts" in markdown


def test_controlled_documentation_registry_references_the_recorded_owner_review() -> None:
    registry = json.loads(
        (ROOT / "qualification/documentation_review_pages.json").read_text(encoding="utf-8")
    )
    review = json.loads(
        (ROOT / "qualification/reviews/owner_review_pages_2026-08-02.json").read_text(
            encoding="utf-8"
        )
    )

    assert registry["policy"]["latest_review_record"].endswith(
        "owner_review_pages_2026-08-02.json"
    )
    assert registry["policy"]["latest_review_doc_id"] == review["doc_id"]
    assert review["decision"] == "accepted"
    assert review["qualification_effect"] == "none"
