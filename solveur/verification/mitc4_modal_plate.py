"""Navier simply-supported square-plate verification for MITC4 modes."""

from __future__ import annotations

import math
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


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STUDY_ID = "VNV-MITC4-MODAL-PLATE-003"
MODE_ORDERS = ((1, 1), (1, 2), (2, 1), (2, 2))
TEN_MODE_ORDERS = (
    (1, 1),
    (1, 2),
    (2, 1),
    (2, 2),
    (1, 3),
    (3, 1),
    (2, 3),
    (3, 2),
    (1, 4),
    (4, 1),
)


class Mitc4SimplySupportedPlateStudy:
    """Check four bending modes of a thin square plate against Navier theory."""

    young_modulus = 70.0e9
    poisson_ratio = 0.3
    thickness = 0.01
    density = 2700.0
    length = 1.0
    frequency_error_limit = 0.05
    mac_limit = 0.995
    residual_limit = 1.0e-7
    orthogonality_limit = 1.0e-7

    def __init__(self, meshes: tuple[int, ...] = (4, 6, 8, 12, 16)) -> None:
        self.meshes = meshes

    def analytical_frequencies_hz(self) -> list[float]:
        rigidity = self.young_modulus * self.thickness**3 / (
            12.0 * (1.0 - self.poisson_ratio**2)
        )
        factor = math.pi / (2.0 * self.length**2) * math.sqrt(
            rigidity / (self.density * self.thickness)
        )
        return [factor * (m * m + n * n) for m, n in MODE_ORDERS]

    def run(self) -> dict[str, Any]:
        references = self.analytical_frequencies_hz()
        points = [self._point(size, references) for size in self.meshes]
        final = points[-1]
        checks = {
            "four_frequency_errors": max(final["relative_frequency_errors"]) <= self.frequency_error_limit,
            "first_mode_mac": final["first_mode_mac"] >= self.mac_limit,
            "repeated_mode_subspace_mac": final["repeated_mode_subspace_mac"] >= self.mac_limit,
            "fourth_mode_mac": final["fourth_mode_mac"] >= self.mac_limit,
            "modal_residual": max(point["maximum_relative_residual"] for point in points)
            <= self.residual_limit,
            "mass_orthogonality": max(point["mass_orthogonality_error"] for point in points)
            <= self.orthogonality_limit,
            "first_frequency_convergence": final["relative_frequency_errors"][0]
            < points[0]["relative_frequency_errors"][0],
        }
        return {
            "study_id": STUDY_ID,
            "reference": {
                "type": "Navier thin simply-supported square plate",
                "equation": "f_mn = pi/(2*a^2)*sqrt(D/(rho*t))*(m^2+n^2)",
                "mode_orders": [list(order) for order in MODE_ORDERS],
                "frequencies_hz": references,
                "domain": "square plate, t/a = 0.01, w=0 on four edges",
            },
            "acceptance": {
                "relative_frequency_error_max": self.frequency_error_limit,
                "mac_min": self.mac_limit,
                "relative_residual_max": self.residual_limit,
                "mass_orthogonality_error_max": self.orthogonality_limit,
            },
            "points": points,
            "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL",
            "limitations": [
                "The Navier reference assumes Kirchhoff thin-plate behavior.",
                "The repeated (1,2)/(2,1) eigenspace is compared as a subspace because individual vectors are not unique.",
                "A same-mesh Abaqus S4R/S4 correlation remains pending.",
            ],
        }

    def finest_mode_data(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return nodes, quads and first-mode translations for plotting."""
        size = self.meshes[-1]
        model, quads = self._model(size)
        result = solve_model(model, enforce_policy=False)
        translations = np.array(
            [
                [result.modes[result.dofs.index(node, name), 0] for name in ("UX", "UY", "UZ")]
                for node in range(model.node_count)
            ],
            dtype=float,
        )
        return model.nodes, quads, translations

    def _point(self, size: int, references: list[float]) -> dict[str, Any]:
        model, _ = self._model(size)
        result = solve_model(model, enforce_policy=False)
        uz = np.asarray([result.dofs.index(node, "UZ") for node in range(model.node_count)], dtype=int)
        numerical = np.asarray(result.modes[uz, :4], dtype=float)
        analytical = np.column_stack(
            [_navier_shape(model.nodes, m, n, self.length) for m, n in MODE_ORDERS]
        )
        frequencies = [float(value) for value in result.frequencies_hz[:4]]
        return {
            "mesh": [size, size],
            "element_count": size * size,
            "frequencies_hz": frequencies,
            "relative_frequency_errors": [
                abs(value - reference) / reference
                for value, reference in zip(frequencies, references, strict=True)
            ],
            "first_mode_mac": _mac(numerical[:, 0], analytical[:, 0]),
            "repeated_mode_subspace_mac": _subspace_mac_min(numerical[:, 1:3], analytical[:, 1:3]),
            "fourth_mode_mac": _mac(numerical[:, 3], analytical[:, 3]),
            "maximum_relative_residual": float(result.solver["max_relative_residual"]),
            "mass_orthogonality_error": float(result.solver["mass_orthogonality_error"]),
        }

    def _model(self, size: int) -> tuple[FiniteElementModel, np.ndarray]:
        mesh = MeshFactory.rectangular_plate(size, size, self.length, self.length)
        x = mesh.nodes[:, 0]
        y = mesh.nodes[:, 1] + 0.5 * self.length
        boundary = np.flatnonzero(
            np.isclose(x, 0.0)
            | np.isclose(x, self.length)
            | np.isclose(y, 0.0)
            | np.isclose(y, self.length)
        )
        fixed = [{"node": int(node), "dofs": ["UZ"]} for node in boundary]
        fixed.extend(
            (
                {"node": 0, "dofs": ["UX", "UY"]},
                {"node": size * (size + 1), "dofs": ["UY"]},
            )
        )
        model = FiniteElementModel.from_raw(
            analysis={
                "type": "modal",
                "method": "eigh",
                "modes": 6,
                "dense_modal_max_dofs": 10000,
                "modal_residual_failure_tolerance": 1.0e-6,
            },
            nodes=mesh.nodes.tolist(),
            elements=[
                {"type": "MITC4", "nodes": quad.tolist(), "material": "skin"}
                for quad in mesh.quads
            ],
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
            fixed_dofs=fixed,
        )
        return model, mesh.quads


def write_mitc4_modal_plate_evidence(output: str | Path) -> dict[str, Any]:
    """Generate controlled JSON, Markdown, figures and manifest."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    study = Mitc4SimplySupportedPlateStudy()
    summary = study.run()
    write_json_file(target / "summary.json", summary)
    _write_report(target / f"{STUDY_ID}.md", summary)
    _plot_convergence(summary, target / f"{STUDY_ID}-convergence.png")
    nodes, quads, translations = study.finest_mode_data()
    _plot_mode(nodes, quads, translations, target / f"{STUDY_ID}-mode-11.png")
    write_json_file(
        target / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "source": git_source_state(PROJECT_ROOT),
            "files": discovered_file_entries(
                target,
                lambda _: "mitc4_modal_plate_vnv",
                exclude_names=("vnv_manifest.json",),
            ),
        },
    )
    return summary


def _navier_shape(nodes: np.ndarray, m: int, n: int, length: float) -> np.ndarray:
    x = nodes[:, 0]
    y = nodes[:, 1] + 0.5 * length
    return np.sin(m * math.pi * x / length) * np.sin(n * math.pi * y / length)


def _mac(first: np.ndarray, second: np.ndarray) -> float:
    numerator = float(np.dot(first, second)) ** 2
    denominator = max(float(np.dot(first, first) * np.dot(second, second)), 1.0e-30)
    return numerator / denominator


def _subspace_mac_min(first: np.ndarray, second: np.ndarray) -> float:
    first_basis, _ = np.linalg.qr(first)
    second_basis, _ = np.linalg.qr(second)
    singular_values = np.linalg.svd(first_basis.T @ second_basis, compute_uv=False)
    return float(np.min(singular_values) ** 2)


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    references = summary["reference"]["frequencies_hz"]
    rows = []
    for point in summary["points"]:
        frequencies = ", ".join(f"{value:.4f}" for value in point["frequencies_hz"])
        errors = ", ".join(f"{100.0 * value:.3f} %" for value in point["relative_frequency_errors"])
        rows.append(
            f"| {point['mesh'][0]}x{point['mesh'][1]} | {point['element_count']} | {frequencies} | "
            f"{errors} | {point['first_mode_mac']:.6f} | {point['repeated_mode_subspace_mac']:.6f} | "
            f"{point['fourth_mode_mac']:.6f} |"
        )
    reference_text = ", ".join(f"{value:.6f}" for value in references)
    limitations = "\n".join(f"- {item}" for item in summary["limitations"])
    rows_text = "\n".join(rows)
    path.write_text(
        f"""# {STUDY_ID}

## Objet

Quatre premiers modes de flexion d'une plaque carree MITC4 simplement appuyee,
compares a la solution de Navier. Frequences analytiques `(11, 12, 21, 22)` :
`{reference_text} Hz`.

| Maillage | Elements | Frequences MITC4 (Hz) | Erreurs | MAC 11 | MAC sous-espace 12/21 | MAC 22 |
| --- | ---: | --- | --- | ---: | ---: | ---: |
{rows_text}

Statut : **{summary['status']}**.

![Convergence]({STUDY_ID}-convergence.png)

![Premier mode]({STUDY_ID}-mode-11.png)

## Limites

{limitations}
""",
        encoding="utf-8",
    )


def _plot_convergence(summary: dict[str, Any], path: Path) -> None:
    points = summary["points"]
    references = summary["reference"]["frequencies_hz"]
    elements = [point["element_count"] for point in points]
    figure, axis = plt.subplots(figsize=(7.4, 4.5))
    for index, order in enumerate(MODE_ORDERS):
        values = [point["frequencies_hz"][index] for point in points]
        axis.semilogx(elements, values, "o-", label=f"MITC4 {order}")
        axis.axhline(references[index], color=axis.lines[-1].get_color(), linestyle="--", alpha=0.55)
    axis.set_xlabel("nombre d'elements")
    axis.set_ylabel("frequence (Hz)")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend(ncol=2)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_mode(nodes: np.ndarray, quads: np.ndarray, translations: np.ndarray, path: Path) -> None:
    amplitude = max(float(np.max(np.abs(translations[:, 2]))), 1.0e-30)
    scale = 0.15 / amplitude
    deformed = nodes + scale * translations
    figure = plt.figure(figsize=(7.4, 4.8))
    axis = figure.add_subplot(111, projection="3d")
    for quad in quads:
        closed = np.append(quad, quad[0])
        axis.plot(*nodes[closed].T, color="#8d99ae", linewidth=0.35)
        axis.plot(*deformed[closed].T, color="#006d77", linewidth=0.65)
    axis.set_title(f"Mode (1,1) MITC4, maillage 16x16, facteur {scale:.3e}")
    axis.set_xlabel("x (m)")
    axis.set_ylabel("y (m)")
    axis.set_zlabel("deformee modale")
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
