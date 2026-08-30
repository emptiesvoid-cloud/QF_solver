"""Driver for the controlled 026-G09 contact Lot 2 campaign.

The public script remains a compatibility entry point while the campaign
helpers live in a separate module below the architecture size limit.
"""

from __future__ import annotations

# These imports intentionally preserve the historical script import surface.
# ruff: noqa: F401

from .g09_lot2_core import (
    Any,
    CASE_CONTRACT,
    COMPARISON_TOLERANCE,
    Callable,
    DEFAULT_OUTPUT,
    FiniteElementModel,
    FrictionlessContact,
    GATE,
    MESH_LEVELS,
    NonlinearStaticSolver,
    NumericalConvergenceError,
    PENALTIES,
    Path,
    ROOT,
    SOLVER_TOLERANCE,
    SOURCE_CONTRACT,
    UTC,
    _bare_contact_model,
    _canonical,
    _excessive_penetration,
    _expected_penetration_failure,
    _failure_case,
    _failure_observation,
    _finite,
    _git,
    _invalid_geometry,
    _invalid_penalty,
    _invalid_target,
    _mesh_contact_model,
    _newton_nonconvergence,
    _now,
    _reaction_norm,
    _refinement_model,
    _run_adversarial,
    _run_contact_cutback,
    _run_cycle,
    _run_cycles,
    _run_mesh_sensitivity,
    _sha256,
    _solve_contact_case,
    _source_state,
    _unsupported_route,
    argparse,
    assemble_penalty_contact,
    datetime,
    hashlib,
    json,
    math,
    np,
    replace,
    solve_model,
    state_digest,
    subprocess,
    sys,
)

def _render_report(evidence: dict[str, Any]) -> str:
    lines = [
        "# 026-G09 Contact Lot 2 Evidence",
        "",
        f"Status: **{evidence['status']}**; official gate remains **{evidence['gate_status_unchanged']}**.",
        f"Source SHA: `{evidence['source']['sha']}`; dirty: `{evidence['source']['dirty']}`.",
        "",
        "## Scope and policy",
        "",
        "This lot exercises the existing TET4 frictionless node-to-triangle penalty path. "
        "No friction, finite-sliding, surface-to-surface formulation or production penalty range is qualified.",
        "",
        "| Declared item | Value |",
        "|---|---|",
        f"| Mesh levels | `{MESH_LEVELS}` |",
        f"| Penalties | `{PENALTIES}` |",
        f"| Solver tolerance | `{SOLVER_TOLERANCE:.1e}` |",
        f"| Reference comparison tolerance | `{COMPARISON_TOLERANCE:.1e}` |",
        "",
        "## Mesh and penalty sensitivity",
        "",
        "| Mesh | Nodes | Elements | DOF | Penalty | Gap | Penetration | Reaction norm | Residual | Iterations |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in evidence["mesh_sensitivity"]["raw_rows"]:
        lines.append(
            f"| {row['mesh_level']} | {row['node_count']} | {row['element_count']} | {row['dof_count']} | "
            f"{row['penalty']:.0e} | {row['gap']:.8e} | {row['penetration']:.8e} | "
            f"{row['reaction_norm']:.8e} | {row['residual']:.8e} | {row['iterations']} |"
        )
    lines.extend(
        [
            "",
            f"Mesh-level replay exact: `{evidence['mesh_sensitivity']['replay_exact']}`.",
            f"Penetration monotone within each tested mesh: `{evidence['mesh_sensitivity']['penetration_monotone_by_mesh']}`.",
            "Mesh trend is observational; no universal convergence or penalty band is inferred.",
            "",
            "## Contact cycles",
            "",
            "| Case | Load path | Active sequence | Gap sequence | Final replay | Status |",
            "|---|---|---|---|---:|---|",
        ]
    )
    for row in evidence["cycles"]["cases"]:
        lines.append(
            f"| `{row['case']}` | `{row['load_path']}` | `{row['active_by_step']}` | "
            f"`{[round(value, 8) for value in row['gaps_by_step']]}` | "
            f"{row['final_reference_relative_difference']:.3e} | `{row['status']}` |"
        )
    lines.extend(
        [
            "",
            f"Recontact replay exact: `{evidence['cycles']['recontact_replay_exact']}`.",
            "The contact active set is recomputed from the current trial displacement; no ghost contact state is stored.",
            "",
            "## Cutback, retry and rollback",
            "",
            "| Case | Rejected attempt | Rejected increments | Adaptive path | Digest preserved | Reference error | Status |",
            "|---|---:|---:|---|---:|---:|---|",
        ]
    )
    for row in evidence["cutback_retry_rollback"]["cases"]:
        lines.append(
            f"| `{row['case']}` | {row['reject_on_attempt']} | {row['rejected_increments']} | "
            f"`{row['adaptive_load_path']}` | {row['clean_retry']} | "
            f"{row['final_displacement_relative_error']:.3e} | `{row['status']}` |"
        )
    lines.extend(
        [
            "",
            "Contact transaction: `N/A` for persistent contact state because this frictionless active set is stateless; common material/displacement transaction is checked.",
            "",
            "## Failure and adversarial contract",
            "",
            "| Case | Status | Exception/reason | Deterministic | Fail closed |",
            "|---|---|---|---:|---:|",
        ]
    )
    for row in evidence["adversarial"]["cases"]:
        first = row["first"]
        if "variants" in first:
            exception_label = "InputValidationError x3"
        else:
            exception_label = first.get("exception", "see JSON")
        lines.append(
            f"| `{row['case']}` | `{row['status']}` | "
            f"`{exception_label}` / `{first.get('reason')}` | "
            f"{row['deterministic']} | {row['fail_closed']} |"
        )
    candidate = evidence["penalty_candidate"]
    lines.extend(
        [
            "",
            "## Penalty governance",
            "",
            f"Experimental candidate for Owner review only: `{candidate['candidate_range']}`.",
            f"Status: `{candidate['status']}`.",
            candidate["rationale"],
            "No universal production range or conditioning cutoff is approved by this report.",
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
        raise RuntimeError("G09 Lot 2 requires a clean source worktree.")
    contract = json.loads(SOURCE_CONTRACT.read_text(encoding="utf-8"))
    case_registry = json.loads(CASE_CONTRACT.read_text(encoding="utf-8"))
    mesh = _run_mesh_sensitivity()
    cycles = _run_cycles()
    cutback_cases = [
        {"case": "failure_before_first_commit", **_run_contact_cutback(-20.0, 1, 1.0)},
        {"case": "failure_after_one_committed_increment", **_run_contact_cutback(-40.0, 2, 0.5)},
    ]
    cutback = {
        "status": "PASS_INTERNAL_ROLLBACK"
        if all(row["status"] == "PASS_INTERNAL_ROLLBACK" for row in cutback_cases)
        else "FAIL",
        "cases": cutback_cases,
        "rollback_state_integrity": all(row["clean_retry"] for row in cutback_cases),
        "limitations": [
            "The rejected failures are deterministic harness fault injections, not material/contact-instability claims.",
            "The contact active set itself is stateless; its recomputation is recorded as N/A for persistent contact state.",
        ],
    }
    adversarial = _run_adversarial()
    unexpected = []
    for name, block in (("mesh", mesh), ("cycles", cycles), ("cutback", cutback), ("adversarial", adversarial)):
        if block["status"] == "FAIL":
            unexpected.append(name)
    evidence = {
        "schema_version": 1,
        "gate": GATE,
        "lot": "LOT2",
        "status": "PASS_WITH_LIMITATIONS" if not unexpected else "FAIL",
        "gate_status_unchanged": "NOT_STARTED",
        "generated_utc": _now(),
        "source": source,
        "solver": {"name": "QF_solver", "version": "0.2.6a0"},
        "configuration": {
            "formulation": "frictionless_penalty_node_to_triangle",
            "search_mode": "initial",
            "family": "TET4",
            "mesh_levels": list(MESH_LEVELS),
            "penalties": list(PENALTIES),
            "solver_tolerance": SOLVER_TOLERANCE,
            "comparison_tolerance": COMPARISON_TOLERANCE,
            "threshold_source": "g09_lot2_requirements.json",
        },
        "contract": {
            "requirements_total": len(contract["requirements"]),
            "registered_cases": len(case_registry["cases"]),
            "thresholds_predeclared": True,
        },
        "mesh_sensitivity": mesh,
        "cycles": cycles,
        "cutback_retry_rollback": cutback,
        "adversarial": adversarial,
        "penalty_candidate": {
            "candidate_range": "1e4..1e6",
            "status": "OWNER_REVIEW_REQUIRED",
            "mesh_dependence": "Observed bounded dependence across mesh levels; no universal range inferred.",
            "conditioning_limitation": "No universal conditioning cutoff approved; residual and contact penetration remain diagnostic outputs.",
            "rationale": "The interval is an experimental candidate for the tested TET4 benchmark because all three values converged at all three mesh levels and penetration was non-increasing. It is not a production policy.",
        },
        "unexpected_failures": unexpected,
        "bugs_found": [],
        "limitations": [
            "Official 026-G09 remains NOT_STARTED; Lot 2 evidence does not close the gate.",
            "Scope remains TET4 frictionless node-to-triangle penalty contact in the initial configuration.",
            "General surface-to-surface, finite sliding, friction, self-contact and external correlation remain out of scope.",
            "No Owner-approved penalty range or conditioning threshold is claimed.",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "g09_lot2_evidence.json"
    md_path = output_dir / "g09_lot2_evidence.md"
    json_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_report(evidence), encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "gate": GATE,
        "lot": "LOT2",
        "source_sha": source["sha"],
        "source_dirty": source["dirty"],
        "generated_utc": evidence["generated_utc"],
        "solver_version": evidence["solver"]["version"],
        "artifacts": {
            "g09_lot2_evidence.json": _sha256(json_path),
            "g09_lot2_evidence.md": _sha256(md_path),
        },
        "status": evidence["status"],
        "official_gate_status_unchanged": evidence["gate_status_unchanged"],
    }
    manifest_path = output_dir / "g09_lot2_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return evidence | {"manifest": manifest}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(args.output_dir)
    print(
        json.dumps(
            {
                "status": result["status"],
                "mesh": result["mesh_sensitivity"]["status"],
                "cycles": result["cycles"]["status"],
                "cutback": result["cutback_retry_rollback"]["status"],
                "adversarial": result["adversarial"]["status"],
                "manifest": result["manifest"],
            },
            indent=2,
            default=str,
        )
    )
    return 0 if result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
