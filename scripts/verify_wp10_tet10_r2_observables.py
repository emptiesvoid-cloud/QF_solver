"""JSON-only independent observable reference for WP10 TET10 R2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


def verify(primary: Path, contract_path: Path, output: Path) -> dict[str, object]:
    record = json.loads(primary.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    result = record.get("result", {})
    displacement = np.asarray(result.get("displacements", []), dtype=float)
    rows: list[dict[str, object]] = []
    finite = bool(displacement.size and np.all(np.isfinite(displacement)))
    load_balance = record.get("load_balance", {})
    load_error = float(load_balance.get("resultant_error_norm", float("inf")))
    mode = str(record.get("mode", record.get("case", ""))).upper()
    if mode == "M1":
        for step in result.get("steps", []):
            active = list(step.get("contact_active_contacts", []))
            rows.append({"step": step.get("step"), "expected_active": False, "observed_active": bool(active)})
        contact_ok = all(not bool(row["observed_active"]) for row in rows)
        passed = record.get("status") == "PASS_CANDIDATE" and finite and load_error <= 1.0e-12 and contact_ok
    elif mode == "M2":
        contact = record.get("surface_load", {}).get("contact", {})
        plane_x = float(contract["m2"]["plane_x"])
        penalty = float(contract["m2"]["penalty"])
        slave_dof = int(result["slave_ux_dof"])
        slave_x = float(contact.get("slave_x_reference", 1.0))
        gap = slave_x + float(displacement[slave_dof]) - plane_x
        steps = result.get("steps", [])
        production_gap = float(steps[-1].get("contact_gaps", [float("nan")])[0]) if steps else float("nan")
        observed_active = bool(steps[-1].get("contact_active_contacts", [])) if steps else False
        expected_active = gap < 0.0
        rows.append({
            "step": steps[-1].get("step") if steps else None,
            "recomputed_gap": gap,
            "production_gap": production_gap,
            "gap_absolute_error": abs(gap - production_gap),
            "recomputed_penalty_force": max(-gap, 0.0) * penalty,
            "expected_active": expected_active,
            "observed_active": observed_active,
        })
        passed = (
            record.get("status") == "PASS_CANDIDATE"
            and finite
            and load_error <= 1.0e-12
            and abs(gap - production_gap) <= 1.0e-12
            and expected_active == observed_active
        )
    else:
        raise ValueError(f"Unsupported reference mode {mode!r}.")
    reference: dict[str, object] = {
        "status": "PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION" if passed else "FAIL_CLOSED",
        "mode": mode,
        "level": record.get("level"),
        "source_sha": record.get("execution_sha"),
        "runner_sha": record.get("runner_sha"),
        "contract_sha256": record.get("contract_sha256"),
        "element_type": "TET10",
        "independence": "JSON/numpy observable recomputation only; no production contact or FEM/Newton import",
        "coverage": "finite displacements, integrated load resultant, and final contact gap/active state for M2",
        "finite_displacements": finite,
        "load_resultant_error_norm": load_error,
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(reference, indent=2), encoding="utf-8")
    return reference


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reference = verify(args.primary, args.contract, args.output)
    return 0 if reference["status"] == "PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
