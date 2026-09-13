"""Phase-0 guard and metadata helpers for the WP06-D contract.

This module deliberately cannot launch a structural or external solve.  The
Phase-1 harness will consume the frozen JSON contract after Owner
authorization and governing-branch integration.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


STRUCTURAL_SOLVES_ENABLED = False
EXTERNAL_SOLVER_ENABLED = False
ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification" / "0_2_9" / "wp06d_structural_limit_point_contract.json"


def load_contract() -> dict[str, Any]:
    """Load the machine-readable frozen contract without executing mechanics."""
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def assert_phase0_guard(*, owner_authorized: bool = False) -> None:
    """Fail closed for any attempted Phase-1 execution from this module."""
    if not owner_authorized or not STRUCTURAL_SOLVES_ENABLED or not EXTERNAL_SOLVER_ENABLED:
        raise RuntimeError(
            "WP06-D is Phase-0 preparation only: structural and external execution are disabled."
        )


def validate_contract() -> dict[str, Any]:
    """Return basic contract metadata; no mesh or solver work is performed."""
    contract = load_contract()
    required = {
        "record_id",
        "benchmark",
        "mesh_series",
        "continuation_policy",
        "reference_path",
        "failure_classifications",
        "execution_guard",
    }
    missing = sorted(required.difference(contract))
    if missing:
        raise ValueError(f"WP06-D contract is missing required sections: {missing}")
    execution_guard = contract["execution_guard"]
    if not isinstance(execution_guard, dict) or any(
        (
            execution_guard.get("structural_solves_enabled") is not False,
            execution_guard.get("external_solver_enabled") is not False,
            execution_guard.get("phase") != "PHASE_0_PREPARATION",
        )
    ):
        raise ValueError("WP06-D Phase-0 execution guard is not fail-closed.")
    return {
        "record_id": contract["record_id"],
        "mesh_levels": [row["level"] for row in contract["mesh_series"]],
        "structural_solves_enabled": STRUCTURAL_SOLVES_ENABLED,
        "external_solver_enabled": EXTERNAL_SOLVER_ENABLED,
    }


if __name__ == "__main__":
    print(json.dumps(validate_contract(), sort_keys=True))
