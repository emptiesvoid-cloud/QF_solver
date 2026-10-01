"""Run the bounded WP09 HEX20 extension study (H20-1/H20-2/H20-3)."""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from solveur.api import solve_model  # noqa: E402
from solveur.mesh.validation import MeshValidator  # noqa: E402
from solveur.verification.robustness_mesh import _refinement_model  # noqa: E402


CONTRACT_PATH = ROOT / "qualification" / "0_2_9" / "wp09_hex20_extension_contract.json"
DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_9" / "wp09_hex20_extension"
FAMILY = "HEX20"
STAGES = (("H1", 1), ("H2", 2), ("H3", 3))
LOAD_SCALE = 0.25
LOAD_PATH = (0.25, 0.5, 0.75, 1.0)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else "UNAVAILABLE"


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def _finite(value: Any) -> bool:
    try:
        return bool(np.isfinite(np.asarray(value, dtype=float)).all())
    except (TypeError, ValueError):
        return False


def _relative(left: float, right: float) -> float:
    return abs(left - right) / max(abs(left), abs(right), 1.0e-14)


def _model(cells: int, *, load_scale: float = LOAD_SCALE):
    model = _refinement_model(FAMILY, cells)
    parameters = dict(model.analysis.parameters)
    parameters.update(
        {
            "kinematics": "corotational_j2",
            "load_steps": len(LOAD_PATH),
            "load_path": list(LOAD_PATH),
            "max_iterations": 40,
            "tolerance": 1.0e-9,
            "corotational_max_local_strain": 0.05,
            "adaptive_load_steps": False,
        }
    )
    return replace(
        model,
        loads=[replace(load, value=float(load.value) * load_scale) for load in model.loads],
        analysis=replace(model.analysis, parameters=parameters),
    )


def _equilibrium(result: Any) -> dict[str, Any]:
    audit = result.audit.equilibrium if result.audit is not None else {}
    return {
        "free_relative_residual": float(audit.get("free_relative_residual", float("nan"))),
        "force_balance_relative_error": float(audit.get("force_balance_relative_error", float("nan"))),
        "moment_balance_relative_error": float(audit.get("moment_balance_relative_error", float("nan"))),
        "reaction_resultant": [float(value) for value in audit.get("reaction_resultant", ())],
        "reaction_moment": [float(value) for value in audit.get("reaction_moment", ())],
    }


def _metrics(result: Any, elapsed_seconds: float) -> dict[str, Any]:
    steps = list(result.solver.get("steps", []))
    points = [point for element in result.element_results for point in element.get("integration_points", [])]
    states = [state for values in result.material_states.values() for state in values]
    equilibrium = _equilibrium(result)
    return {
        "status": str(result.status),
        "run_verdict": getattr(getattr(result, "run_verdict", None), "value", "UNAVAILABLE"),
        "node_count": int(result.node_count),
        "element_count": int(result.element_count),
        "dof_count": int(result.displacements.size),
        "selected_displacement": float(np.max(np.abs(result.displacements))),
        "displacement_norm": float(np.linalg.norm(result.displacements)),
        "reaction_norm": float(np.linalg.norm(equilibrium["reaction_resultant"])),
        "energy": float(sum(float(step.get("incremental_internal_work", 0.0)) for step in steps)),
        "von_mises_max": max((float(element.get("von_mises", 0.0)) for element in result.element_results), default=0.0),
        "equivalent_plastic_strain_max": max((float(state.get("equivalent_plastic_strain", 0.0)) for state in states), default=0.0),
        "plastic_dissipation_max": max((float(state.get("plastic_dissipation", 0.0)) for state in states), default=0.0),
        "min_det_f": min((float(point["det_f"]) for point in points if "det_f" in point), default=float("nan")),
        "max_local_strain_norm": max((float(point["corotational_strain_norm"]) for point in points if "corotational_strain_norm" in point), default=float("nan")),
        "accepted_steps": len(steps) if str(result.status) == "PASS" else 0,
        "step_count": len(steps),
        "newton_iterations": int(sum(int(step.get("iterations", 0)) for step in steps)),
        "rejected_increments": int(result.solver.get("rejected_increments", 0)),
        "fallback_count": int(result.solver.get("fallback_count", 0)),
        "elapsed_seconds": elapsed_seconds,
        "equilibrium": equilibrium,
    }


def _run_one(cells: int, output: Path, label: str) -> dict[str, Any]:
    started = time.perf_counter()
    raw_path = output / f"{label.lower()}_hex20.json"
    try:
        model = _model(cells)
        quality = MeshValidator().validate(model)
        result = solve_model(model, enforce_policy=True)
        metrics = _metrics(result, time.perf_counter() - started)
        raw = {
            "family": FAMILY,
            "stage": label,
            "cells": cells,
            "contract_path": str(CONTRACT_PATH),
            "contract_sha256": _sha256(CONTRACT_PATH),
            "source_sha": _git("rev-parse", "HEAD"),
            "policy_code_digest": "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac",
            "mesh_quality": quality.to_dict(),
            "metrics": metrics,
            "observable_source": {
                "displacements": result.to_dict()["displacements"],
                "solver_steps": result.solver.get("steps", []),
                "element_results": result.element_results,
                "material_states": result.material_states,
                "equilibrium": _equilibrium(result),
            },
            "result": result.to_dict(),
        }
        raw_path.write_text(json.dumps(raw, indent=2, default=_json_default, allow_nan=False), encoding="utf-8")
        return {"raw_path": str(raw_path), **metrics, "stage": label, "cells": cells}
    except Exception as exc:  # noqa: BLE001 - preserve a diagnostic failure.
        failure = {
            "family": FAMILY,
            "stage": label,
            "cells": cells,
            "source_sha": _git("rev-parse", "HEAD"),
            "status": "FAIL_EXCEPTION",
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "elapsed_seconds": time.perf_counter() - started,
        }
        raw_path.write_text(json.dumps(failure, indent=2), encoding="utf-8")
        return failure


def _structural_gate(row: dict[str, Any], contract: dict[str, Any]) -> tuple[bool, list[str]]:
    gates = contract["gates"]
    failures: list[str] = []
    if row.get("status") != gates["production_status"]:
        failures.append("production_status")
    for name in ("selected_displacement", "reaction_norm", "energy", "von_mises_max", "min_det_f", "max_local_strain_norm"):
        if not _finite(row.get(name)):
            failures.append(f"nonfinite:{name}")
    equilibrium = row.get("equilibrium", {})
    for name, limit in (
        ("free_relative_residual", gates["free_residual_relative_max"]),
        ("force_balance_relative_error", gates["force_equilibrium_relative_max"]),
        ("moment_balance_relative_error", gates["moment_equilibrium_relative_max"]),
    ):
        value = equilibrium.get(name, float("nan"))
        if not _finite(value) or float(value) > limit:
            failures.append(name)
    if float(row.get("min_det_f", -float("inf"))) < gates["minimum_det_f"]:
        failures.append("det_f_envelope")
    if float(row.get("max_local_strain_norm", float("inf"))) > gates["maximum_local_strain_norm"]:
        failures.append("local_strain_envelope")
    if int(row.get("accepted_steps", -1)) != contract["path"]["load_steps"]:
        failures.append("accepted_steps")
    if int(row.get("rejected_increments", -1)) != 0:
        failures.append("rejected_increments")
    if int(row.get("fallback_count", -1)) != 0:
        failures.append("fallback_count")
    return not failures, failures


def _mesh_gate(coarse: dict[str, Any], fine: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    thresholds = contract["gates"]["mesh_comparison"]
    deltas = {
        "selected_displacement": _relative(coarse["selected_displacement"], fine["selected_displacement"]),
        "reaction": _relative(coarse["reaction_norm"], fine["reaction_norm"]),
        "energy": _relative(coarse["energy"], fine["energy"]),
        "von_mises": _relative(coarse["von_mises_max"], fine["von_mises_max"]),
    }
    failures = [name for name, value in deltas.items() if value > thresholds[f"{name}_relative_max"]]
    return {"status": "PASS" if not failures else "FAIL_CLOSED", "deltas": deltas, "failures": failures}


def _replay(primary: dict[str, Any], replay: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    names = ("selected_displacement", "reaction_norm", "energy", "von_mises_max", "equivalent_plastic_strain_max")
    checks = {name: _relative(float(primary[name]), float(replay[name])) for name in names}
    tolerance = contract["gates"]["replay_relative_tolerance"]
    return {"status": "PASS" if all(value <= tolerance for value in checks.values()) else "FAIL_CLOSED", "relative_errors": checks}


def _manifest(output: Path, campaign: dict[str, Any]) -> dict[str, Any]:
    files = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name not in {"campaign.json", "manifest.json"}:
            files.append({"path": str(path.relative_to(output)), "sha256": _sha256(path), "bytes": path.stat().st_size})
    manifest = {"schema_version": 1, "contract_sha256": campaign["contract_sha256"], "source_sha": campaign["source_sha"], "files": files}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifest_sha256"] = _sha256(output / "manifest.json")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    campaign: dict[str, Any] = {
        "status": "RUNNING",
        "study": "WP09 HEX20 extension",
        "contract_path": str(CONTRACT_PATH),
        "contract_sha256": _sha256(CONTRACT_PATH),
        "branch": _git("branch", "--show-current"),
        "source_sha": _git("rev-parse", "HEAD"),
        "policy_code_digest": contract["policy"]["frozen_policy_code_digest"],
        "working_tree_at_start": _git("status", "--short"),
        "machine": {"platform": platform.platform(), "python": platform.python_version()},
        "stages": {},
        "formal_points": "0/pending",
    }
    primaries: dict[str, dict[str, Any]] = {}
    replays: dict[str, dict[str, Any]] = {}
    for stage, cells in STAGES:
        primary = _run_one(cells, output, stage)
        primaries[stage] = primary
        passed, failures = _structural_gate(primary, contract)
        replay = _run_one(cells, output, f"{stage}_replay") if passed else {"status": "SKIPPED_DEPENDENCY"}
        if passed:
            replays[stage] = replay
        replay_gate = _replay(primary, replay, contract) if passed else {"status": "SKIPPED_DEPENDENCY"}
        campaign["stages"][stage] = {
            "status": "PASS" if passed and replay_gate["status"] == "PASS" else "FAIL_CLOSED",
            "cells": cells,
            "primary": primary,
            "structural_gate": {"status": "PASS" if passed else "FAIL_CLOSED", "failures": failures},
            "replay": replay_gate,
        }
        if campaign["stages"][stage]["status"] != "PASS":
            break
    if all(campaign["stages"].get(stage, {}).get("status") == "PASS" for stage, _ in STAGES):
        campaign["mesh_gate_h2_to_h3"] = _mesh_gate(primaries["H2"], primaries["H3"], contract)
    else:
        campaign["mesh_gate_h2_to_h3"] = {"status": "SKIPPED_DEPENDENCY"}
    reference_command = [
        sys.executable,
        str(ROOT / "scripts" / "run_wp09_hex20_extension_reference.py"),
        "--input",
        str(output),
        "--output",
        str(output / "independent_reference"),
    ]
    completed = subprocess.run(reference_command, cwd=ROOT, capture_output=True, text=True, check=False)
    (output / "reference_stdout.log").write_text(completed.stdout, encoding="utf-8")
    (output / "reference_stderr.log").write_text(completed.stderr, encoding="utf-8")
    reference_path = output / "independent_reference" / "summary.json"
    reference = json.loads(reference_path.read_text(encoding="utf-8")) if reference_path.exists() else {"status": "FAIL_CLOSED_MISSING_SUMMARY"}
    campaign["independent_reference"] = reference
    campaign["status"] = "PASS_CANDIDATE" if campaign["mesh_gate_h2_to_h3"]["status"] == "PASS" and reference.get("status") == "PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION" else "FAIL_CLOSED"
    campaign["working_tree_at_end"] = _git("status", "--short")
    (output / "campaign.json").write_text(json.dumps(campaign, indent=2, default=_json_default, allow_nan=False), encoding="utf-8")
    manifest = _manifest(output, campaign)
    campaign["manifest"] = manifest
    campaign["artifact_count"] = len(manifest["files"])
    (output / "campaign.json").write_text(json.dumps(campaign, indent=2, default=_json_default, allow_nan=False), encoding="utf-8")
    lines = [
        "# WP09 HEX20 extension study",
        "",
        f"Status: `{campaign['status']}`",
        f"Branch: `{campaign['branch']}`",
        f"Source SHA: `{campaign['source_sha']}`",
        f"Contract SHA-256: `{campaign['contract_sha256']}`",
        "",
        "| Stage | Cells | Status |",
        "|---|---:|---|",
    ]
    for stage, cells in STAGES:
        lines.append(f"| {stage} | {cells} | {campaign['stages'].get(stage, {}).get('status', 'NOT_RUN')} |")
    lines.extend([
        "",
        f"Mesh gate H2→H3: `{campaign['mesh_gate_h2_to_h3']['status']}`",
        f"Independent observables: `{reference.get('status', 'UNKNOWN')}`",
        "",
        "This is a HEX20-only bounded extension study. It does not change the accepted HEX8 WP09 score and does not award formal points.",
        "",
        "The independent check recomputes observables from raw JSON evidence; it is not an independent global FEM/Newton solve.",
    ])
    (output / "campaign.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": campaign["status"], "stages": campaign["stages"], "mesh_gate": campaign["mesh_gate_h2_to_h3"], "reference": reference.get("status")}, indent=2))
    return 0 if campaign["status"] == "PASS_CANDIDATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
