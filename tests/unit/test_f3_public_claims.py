"""F3 guardrails for the public 0.2.7 claim boundary."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = ROOT / "qualification/0_2_7/f3_public_claim_audit.json"


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _active_markdown_scope() -> list[Path]:
    paths = [ROOT / "README.md", ROOT / "CHANGELOG.md"]
    for directory in ("verification/0_2_7", "reference", "solveurs", "elements", "demarrage"):
        paths.extend(sorted((ROOT / "docs" / directory).rglob("*.md")))
    paths.append(ROOT / "examples/README.md")
    return paths


def test_f3_audit_schema_and_evidence_references_are_complete() -> None:
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    assert audit["schema_version"] == 1
    assert audit["audit_start_sha"] == "bcdf7279a61a2942e0619236b3a597ad3e4583ee"
    assert audit["active_branch"] == "codex/0.2.7-foundation"
    assert len(audit["claims"]) >= 20
    assert {"IMPLEMENTED", "TESTED", "VERIFIED", "EXTERNALLY_VALIDATED", "QUALIFIED", "EXPERIMENTAL"} <= set(
        audit["claim_taxonomy"]
    )
    assert audit["finding_summary"]["overclaims_found"] == 0
    for claim in audit["claims"]:
        for reference in claim["evidence_refs"]:
            assert (ROOT / reference).exists(), (claim["id"], reference)
    for finding in audit["findings"]:
        for location in finding["locations"]:
            assert (ROOT / location).exists(), (finding["id"], location)
    assert audit["controls"] == {
        "historical_evidence_modified": False,
        "maturity_promoted": False,
        "numerical_source_changed": False,
        "requalification_required": False,
        "heavy_benchmark_run": False,
        "full_regression_run": False,
        "release_actions": "NOT_PERFORMED",
        "final_sha_recorded_in_closeout": True,
        "claim_policy": "No public statement may be stronger than the nearest executed evidence and its declared boundary.",
    }


def test_active_boundaries_match_registry_and_release_truth() -> None:
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    registry = _load("qualification/0_2_7/capability_registry_v2.json")
    release_truth = _load("qualification/0_2_7/wp21_final_release_truth.json")
    state = _load("qualification/0_2_7/level_up_2_state.json")

    assert audit["current_release_state"]["wedge6_static"] == "EXPERIMENTAL"
    assert audit["current_release_state"]["calculix_wedge6"] == "NOT_COMPARABLE"
    assert registry["source_of_truth"] is True
    assert release_truth["claims"]["wedge6_static"] == "EXPERIMENTAL"
    assert release_truth["claims"]["three_million_gold"] == "UNCLAIMED"
    assert state["global_accounting"]["current_global_progress"] == "96/100"
    assert state["global_accounting"]["level_up_2"] == "46/50 OPEN"

    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "WEDGE6 static remains experimental" in root_readme
    assert "No claim of GPU, general HPC" in root_readme
    assert "two complete 5M Silver replays" in root_readme
    assert "No claim of certification" in root_readme

    interfaces = (ROOT / "docs/reference/interfaces.md").read_text(encoding="utf-8")
    assert "PYTHONPATH=src" in interfaces
    assert "Aucune de ces formes ne garantit l'isolation" in interfaces


def test_active_lu2_views_do_not_present_old_accounting_as_current() -> None:
    views = [
        ROOT / "docs/verification/0_2_7/README.md",
        ROOT / "docs/verification/0_2_7/0_2_7_master_plan.md",
        ROOT / "docs/verification/0_2_7/0_2_7_gate_matrix.md",
        ROOT / "docs/verification/0_2_7/0_2_7_progress_tracker.md",
    ]
    for path in views:
        text = path.read_text(encoding="utf-8")
        assert "46/50" in text
        assert "96/100" in text
    plan = _load("qualification/0_2_7/level_up_2_plan.json")
    statuses = {item["id"]: item["status"] for item in plan["work_packages"]}
    assert statuses["LU2-WP04"] == "PASS"
    assert statuses["LU2-WP05"] == "PASS"

    roadmap = (ROOT / "docs/reference/feuille_de_route.md").read_text(encoding="utf-8")
    assert "historical planning snapshot" in roadmap
    assert "0.2.7a0 active scope" in roadmap

    for relative in ("docs/elements/tet4.md", "docs/elements/tet10.md", "docs/elements/mitc4.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "registry v2" in text


def test_critical_markdown_links_resolve_locally() -> None:
    link_pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    checked = 0
    broken: list[tuple[str, str]] = []
    for path in _active_markdown_scope():
        text = path.read_text(encoding="utf-8")
        for raw_target in link_pattern.findall(text):
            target = raw_target.split("#", 1)[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            checked += 1
            candidate = (path.parent / target).resolve()
            if not candidate.exists():
                broken.append((str(path.relative_to(ROOT)), raw_target))
    assert checked >= 354
    assert broken == broken[:0], broken

    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    assert audit["scanned_scope"]["active_link_scope_broken"] == 0
    assert audit["scanned_scope"]["legacy_or_untracked_links_deferred"] == 27


def test_f3_view_preserves_negative_boundaries() -> None:
    view = (ROOT / "docs/verification/0_2_7/0_2_7_f3_public_claim_audit.md").read_text(encoding="utf-8")
    for phrase in (
        "WEDGE6 static reste `EXPERIMENTAL`",
        "CalculiX/C3D6\n  reste `NOT_COMPARABLE`",
        "Aucun claim GPU",
        "mixed meshes, WEDGE15, PYRAMID5",
        "Historical evidence modified = NO",
        "Le scope actif 0.2.7 compte 366 liens locaux controles",
    ):
        assert phrase in view


def test_f3_view_is_registered_as_a_controlled_document() -> None:
    registry = _load("docs/document_registry.json")
    entries = [
        entry
        for entry in registry["documents"]
        if entry["id"] == "DOC-027-F3-PUBLIC-001"
    ]
    assert entries == [
        {
            "id": "DOC-027-F3-PUBLIC-001",
            "path": "verification/0_2_7/0_2_7_f3_public_claim_audit.md",
            "title": "0.2.7 F3 public claims audit",
            "status": "controlled_candidate",
            "requirements": [],
            "examples": [
                "qualification/0_2_7/f3_public_claim_audit.json",
                "tests/unit/test_f3_public_claims.py",
            ],
            "tests": [
                "tests/unit/test_f3_public_claims.py",
                "tests/unit/test_public_document_audit.py",
            ],
        }
    ]
