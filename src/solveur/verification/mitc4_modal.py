"""Analytical modal verification for a thin MITC4 cantilever.

The study is deliberately independent from the broader MITC4 campaign: it
checks frequency convergence, modal residuals and the first bending shape
against an Euler-Bernoulli reference before transient validation relies on it.
"""

from __future__ import annotations

from solveur.paths import project_root

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from mitc4.mesh import MeshFactory
from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file


PROJECT_ROOT = project_root()
STUDY_ID = "VNV-MITC4-MODAL-CANTILEVER-002"
_BETA_1 = 1.875104068711961


@dataclass(frozen=True)
class Mitc4ModalPoint:
    """One h-refinement point for the first out-of-plane bending mode."""

    mesh: tuple[int, int]
    element_count: int
    frequency_hz: float
    relative_frequency_error: float
    mode_assurance_criterion: float
    relative_residual: float
    mass_orthogonality_error: float

    def to_dict(self) -> dict[str, float | int | list[int]]:
        return {
            "mesh": list(self.mesh),
            "element_count": self.element_count,
            "frequency_hz": self.frequency_hz,
            "relative_frequency_error": self.relative_frequency_error,
            "mode_assurance_criterion": self.mode_assurance_criterion,
            "relative_residual": self.relative_residual,
            "mass_orthogonality_error": self.mass_orthogonality_error,
        }


class Mitc4ModalCantileverStudy:
    """Verify MITC4 first bending mode against Euler-Bernoulli theory.

    The plate is thin (`t/L = 0.01`) and clamped at `x = 0`.  The analytical
    reference is appropriate only for this explicitly declared slender regime.
    """

    young_modulus = 70.0e9
    poisson_ratio = 0.3
    thickness = 0.01
    density = 2700.0
    length = 1.0
    width = 0.2
    frequency_error_limit = 0.05
    mac_limit = 0.995
    residual_limit = 1.0e-7
    orthogonality_limit = 1.0e-7

    def __init__(self, meshes: tuple[tuple[int, int], ...] = ((4, 1), (8, 2), (12, 3), (16, 4), (24, 6))) -> None:
        self.meshes = meshes

    @property
    def analytical_frequency_hz(self) -> float:
        area = self.width * self.thickness
        inertia = self.width * self.thickness**3 / 12.0
        return _BETA_1**2 / (2.0 * math.pi * self.length**2) * math.sqrt(
            self.young_modulus * inertia / (self.density * area)
        )

    def run(self) -> dict[str, Any]:
        reference = self.analytical_frequency_hz
        points = [self._point(nx, ny, reference) for nx, ny in self.meshes]
        final = points[-1]
        increments = [
            abs(current.frequency_hz - previous.frequency_hz) / max(abs(current.frequency_hz), 1.0e-30)
            for previous, current in zip(points, points[1:])
        ]
        checks = {
            "frequency": final.relative_frequency_error <= self.frequency_error_limit,
            "mode_shape": final.mode_assurance_criterion >= self.mac_limit,
            "residual": max(point.relative_residual for point in points) <= self.residual_limit,
            "mass_orthogonality": max(point.mass_orthogonality_error for point in points)
            <= self.orthogonality_limit,
            "convergence": points[-1].frequency_hz < points[0].frequency_hz,
        }
        return {
            "study_id": STUDY_ID,
            "reference": {
                "type": "Euler-Bernoulli first cantilever bending frequency",
                "frequency_hz": reference,
                "beta_1": _BETA_1,
                "domain": "thin plate, t/L = 0.01, clamped root",
            },
            "acceptance": {
                "relative_frequency_error_max": self.frequency_error_limit,
                "mode_assurance_criterion_min": self.mac_limit,
                "relative_residual_max": self.residual_limit,
                "mass_orthogonality_error_max": self.orthogonality_limit,
            },
            "points": [point.to_dict() for point in points],
            "final_increment": increments[-1] if increments else 0.0,
            "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL",
            "limitations": [
                "Euler-Bernoulli is a slender-beam reference, not a general shell modal oracle.",
                "No same-mesh commercial-solver correlation is included in this internal study.",
            ],
        }

    def _point(self, nx: int, ny: int, reference: float) -> Mitc4ModalPoint:
        model, nodes = self.build_model(nx, ny)
        result = solve_model(model, enforce_policy=False)
        frequency = float(result.frequencies_hz[0])
        uz = np.asarray([result.dofs.index(node, "UZ") for node in range(nodes.shape[0])], dtype=int)
        mode = np.asarray(result.modes[uz, 0], dtype=float)
        reference_shape = _cantilever_shape(nodes[:, 0] / self.length)
        return Mitc4ModalPoint(
            mesh=(nx, ny),
            element_count=nx * ny,
            frequency_hz=frequency,
            relative_frequency_error=abs(frequency - reference) / reference,
            mode_assurance_criterion=_mac(mode, reference_shape),
            relative_residual=float(result.solver["max_relative_residual"]),
            mass_orthogonality_error=float(result.solver["mass_orthogonality_error"]),
        )

    def build_model(self, nx: int, ny: int) -> tuple[FiniteElementModel, np.ndarray]:
        """Build the controlled cantilever model for modal or transient reuse."""
        mesh = MeshFactory.rectangular_plate(nx, ny, self.length, self.width)
        root = np.flatnonzero(np.isclose(mesh.nodes[:, 0], 0.0))
        model = FiniteElementModel.from_raw(
            analysis={
                "type": "modal",
                "method": "eigh",
                "modes": 4,
                "dense_modal_max_dofs": 6000,
                "modal_residual_failure_tolerance": 1.0e-6,
            },
            nodes=mesh.nodes.tolist(),
            elements=[{"type": "MITC4", "nodes": quad.tolist(), "material": "skin"} for quad in mesh.quads],
            materials={
                "skin": {
                    "type": "shell_isotropic",
                    "E": self.young_modulus,
                    "nu": self.poisson_ratio,
                    "t": self.thickness,
                    "density": self.density,
                    "drilling_scale": 1.0e-4,
                }
            },
            fixed_dofs=[
                {"node": int(node), "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]} for node in root
            ],
        )
        return model, mesh.nodes


def write_mitc4_modal_cantilever_evidence(output: str | Path) -> dict[str, Any]:
    """Run the study and write JSON, Markdown, PNG and a file manifest."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = Mitc4ModalCantileverStudy().run()
    write_json_file(target / "summary.json", summary)
    _write_report(target / f"{STUDY_ID}.md", summary)
    _plot(summary, target / f"{STUDY_ID}.png")
    write_json_file(
        target / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "source": git_source_state(PROJECT_ROOT),
            "files": discovered_file_entries(target, lambda _: "mitc4_modal_vnv", exclude_names=("vnv_manifest.json",)),
        },
    )
    return summary


def _cantilever_shape(position: np.ndarray) -> np.ndarray:
    coefficient = (math.cosh(_BETA_1) + math.cos(_BETA_1)) / (math.sinh(_BETA_1) + math.sin(_BETA_1))
    beta_x = _BETA_1 * np.asarray(position, dtype=float)
    return np.cosh(beta_x) - np.cos(beta_x) - coefficient * (np.sinh(beta_x) - np.sin(beta_x))


def _mac(first: np.ndarray, second: np.ndarray) -> float:
    numerator = float(np.dot(first, second)) ** 2
    denominator = max(float(np.dot(first, first) * np.dot(second, second)), 1.0e-30)
    return numerator / denominator


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    points = summary["points"]
    rows = "\n".join(
        f"| {point['mesh'][0]}x{point['mesh'][1]} | {point['element_count']} | {point['frequency_hz']:.6f} | "
        f"{100.0 * point['relative_frequency_error']:.3f} % | {point['mode_assurance_criterion']:.6f} | "
        f"{point['relative_residual']:.3e} |"
        for point in points
    )
    text = f"""# {STUDY_ID}

## Objet

Premier mode de flexion hors-plan d'un porte-a-faux MITC4 mince, compare a la
solution Euler-Bernoulli. Cette etude est une preuve interne de convergence de
frequence et de forme, pas une correlation Abaqus/Ansys.

Reference analytique : `{summary['reference']['frequency_hz']:.6f} Hz`.

| Maillage | Elements | Frequence (Hz) | Erreur | MAC | Residu relatif |
| --- | ---: | ---: | ---: | ---: | ---: |
{rows}

Statut : **{summary['status']}**. Les criteres controles sont : erreur de
frequence finale <= 5 %, MAC >= 0,995, residu et orthogonalite masse <= 1e-7.

![Convergence modale]({STUDY_ID}.png)

## Limites

""" + "\n".join(f"- {item}" for item in summary["limitations"])
    path.write_text(text + "\n", encoding="utf-8")


def _plot(summary: dict[str, Any], path: Path) -> None:
    points = summary["points"]
    elements = [point["element_count"] for point in points]
    frequencies = [point["frequency_hz"] for point in points]
    reference = float(summary["reference"]["frequency_hz"])
    figure, axis = plt.subplots(figsize=(7.0, 4.2))
    axis.semilogx(elements, frequencies, "o-", color="#006d77", label="MITC4")
    axis.axhline(reference, color="#ae2012", linestyle="--", label="Euler-Bernoulli")
    axis.set_xlabel("nombre d'elements")
    axis.set_ylabel("premiere frequence (Hz)")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
