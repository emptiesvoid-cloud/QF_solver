"""Controlled numerical comparisons for the standard sparse linear methods."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix

from solveur.core.linear_methods import LinearSystemSolver
from solveur.core.linear_policy import LinearSolverPolicy


_TOLERANCE = 1.0e-10
_METHODS = {
    "symmetric_positive_definite": ("direct", "cg", "minres", "gmres", "bicgstab"),
    "nonsymmetric": ("direct", "gmres", "bicgstab"),
}


def run_linear_solver_comparison() -> dict[str, Any]:
    """Compare eligible standard methods to a direct solution on two matrices.

    The matrices are deterministic and independent from finite-element
    assembly. Element-level agreement remains covered by the meshed cantilever
    benchmark; this campaign verifies the algebraic solver contracts.
    """
    rows: list[dict[str, Any]] = []
    all_pass = True
    for name, matrix, rhs in _controlled_systems():
        direct_solution, direct_info = LinearSystemSolver().solve(matrix, rhs, method="direct")
        selection = LinearSolverPolicy.assess(matrix, "direct", {})
        method_rows: list[dict[str, Any]] = []
        for method in _METHODS[name]:
            if method == "direct":
                solution, info = direct_solution, direct_info
            else:
                solution, info = LinearSystemSolver().solve(
                    matrix,
                    rhs,
                    method=method,
                    parameters={
                        "rtol": 1.0e-12,
                        "atol": 1.0e-14,
                        "maxiter": 1000,
                        "preconditioner": "jacobi",
                    },
                )
            relative_error = float(
                np.linalg.norm(solution - direct_solution) / max(float(np.linalg.norm(direct_solution)), 1.0)
            )
            passed = info.converged and relative_error <= _TOLERANCE and info.residual_norm <= _TOLERANCE
            all_pass = all_pass and passed
            method_rows.append(
                {
                    "method": method,
                    "iterations": int(info.iterations),
                    "residual_norm": float(info.residual_norm),
                    "relative_solution_error_vs_direct": relative_error,
                    "status": "PASS" if passed else "FAIL",
                }
            )
        rows.append(
            {
                "case": name,
                "matrix_contract": selection.to_dict(used_method="direct")["matrix_contract"],
                "recommended_method": selection.recommended_method,
                "excluded_methods": _excluded_methods(name),
                "methods": method_rows,
            }
        )
    return {
        "study_id": "VNV-LINEAR-SOLVERS-001",
        "purpose": "direct-versus-iterative sparse solver comparison",
        "acceptance": {
            "relative_solution_error_max": _TOLERANCE,
            "residual_norm_max": _TOLERANCE,
        },
        "cases": rows,
        "status": "PASS" if all_pass else "FAIL",
    }


def write_linear_solver_comparison(output_dir: str | Path) -> dict[str, Any]:
    """Write portable JSON and Markdown evidence for the controlled study."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    report = run_linear_solver_comparison()
    (root / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (root / "report.md").write_text(_markdown(report), encoding="utf-8")
    return report


def _controlled_systems() -> tuple[tuple[str, csr_matrix, np.ndarray], ...]:
    return (
        (
            "symmetric_positive_definite",
            csr_matrix(
                np.array(
                    [[6.0, -2.0, 0.0, 0.0], [-2.0, 7.0, -1.0, 0.0], [0.0, -1.0, 5.0, -1.0], [0.0, 0.0, -1.0, 4.0]]
                )
            ),
            np.array([1.0, 2.0, -1.0, 3.0]),
        ),
        (
            "nonsymmetric",
            csr_matrix(
                np.array(
                    [[6.0, 2.0, 0.0, 0.0], [-1.0, 7.0, 1.0, 0.0], [0.0, -2.0, 5.0, 1.0], [0.0, 0.0, -1.0, 4.0]]
                )
            ),
            np.array([1.0, 2.0, -1.0, 3.0]),
        ),
    )


def _excluded_methods(case: str) -> list[dict[str, str]]:
    if case == "nonsymmetric":
        return [
            {"method": "cg", "reason": "requires an SPD matrix"},
            {"method": "minres", "reason": "requires a symmetric matrix"},
        ]
    return []


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# VNV-LINEAR-SOLVERS-001",
        "",
        f"Verdict: **{report['status']}**.",
        "",
        "La voie directe est l'oracle algebrique. Les matrices sont controlees hors assemblage EF; le benchmark poutre couvre l'accord sur un systeme EF symetrique.",
    ]
    for case in report["cases"]:
        lines.extend(["", f"## {case['case']}", "", "| Methode | Iterations | Residu | Ecart relatif | Verdict |", "| --- | ---: | ---: | ---: | --- |"])
        for row in case["methods"]:
            lines.append(
                f"| {row['method']} | {row['iterations']} | {row['residual_norm']:.3e} | "
                f"{row['relative_solution_error_vs_direct']:.3e} | {row['status']} |"
            )
        for excluded in case["excluded_methods"]:
            lines.append(f"- `{excluded['method']}` exclu: {excluded['reason']}.")
    return "\n".join(lines) + "\n"
