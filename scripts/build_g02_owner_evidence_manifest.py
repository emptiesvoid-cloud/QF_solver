"""Create the provenance layer for the 025-G02 Owner decision.

The numerical G02 pack is intentionally immutable and remains tied to its
qualified source revision. This helper validates that pack, then records the
separate documentation commit that carries the Owner decision. It never runs a
solver calculation or changes solver behaviour.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
QUALIFIED_SOURCE_SHA = "fec5380db3bcdba13799ce31f3ed042ac5d2557b"
PACK = ROOT / "results" / "vnv_0_2_5" / "g02_latest"
OWNER_REVIEW = ROOT / "docs" / "verification" / "0_2_5" / "0_2_5_g02_owner_review.md"
GATE_MATRIX = ROOT / "docs" / "verification" / "0_2_5" / "0_2_5_gate_matrix.md"
VNV_MATRIX = ROOT / "docs" / "verification" / "0_2_5" / "0_2_5_vnv_matrix.md"
OUTPUT = ROOT / "qualification" / "reviews" / "qf_solver_0_2_5_g02_owner_evidence_manifest.json"


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


def _validated_pack() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest_path = PACK / "evidence_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("source_sha") != QUALIFIED_SOURCE_SHA or manifest.get("dirty") is not False:
        raise ValueError("The controlled G02 pack does not match the qualified clean source SHA.")
    artifacts = manifest.get("files")
    if not isinstance(artifacts, list) or len(artifacts) != 25:
        raise ValueError("The controlled G02 pack must contain exactly 25 digest-tracked artifacts.")
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ValueError("Malformed controlled G02 artifact record.")
        relative = artifact.get("path")
        expected = artifact.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ValueError("Malformed controlled G02 artifact digest.")
        path = ROOT / relative
        if not path.is_file() or _digest(path) != expected:
            raise ValueError(f"Controlled G02 artifact digest mismatch: {relative}")
    return manifest, artifacts


def main() -> int:
    if _git("status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("Owner evidence must be generated from a clean documentation commit.")
    manifest, artifacts = _validated_pack()
    owner_evidence_sha = _git("rev-parse", "HEAD")
    documents = [OWNER_REVIEW, GATE_MATRIX, VNV_MATRIX]
    for path in documents:
        if not path.is_file():
            raise FileNotFoundError(path)
    payload = {
        "schema_version": 1,
        "record_type": "owner_evidence_manifest",
        "gate": "025-G02",
        "gate_status": "PASS",
        "owner_decision": "APPROVED",
        "mesh_decision": "APPROVED_BOUNDED_REFINEMENT",
        "contract_lowered": False,
        "qualified_source_sha": QUALIFIED_SOURCE_SHA,
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
            "status_before_owner_decision": manifest.get("status"),
        },
        "owner_documents": [
            {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": _digest(path),
            }
            for path in documents
        ],
        "qualified_scope": [
            "elastic Total-Lagrangian finite-deformation statics",
            "common Full Newton with sparse tangent assembly",
            "TET4 and HEX8",
            "documented monotonic pre-limit positive-det(F) envelope",
        ],
        "excluded_scope": [
            "TET10/HEX20 finite-kinematic promotion",
            "total_lagrangian_j2 and finite-kinematic plasticity",
            "post-limit response, buckling, arc-length, contact and coupling",
            "friction, multi-million-DOF and physical-validation claims",
        ],
        "unchanged_functional_gates": ["025-G03", "025-G04", "025-G05", "025-G06"],
        "command": "python scripts/build_g02_owner_evidence_manifest.py",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "owner_evidence_sha": owner_evidence_sha}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
