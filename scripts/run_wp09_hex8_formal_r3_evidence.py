"""Run WP09 HEX8 R3 reference, replay, and fail-closed evidence checks."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
CONTRACT_PATH = ROOT / "qualification" / "0_2_9" / "wp09_hex8_formal_r3_contract.json"
PRIMARY_DIR = ROOT / "qualification" / "0_2_9" / "wp09_hex8_formal_r3_primary"
RUNNER_PATH = ROOT / "scripts" / "run_wp09_remesh_study.py"
REFERENCE_PATH = ROOT / "scripts" / "run_wp09_independent_reference.py"
FIELDS = (
    "selected_displacement", "reaction_norm", "energy", "von_mises_max",
    "equivalent_plastic_strain_max", "free_relative_residual",
    "force_balance_relative_error", "moment_balance_relative_error",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().lower()


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def _relative(left: float, right: float) -> float:
    return abs(left - right) / max(abs(left), abs(right), 1.0e-14)


def _finite(value: Any) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _load_runner_module():
    spec = importlib.util.spec_from_file_location("wp09_remesh_runner_r3", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load runner module: {RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _primary_rows(contract: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    expected_contract = _sha256(CONTRACT_PATH)
    policy = contract["policy"]
    rows: dict[str, Any] = {}
    failures: list[str] = []
    for level in contract["mesh_hierarchy"]["levels"]:
        stage = level["stage"]
        path = PRIMARY_DIR / level["raw_filename"]
        if not path.exists():
            failures.append(f"{stage}:missing_raw")
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        metrics = raw.get("metrics", {})
        expected = {
            "contract_sha256": expected_contract,
            "policy_code_digest": policy["frozen_policy_code_digest"],
            "runtime_policy_digest": policy["runtime_policy_binding_digest"],
        }
        for key, value in expected.items():
            if raw.get(key) != value:
                failures.append(f"{stage}:{key}_mismatch")
        if raw.get("classification") != "PROSPECTIVE_PRIMARY_EVIDENCE":
            failures.append(f"{stage}:classification")
        if _sha256(path) != _campaign_hash(stage):
            failures.append(f"{stage}:manifest_hash_mismatch")
        for field in FIELDS:
            if not _finite(metrics.get(field)):
                failures.append(f"{stage}:nonfinite:{field}")
        if metrics.get("status") != "PASS":
            failures.append(f"{stage}:status")
        if metrics.get("accepted_steps") != contract["path"]["load_steps"]:
            failures.append(f"{stage}:accepted_steps")
        if metrics.get("rejected_increments") != 0:
            failures.append(f"{stage}:rejected_increments")
        if metrics.get("max_local_strain_norm", float("inf")) > contract["gates"]["maximum_local_strain_norm"]:
            failures.append(f"{stage}:strain_envelope")
        if metrics.get("free_relative_residual", float("inf")) > contract["gates"]["free_residual_relative_max"]:
            failures.append(f"{stage}:free_residual")
        if metrics.get("force_balance_relative_error", float("inf")) > contract["gates"]["force_equilibrium_relative_max"]:
            failures.append(f"{stage}:force_equilibrium")
        if metrics.get("moment_balance_relative_error", float("inf")) > contract["gates"]["moment_equilibrium_relative_max"]:
            failures.append(f"{stage}:moment_equilibrium")
        rows[stage] = {"path": str(path), "sha256": _sha256(path), "metrics": metrics}
    return rows, failures


def _campaign_hash(stage: str) -> str:
    campaign = json.loads((PRIMARY_DIR / "campaign.json").read_text(encoding="utf-8"))
    return campaign["stages"][stage]["sha256"].lower()


def _run_reference(output: Path) -> dict[str, Any]:
    reference_output = output / "independent_reference"
    completed = subprocess.run(
        [sys.executable, str(REFERENCE_PATH), "--rotation-deg", "50", "--output", str(reference_output)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    (output / "independent_reference_stdout.log").write_text(completed.stdout, encoding="utf-8")
    (output / "independent_reference_stderr.log").write_text(completed.stderr, encoding="utf-8")
    summary_path = reference_output / "summary.json"
    if not summary_path.exists():
        return {"status": "FAIL_CLOSED_MISSING_SUMMARY", "return_code": completed.returncode}
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    hex8 = next((row for row in summary.get("families", []) if row.get("family") == "HEX8"), None)
    module_path = ROOT / "src" / "solveur" / "verification" / "wp09_independent_reference.py"
    module_text = module_path.read_text(encoding="utf-8")
    independent_module = all(name not in module_text for name in ("solveur.elements", "solveur.materials", "solveur.core"))
    status = "PASS_INDEPENDENT_REFERENCE" if completed.returncode == 0 and hex8 and hex8.get("status") == "PASS" and independent_module else "FAIL_CLOSED_INDEPENDENT_REFERENCE"
    return {
        "status": status, "return_code": completed.returncode, "summary_path": str(summary_path),
        "summary_sha256": _sha256(summary_path), "module_sha256": _sha256(module_path),
        "module_independence_check": "PASS" if independent_module else "FAIL", "hex8": hex8,
        "excluded_families": [row.get("family") for row in summary.get("families", []) if row.get("family") != "HEX8"],
    }


def _run_replay(output: Path, contract: dict[str, Any], primary: dict[str, Any]) -> dict[str, Any]:
    module = _load_runner_module()
    from solveur.api import solve_model

    replay_dir = output / "replay"
    replay_dir.mkdir(parents=True, exist_ok=True)
    contract_sha = _sha256(CONTRACT_PATH)
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for level in contract["mesh_hierarchy"]["levels"]:
        stage = level["stage"]
        started = time.perf_counter()
        model = module._model("HEX8", int(level["cells"]))
        result = solve_model(model, enforce_policy=True)
        metrics = module._metrics(result, time.perf_counter() - started)
        reference_metrics = primary[stage]["metrics"]
        checks = {field: _relative(float(reference_metrics[field]), float(metrics[field])) for field in FIELDS}
        passed = metrics.get("status") == "PASS" and all(value <= contract["gates"]["replay_relative_tolerance"] for value in checks.values())
        if not passed:
            failures.append(f"{stage}:replay_mismatch")
        replay_path = replay_dir / f"{stage.lower()}_hex8.json"
        # Do not serialize the full production audit here.  On these meshes it
        # is an exhaustive forensic object and can turn a replay artifact into
        # hundreds of megabytes or an apparent I/O hang.  The replay contract
        # requires the raw observables, provenance, and comparison checks; the
        # primary run retains the full audit separately.
        payload = {
            "classification": "PROSPECTIVE_DETERMINISTIC_REPLAY", "stage": stage, "family": "HEX8", "cells": level["cells"],
            "contract_sha256": contract_sha, "policy_code_digest": contract["policy"]["frozen_policy_code_digest"],
            "runtime_policy_digest": contract["policy"]["runtime_policy_binding_digest"], "execution_sha": _git("rev-parse", "HEAD"),
            "primary_raw_sha256": primary[stage]["sha256"], "metrics": metrics, "checks": checks,
            "status": "PASS" if passed else "FAIL_CLOSED", "displacements": np.asarray(result.displacements, dtype=float),
            "solver": result.solver,
            "audit_export": "COMPACT_REPLAY; full audit retained only in primary evidence",
        }
        replay_path.write_text(json.dumps(payload, indent=2, default=_json_default, allow_nan=False), encoding="utf-8")
        rows.append({"stage": stage, "path": str(replay_path), "sha256": _sha256(replay_path), "checks": checks, "status": payload["status"]})
    return {"status": "PASS" if not failures else "FAIL_CLOSED", "failures": failures, "rows": rows}


def _mesh_gate(contract: dict[str, Any], primary: dict[str, Any]) -> dict[str, Any]:
    middle, fine = primary["M2"]["metrics"], primary["M3"]["metrics"]
    names = {"selected_displacement": "selected_displacement_relative_max", "reaction_norm": "reaction_relative_max", "energy": "energy_relative_max", "von_mises_max": "von_mises_relative_max"}
    deltas = {name: _relative(float(middle[name]), float(fine[name])) for name in names}
    failures = [name for name, value in deltas.items() if value > contract["gates"]["mesh_comparison"][names[name]]]
    return {"status": "PASS" if not failures else "FAIL_CLOSED", "deltas": deltas, "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "qualification" / "0_2_9" / "wp09_hex8_formal_r3_evidence")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    primary, primary_failures = _primary_rows(contract)
    reference = _run_reference(output)
    replay = _run_replay(output, contract, primary) if not primary_failures else {"status": "SKIPPED_DEPENDENCY", "failures": []}
    mesh = _mesh_gate(contract, primary) if not primary_failures else {"status": "SKIPPED_DEPENDENCY"}
    status = "PASS_CANDIDATE" if not primary_failures and reference["status"] == "PASS_INDEPENDENT_REFERENCE" and replay["status"] == "PASS" and mesh["status"] == "PASS" else "FAIL_CLOSED"
    campaign = {
        "status": status, "classification": "HEX8_FORMAL_PROSPECTIVE_R3_CANDIDATE_NO_POINTS", "contract_path": str(CONTRACT_PATH),
        "contract_sha256": _sha256(CONTRACT_PATH), "branch": _git("branch", "--show-current"), "execution_sha": _git("rev-parse", "HEAD"),
        "primary_evidence": primary, "primary_failures": primary_failures, "independent_reference": reference, "replay": replay,
        "mesh_gate_m2_to_m3": mesh, "formal_points": "0/8", "code_aster_status": "NOT_EXECUTED_NOT_REQUIRED_INTERNAL_GATE",
        "production_mechanics_changed_from_r2": False, "thresholds_changed": False,
    }
    (output / "campaign.json").write_text(json.dumps(campaign, indent=2, default=_json_default, allow_nan=False), encoding="utf-8")
    files = [{"path": str(path.relative_to(output)), "sha256": _sha256(path), "bytes": path.stat().st_size} for path in sorted(output.rglob("*")) if path.is_file() and path.name != "manifest.json"]
    (output / "manifest.json").write_text(json.dumps({"schema_version": 1, "contract_sha256": _sha256(CONTRACT_PATH), "files": files}, indent=2), encoding="utf-8")
    report = [
        "# WP09 HEX8 R3 reference and replay evidence", "", f"Status: `{status}`", f"Branch: `{campaign['branch']}`",
        f"Execution SHA: `{campaign['execution_sha']}`", f"Contract SHA-256: `{campaign['contract_sha256']}`", "",
        "Primary H7/H8/H9 artifacts were executed after the R3 contract freeze and embed contract, code-policy, and runtime-policy digests.",
        "The independent reference is a NumPy material-point/affine-element recomputation; it is not an independent global FEM/Newton solve.",
        "Code_Aster was not executed and is not required for this internal gate; external correlation remains out of scope.", "",
        f"Independent reference: `{reference['status']}`", f"Replay: `{replay['status']}`", f"Mesh gate M2→M3: `{mesh['status']}`", "",
        "Formal points remain `0/8` pending Owner review.",
    ]
    (output / "campaign.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "reference": reference["status"], "replay": replay["status"], "mesh": mesh["status"]}, indent=2))
    return 0 if status == "PASS_CANDIDATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
