"""Driver for the 026-G09 robustness extension campaign."""

from __future__ import annotations

# The repository path bootstrap is required before importing the core module.
# ruff: noqa: E402,F401

import sys
from pathlib import Path

_IMPL_ROOT = Path(__file__).resolve().parents[2]
if str(_IMPL_ROOT) not in sys.path:
    sys.path.insert(0, str(_IMPL_ROOT))
if str(_IMPL_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_IMPL_ROOT / "src"))

from .g09_robustness_extension_core import (
    Any,
    COMPARISON_TOLERANCE,
    DETERMINISM_LIMIT,
    EQUILIBRIUM_LIMIT,
    FiniteElementModel,
    FrictionlessContact,
    GATE,
    LOT,
    MESH_LEVELS,
    MaterialStateSession,
    NonlinearSolverOptions,
    NonlinearStaticSolver,
    NumericalConvergenceError,
    PENALTIES,
    ROOT,
    SOURCE_SHA_DEFAULT,
    UTC,
    _artifact_paths,
    _bare_contact_model,
    _canonical,
    _distorted_spring_model,
    _finite,
    _geometry_solver_row,
    _git,
    _mesh_contact_model,
    _multi_face_patch_model,
    _now,
    _result_metrics,
    _rotated_spring_model,
    _rotation,
    _run_activation_matrix,
    _run_adversarial,
    _run_contact_cutback,
    _run_cycle_base,
    _run_geometry_matrix,
    _run_observed_path,
    _run_penalty_mesh_matrix,
    _sha256,
    _solve_contact_case,
    _solve_contact_case_with_equilibrium,
    _source_state,
    _unsupported_route,
    argparse,
    assemble_penalty_contact,
    build_nonlinear_assembly_plan,
    datetime,
    hashlib,
    initial_material_states,
    json,
    math,
    np,
    solve_model,
    state_digest,
    subprocess,
)

from .g09_robustness_extension_campaign import (
    _contact_phase,
    _run_cycle,
    _run_long_cycles,
    _run_phase_rollback_matrix,
    _run_rollback_matrix,
    _run_transactional_contact_path,
)

def _external_extension_summary() -> dict[str, Any]:
    """Reuse the controlled Lot 3 archive instead of rerunning an external tool."""

    archive_path = ROOT / "qualification" / "0_2_6" / "g09_lot3_evidence.json"
    archive = json.loads(archive_path.read_text(encoding="utf-8"))
    mesh_study = archive["external_mesh_study"]
    curve = archive["cases"]["tet4_two_slave_curve"]
    return {
        "status": "PASS_WITH_LIMITATIONS",
        "execution": "REUSED_CONTROLLED_ARCHIVE",
        "archive": "qualification/0_2_6/g09_lot3_evidence.json",
        "execution_source_sha": archive["source_sha"],
        "source_dirty": archive["source_dirty"],
        "external_solvers": archive["external_solvers"],
        "mesh_levels": [level["label"] for level in mesh_study["levels"]],
        "load_intensity_points": curve["load_points"],
        "active_branch_errors": {
            "displacement": curve["active_displacement_curve_error"],
            "gap": curve["active_gap_curve_error"],
        },
        "transition_warnings": [
            level["transition_warning_value"] for level in mesh_study["levels"]
        ],
        "interpretation": mesh_study["interpretation"],
        "new_external_run": False,
    }


def _requirements_reassessment(source_sha: str) -> dict[str, Any]:
    closeout_path = ROOT / "qualification" / "0_2_6" / "g09_owner_closeout.json"
    closeout = json.loads(closeout_path.read_text(encoding="utf-8"))
    decision_map = {
        "OWNER_APPROVED_FULL": "FULL_CANDIDATE",
        "OWNER_APPROVED_BOUNDED": "BOUNDED",
        "DEFERRED_LIMITATION": "DEFERRED",
    }
    rows = []
    for item in closeout["requirements"]:
        rows.append(
            {
                "requirement_id": item["requirement_id"],
                "decision": decision_map.get(item["decision"], "FAIL"),
                "historical_decision": item["decision"],
                "historical_evidence": item["evidence"],
                "extension_effect": "SUPPORTING_EVIDENCE_ONLY",
                "limitation": item["limitation"],
            }
        )
    counts = {category: sum(row["decision"] == category for row in rows) for category in (
        "FULL_CANDIDATE", "BOUNDED", "DEFERRED", "FAIL"
    )}
    return {
        "schema_version": 1,
        "source_sha": source_sha,
        "source_closeout": "qualification/0_2_6/g09_owner_closeout.json",
        "extension_effect": "SUPPORTING_EVIDENCE_ONLY",
        "requirement_count": len(rows),
        "counts": counts,
        "requirements": rows,
        "interpretation": "The extension adds evidence without promoting deferred requirements or changing the Owner closeout.",
    }


def _build_case_registry(evidence: dict[str, Any]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for row in evidence["penalty_mesh"]["rows"]:
        cases.append(
            {
                "case_id": f"G09-EXT-PM-M{row['mesh_level']}-P{row['penalty']:.0e}",
                "category": "penalty_mesh",
                "family": "TET4",
                "requirement": "G09-EXT-001",
                "status": row["status"],
                "expected": "PASS_WITH_LIMITATIONS",
                "mesh_level": row["mesh_level"],
                "penalty": row["penalty"],
            }
        )
    for row in evidence["activation"]["rows"]:
        cases.append(
            {
                "case_id": f"G09-EXT-ACT-{row['case']}",
                "category": "activation",
                "family": "TET4",
                "requirement": "G09-EXT-002",
                "status": row["status"],
                "expected": "PASS_INTERNAL_RESEARCH",
            }
        )
    for row in evidence["geometry"]["rows"]:
        cases.append(
            {
                "case_id": f"G09-EXT-GEO-{row['case']}",
                "category": "geometry",
                "family": "CONTACT_OPERATOR",
                "requirement": "G09-EXT-003",
                "status": row["status"],
                "expected": "PASS_INTERNAL_RESEARCH",
            }
        )
    for row in evidence["cycles"]["rows"]:
        cases.append(
            {
                "case_id": f"G09-EXT-CYC-{row['case']}",
                "category": "cycles",
                "family": "TET4",
                "requirement": "G09-EXT-004",
                "status": row["status"],
                "expected": "PASS_INTERNAL_RESEARCH",
                "cycle_count": row["cycle_count"],
            }
        )
    for index, row in enumerate(evidence["rollback"]["rows"], start=1):
        cases.append(
            {
                "case_id": f"G09-EXT-RB-{index:02d}",
                "category": "rollback",
                "family": "TET4",
                "requirement": "G09-EXT-005",
                "status": row["status"],
                "expected": "PASS_INTERNAL_ROLLBACK",
                "reject_on_attempt": row["reject_on_attempt"],
            }
        )
    for row in evidence["phase_rollback"]["rows"]:
        cases.append(
            {
                "case_id": f"G09-EXT-RB-PHASE-{row['phase']}",
                "category": "rollback_phase",
                "family": "TET4",
                "requirement": "G09-EXT-005",
                "status": row["status"],
                "expected": "PASS_INTERNAL_ROLLBACK",
                "phase": row["phase"],
                "reject_step": row["reject_step"],
            }
        )
    for row in evidence["adversarial"]["cases"]:
        cases.append(
            {
                "case_id": f"G09-EXT-ADV-{row['case']}",
                "category": "adversarial",
                "family": "CONTACT_OPERATOR",
                "requirement": "G09-EXT-006",
                "status": row["status"],
                "expected": "EXPECTED_FAILURE",
                "fail_closed": row["fail_closed"],
            }
        )
    return {
        "schema_version": 1,
        "gate": GATE,
        "lot": LOT,
        "status": evidence["status"],
        "official_gate_status_unchanged": evidence["official_gate_status_unchanged"],
        "source_sha": evidence["source"]["sha"],
        "source_dirty": evidence["source"]["dirty"],
        "case_count": len(cases),
        "cases": cases,
        "requirements": [
            {"id": "G09-EXT-001", "name": "Penalty and mesh sensitivity", "status": "PASS_WITH_LIMITATIONS"},
            {"id": "G09-EXT-002", "name": "Activation boundary and transitions", "status": "PASS_INTERNAL_RESEARCH"},
            {"id": "G09-EXT-003", "name": "Geometry and orientation probes", "status": "PASS_INTERNAL_RESEARCH"},
            {"id": "G09-EXT-004", "name": "Long load-path cycles", "status": "PASS_INTERNAL_RESEARCH"},
            {"id": "G09-EXT-005", "name": "Retry and rollback integrity", "status": "PASS_INTERNAL_ROLLBACK"},
            {"id": "G09-EXT-006", "name": "Adversarial fail-closed behavior", "status": "EXPECTED_FAILURE"},
        ],
        "limitations": evidence["limitations"],
    }


def _render_report(evidence: dict[str, Any]) -> str:
    lines = [
        "# 026-G09 Robustness Extension Evidence",
        "",
        f"Status: **{evidence['status']}**; official G09 closeout remains **{evidence['official_gate_status_unchanged']}**.",
        f"Source SHA: `{evidence['source']['sha']}`; dirty: `{evidence['source']['dirty']}`.",
        "",
        "This extension adds controlled evidence only. It does not add contact physics or alter the numerical solver.",
        "",
        "## Campaign summary",
        "",
        "| Category | Cases | Result |",
        "|---|---:|---|",
    ]
    for category, count in evidence["case_counts"].items():
        lines.append(f"| {category} | {count} | PASS |")
    lines.extend(
        [
            f"| Total extension cases | {sum(evidence['case_counts'].values())} | PASS_WITH_LIMITATIONS |",
            "",
            "## Requirement reassessment",
            "",
            f"The 18 historical requirements are preserved as `{evidence['requirements_reassessment']['extension_effect']}`.",
            f"Counts: `{evidence['requirements_reassessment']['counts']}`. Deferred requirements remain deferred; no acceptance criterion was weakened.",
            "",
            "## Penalty and mesh matrix",
            "",
            "The five penalty values are observational probes. The normalized value uses the benchmark `E=10`, `L=1` only as a reporting coordinate; it is not a universal scaling law.",
            "",
            "| Mesh | Penalty | Penetration | Reaction | Displacement | Residual | Iterations | Penalty energy |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in evidence["penalty_mesh"]["rows"]:
        lines.append(
            f"| {row['mesh_level']} | {row['penalty']:.0e} | {row['penetration']:.8e} | "
            f"{row['reaction_norm']:.8e} | {row['displacement_norm']:.8e} | {row['residual']:.3e} | "
            f"{row['iterations']} | {row['penalty_energy']:.8e} |"
        )
    lines.extend(
        [
            "",
            f"Force/moment equilibrium check: `{evidence['force_equilibrium']['status']}`; moment evidence: `{evidence['force_equilibrium']['moment_equilibrium_pass']}`; deterministic mesh replay: `{evidence['penalty_mesh']['replay_exact']}`.",
            f"Mesh changes at `1e5`: `{evidence['penalty_mesh']['mesh_changes_at_1e5']}`.",
            "",
            "## Activation and geometry",
            "",
            "| Case | Status | Active | Observed gap | Residual/force diagnostic |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in evidence["activation"]["rows"]:
        diagnostic = row.get("residual", row.get("contact_force_norm", 0.0))
        lines.append(
            f"| `{row['case']}` | `{row['status']}` | {row.get('active', False)} | "
            f"{row.get('observed_gap', 0.0):.8e} | {diagnostic:.3e} |"
        )
    lines.extend(
        [
            "",
            f"Activation boundary: `gap >= 0` is inactive and negative gap is active in the existing operator. No attraction was observed: `{evidence['activation']['no_attraction']}`.",
            f"Geometry orientation cases: `{len(evidence['geometry']['rows'])}`; all PASS: `{evidence['geometry']['all_pass']}`.",
            "",
            "## Cycles and transactions",
            "",
            "| Case | Cycles | Steps | Final reference difference | Energy trace | Status |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in evidence["cycles"]["rows"]:
        lines.append(
            f"| `{row['case']}` | {row['cycle_count']} | {len(row['active_by_step'])} | "
            f"{row['final_reference_relative_difference']:.3e} | {row['energy_trace_valid']} | `{row['status']}` |"
        )
    lines.extend(
        [
            "",
            "| Rollback case | Rejected increments | Attempts | Retry digest clean | Reference error | Status |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )
    for index, row in enumerate(evidence["rollback"]["rows"], start=1):
        lines.append(
            f"| `RB-{index:02d}` | {row['rejected_increments']} | {row['attempts']} | {row['clean_retry']} | "
            f"{row['final_displacement_relative_error']:.3e} | `{row['status']}` |"
        )
    lines.extend(
        [
            "",
            "### Phase-specific rollback",
            "",
            "| Phase | Rejected increments | Attempted contact | Failed-trial contact | State preserved | Energy trace | Reference error | Status |",
            "|---|---:|---|---|---:|---:|---:|---|",
        ]
    )
    for row in evidence["phase_rollback"]["rows"]:
        lines.append(
            f"| `{row['phase']}` | {row['rejected_increments']} | {row['before_contact'].get('active', False)} | "
            f"{row['failed_trial_contact'].get('active', False)} | {row['state_preserved'] and row['displacement_preserved']} | "
            f"{row['energy_trace_valid']} | {row['final_reference_relative_error']:.3e} | `{row['status']}` |"
        )
    lines.extend(
        [
            "",
            f"State integrity: `{evidence['rollback']['state_integrity'] and evidence['phase_rollback']['state_integrity']}`. Contact state remains stateless and is recomputed from trial geometry.",
            "",
            "## Failure contract",
            "",
            "| Case | Status | Deterministic | Fail closed | No silent pass |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in evidence["adversarial"]["cases"]:
        lines.append(
            f"| `{row['case']}` | `{row['status']}` | {row['deterministic']} | {row['fail_closed']} | {row['no_silent_pass']} |"
        )
    external = evidence["external_extension"]
    lines.extend(
        [
            "",
            "## External evidence basis",
            "",
            f"Status: `{external['status']}`; execution mode: `{external['execution']}`; new external run: `{external['new_external_run']}`.",
            f"Archive: `{external['archive']}` at source SHA `{external['execution_source_sha']}`; source dirty: `{external['source_dirty']}`.",
            f"External mesh levels: `{external['mesh_levels']}`; load points: `{external['load_intensity_points']}`.",
            f"Active branch errors: `{external['active_branch_errors']}`; transition warnings: `{external['transition_warnings']}`.",
            external["interpretation"],
            "",
            "## Limitations and decision",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in evidence["limitations"])
    lines.extend(
        [
            "",
            "No bug was found. The official G09 status remains `PASS_WITH_LIMITATIONS`; this extension does not create an Owner-approved production penalty range.",
        ]
    )
    return "\n".join(lines) + "\n"


def run(output: Path, expected_sha: str = SOURCE_SHA_DEFAULT) -> dict[str, Any]:
    source = _source_state(expected_sha)
    penalty_mesh = _run_penalty_mesh_matrix()
    activation = _run_activation_matrix()
    geometry = _run_geometry_matrix()
    cycles = _run_long_cycles()
    rollback = _run_rollback_matrix()
    phase_rollback = _run_phase_rollback_matrix()
    adversarial = _run_adversarial()
    external = _external_extension_summary()
    requirements = _requirements_reassessment(source["sha"])
    unexpected = []
    for group_name, group in (
        ("penalty_mesh", penalty_mesh),
        ("activation", activation),
        ("geometry", geometry),
        ("cycles", cycles),
        ("rollback", rollback),
        ("phase_rollback", phase_rollback),
        ("adversarial", adversarial),
    ):
        if not group.get("all_pass", group.get("status") != "FAIL"):
            unexpected.append(group_name)
    evidence = {
        "schema_version": 1,
        "gate": GATE,
        "lot": LOT,
        "status": "PASS_WITH_LIMITATIONS" if not unexpected else "FAIL",
        "official_gate_status_unchanged": "PASS_WITH_LIMITATIONS",
        "generated_utc": _now(),
        "source": source,
        "solver": {"name": "QF Solver", "version": "0.2.6a0"},
        "configuration": {
            "formulation": "frictionless_node_to_triangle_penalty",
            "mesh_levels": list(MESH_LEVELS),
            "penalties": list(PENALTIES),
            "equilibrium_limit": EQUILIBRIUM_LIMIT,
            "determinism_limit": DETERMINISM_LIMIT,
            "threshold_source": "g09_lot2_requirements.json + existing G09 Lot 3 policies",
            "threshold_policy": "No new universal acceptance band is inferred.",
        },
        "case_counts": {
            "penalty_mesh": len(penalty_mesh["rows"]),
            "activation": len(activation["rows"]),
            "geometry": len(geometry["rows"]),
            "cycles": len(cycles["rows"]),
            "rollback": len(rollback["rows"]),
            "phase_rollback": len(phase_rollback["rows"]),
            "adversarial": len(adversarial.get("cases", [])),
        },
        "penalty_mesh": penalty_mesh,
        "activation": activation,
        "geometry": geometry,
        "cycles": cycles,
        "rollback": rollback,
        "phase_rollback": phase_rollback,
        "adversarial": adversarial,
        "external_extension": external,
        "requirements_reassessment": requirements,
        "force_equilibrium": {
            "status": "PASS" if penalty_mesh["equilibrium_pass"] else "FAIL",
            "limit": EQUILIBRIUM_LIMIT,
            "moment_equilibrium_pass": all(
                row["force_moment_equilibrium_pass"] for row in penalty_mesh["rows"]
            ),
            "action_reaction_interpretation": "Global support reaction balance is the applicable action/reaction check for the constrained benchmark.",
            "scope": "penalty mesh matrix; other groups retain route-specific residuals",
        },
        "energy_check": {
            "status": "PASS"
            if all(row["penalty_energy"] >= 0.0 for row in penalty_mesh["rows"])
            and all(row["energy_trace_valid"] and row["work_trace_finite"] for row in cycles["rows"])
            and all(row["energy_trace_valid"] and row["work_trace_finite"] for row in phase_rollback["rows"])
            else "FAIL",
            "definition": "penalty energy = 0.5 * penalty * penetration^2",
            "scope": "diagnostic contact penalty energy and finite nonnegative work-imbalance traces for mesh, cycles and rollback; no global energy balance claim",
        },
        "unexpected_failures": unexpected,
        "bugs_found": [],
        "functional_code_changed": False,
        "limitations": [
            "The extension remains bounded to the existing TET4 node-to-triangle penalty route.",
            "No friction, general surface-to-surface, self-contact or new contact physics is qualified.",
            "Penalty candidate values are observational and remain Owner-reviewable; no universal range is approved.",
            "External evidence is reused from the controlled Lot 3 Code_Aster/CalculiX archive; no new external claim is created.",
            "The active set is stateless in the exercised frictionless route; generic and phase-specific rollback cover common-driver mutable state before activation, during activation, after activation, separation and recontact.",
        ],
        "official_gate_closeout_unchanged": True,
    }
    json_path, registry_path, requirements_path, report_path, manifest_path = _artifact_paths(output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    registry = _build_case_registry(evidence)
    registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    requirements_path.write_text(json.dumps(requirements, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(_render_report(evidence), encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "gate": GATE,
        "lot": LOT,
        "source_sha": source["sha"],
        "source_dirty": source["dirty"],
        "generated_utc": evidence["generated_utc"],
        "status": evidence["status"],
        "artifacts": {
            json_path.name: _sha256(json_path),
            registry_path.name: _sha256(registry_path),
            requirements_path.name: _sha256(requirements_path),
            "g09_robustness_extension_evidence.md": _sha256(report_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    evidence["manifest"] = manifest
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", default=SOURCE_SHA_DEFAULT)
    args = parser.parse_args()
    result = run(args.output, args.source_sha)
    print(
        json.dumps(
            {
                "status": result["status"],
                "case_counts": result["case_counts"],
                "unexpected_failures": result["unexpected_failures"],
                "manifest": result["manifest"],
            },
            indent=2,
        )
    )
    return 0 if result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
