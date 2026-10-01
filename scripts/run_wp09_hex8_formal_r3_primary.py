"""Run prospective WP09 HEX8 R3 primary evidence.

The contract is frozen and committed before this runner is invoked. Every raw
primary artifact embeds the contract SHA-256 and both policy digests.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

CONTRACT_PATH = ROOT / "qualification" / "0_2_9" / "wp09_hex8_formal_r3_contract.json"
RUNNER_HELPER = ROOT / "scripts" / "run_wp09_remesh_study.py"
STAGES = (("M1", 7), ("M2", 8), ("M3", 9))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def _load_helper():
    spec = importlib.util.spec_from_file_location("wp09_strict_helper", RUNNER_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load helper: {RUNNER_HELPER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "qualification" / "0_2_9" / "wp09_hex8_formal_r3_primary")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    contract_sha = _sha256(CONTRACT_PATH)
    helper = _load_helper()
    from solveur.api import solve_model

    campaign: dict[str, Any] = {
        "status": "RUNNING",
        "classification": "PROSPECTIVE_PRIMARY_EVIDENCE",
        "contract_path": str(CONTRACT_PATH),
        "contract_sha256": contract_sha,
        "execution_sha": _git("rev-parse", "HEAD"),
        "branch": _git("branch", "--show-current"),
        "governing_base_sha": contract["governing_base_sha"],
        "policy": contract["policy"],
        "machine": {"platform": platform.platform(), "python": platform.python_version()},
        "working_tree_at_start": _git("status", "--short"),
        "stages": {},
        "formal_points": "0/8",
    }
    all_pass = True
    for stage, cells in STAGES:
        started = time.perf_counter()
        raw_path = output / {"M1": "m1_hex8.json", "M2": "m2_hex8.json", "M3": "m3_hex8.json"}[stage]
        try:
            model = helper._model("HEX8", cells)
            result = solve_model(model, enforce_policy=True)
            metrics = helper._metrics(result, time.perf_counter() - started)
            raw = {
                "schema_version": 1,
                "classification": "PROSPECTIVE_PRIMARY_EVIDENCE",
                "stage": stage,
                "family": "HEX8",
                "cells": cells,
                "contract_sha256": contract_sha,
                "policy_code_digest": contract["policy"]["frozen_policy_code_digest"],
                "runtime_policy_digest": contract["policy"]["runtime_policy_binding_digest"],
                "governing_base_sha": contract["governing_base_sha"],
                "execution_sha": _git("rev-parse", "HEAD"),
                "branch": _git("branch", "--show-current"),
                "metrics": metrics,
                "displacements": np.asarray(result.displacements, dtype=float),
                "solver": result.solver,
                "audit": result.audit.to_dict() if result.audit is not None else {},
            }
            raw_path.write_text(json.dumps(raw, indent=2, default=_json_default, allow_nan=False), encoding="utf-8")
            stage_status = "PASS" if metrics.get("status") == "PASS" else "FAIL_CLOSED"
            campaign["stages"][stage] = {
                "status": stage_status,
                "path": str(raw_path),
                "sha256": _sha256(raw_path),
                "metrics": metrics,
            }
        except Exception as exc:  # noqa: BLE001 - record and stop fail-closed.
            all_pass = False
            raw_path.write_text(
                json.dumps(
                    {
                        "classification": "PROSPECTIVE_PRIMARY_EVIDENCE",
                        "stage": stage,
                        "contract_sha256": contract_sha,
                        "policy_code_digest": contract["policy"]["frozen_policy_code_digest"],
                        "runtime_policy_digest": contract["policy"]["runtime_policy_binding_digest"],
                        "execution_sha": _git("rev-parse", "HEAD"),
                        "status": "FAIL_EXCEPTION",
                        "exception_type": type(exc).__name__,
                        "exception": str(exc),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            campaign["stages"][stage] = {"status": "FAIL_EXCEPTION", "path": str(raw_path), "sha256": _sha256(raw_path)}
            break
        if campaign["stages"][stage]["status"] != "PASS":
            all_pass = False
            break
    campaign["status"] = "PASS_PRIMARY_CANDIDATE" if all_pass and len(campaign["stages"]) == 3 else "FAIL_CLOSED"
    campaign["working_tree_at_end"] = _git("status", "--short")
    (output / "campaign.json").write_text(json.dumps(campaign, indent=2, default=_json_default, allow_nan=False), encoding="utf-8")
    files = []
    for path in sorted(output.glob("*.json")):
        if path.name == "manifest.json":
            continue
        files.append({"path": path.name, "sha256": _sha256(path), "bytes": path.stat().st_size})
    (output / "manifest.json").write_text(json.dumps({"schema_version": 1, "contract_sha256": contract_sha, "files": files}, indent=2), encoding="utf-8")
    (output / "report.md").write_text(
        "\n".join(
            [
                "# WP09 HEX8 R3 prospective primary evidence",
                "",
                f"Status: `{campaign['status']}`",
                f"Contract SHA-256: `{contract_sha}`",
                f"Execution SHA: `{campaign['execution_sha']}`",
                "",
                "Every primary artifact embeds the contract SHA-256 and both policy digests.",
                "Formal points remain `0/8` pending reference, replay and Owner review.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": campaign["status"], "contract_sha256": contract_sha, "stages": campaign["stages"]}, indent=2, default=_json_default))
    return 0 if campaign["status"] == "PASS_PRIMARY_CANDIDATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
