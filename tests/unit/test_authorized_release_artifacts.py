"""Release-asset verification accepts only exact Owner-authorized selected bytes."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.verify_authorized_release_artifacts import verify_artifact_set


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    dist = tmp_path / "dist"
    dist.mkdir()
    wheel = b"audited wheel bytes"
    sdist = b"audited source bytes"
    wheel_name = "qf_solver-0.2.10-py3-none-any.whl"
    sdist_name = "qf_solver-0.2.10.tar.gz"
    manifest_name = "qf_solver-0.2.10-SHA256SUMS.txt"
    (dist / wheel_name).write_bytes(wheel)
    (dist / sdist_name).write_bytes(sdist)
    manifest = f"{_sha(wheel)}  {wheel_name}\n{_sha(sdist)}  {sdist_name}\n".encode("ascii")
    (dist / manifest_name).write_bytes(manifest)
    contract: dict[str, object] = {
        "audited_artifacts": {
            "wheel": {"filename": wheel_name, "bytes": len(wheel), "sha256": _sha(wheel)},
            "sdist": {"filename": sdist_name, "bytes": len(sdist), "sha256": _sha(sdist)},
        },
        "sha256_manifest": {
            "filename": manifest_name, "bytes": len(manifest), "sha256": _sha(manifest),
        },
    }
    return dist, contract


def test_only_exact_packages_and_checksum_manifest_are_accepted(tmp_path: Path) -> None:
    dist, contract = _fixture(tmp_path)
    result = verify_artifact_set(dist, contract)
    assert result["status"] == "PASS_EXACT_RELEASE_ASSETS"
    assert len(result["files"]) == 3


def test_changed_package_bytes_and_manifest_are_rejected(tmp_path: Path) -> None:
    dist, contract = _fixture(tmp_path)
    (dist / "qf_solver-0.2.10.tar.gz").write_bytes(b"changed bytes")
    with pytest.raises(ValueError, match="differs from the authorized contract"):
        verify_artifact_set(dist, contract)

    dist, contract = _fixture(tmp_path / "second")
    (dist / "qf_solver-0.2.10-SHA256SUMS.txt").write_text("0" * 64, encoding="ascii")
    with pytest.raises(ValueError, match="differs from the authorized contract"):
        verify_artifact_set(dist, contract)


def test_extra_assets_are_not_silently_published(tmp_path: Path) -> None:
    dist, contract = _fixture(tmp_path)
    (dist / "repository-source.zip").write_bytes(b"uncleared source archive")
    with pytest.raises(ValueError, match="only the two selected packages"):
        verify_artifact_set(dist, contract)
