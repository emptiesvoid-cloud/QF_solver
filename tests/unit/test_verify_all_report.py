"""Machine-readable records for the verification command sequence."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

from solveur.cli import verification


def test_verify_all_writes_pass_report(monkeypatch, tmp_path: Path) -> None:
    report_path = tmp_path / "verify_all.json"
    monkeypatch.setattr(verification, "_verify_all_commands", lambda _profile, _scope: [["first"], ["second"]])
    monkeypatch.setattr(verification.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=0))

    status = verification.command_verify_all(Namespace(profile="engineering", scope="tet4-linear-static", json_report=report_path))

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert status == 0
    assert report["status"] == "PASS"
    assert report["passed_command_count"] == 2
    assert report["commands"][1]["command"] == ["second"]


def test_verify_all_writes_failure_report(monkeypatch, tmp_path: Path) -> None:
    report_path = tmp_path / "verify_all.json"
    codes = iter((0, 1))
    monkeypatch.setattr(verification, "_verify_all_commands", lambda _profile, _scope: [["first"], ["bad"]])
    monkeypatch.setattr(verification.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=next(codes)))

    status = verification.command_verify_all(Namespace(profile="engineering", scope="tet4-linear-static", json_report=report_path))

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert status == 4
    assert report["status"] == "FAIL"
    assert report["command_count"] == 2
    assert report["passed_command_count"] == 1
