"""Build the compact, versioned WP12 R4 report from its frozen raw evidence."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts import run_wp12_expanded_code_aster as engine  # noqa: E402


METRICS = (
    "displacement_relative_l2",
    "displacement_relative_linf",
    "reaction_relative_l2",
    "reaction_relative_linf",
    "strain_energy_from_external_work_relative",
    "qf_free_residual_relative_l2",
    "qf_force_equilibrium_relative",
    "aster_force_equilibrium_relative",
    "qf_moment_equilibrium_relative",
    "aster_moment_equilibrium_relative",
    "fixed_displacement_abs_max",
)


def _maxima(audit: dict[str, Any]) -> dict[str, float | None]:
    maxima: dict[str, float | None] = {}
    for metric in METRICS:
        values = [
            float(record.get("metrics_recomputed_from_raw", {}).get(metric, float("nan")))
            for record in audit.get("cases", {}).values()
        ]
        finite = [value for value in values if math.isfinite(value)]
        maxima[metric] = max(finite) if finite else None
    return maxima


def _render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# WP12 R4 — extended model-gallery Code_Aster correlation",
        "",
        f"Status: **{summary['status']}**",
        "",
        f"Independent raw-evidence audit: **{summary['independent_audit']['status']}** — {summary['independent_audit']['pass_count']}/{summary['case_count']} cases.",
        "",
        "## Coverage",
        "",
        f"The campaign adds {summary['case_count']} fresh solver-correlation cases to the 144 verified R3.6 cases, for {summary['cumulative_case_count']} cumulative case comparisons.",
        "",
        "| Dimension | Coverage |",
        "|---|---:|",
        f"| New cross-section topologies | {len(summary['coverage']['geometry'])} |",
        f"| Material parameter sets | {len(summary['coverage']['material_variant'])} |",
        f"| Element families | {len(summary['coverage']['family'])} |",
        "| Mesh levels per topology | 3, longitudinal-only H1/H2/H3 |",
        "| Load cases per model/mesh | 4 |",
        f"| Fresh Code_Aster comparisons | {summary['candidate_cases_passed']}/{summary['case_count']} |",
        "",
        "### Cases by topology",
        "",
        "| Topology | Cases | PASS | FAIL/HOLD |",
        "|---|---:|---:|---:|",
    ]
    for name, row in summary["coverage"]["geometry"].items():
        lines.append(f"| {name} | {row['cases']} | {row['passed']} | {row['failed']} |")
    lines.extend(["", "### Cases by material", "", "| Material | Cases | PASS | FAIL/HOLD |", "|---|---:|---:|---:|"])
    for name, row in summary["coverage"]["material_variant"].items():
        lines.append(f"| {name} | {row['cases']} | {row['passed']} | {row['failed']} |")
    lines.extend(["", "### Largest independently recomputed metrics", "", "| Metric | Maximum | Frozen gate |", "|---|---:|---:|"])
    for metric, value in summary["maxima_across_cases"].items():
        limit = summary["gates"].get(metric, "n/a")
        displayed = f"`{value:.6e}`" if value is not None else "not available"
        lines.append(f"| {metric} | {displayed} | `{limit}` |")
    lines.extend(
        [
            "",
            "## Execution and provenance",
            "",
            f"- Branch: `{summary['provenance']['branch']}`",
            f"- Execution SHA: `{summary['provenance']['execution_sha']}`",
            f"- Contract SHA-256: `{summary['provenance']['contract_sha256']}`",
            f"- Manifest SHA-256: `{summary['provenance']['manifest_sha256']}` ({summary['provenance']['manifested_raw_file_count']} raw files)",
            f"- Independent audit SHA-256: `{summary['provenance']['audit_sha256']}`",
            f"- Code_Aster: {summary['execution']['code_aster_version']} in the pinned image; fresh container per case; sequential, one CPU, MPI disabled.",
            f"- Execution window: {summary['execution']['started_utc']} to {summary['execution']['finished_utc']}.",
            "- Raw run directories remain local and ignored; the frozen contract, manifest, audit, compact summary and this report are versioned.",
            "",
            "## Interpretation and limitations",
            "",
            "This is same-discrete-mesh solver correlation: both solvers receive the same coordinates, connectivity, material, fixed root plane and equivalent nodal loads. It is not experimental validation, an independent physical benchmark, or a mesh-convergence proof. The three mesh levels refine only the longitudinal direction. No stress-field, nonlinear, contact, dynamics, buckling, or MPI/scaling claim is made. The campaign is supplemental and does not change WP12 official points or the global ledger.",
            "",
            "## Validation",
            "",
            f"- Targeted tests: {summary['validation']['targeted_tests']}",
            f"- Compileall: {summary['validation']['compileall']}",
            f"- Ruff: {summary['validation']['ruff']}",
            f"- Mypy: {summary['validation']['mypy']}",
            "- Full repository test suite: not run.",
            "",
            "`OFFICIAL_POINTS_CHANGED = NO`  ",
            "`GLOBAL_LEDGER_CHANGED = NO`  ",
            "`PUSH = NO`  ",
            "`MERGE = NO`",
            "",
        ]
    )
    return "\n".join(lines)


def build(contract_path: Path, raw_root: Path, audit_path: Path, validation: dict[str, str]) -> dict[str, Any]:
    contract_path = contract_path.resolve()
    raw_root = raw_root.resolve()
    audit_path = audit_path.resolve()
    contract = engine.load_json(contract_path)
    audit = engine.load_json(audit_path)
    raw = engine.load_json(raw_root / "wp12_gallery_r4_raw_summary.json")
    manifest_path = (ROOT / contract["manifest_path"]).resolve()
    manifest = engine.load_json(manifest_path)
    if audit.get("contract_sha256") != engine.sha256_file(contract_path):
        raise RuntimeError("Independent audit is not bound to the frozen R4 contract.")
    if audit.get("audit_status") not in {"PASS_WITH_LIMITATIONS", "FAIL_CLOSED"}:
        raise RuntimeError("Independent audit has an unknown terminal status.")
    if audit.get("case_count") != contract.get("case_count") or audit.get("case_pass_count") != raw.get("candidate_cases_passed"):
        raise RuntimeError("Raw summary and independent audit case counts disagree.")
    if raw.get("contract_sha256") != engine.sha256_file(contract_path):
        raise RuntimeError("Raw execution summary contract hash mismatch.")
    if raw.get("case_count") != contract.get("case_count"):
        raise RuntimeError("Raw execution summary case count differs from contract.")
    manifest_entries = manifest.get("files")
    if not isinstance(manifest_entries, dict) or not manifest_entries:
        raise RuntimeError("R4 raw manifest is missing or empty.")
    if engine.sha256_file(raw_root / "wp12_gallery_r4_raw_summary.json") != manifest_entries.get(
        "wp12_gallery_r4_raw_summary.json", {}
    ).get("sha256"):
        raise RuntimeError("Raw execution summary is not bound by the manifest.")
    status = "PASS_WITH_LIMITATIONS" if audit.get("audit_status") == "PASS_WITH_LIMITATIONS" else "FAIL_CLOSED"
    maxima = _maxima(audit)
    coverage = raw.get("coverage", {})
    summary = {
        "schema": "wp12-r4-gallery-compact-summary-v1",
        "work_package": "WP12",
        "revision": contract["revision"],
        "status": status,
        "case_count": int(contract["case_count"]),
        "candidate_cases_passed": int(raw.get("candidate_cases_passed", 0)),
        "cumulative_case_count": int(contract["case_count_breakdown"]["cumulative_with_r3_6"]),
        "coverage": coverage,
        "independent_audit": {
            "status": audit["audit_status"],
            "pass_count": audit["case_pass_count"],
            "error_count": len(audit.get("errors", [])),
            "audit_path": contract["audit_path"],
        },
        "maxima_across_cases": maxima,
        "gates": contract["gates"],
        "provenance": {
            "branch": contract["branch"],
            "branch_base_sha": contract["branch_base_sha"],
            "execution_sha": raw["execution_sha"],
            "runner_sha": contract["runner_sha"],
            "model_builder_sha": contract["model_builder_sha"],
            "auditor_sha": contract["auditor_sha"],
            "contract_builder_sha": contract["contract_builder_sha"],
            "contract_sha256": engine.sha256_file(contract_path),
            "manifest_sha256": engine.sha256_file(manifest_path),
            "audit_sha256": engine.sha256_file(audit_path),
            "raw_summary_sha256": engine.sha256_file(raw_root / "wp12_gallery_r4_raw_summary.json"),
            "manifested_raw_file_count": len(manifest_entries),
            "manifested_raw_bytes": sum(int(item["size_bytes"]) for item in manifest_entries.values()),
            "r3_6_prior_audit_status": contract["extends_campaign"]["recomputed_audit_status"],
        },
        "execution": {
            "code_aster_version": contract["code_aster_version"],
            "image": contract["code_aster_image"],
            "image_id": raw["code_aster_image_id"],
            "started_utc": raw["execution_started_utc"],
            "finished_utc": raw["execution_finished_utc"],
            "sequential": True,
            "cpu_per_container": 1,
            "mpi": False,
            "fresh_container_per_case": True,
            "process_nonzero_exit_count": sum(
                1 for record in raw.get("cases", {}).values() if record.get("process", {}).get("exit_code") != 0
            ),
        },
        "validation": validation,
        "limitations": contract["limitations"],
        "official_points_changed": False,
        "ledger_changed": False,
        "push_performed": False,
        "merge_performed": False,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--targeted-tests", default="not run")
    parser.add_argument("--compileall", default="not run")
    parser.add_argument("--ruff", default="not run")
    parser.add_argument("--mypy", default="not run")
    args = parser.parse_args()
    contract_path = args.contract if args.contract.is_absolute() else ROOT / args.contract
    raw_root = args.raw_root if args.raw_root.is_absolute() else ROOT / args.raw_root
    audit_path = args.audit if args.audit.is_absolute() else ROOT / args.audit
    contract = engine.load_json(contract_path)
    validation = {
        "targeted_tests": args.targeted_tests,
        "compileall": args.compileall,
        "ruff": args.ruff,
        "mypy": args.mypy,
        "full_repository_suite": "NOT_RUN",
    }
    summary = build(contract_path, raw_root, audit_path, validation)
    summary_path = ROOT / contract["summary_path"]
    report_path = ROOT / contract["report_path"]
    if summary_path.exists() or report_path.exists():
        raise SystemExit("Refusing to overwrite existing R4 summary or report.")
    engine.write_json(summary_path, summary)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_markdown(summary), encoding="utf-8", newline="\n")
    print(json.dumps({"status": summary["status"], "cases": summary["candidate_cases_passed"], "summary": str(summary_path), "report": str(report_path)}, indent=2))
    return 0 if summary["status"] == "PASS_WITH_LIMITATIONS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
