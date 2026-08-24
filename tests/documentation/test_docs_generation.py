from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

import numpy as np
import pytest
from PIL import Image, ImageStat

from scripts.build_docs import DocumentationEvidenceBuilder, DocumentationQualificationGateError
from scripts.build_technical_latex import _pandoc, _pdflatex
from scripts.docs_models import upgrade_tet4_to_tet10
from scripts.docs_publication import normalize_document_status, read_document_metadata
from scripts.docs_publication import DocumentationPublisher
from scripts.docs_support import automatic_deformation_scale, tetra_boundary_faces, write_markdown_table
from solveur.benchmarks import DemonstrationCatalog
from solveur.io.manifest import sha256


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
class SiteLinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.identifiers: set[str] = set()
        self.targets: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.identifiers.add(str(attributes["id"]))
        if tag == "a" and attributes.get("href"):
            self.targets.append(("link", str(attributes["href"])))
        if tag in {"img", "script"} and attributes.get("src"):
            self.targets.append(("resource", str(attributes["src"])))
        if tag == "link" and attributes.get("href"):
            self.targets.append(("resource", str(attributes["href"])))


def controlled_markdown_paths() -> set[str]:
    return {
        path.relative_to(DOCS).as_posix()
        for path in DOCS.rglob("*.md")
        if "generated" not in path.relative_to(DOCS).parts
        and path.relative_to(DOCS).as_posix() != "assets/vendor/README.md"
    }


def test_tetra_boundary_faces_remove_shared_face() -> None:
    faces = tetra_boundary_faces([(0, 1, 2, 3), (0, 2, 1, 4)])
    assert faces.shape == (6, 3)
    assert len({tuple(sorted(face)) for face in faces.tolist()}) == 6
    assert (0, 1, 2) not in {tuple(sorted(face)) for face in faces.tolist()}


def test_automatic_deformation_scale_has_documented_fraction() -> None:
    nodes = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    translations = np.asarray([[0.0, 0.0, 0.0], [0.1, 0.0, 0.0]])
    assert automatic_deformation_scale(nodes, translations, target_fraction=0.2) == pytest.approx(2.0)
    assert automatic_deformation_scale(nodes, np.zeros_like(nodes)) == 1.0
    with pytest.raises(ValueError, match="target_fraction"):
        automatic_deformation_scale(nodes, translations, target_fraction=0.0)


def test_latex_tool_overrides_use_explicit_portable_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pandoc = tmp_path / "pandoc-test"
    pdflatex = tmp_path / "pdflatex-test"
    pandoc.write_text("test", encoding="utf-8")
    pdflatex.write_text("test", encoding="utf-8")
    monkeypatch.setenv("QF_SOLVER_PANDOC", str(pandoc))
    monkeypatch.setenv("QF_SOLVER_PDFLATEX", str(pdflatex))
    monkeypatch.setattr("scripts.build_technical_latex.shutil.which", lambda _name: None)

    assert _pandoc() == pandoc
    assert _pdflatex() == pdflatex


def test_latex_tool_override_rejects_missing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing = tmp_path / "missing-pandoc"
    monkeypatch.setenv("QF_SOLVER_PANDOC", str(missing))
    with pytest.raises(RuntimeError, match="QF_SOLVER_PANDOC"):
        _pandoc()


def test_latex_tool_discovery_uses_portable_user_data_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pandoc = (
        tmp_path
        / "Microsoft"
        / "WinGet"
        / "Packages"
        / "JohnMacFarlane.Pandoc_test"
        / "pandoc-test"
        / "pandoc.exe"
    )
    pdflatex = tmp_path / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64" / "pdflatex.exe"
    pandoc.parent.mkdir(parents=True)
    pdflatex.parent.mkdir(parents=True)
    pandoc.write_text("test", encoding="utf-8")
    pdflatex.write_text("test", encoding="utf-8")
    monkeypatch.delenv("QF_SOLVER_PANDOC", raising=False)
    monkeypatch.delenv("QF_SOLVER_PDFLATEX", raising=False)
    monkeypatch.setattr("scripts.build_technical_latex.shutil.which", lambda _name: None)
    monkeypatch.setattr("scripts.build_technical_latex._user_data_root", lambda: tmp_path)

    assert _pandoc() == pandoc
    assert _pdflatex() == pdflatex


def test_tet10_upgrade_reuses_shared_midside_nodes() -> None:
    nodes = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, -1.0],
        ]
    )
    upgraded_nodes, connectivities = upgrade_tet4_to_tet10(nodes, [(0, 1, 2, 3), (0, 2, 1, 4)])
    assert upgraded_nodes.shape == (14, 3)
    assert all(len(connectivity) == 10 for connectivity in connectivities)
    assert set(connectivities[0][4:7]) == set(connectivities[1][4:7])


def test_markdown_table_is_deterministic_and_escapes_cells(tmp_path: Path) -> None:
    output = tmp_path / "table.md"
    write_markdown_table(output, ("Etat", "Valeur"), [(True, 1.0e-8), (False, "a|b\nc")])
    assert output.read_text(encoding="utf-8") == (
        "| Etat | Valeur |\n"
        "| --- | --- |\n"
        "| PASS | 1.000000e-08 |\n"
        "| FAIL | a\\|b c |\n"
    )


def test_public_api_demonstration_catalog_is_generated_from_its_registry(tmp_path: Path) -> None:
    publisher = DocumentationPublisher(ROOT, profile="engineering", records=(), scales={})
    publisher.generated = tmp_path
    publisher._demonstration_registry_catalog()

    content = (tmp_path / "demonstration_registry.md").read_text(encoding="utf-8")
    catalog = DemonstrationCatalog()
    assert content.count("\n") == len(catalog.list()) + 2
    assert "| DEMO-MITC4-HARMONIC-001 | model | MITC4 | harmonic_response |" in content
    assert "| DEMO-ORTHO-TET10-NEWMARK-001 | model | TET10 | transient_dynamic |" in content


def test_standalone_tet4_review_references_eleven_existing_png_files() -> None:
    page = DOCS / "reference" / "reports" / "REVUE_TET4_LINEAIRE.html"
    collector = SiteLinkCollector()
    collector.feed(page.read_text(encoding="utf-8"))
    images = [target for role, target in collector.targets if role == "resource" and target.endswith(".png")]
    assert len(images) == 11
    assert all((page.parent / unquote(urlparse(target).path)).is_file() for target in images)


def test_every_controlled_page_is_registered_with_consistent_review_fields() -> None:
    registry = json.loads((DOCS / "document_registry.json").read_text(encoding="utf-8"))
    entries = registry["documents"]
    paths = {str(entry["path"]) for entry in entries}
    identifiers = [str(entry["id"]) for entry in entries]
    assert paths == controlled_markdown_paths()
    assert len(identifiers) == len(set(identifiers))
    for entry in entries:
        metadata = read_document_metadata(DOCS / entry["path"])
        assert metadata["doc_id"] == entry["id"]
        assert normalize_document_status(str(metadata["status"])) == entry["status"]
        if entry["id"] in {
            "DOC-OWNER-BACKEND-022-001",
            "DOC-HEX8-023-003",
            "DOC-HEX20-023-003",
        }:
            assert metadata["reviewer"] == "Owner"
        elif entry["id"] in {
            "DOC-VV-OWNER-PAGES-001",
            "DOC-COMP-007",
            "DOC-VNV-MITC4-LAMINATE-DYN-001",
            "DOC-VV-CODEASTER-OWNER-2026-08-14",
        }:
            assert metadata["reviewer"] == "Quentin Farinazzo"
            if entry["id"] == "DOC-VV-OWNER-PAGES-001":
                assert metadata["review_date"] == "2026-08-02"
        else:
            assert metadata["reviewer"] == ""
        if entry["id"] not in {
            "DOC-VV-CODEASTER-OWNER-2026-08-14",
            "DOC-OWNER-BACKEND-022-001",
            "DOC-HEX8-023-003",
            "DOC-HEX20-023-003",
        }:
            assert metadata["approver"] == ""
        for reference in (*entry.get("examples", []), *entry.get("tests", [])):
            if "/" in reference:
                assert (ROOT / reference).is_file(), reference


def test_owner_reviewed_document_normalizes_to_controlled() -> None:
    assert normalize_document_status("owner_reviewed") == "controlled"


def test_document_lifecycle_statuses_are_preserved() -> None:
    for status in (
        "ready_for_owner_review",
        "owner_accepted",
        "owner_accepted_experimental",
        "owner_accepted_with_recommendations",
        "accepted_for_release_0_2_3",
        "controlled_candidate",
        "verified_development_external_correlation",
    ):
        assert normalize_document_status(status) == status


def test_qualification_build_requires_controlled_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "scripts.build_docs.git_source_state",
        lambda _root: {"revision": "uncommitted", "dirty": True},
    )
    with pytest.raises(DocumentationQualificationGateError, match="no committed source revision"):
        DocumentationEvidenceBuilder(ROOT)._enforce_qualification_gate()


def test_qualification_gate_accepts_controlled_and_superseded_documents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "document_registry.json").write_text(
        json.dumps(
            {
                "documents": [
                    {"id": "DOC-CONTROLLED", "status": "controlled"},
                    {"id": "DOC-LEGACY", "status": "superseded"},
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "scripts.build_docs.git_source_state",
        lambda _root: {"revision": "abc123", "dirty": False},
    )
    DocumentationEvidenceBuilder(tmp_path)._enforce_qualification_gate()


@pytest.mark.docs
def test_generated_manifest_hashes_and_images_are_valid() -> None:
    manifest_path = DOCS / "generated" / "docs_manifest.json"
    if not manifest_path.is_file():
        pytest.skip("Run scripts/build_docs.py before generated documentation checks.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["qualification_campaign"]["status"] == "PASS"
    assert manifest["test_count"] >= 232
    assert manifest["demonstrations"]
    for entry in manifest["files"]:
        path = DOCS / entry["path"]
        assert path.is_file(), entry["path"]
        assert sha256(path) == entry["sha256"]
    for record in manifest["demonstrations"]:
        model = ROOT / record["model_path"]
        assert model.is_file()
        assert sha256(model) == record["input_sha256"]

    images = sorted((DOCS / "assets" / "generated").rglob("*.png"))
    assert len(images) >= 30
    for case in ("tet10_j2_complex", "tet10_j2_structural"):
        assert (DOCS / "assets" / "reviews" / f"{case}_comparison.png").stat().st_size > 10_000
        assert (DOCS / "assets" / "reviews" / f"{case}_deformation.png").stat().st_size > 10_000
    for image_path in images:
        with Image.open(image_path) as image:
            assert image.width >= 300 and image.height >= 200
            grayscale = image.convert("L")
            assert ImageStat.Stat(grayscale).var[0] > 1.0, image_path.name

    benchmark = json.loads((DOCS / "generated" / "benchmarks" / "campaign_summary.json").read_text(encoding="utf-8"))
    assert benchmark["status"] == "PASS"
    assert benchmark["case_count"] == 11
    assert all(all(check["status"] == "PASS" for check in case["checks"]) for case in benchmark["cases"])
    review = json.loads((DOCS / "generated" / "review_readiness.json").read_text(encoding="utf-8"))
    formulas = json.loads((ROOT / "qualification" / "formulas.json").read_text(encoding="utf-8"))
    formula_count = len(formulas["formulas"])
    assert review["automated_traceability"] == "PASS"
    assert review["formula_coverage"] == {"covered": formula_count, "total": formula_count}
    assert review["owner_review"]["status"] == "BLOCKED"
    assert review["source_baseline"]["status"] == "BLOCKED"
    assert review["status"] == "BLOCKED"


def test_documentation_is_markdown_and_pdf_first_without_web_runtime() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    installation = (DOCS / "demarrage" / "installation.md").read_text(encoding="utf-8")
    for content in (readme, installation):
        assert "scripts\\build_docs.py" in content
        assert "scripts\\build_technical_latex.py" in content
        assert "serve_docs.py" not in content
    assert not (ROOT / "mkdocs.yml").exists()


def test_printable_mitc4_reviews_do_not_require_a_latex_renderer() -> None:
    reviews = (
        DOCS / "verification" / "revue_mitc4_modale.md",
        DOCS / "verification" / "revue_mitc4_transitoire.md",
    )
    raw_latex_markers = ("$$", "\\frac", "\\phi", "\\lambda", "\\ddot", "\\dot", "\\int")
    for review in reviews:
        content = review.read_text(encoding="utf-8")
        assert not any(marker in content for marker in raw_latex_markers), review
        assert "```text" in content


def test_complete_formulation_pages_are_registered() -> None:
    pages = {
        "elements/tet4/formulation_complete.md": ("# TET4 : derivation complete", "Demonstration : traction"),
        "elements/tet10/formulation_complete.md": ("# TET10 : derivation complete", "Consistance et demonstration"),
        "elements/mitc4/formulation_complete.md": ("# MITC4 : derivation complete", "Demonstrations de comportement"),
        "solveurs/methodes_lineaires.md": ("# Methodes lineaires", "## 4. CG, MINRES, GMRES et BiCGSTAB"),
    }
    registry = json.loads((DOCS / "document_registry.json").read_text(encoding="utf-8"))
    registered_paths = {entry["path"] for entry in registry["documents"]}
    for relative_path, required_fragments in pages.items():
        content = (DOCS / relative_path).read_text(encoding="utf-8")
        assert relative_path in registered_paths
        for fragment in required_fragments:
            assert fragment in content


