"""Review evidence for the total-Lagrangian TET4 verification kernel."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from solveur.elements.solid.tet4 import Tet4Element
from solveur.elements.solid.tet4_total_lagrangian import TotalLagrangianTet4Kernel
from solveur.io.manifest import write_json_file
from solveur.materials.solid import SolidMaterial


class TotalLagrangianTet4Campaign:
    """Generate auditable kernel-level finite-kinematics evidence."""

    campaign_id = "VNV-TET4-TL-KERNEL-001"
    reference_tetra = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    )

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()
        self.material = SolidMaterial(E=210.0e9, nu=0.3)
        self.element = TotalLagrangianTet4Kernel(self.material)

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        angle = np.deg2rad(73.0)
        rotation = np.array(
            [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
        )
        rigid_u = self._affine_displacement(rotation)
        rigid_force, rigid_tangent = self.element.internal_force_and_tangent(self.reference_tetra, rigid_u)
        volume = Tet4Element.signed_volume(self.reference_tetra)
        rigid_energy = self.element.strain_energy(self.reference_tetra, rigid_u)
        zero_tangent = self.element.internal_force_and_tangent(self.reference_tetra, np.zeros(12))[1]
        linear_tangent = Tet4Element(self.material).stiffness(self.reference_tetra)
        finite_deformation = np.array([[1.12, 0.08, 0.0], [0.03, 0.94, 0.04], [0.02, -0.01, 1.06]])
        tangent_error = self._tangent_error(self._affine_displacement(finite_deformation))
        extension_error = self._extension_energy_error(1.2)
        checks = [
            _check("linear_tangent", _relative_matrix(zero_tangent, linear_tangent), 1.0e-12),
            _check("rigid_rotation_force", np.linalg.norm(rigid_force) / (self.material.E * volume), 1.0e-14),
            _check("rigid_rotation_energy", abs(rigid_energy) / (self.material.E * volume), 1.0e-14),
            _check("tangent_symmetry", _relative_matrix(rigid_tangent, rigid_tangent.T), 1.0e-12),
            _check("consistent_tangent_fd", tangent_error, 1.0e-8),
            _check("homogeneous_extension_energy", extension_error, 1.0e-12),
        ]
        summary: dict[str, object] = {
            "campaign_id": self.campaign_id,
            "status": "PASS_KERNEL" if all(check["status"] == "PASS" for check in checks) else "FAIL",
            "maturity": "research",
            "formulation": "total_lagrangian_saint_venant_kirchhoff",
            "checks": checks,
            "owner_review_required": True,
            "integration_authorized": False,
            "limitations": [
                "Kernel-level evidence only; no assembled structural benchmark yet.",
                "Dead loads only are planned for the first integration.",
                "No finite-strain plasticity, follower pressure, contact or qualified buckling.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(rotation)
        self._write_report(summary)
        return summary

    def _tangent_error(self, local_u: np.ndarray) -> float:
        tangent = self.element.internal_force_and_tangent(self.reference_tetra, local_u)[1]
        numerical = np.zeros_like(tangent)
        step = 1.0e-7
        for column in range(12):
            perturbation = np.zeros(12)
            perturbation[column] = step
            plus = self.element.internal_force_and_tangent(self.reference_tetra, local_u + perturbation)[0]
            minus = self.element.internal_force_and_tangent(self.reference_tetra, local_u - perturbation)[0]
            numerical[:, column] = (plus - minus) / (2.0 * step)
        return _relative_matrix(tangent, numerical)

    def _extension_energy_error(self, stretch: float) -> float:
        deformation = np.diag([stretch, 1.0, 1.0])
        strain_x = 0.5 * (stretch**2 - 1.0)
        lam, mu = self.element.lame_constants
        exact = Tet4Element.signed_volume(self.reference_tetra) * (0.5 * lam + mu) * strain_x**2
        computed = self.element.strain_energy(self.reference_tetra, self._affine_displacement(deformation))
        return abs(computed - exact) / abs(exact)

    def _affine_displacement(self, deformation: np.ndarray) -> np.ndarray:
        return (self.reference_tetra @ (deformation - np.eye(3)).T).reshape(12)

    def _plot(self, rotation: np.ndarray) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        current = self.reference_tetra @ rotation.T
        figure = plt.figure(figsize=(8.6, 4.2))
        for index, (coords, title) in enumerate(
            ((self.reference_tetra, "Configuration de reference"), (current, "Rotation rigide 73 deg")), start=1
        ):
            axis = figure.add_subplot(1, 2, index, projection="3d")
            for node_a, node_b in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)):
                axis.plot(*coords[[node_a, node_b]].T, color="#006d77", linewidth=2)
            axis.scatter(*coords.T, color="#c1121f", s=28)
            axis.set_title(title)
            axis.set_box_aspect((1, 1, 1))
        figure.tight_layout()
        figure.savefig(self.output_dir / "rigid_rotation.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.campaign_id}",
            "",
            f"Statut automatique : **{summary['status']}**",
            "",
            "![Tetraedre et rotation rigide](rigid_rotation.png)",
            "",
            "| Controle | Valeur | Limite | Statut |",
            "| --- | ---: | ---: | --- |",
        ]
        for check in summary["checks"]:
            lines.append(f"| `{check['id']}` | {check['value']:.6e} | {check['limit']:.6e} | {check['status']} |")
        lines.extend(
            [
                "",
                "## Decision Owner demandee",
                "",
                "- [ ] Les mesures Green-Lagrange / Piola-Kirchhoff 2 sont acceptees pour le scope de recherche.",
                "- [ ] La loi Saint-Venant-Kirchhoff et ses limites sont comprises et acceptees.",
                "- [ ] L'integration peut commencer avec charges mortes uniquement.",
                "- [ ] Le statut reste `research` jusqu'aux benchmarks structurels.",
                "",
                "Decision : `pending_owner_review`.",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _relative_matrix(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right) / max(float(np.linalg.norm(right)), np.finfo(float).tiny))


def _check(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": float(value), "limit": float(limit), "status": "PASS" if value <= limit else "FAIL"}
