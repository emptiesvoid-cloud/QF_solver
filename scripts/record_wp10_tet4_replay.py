"""Run and attest one fresh WP10-TET4 replay process."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    primary = out / "m3_replay_r2.json"
    reference = out / "m3_reference_r2.json"
    command = [
        sys.executable,
        str(root / "scripts" / "run_wp10_tet4_coupled.py"),
        "--case",
        "m2",
        "--output",
        str(primary),
        "--reference",
        str(reference),
    ]
    started = time.time()
    process = subprocess.Popen(command, cwd=root)
    return_code = process.wait()
    ended = time.time()
    manifest = {
        "kind": "fresh_process_replay_attestation",
        "pid": process.pid,
        "command": command,
        "cwd": str(root),
        "started_unix": started,
        "ended_unix": ended,
        "return_code": return_code,
        "source_sha": json.loads(primary.read_text(encoding="utf-8"))["source_sha"]
        if primary.exists()
        else None,
        "primary_sha256": sha256(primary) if primary.exists() else None,
        "reference_sha256": sha256(reference) if reference.exists() else None,
    }
    (out / "m3_replay_process_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
