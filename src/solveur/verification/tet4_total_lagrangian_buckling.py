"""Euler buckling benchmark for the total-Lagrangian TET4 tangent."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Callable

import numpy as np

from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.io.manifest import write_json_file
from solveur.materials.solid import SolidMaterial
from solveur.verification.tet4_total_lagrangian_assembly import (
    _relative_error,
    _structured_tet4_mesh,
    _unique_edges,
)
from solveur.verification.total_lagrangian_structural import (
    smallest_tangent_eigenpair,
    solve_proportional_dead_load,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


class TotalLagrangianBucklingCampaign:
    """Track loss of tangent positivity for a clamped Euler column."""

    study_id = "VNV-TET4-TL-BUCKLING-EULER-006"
    levels = ((16, 4, 4), (24, 6, 6), (32, 8, 8), (40, 10, 10))

    def __init__(
        self,
        output_dir: str | Path,
        *,
        levels: tuple[tuple[int, int, int], ...] | None = None,
    ):
        self.output_dir = Path(output_dir).resolve()
        self.levels = levels or self.levels
        self.young = 1.0e6
        self.poisson = 0.3
        self.length = 4.0
        self.height = 0.5
        self.depth = 0.5
        self.material = SolidMaterial(E=self.young, nu=self.poisson)

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        reference = euler_cantilever_critical_load(
            self.young, self.depth * self.height**3 / 12.0, self.length
        )
        rows: list[dict[str, object]] = []
        finest_plot: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None
        for cells in self.levels:
            row, nodes, elements, mode = self.evaluate_level(cells, reference)
            rows.append(row)
            finest_plot = nodes, elements, mode
        for index, row in enumerate(rows):
            row["change_from_previous"] = None if index == 0 else _relative_error(
                float(row["critical_load"]), float(rows[index - 1]["critical_load"])
            )
        final_error = float(rows[-1]["euler_relative_error"])
        final_change = float(rows[-1]["change_from_previous"])
        checks = [
            _upper_check("euler_critical_load_error", final_error, 0.10),
            _upper_check("critical_load_refinement_change", final_change, 0.10),
            _upper_check(
                "critical_load_bracket",
                max(float(row["relative_bracket_width"]) for row in rows),
                5.0e-3,
            ),
            _lower_check(
                "positive_precritical_jacobian",
                min(float(row["minimum_det_f"]) for row in rows),
                0.9,
            ),
        ]
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_BUCKLING_RESEARCH" if passed else "FAIL",
            "maturity": "research",
            "reference": {
                "type": "euler_clamped_free_column",
                "formula": "pi^2 E I / (4 L^2)",
                "critical_load": reference,
                "young": self.young,
                "inertia": self.depth * self.height**3 / 12.0,
                "length": self.length,
            },
            "levels": rows,
            "checks": checks,
            "limitations": [
                "The square TET4 section converges slowly in bending because of first-order solid locking.",
                "The benchmark detects a bifurcation from the precritical tangent; it is not a postbuckling solve.",
                "The load is a conservative nodal dead load with a perfectly straight reference geometry.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot_convergence(rows, reference)
        if finest_plot is not None:
            self._plot_mode(*finest_plot)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def evaluate_level(
        self, cells: tuple[int, int, int], reference: float | None = None
    ) -> tuple[dict[str, object], np.ndarray, np.ndarray, np.ndarray]:
        """Evaluate one structured refinement level without changing campaign defaults."""
        started = perf_counter()
        analytical = reference or euler_cantilever_critical_load(
            self.young, self.depth * self.height**3 / 12.0, self.length
        )
        nodes, elements = _structured_tet4_mesh(
            *cells, self.length, self.height, self.depth
        )
        assembly = TotalLagrangianTet4Assembly(nodes, elements, self.material)
        fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
        fixed = (3 * fixed_nodes[:, None] + np.arange(3)).reshape(-1)
        free = np.setdiff1d(np.arange(assembly.ndof), fixed)
        tip_nodes = np.flatnonzero(np.isclose(nodes[:, 0], self.length))
        pattern = np.zeros(assembly.ndof, dtype=float)
        pattern[3 * tip_nodes] = -1.0 / tip_nodes.size
        result = self._critical_load(assembly, pattern, fixed, free, analytical)
        row = {
            "cells": list(cells),
            "elements": int(elements.shape[0]),
            "dofs": int(assembly.ndof),
            "critical_load": result["load"],
            "euler_relative_error": _relative_error(float(result["load"]), analytical),
            "relative_bracket_width": result["relative_bracket_width"],
            "normalized_tangent_eigenvalue": result["normalized_eigenvalue"],
            "minimum_det_f": result["minimum_det_f"],
            "axial_tip_displacement": result["axial_tip_displacement"],
            "evaluations": result["evaluations"],
            "elapsed_seconds": perf_counter() - started,
        }
        return row, nodes, elements, result["mode"]

    def _critical_load(
        self,
        assembly: TotalLagrangianTet4Assembly,
        load_pattern: np.ndarray,
        fixed: np.ndarray,
        free: np.ndarray,
        reference: float,
    ) -> dict[str, object]:
        zero = np.zeros(assembly.ndof, dtype=float)
        _, initial_tangent = assembly.assemble(zero)
        assert initial_tangent is not None
        preload = 0.05 * reference
        equilibrium = solve_proportional_dead_load(
            assembly,
            preload * load_pattern,
            fixed,
            increments=6,
        )
        # Buckling uses only the initial-stress geometric contribution.  The
        # full tangent difference also contains the material tangent and
        # therefore does not represent the geometric eigenproblem.
        tangent_rate = assembly.geometric_tangent(equilibrium.displacement) / preload
        evaluations: dict[float, tuple[float, np.ndarray]] = {}

        def evaluate(load_value: float) -> float:
            key = float(load_value)
            if key not in evaluations:
                linearized_tangent = initial_tangent + key * tangent_rate
                initial_mode = None
                if evaluations:
                    nearest = min(evaluations, key=lambda known: abs(known - key))
                    initial_mode = evaluations[nearest][1]
                eigenvalue, mode = smallest_tangent_eigenpair(
                    linearized_tangent.tocsr(), free, initial_mode=initial_mode
                )
                evaluations[key] = (eigenvalue, mode)
            return evaluations[key][0]

        lower = 0.0
        lower_value = evaluate(lower)
        upper = 1.25 * reference
        upper_value = evaluate(upper)
        while upper_value > 0.0 and upper < 5.0 * reference:
            upper *= 1.5
            upper_value = evaluate(upper)
        if lower_value <= 0.0 or upper_value >= 0.0:
            raise RuntimeError("Could not bracket the first tangent eigenvalue sign change.")
        lower, upper, lower_value, upper_value = refine_sign_change(
            evaluate, lower, upper, lower_value, upper_value, tolerance=2.5e-3
        )
        best_load = min((lower, upper), key=lambda value: abs(evaluate(value)))
        eigenvalue, mode = evaluations[best_load]
        tangent_scale = max(abs(evaluations[0.0][0]), np.finfo(float).tiny)
        tip_nodes = np.flatnonzero(np.isclose(assembly.nodes[:, 0], self.length))
        return {
            "load": best_load,
            "mode": mode,
            "normalized_eigenvalue": abs(eigenvalue) / tangent_scale,
            "relative_bracket_width": (upper - lower) / max(best_load, np.finfo(float).tiny),
            "minimum_det_f": equilibrium.minimum_det_f,
            "preload": preload,
            "preload_relative_residual": equilibrium.relative_residual,
            "axial_tip_displacement": float(np.mean(equilibrium.displacement[3 * tip_nodes])),
            "evaluations": [
                {"load": load, "smallest_eigenvalue": values[0]}
                for load, values in sorted(evaluations.items())
            ],
        }

    def _plot_convergence(self, rows: list[dict[str, object]], reference: float) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        elements = [int(row["elements"]) for row in rows]
        loads = [float(row["critical_load"]) for row in rows]
        figure, axis = plt.subplots(figsize=(7.6, 4.5))
        axis.semilogx(elements, loads, "o-", color="#006d77", label="QF_solver")
        axis.axhline(reference, color="#bc4749", linestyle="--", label="Euler")
        axis.set_xlabel("Nombre de TET4")
        axis.set_ylabel("Charge critique")
        axis.grid(True, which="both", alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "buckling_convergence.png", dpi=180)
        plt.close(figure)

    def _plot_mode(self, nodes: np.ndarray, elements: np.ndarray, mode: np.ndarray) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        mode_nodes = mode.reshape(-1, 3)
        lateral = np.linalg.norm(mode_nodes[:, 1:], axis=1)
        scale = 0.8 / max(float(np.max(lateral)), np.finfo(float).tiny)
        deformed = nodes + scale * mode_nodes
        edges = _unique_edges(elements)
        sampled = edges[:: max(1, len(edges) // 800)]
        figure = plt.figure(figsize=(9.0, 4.8))
        axis = figure.add_subplot(111, projection="3d")
        for coordinates, color, label in (
            (nodes, "#6c757d", "initial"),
            (deformed, "#d1495b", "mode amplifie"),
        ):
            for edge in sampled:
                axis.plot(*coordinates[list(edge)].T, color=color, linewidth=0.4, alpha=0.55)
            axis.scatter([], [], [], color=color, label=label)
        axis.set_box_aspect((4.0, 1.0, 1.0))
        axis.legend()
        axis.set_title("Premier mode de flambement tangent")
        figure.tight_layout()
        figure.savefig(self.output_dir / "buckling_mode.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "La charge critique est detectee lorsque la plus petite valeur propre de la "
            "tangente precontrainte change de signe. La reference est la colonne d'Euler "
            "encastree-libre.",
            "",
            "| Elements | DDL | P critique | Ecart Euler | Variation | Intervalle | det(F) | Temps |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in summary["levels"]:
            change = "-" if row["change_from_previous"] is None else f"{100*row['change_from_previous']:.2f} %"
            lines.append(
                f"| {row['elements']} | {row['dofs']} | {row['critical_load']:.6e} | "
                f"{100*row['euler_relative_error']:.2f} % | {change} | "
                f"{100*row['relative_bracket_width']:.3f} % | {row['minimum_det_f']:.6f} | "
                f"{row['elapsed_seconds']:.1f} s |"
            )
        lines.extend(
            [
                "",
                "![Convergence de la charge critique](buckling_convergence.png)",
                "",
                "![Mode de flambement](buckling_mode.png)",
                "",
                "Le critere porte sur la charge critique globale. Les contraintes locales et "
                "la branche post-critique sont traitees dans des etudes separees.",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def euler_cantilever_critical_load(young: float, inertia: float, length: float) -> float:
    """Return Pcr = pi^2 E I / (4 L^2) for a clamped-free column."""
    if min(young, inertia, length) <= 0.0:
        raise ValueError("Euler buckling parameters must be strictly positive.")
    return float(np.pi**2 * young * inertia / (4.0 * length**2))


def refine_sign_change(
    function: Callable[[float], float],
    lower: float,
    upper: float,
    lower_value: float,
    upper_value: float,
    *,
    tolerance: float,
    maximum_iterations: int = 12,
) -> tuple[float, float, float, float]:
    """Refine a signed bracket with safeguarded secant iterations."""
    if lower_value > 0.0 and upper_value < 0.0:
        pass
    else:
        raise ValueError("refine_sign_change requires a positive-to-negative bracket.")
    for _ in range(maximum_iterations):
        if (upper - lower) / max(abs(upper), 1.0) <= tolerance:
            break
        estimate = lower - lower_value * (upper - lower) / (upper_value - lower_value)
        margin = 0.1 * (upper - lower)
        estimate = float(np.clip(estimate, lower + margin, upper - margin))
        value = function(estimate)
        if value > 0.0:
            lower, lower_value = estimate, value
        else:
            upper, upper_value = estimate, value
    return lower, upper, lower_value, upper_value


def _upper_check(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}


def _lower_check(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value >= limit else "FAIL"}
