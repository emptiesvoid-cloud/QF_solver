"""Standard model CLI commands."""

from __future__ import annotations

import argparse
import json

import numpy as np

from mitc4.visualization import DeformationPlotter

from solveur.api.public import (
    check_mesh,
    inspect_model,
    list_methods,
    load_model,
    save_audit_markdown,
    save_evidence,
    save_result,
    save_result_csv,
    save_result_vtu,
    solve_model,
)
from solveur.core.audit_checks import audit_gate_failed, check_status_counts
from solveur.core.errors import ExitCode
from solveur.core.qualification import RunVerdict, qualification_summary, verification_profile


def command_solve(args: argparse.Namespace) -> int:
    model = load_model(args.input)
    apply_verification_profile(model, args.verification_profile)
    if args.analysis is not None or args.method is not None:
        model.analysis = model.analysis.with_overrides(analysis_type=args.analysis, method=args.method)
    result = solve_model(model, enforce_policy=False)
    save_result(result, args.output)
    if args.audit_md is not None:
        save_audit_markdown(result, args.audit_md)
    if args.csv_dir is not None:
        save_result_csv(result, args.csv_dir, model)
    if args.vtu is not None:
        save_result_vtu(result, model, args.vtu)
    if args.evidence_dir is not None:
        save_evidence(model, result, args.evidence_dir, input_path=args.input)
    if args.png is not None:
        if not hasattr(result, "displacements_for_plot"):
            raise ValueError("PNG export is available for displacement results only.")
        DeformationPlotter(scale=args.scale).plot(
            model.nodes,
            _surface_quads(model),
            result.displacements_for_plot(),
            title="Solved deformation",
            png=args.png,
            show=False,
        )
    print(f"SOLVE STATUS: {result.status}")
    print(f"RUN VERDICT: {result.run_verdict.value}")
    print(f"output: {args.output}")
    if args.audit_md is not None:
        print(f"audit markdown: {args.audit_md}")
    if args.csv_dir is not None:
        print(f"csv directory: {args.csv_dir}")
    if args.vtu is not None:
        print(f"vtu: {args.vtu}")
    if args.evidence_dir is not None:
        print(f"evidence directory: {args.evidence_dir}")
    profile_code = qualification_exit_code(result, model)
    if profile_code:
        return profile_code
    return audit_gate_exit_code(getattr(result, "audit", None), args.audit_gate)


def command_check_mesh(args: argparse.Namespace) -> int:
    model = load_model(args.input)
    apply_verification_profile(model, args.verification_profile)
    report = check_mesh(model)
    if args.json_report is not None:
        save_result(report, args.json_report)
    print(f"MESH STATUS: {report.status}")
    if args.json_report is not None:
        print(f"json report: {args.json_report}")
    for message in report.errors:
        print(f"ERROR: {message}")
    for message in report.warnings:
        print(f"WARNING: {message}")
    return mesh_profile_exit_code(report, model)


def command_inspect(args: argparse.Namespace) -> int:
    model = load_model(args.input)
    apply_verification_profile(model, args.verification_profile)
    audit = inspect_model(model, detail=args.detail)
    data = audit.to_dict()
    if args.output is None and args.markdown is None:
        print(json.dumps(data, indent=2))
    if args.output is not None:
        save_result(audit, args.output)
        print(f"AUDIT STATUS: {audit.mesh_status}")
        print(f"output: {args.output}")
    if args.markdown is not None:
        save_audit_markdown(audit, args.markdown)
        print(f"AUDIT STATUS: {audit.mesh_status}")
        print(f"markdown: {args.markdown}")
    gate_code = audit_gate_exit_code(audit, args.audit_gate)
    if gate_code:
        return gate_code
    if audit.mesh_status == "FAIL":
        return int(ExitCode.INPUT_OR_MESH)
    if audit.mesh_status == "WARNING" and verification_profile(model.verification_profile).fail_on_warning:
        return int(ExitCode.QUALIFICATION_REJECTED)
    return int(ExitCode.ACCEPTED)


def command_evidence(args: argparse.Namespace) -> int:
    model = load_model(args.input)
    apply_verification_profile(model, args.verification_profile)
    result = solve_model(model, enforce_policy=False)
    paths = save_evidence(model, result, args.output, input_path=args.input)
    print(f"EVIDENCE STATUS: {result.status}")
    print(f"RUN VERDICT: {result.run_verdict.value}")
    print(f"evidence directory: {args.output}")
    print(f"qualification summary: {paths['qualification_summary']}")
    return qualification_exit_code(result, model)


def command_methods(_: argparse.Namespace) -> int:
    for analysis, methods in list_methods().items():
        print(f"{analysis}: {', '.join(methods)}")
    return 0


def audit_gate_exit_code(audit: object, policy: str) -> int:
    if policy == "none":
        return 0
    if audit is None or not hasattr(audit, "checks"):
        print("AUDIT GATE: FAIL no audit available")
        return int(ExitCode.INPUT_OR_MESH)
    counts = check_status_counts(audit.checks)
    if audit_gate_failed(audit.checks, policy):
        print(
            "AUDIT GATE: FAIL "
            f"policy={policy} PASS={counts['PASS']} WARNING={counts['WARNING']} FAIL={counts['FAIL']}"
        )
        return int(ExitCode.INPUT_OR_MESH)
    print(
        "AUDIT GATE: PASS "
        f"policy={policy} PASS={counts['PASS']} WARNING={counts['WARNING']} FAIL={counts['FAIL']}"
    )
    return 0


def qualification_exit_code(result: object, model: object) -> int:
    """Map a result policy verdict to the stable qualification exit code."""
    summary = qualification_summary(result, model)
    if summary["status"] == RunVerdict.FAIL.value:
        print("QUALIFICATION GATE: FAIL " + "; ".join(summary["blocking_errors"]))
        return int(ExitCode.QUALIFICATION_REJECTED)
    if summary["status"] == RunVerdict.WARNING.value:
        print("QUALIFICATION GATE: WARNING " + "; ".join(summary["warnings"]))
    return int(ExitCode.ACCEPTED)


def mesh_profile_exit_code(report: object, model: object) -> int:
    """Apply warning policy to a mesh-only command."""
    if report.status == "FAIL":
        return int(ExitCode.INPUT_OR_MESH)
    profile = verification_profile(getattr(model, "verification_profile", "engineering"))
    if report.status == "WARNING" and profile.fail_on_warning:
        print(f"QUALIFICATION GATE: FAIL mesh warning rejected by profile={profile.name}")
        return int(ExitCode.QUALIFICATION_REJECTED)
    return int(ExitCode.ACCEPTED)


def apply_verification_profile(model: object, profile: str | None) -> None:
    if profile is not None:
        model.verification_profile = verification_profile(profile).name


def _surface_quads(model: object) -> object:
    quads = [element.nodes for element in model.elements if element.type == "MITC4"]
    if quads:
        return np.asarray(quads, dtype=int)
    raise ValueError("PNG export currently supports MITC4 surface elements only.")
