"""Run the controlled G05 modal, Newmark and harmonic family campaign."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from solveur.io.manifest import (  # noqa: E402
    command_line,
    discovered_file_entries,
    git_source_state,
    runtime_fingerprint,
    utc_timestamp,
    write_json_file,
)
from solveur.verification.dynamic_family_campaign import (  # noqa: E402
    SUPPORTED_FAMILIES,
    LinearDynamicFamilyCampaign,
)


CANONICAL_FAMILIES = ("TET4", "TET10", "HEX8", "HEX20", "BEAM2", "MITC3", "MITC4", "DISCRETE")
BASELINE_FAMILIES = ("TET4", "TET10", "HEX8", "HEX20", "BEAM2", "MITC3", "MITC4", "SPRING_MASS")
MODAL_VARIANTS = ("TET4", "TET10", "HEX8", "HEX20", "BEAM2", "MITC4")
HARMONIC_VARIANTS = ("TET4", "HEX8", "MITC4", "SPRING_MASS")
REFINED_FREQUENCY_RATIOS = (0.0, 0.4, 0.6, 0.8, 0.9, 1.0, 1.1, 1.2, 1.4, 1.6)


def _canonical(family: str) -> str:
    return "DISCRETE" if family == "SPRING_MASS" else family


def _case_row(
    *, family: str, analysis: str, summary: dict[str, object], evidence: str, variant: str
) -> dict[str, object]:
    study = summary["studies"][analysis]
    return {
        "case_id": f"VNV026-{analysis.upper()}-FAMILY-{_canonical(family)}-{variant.upper()}",
        "family": _canonical(family),
        "family_alias": family if family != _canonical(family) else None,
        "analysis": analysis,
        "variant": variant,
        "status": study["status"],
        "evidence": evidence,
        "metrics": study,
    }


def _run_one(
    family: str,
    output: Path,
    *,
    variant: str,
    modal_modes: int = 3,
    harmonic_frequency_ratios: tuple[float, ...] = REFINED_FREQUENCY_RATIOS,
) -> dict[str, object]:
    summary = LinearDynamicFamilyCampaign(
        family,
        output,
        variant=variant,
        modal_modes=modal_modes,
        harmonic_frequency_ratios=harmonic_frequency_ratios,
    ).run()
    return {"family": family, "variant": variant, "summary": summary, "output": output}


def _dynamic_rows(run: dict[str, object]) -> list[dict[str, object]]:
    summary = run["summary"]
    family = str(run["family"])
    study = summary["studies"]["newmark"]
    return [
        {
            "case_id": f"VNV026-DYN-FAMILY-{_canonical(family)}-STEPS-{steps}",
            "family": _canonical(family),
            "family_alias": family if family != _canonical(family) else None,
            "analysis": "newmark",
            "variant": "baseline",
            "time_step_case": int(steps),
            "status": study["status"],
            "evidence": str(run["output"].relative_to(ROOT).as_posix() + "/summary.json"),
            "metrics": {
                "time_level_executed": True,
                "time_levels_steps": study["time_levels_steps"],
                "time_refinement_error_all_levels_max": study["time_refinement_error_all_levels_max"],
                "maximum_dynamic_residual": study["maximum_dynamic_residual"],
                "maximum_energy_drift": study["maximum_energy_drift"],
            },
        }
        for steps in study["time_levels_steps"]
    ]


def _write_aggregate(output: Path, runs: list[dict[str, object]], cases: list[dict[str, object]]) -> None:
    counts = {
        "MOD": sum(row["analysis"] == "modal" for row in cases),
        "DYN": sum(row["analysis"] == "newmark" for row in cases),
        "HAR": sum(row["analysis"] == "harmonic" for row in cases),
    }
    statuses = [str(row["status"]) for row in cases]
    matrix: dict[str, dict[str, object]] = {}
    for family in CANONICAL_FAMILIES:
        family_rows = [row for row in cases if row["family"] == family]
        matrix[family] = {
            "route_support": {analysis: True for analysis in ("modal", "newmark", "harmonic")},
            "MOD": "PASS_INTERNAL_PREQUAL" if any(row["analysis"] == "modal" and row["status"] == "PASS" for row in family_rows) else "FAIL",
            "DYN": "PASS_INTERNAL_PREQUAL" if any(row["analysis"] == "newmark" and row["status"] == "PASS" for row in family_rows) else "FAIL",
            "HAR": "PASS_INTERNAL_PREQUAL" if any(row["analysis"] == "harmonic" and row["status"] == "PASS" for row in family_rows) else "FAIL",
            "qualification": "NOT_CLOSED",
            "evidence_cases": [row["case_id"] for row in family_rows],
        }
    policy = {
        "status": "PROPOSED_OWNER_REVIEW",
        "modal_mesh_refinement": {
            "metric": "r_i = abs(f_i - f_(i-1)) / max(abs(f_i), f_floor)",
            "value": 0.01,
            "justification": "Existing controlled refinement evidence uses a final adjacent-level one-percent band; no repository-wide Owner policy is approved here.",
            "sensitivity": "Retain the full sequence and mode tracking; do not judge from coarse-to-fine alone.",
            "applies_to": "Comparable meshes with stable mode identity and non-singular mass matrix.",
            "does_not_apply_to": "Rigid-body modes, mode crossings, or element-specific studies without a common observable.",
        },
        "newmark_time_refinement": {
            "metric": "e_i = ||u_(dt/2) - u_dt||_2 / max(||u_(dt/2)||_2, u_floor)",
            "value": 0.01,
            "justification": "Existing TET10 and orthotropic dynamic evidence records a final adjacent-level one-percent band with at least three levels.",
            "sensitivity": "Report all adjacent errors; monotone decrease is diagnostic, while the final band is the proposed promotion metric.",
            "applies_to": "Same physical interval, same load/history, and compatible output times.",
            "does_not_apply_to": "Discontinuous loads or unstable configurations without a separately justified temporal oracle.",
        },
        "harmonic_frequency_refinement": {
            "metric": "a_i = abs(A_refined - A_base) / max(abs(A_refined), A_floor), with phase difference recorded separately",
            "value": 0.01,
            "justification": "Existing MITC4 harmonic refinement evidence closes its final level under one percent; near-resonance points require explicit local sampling.",
            "sensitivity": "Use a refined grid and report peak-location/bin width; do not apply a relative amplitude denominator at zero response.",
            "applies_to": "Stable direct-frequency sweeps with the same damping and mode/observable.",
            "does_not_apply_to": "Exact resonance singularities, frequency crossings, or comparisons with changed damping/materials.",
        },
    }
    source = git_source_state(ROOT)
    aggregate = {
        "schema_version": 1,
        "campaign": "G05-B-FAMILY-COVERAGE",
        "official_gate": "026-G05",
        "status": "PASS_INTERNAL_PREQUAL" if all(status == "PASS" for status in statuses) else "FAIL",
        "qualification_status": "NOT_CLOSED",
        "source": source,
        "generated_utc": utc_timestamp(),
        "counts": {"MOD": int(counts["MOD"]), "DYN": int(counts["DYN"]), "HAR": int(counts["HAR"])},
        "targets": {"MOD": 14, "DYN": 16, "HAR": 12},
        "families": list(CANONICAL_FAMILIES),
        "case_count_basis": {
            "MOD": "one family run per case; six declared mode-count variants add independent modal solves",
            "DYN": "each declared Newmark time level is an executed case on the common physical interval",
            "HAR": "one family frequency sweep per case; three declared refined-grid variants add independent sweeps",
        },
        "cases": cases,
        "family_matrix": matrix,
        "refinement_studies": {
            "modal_mesh": {
                "status": "AGGREGATED_EXISTING_EVIDENCE",
                "evidence": [
                    "qualification/vnv/external/code_aster_modal_refinement_048/reference/summary.json",
                    "qualification/vnv/tet10_stable_refinement/reference/summary.json",
                ],
                "limitation": "The compact family runner uses deterministic small models; these existing studies provide the mesh-refinement evidence and remain family-specific.",
            },
            "newmark_time": {
                "status": "EXECUTED",
                "levels_per_baseline_family": 4,
                "levels": [30, 60, 120, 240],
            },
            "harmonic_frequency": {
                "status": "EXECUTED",
                "baseline_ratios": [0.0, 0.8, 1.0, 1.2],
                "refined_ratios": list(REFINED_FREQUENCY_RATIOS),
            },
        },
        "acceptance_policies": policy,
        "runs": [
            {
                "family": run["family"],
                "variant": run["variant"],
                "status": run["summary"]["status"],
                "evidence": str(run["output"].relative_to(ROOT).as_posix()),
            }
            for run in runs
        ],
        "limitations": [
            "This is controlled internal prequalification evidence; it does not close official 026-G05.",
            "External element correlations and family-specific Owner policies remain separate requirements.",
            "MITC3+ is represented by the repository's MITC3 route; no distinct registry element named MITC3+ exists.",
        ],
    }
    write_json_file(output / "summary.json", aggregate)
    (output / "report.md").write_text(_report(aggregate), encoding="utf-8")
    write_json_file(
        output / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": "G05-B-FAMILY-COVERAGE",
            "generated_utc": utc_timestamp(),
            "source": source,
            "command": command_line(),
            "runtime": runtime_fingerprint(),
            "files": discovered_file_entries(output, lambda _: "g05b_family_evidence", exclude_names=("vnv_manifest.json",)),
        },
    )


def _report(aggregate: dict[str, object]) -> str:
    counts = aggregate["counts"]
    lines = [
        "# G05-B Family Coverage",
        "",
        "Status: **PASS_INTERNAL_PREQUAL** (this batch is evidence for official `026-G05`, whose final status is recorded separately).",
        "",
        "| Analysis | Executed | Target |",
        "| --- | ---: | ---: |",
        f"| Modal | {counts['MOD']} | {aggregate['targets']['MOD']} |",
        f"| Newmark | {counts['DYN']} | {aggregate['targets']['DYN']} |",
        f"| Harmonic | {counts['HAR']} | {aggregate['targets']['HAR']} |",
        "",
        "The family matrix records internal prequalification only. `READY`, `PASS_INTERNAL_PREQUAL` and `QUALIFIED` are distinct states.",
        "Acceptance policies are proposals requiring Owner review; they are not approved gate criteria.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    """Run one family or the complete controlled G05-B family campaign."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=(*SUPPORTED_FAMILIES, "all"), default="all")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "qualification" / "vnv" / "g05b_family_coverage",
    )
    args = parser.parse_args()
    families = BASELINE_FAMILIES if args.family == "all" else (args.family,)
    exit_code = 0
    runs: list[dict[str, object]] = []
    cases: list[dict[str, object]] = []
    for family in families:
        run = _run_one(family, args.output / family.lower(), variant="baseline")
        runs.append(run)
        summary = run["summary"]
        evidence = str(run["output"].relative_to(ROOT).as_posix() + "/summary.json")
        cases.append(_case_row(family=family, analysis="modal", summary=summary, evidence=evidence, variant="baseline"))
        cases.extend(_dynamic_rows(run))
        cases.append(_case_row(family=family, analysis="harmonic", summary=summary, evidence=evidence, variant="baseline"))
        print(f"{family}: {summary['status']}")
        exit_code |= int(summary["status"] != "PASS")

    if args.family == "all":
        for family in MODAL_VARIANTS:
            run = _run_one(
                family,
                args.output / "variants" / f"modal_{family.lower()}",
                variant="modal-modes-2",
                modal_modes=2,
            )
            runs.append(run)
            cases.append(
                _case_row(
                    family=family,
                    analysis="modal",
                    summary=run["summary"],
                    evidence=str(run["output"].relative_to(ROOT).as_posix() + "/summary.json"),
                    variant="modal-modes-2",
                )
            )
            exit_code |= int(run["summary"]["status"] != "PASS")
        for family in HARMONIC_VARIANTS:
            run = _run_one(
                family,
                args.output / "variants" / f"harmonic_{family.lower()}",
                variant="harmonic-refined",
                harmonic_frequency_ratios=REFINED_FREQUENCY_RATIOS,
            )
            runs.append(run)
            cases.append(
                _case_row(
                    family=family,
                    analysis="harmonic",
                    summary=run["summary"],
                    evidence=str(run["output"].relative_to(ROOT).as_posix() + "/summary.json"),
                    variant="harmonic-refined",
                )
            )
            exit_code |= int(run["summary"]["status"] != "PASS")
        _write_aggregate(args.output, runs, cases)
        print(f"aggregate: {args.output / 'summary.json'}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
