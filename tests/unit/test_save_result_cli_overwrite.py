from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

from solveur.cli.main import SolverCli
from solveur.cli import standard


def test_solve_cli_overwrite_is_opt_in() -> None:
    parser = SolverCli().build_parser()
    base = ["solve", "--input", "model.json", "--output", "result.json"]

    assert parser.parse_args(base).overwrite is False
    assert parser.parse_args([*base, "--overwrite"]).overwrite is True


def test_all_json_result_cli_commands_expose_overwrite() -> None:
    parser = SolverCli().build_parser()
    commands = (
        ["check-mesh", "--input", "model.json", "--json-report", "mesh.json"],
        ["inspect", "--input", "model.json", "--output", "audit.json"],
        ["inspect-large", "--input", "model.h5", "--output", "audit.json"],
        ["verify-evidence", "--input", "bundle", "--json-report", "verify.json"],
        ["qualification-readiness", "--json-report", "readiness.json"],
    )

    for argv in commands:
        assert parser.parse_args(argv).overwrite is False
        assert parser.parse_args([*argv, "--overwrite"]).overwrite is True


def test_solve_cli_forwards_explicit_overwrite_without_solving(monkeypatch) -> None:
    result = SimpleNamespace(status="PASS", run_verdict=None, audit=None)
    captured: dict[str, object] = {}
    monkeypatch.setattr(standard, "load_model", lambda _path: object())
    monkeypatch.setattr(standard, "apply_verification_profile", lambda *_: None)
    monkeypatch.setattr(standard, "solve_model", lambda *_args, **_kwargs: result)
    monkeypatch.setattr(
        standard,
        "save_result",
        lambda _result, _path, *, overwrite: captured.update(overwrite=overwrite),
    )
    monkeypatch.setattr(standard, "qualification_exit_code", lambda *_: 0)
    monkeypatch.setattr(standard, "audit_gate_exit_code", lambda *_: 0)

    code = standard.command_solve(
        Namespace(
            input=Path("model.json"),
            output=Path("result.json"),
            overwrite=True,
            verification_profile=None,
            analysis=None,
            method=None,
            audit_md=None,
            csv_dir=None,
            vtu=None,
            evidence_dir=None,
            png=None,
            audit_gate="none",
        )
    )

    assert code == 0
    assert captured["overwrite"] is True
