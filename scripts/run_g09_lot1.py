"""Run the controlled 026-G09 contact Lot 1 evidence campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from dataclasses import replace
from pathlib import Path
from typing import Any

UTC = timezone.utc

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
# ruff: noqa: E402

from solveur.contact.entities import FrictionlessContact
from solveur.contact.solver import assemble_penalty_contact
from solveur.api import solve_model
from solveur.core.errors import NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.verification.robustness_contact import (
    run_common_contact_benchmark,
    run_contact_penalty_sensitivity_benchmark,
    run_contact_recontact_benchmark,
)
from solveur.verification.robustness_mesh import _refinement_model

GATE = "026-G09"
SOURCE_CONTRACT = ROOT / "qualification" / "0_2_6" / "g09_requirements.json"
CASE_CONTRACT = ROOT / "qualification" / "0_2_6" / "g09_case_registry.json"
DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_6"
PENALTIES = (1.0e2, 1.0e3, 1.0e4, 1.0e5, 1.0e6)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _source_state() -> dict[str, Any]:
    return {"sha": _git("rev-parse", "HEAD"), "dirty": bool(_git("status", "--porcelain"))}


def _finite(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, dict):
        return all(_finite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite(item) for item in value)
    return True


def _expected_penetration_failure() -> dict[str, Any]:
    model = FiniteElementModel.from_raw(
        nodes=[[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [0.1, 0.25, 0.25]],
        elements=[],
        materials={},
        fixed_dofs=[],
        loads=[],
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "parameters": {"contact_max_penetration": 1.0e-6},
        },
    )
    model.contacts.append(
        FrictionlessContact(name="failure_limit", slave_node=3, master_nodes=(0, 1, 2))
    )
    dofs = model.dof_manager()
    displacement = np.zeros(dofs.ndof, dtype=float)
    displacement[dofs.index(3, "UX")] = -0.2
    try:
        assemble_penalty_contact(model, dofs, displacement, penalty=1.0e5)
    except NumericalConvergenceError as exc:
        reason = getattr(exc, "reason", None)
        return {
            "status": "EXPECTED_FAILURE",
            "converged": False,
            "exception": type(exc).__name__,
            "reason": reason.value if reason is not None else None,
            "message": str(exc),
            "fail_closed": True,
        }
    return {
        "status": "FAIL",
        "converged": True,
        "fail_closed": False,
        "message": "The penetration limit was not enforced.",
    }


def _replay_check(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    left = json.dumps(first, sort_keys=True, separators=(",", ":"))
    right = json.dumps(second, sort_keys=True, separators=(",", ":"))
    return {"status": "PASS" if left == right else "FAIL", "exact": left == right}


def _reaction_norm(result: Any) -> float | None:
    audit = result.to_dict().get("audit", {})
    for vector in audit.get("vectors", []):
        if vector.get("name") == "reactions":
            return float(vector["norm"])
    return None


def _penalty_reaction_sensitivity(penalties: tuple[float, ...]) -> list[dict[str, Any]]:
    """Expose contact and global reaction norms for the declared sweep."""

    rows: list[dict[str, Any]] = []
    for penalty in penalties:
        model = _refinement_model("TET4", 1)
        model.materials["j2"] = {"type": "isotropic_3d", "E": 10.0, "nu": 0.3}
        model.loads = [replace(load, value=-5.0) for load in model.loads]
        model.contacts.append(FrictionlessContact(slave_node=1, master_nodes=(0, 3, 4)))
        model.analysis = replace(
            model.analysis,
            parameters={
                **model.analysis.parameters,
                "load_path": [1.0],
                "contact_mode": "penalty",
                "contact_penalty": penalty,
                "contact_search_mode": "initial",
            },
        )
        result = solve_model(model, enforce_policy=False)
        dofs = model.dof_manager()
        _, _, details = assemble_penalty_contact(model, dofs, result.displacements, penalty=penalty)
        rows.append(
            {
                "penalty": float(penalty),
                "contact_force_norm": float(details["contact_force_norm"]),
                "global_reaction_norm": _reaction_norm(result),
                "run_verdict": result.run_verdict.value,
            }
        )
    return rows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_report(evidence: dict[str, Any]) -> str:
    lines = [
        "# 026-G09 Contact Lot 1 Evidence",
        "",
        f"Status: **{evidence['status']}**; official gate remains **{evidence['gate_status_unchanged']}**.",
        f"Source SHA: `{evidence['source']['sha']}`; dirty: `{evidence['source']['dirty']}`.",
        "",
        "## Scope",
        "",
        "Bounded frictionless node-to-triangle penalty contact on the existing nonlinear common driver. "
        "No friction, general surface-to-surface, finite-sliding or external-correlation claim is made.",
        "",
        "## Executed cases",
        "",
        "| Case | Status | Key evidence |",
        "|---|---|---|",
    ]
    for row in evidence["cases"]:
        detail = row.get("detail", row.get("message", ""))
        lines.append(f"| `{row['case_id']}` | `{row['status']}` | {detail} |")
    lines.extend(["", "## Penalty sensitivity", "", "| Penalty | Gap | Penetration | Residual | Iterations |", "|---:|---:|---:|---:|---:|"])
    for row in evidence["penalty_sensitivity"]["rows"]:
        lines.append(
            f"| {row['penalty']:.0e} | {row['gap']:.8e} | {row['maximum_penetration']:.8e} | "
            f"{row['relative_residual']:.8e} | {row['iterations']} |"
        )
    lines.extend(["", "| Penalty | Contact force norm | Global reaction norm | Audit verdict |", "|---:|---:|---:|---|"])
    for row in evidence["reaction_sensitivity"]:
        lines.append(
            f"| {row['penalty']:.0e} | {row['contact_force_norm']:.8e} | "
            f"{row['global_reaction_norm'] if row['global_reaction_norm'] is not None else 'not reported'} | "
            f"`{row['run_verdict']}` |"
        )
    lines.extend(
        [
            "",
            f"Penetration monotone non-increasing: `{evidence['penalty_sensitivity']['penetration_monotone_nonincreasing']}`.",
            "The production penalty range and conditioning acceptance band remain Owner decisions.",
            "",
            "## Failure contract",
            "",
            "The excessive-penetration case is expected to fail closed with a structured "
            "`NumericalConvergenceError`; it is not counted as a converged case.",
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in evidence["limitations"])
    return "\n".join(lines) + "\n"


def run(output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    source = _source_state()
    if source["dirty"]:
        raise RuntimeError("G09 Lot 1 requires a clean source worktree.")
    contract = json.loads(SOURCE_CONTRACT.read_text(encoding="utf-8"))
    cases = json.loads(CASE_CONTRACT.read_text(encoding="utf-8"))["cases"]
    common = run_common_contact_benchmark()
    recontact = run_contact_recontact_benchmark()
    sensitivity = run_contact_penalty_sensitivity_benchmark(PENALTIES)
    reaction_sensitivity = _penalty_reaction_sensitivity(PENALTIES)
    failure = _expected_penetration_failure()
    replay = _replay_check(recontact, run_contact_recontact_benchmark())
    case_rows = [
        {
            "case_id": "G09-L1-001",
            "status": common["status"],
            "detail": f"open/closed active={common['open']['active_contacts']}/{common['closed']['active_contacts']}; "
            f"common driver residual={common['global_max_relative_residual']:.3e}",
            "result": common,
        },
        {
            "case_id": "G09-L1-002",
            "status": recontact["status"],
            "detail": f"active sequence={recontact['active_by_step']}; gaps={recontact['gaps_by_step']}",
            "result": recontact,
        },
        {
            "case_id": "G09-L1-003",
            "status": sensitivity["status"],
            "detail": f"penetration monotone={sensitivity['penetration_monotone_nonincreasing']}",
            "result": sensitivity,
        },
        {"case_id": "G09-L1-004", "status": failure["status"], "detail": failure["message"], "result": failure},
        {"case_id": "G09-L1-005", "status": replay["status"], "detail": "exact deterministic replay", "result": replay},
    ]
    unexpected = [row["case_id"] for row in case_rows if row["status"] == "FAIL"]
    evidence = {
        "schema_version": 1,
        "gate": GATE,
        "lot": "LOT1",
        "status": "PASS_WITH_LIMITATIONS" if not unexpected else "FAIL",
        "gate_status_unchanged": "NOT_STARTED",
        "generated_utc": _now(),
        "source": source,
        "solver": {"name": "QF_solver", "version": "0.2.6a0"},
        "configuration": {
            "contact_mode": "penalty",
            "contact_search_mode": "initial",
            "families": ["TET4"],
            "penalties": list(PENALTIES),
            "threshold_source": "g09_requirements.json",
        },
        "contract": {
            "requirements_total": len(contract["requirements"]),
            "case_registry_ready": sum(row["status"] == "READY" for row in cases),
            "case_registry_not_supported": sum(row["status"] == "NOT_SUPPORTED" for row in cases),
        },
        "cases": case_rows,
        "penalty_sensitivity": sensitivity,
        "reaction_sensitivity": reaction_sensitivity,
        "failure_mode": failure,
        "determinism": replay,
        "no_nan_inf": all(_finite(row) for row in case_rows),
        "no_silent_pass": failure["status"] == "EXPECTED_FAILURE" and not failure.get("converged", True),
        "unexpected_failures": unexpected,
        "bugs_found": [],
        "limitations": [
            "Bounded TET4 node-to-triangle penalty contact only.",
            "Initial-configuration search only in this lot; finite sliding is not qualified.",
            "Penalty production range and conditioning band require Owner decision.",
            "The exact linear active-set route and external contact studies are separate evidence.",
            "Official G09 remains NOT_STARTED; this is Lot 1 evidence, not gate closure.",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "g09_lot1_evidence.json"
    md_path = output_dir / "g09_lot1_evidence.md"
    json_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_report(evidence), encoding="utf-8")
    evidence["artifact_digests"] = {
        "g09_lot1_evidence.md": _sha256(md_path),
    }
    json_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "gate": GATE,
        "lot": "LOT1",
        "source_sha": source["sha"],
        "source_dirty": source["dirty"],
        "generated_utc": evidence["generated_utc"],
        "solver_version": evidence["solver"]["version"],
        "artifacts": {
            "g09_lot1_evidence.json": _sha256(json_path),
            "g09_lot1_evidence.md": _sha256(md_path),
        },
        "status": evidence["status"],
    }
    manifest_path = output_dir / "g09_lot1_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return evidence | {"manifest": manifest}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(args.output_dir)
    print(json.dumps({"status": result["status"], "cases": result["cases"], "manifest": result["manifest"]}, indent=2, default=str))
    return 0 if result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
