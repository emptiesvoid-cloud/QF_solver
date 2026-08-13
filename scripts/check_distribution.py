"""Check that release archives respect the public runtime/source boundary."""

from __future__ import annotations

import argparse
import glob
import tarfile
import zipfile
from pathlib import Path
from typing import Sequence


WHEEL_REQUIRED_PREFIXES = ("solveur/", "mitc4/", "qf_solver-")
WHEEL_FORBIDDEN_PREFIXES = (
    "docs/",
    "scripts/",
    "tests/",
    "tools/",
    "qualification/reviews/",
    "qualification/vnv/",
)
SDIST_REQUIRED_PARTS = ("README.md", "LICENSE", "src/solveur/", "src/mitc4/")
MAX_WHEEL_BYTES = 5 * 1024 * 1024
MAX_SDIST_BYTES = 75 * 1024 * 1024


def check_distributions(paths: Sequence[str | Path]) -> list[str]:
    """Return deterministic packaging-policy failures for wheel and sdist paths."""
    files = [Path(path) for path in paths]
    wheels = [path for path in files if path.suffix == ".whl"]
    sdists = [path for path in files if path.name.endswith(".tar.gz")]
    failures: list[str] = []
    if len(wheels) != 1:
        failures.append(f"expected one wheel, found {len(wheels)}")
    if len(sdists) != 1:
        failures.append(f"expected one sdist, found {len(sdists)}")
    for wheel in wheels:
        failures.extend(_check_wheel(wheel))
    for sdist in sdists:
        failures.extend(_check_sdist(sdist))
    return failures


def _check_wheel(path: Path) -> list[str]:
    if path.stat().st_size > MAX_WHEEL_BYTES:
        return [f"wheel exceeds {MAX_WHEEL_BYTES} bytes: {path.stat().st_size}"]
    with zipfile.ZipFile(path) as archive:
        names = tuple(archive.namelist())
    failures = [
        f"wheel contains repository-only path {name}"
        for name in names
        if name.startswith(WHEEL_FORBIDDEN_PREFIXES)
    ]
    for prefix in WHEEL_REQUIRED_PREFIXES:
        if not any(name.startswith(prefix) for name in names):
            failures.append(f"wheel missing required prefix {prefix}")
    return failures


def _check_sdist(path: Path) -> list[str]:
    if path.stat().st_size > MAX_SDIST_BYTES:
        return [f"sdist exceeds {MAX_SDIST_BYTES} bytes: {path.stat().st_size}"]
    with tarfile.open(path, "r:gz") as archive:
        names = tuple(_without_archive_root(name) for name in archive.getnames())
    return [
        f"sdist missing required path {required}"
        for required in SDIST_REQUIRED_PARTS
        if not any(name.startswith(required) for name in names)
    ]


def _without_archive_root(name: str) -> str:
    parts = name.replace("\\", "/").split("/", 1)
    return parts[1] if len(parts) == 2 else ""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", nargs="+")
    args = parser.parse_args(argv)
    expanded = [match for pattern in args.archives for match in (glob.glob(pattern) or [pattern])]
    failures = check_distributions(expanded)
    if failures:
        for failure in failures:
            print(f"DISTRIBUTION FAIL: {failure}")
        return 1
    print("DISTRIBUTION CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
