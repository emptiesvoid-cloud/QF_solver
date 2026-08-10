"""Failure classification tests for the pinned Code_Aster Docker runner."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from solveur.core.errors import InfrastructureError
from solveur.verification.code_aster_tl_structural import _docker_unavailable, run_code_aster


def test_code_aster_runner_classifies_missing_docker_cli(tmp_path, monkeypatch) -> None:
    def missing(*args, **kwargs):
        raise FileNotFoundError("docker")

    monkeypatch.setattr("solveur.verification.code_aster_tl_structural.subprocess.run", missing)

    with pytest.raises(InfrastructureError, match="Docker CLI"):
        run_code_aster(tmp_path, "case")


def test_code_aster_runner_classifies_unavailable_daemon(tmp_path, monkeypatch) -> None:
    completed = SimpleNamespace(
        returncode=1,
        stdout="",
        stderr="failed to connect to the Docker API at npipe://dockerDesktopLinuxEngine",
    )
    monkeypatch.setattr(
        "solveur.verification.code_aster_tl_structural.subprocess.run",
        lambda *args, **kwargs: completed,
    )

    with pytest.raises(InfrastructureError, match="backend is unavailable"):
        run_code_aster(tmp_path, "case")

    assert (tmp_path / "code_aster_stderr.log").is_file()


def test_code_aster_docker_unavailable_does_not_classify_a_deck_failure() -> None:
    assert _docker_unavailable("cannot connect to the Docker daemon")
    assert not _docker_unavailable("<F>_ERROR: invalid AFFE_MODELE keyword")
