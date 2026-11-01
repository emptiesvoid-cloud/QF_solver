"""Run the exact non-scientific compatibility nodeids approved for WP13."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "qualification" / "0_2_12" / "wp13_compatibility_nodeids.json"


def load_nodeids() -> tuple[list[str], str]:
    raw = MANIFEST.read_bytes()
    manifest: Any = json.loads(raw)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("Unsupported WP13 compatibility manifest schema.")
    nodeids = manifest.get("nodeids")
    if (
        not isinstance(nodeids, list)
        or not nodeids
        or not all(isinstance(nodeid, str) for nodeid in nodeids)
        or len(nodeids) != manifest.get("selection_count")
        or len(set(nodeids)) != len(nodeids)
    ):
        raise ValueError("WP13 compatibility nodeid selection is empty, duplicated, or malformed.")

    for nodeid in nodeids:
        module, separator, function = nodeid.partition("::")
        module_path = PurePosixPath(module)
        if (
            not separator
            or "::" in function
            or not function.startswith("test_")
            or module_path.is_absolute()
            or ".." in module_path.parts
            or not module.startswith("tests/unit/")
            or not (ROOT.joinpath(*module_path.parts)).is_file()
        ):
            raise ValueError(f"Invalid or unavailable compatibility nodeid: {nodeid}")
    return nodeids, hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="print the frozen nodeids and manifest hash without running pytest",
    )
    args = parser.parse_args()

    nodeids, manifest_sha256 = load_nodeids()
    print(f"WP13_COMPATIBILITY_MANIFEST_SHA256={manifest_sha256}")
    print(f"WP13_COMPATIBILITY_NODEID_COUNT={len(nodeids)}")
    for nodeid in nodeids:
        print(f"WP13_COMPATIBILITY_NODEID={nodeid}")
    if args.list_only:
        return 0

    command = [
        sys.executable,
        "-m",
        "pytest",
        *nodeids,
        "--durations=20",
        "--junitxml=junit.xml",
    ]
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
