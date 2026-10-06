from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import unquote, urlparse

import numpy as np
import pytest
from PIL import Image, ImageStat

from scripts.build_docs import DocumentationEvidenceBuilder, DocumentationQualificationGateError
from scripts.build_technical_latex import _pandoc, _pdflatex
from scripts.docs_assets import DocumentationAssetBuilder
from scripts.docs_models import upgrade_tet4_to_tet10
from scripts.docs_publication import (
    DocumentationPublisher,
    _has_nonempty_review_metadata,
    _missing_review_metadata_fields,
    _review_scope_documents,
    is_generated_document,
    normalize_document_status,
    read_document_metadata,
)
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
        if not is_generated_document(path.relative_to(DOCS).as_posix())
        and path.relative_to(DOCS).as_posix() != "assets/vendor/README.md"
    }


def test_public_release_status_copy_distinguishes_release_and_tagged_source() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    index = (DOCS / "index.md").read_text(encoding="utf-8")
    roadmap = (DOCS / "reference" / "feuille_de_route.md").read_text(encoding="utf-8")
    architecture = (DOCS / "architecture.md").read_text(encoding="utf-8")
    open_source = (DOCS / "reference" / "open_source.md").read_text(encoding="utf-8")
    comparisons = (DOCS / "comparisons" / "index.md").read_text(encoding="utf-8")
    comparison_snapshot = (DOCS / "comparisons" / "qf-vs-code-aster.md").read_text(
        encoding="utf-8"
    )
    normalized_roadmap = " ".join(roadmap.split())
    normalized_architecture = " ".join(architecture.split())
    normalized_index = " ".join(index.split())
    normalized_comparisons = " ".join(comparisons.split())
    normalized_comparison_snapshot = " ".join(
        comparison_snapshot.replace(">", "").split()
    )

    assert "latest **published** release is `0.2.10`" in readme
    assert "0.2.11 is a **candidate, not yet published**" in readme
    assert "`0.2.8` — release candidate; not published" not in readme
    assert "source tag" in readme and "v0.2.10" in readme
    assert "QF Solver 0.2.10 is the current published release" in normalized_roadmap
    assert "Version 0.2.9 was a development/source snapshot" in normalized_roadmap
    assert "QF Solver 0.2.10 architecture" in normalized_architecture
    assert "published 0.2.8 release scope" in open_source
    assert "first public release after 0.2.8" in normalized_index
    assert "0.2.10" in index
    assert "0.2.8 is the current development candidate" not in roadmap
    assert "10.5281/zenodo.23106744" in readme
    assert "10.5281/zenodo.23106744" in index
    assert "version DOI" in readme
    assert "Current release" in normalized_index
    assert "current published package is 0.2.10" in normalized_comparisons
    assert (
        "not been refreshed against the 0.2.10 release"
        in normalized_comparison_snapshot
    )
    assert "not a current capability or maturity record" in normalized_comparison_snapshot
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert 'version: "0.2.11"' in citation
    assert not any(line.startswith("date-released:") for line in citation.splitlines())
    assert not any(line.startswith("doi:") for line in citation.splitlines())


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


def test_documentation_builder_captures_source_before_reset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    builder = DocumentationAssetBuilder(tmp_path)
    captured: dict[str, object] = {}

    def source_state(_root: Path, **_kwargs: object) -> dict[str, object]:
        captured["source_called"] = True
        return {"revision": "abc123", "dirty": False}

    def reset_outputs() -> None:
        captured["reset_after_source"] = captured.get("source_called", False)

    class Publisher:
        def __init__(self, _root: Path, **kwargs: object) -> None:
            captured["published_source"] = kwargs["source_state"]

        def publish(self) -> dict[str, object]:
            return {"qualification_campaign": {"status": "PASS"}}

    monkeypatch.setattr("scripts.docs_assets.git_source_state", source_state)
    monkeypatch.setattr(builder, "_reset_outputs", reset_outputs)
    for method_name in (
        "_build_formulation_figures",
        "_build_static_examples",
        "_build_solid_convergence",
        "_build_linear_methods",
        "_build_modal",
        "_build_newmark",
        "_build_harmonic",
        "_build_nonlinear",
        "_build_large_model",
        "_build_meshed_benchmarks",
    ):
        monkeypatch.setattr(builder, method_name, lambda: None)
    for function_name in (
        "publish_assembly_element_examples",
        "publish_mitc4_modal_plate",
        "publish_contact_verification",
        "publish_shell_verification",
        "publish_technical_content_closure",
    ):
        monkeypatch.setattr(f"scripts.docs_assets.{function_name}", lambda *args: None)
    monkeypatch.setattr("scripts.docs_assets.DocumentationPublisher", Publisher)

    builder.build()

    assert captured["reset_after_source"] is True
    assert captured["published_source"] == {"revision": "abc123", "dirty": False}


def test_standalone_tet4_review_references_eleven_existing_png_files() -> None:
    page = DOCS / "reference" / "reports" / "REVUE_TET4_LINEAIRE.html"
    collector = SiteLinkCollector()
    collector.feed(page.read_text(encoding="utf-8"))
    images = [target for role, target in collector.targets if role == "resource" and target.endswith(".png")]
    assert len(images) == 11
    assert all((page.parent / unquote(urlparse(target).path)).is_file() for target in images)


def test_every_controlled_page_is_registered_with_consistent_review_fields() -> None:
    registry = json.loads((DOCS / "document_registry.json").read_text(encoding="utf-8"))
    requirement_ids: set[str] = set()
    for requirements_path in (
        ROOT / "qualification" / "requirements.json",
        ROOT / "qualification" / "0_2_7" / "requirements.json",
    ):
        requirements = json.loads(requirements_path.read_text(encoding="utf-8"))
        for section in ("requirements", "level_up_requirements", "level_up_2_requirements"):
            requirement_ids.update(item["id"] for item in requirements.get(section, []))
    entries = registry["documents"]
    paths = {str(entry["path"]) for entry in entries}
    identifiers = [str(entry["id"]) for entry in entries]
    assert paths == controlled_markdown_paths()
    assert len(identifiers) == len(set(identifiers))
    reviewer_expectations = {
        **{
            identifier: "Owner"
            for identifier in {
                "DOC-OWNER-BACKEND-022-001",
                "DOC-HEX8-023-003",
                "DOC-HEX20-023-003",
                "DOC-029-WP05-C-REQUALIFICATION-001",
                "DOC-029-WP05-E-CROSS-FAMILY-001",
                "DOC-029-WP05-CDE-OWNER-INTEGRATION-001",
                "DOC-029-WP06-ABC-OWNER-DECISION",
                "DOC-029-WP08E-001",
                "DOC-029-WP08-OWNER-002",
                "DOC-029-WP12-OWNER-ACCEPTANCE-R2",
                "DOC-029-WP08-AREA-SUPPORTED-CONTACT-R1-13-RESULTS",
                "DOC-029-WP08-AREA-SUPPORTED-CONTACT-R1-13-OWNER-DECISION",
                "DOC-029-WP07-D-R2.5-OWNER-ACCEPTANCE-001",
                "DOC-029-WP07-R2.5-INTEGRATION-001",
                "DOC-029-WP08-AREA-SUPPORTED-CONTACT-R1-13-INTEGRATION",
                "DOC-029-WP09-OWNER-R3",
            }
        },
        **{
            identifier: "Quentin Farinazzo"
            for identifier in {"DOC-HEX8-023-002", "DOC-HEX20-023-002"}
        },
        **{
            identifier: "Quentin Farinazzo"
            for identifier in {
                "DOC-VV-OWNER-PAGES-001",
                "DOC-COMP-007",
                "DOC-VNV-MITC4-LAMINATE-DYN-001",
                "DOC-VV-CODEASTER-OWNER-2026-08-14",
                "DOC-VNV-MITC3-DYNAMICS-CODEASTER-DKT-017",
                "DOC-VNV-TET10-DYNAMICS-CODEASTER-TETRA10-018",
                "DOC-VNV-TET4-DYNAMICS-CODEASTER-TETRA4-020",
                "DOC-VNV-BEAM2-TRANSVERSE-DYNAMICS-CODEASTER-POUDE-019",
                "DOC-VNV-MITC3-CURVED-PROJECTED-001",
            }
        },
    }
    approver_expectations = {
        **{
            identifier: "Owner"
            for identifier in {
                "DOC-OWNER-BACKEND-022-001",
                "DOC-HEX8-023-003",
                "DOC-HEX20-023-003",
                "DOC-029-WP05-C-REQUALIFICATION-001",
                "DOC-029-WP05-E-CROSS-FAMILY-001",
                "DOC-029-WP05-CDE-OWNER-INTEGRATION-001",
                "DOC-029-WP06-ABC-OWNER-DECISION",
                "DOC-029-WP08E-001",
                "DOC-029-WP08-OWNER-002",
                "DOC-029-WP12-OWNER-ACCEPTANCE-R2",
                "DOC-029-WP08-AREA-SUPPORTED-CONTACT-R1-13-RESULTS",
                "DOC-029-WP08-AREA-SUPPORTED-CONTACT-R1-13-OWNER-DECISION",
                "DOC-029-WP07-D-R2.5-OWNER-ACCEPTANCE-001",
                "DOC-029-WP07-R2.5-INTEGRATION-001",
                "DOC-029-WP08-AREA-SUPPORTED-CONTACT-R1-13-INTEGRATION",
                "DOC-029-WP09-OWNER-R3",
            }
        },
        **{
            identifier: "Quentin Farinazzo"
            for identifier in {
                "DOC-VV-CODEASTER-OWNER-2026-08-14",
                "DOC-VNV-MITC3-DYNAMICS-CODEASTER-DKT-017",
                "DOC-VNV-TET10-DYNAMICS-CODEASTER-TETRA10-018",
                "DOC-VNV-TET4-DYNAMICS-CODEASTER-TETRA4-020",
                "DOC-VNV-BEAM2-TRANSVERSE-DYNAMICS-CODEASTER-POUDE-019",
                "DOC-VNV-MITC3-CURVED-PROJECTED-001",
            }
        },
    }
    review_dates = {
        "DOC-HEX8-023-002": "2026-08-24",
        "DOC-HEX20-023-002": "2026-08-24",
        "DOC-029-WP09-OWNER-R3": "2026-09-20",
        "DOC-VV-OWNER-PAGES-001": "2026-08-02",
        "DOC-VNV-MITC3-DYNAMICS-CODEASTER-DKT-017": "2026-08-02",
        "DOC-VNV-TET10-DYNAMICS-CODEASTER-TETRA10-018": "2026-08-02",
        "DOC-VNV-TET4-DYNAMICS-CODEASTER-TETRA4-020": "2026-08-02",
        "DOC-VNV-BEAM2-TRANSVERSE-DYNAMICS-CODEASTER-POUDE-019": "2026-08-02",
        "DOC-VNV-MITC3-CURVED-PROJECTED-001": "2026-08-09",
    }
    for entry in entries:
        metadata = read_document_metadata(DOCS / entry["path"])
        assert metadata["doc_id"] == entry["id"]
        assert normalize_document_status(str(metadata["status"])) == entry["status"]
        assert {"revision", "applicable_version", "reviewer", "approver"}.issubset(metadata)
        assert set(entry.get("requirements", [])).issubset(requirement_ids)
        assert metadata["reviewer"] == reviewer_expectations.get(entry["id"], "")
        assert metadata["approver"] == approver_expectations.get(entry["id"], "")
        if entry["id"] in review_dates:
            assert metadata["review_date"] == review_dates[entry["id"]]
        for reference in (*entry.get("examples", []), *entry.get("tests", [])):
            if "/" in reference:
                assert (ROOT / reference).is_file(), reference


@pytest.mark.parametrize("missing_field", ("revision", "applicable_version", "reviewer", "approver"))
def test_document_registry_requires_all_r1_metadata_fields(
    tmp_path: Path, missing_field: str
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    generated = docs / "generated"
    generated.mkdir()
    metadata = {
        "doc_id": "DOC-TEST-STRICT-001",
        "revision": "1",
        "applicable_version": "0.2.9",
        "reviewer": "Reviewer Name",
        "approver": "Approver Name",
        "status": "controlled",
    }
    metadata.pop(missing_field)
    yaml_lines = [f"{key}: {json.dumps(value)}" for key, value in metadata.items()]
    (docs / "controlled.md").write_text(
        "---\n" + "\n".join(yaml_lines) + "\n---\n# Controlled\n",
        encoding="utf-8",
    )
    (docs / "document_registry.json").write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "id": "DOC-TEST-STRICT-001",
                        "path": "controlled.md",
                        "title": "Strict metadata fixture",
                        "status": "controlled",
                        "requirements": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    publisher = object.__new__(DocumentationPublisher)
    publisher.root = tmp_path
    publisher.docs = docs
    publisher.generated = generated

    with pytest.raises(ValueError, match=f"no '{missing_field}' metadata"):
        publisher._document_registry()


@pytest.mark.parametrize(
    "metadata",
    (
        {},
        {"reviewer": "", "approver": "Owner"},
        {"reviewer": "Reviewer", "approver": "   "},
        {"reviewer": None, "approver": "Owner"},
    ),
)
def test_empty_review_fields_are_not_owner_approval_metadata(metadata: dict[str, Any]) -> None:
    assert _has_nonempty_review_metadata(metadata) is False


def test_complete_review_metadata_is_not_itself_an_owner_decision() -> None:
    assert _has_nonempty_review_metadata({"reviewer": "Reviewer", "approver": "Approver"}) is True


@pytest.mark.parametrize(
    ("metadata", "expected"),
    (
        ({}, ["reviewer", "approver"]),
        ({"reviewer": "Reviewer", "approver": ""}, ["approver"]),
        ({"reviewer": " ", "approver": "Approver"}, ["reviewer"]),
        ({"reviewer": "Reviewer", "approver": "Approver"}, []),
    ),
)
def test_review_metadata_gap_report_names_only_missing_fields(
    metadata: dict[str, Any], expected: list[str]
) -> None:
    assert _missing_review_metadata_fields(metadata) == expected


def test_review_readiness_emits_actionable_metadata_gap_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs = tmp_path / "docs"
    generated = docs / "generated"
    generated.mkdir(parents=True)
    (docs / "document_registry.json").write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "id": "DOC-MISSING-APPROVER",
                        "path": "missing_approver.md",
                        "status": "controlled",
                    },
                    {
                        "id": "DOC-COMPLETE",
                        "path": "complete.md",
                        "status": "owner_accepted",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (docs / "missing_approver.md").write_text(
        '---\ndoc_id: DOC-MISSING-APPROVER\nreviewer: "Reviewer A"\napprover: ""\n---\n',
        encoding="utf-8",
    )
    (docs / "complete.md").write_text(
        '---\ndoc_id: DOC-COMPLETE\nreviewer: "Reviewer B"\napprover: "Approver B"\n---\n',
        encoding="utf-8",
    )
    qualification = tmp_path / "qualification"
    qualification.mkdir()
    (qualification / "requirements.json").write_text('{"requirements": []}', encoding="utf-8")
    (qualification / "formulas.json").write_text('{"formulas": []}', encoding="utf-8")

    class StubFormulaRegistry:
        formulas: dict[str, Any] = {}

        def __init__(self, _path: Path) -> None:
            pass

        def validate(self, _formula_ids: list[str], _requirement_ids: set[str]) -> SimpleNamespace:
            return SimpleNamespace(status="PASS", issues=[], covered_count=0, requested_count=0)

    monkeypatch.setattr("scripts.docs_publication.FormulaRegistry", StubFormulaRegistry)
    publisher = object.__new__(DocumentationPublisher)
    publisher.root = tmp_path
    publisher.docs = docs
    publisher.generated = generated
    publisher.source_state = {"revision": "frozen-sha", "dirty": False}
    publisher._review_readiness()

    report = json.loads((generated / "review_readiness.json").read_text(encoding="utf-8"))
    owner_review = report["owner_review"]
    assert report["status"] == "PASS"
    assert owner_review["status"] == "PASS"
    assert owner_review["metadata_complete_documents"] == 1
    assert owner_review["review_scope_documents"] == 1
    assert owner_review["documents_missing_metadata"] == []
    assert owner_review["missing_metadata_field_counts"] == {"reviewer": 0, "approver": 0}
    assert report["review_metadata_backlog"]["status"] == "ADVISORY"
    assert report["review_metadata_backlog"]["documents_with_missing_metadata"] == 1
    assert report["review_metadata_backlog"]["missing_field_counts"] == {"reviewer": 0, "approver": 1}
    assert report["review_metadata_backlog"]["details"] == [
        {
            "id": "DOC-MISSING-APPROVER",
            "path": "missing_approver.md",
            "status": "controlled",
            "missing_fields": ["approver"],
        }
    ]


def test_review_readiness_blocks_explicit_approval_status_with_incomplete_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs = tmp_path / "docs"
    generated = docs / "generated"
    generated.mkdir(parents=True)
    (docs / "document_registry.json").write_text(
        json.dumps(
            {
                "documents": [
                    {"id": "DOC-CONTROLLED", "path": "controlled.md", "status": "controlled"},
                    {"id": "DOC-OWNER-ACCEPTED", "path": "accepted.md", "status": "owner_accepted"},
                ]
            }
        ),
        encoding="utf-8",
    )
    (docs / "controlled.md").write_text('---\nreviewer: ""\napprover: ""\n---\n', encoding="utf-8")
    (docs / "accepted.md").write_text('---\nreviewer: "Owner"\napprover: ""\n---\n', encoding="utf-8")
    qualification = tmp_path / "qualification"
    qualification.mkdir()
    (qualification / "requirements.json").write_text('{"requirements": []}', encoding="utf-8")
    (qualification / "formulas.json").write_text('{"formulas": []}', encoding="utf-8")

    class StubFormulaRegistry:
        formulas: dict[str, Any] = {}

        def __init__(self, _path: Path) -> None:
            pass

        def validate(self, _formula_ids: list[str], _requirement_ids: set[str]) -> SimpleNamespace:
            return SimpleNamespace(status="PASS", issues=[], covered_count=0, requested_count=0)

    monkeypatch.setattr("scripts.docs_publication.FormulaRegistry", StubFormulaRegistry)
    publisher = object.__new__(DocumentationPublisher)
    publisher.root = tmp_path
    publisher.docs = docs
    publisher.generated = generated
    publisher.source_state = {"revision": "frozen-sha", "dirty": False}
    publisher._review_readiness()

    report = json.loads((generated / "review_readiness.json").read_text(encoding="utf-8"))
    assert report["status"] == "BLOCKED"
    assert report["owner_review"]["documents_missing_metadata"] == ["DOC-OWNER-ACCEPTED"]
    assert report["review_metadata_backlog"]["details"][0]["id"] == "DOC-CONTROLLED"


def test_owner_reviewed_document_normalizes_to_controlled() -> None:
    assert normalize_document_status("owner_reviewed") == "controlled"


def test_legacy_and_extended_document_statuses_normalize_to_registry_values() -> None:
    assert normalize_document_status("approved_with_limitations") == "owner_approved_with_limitations"
    assert normalize_document_status("owner_correction_r1_candidate") == "controlled_candidate"


def test_review_metadata_scope_excludes_unreviewed_lifecycle_states() -> None:
    documents = [
        {"id": "controlled", "status": "controlled"},
        {"id": "controlled-release", "status": "controlled_release"},
        {"id": "accepted", "status": "owner_accepted_experimental"},
        {"id": "approved", "status": "approved"},
        {"id": "future-release-acceptance", "status": "accepted_for_release_0_2_9"},
        {"id": "accepted-with-limits", "status": "owner_accepted_with_limitations"},
        {"id": "candidate", "status": "controlled_candidate"},
        {"id": "evidence", "status": "controlled_evidence"},
        {"id": "pending", "status": "ready_for_owner_review"},
        {"id": "superseded", "status": "superseded"},
        {"id": "draft", "status": "draft"},
    ]

    assert [item["id"] for item in _review_scope_documents(documents)] == [
        "accepted",
        "approved",
        "future-release-acceptance",
        "accepted-with-limits",
    ]


def test_dynamic_owner_metadata_matches_recorded_review_decisions() -> None:
    dynamic_review = json.loads(
        (ROOT / "qualification" / "reviews" / "owner_review_linear_dynamics_2026-08-02.json").read_text(
            encoding="utf-8"
        )
    )
    curved_review = json.loads(
        (ROOT / "qualification" / "reviews" / "mitc3_laminate_curved_projected_2026-08-09.json").read_text(
            encoding="utf-8"
        )
    )
    registry = json.loads((DOCS / "document_registry.json").read_text(encoding="utf-8"))
    documents = {item["id"]: item for item in registry["documents"]}
    dynamic_ids = (
        "DOC-VNV-MITC3-DYNAMICS-CODEASTER-DKT-017",
        "DOC-VNV-TET10-DYNAMICS-CODEASTER-TETRA10-018",
        "DOC-VNV-TET4-DYNAMICS-CODEASTER-TETRA4-020",
        "DOC-VNV-BEAM2-TRANSVERSE-DYNAMICS-CODEASTER-POUDE-019",
    )

    for identifier in dynamic_ids:
        metadata = read_document_metadata(DOCS / documents[identifier]["path"])
        assert metadata["reviewer"] == dynamic_review["owner"]
        assert metadata["approver"] == dynamic_review["owner"]
        assert metadata["review_date"] == dynamic_review["decision_date"]

    curved_metadata = read_document_metadata(DOCS / documents["DOC-VNV-MITC3-CURVED-PROJECTED-001"]["path"])
    assert curved_metadata["reviewer"] == curved_review["signature"]["name"]
    assert curved_metadata["approver"] == curved_review["signature"]["name"]
    assert curved_metadata["review_date"] == curved_review["decision_date"]


def test_document_lifecycle_statuses_are_preserved() -> None:
    for status in (
        "controlled_audit",
        "closed",
        "planning",
        "implementation_foundation",
        "implementation_migration",
        "prospective_contract",
        "evidence",
        "executed_targeted_evidence",
        "frozen_execution",
        "frozen_execution_protocol",
        "hold",
        "owner_approved",
        "owner_decision_required",
        "candidate_for_owner_review",
        "audit_addendum",
        "preflight_hold",
        "controlled_release",
        "controlled_evidence",
        "ready_for_owner_review",
        "owner_accepted",
        "owner_accepted_experimental",
        "owner_accepted_with_recommendations",
        "owner_accepted_experimental_with_limitations",
        "owner_approved_with_limitations",
        "owner_approved_with_limitations_local_governing_unpushed",
        "accepted_for_release_0_2_3",
        "controlled_candidate",
        "controlled_candidate_contract",
        "merged_locally_pending_structural_requalification",
        "phase_0_preparation",
        "preparation_only",
        "verified_development_external_correlation",
    ):
        assert normalize_document_status(status) == status


def test_historical_document_status_aliases_normalize_without_downgrading() -> None:
    aliases = {
        "controlled-audit": "controlled_audit",
        "controlled-evidence": "controlled_evidence",
        "executed-targeted-evidence": "executed_targeted_evidence",
        "frozen-execution": "frozen_execution",
        "owner-approved": "owner_approved",
        "preparation-only": "preparation_only",
        "prospective-contract": "prospective_contract",
        "ready-for-owner-review": "ready_for_owner_review",
    }
    for source, expected in aliases.items():
        assert normalize_document_status(source) == expected


def test_qualification_build_requires_controlled_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "scripts.build_docs.git_source_state",
        lambda _root, **_kwargs: {"revision": "uncommitted", "dirty": True},
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
        lambda _root, **_kwargs: {"revision": "abc123", "dirty": False},
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


def test_current_documentation_uses_static_site_build_and_preserves_legacy_tools() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    installation = (DOCS / "getting-started" / "installation.md").read_text(encoding="utf-8")
    legacy_installation = (DOCS / "demarrage" / "installation.md").read_text(encoding="utf-8")

    assert "python -m pip install \".[docs]\"" in installation
    assert "python -m mkdocs build --strict -f .github/pages/mkdocs.yml" in installation
    assert "scripts/serve_docs.py" not in readme
    assert "scripts/serve_docs.py" not in installation
    assert "scripts\\build_docs.py" in legacy_installation
    assert "scripts\\build_technical_latex.py" in legacy_installation


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
