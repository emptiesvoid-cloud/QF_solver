from __future__ import annotations

import sys
from types import SimpleNamespace

from scripts.release_readiness_pipeline_025 import (
    _sha_consistency_command,
    _run_gate_check,
    _source_changes,
    check_candidate_provenance,
    main,
    run_pipeline,
    steps,
)
from solveur.io.manifest import _source_status


def test_targeted_pipeline_is_dry_run_and_never_publishes() -> None:
    report = run_pipeline(profile="targeted")

    assert report["status"] == "PLANNED"
    assert report["publication"] == "OWNER_ONLY"
    assert "git push" in report["forbidden_actions"]
    assert all("upload" not in " ".join(step["command"]) for step in report["steps"])
    assert "tests/unit/test_calculix_buckling_025.py" in report["steps"][0]["command"]
    assert [step["name"] for step in report["steps"]] == [
        "tests",
        "docs",
        "gate_check",
        "sha_consistency",
        "build",
        "twine_check",
        "smoke_install",
    ]


def test_full_pipeline_adds_coverage_and_external_vnv_before_packaging() -> None:
    names = [step.name for step in steps("full")]
    assert names[:3] == ["tests", "coverage", "external_vnv"]
    assert names[-3:] == ["build", "twine_check", "smoke_install"]
    assert all("git tag" not in " ".join(step.command) for step in steps("full"))


def test_sha_consistency_step_is_fail_closed_and_reports_provenance() -> None:
    command = " ".join(_sha_consistency_command())

    assert "_run_sha_consistency" in command
    assert "raise SystemExit" in command


def _gate_document(status: str = "PASS") -> str:
    lines = ["| Gate | Name | Criteria | Dependencies | Status |"]
    for index in (*range(0, 7), *range(8, 13)):
        lines.append(f"| 025-G{index:02d} | gate | criteria | none | {status} |")
    lines.append("| 025-G07 | friction | optional | none | NOT_IN_RELEASE_SCOPE |")
    return "\n".join(lines) + "\n"


def test_gate_check_accepts_closed_mandatory_gates_and_optional_friction_scope(tmp_path, capsys) -> None:
    path = tmp_path / "gates.md"
    path.write_text(_gate_document(), encoding="utf-8")

    assert _run_gate_check(path) == 0
    output = capsys.readouterr().out
    assert "GATE_STATUS=PASS" in output
    assert "MISSING_GATES=" in output


def test_gate_check_accepts_owner_excluded_mandatory_gates_after_scope_revision(tmp_path, capsys) -> None:
    path = tmp_path / "gates.md"
    document = _gate_document()
    document = document.replace(
        "| 025-G04 | gate | criteria | none | PASS |",
        "| 025-G04 | gate | criteria | none | NOT_IN_RELEASE_SCOPE |",
    )
    document = document.replace(
        "| 025-G06 | gate | criteria | none | PASS |",
        "| 025-G06 | gate | criteria | none | NOT_IN_RELEASE_SCOPE |",
    )
    path.write_text(
        document + "\nOWNER_SCOPE_REVISION = APPROVED\nSCOPE_CHANGE = YES\n",
        encoding="utf-8",
    )

    assert _run_gate_check(path) == 0
    output = capsys.readouterr().out
    assert "SCOPE_REVISION_APPROVED=true" in output
    assert "OPEN_GATES=" in output


def test_gate_check_ignores_later_owner_disposition_tables(tmp_path, capsys) -> None:
    path = tmp_path / "gates.md"
    path.write_text(
        _gate_document()
        + "\n| 025-G04 | disposition | excluded | Owner decision | NOT_IN_RELEASE_SCOPE |\n",
        encoding="utf-8",
    )

    assert _run_gate_check(path) == 0
    assert "OPEN_GATES=" in capsys.readouterr().out


def test_gate_check_rejects_excluded_gate_without_owner_scope_revision(tmp_path, capsys) -> None:
    path = tmp_path / "gates.md"
    path.write_text(
        _gate_document().replace(
            "| 025-G04 | gate | criteria | none | PASS |",
            "| 025-G04 | gate | criteria | none | NOT_IN_RELEASE_SCOPE |",
        ),
        encoding="utf-8",
    )

    assert _run_gate_check(path) == 4
    assert "025-G04:NOT_IN_RELEASE_SCOPE" in capsys.readouterr().out


def test_gate_check_keeps_evidence_labels_separate_from_gate_status(tmp_path, capsys) -> None:
    path = tmp_path / "gates.md"
    path.write_text(_gate_document("PASS_INTERNAL"), encoding="utf-8")

    assert _run_gate_check(path) == 4
    assert "025-G00:PASS_INTERNAL" in capsys.readouterr().out


def test_gate_check_rejects_blocked_gate(tmp_path, capsys) -> None:
    path = tmp_path / "gates.md"
    path.write_text(_gate_document().replace("025-G03 | gate | criteria | none | PASS", "025-G03 | gate | criteria | none | BLOCKED"), encoding="utf-8")

    assert _run_gate_check(path) == 4
    assert "025-G03:BLOCKED" in capsys.readouterr().out


def test_gate_check_rejects_missing_gate(tmp_path, capsys) -> None:
    path = tmp_path / "gates.md"
    path.write_text(_gate_document().replace("| 025-G05 | gate | criteria | none | PASS |\n", ""), encoding="utf-8")

    assert _run_gate_check(path) == 4
    assert "MISSING_GATES=025-G05" in capsys.readouterr().out


def test_candidate_provenance_accepts_clean_revision(monkeypatch, tmp_path) -> None:
    responses = iter(
        [
            SimpleNamespace(returncode=0, stdout="abc123\n"),
            SimpleNamespace(returncode=0, stdout=""),
        ]
    )
    monkeypatch.setattr(
        "scripts.release_readiness_pipeline_025.subprocess.run",
        lambda *args, **kwargs: next(responses),
    )

    result = check_candidate_provenance(tmp_path)

    assert result == {
        "status": "PASS",
        "revision": "abc123",
        "tree_clean": True,
        "evidence_sha_match": None,
        "detail": "candidate revision is committed and the tree is clean",
    }


def test_candidate_provenance_rejects_dirty_revision(monkeypatch, tmp_path) -> None:
    responses = iter(
        [
            SimpleNamespace(returncode=0, stdout="abc123\n"),
            SimpleNamespace(returncode=0, stdout=" M README.md\n"),
        ]
    )
    monkeypatch.setattr(
        "scripts.release_readiness_pipeline_025.subprocess.run",
        lambda *args, **kwargs: next(responses),
    )

    result = check_candidate_provenance(tmp_path)

    assert result["status"] == "FAIL"
    assert result["revision"] == "abc123"
    assert result["tree_clean"] is False


def test_candidate_provenance_requires_matching_generated_manifest(monkeypatch, tmp_path) -> None:
    manifest = tmp_path / "docs" / "generated" / "docs_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        '{"source": {"revision": "abc123", "dirty": false}}\n',
        encoding="utf-8",
    )
    responses = iter(
        [
            SimpleNamespace(returncode=0, stdout="abc123\n"),
            SimpleNamespace(returncode=0, stdout=""),
        ]
    )
    monkeypatch.setattr(
        "scripts.release_readiness_pipeline_025.subprocess.run",
        lambda *args, **kwargs: next(responses),
    )

    result = check_candidate_provenance(tmp_path, require_evidence=True)

    assert result["status"] == "PASS"
    assert result["evidence_sha_match"] is True


def test_generated_evidence_changes_do_not_dirty_source_tree() -> None:
    assert _source_changes(" M README.md\n M docs/generated/docs_manifest.json\n") == [" M README.md"]
    assert _source_changes(" M docs/assets/generated/site.css\n?? .tmp_release_readiness_025/report.json\n") == []
    assert _source_changes(" M docs/verification/project_hygiene_architecture_audit_0_2_1.md\n") == []


def test_manifest_source_state_ignores_only_declared_generated_prefixes() -> None:
    status = " M docs/generated/docs_manifest.json\n M README.md\n"

    assert _source_status(status, ("docs/generated/", "docs/assets/generated/")) == [" M README.md"]


def test_candidate_provenance_matches_explicit_source_sha_after_evidence_generation(monkeypatch, tmp_path) -> None:
    manifest = tmp_path / "docs" / "generated" / "docs_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        '{"source_sha": "abc123", "source": {"revision": "abc123", "dirty": false}}\n',
        encoding="utf-8",
    )
    responses = iter(
        [
            SimpleNamespace(returncode=0, stdout="abc123\n"),
            SimpleNamespace(returncode=0, stdout=" M docs/generated/docs_manifest.json\n"),
        ]
    )
    monkeypatch.setattr(
        "scripts.release_readiness_pipeline_025.subprocess.run",
        lambda *args, **kwargs: next(responses),
    )

    result = check_candidate_provenance(tmp_path, require_evidence=True)

    assert result["status"] == "PASS"
    assert result["tree_clean"] is True
    assert result["evidence_sha_match"] is True


def test_candidate_provenance_rejects_missing_generated_manifest(monkeypatch, tmp_path) -> None:
    responses = iter(
        [
            SimpleNamespace(returncode=0, stdout="abc123\n"),
            SimpleNamespace(returncode=0, stdout=""),
        ]
    )
    monkeypatch.setattr(
        "scripts.release_readiness_pipeline_025.subprocess.run",
        lambda *args, **kwargs: next(responses),
    )

    result = check_candidate_provenance(tmp_path, require_evidence=True)

    assert result["status"] == "FAIL"
    assert result["evidence_sha_match"] is False


def test_gate_failure_keeps_packaging_evidence_running(monkeypatch, tmp_path) -> None:
    calls: list[str] = []

    def fake_run(command, **kwargs):
        name = command[command.index("-c") + 1] if "-c" in command else command[2]
        calls.append(name)
        return SimpleNamespace(returncode=4 if "OPEN_GATES" in name else 0, stdout="", stderr="")

    monkeypatch.setattr("scripts.release_readiness_pipeline_025.subprocess.run", fake_run)

    report = run_pipeline(root=tmp_path, profile="targeted", execute=True)

    assert report["status"] == "NOT_READY"
    assert report["blocking_steps"] == ["gate_check"]
    assert [step["name"] for step in report["steps"]][-3:] == [
        "build",
        "twine_check",
        "smoke_install",
    ]
    assert len(calls) == 7


def test_readiness_report_creates_nested_output_directory(tmp_path, monkeypatch) -> None:
    output = tmp_path / "nested" / "readiness.json"
    monkeypatch.setattr(sys, "argv", ["release_readiness_pipeline_025.py", "--output", str(output)])

    assert main() == 0
    assert output.exists()
