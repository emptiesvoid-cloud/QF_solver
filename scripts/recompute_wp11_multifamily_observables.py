"""Independently recompute WP11 multi-family file-backed observables.

This script intentionally imports only the Python standard library and NumPy.
It does not import ``solveur`` and does not solve or assemble a FEM model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


EXPECTED_DOFS = {"TET4": 12, "HEX8": 24, "TET10": 30, "HEX20": 60}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(actual: float, declared: float) -> float:
    return abs(actual - declared) / max(abs(declared), 1.0)


def recompute(result_path: Path, contract_path: Path, output_path: Path) -> dict[str, Any]:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    family = str(result.get("element_family", "")).upper()
    case_dir = result_path.parent
    displacement = np.load(case_dir / "displacement.npy")
    stiffness = np.load(case_dir / "stiffness.npy")
    loads = np.load(case_dir / "loads.npy")
    fixed = np.load(case_dir / "fixed.npy").astype(np.int64, copy=False)
    errors: list[str] = []
    if family not in EXPECTED_DOFS:
        errors.append(f"unsupported family in result: {family!r}")
    expected_dofs = EXPECTED_DOFS.get(family)
    if expected_dofs is not None and displacement.shape != (expected_dofs,):
        errors.append(f"displacement shape {displacement.shape} != {(expected_dofs,)}")
    if stiffness.shape != (displacement.size, displacement.size):
        errors.append("stiffness shape does not match displacement")
    if loads.shape != displacement.shape:
        errors.append("loads shape does not match displacement")
    if not np.all(np.isfinite(displacement)) or not np.all(np.isfinite(stiffness)) or not np.all(np.isfinite(loads)):
        errors.append("non-finite raw numerical data")
    if np.any(fixed < 0) or np.any(fixed >= displacement.size):
        errors.append("fixed DOF index out of range")

    residual = stiffness @ displacement - loads
    mask = np.ones(displacement.size, dtype=bool)
    mask[fixed] = False
    free_residual = residual[mask]
    load_norm = max(float(np.linalg.norm(loads)), 1.0)
    observables = {
        "dof_count": int(displacement.size),
        "displacement_l2": float(np.linalg.norm(displacement)),
        "displacement_inf": float(np.max(np.abs(displacement), initial=0.0)),
        "free_residual_l2": float(np.linalg.norm(free_residual)),
        "free_residual_inf": float(np.max(np.abs(free_residual), initial=0.0)),
        "free_residual_relative_l2": float(np.linalg.norm(free_residual) / load_norm),
        "reaction_l2": float(np.linalg.norm(residual[fixed])),
        "reaction_inf": float(np.max(np.abs(residual[fixed]), initial=0.0)),
        "energy": float(0.5 * displacement @ (stiffness @ displacement)),
        "load_l2": float(np.linalg.norm(loads)),
        "fixed_dof_count": int(fixed.size),
        "finite": bool(
            np.all(np.isfinite(residual))
            and np.all(np.isfinite(displacement))
            and np.all(np.isfinite(stiffness))
        ),
    }
    declared = result.get("observables", {})
    comparisons: dict[str, float] = {}
    for key, value in observables.items():
        if key == "finite":
            if declared.get(key) is not True:
                errors.append(f"declared {key} is not true")
            continue
        if key not in declared:
            errors.append(f"declared observable missing: {key}")
            continue
        comparisons[key] = _relative(float(value), float(declared[key]))
        if comparisons[key] > 1.0e-12:
            errors.append(f"observable mismatch: {key} relative={comparisons[key]:.3e}")
    contract_sha = _sha256(contract_path)
    if result.get("contract_sha256") != contract_sha:
        errors.append("result contract SHA-256 mismatch")
    if result.get("element_family") != family:
        errors.append("family normalization mismatch")
    output = {
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "kind": "independent_observable_recomputation",
        "independent_fem_solve": False,
        "production_imports": False,
        "result_path": str(result_path),
        "result_sha256": _sha256(result_path),
        "contract_sha256": contract_sha,
        "contract_revision": contract.get("revision"),
        "element_family": family,
        "observables": observables,
        "relative_comparison_errors": comparisons,
        "errors": errors,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = recompute(args.result, args.contract, args.output)
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
