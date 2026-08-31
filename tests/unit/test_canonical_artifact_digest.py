"""Tests for the cross-platform release-evidence digest policy."""

from __future__ import annotations

from scripts.canonical_artifact_digest import canonical_artifact_bytes, canonical_artifact_sha256


def test_text_digest_normalizes_crlf_and_lone_cr_to_lf(tmp_path) -> None:
    lf = tmp_path / "evidence.json"
    crlf = tmp_path / "evidence.md"
    lf.write_bytes(b"one\ntwo\n")
    crlf.write_bytes(b"one\r\ntwo\r")

    assert canonical_artifact_bytes(lf) == b"one\ntwo\n"
    assert canonical_artifact_bytes(crlf) == b"one\ntwo\n"
    assert canonical_artifact_sha256(lf) == canonical_artifact_sha256(crlf)


def test_binary_digest_remains_byte_exact(tmp_path) -> None:
    first = tmp_path / "evidence.bin"
    second = tmp_path / "evidence-copy.bin"
    first.write_bytes(b"one\r\ntwo")
    second.write_bytes(b"one\ntwo")

    assert canonical_artifact_bytes(first) != canonical_artifact_bytes(second)
    assert canonical_artifact_sha256(first) != canonical_artifact_sha256(second)
