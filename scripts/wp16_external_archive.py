"""Pack and verify an explicit, off-Git qualification-evidence bundle.

This operator-only script is never imported by the installable solver. It does
not contact Drive: upload and download are explicit, separate operations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


CHUNK_BYTES = 4 * 1024 * 1024
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class ArchiveError(ValueError):
    """An input or output violates the frozen archive contract."""


def _relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ArchiveError(f"Invalid relative path: {value!r}")
    path = PurePosixPath(value)
    parts = value.split("/")
    if (
        path.is_absolute()
        or any(part in {"", ".", ".."} or ":" in part for part in parts)
        or path.as_posix() != value
    ):
        raise ArchiveError(f"Unsafe relative path: {value!r}")
    return path


def _digest(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as source:
        while block := source.read(CHUNK_BYTES):
            digest.update(block)
            count += len(block)
    return count, digest.hexdigest()


def _selected_roots(values: list[str] | None) -> list[str] | None:
    if values is None:
        return None
    if not values:
        raise ArchiveError("Selected source roots cannot be empty")
    selected = sorted(_relative_path(value).as_posix() for value in values)
    if len(set(selected)) != len(selected) or any(
        later.startswith(earlier + "/")
        for index, earlier in enumerate(selected)
        for later in selected[index + 1 :]
    ):
        raise ArchiveError("Selected source roots overlap or repeat")
    return selected


def _source_files(root: Path, selected_roots: list[str] | None = None) -> list[tuple[str, Path]]:
    if not root.is_dir() or root.is_symlink():
        raise ArchiveError(f"Source must be a real directory: {root}")
    selected = _selected_roots(selected_roots)
    scan_roots = [root] if selected is None else []
    if selected is not None:
        for relative in selected:
            path = root
            for component in PurePosixPath(relative).parts:
                path = path / component
                if path.is_symlink():
                    raise ArchiveError(f"Selected source root contains a symlink: {path}")
            if not path.is_dir():
                raise ArchiveError(f"Selected source root is not a directory: {path}")
            scan_roots.append(path)
    files: list[tuple[str, Path]] = []
    for scan_root in scan_roots:
        for path in scan_root.rglob("*"):
            if path.is_symlink() or not (path.is_dir() or path.is_file()):
                raise ArchiveError(f"Unsupported source entry: {path}")
            if path.is_file():
                name = path.relative_to(root).as_posix()
                _relative_path(name)
                files.append((name, path))
    if not files:
        raise ArchiveError("Evidence source is empty")
    return sorted(files)


def _validated_manifest(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ArchiveError("Unsupported archive manifest")
    _relative_path(payload.get("source_relative_root"))
    selected_roots = payload.get("selected_roots")
    if selected_roots is not None:
        if not isinstance(selected_roots, list) or not all(isinstance(item, str) for item in selected_roots):
            raise ArchiveError("Invalid selected source roots")
        if _selected_roots(selected_roots) != selected_roots:
            raise ArchiveError("Selected source roots must be in canonical order")
    records = payload.get("files")
    if not isinstance(records, list) or not records:
        raise ArchiveError("Manifest must list files")
    seen: set[str] = set()
    total = 0
    for record in records:
        if not isinstance(record, dict):
            raise ArchiveError("Invalid file record")
        name = _relative_path(record.get("path")).as_posix()
        if selected_roots is not None and not any(name.startswith(root + "/") for root in selected_roots):
            raise ArchiveError(f"File outside selected source roots: {name}")
        size = record.get("size_bytes")
        digest = record.get("sha256")
        if (
            name in seen
            or not isinstance(size, int)
            or isinstance(size, bool)
            or size < 0
            or not isinstance(digest, str)
            or SHA256.fullmatch(digest) is None
        ):
            raise ArchiveError(f"Invalid or duplicate file record: {name}")
        seen.add(name)
        total += size
    if (
        len(records) != payload.get("file_count")
        or total != payload.get("uncompressed_bytes")
        or len(seen) != len(records)
    ):
        raise ArchiveError("Manifest totals do not agree")
    archive = payload.get("archive")
    if not isinstance(archive, dict):
        raise ArchiveError("Archive identity is missing")
    if (
        not isinstance(archive.get("name"), str)
        or Path(archive["name"]).name != archive["name"]
        or not isinstance(archive.get("size_bytes"), int)
        or isinstance(archive.get("size_bytes"), bool)
        or archive["size_bytes"] < 0
        or not isinstance(archive.get("sha256"), str)
        or SHA256.fullmatch(archive["sha256"]) is None
    ):
        raise ArchiveError("Invalid archive identity")
    return payload


def pack(
    source_root: Path,
    source_relative_root: str,
    archive_path: Path,
    manifest_path: Path,
    *,
    expected_count: int | None = None,
    expected_bytes: int | None = None,
    selected_roots: list[str] | None = None,
) -> dict[str, Any]:
    """Create an immutable ZIP64 and a byte-level manifest outside the source."""
    _relative_path(source_relative_root)
    selected = _selected_roots(selected_roots)
    paths = _source_files(source_root, selected)
    if expected_count is not None and len(paths) != expected_count:
        raise ArchiveError(f"Expected {expected_count} files, found {len(paths)}")
    if archive_path.exists() or manifest_path.exists():
        raise ArchiveError("Refusing to overwrite an archive or manifest")
    if archive_path.resolve().is_relative_to(source_root.resolve()):
        raise ArchiveError("Archive cannot be inside its source")
    if manifest_path.resolve().is_relative_to(source_root.resolve()):
        raise ArchiveError("Manifest cannot be inside its source")
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="wp16-", suffix=".zip", dir=archive_path.parent, delete=False) as temp:
            temporary_path = Path(temp.name)
        with zipfile.ZipFile(temporary_path, "w", allowZip64=True) as archive:
            for name, path in paths:
                before = path.stat()
                if not stat.S_ISREG(before.st_mode):
                    raise ArchiveError(f"Non-regular source: {path}")
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                digest = hashlib.sha256()
                size = 0
                with path.open("rb") as source, archive.open(info, "w", force_zip64=True) as sink:
                    while block := source.read(CHUNK_BYTES):
                        sink.write(block)
                        digest.update(block)
                        size += len(block)
                after = path.stat()
                if before.st_size != size or after.st_size != size or before.st_mtime_ns != after.st_mtime_ns:
                    raise ArchiveError(f"Source changed while packing: {path}")
                records.append({"path": name, "size_bytes": size, "sha256": digest.hexdigest()})
        total = sum(item["size_bytes"] for item in records)
        if expected_bytes is not None and total != expected_bytes:
            raise ArchiveError(f"Expected {expected_bytes} source bytes, found {total}")
        archive_size, archive_sha = _digest(temporary_path)
        manifest = {
            "schema_version": 1,
            "status": "LOCAL_ARCHIVE_VERIFIED_PENDING_REMOTE",
            "source_relative_root": source_relative_root,
            "file_count": len(records),
            "uncompressed_bytes": total,
            "archive": {"name": archive_path.name, "size_bytes": archive_size, "sha256": archive_sha},
            "files": records,
        }
        if selected is not None:
            manifest["selected_roots"] = selected
        _validated_manifest(manifest)
        verify(temporary_path, manifest)
        if archive_path.exists() or manifest_path.exists():
            raise ArchiveError("Destination appeared while packing")
        with manifest_path.open("x", encoding="utf-8", newline="\n") as target:
            json.dump(manifest, target, indent=2, ensure_ascii=False)
            target.write("\n")
        os.rename(temporary_path, archive_path)
        temporary_path = None
        return manifest
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def verify(archive_path: Path, manifest: dict[str, Any]) -> None:
    """Verify outer ZIP identity and every uncompressed member, fail closed."""
    manifest = _validated_manifest(manifest)
    archive_size, archive_sha = _digest(archive_path)
    declared = manifest["archive"]
    if archive_size != declared["size_bytes"] or archive_sha != declared["sha256"]:
        raise ArchiveError("Archive byte size or SHA-256 mismatch")
    expected = {item["path"]: item for item in manifest["files"]}
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        names = [member.filename for member in members]
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ArchiveError("ZIP members do not exactly match the manifest")
        for member in members:
            name = _relative_path(member.filename).as_posix()
            mode = member.external_attr >> 16
            if member.is_dir() or member.flag_bits & 0x1 or stat.S_IFMT(mode) not in {0, stat.S_IFREG}:
                raise ArchiveError(f"Unsupported ZIP member: {name}")
            record = expected[name]
            if member.file_size != record["size_bytes"]:
                raise ArchiveError(f"ZIP size mismatch: {name}")
            digest = hashlib.sha256()
            count = 0
            with archive.open(member) as source:
                while block := source.read(CHUNK_BYTES):
                    digest.update(block)
                    count += len(block)
            if count != record["size_bytes"] or digest.hexdigest() != record["sha256"]:
                raise ArchiveError(f"ZIP content mismatch: {name}")


def split(archive_path: Path, manifest: dict[str, Any], target_dir: Path, part_bytes: int) -> dict[str, Any]:
    """Split a verified ZIP into upload-sized, separately hashed raw parts."""
    verify(archive_path, manifest)
    if part_bytes < CHUNK_BYTES or part_bytes > 96 * 1024 * 1024 or target_dir.exists():
        raise ArchiveError("Part size must fit the Drive connector and destination must be new")
    target_dir.mkdir(parents=True)
    records: list[dict[str, Any]] = []
    with archive_path.open("rb") as source:
        index = 1
        while True:
            block = source.read(part_bytes)
            if not block:
                break
            name = f"{archive_path.name}.part{index:04d}"
            path = target_dir / name
            with path.open("xb") as sink:
                sink.write(block)
            records.append({"name": name, "size_bytes": len(block), "sha256": hashlib.sha256(block).hexdigest()})
            index += 1
    receipt = {"schema_version": 1, "archive": manifest["archive"], "parts": records}
    with (target_dir / "parts.json").open("x", encoding="utf-8", newline="\n") as sink:
        json.dump(receipt, sink, indent=2)
        sink.write("\n")
    return receipt


def verify_parts(parts_dir: Path, receipt: dict[str, Any]) -> None:
    if not isinstance(receipt, dict) or receipt.get("schema_version") != 1:
        raise ArchiveError("Invalid parts receipt")
    archive = receipt.get("archive")
    parts = receipt.get("parts")
    if not isinstance(archive, dict) or not isinstance(parts, list) or not parts:
        raise ArchiveError("Missing archive parts")
    if (
        not isinstance(archive.get("name"), str)
        or Path(archive["name"]).name != archive["name"]
        or not isinstance(archive.get("size_bytes"), int)
        or isinstance(archive.get("size_bytes"), bool)
        or archive["size_bytes"] < 0
        or not isinstance(archive.get("sha256"), str)
        or SHA256.fullmatch(archive["sha256"]) is None
    ):
        raise ArchiveError("Invalid archive identity in parts receipt")
    digest = hashlib.sha256()
    total = 0
    for index, record in enumerate(parts, 1):
        if not isinstance(record, dict):
            raise ArchiveError("Invalid part record")
        name = record.get("name")
        if name != f"{archive.get('name')}.part{index:04d}":
            raise ArchiveError("Invalid part order or name")
        if (
            not isinstance(record.get("size_bytes"), int)
            or isinstance(record.get("size_bytes"), bool)
            or record["size_bytes"] <= 0
            or not isinstance(record.get("sha256"), str)
            or SHA256.fullmatch(record["sha256"]) is None
        ):
            raise ArchiveError(f"Invalid part identity: {name}")
        path = parts_dir / name
        size, part_sha = _digest(path)
        if size != record.get("size_bytes") or part_sha != record.get("sha256"):
            raise ArchiveError(f"Part byte mismatch: {name}")
        with path.open("rb") as source:
            while block := source.read(CHUNK_BYTES):
                digest.update(block)
                total += len(block)
    if total != archive.get("size_bytes") or digest.hexdigest() != archive.get("sha256"):
        raise ArchiveError("Reassembled archive identity mismatch")


def assemble(parts_dir: Path, receipt: dict[str, Any], manifest: dict[str, Any], output: Path) -> None:
    """Reassemble only a complete matching set of parts, then verify every member."""
    manifest = _validated_manifest(manifest)
    if receipt.get("archive") != manifest["archive"]:
        raise ArchiveError("Parts receipt does not match the archive manifest")
    verify_parts(parts_dir, receipt)
    if output.exists():
        raise ArchiveError("Refusing to overwrite a reassembled archive")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="wp16-reassembled-", suffix=".zip", dir=output.parent, delete=False) as temp:
            temporary_path = Path(temp.name)
            for record in receipt["parts"]:
                with (parts_dir / record["name"]).open("rb") as source:
                    shutil.copyfileobj(source, temp, CHUNK_BYTES)
        verify(temporary_path, manifest)
        if output.exists():
            raise ArchiveError("Destination appeared while assembling")
        os.rename(temporary_path, output)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def restore(archive_path: Path, manifest: dict[str, Any], destination: Path) -> None:
    """Restore only verified regular files into a new directory."""
    verify(archive_path, manifest)
    if destination.exists():
        raise ArchiveError("Refusing to restore over an existing path")
    destination.mkdir(parents=True)
    with zipfile.ZipFile(archive_path) as archive:
        for record in manifest["files"]:
            relative = _relative_path(record["path"])
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(record["path"]) as source, target.open("xb") as sink:
                shutil.copyfileobj(source, sink, CHUNK_BYTES)
            size, digest = _digest(target)
            if size != record["size_bytes"] or digest != record["sha256"]:
                raise ArchiveError(f"Restored file mismatch: {relative}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    create = actions.add_parser("pack")
    create.add_argument("--source", type=Path, required=True)
    create.add_argument("--relative-root", required=True)
    create.add_argument("--archive", type=Path, required=True)
    create.add_argument("--manifest", type=Path, required=True)
    create.add_argument("--expected-count", type=int)
    create.add_argument("--expected-bytes", type=int)
    create.add_argument("--include-root", action="append", dest="selected_roots")
    check = actions.add_parser("verify")
    check.add_argument("--archive", type=Path, required=True)
    check.add_argument("--manifest", type=Path, required=True)
    divide = actions.add_parser("split")
    divide.add_argument("--archive", type=Path, required=True)
    divide.add_argument("--manifest", type=Path, required=True)
    divide.add_argument("--target-dir", type=Path, required=True)
    divide.add_argument("--part-mib", type=int, default=64)
    pieces = actions.add_parser("verify-parts")
    pieces.add_argument("--parts-dir", type=Path, required=True)
    pieces.add_argument("--receipt", type=Path)
    join = actions.add_parser("assemble")
    join.add_argument("--parts-dir", type=Path, required=True)
    join.add_argument("--receipt", type=Path)
    join.add_argument("--manifest", type=Path, required=True)
    join.add_argument("--output", type=Path, required=True)
    recover = actions.add_parser("restore")
    recover.add_argument("--archive", type=Path, required=True)
    recover.add_argument("--manifest", type=Path, required=True)
    recover.add_argument("--destination", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.action == "verify-parts":
        receipt_path = arguments.receipt or arguments.parts_dir / "parts.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        verify_parts(arguments.parts_dir, receipt)
        print("WP16 parts verified")
        return 0
    if arguments.action == "assemble":
        receipt_path = arguments.receipt or arguments.parts_dir / "parts.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        manifest = json.loads(arguments.manifest.read_text(encoding="utf-8"))
        assemble(arguments.parts_dir, receipt, manifest, arguments.output)
        print("WP16 archive reassembled and fully verified")
        return 0
    if arguments.action == "pack":
        manifest = pack(
            arguments.source,
            arguments.relative_root,
            arguments.archive,
            arguments.manifest,
            expected_count=arguments.expected_count,
            expected_bytes=arguments.expected_bytes,
            selected_roots=arguments.selected_roots,
        )
        print(f"WP16 archive packed: {manifest['archive']['sha256']}")
        return 0
    manifest = json.loads(arguments.manifest.read_text(encoding="utf-8"))
    if arguments.action == "verify":
        verify(arguments.archive, manifest)
        print("WP16 archive verified")
    elif arguments.action == "split":
        receipt = split(arguments.archive, manifest, arguments.target_dir, arguments.part_mib * 1024 * 1024)
        print(f"WP16 archive split into {len(receipt['parts'])} parts")
    elif arguments.action == "restore":
        restore(arguments.archive, manifest, arguments.destination)
        print("WP16 archive restored and verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
