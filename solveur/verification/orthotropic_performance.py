"""Functional and relative-performance non-regression for isotropic solids."""

from __future__ import annotations

import platform
import time
import tracemalloc
from pathlib import Path
from statistics import median
from typing import Callable

import numpy as np

from solveur.elements.solid.tet10 import Tet10Element
from solveur.elements.solid.tet4 import Tet4Element
from solveur.io.manifest import write_json_file
from solveur.materials.orthotropic import OrthotropicSolidMaterial
from solveur.materials.solid import SolidMaterial
from solveur.verification.vnv_manifest import write_vnv_manifest


class OrthotropicIsotropicPerformanceCampaign:
    """Ensure the historical isotropic path stays exact and comparatively lean."""

    study_id = "VNV-ORTHOTROPIC-ISOTROPIC-NONREGRESSION-004"

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        young, poisson = 70.0e9, 0.29
        shear = young / (2.0 * (1.0 + poisson))
        isotropic = SolidMaterial(E=young, nu=poisson, density=2700.0)
        angle = np.deg2rad(27.0)
        orientation = np.array(
            [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
        )
        equivalent = OrthotropicSolidMaterial(
            E1=young,
            E2=young,
            E3=young,
            nu12=poisson,
            nu13=poisson,
            nu23=poisson,
            G12=shear,
            G13=shear,
            G23=shear,
            density=2700.0,
            orientation=orientation,
        )
        families = {
            "TET4": self._family(Tet4Element(isotropic), Tet4Element(equivalent), _tet4_coords(), 250),
            "TET10": self._family(Tet10Element(isotropic), Tet10Element(equivalent), _tet10_coords(), 20),
        }
        checks = []
        for name, row in families.items():
            checks.extend(
                [
                    _upper(f"{name.lower()}_stiffness_equivalence", row["stiffness_relative_error"], 1.0e-12),
                    _upper(f"{name.lower()}_stress_equivalence", row["stress_relative_error"], 1.0e-12),
                    _upper(f"{name.lower()}_isotropic_time_ratio", row["isotropic_to_orthotropic_time_ratio"], 1.25),
                    _upper(
                        f"{name.lower()}_isotropic_memory_ratio", row["isotropic_to_orthotropic_memory_ratio"], 1.25
                    ),
                ]
            )
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_NON_REGRESSION" if passed else "FAIL",
            "maturity": "research",
            "covered_specifications": ["SPEC-COMP-SOLID-008"],
            "method": (
                "In-run comparison of the unchanged isotropic material against a rotated, mathematically equivalent "
                "orthotropic law; median of nine warmed, paired batches with alternating execution order."
            ),
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "numpy": np.__version__,
            },
            "families": families,
            "checks": checks,
            "limitations": [
                "Wall-clock values are informative and machine-dependent; acceptance uses only same-process ratios.",
                "tracemalloc observes Python allocations and does not include every native BLAS allocation.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    @staticmethod
    def _family(isotropic: object, equivalent: object, coordinates: np.ndarray, repeats: int) -> dict[str, float]:
        displacement = np.linspace(-2.0e-4, 3.0e-4, coordinates.shape[0] * 3)
        stiffness_iso = isotropic.stiffness(coordinates)
        stiffness_ortho = equivalent.stiffness(coordinates)
        stress_iso = isotropic.stress(coordinates, displacement)
        stress_ortho = equivalent.stress(coordinates, displacement)
        isotropic_time, orthotropic_time = _paired_median_times(
            lambda: isotropic.stiffness(coordinates),
            lambda: equivalent.stiffness(coordinates),
            repeats,
        )
        isotropic_memory = _peak_memory(lambda: isotropic.stiffness(coordinates), max(5, repeats // 10))
        orthotropic_memory = _peak_memory(lambda: equivalent.stiffness(coordinates), max(5, repeats // 10))
        return {
            "stiffness_relative_error": _relative_matrix(stiffness_iso, stiffness_ortho),
            "stress_relative_error": _relative_matrix(stress_iso, stress_ortho),
            "isotropic_seconds_per_stiffness": isotropic_time,
            "orthotropic_seconds_per_stiffness": orthotropic_time,
            "isotropic_to_orthotropic_time_ratio": isotropic_time / max(orthotropic_time, np.finfo(float).tiny),
            "isotropic_peak_python_bytes": float(isotropic_memory),
            "orthotropic_peak_python_bytes": float(orthotropic_memory),
            "isotropic_to_orthotropic_memory_ratio": isotropic_memory / max(orthotropic_memory, 1),
        }

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Verdict automatise : **{summary['status']}**",
            "",
            "| Famille | Ecart K | Ecart sigma | Ratio temps iso/ortho | Ratio memoire iso/ortho |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        for family, row in summary["families"].items():
            lines.append(
                f"| {family} | {row['stiffness_relative_error']:.3e} | {row['stress_relative_error']:.3e} | "
                f"{row['isotropic_to_orthotropic_time_ratio']:.3f} | "
                f"{row['isotropic_to_orthotropic_memory_ratio']:.3f} |"
            )
        lines.extend(
            [
                "",
                "Les temps absolus sont informatifs. Le critere portable est un ratio mesure dans le meme processus.",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _paired_median_times(
    first: Callable[[], object],
    second: Callable[[], object],
    repeats: int,
) -> tuple[float, float]:
    """Measure both paths in alternating order to limit timing drift."""
    for _ in range(3):
        first()
        second()
    first_samples = []
    second_samples = []
    for sample in range(9):
        functions = ((first, first_samples), (second, second_samples))
        if sample % 2:
            functions = tuple(reversed(functions))
        for function, samples in functions:
            start = time.perf_counter()
            for _ in range(repeats):
                function()
            samples.append((time.perf_counter() - start) / repeats)
    return float(median(first_samples)), float(median(second_samples))


def _peak_memory(function: Callable[[], object], repeats: int) -> int:
    tracemalloc.start()
    try:
        for _ in range(repeats):
            function()
        _, peak = tracemalloc.get_traced_memory()
        return int(peak)
    finally:
        tracemalloc.stop()


def _tet4_coords() -> np.ndarray:
    return np.array([[0.0, 0.0, 0.0], [1.1, 0.0, 0.0], [0.0, 0.9, 0.0], [0.0, 0.0, 1.2]])


def _tet10_coords() -> np.ndarray:
    corners = _tet4_coords()
    edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
    return np.vstack((corners, [0.5 * (corners[first] + corners[second]) for first, second in edges]))


def _relative_matrix(value: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(value - reference) / max(np.linalg.norm(reference), np.finfo(float).tiny))


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}
