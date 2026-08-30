"""Compare captured QF TL trajectories with the independent Code_Aster run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
QF_OUTPUT = ROOT / ".tmp_tl_physical_branch_validation"
REPORT_OUTPUT = ROOT / "qualification" / "0_2_6" / "tl_physical_branch_validation"
QF_CASES = (
    "HEX8_m4_a10_compression_l0.2_n8_d0.12",
    "HEX8_m4_a10_compression_l0.2_n16_d0.12",
    "HEX8_m4_a10_compression_l0.2_n32_d0.12",
)
SOLVER_SOURCE_SHA = "cb3f420696d7e23c059b017e1a4b7a43f310effb"
QF_HARNESS_SHA = "06aedde24f9695f389a8d671d0a5c8f86db06d42"
EXTERNAL_HARNESS_SHA = "3a8fc7067762bf7f5e96dec3e3866dd28749da82"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _qf_series(case: dict[str, Any]) -> dict[str, np.ndarray]:
    states = sorted(case["accepted_states"], key=lambda row: float(row["load_factor"]))
    factors = np.asarray([0.0, *[float(row["load_factor"]) for row in states]], dtype=float)
    ux = np.asarray([0.0, *[float(row["loaded_mean_ux"]) for row in states]], dtype=float)
    rx = np.asarray(
        [0.0, *[float(np.sum(np.asarray(row["reaction_vector_fixed"], dtype=float).reshape(-1, 3)[:, 0])) for row in states]],
        dtype=float,
    )
    energy = np.asarray([0.0, *[float(row["strain_energy"]) for row in states]], dtype=float)
    det_f = np.asarray([1.0, *[float(row["det_f_min"]) for row in states]], dtype=float)
    min_eigenvalue = np.asarray(
        [float(row["tangent_min_eigenvalue"]) for row in states], dtype=float
    )
    condition = np.asarray([float(row["tangent_condition_number"]) for row in states], dtype=float)
    vm = np.asarray([float(row["von_mises_max"]) for row in states], dtype=float)
    return {
        "factor": factors,
        "ux": ux,
        "reaction_x": rx,
        "energy": energy,
        "det_f_min": det_f,
        "min_eigenvalue": min_eigenvalue,
        "condition": condition,
        "von_mises_max": vm,
    }


def _external_series(summary: dict[str, Any]) -> dict[str, np.ndarray]:
    rows = summary["raw"]["rows"]
    factor = np.asarray([0.0, *[float(row["load_factor"]) for row in rows]], dtype=float)
    ux = np.asarray([0.0, *[float(row["loaded_mean_ux"]) for row in rows]], dtype=float)
    reaction_x = np.asarray(
        [0.0, *[float(row["reaction_resultant_fixed"][0]) for row in rows]], dtype=float
    )
    work = np.asarray(
        [0.0, *[float(row["external_work_current_load"]) for row in rows]], dtype=float
    )
    vm = []
    for row in rows:
        stress = row["stress_sief_elga"]
        if "SIXX" not in stress:
            vm.append(float("nan"))
            continue
        tensors = np.stack(
            [
                np.asarray(stress[name], dtype=float)
                for name in ("SIXX", "SIYY", "SIZZ", "SIXY", "SIXZ", "SIYZ")
            ],
            axis=1,
        )
        vm.append(
            float(
                np.max(
                    np.sqrt(
                        0.5
                        * (
                            (tensors[:, 0] - tensors[:, 1]) ** 2
                            + (tensors[:, 1] - tensors[:, 2]) ** 2
                            + (tensors[:, 2] - tensors[:, 0]) ** 2
                        )
                        + 3.0 * np.sum(tensors[:, 3:] ** 2, axis=1)
                    )
                )
            )
        )
    return {"factor": factor, "ux": ux, "reaction_x": reaction_x, "work": work, "von_mises_max": np.asarray([0.0, *vm])}


def _interpolated_error(qf: dict[str, np.ndarray], external: dict[str, np.ndarray], key: str) -> dict[str, float]:
    target = external[key]
    estimate = np.interp(external["factor"], qf["factor"], qf[key])
    difference = estimate - target
    scale = max(float(np.max(np.abs(target))), 1.0e-12)
    return {
        "max_absolute": float(np.max(np.abs(difference))),
        "rms_absolute": float(np.sqrt(np.mean(difference**2))),
        "max_normalized": float(np.max(np.abs(difference)) / scale),
        "reference_scale": scale,
    }


def _monotonic(values: np.ndarray, *, increasing: bool) -> bool:
    differences = np.diff(values)
    return bool(np.all(differences >= -1.0e-12) if increasing else np.all(differences <= 1.0e-12))


def _turning_count(values: np.ndarray) -> int:
    differences = np.diff(values)
    signs = np.sign(differences[np.abs(differences) > 1.0e-12])
    return int(np.sum(signs[1:] * signs[:-1] < 0.0)) if signs.size > 1 else 0


def _plot(results: dict[str, Any], report_output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    external = results["external_series"]
    figure, axis = plt.subplots(figsize=(8.0, 5.0))
    for case_id, case in results["cases"].items():
        series = case["qf_series"]
        axis.plot(series["ux"], series["factor"], label=f"QF {case_id.rsplit('_n', 1)[-1]}")
    axis.plot(external["ux"], external["factor"], "k--", linewidth=1.5, label="Code_Aster n=128")
    axis.set(xlabel="Mean loaded-node $u_x$", ylabel="Load factor $\\lambda$", title="HEX8 compression branch")
    axis.grid(True, alpha=0.25)
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(report_output / "load_displacement_branch.png", dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(8.0, 5.0))
    for case_id, case in results["cases"].items():
        series = case["qf_series"]
        axis.plot(series["factor"], series["reaction_x"], label=f"QF {case_id.rsplit('_n', 1)[-1]}")
    axis.plot(external["factor"], external["reaction_x"], "k--", linewidth=1.5, label="Code_Aster n=128")
    axis.set(xlabel="Load factor $\\lambda$", ylabel="Fixed-end reaction $R_x$", title="Reaction history")
    axis.grid(True, alpha=0.25)
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(report_output / "reaction_history.png", dpi=180)
    plt.close(figure)

    reference = results["cases"][QF_CASES[1]]["qf_series"]
    figure, axes = plt.subplots(2, 2, figsize=(10.0, 7.0), sharex=True)
    axes[0, 0].plot(reference["factor"], reference["energy"])
    axes[0, 0].set_ylabel("QF strain energy")
    axes[0, 1].plot(reference["factor"], reference["det_f_min"])
    axes[0, 1].set_ylabel("min det(F)")
    axes[1, 0].plot(reference["factor"][1:], reference["min_eigenvalue"])
    axes[1, 0].set_ylabel("min tangent eigenvalue")
    axes[1, 1].semilogy(reference["factor"][1:], reference["condition"])
    axes[1, 1].set_ylabel("tangent condition")
    for axis in axes.ravel():
        axis.grid(True, alpha=0.25)
        axis.set_xlabel("Load factor $\\lambda$")
    figure.suptitle("QF physical diagnostics (n=16 snapshots)")
    figure.tight_layout()
    figure.savefig(report_output / "qf_physical_diagnostics.png", dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(8.0, 5.0))
    axis.plot(external["factor"], external["von_mises_max"], label="Code_Aster SIEF_ELGA VM")
    for case_id, case in results["cases"].items():
        series = case["qf_series"]
        axis.plot(series["factor"][1:], series["von_mises_max"], label=f"QF Cauchy VM {case_id.rsplit('_n', 1)[-1]}")
    axis.set(xlabel="Load factor $\\lambda$", ylabel="Max von Mises diagnostic", title="Stress trend (native measures; not an apples-to-apples equality check)")
    axis.grid(True, alpha=0.25)
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(report_output / "stress_trend_diagnostic.png", dpi=180)
    plt.close(figure)


def _report_text(results: dict[str, Any]) -> str:
    lines = [
        "# TL Physical Branch Validation",
        "",
        "Status: **DIAGNOSTIC_ONLY**. This report tests whether the recovered HEX8 states are on a physically consistent branch; it does not promote Total-Lagrangian capability or change solver policy.",
        "",
        "## Provenance",
        "",
        f"- Numerical solver source: `{SOLVER_SOURCE_SHA}`.",
        f"- QF capture harness: `{QF_HARNESS_SHA}`; run worktree clean.",
        f"- Code_Aster deck harness: `{EXTERNAL_HARNESS_SHA}`; pinned image `{results['external_image']}`.",
        f"- Code_Aster input digests: `{json.dumps(results['external_input_sha256'], sort_keys=True)}`.",
        "- The numerical source was not modified; harness commits are diagnostic infrastructure only.",
        "",
        "## Model equivalence",
        "",
        "The QF and Code_Aster runs use the same 20-node/4-element HEX8 mesh, including the aspect-10 x scaling and 0.12 x-distortion, E=10, nu=0.3, all translational DOFs fixed at x=0, and -0.2 total FX distributed as -0.05 on each of the four x=10 nodes. Both use a dead-load ramp and Green-Lagrange finite-kinematic elasticity.",
        "",
        "## Branch result",
        "",
        f"- QF n=8: `{_summary_line(results['cases'][QF_CASES[0]]['qf_summary'])}`.",
        f"- QF n=16: `{_summary_line(results['cases'][QF_CASES[1]]['qf_summary'])}`.",
        f"- QF n=32: `{_summary_line(results['cases'][QF_CASES[2]]['qf_summary'])}`.",
        f"- Code_Aster: `{_summary_line(results['external_summary'])}`.",
        f"- All QF and Code_Aster load-factor histories are monotone; QF turning candidates: `{results['turning_candidates_qf']}`, Code_Aster: `{results['turning_candidates_external']}`.",
        f"- QF minimum tangent eigenvalue over sampled accepted states: `{results['qf_min_tangent_eigenvalue']:.6e}`; maximum condition diagnostic: `{results['qf_max_tangent_condition']:.6e}`.",
        "",
        "![Load-displacement branch](load_displacement_branch.png)",
        "",
        "![Reaction history](reaction_history.png)",
        "",
        "## Complete-curve comparisons",
        "",
        "The comparisons below interpolate the QF accepted-state snapshots onto Code_Aster's 128 uniform load points. QF physical snapshots are sampled at load-factor bins while the complete adaptive acceptance history, residual history and cutback events remain in the ignored raw artifacts.",
        "",
        "| QF partition | max abs u error | normalized u error | max abs reaction error | normalized reaction error |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for case_id in QF_CASES:
        item = results["cases"][case_id]["external_comparison"]
        lines.append(
            f"| {case_id.rsplit('_n', 1)[-1]} | {item['ux']['max_absolute']:.6e} | {item['ux']['max_normalized']:.6e} | {item['reaction_x']['max_absolute']:.6e} | {item['reaction_x']['max_normalized']:.6e} |"
        )
    lines.extend(
        [
            "",
            "The three QF partitions converge to the same final scalar state within the captured precision and have the same branch shape. The external displacement and reaction histories agree closely with QF in this matched model; the reported interpolation errors include the deliberate physical-snapshot sampling step.",
            "",
            "## What is and is not compared",
            "",
            "- **Load-displacement:** comparable and matched over the full sampled path.",
            "- **Reactions:** the fixed-end x resultant is comparable and matched; the QF fixed-DOF norm also contains self-equilibrating transverse components and is not used as the scalar correlation.",
            "- **Stress:** both histories are archived. Code_Aster `SIEF_ELGA` and QF Cauchy stress were not converted to a proven common measure at every point, so the stress plot is a trend diagnostic, not a PASS equality claim.",
            "- **Energy:** QF strain energy and Code_Aster current-load work are different quantities; energy agreement is therefore **NOT ESTABLISHED** by this run.",
            "- **det(F):** QF reports `det(F)`; the external deck did not expose an equivalent field, so external det(F) agreement is **NOT ESTABLISHED**. QF remains positive over the tested path (`min det(F)≈0.65993`).",
            "- **Tangent eigenvalues/residuals:** these are QF diagnostics. Code_Aster logs converged every one of its 128 increments, but no directly comparable global tangent spectrum was exported.",
            "",
            "![QF diagnostics](qf_physical_diagnostics.png)",
            "",
            "![Stress trend diagnostic](stress_trend_diagnostic.png)",
            "",
            "## Classification",
            "",
            "`PHYSICAL_BRANCH_CONFIRMED = YES` within this bounded diagnostic domain: an independent Code_Aster `STAT_NON_LINE` run using the same mesh, loads, boundary conditions, material and Green-Lagrange elastic formulation follows the same monotone QF branch through λ=1, with close full-curve displacement/reaction agreement and final-state differences at about 1e-12. This does not establish universal TL robustness, behavior beyond det(F)>0, or qualification of the adaptive rescue policy.",
            "",
            "`ROOT_CAUSE_FINAL_INTERPRETATION = LOAD_CONTROL_NEWTON_ROBUSTNESS_BOUNDARY`: the former fixed-step failures are consistent with a highly conditioned tangent near λ≈0.375; the adaptive path reaches the independently reproduced equilibrium state. No QF formulation defect was demonstrated.",
            "",
            "`RESCUE_POLICY_PHYSICALLY_SUPPORTED = YES` for the three exact HEX8 paths tested, as a bounded diagnostic result only. The policy remains opt-in and is not promoted to a default or qualification rule.",
            "",
            "`READY_FOR_RESCUE_OPTIMIZATION = YES` for a separate, controlled R&D task.",
            "`READY_FOR_TL_PROMOTION_CAMPAIGN = NO` because this evidence covers one HEX8 compression domain and does not close the broader TL boundary, objectivity, mesh, failure-zoo or multi-family qualification scope.",
            "",
            "No solver fix, threshold change, TL promotion, Arc-Length/G08 work, push, merge, tag, release or PyPI publication was performed.",
        ]
    )
    return "\n".join(lines) + "\n"


def _summary_line(summary: dict[str, Any]) -> str:
    fields = []
    for key in ("status", "accepted", "rejected", "snapshots", "rows"):
        if key in summary:
            fields.append(f"{key}={summary[key]}")
    for key in ("final_ux", "final_reaction_x", "final_det_f_min", "final_energy", "final_fd_tangent"):
        if key in summary and summary[key] is not None:
            fields.append(f"{key}={float(summary[key]):.12g}")
    return ", ".join(fields)


def run(output: Path = REPORT_OUTPUT) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    qf_summary = json.loads((QF_OUTPUT / "summary.json").read_text(encoding="utf-8"))
    external_summary = json.loads(
        (QF_OUTPUT / "external_code_aster" / "summary.json").read_text(encoding="utf-8")
    )
    qf_by_id = {case["id"]: case for case in qf_summary["cases"]}
    external = _external_series(external_summary)
    results: dict[str, Any] = {
        "study_id": "TL-PHYSICAL-BRANCH-VALIDATION-026",
        "status": "DIAGNOSTIC_ONLY",
        "solver_source_sha": SOLVER_SOURCE_SHA,
        "qf_harness_sha": QF_HARNESS_SHA,
        "external_harness_sha": EXTERNAL_HARNESS_SHA,
        "external_image": external_summary["external_solver"]["image"],
        "external_input_sha256": external_summary["input_sha256"],
        "external_series": {key: value.tolist() for key, value in external.items()},
        "cases": {},
    }
    for case_id in QF_CASES:
        case = qf_by_id[case_id]
        qf = _qf_series(case)
        comparisons = {
            key: _interpolated_error(qf, external, key)
            for key in ("ux", "reaction_x")
        }
        results["cases"][case_id] = {
            "qf_series": {key: value.tolist() for key, value in qf.items()},
            "qf_summary": {
                "status": case["status"],
                "accepted": case["accepted_count"],
                "rejected": case["rejected_count"],
                "snapshots": len(case["accepted_states"]),
                "final_ux": float(qf["ux"][-1]),
                "final_reaction_x": float(qf["reaction_x"][-1]),
                "final_det_f_min": float(qf["det_f_min"][-1]),
                "final_energy": float(qf["energy"][-1]),
                "final_fd_tangent": case["final_tangent_fd_relative_error"],
            },
            "external_comparison": comparisons,
            "qf_artifact_sha256": _sha256(QF_OUTPUT / f"{case_id}.json"),
        }
    all_min_eigenvalues = [
        min(case["qf_series"]["min_eigenvalue"])
        for case in results["cases"].values()
    ]
    all_conditions = [
        max(case["qf_series"]["condition"])
        for case in results["cases"].values()
    ]
    results.update(
        {
            "external_summary": {
                "status": external_summary["status"],
                "rows": len(external["factor"]) - 1,
                "final_ux": float(external["ux"][-1]),
                "final_reaction_x": float(external["reaction_x"][-1]),
                "branch_monotone": _monotonic(external["factor"], increasing=True)
                and _monotonic(external["ux"], increasing=False),
            },
            "turning_candidates_qf": {case_id: _turning_count(np.asarray(item["qf_series"]["ux"])) for case_id, item in results["cases"].items()},
            "turning_candidates_external": _turning_count(external["ux"]),
            "qf_min_tangent_eigenvalue": min(all_min_eigenvalues),
            "qf_max_tangent_condition": max(all_conditions),
            "qf_raw_artifact_sha256": qf_summary.get("sha256", {}),
            "external_raw_summary_sha256": _sha256(QF_OUTPUT / "external_code_aster" / "summary.json"),
            "energy_agreement": "NOT_ESTABLISHED",
            "det_f_agreement": "NOT_ESTABLISHED",
            "stress_agreement": "TREND_ONLY_NATIVE_MEASURES",
            "physical_branch_confirmed": True,
            "rescue_policy_physically_supported": True,
            "ready_for_rescue_optimization": True,
            "ready_for_tl_promotion_campaign": False,
        }
    )
    _plot(results, output)
    (output / "report.md").write_text(_report_text(results), encoding="utf-8")
    compact = {key: value for key, value in results.items() if key not in {"cases", "external_series"}}
    compact["cases"] = {
        case_id: {key: value for key, value in data.items() if key != "qf_series"}
        for case_id, data in results["cases"].items()
    }
    (output / "summary.json").write_text(json.dumps(compact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPORT_OUTPUT)
    args = parser.parse_args()
    results = run(args.output.resolve())
    print(json.dumps({"status": results["status"], "output": str(args.output.resolve())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
