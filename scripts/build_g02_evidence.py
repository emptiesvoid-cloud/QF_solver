"""Build the controlled geometric-nonlinearity evidence pack for 025-G02.

This script is a verification/reproducibility entry point. It does not alter
solver behaviour and intentionally keeps the finite-kinematic J2 path outside
the G02 qualification claim.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from g02_evidence_publication import (  # noqa: E402
    CODE_ASTER_IMAGE,
    OUT,
    ROOT,
    external_correlation,
    plots,
    report,
)
from g02_evidence_studies import (  # noqa: E402
    large_rotation_evidence,
    mesh_evidence,
    objectivity_evidence,
    small_strain_limit_evidence,
    tangent_evidence,
)


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def manifest(source_sha: str, dirty: bool, timestamp: str) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path.name == "evidence_manifest.json":
            continue
        files.append({"path": str(path.relative_to(ROOT)), "sha256": digest(path), "bytes": path.stat().st_size})
    return {
        "schema_version": 1,
        "study_id": "VNV-G02-GEOMETRIC-NONLINEAR-025",
        "gate": "025-G02",
        "status": "OPEN",
        "source_sha": source_sha,
        "dirty": dirty,
        "timestamp_utc": timestamp,
        "command": "python scripts/build_g02_evidence.py",
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
            "docker": shutil.which("docker") is not None,
            "code_aster_image": CODE_ASTER_IMAGE,
        },
        "files": files,
        "limitations": [
            "No G03-G06 gate is evaluated or closed.",
            "Mesh acceptance and G02 scope decision remain Owner-controlled.",
        ],
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    source_sha = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain"))
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    data: dict[str, Any] = {
        "schema_version": 1,
        "study_id": "VNV-G02-GEOMETRIC-NONLINEAR-025",
        "gate": "025-G02",
        "source_sha": source_sha,
        "dirty": dirty,
        "timestamp_utc": timestamp,
        "objectivity": objectivity_evidence(),
        "tangent": tangent_evidence(),
        "large_rotation": large_rotation_evidence(),
        "mesh": mesh_evidence(),
        "small_strain_limit": small_strain_limit_evidence(),
    }
    data["external"] = external_correlation()
    plot_paths = plots(data)
    data["plots"] = plot_paths
    data["status"] = "OPEN"
    data["owner_decision"] = "REQUIRED"
    data["claims"] = {
        "qualified_candidate": "bounded elastic Total-Lagrangian TET4/HEX8 only, pending Owner scope acceptance",
        "experimental": ["TET10/HEX20 elastic adapter observations", "four-family objectivity and tangent observations"],
        "research": ["total_lagrangian_j2", "finite-kinematic plasticity", "plastic large rotation"],
        "not_in_release_scope": ["G03", "G04", "G05", "G06", "G07"],
    }
    write_json(OUT / "summary.json", data)
    (OUT / "report.md").write_text(report(data, source_sha, dirty, timestamp, plot_paths), encoding="utf-8")
    write_json(
        OUT / "gate_decision.json",
        {
            "gate": "025-G02",
            "status": "OPEN",
            "recommended_status": "OPEN",
            "owner_decision": "REQUIRED",
            "source_sha": source_sha,
            "dirty": dirty,
            "evidence": "results/vnv_0_2_5/g02_latest/summary.json",
            "blocker": "Owner must accept the bounded pre-limit mesh/refinement treatment and record the G02 scope decision; this script does not sign on behalf of the Owner.",
            "functional_scope_not_changed": ["025-G03", "025-G04", "025-G05", "025-G06"],
        },
    )
    write_json(OUT / "evidence_manifest.json", manifest(source_sha, dirty, timestamp))
    print(json.dumps({"status": data["status"], "source_sha": source_sha, "dirty": dirty, "output": str(OUT)}, indent=2))
    return 0
