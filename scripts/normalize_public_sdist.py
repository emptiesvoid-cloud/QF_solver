"""Normalize a built source distribution without changing its file payloads."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import tarfile
from pathlib import Path, PurePosixPath


def normalize_sdist(source: Path, destination: Path, source_date_epoch: int) -> dict[str, object]:
    """Rewrite an sdist with canonical ordering, ownership, timestamps and gzip header."""
    source = source.resolve(strict=True)
    destination = destination.resolve()
    if source == destination or destination.exists():
        raise ValueError("The normalized sdist output must be a new path.")
    if source_date_epoch < 0:
        raise ValueError("SOURCE_DATE_EPOCH must be a non-negative integer.")

    payloads: dict[str, tuple[bytes, int]] = {}
    roots: set[str] = set()
    folded: set[str] = set()
    with tarfile.open(source, "r:gz") as archive:
        for member in archive.getmembers():
            path = PurePosixPath(member.name)
            if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
                raise ValueError("The input sdist contains a non-canonical member path.")
            roots.add(path.parts[0])
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError("The input sdist contains a non-regular member.")
            if len(path.parts) < 2:
                raise ValueError("The input sdist must contain one top-level directory.")
            relative = path.relative_to(path.parts[0]).as_posix()
            if relative.casefold() in folded:
                raise ValueError("The input sdist contains duplicate or case-colliding paths.")
            folded.add(relative.casefold())
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("An input sdist member cannot be read.")
            payloads[member.name] = (stream.read(), member.mode & 0o777)

    if len(roots) != 1 or not payloads:
        raise ValueError("The input sdist must contain files under exactly one top-level directory.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as output:
                for name, (payload, mode) in sorted(payloads.items()):
                    info = tarfile.TarInfo(name)
                    info.size = len(payload)
                    info.mode = mode
                    info.mtime = source_date_epoch
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.pax_headers = {}
                    output.addfile(info, io.BytesIO(payload))

    observed: dict[str, bytes] = {}
    with tarfile.open(destination, "r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile() or member.mtime != source_date_epoch or member.uid != 0 or member.gid != 0:
                raise ValueError("The normalized sdist metadata is not canonical.")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("A normalized sdist member cannot be read.")
            observed[member.name] = stream.read()
    expected = {name: payload for name, (payload, _mode) in payloads.items()}
    if observed != expected:
        raise ValueError("The normalized sdist changed a path or file payload.")

    data = destination.read_bytes()
    return {
        "path": destination.name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "files": len(payloads),
        "source_date_epoch": source_date_epoch,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-date-epoch", type=int, required=True)
    args = parser.parse_args()
    try:
        import json

        print(json.dumps(normalize_sdist(args.input, args.output, args.source_date_epoch), indent=2))
    except (OSError, ValueError, tarfile.TarError) as exc:
        parser.exit(1, f"FAIL_CLOSED: {type(exc).__name__}: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
