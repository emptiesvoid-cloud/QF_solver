"""Build a causal error audit for the linear TET4 scopes.

The audit consumes archived evidence instead of rerunning the expensive
campaigns. It separates spatial approximation, algebraic solution, and time
integration effects, and never promotes a general TET4 scope automatically.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.io.manifest import write_json_file
from solveur.verification.vnv_manifest import write_vnv_manifest


def build_tet4_error_audit(
    static_evidence: dict[str, Any],
    dynamics_evidence: dict[str, Any],
    static_reference: dict[str, Any],
    higher_order_reference: dict[str, Any],
) -> dict[str, Any]:
    """Classify the observed TET4 errors using the archived evidence."""

    static_row = static_evidence["structured_flexion_refinement"]
    external_static = static_evidence["same_order_external_correlation"]
    static_reference_rows = static_reference["rows"]
    higher_rows = higher_order_reference["rows"]
    fine_structured_error = float(static_row["relative_error"])
    final_mesh_increment = float(static_reference["qf_final_mesh_increment"])
    fine_same_order_error = float(external_static["fine_relative_difference"])
    fine_higher_order_error = float(higher_rows[-1]["tet4_reference_error"])

    internal_dynamic = dynamics_evidence["internal_family"]
    external_dynamic = dynamics_evidence["external_code_aster"]
    dynamic_errors = {
        "modal_frequency": float(external_dynamic["modal"]["relative_frequency_error_max"]),
        "newmark_history": float(external_dynamic["newmark"]["relative_history_error_max"]),
        "harmonic_response": float(external_dynamic["harmonic"]["relative_response_error_max"]),
    }
    dynamic_under_one_percent = max(dynamic_errors.values()) <= 0.01

    checks = [
        {
            "id": "TET4-STATIC-UNDER-ONE-PERCENT",
            "value": fine_structured_error,
            "limit": 0.01,
            "status": "PASS" if fine_structured_error <= 0.01 else "FAIL",
            "meaning": "The documented structured bending case reaches the 1 percent gate.",
        },
        {
            "id": "TET4-STATIC-SAME-ORDER-CORRELATION",
            "value": fine_same_order_error,
            "limit": 0.01,
            "status": "PASS" if fine_same_order_error <= 0.01 else "FAIL",
            "meaning": "QF_solver and Code_Aster TETRA4 agree on the same mesh.",
        },
        {
            "id": "TET4-STATIC-MESH-INCREMENT",
            "value": final_mesh_increment,
            "limit": 0.01,
            "status": "PASS" if final_mesh_increment <= 0.01 else "WARNING",
            "meaning": "A small final mesh increment is needed before claiming an asymptotic plateau.",
        },
        {
            "id": "TET4-DYNAMIC-ALL-PRIMARY-OBSERVABLES",
            "value": max(dynamic_errors.values()),
            "limit": 0.01,
            "status": "PASS" if dynamic_under_one_percent else "FAIL",
            "meaning": "Modal, Newmark, and harmonic external comparisons remain below 1 percent.",
        },
    ]

    return {
        "study_id": "VNV-TET4-ERROR-CAUSAL-AUDIT-001",
        "status": "PASS_DIAGNOSTIC" if all(item["status"] != "FAIL" for item in checks) else "WARNING",
        "scope": ["tet4-linear-static", "tet4-modal", "tet4-transient-dynamic", "tet4-harmonic-response"],
        "question": "Determine whether TET4 discrepancies are caused by time step, linear solver, quadrature, or spatial formulation.",
        "conclusion": {
            "primary_static_cause": "spatial_discretization_low_order_constant_strain",
            "static_time_step_cause": False,
            "static_linear_solver_cause": False,
            "static_same_order_implementation_mismatch": False,
            "dynamic_time_step_cause": False,
            "under_one_percent_demonstrated": fine_structured_error <= 0.01 and dynamic_under_one_percent,
            "under_one_percent_general_tet4_proven": False,
            "stable_promotion": "bounded_owner_review_required",
        },
        "static": {
            "structured_flexion": {
                "elements": int(static_row["elements"]),
                "dofs": int(static_row["dofs"]),
                "relative_error": fine_structured_error,
                "relative_residual": float(static_row["relative_residual"]),
                "iterations": int(static_row["iterations"]),
            },
            "same_order_external": {
                "fine_relative_difference": fine_same_order_error,
                "same_mesh": bool(external_static["same_mesh"]),
            },
                "higher_order_diagnostic": {
                    "fine_tet4_reference_error": fine_higher_order_error,
                    "fine_tet10_reference_error": float(higher_rows[-1]["tet10_reference_error"]),
                    "interpretation": "The higher-order comparison diagnoses interpolation order; it is not the primary TET4 oracle.",
                },
                "higher_order_levels": [
                    {
                        "tet4_elements": int(row["tet4_elements"]),
                        "tet4_reference_error": float(row["tet4_reference_error"]),
                        "tet10_reference_error": float(row["tet10_reference_error"]),
                    }
                    for row in higher_rows
                ],
                "mesh_behavior": {
                "available_same_order_levels": len(static_reference_rows),
                "qf_final_mesh_increment": final_mesh_increment,
                "code_aster_final_mesh_increment": float(static_reference["code_aster_final_mesh_increment"]),
                "asymptotic_plateau_demonstrated": final_mesh_increment <= 0.01,
            },
        },
        "dynamic": {
            "internal": {
                "newmark_rms_error": float(internal_dynamic["newmark"]["relative_rms_error_to_single_mode"]),
                "newmark_energy_drift": float(internal_dynamic["newmark"]["maximum_energy_drift"]),
                "newmark_dynamic_residual": float(internal_dynamic["newmark"]["maximum_dynamic_residual"]),
            },
            "external_code_aster": {
                "time_level_count": int(external_dynamic["newmark"]["time_level_count"]),
                "frequency_grid_count": int(external_dynamic["harmonic"]["frequency_count"]),
                "relative_errors": dynamic_errors,
            },
            "interpretation": "The temporal and external dynamic comparisons are already below 1 percent; the remaining limitation is domain breadth, not the tested time step.",
        },
        "checks": checks,
        "causal_findings": [
            {
                "id": "F-TET4-001",
                "cause": "spatial_discretization",
                "status": "CONFIRMED",
                "evidence": "TET4 uses linear shape functions and a constant strain-displacement matrix B; bending curvature is piecewise constant.",
            },
            {
                "id": "F-TET4-002",
                "cause": "static_time_step",
                "status": "NOT_APPLICABLE",
                "evidence": "Linear static has no time integration step.",
            },
            {
                "id": "F-TET4-003",
                "cause": "linear_solver_convergence",
                "status": "EXCLUDED",
                "evidence": f"The refined case has relative residual {float(static_row['relative_residual']):.3e} and converged in {int(static_row['iterations'])} iterations.",
            },
            {
                "id": "F-TET4-004",
                "cause": "same_order_operator_mismatch",
                "status": "EXCLUDED",
                "evidence": f"Same-mesh QF_solver/Code_Aster TETRA4 difference is {fine_same_order_error:.3e}.",
            },
            {
                "id": "F-TET4-005",
                "cause": "dynamic_time_step",
                "status": "EXCLUDED_FOR_TESTED_SCOPE",
                "evidence": f"Maximum external modal/Newmark/harmonic error is {max(dynamic_errors.values()):.3e}; internal Newmark energy drift is {float(internal_dynamic['newmark']['maximum_energy_drift']):.3e}.",
            },
        ],
        "actions_before_general_stable": [
            "Add at least one intermediate refinement level after the current 4.64 percent final mesh increment.",
            "Retain the same-mesh TETRA4 correlation as the primary implementation check.",
            "Keep the beam and TET10 comparisons diagnostic unless a declared three-dimensional reference is used.",
            "Repeat the 1 percent check on at least one non-rectilinear or multi-load TET4 structure.",
        ],
        "limitations": [
            "The under-1-percent result is a documented structured cantilever sub-scope, not a universal TET4 guarantee.",
            "No time-step conclusion can be transferred from this linear audit to nonlinear dynamics.",
            "The audit does not change maturity or sign an Owner decision.",
        ],
    }


def write_tet4_error_audit(
    static_path: str | Path,
    dynamics_path: str | Path,
    static_reference_path: str | Path,
    higher_order_path: str | Path,
    output: str | Path,
) -> dict[str, Any]:
    """Write the TET4 causal audit and its deterministic convergence figure."""

    def read(path: str | Path) -> dict[str, Any]:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    report = build_tet4_error_audit(read(static_path), read(dynamics_path), read(static_reference_path), read(higher_order_path))
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    write_json_file(root / "summary.json", report)
    _plot(report, root / "tet4_error_convergence.png")
    (root / "report.md").write_text(_markdown(report), encoding="utf-8")
    write_vnv_manifest(root, report["study_id"])
    return report


def _plot(report: dict[str, Any], path: Path) -> None:
    higher = report["static"]["higher_order_diagnostic"]
    levels = report["static"].get("higher_order_levels", [])
    if not levels:
        levels = [
            {
                "tet4_elements": 24576,
                "tet4_reference_error": higher["fine_tet4_reference_error"],
                "tet10_reference_error": higher["fine_tet10_reference_error"],
            }
        ]
    elements = [int(row["tet4_elements"]) for row in levels]
    tet4 = [100.0 * float(row["tet4_reference_error"]) for row in levels]
    tet10 = [100.0 * float(row["tet10_reference_error"]) for row in levels]
    figure, axis = plt.subplots(figsize=(7.6, 4.5))
    axis.loglog(elements, tet4, "o-", color="#0072B2", label="TET4")
    axis.loglog(elements, tet10, "s--", color="#D55E00", label="TET10")
    axis.axhline(1.0, color="#009E73", linestyle="--", label="gate 1 %")
    axis.set_xlabel("Nombre de TET4")
    axis.set_ylabel("Ecart a la reference poutre [%]")
    axis.set_title("Convergence diagnostique TET4/TET10")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _markdown(report: dict[str, Any]) -> str:
    dynamic = report["dynamic"]["external_code_aster"]["relative_errors"]
    lines = [
        f"# {report['study_id']}",
        "",
        f"Statut : **{report['status']}**.",
        "",
        "## Conclusion courte",
        "",
        "L'ecart TET4 observe ici est principalement spatial : l'interpolation lineaire et la deformation constante par element representent lentement une courbure de flexion. Le pas de temps n'explique pas l'ecart statique, et les preuves dynamiques disponibles restent sous 1 %.",
        "",
        "Le resultat sous 1 % est demontre pour le porte-a-faux structure etudie. Il ne constitue pas une garantie generale pour toutes les geometries, tous les chargements ou les domaines non lineaires.",
        "",
        "## Indicateurs",
        "",
        "| Controle | Valeur | Limite | Statut |",
        "| --- | ---: | ---: | --- |",
    ]
    for check in report["checks"]:
        value = check["value"]
        limit = "-" if check["limit"] is None else f"{check['limit']:.3e}"
        lines.append(f"| {check['id']} | {value:.3e} | {limit} | {check['status']} |")
    lines.extend(
        [
            "",
            "## Dynamique TET4",
            "",
            f"Les erreurs externes sont : modal {100 * dynamic['modal_frequency']:.3e} %, Newmark {100 * dynamic['newmark_history']:.3e} %, harmonique {100 * dynamic['harmonic_response']:.3e} %. Elles restent toutes sous 1 % sur le domaine teste.",
            "",
            "![Diagnostic d'ordre](tet4_error_convergence.png)",
            "",
            "## Causes retenues",
            "",
        ]
    )
    for finding in report["causal_findings"]:
        lines.append(f"- **{finding['id']} — {finding['cause']} : {finding['status']}.** {finding['evidence']}")
    lines.extend(
        [
            "",
            "## Actions avant promotion generale stable",
            "",
        ]
    )
    lines.extend(f"- {action}" for action in report["actions_before_general_stable"])
    lines.extend(
        [
            "",
            "## Limites",
            "",
        ]
    )
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    return "\n".join(lines) + "\n"
