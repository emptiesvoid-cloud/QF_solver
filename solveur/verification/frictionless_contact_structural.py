"""Structural TET4 mesh-refinement verification for unilateral contact."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh
from solveur.verification.vnv_manifest import write_vnv_manifest
from solveur.verification.vnv_visualization import exterior_tet4_faces


@dataclass(frozen=True)
class StructuralContactCheck:
    """A scalar acceptance criterion for the assembled contact study."""

    name: str
    value: float
    limit: float
    status: str
    criterion: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class FrictionlessStructuralContactCampaign:
    """Refine an assembled TET4 bar closed against a rigid triangular plane.

    The contact is deliberately a single slave node against a fixed master
    triangle, which is the implemented V1 scope.  Unlike the analytical block
    proof, the slave node is carried by a deformable three-dimensional TET4
    structure.  The campaign therefore observes spatial discretization of the
    structural reaction, while the exact normal gap constraint remains zero.
    """

    campaign_id = "VNV-CONTACT-TET4-STRUCTURAL-001"
    levels = ((4, 2, 2), (8, 4, 4), (12, 6, 6), (16, 8, 8))

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)
        self._previous_pressure_value: float | None = None

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows: list[dict[str, Any]] = []
        finest: tuple[np.ndarray, np.ndarray, np.ndarray, int, tuple[int, int, int]] | None = None
        for level in self.levels:
            row, mesh = self._solve_level(*level)
            rows.append(row)
            finest = mesh
        checks = self._checks(rows)
        status = "PASS_INTERNAL" if all(check.status == "PASS" for check in checks) else "FAIL"
        summary: dict[str, Any] = {
            "campaign_id": self.campaign_id,
            "status": status,
            "maturity": "experimental",
            "scope": "linear_static_tet4_node_triangle_frictionless",
            "reference": {
                "kind": "mesh_refinement_internal",
                "description": "Deformable TET4 bar against a rigid triangular plane; no external correlation.",
                "young_modulus": 10000.0,
                "poisson_ratio": 0.3,
                "initial_gap": 0.1,
                "normal_load": -4000.0,
            },
            "levels": rows,
            "checks": [check.to_dict() for check in checks],
            "limitations": [
                "The master is a fixed triangle and the normal is frozen in the initial configuration.",
                "This checks TET4 spatial convergence coupled to normal contact, not surface-to-surface contact.",
                "No external solver correlation is claimed; friction, large sliding and nonlinear geometry remain outside scope.",
            ],
        }
        (self.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self._plot_convergence(rows)
        if finest is not None:
            self._plot_deformation(*finest)
        (self.output_dir / "report.md").write_text(self._markdown(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.campaign_id)
        return summary

    def _solve_level(
        self, nx: int, ny: int, nz: int
    ) -> tuple[dict[str, Any], tuple[np.ndarray, np.ndarray, np.ndarray, int, tuple[int, int, int]]]:
        nodes, elements = _structured_tet4_mesh(nx, ny, nz, 1.0, 1.0, 1.0)
        nodes[:, 0] += 0.1
        structural_count = len(nodes)
        nodes = np.vstack((nodes, np.array([[0.0, -1.0, -1.0], [0.0, 1.0, -1.0], [0.0, -1.0, 1.0]])))
        slave = self._slave_node(nodes[:structural_count])
        model = JsonModelReader().from_dict(self._model_data(nodes, elements, structural_count, slave))
        result = LinearStaticSolver().solve(model)
        detail = result.solver["contact"]["contacts"][0]
        pressure = float(detail["pressure"])
        displacement = np.asarray(result.displacements, dtype=float).reshape(-1, 3)
        audit = result.audit.to_dict() if result.audit is not None else {}
        equilibrium = audit.get("equilibrium", {})
        row: dict[str, Any] = {
            "cells": [nx, ny, nz],
            "nodes": structural_count,
            "elements": int(len(elements)),
            "dofs": int(result.dofs.ndof),
            "gap": float(detail["gap"]),
            "pressure": pressure,
            "slave_ux": float(displacement[slave, 0]),
            "active_iterations": len(result.solver["contact"]["history"]),
            "relative_residual": float(equilibrium.get("free_relative_residual", float("inf"))),
            "pressure_change_from_previous": None,
        }
        if self._previous_pressure_value is not None:
            previous = self._previous_pressure_value
            row["pressure_change_from_previous"] = abs(pressure - previous) / max(abs(pressure), 1.0)
        self._previous_pressure_value = pressure
        return row, (nodes, elements, displacement, slave, (nx, ny, nz))

    @staticmethod
    def _slave_node(nodes: np.ndarray) -> int:
        matches = np.flatnonzero(
            np.isclose(nodes[:, 0], 0.1) & np.isclose(nodes[:, 1], 0.0) & np.isclose(nodes[:, 2], 0.0)
        )
        if len(matches) != 1:
            raise RuntimeError("Structured contact mesh did not produce exactly one central slave node.")
        return int(matches[0])

    @staticmethod
    def _model_data(nodes: np.ndarray, elements: np.ndarray, structural_count: int, slave: int) -> dict[str, object]:
        fixed = [
            {"node": index, "dofs": ["UX", "UY", "UZ"]}
            for index, point in enumerate(nodes)
            if index >= structural_count or np.isclose(point[0], 1.1)
        ]
        return {
            "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 25},
            "nodes": nodes.tolist(),
            "elements": [{"type": "TET4", "nodes": cell.tolist(), "material": "steel_like"} for cell in elements],
            "materials": {"steel_like": {"type": "isotropic_3d", "E": 10000.0, "nu": 0.3}},
            "fixed_dofs": fixed,
            "loads": [{"node": slave, "dof": "UX", "value": -4000.0}],
            "contacts": [{"name": "rigid_plane", "slave_node": slave, "master_nodes": [structural_count, structural_count + 1, structural_count + 2]}],
        }

    @staticmethod
    def _checks(rows: list[dict[str, Any]]) -> list[StructuralContactCheck]:
        maximum_gap = max(abs(float(row["gap"])) for row in rows)
        minimum_pressure = min(float(row["pressure"]) for row in rows)
        maximum_residual = max(float(row["relative_residual"]) for row in rows)
        final_change = float(rows[-1]["pressure_change_from_previous"])
        max_iterations = max(float(row["active_iterations"]) for row in rows)
        return [
            _upper("closed-contact gap", maximum_gap, 1.0e-10, "maximum absolute normal gap [m]"),
            _lower("compressive normal pressure", minimum_pressure, 0.0, "minimum reaction [N]"),
            _upper("free relative residual", maximum_residual, 1.0e-10, "maximum free residual"),
            _upper("finest pressure change", final_change, 0.03, "relative change between final two meshes"),
            _upper("active-set iterations", max_iterations, 3.0, "maximum active-set iterations"),
        ]

    def _plot_convergence(self, rows: list[dict[str, Any]]) -> None:
        elements = np.asarray([row["elements"] for row in rows], dtype=float)
        pressures = np.asarray([row["pressure"] for row in rows], dtype=float)
        figure, axis = plt.subplots(figsize=(7.3, 4.4), constrained_layout=True)
        axis.semilogx(elements, pressures, "o-", color="#006d77", label="QF_solver TET4")
        axis.set(xlabel="Nombre de TET4", ylabel="Reaction normale de contact [N]")
        axis.grid(True, which="both", alpha=0.3)
        axis.legend()
        figure.savefig(self.output_dir / "contact_structural_convergence.png", dpi=170)
        plt.close(figure)

    def _plot_deformation(
        self, nodes: np.ndarray, elements: np.ndarray, displacement: np.ndarray, slave: int, cells: tuple[int, int, int]
    ) -> None:
        from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection

        scale = 2.0
        current = nodes + scale * displacement
        edges = _unique_edges(elements)
        faces, _ = exterior_tet4_faces(elements)
        magnitude = np.linalg.norm(displacement, axis=1)
        cmap = plt.get_cmap("cividis")
        figure = plt.figure(figsize=(8.0, 5.2), constrained_layout=True)
        axis = figure.add_subplot(111, projection="3d")
        sampled_edges = edges[:: max(1, len(edges) // 650)]
        axis.add_collection3d(
            Line3DCollection(
                [[nodes[left], nodes[right]] for left, right in sampled_edges],
                colors="#555555",
                linewidths=0.35,
                alpha=0.42,
                linestyles="dashed",
            )
        )
        face_values = np.asarray([float(np.mean(magnitude[face])) for face in faces])
        surface_minimum = float(np.min(face_values))
        surface_maximum = float(np.max(face_values))
        surface_range = max(surface_maximum - surface_minimum, np.finfo(float).tiny)
        axis.add_collection3d(
            Poly3DCollection(
                [current[face] for face in faces],
                facecolors=cmap((face_values - surface_minimum) / surface_range),
                edgecolors="#202020",
                linewidths=0.22,
                alpha=0.94,
            )
        )
        master = current[-3:]
        axis.add_collection3d(
            Poly3DCollection(
                [master],
                facecolors="#d55e00",
                edgecolors="#7f2704",
                linewidths=1.1,
                alpha=0.42,
            )
        )
        axis.scatter([], [], [], color="#555555", marker="_", label="maillage initial")
        axis.scatter([], [], [], color=cmap(0.65), marker="s", label="deformee coloree x2")
        axis.scatter([], [], [], color="#d55e00", marker="s", label="surface maitre")
        axis.scatter(*current[slave], color="#cc0000", edgecolor="white", s=34, label="noeud esclave")
        scalar = plt.cm.ScalarMappable(
            cmap=cmap,
            norm=plt.Normalize(vmin=surface_minimum, vmax=surface_maximum),
        )
        scalar.set_array([])
        colorbar = figure.colorbar(scalar, ax=axis, shrink=0.68, pad=0.08)
        colorbar.set_label("Norme moyenne du deplacement sur la face [m]")
        axis.set(xlabel="X [m]", ylabel="Y [m]", zlabel="Z [m]", title=f"Contact TET4 structurel, {cells[0]}x{cells[1]}x{cells[2]}")
        axis.set_box_aspect((1.2, 1.0, 1.0))
        axis.legend(loc="upper left")
        figure.savefig(self.output_dir / "contact_structural_deformation.png", dpi=170)
        plt.close(figure)

    @staticmethod
    def _markdown(summary: dict[str, Any]) -> str:
        lines = [
            "# V&V contact unilateral : convergence structurelle TET4",
            "",
            f"- Etude : `{summary['campaign_id']}`",
            f"- Verdict interne : `{summary['status']}`",
            "- Maturite : `experimental`",
            "- Reference : convergence interne d'une barre deformable TET4 contre un plan rigide.",
            "",
            "## Resultats de raffinement",
            "",
            "| Maillage | TET4 | DDL | Gap [m] | Reaction [N] | Variation | Residu |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in summary["levels"]:
            cells = "x".join(str(value) for value in row["cells"])
            variation = row["pressure_change_from_previous"]
            formatted = "-" if variation is None else f"{100.0 * float(variation):.2f} %"
            lines.append(
                f"| {cells} | {row['elements']} | {row['dofs']} | {float(row['gap']):.3e} | "
                f"{float(row['pressure']):.6f} | {formatted} | {float(row['relative_residual']):.3e} |"
            )
        lines.extend([
            "",
            "## Interpretation",
            "",
            "Le gap normal est impose exactement quand le contact est actif. La reaction depend en revanche "
            "de la compliance de la structure TET4 et doit donc se stabiliser sous raffinement. Ce test "
            "ne remplace ni une correlation externe, ni un test de contact surface-a-surface.",
            "",
            "![Convergence de la reaction](contact_structural_convergence.png)",
            "",
            "![Maillage et deformee](contact_structural_deformation.png)",
            "",
        ])
        return "\n".join(lines)


def _unique_edges(elements: np.ndarray) -> list[tuple[int, int]]:
    edges: set[tuple[int, int]] = set()
    for cell in elements:
        for left, right in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)):
            first, second = int(cell[left]), int(cell[right])
            edges.add((min(first, second), max(first, second)))
    return sorted(edges)


def _upper(name: str, value: float, limit: float, criterion: str) -> StructuralContactCheck:
    return StructuralContactCheck(name, value, limit, "PASS" if value <= limit else "FAIL", criterion)


def _lower(name: str, value: float, limit: float, criterion: str) -> StructuralContactCheck:
    return StructuralContactCheck(name, value, limit, "PASS" if value >= limit else "FAIL", criterion)
