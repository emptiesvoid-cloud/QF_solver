"""Normalization helpers for the Code_Aster NAFEMS 13H correlation."""

from __future__ import annotations

import cmath
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class CodeAsterFrequencyPoint:
    """Complex center response reconstructed from one Code_Aster order."""

    frequency_hz: float
    uz_m: complex
    s11_top_pa: complex


@dataclass(frozen=True)
class CodeAsterTransientPoint:
    """Real center response reconstructed at one transient instant."""

    time_s: float
    uz_m: float
    s11_top_pa: float


class CodeAsterNafems13HParser:
    """Parse Code_Aster nodal fields and reconstruct the top-face stress."""

    def __init__(self, *, young_pa: float = 200.0e9, poisson: float = 0.3, thickness_m: float = 0.05):
        self.young_pa = float(young_pa)
        self.poisson = float(poisson)
        self.thickness_m = float(thickness_m)

    def parse(self, path: str | Path) -> list[CodeAsterFrequencyPoint]:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return [self._point(item) for item in payload["frequency_points"]]

    def _point(self, item: dict[str, Any]) -> CodeAsterFrequencyPoint:
        rotations = {
            int(node): (complex(*drx), complex(*dry))
            for node, drx, dry in item["center_rotations"]
        }
        stresses = [
            self.top_face_s11(
                [rotations[node][0] for node in element],
                [rotations[node][1] for node in element],
                element_size=float(item["element_size_m"]),
            )
            for element in item["center_elements"]
        ]
        return CodeAsterFrequencyPoint(
            frequency_hz=float(item["frequency_hz"]),
            uz_m=complex(*item["center_uz"]),
            s11_top_pa=sum(stresses) / len(stresses),
        )

    def top_face_s11(
        self,
        drx: list[complex],
        dry: list[complex],
        *,
        element_size: float,
    ) -> complex:
        """Return S11 at z=+t/2 from bilinear rotation gradients.

        Node order is bottom-left, bottom-right, top-right, top-left. For a
        plate whose normal is +Z, Code_Aster DRY is the rotation associated
        with x-curvature and DRX with y-curvature. Only the magnitude and
        relative phase are used for the external correlation because shell
        face/sign conventions differ between the published solvers.
        """
        if len(drx) != 4 or len(dry) != 4:
            raise ValueError("four corner rotations are required")
        if element_size <= 0.0:
            raise ValueError("element_size must be positive")
        d_dx = np.asarray([-1.0, 1.0, 1.0, -1.0]) / (2.0 * element_size)
        d_dy = np.asarray([-1.0, -1.0, 1.0, 1.0]) / (2.0 * element_size)
        kappa_x = complex(np.dot(d_dx, np.asarray(dry, dtype=complex)))
        kappa_y = complex(-np.dot(d_dy, np.asarray(drx, dtype=complex)))
        factor = self.young_pa * self.thickness_m / (2.0 * (1.0 - self.poisson**2))
        return factor * (kappa_x + self.poisson * kappa_y)

    def parse_transient(self, path: str | Path) -> list[CodeAsterTransientPoint]:
        """Parse real Newmark fields and reconstruct top-face stress."""
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        points: list[CodeAsterTransientPoint] = []
        for item in payload["time_points"]:
            rotations = {
                int(node): (float(drx), float(dry))
                for node, drx, dry in item["center_rotations"]
            }
            stresses = [
                self.top_face_s11(
                    [complex(rotations[node][0]) for node in element],
                    [complex(rotations[node][1]) for node in element],
                    element_size=float(item["element_size_m"]),
                ).real
                for element in item["center_elements"]
            ]
            points.append(
                CodeAsterTransientPoint(
                    time_s=float(item["time_s"]),
                    uz_m=float(item["center_uz"]),
                    s11_top_pa=float(np.mean(stresses)),
                )
            )
        return points


def complex_polar(value: complex) -> dict[str, float]:
    """Serialize a complex value with Cartesian, amplitude and phase data."""
    return {
        "real": float(value.real),
        "imag": float(value.imag),
        "amplitude": float(abs(value)),
        "phase_deg": float(np.degrees(cmath.phase(value))),
    }


def relative_difference(value: float, reference: float) -> float:
    """Return an absolute relative difference in percent."""
    if reference == 0.0:
        raise ValueError("reference must be non-zero")
    return 100.0 * abs(float(value) - float(reference)) / abs(float(reference))
