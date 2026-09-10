"""Contracts for the consolidated 0.2.1 Owner-review document pack."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pypdf import PdfReader

from scripts import build_owner_review_audit_pack as audit_pack


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def generated_pack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    """Build all generated artifacts outside tracked documentation paths."""
    tracked_sources = {
        path: path.read_bytes()
        for path in (
            audit_pack.STABLE_MD,
            audit_pack.OPEN_MD,
            audit_pack.PROJECT_AUDIT_MD,
        )
    }
    markdown = tmp_path / "markdown"
    pdfs = tmp_path / "pdf"
    monkeypatch.setattr(audit_pack, "STABLE_MD", markdown / "stable.md")
    monkeypatch.setattr(audit_pack, "OPEN_MD", markdown / "open.md")
    monkeypatch.setattr(audit_pack, "PROJECT_AUDIT_MD", markdown / "audit.md")
    monkeypatch.setattr(audit_pack, "STABLE_PDF", pdfs / "stable.pdf")
    monkeypatch.setattr(audit_pack, "OPEN_PDF", pdfs / "open.pdf")
    monkeypatch.setattr(audit_pack, "PROJECT_AUDIT_PDF", pdfs / "audit.pdf")
    result = audit_pack.build()
    assert {path: path.read_bytes() for path in tracked_sources} == tracked_sources
    return result


def _text(path: Path) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)


@pytest.mark.docs
def test_pack_contains_every_scope_without_prefilled_decision(
    generated_pack: tuple[Path, Path, Path],
) -> None:
    stable_pdf, open_pdf, _ = generated_pack
    snapshot = json.loads(
        (ROOT / "qualification" / "public_evidence" / "owner_review_audit_pack_0_2_1.json").read_text(encoding="utf-8")
    )
    packet = snapshot["packet"]
    stable_text = _text(stable_pdf)
    open_text = _text(open_pdf)
    for row in packet["scopes"]:
        target = open_text if row.get("blocking_classification") == "owner_decision_pending" else stable_text
        assert row["scope"] in target
    assert "Decision pre-remplie" in stable_text
    assert "Decision pre-remplie" in open_text
    assert "tet4-total-lagrangian-structural-v2" in open_text
    assert "1.896 pour cent" in open_text
    assert "4,5 %" not in open_text


@pytest.mark.docs
def test_pack_page_counts_and_project_audit_verdict(
    generated_pack: tuple[Path, Path, Path],
) -> None:
    stable_pdf, open_pdf, audit_pdf = generated_pack
    assert len(PdfReader(str(stable_pdf)).pages) >= 5
    assert len(PdfReader(str(open_pdf)).pages) >= 5
    assert len(PdfReader(str(audit_pdf)).pages) >= 5
    audit_text = _text(audit_pdf)
    assert "Confidentialite" in audit_text
    assert "0 finding" in audit_text
    assert "Release-vv" in audit_text


@pytest.mark.docs
def test_markdown_sources_keep_decisions_pending(
    generated_pack: tuple[Path, Path, Path],
) -> None:
    del generated_pack
    for name in (
        "owner_review_stable_promotions_0_2_1.md",
        "owner_review_open_gates_0_2_1.md",
    ):
        text = (ROOT / "docs" / "verification" / name).read_text(encoding="utf-8")
        assert "decision: pending" in text
        assert "Signature : `__________`" in text or "relecture independante" in text
