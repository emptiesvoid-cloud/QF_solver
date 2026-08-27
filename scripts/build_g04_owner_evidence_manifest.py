"""Record the documentary provenance for the 025-G04 Owner audit.

The numerical/evidence pack remains immutable and intentionally reports an
open gate.  This manifest records the clean source revision on which that
pack was produced and the documentary commit carrying the Owner audit.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "results" / "vnv_0_2_5" / "g04_latest"
OUTPUT = ROOT / "qualification" / "reviews" / "qf_solver_0_2_5_g04_owner_evidence_manifest.json"
OWNER_REVIEW = ROOT / "docs" / "verification" / "0_2_5" / "0_2_5_g04_owner_review.md"
GATE_MATRIX = ROOT / "docs" / "verification" / "0_2_5" / "0_2_5_gate_matrix.md"
VNV_MATRIX = ROOT / "docs" / "verification" / "0_2_5" / "0_2_5_vnv_matrix.md"


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def _validate_pack() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest_path = PACK / "evidence_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"G04 evidence pack is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "OPEN" or manifest.get("dirty") is not False:
        raise ValueError("The G04 evidence pack must remain OPEN and clean-source controlled evidence.")
    source_sha = manifest.get("source_sha")
    if not isinstance(source_sha, str) or len(source_sha) != 40:
        raise ValueError("The G04 evidence pack has no valid source SHA.")
    if not isinstance(manifest.get("files"), list) or not manifest["files"]:
        raise ValueError("The G04 evidence pack has no digest-tracked artifacts.")
    for artifact in manifest["files"]:
        if not isinstance(artifact, dict):
            raise ValueError("Malformed G04 artifact record.")
        relative = artifact.get("path")
        expected = artifact.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ValueError("Malformed G04 artifact digest.")
        path = ROOT / relative
        if not path.is_file() or _digest(path) != expected:
            raise ValueError(f"G04 artifact digest mismatch: {relative}")
    return manifest, manifest["files"]


def main() -> int:
    if _git("status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("G04 Owner evidence must be generated from a clean documentation commit.")
    manifest, artifacts = _validate_pack()
    documents = [OWNER_REVIEW, GATE_MATRIX, VNV_MATRIX]
    if any(not path.is_file() for path in documents):
        raise FileNotFoundError("One or more G04 Owner documents are missing.")
    owner_evidence_sha = _git("rev-parse", "HEAD")
    source_sha = str(manifest["source_sha"])
    payload = {
        "schema_version": 1,
        "record_type": "owner_evidence_manifest",
        "gate": "025-G04",
        "gate_status": "OPEN",
        "owner_decision": "REQUIRED",
        "mesh_decision": "OPEN_MISSING_REQUIRED_LEVELS",
        "external_decision": "FAIL_EXTERNAL_BRANCH_REQUIREMENT",
        "contract_lowered": False,
        "qualified_source_sha": source_sha,
        "qualified_source_dirty": False,
        "owner_evidence_sha": owner_evidence_sha,
        "owner_evidence_tree_clean": True,
        "generated_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "qualified_evidence": {
            "path": str((PACK / "evidence_manifest.json").relative_to(ROOT)).replace("\\", "/"),
            "sha256": _digest(PACK / "evidence_manifest.json"),
            "artifact_count": len(artifacts),
            "status": manifest.get("status"),
        },
        "owner_documents": [
            {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": _digest(path),
            }
            for path in documents
        ],
        "internal_claim": "PASS_INTERNAL_RESEARCH only for the minimal common-driver two-element TET4 path",
        "remaining_blockers": [
            "No coarse/medium/fine/refined arc-length branch mesh study.",
            "Code_Aster complete-path correlation does not reproduce the QF turning point.",
            "No published or externally reproducible FEM branch reference is linked.",
        ],
        "command": "python scripts/build_g04_owner_evidence_manifest.py",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "owner_evidence_sha": owner_evidence_sha}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
