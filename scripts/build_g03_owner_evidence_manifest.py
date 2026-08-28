"""Create the provenance record for the approved 025-G03 Owner decision."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
QUALIFIED_SOURCE_SHA = "85c75d06955976251dd54ad782f57f1eb5a7f8f4"
PACK = ROOT / "results" / "vnv_0_2_5" / "g03_final"
EULER_MANIFEST = ROOT / "results" / "vnv_0_2_5" / "g03_euler_final" / "vnv_manifest.json"
OWNER_REVIEW = ROOT / "docs" / "verification" / "0_2_5" / "0_2_5_g03_owner_review.md"
GATE_MATRIX = ROOT / "docs" / "verification" / "0_2_5" / "0_2_5_gate_matrix.md"
VNV_MATRIX = ROOT / "docs" / "verification" / "0_2_5" / "0_2_5_vnv_matrix.md"
RELEASE_READINESS = ROOT / "docs" / "verification" / "0_2_5" / "0_2_5_release_readiness.md"
OUTPUT = ROOT / "qualification" / "reviews" / "qf_solver_0_2_5_g03_owner_evidence_manifest.json"


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def _validate_pack() -> dict[str, Any]:
    manifest_path = PACK / "evidence_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = manifest.get("source", {})
    if source.get("source_sha") != QUALIFIED_SOURCE_SHA or source.get("dirty") is not False:
        raise ValueError("The G03 evidence pack does not match the clean qualified source SHA.")
    artifacts = manifest.get("files")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("The G03 evidence pack has no digest-tracked artifacts.")
    for artifact in artifacts:
        relative = artifact.get("path")
        expected = artifact.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ValueError("Malformed G03 artifact digest.")
        path = PACK / relative
        if not path.is_file() or _digest(path) != expected:
            raise ValueError(f"G03 artifact digest mismatch: {relative}")
    euler = json.loads(EULER_MANIFEST.read_text(encoding="utf-8"))
    if euler.get("source", {}).get("revision") != QUALIFIED_SOURCE_SHA or euler.get("source", {}).get("dirty") is not False:
        raise ValueError("The Euler evidence does not match the clean qualified source SHA.")
    return manifest


def main() -> int:
    if _git("status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("Owner evidence must be generated from a clean documentation commit.")
    pack = _validate_pack()
    documents = [OWNER_REVIEW, GATE_MATRIX, VNV_MATRIX, RELEASE_READINESS]
    if any(not path.is_file() for path in documents):
        raise FileNotFoundError("A required G03 Owner document is missing.")
    owner_evidence_sha = _git("rev-parse", "HEAD")
    payload = {
        "schema_version": 1,
        "record_type": "owner_evidence_manifest",
        "gate": "025-G03",
        "gate_status": "PASS",
        "owner_decision": "APPROVED",
        "mesh_decision": "APPROVED_BOUNDED_REFINEMENT",
        "contract_lowered": False,
        "qualified_source_sha": QUALIFIED_SOURCE_SHA,
        "qualified_source_dirty": False,
        "owner_evidence_sha": owner_evidence_sha,
        "owner_evidence_tree_clean": True,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "qualified_evidence": {
            "path": str((PACK / "evidence_manifest.json").relative_to(ROOT)).replace("\\", "/"),
            "sha256": _digest(PACK / "evidence_manifest.json"),
            "artifact_count": len(pack["files"]),
            "status": pack.get("status"),
        },
        "owner_documents": [
            {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": _digest(path)}
            for path in documents
        ],
        "qualified_scope": [
            "sparse linear buckling / first tangent instability",
            "TET4 externally correlated bounded probe",
            "four-level TET4 Euler refinement trend",
            "recorded total-Lagrangian tested domain",
        ],
        "excluded_scope": [
            "TET10/HEX8/HEX20 external buckling qualification",
            "post-buckling and imperfection-sensitive collapse",
            "production-wide stability qualification",
            "physical-validation claims",
        ],
        "unchanged_functional_gates": ["025-G04", "025-G05", "025-G06"],
        "command": "python scripts/build_g03_owner_evidence_manifest.py",
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "owner_evidence_sha": owner_evidence_sha}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
