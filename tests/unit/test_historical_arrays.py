"""Local/archive parity and fail-closed integrity checks using synthetic bytes."""

from __future__ import annotations

import hashlib
from io import BytesIO
import json
from pathlib import Path

import numpy as np
import pytest

from tests.helpers.historical_arrays import HistoricalArrayError, load_historical_array_bytes


@pytest.fixture
def array_fixture(tmp_path: Path) -> tuple[Path, Path, Path, str, bytes]:
    buffer = BytesIO()
    np.savez(buffer, displacement=np.arange(3, dtype=float))
    payload = buffer.getvalue()
    repository = tmp_path / "checkout"
    repository.mkdir()
    archive_root = tmp_path / "archive"
    relative = "qualification/fixture/raw.npz"
    archived = archive_root / "fixture" / relative
    archived.parent.mkdir(parents=True)
    archived.write_bytes(payload)
    manifest = tmp_path / "fixture_manifest.json"
    manifest.write_text(json.dumps({
        "archive_subdirectory": "fixture",
        "files": [{"repository_path": relative, "archive_path": relative,
                   "sha256": hashlib.sha256(payload).hexdigest(), "size_bytes": len(payload)}],
    }), encoding="utf-8")
    return repository, archive_root, manifest, relative, payload


def _load(fixture: tuple[Path, Path, Path, str, bytes]) -> bytes:
    root, archive_root, manifest, relative, payload = fixture
    return load_historical_array_bytes(relative, hashlib.sha256(payload).hexdigest(), len(payload),
                                       root=root, manifest_path=manifest, archive_root=archive_root)


def test_hash_bound_archive_loads_without_copying_into_checkout(array_fixture: tuple) -> None:
    root, _, _, relative, expected = array_fixture
    assert _load(array_fixture) == expected
    assert not (root / relative).exists()
    with np.load(BytesIO(expected), allow_pickle=False) as arrays:
        assert arrays["displacement"].shape == (3,)


def test_exact_local_bytes_and_archive_bytes_have_same_identity(array_fixture: tuple) -> None:
    root, _, _, relative, expected = array_fixture
    path = root / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(expected)
    assert _load(array_fixture) == expected


def test_corrupt_local_copy_is_not_silently_replaced_by_valid_archive(array_fixture: tuple) -> None:
    root, _, _, relative, _ = array_fixture
    path = root / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(b"corruption")
    with pytest.raises(HistoricalArrayError, match="HASH_MISMATCH"):
        _load(array_fixture)


@pytest.mark.parametrize("kind", ["missing_bytes", "unlisted", "wrong_hash", "wrong_size"])
def test_archive_missing_or_inconsistent_bytes_cannot_pass(array_fixture: tuple, kind: str) -> None:
    _, archive_root, manifest, relative, _ = array_fixture
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if kind == "missing_bytes":
        (archive_root / "fixture" / relative).unlink()
    elif kind == "unlisted":
        data["files"] = []
    elif kind == "wrong_hash":
        data["files"][0]["sha256"] = "0" * 64
    else:
        data["files"][0]["size_bytes"] += 1
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(HistoricalArrayError, match="UNAVAILABLE"):
        _load(array_fixture)


@pytest.mark.parametrize("relative", ["../raw.npz", "/raw.npz", "q/../raw.npz", "q\\raw.npz", "q:raw.npz", "q//raw.npz", ""])
def test_unsafe_historical_array_paths_are_rejected(tmp_path: Path, relative: str) -> None:
    with pytest.raises(HistoricalArrayError, match="Invalid"):
        load_historical_array_bytes(relative, "0" * 64, 1, root=tmp_path)


def test_archive_symlink_cannot_escape_declared_root(array_fixture: tuple, tmp_path: Path) -> None:
    _, archive_root, _, relative, _ = array_fixture
    from unittest.mock import patch

    real_resolve = Path.resolve

    def substituted_resolve(path: Path, *args, **kwargs) -> Path:
        if path == archive_root / "fixture" / relative:
            return tmp_path / "outside.npz"
        return real_resolve(path, *args, **kwargs)

    with patch.object(Path, "resolve", substituted_resolve):
        with pytest.raises(HistoricalArrayError, match="UNAVAILABLE"):
            _load(array_fixture)
