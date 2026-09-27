import json
from pathlib import Path

import pytest

from scripts import review_vocabulary as vocabulary
from scripts.audit_public_documents import _review_vocabulary_offenders


@pytest.mark.parametrize("label", ["analyseur", "analyzer_report", "Owner review", "owner_analysis"])
def test_controlled_terms_are_allowed(tmp_path: Path, label: str) -> None:
    (tmp_path / "report.md").write_text(label, encoding="utf-8")
    assert vocabulary.review_vocabulary_audit(tmp_path, ["report.md"])["status"] == "PASS"


@pytest.mark.parametrize("term", vocabulary.FORBIDDEN_TERMS)
@pytest.mark.parametrize("relative", ["qualification/new.json", "qualification/evidence/old.md", "docs/generated/report.md"])
def test_generic_terms_fail_even_in_archives(tmp_path: Path, term: str, relative: str) -> None:
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text(term.upper(), encoding="utf-8")
    report = vocabulary.review_vocabulary_audit(tmp_path, [relative])
    assert report["status"] == "FAIL"
    assert report["offenders"] == [relative]
    assert _review_vocabulary_offenders(tmp_path, [relative]) == [relative]


def test_known_historical_path_has_no_lexical_exemption(tmp_path: Path) -> None:
    relative = "qualification/0_2_9/wp06f_closure_contract.json"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text(vocabulary.FORBIDDEN_TERMS[0], encoding="utf-8")
    assert vocabulary.review_vocabulary_audit(tmp_path, [relative])["status"] == "FAIL"


def test_missing_listed_input_fails_closed(tmp_path: Path) -> None:
    report = vocabulary.review_vocabulary_audit(tmp_path, ["absent.md"])
    assert report["status"] == "FAIL"
    assert report["integrity_errors"] == ["absent.md"]


def test_non_utf8_input_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "bad.md").write_bytes(b"\xff")
    report = vocabulary.review_vocabulary_audit(tmp_path, ["bad.md"])
    assert report["status"] == "FAIL"
    assert report["integrity_errors"] == ["bad.md"]


def test_current_historical_copies_use_the_analyzer_label() -> None:
    root = Path(__file__).resolve().parents[2]
    paths = [
        "docs/verification/0_2_9/wp06f-closure-contract.md",
        "qualification/0_2_9/wp06f_closure_contract.json",
    ]
    assert vocabulary.review_vocabulary_audit(root, paths)["status"] == "PASS"
    contract = json.loads((root / paths[1]).read_text(encoding="utf-8"))
    assert contract["authority_order"] == [
        "RAW_NUMERIC_EVIDENCE", "MACHINE_DERIVED_METRICS", "ANALYZER_REPORT", "SUMMARY_STATUS",
    ]
