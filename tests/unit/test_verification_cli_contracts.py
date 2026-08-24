"""Contract coverage for verification and release-gate CLI commands."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

from solveur.cli import verification
from solveur.core.errors import ExitCode


def test_mechanical_and_tet10_verification_commands_report_success_and_failure(
    monkeypatch, tmp_path: Path
) -> None:
    checks = [SimpleNamespace(passed=True)]
    monkeypatch.setattr(verification, "MechanicalVerifier", lambda: SimpleNamespace(run=lambda **_: checks))
    monkeypatch.setattr(verification, "print_results_table", lambda _: None)
    assert verification.command_verify(Namespace(quick=True, png=None)) == int(ExitCode.ACCEPTED)

    monkeypatch.setattr(verification, "MechanicalVerifier", lambda: SimpleNamespace(run=lambda **_: [SimpleNamespace(passed=False)]))
    assert verification.command_verify(Namespace(quick=False, png="plot.png")) == int(ExitCode.QUALIFICATION_REJECTED)

    tet10_report = {"status": "PASS", "checks": [{"status": "PASS", "name": "frequency", "value": 1.0, "limit": 2.0}]}
    monkeypatch.setattr(verification, "Tet10MechanicalVerifier", lambda: SimpleNamespace(run=lambda: tet10_report))
    assert verification.command_verify_tet10(Namespace(json_report=tmp_path / "tet10.json")) == int(ExitCode.ACCEPTED)

    tet10_report["status"] = "FAIL"
    assert verification.command_verify_tet10(Namespace(json_report=None)) == int(ExitCode.QUALIFICATION_REJECTED)


def test_contact_and_verification_all_commands_cover_success_and_error_codes(monkeypatch, tmp_path: Path) -> None:
    contact = {"status": "PASS_INTERNAL", "studies": [{"status": "PASS", "campaign_id": "c1", "scope": "planar"}]}
    monkeypatch.setattr(verification, "run_contact_verification", lambda _: contact)
    assert verification.command_verify_contact(Namespace(output=tmp_path / "contact", json_report=None)) == int(ExitCode.ACCEPTED)
    contact["status"] = "FAIL"
    assert verification.command_verify_contact(Namespace(output=tmp_path / "contact", json_report=None)) == int(ExitCode.QUALIFICATION_REJECTED)

    monkeypatch.setattr(verification, "verification_profile", lambda _: SimpleNamespace(name="engineering"))
    monkeypatch.setattr(verification, "_verify_all_commands", lambda *_: [["first"], ["second"]])
    calls = iter([SimpleNamespace(returncode=0), SimpleNamespace(returncode=int(ExitCode.QUALIFICATION_REJECTED))])
    monkeypatch.setattr(verification.subprocess, "run", lambda *args, **kwargs: next(calls))
    report_path = tmp_path / "verify-all.json"
    failed = verification.command_verify_all(
        Namespace(profile="engineering", scope="scope", json_report=report_path)
    )
    assert failed == int(ExitCode.QUALIFICATION_REJECTED)
    assert report_path.is_file()

    monkeypatch.setattr(verification.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0))
    assert verification.command_verify_all(Namespace(profile="engineering", scope="scope", json_report=None)) == 0


def test_readiness_promotion_owner_and_qualification_commands(monkeypatch, tmp_path: Path) -> None:
    readiness = SimpleNamespace(
        status="PASS",
        scope="scope",
        scope_status="stable",
        covered_requirement_count=2,
        requirement_count=2,
        covered_formula_count=1,
        formula_count=1,
        checks=[SimpleNamespace(status="FAIL", identifier="r1", detail="missing")],
    )
    monkeypatch.setattr(verification, "qualification_readiness", lambda *_: readiness)
    monkeypatch.setattr(verification, "save_result", lambda *_: None)
    assert verification.command_qualification_readiness(
        Namespace(scope="scope", registry="registry.json", json_report=tmp_path / "readiness.json")
    ) == int(ExitCode.ACCEPTED)
    readiness.status = "FAIL"
    assert verification.command_qualification_readiness(
        Namespace(scope="scope", registry="registry.json", json_report=None)
    ) == int(ExitCode.QUALIFICATION_REJECTED)

    promotion = {"status": "WARNING", "summary": {"scope_count": 2, "blocked_scope_count": 1}}
    paths = {"json": "report.json", "markdown": "report.md", "owner_packet_json": "packet.json", "owner_packet_markdown": "packet.md"}
    monkeypatch.setattr(verification, "audit_maturity_promotion", lambda **_: promotion)
    monkeypatch.setattr(verification, "write_maturity_promotion_reports", lambda *_: paths)
    args = Namespace(plan="plan", matrix="matrix", coverage="coverage", criteria="criteria", output=tmp_path, fail_on_blocking=False)
    assert verification.command_maturity_promotion(args) == int(ExitCode.ACCEPTED)
    args.fail_on_blocking = True
    assert verification.command_maturity_promotion(args) == int(ExitCode.QUALIFICATION_REJECTED)

    review = SimpleNamespace(
        status="PASS",
        review_id="review-1",
        scopes=["scope"],
        decision="accepted",
        promotion_target="stable",
        errors=[],
        warnings=["bounded"],
        to_dict=lambda: {"status": "PASS"},
    )
    monkeypatch.setattr(verification, "validate_owner_review", lambda *_, **__: review)
    monkeypatch.setattr(verification, "write_json_file", lambda path, value: Path(path).write_text("{}", encoding="utf-8"))
    owner_args = Namespace(input="review.json", scope="scope", require_decision=True, target_maturity="stable", json_report=tmp_path / "owner.json")
    assert verification.command_owner_review_check(owner_args) == int(ExitCode.ACCEPTED)
    review.status = "FAIL"
    assert verification.command_owner_review_check(Namespace(**{**vars(owner_args), "json_report": None})) == int(ExitCode.QUALIFICATION_REJECTED)

    campaign = {"status": "PASS", "passed_count": 2, "case_count": 2}
    monkeypatch.setattr(verification, "run_qualification_campaign", lambda *_: campaign)
    assert verification.command_qualify(Namespace(manifest="manifest.json", output=tmp_path)) == int(ExitCode.ACCEPTED)
    campaign["status"] = "FAIL"
    assert verification.command_qualify(Namespace(manifest="manifest.json", output=tmp_path)) == int(ExitCode.QUALIFICATION_REJECTED)


def test_release_vv_and_evidence_commands_cover_pass_warning_and_fail(monkeypatch, tmp_path: Path) -> None:
    release = {
        "status": "PASS",
        "release": {"version": "0.2.4a0"},
        "scope_summary": {"pass_count": 2, "warning_count": 0, "fail_count": 0},
    }
    monkeypatch.setattr(verification, "run_release_vv", lambda *_, **__: release)
    args = Namespace(output=tmp_path, registry="registry.json", execute_campaign=False, fail_on_warning=False)
    assert verification.command_release_vv(args) == int(ExitCode.ACCEPTED)
    release["status"] = "WARNING"
    release["scope_summary"] = {"pass_count": 1, "warning_count": 1, "fail_count": 0}
    args.fail_on_warning = True
    assert verification.command_release_vv(args) == int(ExitCode.QUALIFICATION_REJECTED)
    release["status"] = "FAIL"
    assert verification.command_release_vv(args) == int(ExitCode.QUALIFICATION_REJECTED)

    evidence = SimpleNamespace(status="PASS", manifest_path="manifest.json", checked_file_count=3, errors=[], warnings=[])
    monkeypatch.setattr(verification, "verify_evidence", lambda _: evidence)
    monkeypatch.setattr(verification, "save_result", lambda *_: None)
    assert verification.command_verify_evidence(
        Namespace(input="manifest.json", json_report=tmp_path / "evidence.json")
    ) == int(ExitCode.ACCEPTED)
    evidence.status = "FAIL"
    evidence.errors = ["bad checksum"]
    assert verification.command_verify_evidence(Namespace(input="manifest.json", json_report=None)) == int(ExitCode.QUALIFICATION_REJECTED)
