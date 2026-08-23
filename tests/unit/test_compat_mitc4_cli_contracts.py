from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from solveur.compat.mitc4 import cli


def _result(passed: bool = True, values: dict[str, float] | None = None) -> SimpleNamespace:
    return SimpleNamespace(passed=passed, values=values or {})


def test_compat_verify_returns_success_and_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, ...]] = []

    class FakeVerifier:
        def run(self, **kwargs):
            calls.append((kwargs,))
            return [_result(True), _result(False)]

    monkeypatch.setattr(cli, "MechanicalVerifier", FakeVerifier)
    monkeypatch.setattr(cli, "print_results_table", lambda results: calls.append(tuple(results)))
    args = SimpleNamespace(quick=True, png=Path("quick.png"))
    assert cli.command_verify(args) == 1
    assert calls[0][0] == {"include_benchmark": False, "png": Path("quick.png")}

    class PassingVerifier:
        def run(self, **kwargs):
            return [_result(True)]

    monkeypatch.setattr(cli, "MechanicalVerifier", PassingVerifier)
    assert cli.command_verify(SimpleNamespace(quick=False, png=None)) == 0


def test_compat_scordelis_prints_values_and_applies_threshold(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    class FakeBenchmark:
        def __init__(self, nx, ny):
            self.mesh = (nx, ny)

        def run(self, **kwargs):
            assert kwargs["show"] is True
            assert kwargs["png"] == Path("roof.png")
            return SimpleNamespace(values={
                "w_edge_center": 1.0,
                "w_opposite_edge_center": 2.0,
                "reference": 3.0,
                "error_percent": 0.5,
                "symmetry_error_percent": 0.25,
            })

    monkeypatch.setattr(cli, "ScordelisLoBenchmark", FakeBenchmark)
    args = SimpleNamespace(nx=2, ny=3, show=True, png=Path("roof.png"), scale=10.0, max_error=1.0)
    assert cli.command_scordelis(args) == 0
    output = capsys.readouterr().out
    assert "Scordelis-Lo roof" in output
    assert "figure saved" in output

    args.max_error = 0.1
    assert cli.command_scordelis(args) == 1


def test_compat_cantilever_and_shear_commands(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    calls: list[tuple[object, ...]] = []

    class FakeCantilever:
        def __init__(self, *args, **kwargs):
            calls.append((args, kwargs))

        def run(self, **kwargs):
            assert kwargs == {"show": False, "png": None, "scale": None}
            return SimpleNamespace(values={"tip_w": 1.0, "reference": 2.0, "error_percent": 0.0})

    class FakeShear:
        def __init__(self, nx, ny):
            calls.append(((nx, ny),))

        def run(self):
            return SimpleNamespace(values={"locking_ratio": 1.0})

    monkeypatch.setattr(cli, "CantileverPlateBenchmark", FakeCantilever)
    monkeypatch.setattr(cli, "ShearLockingStudy", FakeShear)
    assert cli.command_cantilever(SimpleNamespace(
        nx=2, ny=1, length=1.0, width=0.2, thickness=0.01, force=-1.0,
        E=10.0, nu=0.3, show=False, png=None, scale=None,
    )) == 0
    assert cli.command_shear_study(SimpleNamespace(nx=4, ny=2)) == 0
    output = capsys.readouterr().out
    assert "Cantilever plate" in output
    assert "Transverse shear" in output
    assert calls


def test_compat_parser_defines_all_commands_and_defaults() -> None:
    parser = cli.build_parser()
    assert parser.parse_args(["verify", "--quick"]).quick is True
    assert parser.parse_args(["scordelis"]).command == "scordelis"
    assert parser.parse_args(["cantilever"]).command == "cantilever"
    assert parser.parse_args(["shear-study"]).command == "shear-study"


def test_compat_main_defaults_to_verify_and_emits_deprecation(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(cli, "command_verify", lambda args: 7)
    assert cli.main([]) == 7
    assert "DEPRECATION" in capsys.readouterr().err
