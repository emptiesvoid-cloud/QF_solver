"""Extraction of the CalculiX NAFEMS 13H complex response."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


_DISPLACEMENT_HEADER = re.compile(
    r"displacements .* time\s+([0-9.E+\-]+)", re.IGNORECASE
)
_STRESS_HEADER = re.compile(r"stresses .* time\s+([0-9.E+\-]+)", re.IGNORECASE)


@dataclass(frozen=True)
class CalculixFrequencyPoint:
    """Complex displacement and face stress at one forcing frequency."""

    frequency_hz: float
    center_uz: complex
    center_top_s11_pa: complex

    def to_dict(self) -> dict[str, float]:
        return {
            "frequency_hz": self.frequency_hz,
            "center_uz_real_m": float(self.center_uz.real),
            "center_uz_imag_m": float(self.center_uz.imag),
            "center_uz_amplitude_mm": float(abs(self.center_uz) * 1.0e3),
            "center_uz_phase_degrees": float(np.degrees(np.angle(self.center_uz))),
            "center_top_s11_real_mpa": float(self.center_top_s11_pa.real / 1.0e6),
            "center_top_s11_imag_mpa": float(self.center_top_s11_pa.imag / 1.0e6),
            "center_top_s11_amplitude_mpa": float(abs(self.center_top_s11_pa) / 1.0e6),
            "center_top_s11_phase_degrees": float(
                np.degrees(np.angle(self.center_top_s11_pa))
            ),
        }


class CalculixNafems13HParser:
    """Parse real/imaginary CalculiX blocks and recover top-face stress."""

    def parse(
        self,
        path: str | Path,
        *,
        center_node: int,
        center_element_corners: dict[int, tuple[float, float]],
    ) -> list[CalculixFrequencyPoint]:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
        displacements = self._displacement_blocks(lines, center_node)
        stresses = self._stress_blocks(lines)
        displacement_pairs = _pair_complex_blocks(displacements)
        stress_pairs = _pair_complex_blocks(stresses)
        if len(displacement_pairs) != len(stress_pairs):
            raise ValueError("CalculiX displacement/stress frequency counts differ.")

        points: list[CalculixFrequencyPoint] = []
        for (frequency, displacement), (stress_frequency, stress) in zip(
            displacement_pairs, stress_pairs, strict=True
        ):
            if not np.isclose(frequency, stress_frequency, rtol=0.0, atol=1.0e-10):
                raise ValueError("CalculiX displacement/stress frequencies differ.")
            recovered = [
                extrapolate_shell_surface_stress(
                    {point: stress[(element, point)] for point in range(1, 9)},
                    xi=corner[0],
                    eta=corner[1],
                    face=1.0,
                )
                for element, corner in center_element_corners.items()
            ]
            points.append(
                CalculixFrequencyPoint(
                    frequency_hz=frequency,
                    center_uz=displacement,
                    center_top_s11_pa=sum(recovered) / len(recovered),
                )
            )
        if not points:
            raise ValueError("No CalculiX harmonic frequency point was parsed.")
        return points

    @staticmethod
    def _displacement_blocks(
        lines: list[str], center_node: int
    ) -> list[tuple[float, float]]:
        blocks: list[tuple[float, float]] = []
        for index, line in enumerate(lines):
            match = _DISPLACEMENT_HEADER.search(line)
            if match is None:
                continue
            frequency = float(match.group(1))
            for candidate in lines[index + 1 : index + 9]:
                fields = candidate.split()
                if len(fields) >= 4 and fields[0] == str(center_node):
                    blocks.append((frequency, float(fields[3])))
                    break
            else:
                raise ValueError(f"Missing displacement for center node {center_node}.")
        return blocks

    @staticmethod
    def _stress_blocks(
        lines: list[str],
    ) -> list[tuple[float, dict[tuple[int, int], float]]]:
        blocks: list[tuple[float, dict[tuple[int, int], float]]] = []
        index = 0
        while index < len(lines):
            match = _STRESS_HEADER.search(lines[index])
            if match is None:
                index += 1
                continue
            frequency = float(match.group(1))
            values: dict[tuple[int, int], float] = {}
            index += 1
            while index < len(lines):
                fields = lines[index].split()
                if len(fields) >= 8 and fields[0].isdigit() and fields[1].isdigit():
                    values[(int(fields[0]), int(fields[1]))] = float(fields[2])
                    index += 1
                    continue
                if values:
                    break
                index += 1
            blocks.append((frequency, values))
        return blocks


def extrapolate_shell_surface_stress(
    gauss_values: dict[int, complex], *, xi: float, eta: float, face: float
) -> complex:
    """Extrapolate a trilinear expanded-shell stress from 8 Gauss points."""
    if set(gauss_values) != set(range(1, 9)):
        raise ValueError("Eight CalculiX Gauss-point values are required.")
    if xi not in {-1.0, 1.0} or eta not in {-1.0, 1.0} or face not in {-1.0, 1.0}:
        raise ValueError("Surface coordinates must be -1 or +1.")
    gauss = 1.0 / np.sqrt(3.0)
    coordinates = (
        (-gauss, -gauss, -gauss),
        (gauss, -gauss, -gauss),
        (gauss, gauss, -gauss),
        (-gauss, gauss, -gauss),
        (-gauss, -gauss, gauss),
        (gauss, -gauss, gauss),
        (gauss, gauss, gauss),
        (-gauss, gauss, gauss),
    )
    interpolation = np.asarray([_trilinear_terms(*point) for point in coordinates])
    values = np.asarray([gauss_values[index] for index in range(1, 9)], dtype=complex)
    coefficients = np.linalg.solve(interpolation, values)
    return complex(np.dot(_trilinear_terms(xi, eta, face), coefficients))


def summarize_calculix_points(
    points: list[CalculixFrequencyPoint], *, formulation: str
) -> dict[str, Any]:
    """Create a compact machine-readable summary without hiding formulation."""
    displacement_peak = max(points, key=lambda point: abs(point.center_uz))
    stress_peak = max(points, key=lambda point: abs(point.center_top_s11_pa))
    return {
        "status": "PASS" if points else "FAIL",
        "solver": {"name": "CalculiX", "version": "2.20-1"},
        "formulation": formulation,
        "frequency_point_count": len(points),
        "peak": {
            "frequency_hz": displacement_peak.frequency_hz,
            "center_uz_amplitude_mm": abs(displacement_peak.center_uz) * 1.0e3,
            "center_uz_phase_degrees": float(
                np.degrees(np.angle(displacement_peak.center_uz))
            ),
            "stress_peak_frequency_hz": stress_peak.frequency_hz,
            "center_top_s11_amplitude_mpa": abs(stress_peak.center_top_s11_pa) / 1.0e6,
            "center_top_s11_phase_degrees": float(
                np.degrees(np.angle(stress_peak.center_top_s11_pa))
            ),
        },
        "frequency_response": [point.to_dict() for point in points],
    }


def _pair_complex_blocks(
    blocks: list[tuple[float, Any]],
) -> list[tuple[float, complex | dict[tuple[int, int], complex]]]:
    if len(blocks) % 2:
        raise ValueError("CalculiX real/imaginary block count must be even.")
    pairs: list[tuple[float, complex | dict[tuple[int, int], complex]]] = []
    for index in range(0, len(blocks), 2):
        frequency, real = blocks[index]
        imag_frequency, imag = blocks[index + 1]
        if not np.isclose(frequency, imag_frequency, rtol=0.0, atol=1.0e-10):
            raise ValueError("CalculiX real/imaginary frequencies differ.")
        if isinstance(real, dict) and isinstance(imag, dict):
            if real.keys() != imag.keys():
                raise ValueError("CalculiX real/imaginary stress keys differ.")
            value: complex | dict[tuple[int, int], complex] = {
                key: complex(component, imag[key]) for key, component in real.items()
            }
        elif isinstance(real, float) and isinstance(imag, float):
            value = complex(real, imag)
        else:
            raise ValueError("CalculiX real/imaginary block types differ.")
        pairs.append((frequency, value))
    return pairs


def _trilinear_terms(xi: float, eta: float, zeta: float) -> np.ndarray:
    return np.asarray(
        [1.0, xi, eta, zeta, xi * eta, xi * zeta, eta * zeta, xi * eta * zeta]
    )
