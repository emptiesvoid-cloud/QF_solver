"""Controlled numerical comparisons for the standard sparse linear methods."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix, diags

from solveur.core.linear_methods import LinearSystemSolver
from solveur.core.linear_policy import LinearSolverPolicy
from solveur.verification.vnv_manifest import write_vnv_manifest


_TOLERANCE = 1.0e-10
_METHODS = {
    "symmetric_positive_definite": ("direct", "cg", "minres", "gmres", "bicgstab"),
    "nonsymmetric": ("direct", "gmres", "bicgstab"),
}


@dataclass(frozen=True)
class _ControlledSystem:
    """Small deterministic matrix used to verify algebraic solver contracts."""

    name: str
    solver_family: str
    matrix: csr_matrix
    rhs: np.ndarray
    origin: str


def run_linear_solver_comparison() -> dict[str, Any]:
    """Compare eligible standard methods to a direct solution on two matrices.

    The matrices are deterministic and independent from finite-element
    assembly. Element-level agreement remains covered by the meshed cantilever
    benchmark; this campaign verifies the algebraic solver contracts. The
    32-DOF systems are intentionally still small enough for a dense condition
    estimate. That estimate is diagnostic only and is never used by the
    production large-model path.
    """
    rows: list[dict[str, Any]] = []
    all_pass = True
    for system in _controlled_systems():
        name = system.name
        matrix = system.matrix
        rhs = system.rhs
        started = time.perf_counter()
        direct_solution, direct_info = LinearSystemSolver().solve(matrix, rhs, method="direct")
        direct_elapsed = max(time.perf_counter() - started, 0.0)
        selection = LinearSolverPolicy.assess(matrix, "direct", {})
        condition_number = float(np.linalg.cond(matrix.toarray()))
        method_rows: list[dict[str, Any]] = []
        for method in _METHODS[system.solver_family]:
            started = time.perf_counter()
            if method == "direct":
                solution, info = direct_solution, direct_info
                elapsed = direct_elapsed
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
                elapsed = max(time.perf_counter() - started, 0.0)
            relative_error = float(
                np.linalg.norm(solution - direct_solution) / max(float(np.linalg.norm(direct_solution)), 1.0)
            )
            relative_residual = float(
                info.residual_norm / max(float(np.linalg.norm(rhs)), float(np.linalg.norm(matrix @ solution)), 1.0)
            )
            passed = info.converged and relative_error <= _TOLERANCE and relative_residual <= _TOLERANCE
            all_pass = all_pass and passed
            method_rows.append(
                {
                    "method": method,
                    "iterations": int(info.iterations),
                    "residual_norm": float(info.residual_norm),
                    "relative_residual": relative_residual,
                    "relative_solution_error_vs_direct": relative_error,
                    "solve_time_seconds": elapsed,
                    "preconditioner": info.preconditioner,
                    "status": "PASS" if passed else "FAIL",
                }
            )
        rows.append(
            {
                "case": name,
                "origin": system.origin,
                "dimension": int(matrix.shape[0]),
                "nnz": int(matrix.nnz),
                "condition_number_2": condition_number,
                "matrix_contract": selection.to_dict(used_method="direct")["matrix_contract"],
                "recommended_method": selection.recommended_method,
                "excluded_methods": _excluded_methods(system.solver_family),
                "methods": method_rows,
            }
        )
    return {
        "study_id": "VNV-LINEAR-SOLVERS-001",
        "purpose": "direct-versus-iterative sparse solver comparison with contract diagnostics",
        "diagnostic_policy": {
            "condition_number": "2-norm estimate on controlled matrices only; no dense conversion in production paths",
            "timing": "informational only; not an acceptance criterion because it depends on the host",
            "reference": "direct sparse solve for the controlled algebraic systems",
        },
        "acceptance": {
            "relative_solution_error_max": _TOLERANCE,
            "relative_residual_max": _TOLERANCE,
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
    write_vnv_manifest(root, report["study_id"])
    return report


def _controlled_systems() -> tuple[_ControlledSystem, ...]:
    n = 32
    chain_rhs = np.sin(np.linspace(0.2, 2.8, n))
    nonsymmetric_rhs = np.cos(np.linspace(0.1, 2.9, n))
    return (
        _ControlledSystem(
            "symmetric_positive_definite",
            "symmetric_positive_definite",
            csr_matrix(
                np.array(
                    [[6.0, -2.0, 0.0, 0.0], [-2.0, 7.0, -1.0, 0.0], [0.0, -1.0, 5.0, -1.0], [0.0, 0.0, -1.0, 4.0]]
                )
            ),
            np.array([1.0, 2.0, -1.0, 3.0]),
            "controlled SPD reference matrix",
        ),
        _ControlledSystem(
            "nonsymmetric",
            "nonsymmetric",
            csr_matrix(
                np.array(
                    [[6.0, 2.0, 0.0, 0.0], [-1.0, 7.0, 1.0, 0.0], [0.0, -2.0, 5.0, 1.0], [0.0, 0.0, -1.0, 4.0]]
                )
            ),
            np.array([1.0, 2.0, -1.0, 3.0]),
            "controlled nonsymmetric reference matrix",
        ),
        _ControlledSystem(
            "symmetric_positive_definite_32",
            "symmetric_positive_definite",
            diags((-np.ones(n - 1), 2.0 * np.ones(n), -np.ones(n - 1)), (-1, 0, 1), format="csr"),
            chain_rhs,
            "32-DOF scalar bar-like stiffness chain",
        ),
        _ControlledSystem(
            "nonsymmetric_32",
            "nonsymmetric",
            diags(
                (-1.25 * np.ones(n - 1), 3.0 * np.ones(n), -0.75 * np.ones(n - 1)),
                (-1, 0, 1),
                format="csr",
            ),
            nonsymmetric_rhs,
            "32-DOF nonsymmetric transport-like chain",
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
        "Les conditionnements sont des diagnostics sur ces petites matrices uniquement; les temps sont informatifs et ne constituent pas un critere de qualification.",
    ]
    for case in report["cases"]:
        lines.extend(
            [
                "",
                f"## {case['case']} ({case['dimension']} DDL)",
                "",
                f"Origine : {case['origin']}. `nnz={case['nnz']}`, conditionnement 2-norme : `{case['condition_number_2']:.3e}`.",
                "",
                "| Methode | Iterations | Residu relatif | Ecart relatif | Temps [s] | Verdict |",
                "| --- | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for row in case["methods"]:
            lines.append(
                f"| {row['method']} | {row['iterations']} | {row['relative_residual']:.3e} | "
                f"{row['relative_solution_error_vs_direct']:.3e} | {row['solve_time_seconds']:.3e} | {row['status']} |"
            )
        for excluded in case["excluded_methods"]:
            lines.append(f"- `{excluded['method']}` exclu: {excluded['reason']}.")
    return "\n".join(lines) + "\n"
