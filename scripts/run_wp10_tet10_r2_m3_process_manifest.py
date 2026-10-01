"""Run the frozen WP10 TET10 M3 replay and archive process provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "qualification" / "0_2_9" / "wp10_tet10_surface_r2_contract.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def run(output: Path, manifest: Path) -> dict[str, Any]:
    output = output if output.is_absolute() else ROOT / output
    manifest = manifest if manifest.is_absolute() else ROOT / manifest
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    command = [
        sys.executable,
        str(ROOT / "scripts" / "run_wp10_tet10_surface_r2.py"),
        "--mode",
        "M2",
        "--level",
        "H3",
        "--output",
        str(output),
    ]
    stdout_path = manifest.with_suffix(".stdout.log")
    stderr_path = manifest.with_suffix(".stderr.log")
    payload: dict[str, Any] = {
        "status": "RUNNING",
        "role": "M3_FRESH_PROCESS_REPLAY",
        "child_mode": "M2",
        "level": "H3",
        "branch": _git("branch", "--show-current"),
        "execution_sha_before": _git("rev-parse", "HEAD"),
        "contract_declared_branch": contract.get("branch"),
        "contract_sha256": _sha256(CONTRACT),
        "runner_sha": contract.get("runner_sha"),
        "reference_sha": contract.get("reference_sha"),
        "policy_digest": contract.get("policy_digest"),
        "command": command,
        "parent_pid": os.getpid(),
        "output": str(output),
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "started_at_utc": _utc_now(),
    }
    _write_manifest(manifest, payload)

    output.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=stdout,
            stderr=stderr,
            text=True,
        )
        payload["child_pid"] = process.pid
        payload["status"] = "RUNNING_CHILD"
        _write_manifest(manifest, payload)
        payload["exit_code"] = process.wait()

    payload["finished_at_utc"] = _utc_now()
    payload["status"] = "PASS" if payload["exit_code"] == 0 else "FAIL_CLOSED"
    payload["execution_sha_after"] = _git("rev-parse", "HEAD")
    if output.exists():
        result = json.loads(output.read_text(encoding="utf-8"))
        payload["result_status"] = result.get("status")
        payload["result_execution_sha"] = result.get("execution_sha")
        payload["result_contract_sha256"] = result.get("contract_sha256")
    _write_manifest(manifest, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.output, args.manifest)
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
