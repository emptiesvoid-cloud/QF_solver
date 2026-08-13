"""Imperfect-column postcritical benchmark for total-Lagrangian TET4."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.io.manifest import write_json_file
from solveur.materials.solid import SolidMaterial
from solveur.verification.tet4_total_lagrangian_assembly import (
    _structured_tet4_mesh,
    _unique_edges,
)
from solveur.verification.tet4_total_lagrangian_buckling import (
    euler_cantilever_critical_load,
)
from solveur.verification.total_lagrangian_structural import trace_sparse_arc_length
from solveur.verification.vnv_manifest import write_vnv_manifest


class TotalLagrangianPostbucklingCampaign:
    """Trace continuous imperfect-column paths with sparse arc length."""

    study_id = "VNV-TET4-TL-POSTBUCKLING-007"
    cells = (16, 4, 4)
    imperfection_ratios = (0.0025, 0.005, 0.01)

    def __init__(self, output_dir: str | Path, buckling_summary: str | Path):
        self.output_dir = Path(output_dir).resolve()
        self.buckling_summary = Path(buckling_summary).resolve()
        self.young = 1.0e6
        self.poisson = 0.3
        self.length = 4.0
        self.height = 0.5
        self.depth = 0.5

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        mesh_critical = load_mesh_critical_load(
            self.buckling_summary, int(6 * np.prod(self.cells))
        )
        euler = euler_cantilever_critical_load(
            self.young, self.depth * self.height**3 / 12.0, self.length
        )
        paths: list[dict[str, object]] = []
        plot_state: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None
        for ratio in self.imperfection_ratios:
            nodes, elements = _structured_tet4_mesh(
                *self.cells, self.length, self.height, self.depth
            )
            amplitude = ratio * self.length
            nodes[:, 2] += amplitude * (
                1.0 - np.cos(0.5 * np.pi * nodes[:, 0] / self.length)
            )
            assembly = TotalLagrangianTet4Assembly(
                nodes, elements, SolidMaterial(E=self.young, nu=self.poisson)
            )
            fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
            fixed = (3 * fixed_nodes[:, None] + np.arange(3)).reshape(-1)
            tip_nodes = np.flatnonzero(np.isclose(nodes[:, 0], self.length))
            reference_load = np.zeros(assembly.ndof, dtype=float)
            reference_load[3 * tip_nodes] = -mesh_critical / tip_nodes.size
            displacement, history = trace_sparse_arc_length(
                assembly,
                reference_load,
                fixed,
                tip_nodes,
                steps=120,
                initial_load_increment=0.05,
            )
            points = [
                {
                    "step": point.step,
                    "load_factor_fe_critical": point.load_factor,
                    "load": point.load_factor * mesh_critical,
                    "tip_axial_displacement": point.tip_axial_displacement,
                    "tip_lateral_increment": point.tip_lateral_displacement,
                    "tip_lateral_total": amplitude + point.tip_lateral_displacement,
                    "relative_residual": point.relative_residual,
                    "iterations": point.iterations,
                    "minimum_det_f": point.minimum_det_f,
                }
                for point in history
            ]
            final = points[-1]
            paths.append(
                {
                    "imperfection_ratio": ratio,
                    "imperfection_amplitude": amplitude,
                    "steps": len(points),
                    "maximum_load_factor_fe_critical": max(
                        float(point["load_factor_fe_critical"]) for point in points
                    ),
                    "maximum_load_factor_euler": max(float(point["load"]) for point in points)
                    / euler,
                    "final_lateral_amplification": float(final["tip_lateral_total"]) / amplitude,
                    "maximum_relative_residual": max(
                        float(point["relative_residual"]) for point in points
                    ),
                    "minimum_det_f": min(float(point["minimum_det_f"]) for point in points),
                    "points": points,
                }
            )
            if np.isclose(ratio, 0.005):
                plot_state = nodes, elements, displacement
        checks = [
            _upper_check(
                "arc_length_residual",
                max(float(path["maximum_relative_residual"]) for path in paths),
                1.0e-7,
            ),
            _lower_check(
                "positive_current_jacobian",
                min(float(path["minimum_det_f"]) for path in paths),
                0.9,
            ),
            _lower_check(
                "postcritical_load_reached",
                min(float(path["maximum_load_factor_euler"]) for path in paths),
                1.10,
            ),
            _lower_check(
                "imperfection_amplification",
                min(float(path["final_lateral_amplification"]) for path in paths),
                3.0,
            ),
        ]
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_POSTBUCKLING_RESEARCH" if passed else "FAIL",
            "maturity": "research",
            "mesh": {
                "cells": list(self.cells),
                "elements": int(6 * np.prod(self.cells)),
            },
            "references": {
                "euler_critical_load": euler,
                "same_mesh_fe_critical_load": mesh_critical,
                "buckling_study": str(self.buckling_summary),
                "buckling_summary_sha256": hashlib.sha256(
                    self.buckling_summary.read_bytes()
                ).hexdigest(),
            },
            "paths": paths,
            "checks": checks,
            "limitations": [
                "The curved reference meshes are stress-free geometric imperfections.",
                "The paths demonstrate postcritical geometric response but are not an external correlation.",
                "Follower loads, material nonlinearity and contact are excluded.",
                "The TET4 bending stiffness remains mesh dependent at this discretization.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot_paths(paths, euler / mesh_critical)
        self._plot_imperfections(paths)
        if plot_state is not None:
            self._plot_deformation(*plot_state)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _plot_paths(self, paths: list[dict[str, object]], euler_ratio: float) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        figure, axis = plt.subplots(figsize=(7.5, 4.8))
        for path in paths:
            points = path["points"]
            lateral = [float(point["tip_lateral_total"]) / self.length for point in points]
            load = [float(point["load_factor_fe_critical"]) for point in points]
            axis.plot(lateral, load, label=f"e0/L={path['imperfection_ratio']:.4f}")
        axis.axhline(euler_ratio, color="#bc4749", linestyle="--", label="Euler / Pcr FE")
        axis.axhline(1.0, color="#6c757d", linestyle=":", label="Pcr FE parfait")
        axis.set_xlabel("Deflexion laterale totale / L")
        axis.set_ylabel("Charge / Pcr FE")
        axis.grid(True, alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "postbuckling_paths.png", dpi=180)
        plt.close(figure)

    def _plot_imperfections(self, paths: list[dict[str, object]]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        coordinate = np.linspace(0.0, self.length, 200)
        figure, axis = plt.subplots(figsize=(7.5, 4.2))
        for path in paths:
            amplitude = float(path["imperfection_amplitude"])
            shape = amplitude * (1.0 - np.cos(0.5 * np.pi * coordinate / self.length))
            axis.plot(coordinate, shape, label=f"e0={amplitude:.3f}")
        axis.set_xlabel("x")
        axis.set_ylabel("Imperfection z")
        axis.grid(True, alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "initial_imperfections.png", dpi=180)
        plt.close(figure)

    def _plot_deformation(
        self, nodes: np.ndarray, elements: np.ndarray, displacement: np.ndarray
    ) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        current = nodes + displacement.reshape(-1, 3)
        edges = _unique_edges(elements)
        sampled = edges[:: max(1, len(edges) // 800)]
        figure = plt.figure(figsize=(9.0, 4.8))
        axis = figure.add_subplot(111, projection="3d")
        for coordinates, color, label in (
            (nodes, "#6c757d", "imparfaite initiale"),
            (current, "#0077b6", "etat final"),
        ):
            for edge in sampled:
                axis.plot(*coordinates[list(edge)].T, color=color, linewidth=0.4, alpha=0.55)
            axis.scatter([], [], [], color=color, label=label)
        axis.set_box_aspect((4.0, 1.0, 1.0))
        axis.legend()
        axis.set_title("Branche post-critique imparfaite")
        figure.tight_layout()
        figure.savefig(self.output_dir / "postbuckling_deformation.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "Trois colonnes imparfaites, initialement sans contrainte, sont suivies avec une "
            "continuation arc-length creuse. La charge est normalisee par la charge critique "
            "du meme maillage parfait issue de VNV-TET4-TL-BUCKLING-EULER-006.",
            "",
            "| e0/L | Etapes | Pmax/Pcr FE | Pmax/P Euler | Amplification finale | Residu max | det(F) min |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for path in summary["paths"]:
            lines.append(
                f"| {path['imperfection_ratio']:.4f} | {path['steps']} | "
                f"{path['maximum_load_factor_fe_critical']:.4f} | "
                f"{path['maximum_load_factor_euler']:.4f} | "
                f"{path['final_lateral_amplification']:.3f} | "
                f"{path['maximum_relative_residual']:.3e} | {path['minimum_det_f']:.6f} |"
            )
        lines.extend(
            [
                "",
                "![Branches post-critiques](postbuckling_paths.png)",
                "",
                "![Imperfections initiales](initial_imperfections.png)",
                "",
                "![Deformee post-critique](postbuckling_deformation.png)",
                "",
                "L'imperfection regularise la bifurcation parfaite et produit une branche continue. "
                "Cette preuve reste au statut recherche jusqu'a correlation externe.",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def load_mesh_critical_load(path: str | Path, element_count: int) -> float:
    """Read the critical load for one mesh from the controlled buckling summary."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Buckling summary not found: {source}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("status") != "PASS_BUCKLING_RESEARCH":
        raise ValueError("Buckling summary must have PASS_BUCKLING_RESEARCH status.")
    for row in data.get("levels", []):
        if int(row.get("elements", -1)) == element_count:
            value = float(row["critical_load"])
            if value > 0.0 and np.isfinite(value):
                return value
    raise ValueError(f"Buckling summary has no valid {element_count}-element level.")


def _upper_check(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}


def _lower_check(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value >= limit else "FAIL"}
