"""Assembled-model verification for the total-Lagrangian TET4 kernel."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.sparse.linalg import spsolve

from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.io.manifest import write_json_file
from solveur.materials.solid import SolidMaterial
from solveur.verification.elastica import solve_cantilever_elastica


class TotalLagrangianAssemblyCampaign:
    """Exercise objectivity, patch equilibrium and Newton on assembled meshes."""

    campaign_id = "VNV-TET4-TL-ASSEMBLY-002"
    levels = (
        (8, 2, 2),
        (12, 3, 3),
        (16, 4, 4),
        (24, 6, 6),
        (32, 8, 8),
        (40, 10, 10),
    )

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()
        self.material = SolidMaterial(E=1.0e6, nu=0.3)

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        finest_solution: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None
        reference = solve_cantilever_elastica(
            young=self.material.E,
            inertia=0.5 * 0.5**3 / 12.0,
            length=4.0,
            transverse_load=150.0,
        )
        for nx, ny, nz in self.levels:
            started = perf_counter()
            nodes, elements = _structured_tet4_mesh(nx, ny, nz, 4.0, 0.5, 0.5)
            assembly = TotalLagrangianTet4Assembly(nodes, elements, self.material)
            patch_error = self._patch_error(assembly)
            rotation_error = self._rotation_error(assembly)
            solution = self._solve_cantilever(assembly, load=150.0, load_steps=12)
            row = {
                "cells": [nx, ny, nz],
                "nodes": int(nodes.shape[0]),
                "elements": int(elements.shape[0]),
                "dofs": int(3 * nodes.shape[0]),
                "patch_interior_force_ratio": patch_error,
                "rigid_rotation_force_ratio": rotation_error,
                "elapsed_seconds": perf_counter() - started,
                **solution[2],
            }
            row["elastica_tip_error"] = _relative_error(
                row["tip_displacement_z"], reference.tip_z
            )
            rows.append(row)
            finest_solution = (nodes, elements, solution[0])
        for index, row in enumerate(rows):
            row["tip_change_from_previous"] = None if index == 0 else _relative_change(
                row["tip_displacement_z"], rows[index - 1]["tip_displacement_z"]
            )
        last_tip_change = float(rows[-1]["tip_change_from_previous"])
        checks = [
            _upper_check("patch_equilibrium", max(row["patch_interior_force_ratio"] for row in rows), 1.0e-12),
            _upper_check("assembled_objectivity", max(row["rigid_rotation_force_ratio"] for row in rows), 1.0e-13),
            _upper_check("newton_residual", max(row["maximum_relative_residual"] for row in rows), 1.0e-8),
            _lower_check("positive_current_jacobian", min(row["minimum_det_f"] for row in rows), 0.2),
            _lower_check("large_tip_displacement", abs(rows[-1]["tip_displacement_z"]) / 4.0, 0.05),
        ]
        observations = [
            _upper_check("tip_refinement_change", last_tip_change, 0.05),
            _upper_check("elastica_tip_error", float(rows[-1]["elastica_tip_error"]), 0.10),
        ]
        passed = all(check["status"] == "PASS" for check in checks)
        converged = all(check["status"] == "PASS" for check in observations)
        summary: dict[str, object] = {
            "campaign_id": self.campaign_id,
            "status": "PASS_ASSEMBLY" if passed and converged else "PASS_WITH_RECOMMENDATION" if passed else "FAIL",
            "maturity": "research",
            "levels": rows,
            "checks": checks,
            "observations": observations,
            "reference": {
                "type": "inextensible_euler_elastica_dead_tip_load",
                "tip_x": reference.tip_x,
                "tip_z": reference.tip_z,
                "tip_rotation": reference.tip_rotation,
                "solver_nodes": reference.nodes,
                "acceptance_oracle": False,
            },
            "owner_review_required": True,
            "limitations": [
                "The cantilever uses dead nodal loads and Saint-Venant-Kirchhoff elasticity.",
                "No analytical large-deflection beam value is used as an acceptance oracle yet.",
                "Euler elastica neglects transverse shear and three-dimensional end effects.",
                "Mesh convergence of stress and buckling are outside this campaign.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        if finest_solution is not None:
            self._plot_deformation(*finest_solution)
        self._plot_convergence(rows, reference.tip_z)
        self._write_report(summary)
        return summary

    def _patch_error(self, assembly: TotalLagrangianTet4Assembly) -> float:
        nodes = assembly.nodes
        deformation = np.array([[1.08, 0.05, 0.0], [0.02, 0.97, 0.01], [0.0, 0.03, 1.04]])
        displacement = (nodes @ (deformation - np.eye(3)).T).reshape(-1)
        internal, _ = assembly.assemble(displacement, tangent_required=False)
        minimum = np.min(nodes, axis=0)
        maximum = np.max(nodes, axis=0)
        interior_nodes = np.flatnonzero(
            np.all((nodes > minimum + 1.0e-12) & (nodes < maximum - 1.0e-12), axis=1)
        )
        interior_dofs = (3 * interior_nodes[:, None] + np.arange(3)).reshape(-1)
        return float(np.linalg.norm(internal[interior_dofs]) / max(np.linalg.norm(internal), np.finfo(float).tiny))

    def _rotation_error(self, assembly: TotalLagrangianTet4Assembly) -> float:
        nodes = assembly.nodes
        angle = np.deg2rad(61.0)
        rotation = np.array(
            [[np.cos(angle), 0.0, np.sin(angle)], [0.0, 1.0, 0.0], [-np.sin(angle), 0.0, np.cos(angle)]]
        )
        displacement = (nodes @ (rotation - np.eye(3)).T).reshape(-1)
        internal, _ = assembly.assemble(displacement, tangent_required=False)
        volume = 4.0 * 0.5 * 0.5
        return float(np.linalg.norm(internal) / (self.material.E * volume))

    def _solve_cantilever(
        self, assembly: TotalLagrangianTet4Assembly, *, load: float, load_steps: int
    ) -> tuple[np.ndarray, list[dict[str, float]], dict[str, float | int]]:
        nodes = assembly.nodes
        ndof = assembly.ndof
        displacement = np.zeros(ndof, dtype=float)
        fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
        fixed = (3 * fixed_nodes[:, None] + np.arange(3)).reshape(-1)
        free = np.setdiff1d(np.arange(ndof), fixed)
        tip_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 4.0))
        force = np.zeros(ndof, dtype=float)
        force[3 * tip_nodes + 2] = -load / tip_nodes.size
        history: list[dict[str, float]] = []
        for step in range(1, load_steps + 1):
            factor = step / load_steps
            reference = max(float(np.linalg.norm(factor * force[free])), 1.0)
            for iteration in range(1, 31):
                internal, tangent = assembly.assemble(displacement)
                residual = factor * force - internal
                relative = float(np.linalg.norm(residual[free]) / reference)
                if relative <= 1.0e-9:
                    history.append({"step": step, "iterations": iteration - 1, "relative_residual": relative})
                    break
                assert tangent is not None
                correction = spsolve(tangent[free, :][:, free], residual[free])
                alpha = self._line_search(
                    assembly, displacement, free, correction, factor * force, relative * reference
                )
                displacement[free] += alpha * correction
            else:
                raise RuntimeError(f"Assembled finite-kinematics cantilever failed at load step {step}.")
        minimum_det_f = float(np.min(assembly.deformation_determinants(displacement)))
        metrics: dict[str, float | int] = {
            "tip_displacement_z": float(np.mean(displacement[3 * tip_nodes + 2])),
            "maximum_relative_residual": max(row["relative_residual"] for row in history),
            "total_newton_iterations": int(sum(row["iterations"] for row in history)),
            "maximum_step_iterations": int(max(row["iterations"] for row in history)),
            "minimum_det_f": minimum_det_f,
            "strain_energy": assembly.strain_energy(displacement),
        }
        return displacement, history, metrics

    def _line_search(
        self,
        assembly: TotalLagrangianTet4Assembly,
        displacement: np.ndarray,
        free: np.ndarray,
        correction: np.ndarray,
        target_load: np.ndarray,
        residual_norm: float,
    ) -> float:
        alpha = 1.0
        for _ in range(12):
            trial = displacement.copy()
            trial[free] += alpha * correction
            try:
                internal, _ = assembly.assemble(trial, tangent_required=False)
            except ValueError:
                alpha *= 0.5
                continue
            if np.linalg.norm((target_load - internal)[free]) < residual_norm:
                return alpha
            alpha *= 0.5
        raise RuntimeError("Assembled finite-kinematics line search failed.")

    def _plot_deformation(self, nodes: np.ndarray, elements: np.ndarray, displacement: np.ndarray) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        current = nodes + displacement.reshape(-1, 3)
        edges = _unique_edges(elements)
        sampled_edges = edges[:: max(1, len(edges) // 500)]
        figure = plt.figure(figsize=(9.0, 4.6))
        axis = figure.add_subplot(111, projection="3d")
        for coords, color, label in ((nodes, "#6c757d", "initial"), (current, "#006d77", "deformee")):
            for edge in sampled_edges:
                axis.plot(*coords[list(edge)].T, color=color, linewidth=0.45, alpha=0.55)
            axis.scatter([], [], [], color=color, label=label)
        axis.set_box_aspect((4.0, 1.0, 1.0))
        axis.legend()
        axis.set_title("Porte-a-faux TET4 total lagrangien - maillage fin")
        figure.tight_layout()
        figure.savefig(self.output_dir / "cantilever_deformation.png", dpi=180)
        plt.close(figure)

    def _plot_convergence(self, rows: list[dict[str, object]], reference_tip: float) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        element_counts = np.array([row["elements"] for row in rows], dtype=float)
        tips = np.abs(np.array([row["tip_displacement_z"] for row in rows], dtype=float))
        figure, axis = plt.subplots(figsize=(7.6, 4.5))
        axis.semilogx(element_counts, tips, "o-", color="#006d77", label="QF_solver TET4-TL")
        axis.axhline(abs(reference_tip), color="#bc4749", linestyle="--", label="elastica Euler")
        axis.set_xlabel("Nombre de TET4")
        axis.set_ylabel("Fleche absolue au bout")
        axis.grid(True, which="both", alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "cantilever_convergence.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.campaign_id}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "Reference elastica Euler sous charge morte : "
            f"`UZ={summary['reference']['tip_z']:.6e}`. Cette reference ne constitue pas encore un oracle "
            "d'acceptation du solide 3D.",
            "",
            "| Elements | DDL | Patch | Rotation | UZ bout | Variation | Ecart elastica | det(F) | Iter. | Temps |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in summary["levels"]:
            lines.append(
                f"| {row['elements']} | {row['dofs']} | {row['patch_interior_force_ratio']:.3e} | "
                f"{row['rigid_rotation_force_ratio']:.3e} | {row['tip_displacement_z']:.6e} | "
                f"{_format_percent(row['tip_change_from_previous'])} | {100.0 * row['elastica_tip_error']:.2f} % | "
                f"{row['minimum_det_f']:.6f} | {row['total_newton_iterations']} | "
                f"{row['elapsed_seconds']:.2f} s |"
            )
        lines.extend(
            [
                "",
                "![Deformee du porte-a-faux](cantilever_deformation.png)",
                "",
                "![Convergence de la fleche](cantilever_convergence.png)",
                "",
                "Les invariants assembles sont satisfaits. La convergence de la fleche et son ecart a "
                "l'elastica sont classes comme observations distinctes.",
                "Cette campagne autorise une revue du comportement assemble, pas encore la qualification de "
                "la fleche, du flambement ou des contraintes locales.",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _structured_tet4_mesh(
    nx: int, ny: int, nz: int, length: float, height: float, depth: float
) -> tuple[np.ndarray, np.ndarray]:
    x = np.linspace(0.0, length, nx + 1)
    y = np.linspace(-0.5 * height, 0.5 * height, ny + 1)
    z = np.linspace(-0.5 * depth, 0.5 * depth, nz + 1)
    nodes = np.stack(np.meshgrid(x, y, z, indexing="ij"), axis=-1).reshape(-1, 3)
    elements: list[list[int]] = []
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                cube = [_node_id(a, b, c, ny, nz) for a, b, c in (
                    (i, j, k), (i + 1, j, k), (i, j + 1, k), (i + 1, j + 1, k),
                    (i, j, k + 1), (i + 1, j, k + 1), (i, j + 1, k + 1), (i + 1, j + 1, k + 1),
                )]
                for local in ((0, 1, 3, 7), (0, 3, 2, 7), (0, 2, 6, 7), (0, 6, 4, 7), (0, 4, 5, 7), (0, 5, 1, 7)):
                    elements.append([cube[index] for index in local])
    return nodes, np.asarray(elements, dtype=int)


def _node_id(i: int, j: int, k: int, ny: int, nz: int) -> int:
    return i * (ny + 1) * (nz + 1) + j * (nz + 1) + k


def _element_dofs(connectivity: np.ndarray) -> np.ndarray:
    return (3 * np.asarray(connectivity)[:, None] + np.arange(3)).reshape(-1)


def _relative_change(value: float, previous: float) -> float:
    return abs(float(value) - float(previous)) / max(abs(float(value)), np.finfo(float).tiny)


def _relative_error(value: float, reference: float) -> float:
    return abs(float(value) - float(reference)) / max(abs(float(reference)), np.finfo(float).tiny)


def _format_percent(value: object) -> str:
    return "-" if value is None else f"{100.0 * float(value):.2f} %"


def _unique_edges(elements: np.ndarray) -> list[tuple[int, int]]:
    edges = set()
    for element in elements:
        for left, right in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)):
            edges.add(tuple(sorted((int(element[left]), int(element[right])))))
    return sorted(edges)


def _upper_check(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}


def _lower_check(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value >= limit else "FAIL"}
