"""Finite-strain stress and energy benchmark for the total-Lagrangian TET4."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.io.manifest import write_json_file
from solveur.materials.solid import SolidMaterial
from solveur.verification.tet4_total_lagrangian_assembly import (
    _structured_tet4_mesh,
    _unique_edges,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


class TotalLagrangianStressCampaign:
    """Verify PK2, Cauchy stress and energy under homogeneous finite strain."""

    study_id = "VNV-TET4-TL-STRESS-005"
    levels = ((2, 1, 1), (4, 2, 2), (8, 4, 4), (12, 6, 6))

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()
        self.material = SolidMaterial(E=1.0e6, nu=0.3)
        self.deformation = np.array(
            [[1.08, 0.06, 0.01], [0.02, 0.97, 0.03], [0.00, 0.01, 1.04]],
            dtype=float,
        )

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        reference = analytical_svk_state(self.deformation, self.material)
        rows: list[dict[str, object]] = []
        finest: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None = None
        for cells in self.levels:
            nodes, elements = _structured_tet4_mesh(*cells, 2.0, 1.0, 0.75)
            assembly = TotalLagrangianTet4Assembly(nodes, elements, self.material)
            displacement = (nodes @ (self.deformation - np.eye(3)).T).reshape(-1)
            states = assembly.element_states(displacement)
            total_energy = float(np.dot(assembly.volumes, states["strain_energy_density"]))
            expected_energy = float(np.sum(assembly.volumes) * reference["energy_density"])
            rows.append(
                {
                    "cells": list(cells),
                    "elements": int(elements.shape[0]),
                    "dofs": int(assembly.ndof),
                    "green_l2_error": _maximum_relative_tensor_error(
                        states["green_lagrange_strain"], reference["green_lagrange_strain"]
                    ),
                    "pk2_l2_error": _maximum_relative_tensor_error(
                        states["second_piola_stress"], reference["second_piola_stress"]
                    ),
                    "cauchy_l2_error": _maximum_relative_tensor_error(
                        states["cauchy_stress"], reference["cauchy_stress"]
                    ),
                    "energy_relative_error": _relative_error(total_energy, expected_energy),
                    "det_f_error": float(np.max(np.abs(states["det_f"] - reference["det_f"]))),
                    "cauchy_von_mises": float(np.mean(_von_mises(states["cauchy_stress"]))),
                }
            )
            finest = nodes, elements, displacement, _von_mises(states["cauchy_stress"])
        maximum_error = max(
            max(
                float(row[key])
                for key in (
                    "green_l2_error",
                    "pk2_l2_error",
                    "cauchy_l2_error",
                    "energy_relative_error",
                    "det_f_error",
                )
            )
            for row in rows
        )
        limit = 1.0e-11
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_STRESS_ENERGY" if maximum_error <= limit else "FAIL",
            "maturity": "research",
            "reference": {
                "type": "homogeneous_finite_strain_saint_venant_kirchhoff",
                "deformation_gradient": self.deformation.tolist(),
                **{key: _json_value(value) for key, value in reference.items()},
            },
            "levels": rows,
            "checks": [
                {
                    "id": "maximum_constitutive_relative_error",
                    "value": maximum_error,
                    "limit": limit,
                    "status": "PASS" if maximum_error <= limit else "FAIL",
                }
            ],
            "limitations": [
                "The affine benchmark has no stress singularity and must be reproduced exactly by TET4.",
                "Structural stress convergence near clamps and concentrated loads remains excluded.",
                "Saint-Venant-Kirchhoff is used as a verification law, not as a universal material law.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot_convergence(rows)
        if finest is not None:
            self._plot_state(*finest)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _plot_convergence(self, rows: list[dict[str, object]]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        elements = [int(row["elements"]) for row in rows]
        figure, axis = plt.subplots(figsize=(7.4, 4.4))
        for key, label in (
            ("pk2_l2_error", "PK2"),
            ("cauchy_l2_error", "Cauchy"),
            ("energy_relative_error", "energie"),
        ):
            values = np.maximum([float(row[key]) for row in rows], 1.0e-17)
            axis.loglog(elements, values, "o-", label=label)
        axis.axhline(1.0e-11, color="#bc4749", linestyle="--", label="limite")
        axis.set_xlabel("Nombre de TET4")
        axis.set_ylabel("Erreur relative")
        axis.grid(True, which="both", alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "stress_convergence.png", dpi=180)
        plt.close(figure)

    def _plot_state(
        self,
        nodes: np.ndarray,
        elements: np.ndarray,
        displacement: np.ndarray,
        von_mises: np.ndarray,
    ) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        current = nodes + displacement.reshape(-1, 3)
        centroids = np.mean(current[elements], axis=1)
        edges = _unique_edges(elements)
        sampled = edges[:: max(1, len(edges) // 700)]
        figure = plt.figure(figsize=(8.6, 4.8))
        axis = figure.add_subplot(111, projection="3d")
        for edge in sampled:
            axis.plot(*current[list(edge)].T, color="#6c757d", linewidth=0.35, alpha=0.35)
        cloud = axis.scatter(*centroids.T, c=von_mises, cmap="viridis", s=5)
        figure.colorbar(cloud, ax=axis, shrink=0.72, label="von Mises Cauchy")
        axis.set_box_aspect((2.0, 1.0, 0.75))
        axis.set_title("Etat affine fini - maillage deforme")
        figure.tight_layout()
        figure.savefig(self.output_dir / "stress_deformation.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "Le champ affine impose le meme gradient de deformation dans chaque TET4. "
            "Les contraintes PK2 et Cauchy ainsi que l'energie sont comparees aux relations "
            "analytiques de Saint-Venant-Kirchhoff.",
            "",
            "| Elements | DDL | Erreur PK2 | Erreur Cauchy | Erreur energie | Erreur det(F) |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in summary["levels"]:
            lines.append(
                f"| {row['elements']} | {row['dofs']} | {row['pk2_l2_error']:.3e} | "
                f"{row['cauchy_l2_error']:.3e} | {row['energy_relative_error']:.3e} | "
                f"{row['det_f_error']:.3e} |"
            )
        lines.extend(
            [
                "",
                "![Convergence des grandeurs finies](stress_convergence.png)",
                "",
                "![Etat deforme et contrainte equivalente](stress_deformation.png)",
                "",
                "Ce patch valide le calcul constitutif hors singularite. Il ne valide pas encore "
                "une contrainte locale de pied d'encastrement.",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def analytical_svk_state(
    deformation: np.ndarray, material: SolidMaterial
) -> dict[str, np.ndarray | float]:
    """Return the closed-form Saint-Venant-Kirchhoff state for a constant F."""
    gradient = np.asarray(deformation, dtype=float)
    determinant = float(np.linalg.det(gradient))
    if gradient.shape != (3, 3) or determinant <= 0.0:
        raise ValueError("The analytical deformation gradient must be an orientation-preserving 3x3 matrix.")
    green = 0.5 * (gradient.T @ gradient - np.eye(3))
    lam = material.E * material.nu / ((1.0 + material.nu) * (1.0 - 2.0 * material.nu))
    mu = material.E / (2.0 * (1.0 + material.nu))
    second_piola = lam * float(np.trace(green)) * np.eye(3) + 2.0 * mu * green
    cauchy = gradient @ second_piola @ gradient.T / determinant
    return {
        "green_lagrange_strain": green,
        "second_piola_stress": second_piola,
        "cauchy_stress": cauchy,
        "energy_density": 0.5 * float(np.sum(green * second_piola)),
        "det_f": determinant,
    }


def _maximum_relative_tensor_error(values: np.ndarray, reference: np.ndarray) -> float:
    differences = np.linalg.norm(values - reference, axis=(1, 2))
    scale = max(float(np.linalg.norm(reference)), np.finfo(float).tiny)
    return float(np.max(differences) / scale)


def _relative_error(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), np.finfo(float).tiny)


def _von_mises(stress: np.ndarray) -> np.ndarray:
    mean = np.trace(stress, axis1=1, axis2=2)[:, None, None] / 3.0
    deviator = stress - mean * np.eye(3)
    return np.sqrt(1.5 * np.einsum("mij,mij->m", deviator, deviator, optimize=True))


def _json_value(value: np.ndarray | float) -> object:
    return value.tolist() if isinstance(value, np.ndarray) else float(value)
