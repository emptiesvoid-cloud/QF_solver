"""Deterministic source-distribution normalization guards."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from scripts.normalize_public_sdist import normalize_sdist


def _write_sdist(path: Path, mtime: int, *, symlink: bool = False) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name, payload in (
            ("qf_solver-0.2.10/README.md", b"release notes\n"),
            ("qf_solver-0.2.10/src/qf_solver/__init__.py", b"__version__ = '0.2.10'\n"),
        ):
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            member.mtime = mtime
            archive.addfile(member, io.BytesIO(payload))
        if symlink:
            member = tarfile.TarInfo("qf_solver-0.2.10/escape")
            member.type = tarfile.SYMTYPE
            member.linkname = "../../outside"
            archive.addfile(member)


def test_normalized_sdist_bytes_are_stable_and_payload_preserving(tmp_path: Path) -> None:
    first, second = tmp_path / "first.tar.gz", tmp_path / "second.tar.gz"
    _write_sdist(first, 1_700_000_000)
    _write_sdist(second, 1_800_000_000)
    normalized_first, normalized_second = tmp_path / "normalized-1.tar.gz", tmp_path / "normalized-2.tar.gz"

    result_first = normalize_sdist(first, normalized_first, 1_791_032_593)
    result_second = normalize_sdist(second, normalized_second, 1_791_032_593)

    assert normalized_first.read_bytes() == normalized_second.read_bytes()
    assert result_first["sha256"] == result_second["sha256"]
    with tarfile.open(normalized_first, "r:gz") as archive:
        assert [item.name for item in archive.getmembers()] == [
            "qf_solver-0.2.10/README.md",
            "qf_solver-0.2.10/src/qf_solver/__init__.py",
        ]
        assert all(item.mtime == 1_791_032_593 and item.uid == item.gid == 0 for item in archive.getmembers())


def test_normalizer_rejects_symlinks_and_does_not_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "source.tar.gz"
    _write_sdist(source, 1_700_000_000, symlink=True)
    with pytest.raises(ValueError, match="non-regular"):
        normalize_sdist(source, tmp_path / "out.tar.gz", 1_791_032_593)
    with pytest.raises(ValueError, match="new path"):
        normalize_sdist(source, source, 1_791_032_593)


def test_normalizer_rejects_negative_epoch_and_multiple_roots(tmp_path: Path) -> None:
    source = tmp_path / "source.tar.gz"
    _write_sdist(source, 1_700_000_000)
    with pytest.raises(ValueError, match="non-negative"):
        normalize_sdist(source, tmp_path / "negative.tar.gz", -1)

    multiple = tmp_path / "multiple.tar.gz"
    with tarfile.open(multiple, "w:gz") as archive:
        for name, payload in (("one/a", b"a"), ("two/b", b"b")):
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
    with pytest.raises(ValueError, match="exactly one top-level directory"):
        normalize_sdist(multiple, tmp_path / "multiple-normalized.tar.gz", 1_791_032_593)
