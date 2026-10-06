"""Validated, unit-explicit configuration for the experimental rotor route."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, pi
from typing import Any, Mapping

import numpy as np

from solveur.core.errors import InputValidationError


FRAME_CONVENTION = "global_fixed_right_hand_rule"


@dataclass(frozen=True)
class RotationConfig:
    """Global spin axis and signed angular velocity, always expressed in rad/s."""

    axis_global: tuple[float, float, float]
    speed_rad_s: float
    frame_convention: str = FRAME_CONVENTION

    def __post_init__(self) -> None:
        axis = np.asarray(self.axis_global, dtype=float)
        if axis.shape != (3,) or not np.all(np.isfinite(axis)):
            raise InputValidationError("rotation.axis_global must contain three finite values.")
        scale = float(np.max(np.abs(axis)))
        if not isfinite(scale) or scale <= 0.0:
            raise InputValidationError("rotation.axis_global must be non-zero.")
        speed = float(self.speed_rad_s)
        if not isfinite(speed):
            raise InputValidationError("rotation.speed_rad_s must be finite.")
        if self.frame_convention != FRAME_CONVENTION:
            raise InputValidationError(f"rotation.frame_convention must be {FRAME_CONVENTION!r}.")
        scaled_axis = axis / scale
        unit_axis = scaled_axis / np.linalg.norm(scaled_axis)
        object.__setattr__(self, "axis_global", tuple(float(value) for value in unit_axis))
        object.__setattr__(self, "speed_rad_s", speed)

    @classmethod
    def from_mapping(cls, value: Any) -> "RotationConfig":
        if not isinstance(value, Mapping):
            raise InputValidationError("analysis.parameters.rotation must be an object.")
        expected = {"axis_global", "speed_rad_s", "frame_convention"}
        unknown = sorted(str(key) for key in value if key not in expected)
        missing = sorted(expected - set(value))
        if missing or unknown:
            pieces = []
            if missing:
                pieces.append(f"missing fields: {', '.join(missing)}")
            if unknown:
                pieces.append(f"unknown fields: {', '.join(unknown)}")
            raise InputValidationError("Invalid rotation configuration (" + "; ".join(pieces) + ").")
        try:
            return cls(
                axis_global=tuple(float(item) for item in value["axis_global"]),
                speed_rad_s=float(value["speed_rad_s"]),
                frame_convention=str(value["frame_convention"]),
            )
        except (TypeError, ValueError) as exc:
            if isinstance(exc, InputValidationError):
                raise
            raise InputValidationError(f"Invalid rotation configuration: {exc}") from exc

    @classmethod
    def from_rpm(
        cls,
        *,
        axis_global: tuple[float, float, float],
        speed_rpm: float,
        frame_convention: str = FRAME_CONVENTION,
    ) -> "RotationConfig":
        """Convert RPM only when the caller explicitly names that unit."""
        rpm = float(speed_rpm)
        if not isfinite(rpm):
            raise InputValidationError("speed_rpm must be finite.")
        return cls(axis_global=axis_global, speed_rad_s=rpm * (2.0 * pi / 60.0), frame_convention=frame_convention)

    def to_dict(self) -> dict[str, Any]:
        return {
            "axis_global": list(self.axis_global),
            "speed_rad_s": self.speed_rad_s,
            "frame_convention": self.frame_convention,
        }
