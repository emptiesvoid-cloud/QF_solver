"""Ply-stress verification for smooth MITC4 laminate fields."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from solveur.elements.shell.mitc4.mesh import MeshFactory, QuadMesh

from solveur.api import solve_model
from solveur.io.manifest import write_json_file
from solveur.materials.factory import MaterialFactory
from solveur.verification.composite_structural import (
    _edge_weights,
    _laminate_definition,
    _nodes_at_x,
    _shell_model,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


class CompositePlyStressCampaign:
    """Compare recovered ply stresses with CLT away from loaded and clamped edges."""

    study_id = "VNV-COMP-PLY-STRESS-005"
    meshes = ((8, 2), (16, 4), (32, 8))
    cases = (
        ("membrane", 1.0e4, 0.0, 0.0),
        ("bending", 0.0, 2.0, 0.0),
        ("combined", 1.0e4, 2.0, 0.0),
        ("combined_distorted", 1.0e4, 2.0, 0.15),
    )

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        models = {
            name: [
                self._run_case(nx, ny, membrane_force, transverse_force, distortion)
                for nx, ny in self.meshes
            ]
            for name, membrane_force, transverse_force, distortion in self.cases
        }
        checks = [
            _upper("membrane_fine_l2_error", models["membrane"][-1]["stress_l2_error"], 1.0e-4),
            _upper("bending_fine_l2_error", models["bending"][-1]["stress_l2_error"], 5.0e-3),
            _upper("combined_fine_l2_error", models["combined"][-1]["stress_l2_error"], 1.0e-3),
            _upper(
                "distorted_combined_fine_l2_error",
                models["combined_distorted"][-1]["stress_l2_error"],
                2.0e-2,
            ),
            _upper(
                "maximum_free_relative_residual",
                max(float(row["residual_relative"]) for rows in models.values() for row in rows),
                1.0e-8,
            ),
        ]
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_TECHNICAL_VERIFICATION" if passed else "FAIL",
            "maturity": "experimental",
            "models": models,
            "checks": checks,
            "acceptance_region": {
                "x_over_length": [0.2, 0.8],
                "y_over_width": [-0.4, 0.4],
                "reason": "Exclude clamp and loaded-edge effects from smooth-field stress acceptance.",
            },
            "stress_metric": (
                "Global L2 norm over all material-axis stress components, all plies and "
                "lower/middle/upper ply points in the acceptance region."
            ),
            "scope_limit": (
                "Flat linear laminates under membrane, bending and combined loads. "
                "The distorted case perturbs only interior nodes by 15 percent of local spacing. "
                "Interlaminar S13, free-edge singularities, damage and curved material-axis "
                "transport are not covered."
            ),
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot_convergence(models)
        self._plot_stress_profile(models["combined"][-1])
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _run_case(
        self,
        nx: int,
        ny: int,
        membrane_force: float,
        transverse_force: float,
        distortion: float,
    ) -> dict[str, object]:
        length, width, thickness = 1.0, 0.2, 1.0e-2
        mesh = _distorted_plate(nx, ny, length, width, distortion)
        material_data = _laminate_definition([0.0, 90.0, 90.0, 0.0], thickness)
        material = MaterialFactory.create(material_data)
        left = _nodes_at_x(mesh, 0.0)
        right = _nodes_at_x(mesh, length)
        fixed = [{"node": node, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]} for node in left]
        weights = _edge_weights(mesh, right)
        loads: list[dict[str, object]] = []
        for index, node in enumerate(right):
            if membrane_force:
                loads.append({"node": node, "dof": "UX", "value": membrane_force * weights[index]})
            if transverse_force:
                loads.append(
                    {
                        "node": node,
                        "dof": "UZ",
                        "value": -transverse_force * weights[index] / width,
                    }
                )
        result = solve_model(_shell_model(mesh, material_data, fixed, loads))
        qf_values: list[float] = []
        reference_values: list[float] = []
        profile: list[dict[str, object]] = []
        for element_index, item in enumerate(result.element_results):
            center = np.mean(mesh.nodes[mesh.quads[element_index]], axis=0)
            x, y = float(center[0]), float(center[1])
            if not (0.2 * length <= x <= 0.8 * length and abs(y) <= 0.4 * width):
                continue
            membrane = np.array([membrane_force, 0.0, 0.0])
            moment = np.array([transverse_force * (length - x) / width, 0.0, 0.0])
            strain, curvature = material.laminate.generalized_strains(membrane, moment)
            references = material.laminate.ply_results(strain, curvature)
            for recovered, reference in zip(item["ply_results"], references, strict=True):
                qf_stress = np.asarray(recovered["material_stress"], dtype=float)
                reference_stress = np.asarray(reference.stress_material, dtype=float)
                qf_values.extend(qf_stress)
                reference_values.extend(reference_stress)
                if recovered["location"] == "middle":
                    profile.append(
                        {
                            "x": x,
                            "y": y,
                            "ply_index": int(recovered["ply_index"]),
                            "qf_s1": float(qf_stress[0]),
                            "reference_s1": float(reference_stress[0]),
                        }
                    )
        qf = np.asarray(qf_values)
        reference = np.asarray(reference_values)
        difference = qf - reference
        reference_norm = max(float(np.linalg.norm(reference)), np.finfo(float).tiny)
        reference_peak = max(float(np.max(np.abs(reference))), np.finfo(float).tiny)
        return {
            "nx": nx,
            "ny": ny,
            "elements": int(len(mesh.quads)),
            "distortion": distortion,
            "accepted_elements": int(len(qf_values) // 36),
            "stress_l2_error": float(np.linalg.norm(difference) / reference_norm),
            "stress_peak_normalized_error": float(np.max(np.abs(difference)) / reference_peak),
            "residual_relative": float(result.audit.equilibrium["free_relative_residual"]),
            "profile": profile,
        }

    def _plot_convergence(self, models: dict[str, list[dict[str, object]]]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        figure, axis = plt.subplots(figsize=(8.4, 5.2))
        labels = {
            "membrane": "Membrane",
            "bending": "Flexion",
            "combined": "Membrane + flexion",
            "combined_distorted": "Combine, maillage distordu 15 %",
        }
        for name, rows in models.items():
            axis.loglog(
                [int(row["elements"]) for row in rows],
                [max(float(row["stress_l2_error"]), 1.0e-16) for row in rows],
                marker="o",
                label=labels[name],
            )
        axis.set(
            xlabel="Nombre d'elements MITC4",
            ylabel="Erreur L2 relative des contraintes par pli",
            title="Contraintes hors effets de bord",
        )
        axis.grid(True, which="both", alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "ply_stress_convergence.png", dpi=180)
        plt.close(figure)

    def _plot_stress_profile(self, finest: dict[str, object]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        profile = finest["profile"]
        figure, axis = plt.subplots(figsize=(8.4, 5.2))
        for ply in range(4):
            rows = sorted(
                (
                    row
                    for row in profile
                    if int(row["ply_index"]) == ply and abs(float(row["y"])) < 0.03
                ),
                key=lambda row: float(row["x"]),
            )
            axis.plot(
                [float(row["x"]) for row in rows],
                [float(row["qf_s1"]) / 1.0e6 for row in rows],
                marker="o",
                markersize=2.5,
                linewidth=1.0,
                label=f"QF pli {ply + 1}",
            )
            axis.plot(
                [float(row["x"]) for row in rows],
                [float(row["reference_s1"]) / 1.0e6 for row in rows],
                linestyle="--",
                linewidth=1.0,
                label=f"CLT pli {ply + 1}",
            )
        axis.set(
            xlabel="X [m]",
            ylabel="Contrainte materiau S1 [MPa]",
            title="Chargement combine, ligne centrale, maillage fin",
        )
        axis.grid(True, alpha=0.25)
        axis.legend(ncol=2, fontsize=8)
        figure.tight_layout()
        figure.savefig(self.output_dir / "ply_stress_profile.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut automatise : **{summary['status']}**",
            "",
            "Les contraintes sont comparees dans les axes materiau de chaque pli.",
            "La bande `0,2 <= x/L <= 0,8` et `|y|/W <= 0,4` exclut",
            "l'encastrement, le bord charge et les bords lateraux.",
            "",
            "| Cas | Maillage | Elements | Erreur L2 | Erreur pic normalisee | Residu |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for name, rows in summary["models"].items():
            for row in rows:
                lines.append(
                    f"| {name} | {row['nx']}x{row['ny']} | {row['elements']} | "
                    f"{row['stress_l2_error']:.6e} | "
                    f"{row['stress_peak_normalized_error']:.6e} | "
                    f"{row['residual_relative']:.6e} |"
                )
        lines.extend(
            [
                "",
                "L'oracle est la theorie classique des stratifies : les efforts de",
                "membrane et moments analytiques sont convertis par la matrice ABD, puis",
                "les contraintes sont evaluees aux faces et au milieu de chaque pli.",
                "",
                "![Convergence des contraintes par pli](ply_stress_convergence.png)",
                "",
                "![Profil des contraintes par pli](ply_stress_profile.png)",
                "",
                "Cette campagne ne couvre pas les contraintes interlaminaires, les pics",
                "singuliers de bord libre, le dommage ni le transport continu des axes",
                "materiau sur une coque courbe.",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _distorted_plate(nx: int, ny: int, length: float, width: float, ratio: float) -> QuadMesh:
    mesh = MeshFactory.rectangular_plate(nx, ny, length, width)
    if ratio == 0.0:
        return mesh
    nodes = mesh.nodes.copy()
    dx, dy = length / nx, width / ny
    for node in nodes:
        x, y = float(node[0]), float(node[1])
        if 0.0 < x < length and abs(y) < 0.5 * width:
            node[0] += ratio * dx * np.sin(np.pi * x / length) * np.sin(2.0 * np.pi * y / width)
            node[1] += ratio * dy * np.sin(2.0 * np.pi * x / length) * np.cos(np.pi * y / width)
    return QuadMesh(nodes, mesh.quads.copy())


def _upper(identifier: str, value: object, limit: float) -> dict[str, object]:
    measured = float(value)
    return {
        "id": identifier,
        "value": measured,
        "limit": limit,
        "status": "PASS" if measured <= limit else "FAIL",
    }
