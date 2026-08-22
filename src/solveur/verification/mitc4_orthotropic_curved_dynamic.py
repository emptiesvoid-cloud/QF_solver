"""Internal dynamic V&V for a one-ply orthotropic MITC4 curved panel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.paths import project_root
from solveur.verification.composite_curved_assembly import (
    _cylindrical_panel,
    _nodes_at_x,
)
from solveur.verification.mitc4_laminate_dynamic import Mitc4LaminateDynamicStudy
from solveur.verification.vnv_manifest import write_vnv_manifest


PROJECT_ROOT = project_root()
STUDY_ID = "VNV-MITC4-ORTHOTROPIC-CURVED-DYNAMIC-001"


class Mitc4OrthotropicCurvedDynamicStudy(Mitc4LaminateDynamicStudy):
    """Run modal, Newmark and harmonic checks on a faceted cylindrical panel."""

    include_history_shell_stress_probe = False
    drilling_mass_tolerance = 1.0e-14
    dynamic_probe_dof = "UY"

    def __init__(
        self,
        *,
        mesh: tuple[int, int] = (16, 4),
        angle_deg: float = 0.0,
        steps_per_period: tuple[int, ...] = (20, 40, 80),
        frequency_ratios: tuple[float, ...] = (0.0, 0.5, 0.95, 1.0, 1.05, 1.5, 2.0),
        modal_method: str = "eigh",
    ) -> None:
        super().__init__(
            mesh=mesh,
            layup=(float(angle_deg),),
            steps_per_period=steps_per_period,
            frequency_ratios=frequency_ratios,
            modal_method=modal_method,
        )
        self.angle_deg = float(angle_deg)

    def build_model(self) -> tuple[FiniteElementModel, np.ndarray]:
        """Build the curved faceted panel with a single orthotropic ply."""
        nx, ny = self.mesh
        mesh = _cylindrical_panel(nx, ny)
        root = _nodes_at_x(mesh, 0.0)
        ply = {
            "name": "orthotropic-ply-1",
            "E1": 135.0e9,
            "E2": 10.0e9,
            "nu12": 0.3,
            "G12": 5.0e9,
            "G13": 4.5e9,
            "G23": 3.8e9,
            "density": 1600.0,
            "thickness": 1.0e-2,
            "angle_deg": self.angle_deg,
        }
        model = FiniteElementModel.from_raw(
            analysis={
                "type": "modal",
                "method": self.modal_method,
                "modes": 4,
                "dense_modal_max_dofs": 6000,
                "modal_residual_failure_tolerance": self.residual_limit,
                "modal_eigenpair_refinement_iterations": 2,
                "drilling_mass_tolerance": 1.0e-14,
            },
            nodes=mesh.nodes.tolist(),
            elements=[
                {"type": "MITC4", "nodes": quad.tolist(), "material": "laminate"}
                for quad in mesh.quads
            ],
            materials={
                "laminate": {
                    "type": "shell_laminate",
                    "reference_direction": [1.0, 0.0, 0.0],
                    "drilling_scale": 1.0e-4,
                    "shear_factor": 5.0 / 6.0,
                    "plies": [ply],
                }
            },
            fixed_dofs=[
                {"node": int(node), "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}
                for node in root
            ],
        )
        return model, mesh.nodes

    def run(self) -> dict[str, Any]:
        summary = super().run()
        summary["study_id"] = STUDY_ID
        summary["scope"] = "curved faceted MITC4 one-ply orthotropic internal dynamics"
        summary["geometry"] = {
            "type": "faceted cylindrical panel",
            "mesh": list(self.mesh),
            "angle_deg": self.angle_deg,
            "reference_direction": [1.0, 0.0, 0.0],
        }
        summary["limitations"] = [
            "Internal dynamic consistency evidence; no external curved dynamic oracle.",
            "The external curved correlation is static and axial 0 degrees only.",
            "Non-axial projected orientation, damage, rupture and delamination remain outside scope.",
        ]
        return summary


def write_curved_dynamic_evidence(output: str | Path) -> dict[str, Any]:
    """Run the curved campaign and write reviewable JSON, report and figure."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = Mitc4OrthotropicCurvedDynamicStudy().run()
    write_json_file(target / "summary.json", summary)
    _write_report(target / "report.md", summary)
    _plot(target / "curved_dynamic_convergence.png", summary)
    write_vnv_manifest(target, STUDY_ID)
    return summary


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    modal = summary["modal"]
    points = summary["newmark"]["points"]
    harmonic = summary["harmonic"]
    lines = [
        f"# {STUDY_ID}",
        "",
        "Statut : **" + str(summary["status"]) + "**",
        "",
        "Panneau cylindrique facettisé MITC4, une lamelle orthotrope homogène, "
        f"orientation {summary['geometry']['angle_deg']:.1f} degrés.",
        "",
        f"Fréquence fondamentale : `{modal['frequencies_hz'][0]:.8f}` Hz.",
        f" Résidu modal : `{modal['max_relative_residual']:.3e}`.",
        "",
        "| Pas/periode | Erreur RMS Newmark | Derive energie | Residu dynamique |",
        "| ---: | ---: | ---: | ---: |",
    ]
    lines.extend(
        f"| {point['steps_per_period']} | {point['normalized_rms_error']:.3e} | "
        f"{point['maximum_relative_energy_drift']:.3e} | "
        f"{point['maximum_dynamic_residual_norm']:.3e} |"
        for point in points
    )
    lines.extend(
        [
            "",
            f"Erreur harmonique maximale : `{harmonic['maximum_relative_error']:.3e}`.",
            "",
            "Cette campagne complète la preuve statique externe du panneau courbe "
            "par une vérification dynamique interne cohérente. Elle ne constitue "
            "pas une corrélation externe dynamique courbe.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _plot(path: Path, summary: dict[str, Any]) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.0))
    points = summary["newmark"]["points"]
    axes[0].semilogy(
        [point["steps_per_period"] for point in points],
        [point["normalized_rms_error"] for point in points],
        "o-",
        color="#1769aa",
    )
    axes[0].set(xlabel="Pas par période", ylabel="Erreur RMS", title="Newmark courbe")
    axes[0].grid(True, which="both", alpha=0.25)
    harmonic = summary["harmonic"]
    axes[1].plot(
        harmonic["frequency_ratios"],
        harmonic["amplitudes_m"],
        "o-",
        color="#c43d3d",
    )
    axes[1].set(xlabel="Fréquence / f1", ylabel="Amplitude [m]", title="Harmonique courbe")
    axes[1].grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
