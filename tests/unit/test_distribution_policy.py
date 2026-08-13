from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

from scripts.check_distribution import check_distributions


def test_distribution_policy_accepts_runtime_wheel_and_transparent_sdist(tmp_path: Path) -> None:
    wheel = tmp_path / "qf_solver-0.2.0a0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("solveur/__init__.py", "")
        archive.writestr("mitc4/__init__.py", "")
        archive.writestr("qf_solver-0.2.0a0.dist-info/METADATA", "")
    sdist = tmp_path / "qf_solver-0.2.0a0.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        for relative in (
            "README.md",
            "LICENSE",
            "src/solveur/__init__.py",
            "src/mitc4/__init__.py",
        ):
            payload = relative.encode("utf-8")
            info = tarfile.TarInfo(f"qf_solver-0.2.0a0/{relative}")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    assert check_distributions([wheel, sdist]) == []


def test_distribution_policy_rejects_tests_in_wheel(tmp_path: Path) -> None:
    wheel = tmp_path / "qf_solver-0.2.0a0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("solveur/__init__.py", "")
        archive.writestr("mitc4/__init__.py", "")
        archive.writestr("qf_solver-0.2.0a0.dist-info/METADATA", "")
        archive.writestr("tests/unit/test_solver.py", "")
    failures = check_distributions([wheel])
    assert "expected one sdist, found 0" in failures
    assert any("repository-only path tests/unit/test_solver.py" in failure for failure in failures)
