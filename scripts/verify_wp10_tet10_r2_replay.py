"""Fail-closed comparison of a fresh WP10 TET10 M2 replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


def _max_abs(left: Any, right: Any) -> float:
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    if a.shape != b.shape:
        return float("inf")
    return float(np.max(np.abs(a - b))) if a.size else 0.0


def _mapping_max_abs(left: Any, right: Any) -> float:
    if not isinstance(left, dict) or not isinstance(right, dict) or set(left) != set(right):
        return float("inf")
    maximum = 0.0
    for key in left:
        if isinstance(left[key], dict) or isinstance(right[key], dict):
            maximum = max(maximum, _mapping_max_abs(left[key], right[key]))
        else:
            maximum = max(maximum, _max_abs(left[key], right[key]))
    return maximum


def verify(primary: Path, replay: Path, reference: Path, output: Path) -> dict[str, object]:
    expected = json.loads(primary.read_text(encoding="utf-8"))
    actual = json.loads(replay.read_text(encoding="utf-8"))
    reference_data = json.loads(reference.read_text(encoding="utf-8"))
    expected_result = expected.get("result", {})
    actual_result = actual.get("result", {})
    comparisons = {
        "status": expected.get("status") == actual.get("status") == "PASS_CANDIDATE",
        "contract_sha256": expected.get("contract_sha256") == actual.get("contract_sha256"),
        "runner_sha": expected.get("runner_sha") == actual.get("runner_sha"),
        "displacements_max_abs": _max_abs(expected_result.get("displacements", []), actual_result.get("displacements", [])),
        "load_path_max_abs": _max_abs(
            [row.get("load_factor") for row in expected_result.get("steps", [])],
            [row.get("load_factor") for row in actual_result.get("steps", [])],
        ),
        "contact_gaps_max_abs": _max_abs(
            [row.get("contact_gaps", []) for row in expected_result.get("steps", [])],
            [row.get("contact_gaps", []) for row in actual_result.get("steps", [])],
        ),
        "active_contacts_equal": [
            row.get("contact_active_contacts", []) for row in expected_result.get("steps", [])
        ] == [
            row.get("contact_active_contacts", []) for row in actual_result.get("steps", [])
        ],
        "equilibrium_max_abs": _mapping_max_abs(expected_result.get("equilibrium", {}), actual_result.get("equilibrium", {})),
        "envelope_max_abs": _mapping_max_abs(expected_result.get("envelope", {}), actual_result.get("envelope", {})),
        "reference_pass": reference_data.get("status") == "PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION",
    }
    numeric_keys = [key for key in comparisons if key.endswith("max_abs")]
    passed = all(
        bool(value) if key not in numeric_keys else float(value) <= 1.0e-12
        for key, value in comparisons.items()
    )
    audit = {
        "status": "PASS_REPLAY" if passed else "FAIL_CLOSED",
        "primary": str(primary),
        "replay": str(replay),
        "reference": str(reference),
        "primary_execution_sha": expected.get("execution_sha"),
        "replay_execution_sha": actual.get("execution_sha"),
        "comparisons": comparisons,
        "independence_note": "Replay is a fresh production process; the reference is JSON/numpy observable recomputation, not an independent global solve.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = verify(args.primary, args.replay, args.reference, args.output)
    return 0 if audit["status"] == "PASS_REPLAY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
