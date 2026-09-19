"""Run the frozen WP09 corotational M1/M2/M3 requalification campaign."""

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
from solveur.verification.robustness_mesh import _refinement_model  # noqa: E402


CONTRACT_PATH = ROOT / "qualification" / "0_2_9" / "wp09_formal_requalification_contract.json"
DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_9" / "wp09_formal_requalification_r1"
STAGES = ("M1", "M2", "M3")
FAMILIES = ("TET4", "HEX8")
LOAD_PATH = (0.25, 0.5, 0.75, 1.0)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"


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


def _analysis_model(family: str, cells: int):
    model = _refinement_model(family, cells)
    parameters = dict(model.analysis.parameters)
    parameters.update(
        {
            "kinematics": "corotational_j2",
            "load_steps": len(LOAD_PATH),
            "load_path": list(LOAD_PATH),
            "max_iterations": 40,
            "tolerance": 1.0e-7,
            "corotational_max_local_strain": 0.05,
            "adaptive_load_steps": False,
        }
    )
    return replace(model, analysis=replace(model.analysis, parameters=parameters))


def _equilibrium(result: Any) -> dict[str, Any]:
    audit = result.audit.equilibrium if result.audit is not None else {}
    return {
        "free_relative_residual": float(audit.get("free_relative_residual", float("nan"))),
        "force_balance_relative_error": float(
            audit.get("force_balance_relative_error", float("nan"))
        ),
        "moment_balance_relative_error": float(
            audit.get("moment_balance_relative_error", float("nan"))
        ),
        "reaction_resultant": [float(value) for value in audit.get("reaction_resultant", ())],
        "reaction_moment": [float(value) for value in audit.get("reaction_moment", ())],
    }


def _metrics(result: Any, *, elapsed_seconds: float) -> dict[str, Any]:
    steps = list(result.solver.get("steps", []))
    point_rows = [
        point
        for element in result.element_results
        for point in element.get("integration_points", [])
    ]
    det_values = [float(point["det_f"]) for point in point_rows if "det_f" in point]
    local_strain_values = [
        float(point["corotational_strain_norm"])
        for point in point_rows
        if "corotational_strain_norm" in point
    ]
    stress_values = [
        float(element.get("von_mises", 0.0))
        for element in result.element_results
        if "von_mises" in element
    ]
    plastic_values = [
        float(state.get("equivalent_plastic_strain", 0.0))
        for states in result.material_states.values()
        for state in states
    ]
    dissipation_values = [
        float(state.get("plastic_dissipation", 0.0))
        for states in result.material_states.values()
        for state in states
    ]
    energy = sum(float(step.get("incremental_internal_work", 0.0)) for step in steps)
    if not energy:
        energy = sum(float(element.get("strain_energy", 0.0)) for element in result.element_results)
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
        "reaction_resultant": equilibrium["reaction_resultant"],
        "reaction_moment": equilibrium["reaction_moment"],
        "energy": float(energy),
        "von_mises_max": max(stress_values, default=0.0),
        "equivalent_plastic_strain_max": max(plastic_values, default=0.0),
        "plastic_dissipation_max": max(dissipation_values, default=0.0),
        "min_det_f": min(det_values, default=float("nan")),
        "max_local_strain_norm": max(local_strain_values, default=float("nan")),
        # Solver history entries are accepted once the result is PASS; the
        # serialized step DTO intentionally has no status/accepted flag.
        "accepted_steps": len(steps) if str(result.status) == "PASS" else 0,
        "step_count": len(steps),
        "newton_iterations": sum(int(step.get("iterations", 0)) for step in steps),
        "rejected_increments": int(result.solver.get("rejected_increments", 0)),
        "fallback_count": int(result.solver.get("fallback_count", 0)),
        "elapsed_seconds": elapsed_seconds,
        "equilibrium": equilibrium,
    }


def _run_one(family: str, cells: int, output: Path, label: str) -> dict[str, Any]:
    started = time.perf_counter()
    raw_path = output / f"{label}_{family.lower()}_{cells}.json"
    try:
        model = _analysis_model(family, cells)
        result = solve_model(model, enforce_policy=True)
        metrics = _metrics(result, elapsed_seconds=time.perf_counter() - started)
        raw = {
            "family": family,
            "cells": cells,
            "label": label,
            "execution_sha": _git("rev-parse", "HEAD"),
            "metrics": metrics,
            "result": result.to_dict(),
        }
        raw_path.write_text(
            json.dumps(raw, indent=2, default=_json_default, allow_nan=False),
            encoding="utf-8",
        )
        return {"family": family, "cells": cells, "label": label, "raw_path": str(raw_path), **metrics}
    except Exception as exc:  # noqa: BLE001 - failure is recorded fail-closed.
        failure = {
            "family": family,
            "cells": cells,
            "label": label,
            "execution_sha": _git("rev-parse", "HEAD"),
            "status": "FAIL_EXCEPTION",
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "elapsed_seconds": time.perf_counter() - started,
        }
        raw_path.write_text(json.dumps(failure, indent=2), encoding="utf-8")
        return failure


def _structural_gate(row: dict[str, Any], contract: dict[str, Any]) -> tuple[bool, list[str]]:
    gates = contract["gates"]
    errors: list[str] = []
    if row.get("status") != gates["production_status"]:
        errors.append("production_status")
    for name in (
        "selected_displacement",
        "reaction_norm",
        "energy",
        "von_mises_max",
        "equivalent_plastic_strain_max",
        "plastic_dissipation_max",
        "min_det_f",
        "max_local_strain_norm",
    ):
        if not _finite(row.get(name)):
            errors.append(f"nonfinite:{name}")
    equilibrium = row.get("equilibrium", {})
    if not _finite(equilibrium.get("free_relative_residual")):
        errors.append("nonfinite:free_relative_residual")
    if not _finite(equilibrium.get("force_balance_relative_error")):
        errors.append("nonfinite:force_equilibrium")
    if not _finite(equilibrium.get("moment_balance_relative_error")):
        errors.append("nonfinite:moment_equilibrium")
    if float(equilibrium.get("free_relative_residual", float("inf"))) > gates["free_residual_relative_max"]:
        errors.append("free_residual")
    if float(equilibrium.get("force_balance_relative_error", float("inf"))) > gates["force_equilibrium_relative_max"]:
        errors.append("force_equilibrium")
    if float(equilibrium.get("moment_balance_relative_error", float("inf"))) > gates["moment_equilibrium_relative_max"]:
        errors.append("moment_equilibrium")
    if float(row.get("min_det_f", -float("inf"))) < gates["minimum_det_f"]:
        errors.append("det_f_envelope")
    if float(row.get("max_local_strain_norm", float("inf"))) > gates["maximum_local_strain_norm"]:
        errors.append("local_strain_envelope")
    if int(row.get("accepted_steps", -1)) != contract["path"]["load_steps"]:
        errors.append("accepted_steps")
    if int(row.get("rejected_increments", -1)) != 0:
        errors.append("rejected_increments")
    return not errors, errors


def _replay_gate(primary: dict[str, Any], replay_a: dict[str, Any], replay_b: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    names = ("selected_displacement", "reaction_norm", "energy", "von_mises_max", "equivalent_plastic_strain_max")
    checks = {
        name: {
            "primary_vs_replay_a": _relative(float(primary[name]), float(replay_a[name])),
            "replay_a_vs_replay_b": _relative(float(replay_a[name]), float(replay_b[name])),
        }
        for name in names
    }
    tolerance = contract["gates"]["replay_relative_tolerance"]
    passed = all(
        values["primary_vs_replay_a"] <= tolerance and values["replay_a_vs_replay_b"] <= tolerance
        for values in checks.values()
    )
    return {"status": "PASS" if passed else "FAIL_CLOSED", "checks": checks}


def _run_independent_reference(output: Path) -> dict[str, Any]:
    reference_output = output / "independent_component_reference"
    command = [
        sys.executable,
        str(ROOT / "scripts" / "run_wp09_independent_reference.py"),
        "--rotation-deg",
        "50",
        "--output",
        str(reference_output),
    ]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    (output / "independent_reference_stdout.log").write_text(completed.stdout, encoding="utf-8")
    (output / "independent_reference_stderr.log").write_text(completed.stderr, encoding="utf-8")
    summary_path = reference_output / "summary.json"
    if not summary_path.exists():
        return {"status": "FAIL_CLOSED_MISSING_SUMMARY", "return_code": completed.returncode}
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return {
        "status": summary.get("status", "FAIL_CLOSED"),
        "return_code": completed.returncode,
        "summary_path": str(summary_path),
        "summary_sha256": _sha256(summary_path),
        "summary": summary,
    }


def _mesh_gate(m2: list[dict[str, Any]], m3: list[dict[str, Any]], contract: dict[str, Any]) -> dict[str, Any]:
    thresholds = contract["gates"]["mesh_comparison"]
    rows: list[dict[str, Any]] = []
    for middle in m2:
        fine = next(row for row in m3 if row["family"] == middle["family"])
        deltas = {
            "selected_displacement": _relative(middle["selected_displacement"], fine["selected_displacement"]),
            "reaction": _relative(middle["reaction_norm"], fine["reaction_norm"]),
            "energy": _relative(middle["energy"], fine["energy"]),
            "von_mises": _relative(middle["von_mises_max"], fine["von_mises_max"]),
        }
        failures = [
            name
            for name, value in deltas.items()
            if value > thresholds[f"{name}_relative_max"]
        ]
        rows.append({"family": middle["family"], "deltas": deltas, "failures": failures})
    return {"status": "PASS" if all(not row["failures"] for row in rows) else "FAIL_CLOSED", "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("M1", "M2", "M3", "all"), default="all")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    selected = STAGES if args.stage == "all" else STAGES[: STAGES.index(args.stage) + 1]
    campaign: dict[str, Any] = {
        "status": "RUNNING",
        "contract_path": str(CONTRACT_PATH),
        "contract_sha256": _sha256(CONTRACT_PATH),
        "governing_branch": _git("branch", "--show-current"),
        "execution_sha": _git("rev-parse", "HEAD"),
        "authorized_source_sha": contract["authorized_source_sha"],
        "working_tree_at_start": _git("status", "--short"),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "machine": {"platform": platform.platform(), "python": platform.python_version()},
        "stages": {},
        "formal_points": "0/8",
    }
    reference = _run_independent_reference(output)
    campaign["independent_component_reference"] = reference
    reference_pass = reference["status"] == "PASS_INDEPENDENT_REFERENCE"
    previous_pass = reference_pass
    stage_rows: dict[str, list[dict[str, Any]]] = {}
    for stage in selected:
        cells = int(contract["stages"][stage]["cells"][0])
        if not previous_pass:
            campaign["stages"][stage] = {"status": "SKIPPED_DEPENDENCY", "cells": cells}
            continue
        rows: list[dict[str, Any]] = []
        for family in FAMILIES:
            primary = _run_one(family, cells, output, stage.lower())
            replay_a = _run_one(family, cells, output, f"{stage.lower()}_replay_a")
            replay_b = _run_one(family, cells, output, f"{stage.lower()}_replay_b")
            structural_pass, structural_failures = _structural_gate(primary, contract)
            replay = _replay_gate(primary, replay_a, replay_b, contract) if structural_pass else {
                "status": "SKIPPED_DEPENDENCY", "checks": {}
            }
            row = {
                "family": family,
                "cells": cells,
                "primary": primary,
                "structural_gate": {"status": "PASS" if structural_pass else "FAIL_CLOSED", "failures": structural_failures},
                "replay": replay,
            }
            row["status"] = "PASS" if structural_pass and replay["status"] == "PASS" else "FAIL_CLOSED"
            rows.append(row)
        stage_status = "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL_CLOSED"
        campaign["stages"][stage] = {"status": stage_status, "cells": cells, "rows": rows}
        stage_rows[stage] = [row["primary"] for row in rows]
        previous_pass = stage_status == "PASS"
        if not previous_pass:
            for later in STAGES[STAGES.index(stage) + 1 :]:
                if later in selected:
                    campaign["stages"][later] = {
                        "status": "SKIPPED_DEPENDENCY",
                        "cells": int(contract["stages"][later]["cells"][0]),
                    }
            break
    if "M2" in stage_rows and "M3" in stage_rows and campaign["stages"]["M2"]["status"] == "PASS" and campaign["stages"]["M3"]["status"] == "PASS":
        campaign["mesh_gate_m2_to_m3"] = _mesh_gate(stage_rows["M2"], stage_rows["M3"], contract)
    else:
        campaign["mesh_gate_m2_to_m3"] = {"status": "SKIPPED_DEPENDENCY"}
    campaign["status"] = "PASS_CANDIDATE" if previous_pass else "FAIL_CLOSED"
    campaign["working_tree_at_end"] = _git("status", "--short")
    (output / "campaign.json").write_text(json.dumps(campaign, indent=2, default=_json_default, allow_nan=False), encoding="utf-8")
    manifest_rows = []
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path.name in {"campaign.json", "manifest.json"}:
            continue
        manifest_rows.append(
            {
                "path": str(path.relative_to(output)),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "execution_sha": campaign["execution_sha"],
                "contract_sha256": campaign["contract_sha256"],
                "files": manifest_rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    campaign["manifest_sha256"] = _sha256(output / "manifest.json")
    campaign["artifact_count"] = len(manifest_rows)
    (output / "campaign.json").write_text(json.dumps(campaign, indent=2, default=_json_default, allow_nan=False), encoding="utf-8")
    lines = [
        "# WP09 formal requalification campaign",
        "",
        f"Status: `{campaign['status']}`",
        f"Execution SHA: `{campaign['execution_sha']}`",
        f"Authorized source SHA: `{campaign['authorized_source_sha']}`",
        f"Contract SHA-256: `{campaign['contract_sha256']}`",
        "",
        "| Stage | Status |",
        "|---|---|",
    ]
    for stage in selected:
        row = campaign["stages"].get(stage, {"status": "NOT_RUN"})
        lines.append(f"| {stage} | {row['status']} |")
    lines.extend(
        [
            "",
            "The independent reference is a material-point/affine-element recomputation, not an independent global FEM solve.",
            "",
            "Formal WP09 points remain `0/8` pending Owner review.",
        ]
    )
    (output / "campaign.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": campaign["status"], "execution_sha": campaign["execution_sha"], "stages": campaign["stages"], "mesh_gate_m2_to_m3": campaign["mesh_gate_m2_to_m3"]}, indent=2, default=_json_default))
    return 0 if campaign["status"] == "PASS_CANDIDATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
