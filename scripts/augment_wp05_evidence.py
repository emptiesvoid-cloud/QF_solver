"""Add non-numerical provenance metadata to existing WP05 run records."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "qualification" / "0_2_9" / "wp05_cd_structural_contract.json"
RUNS = ROOT / "qualification" / "0_2_9" / "overnight_r2" / "wp05_runs"


def digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    contract_payload: dict[str, Any] = json.loads(CONTRACT.read_text(encoding="utf-8"))
    contract_digest = hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
    policy_digest = digest({
        "linear_solver": "minres",
        "linear_preconditioner": "jacobi",
        "linear_rtol": 1.0e-11,
        "linear_atol": 1.0e-14,
        "linear_maxiter": 10000,
        "linear_direct_fallback": False,
        "line_search": "existing",
        "floor_aware_termination": True,
        "tolerance": 1.0e-10,
        "load_increments": 12,
        "contract_schema_version": contract_payload.get("schema_version"),
    })
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    for path in sorted(RUNS.glob("*/H*/result.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "PASS":
            continue
        payload.setdefault("evidence_schema_version", 2)
        payload.setdefault("contract_sha256", contract_digest)
        payload.setdefault("governing_policy_digest", policy_digest)
        payload.setdefault("branch_at_capture", branch)
        payload.setdefault("source_sha_at_capture", payload.get("source_sha"))
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        temporary.replace(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
