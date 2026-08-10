"""Analysis type and numerical method configuration."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any


DEFAULT_METHODS = {
    "linear_static": "direct",
    "modal": "eigsh",
    "nonlinear_static": "newton_raphson",
    "geometric_nonlinear_static": "newton_raphson",
    "transient_dynamic": "newmark",
    "harmonic_response": "direct_frequency",
}

SUPPORTED_METHODS = {
    "linear_static": ("direct", "spsolve", "cg", "conjugate_gradient", "gmres", "bicgstab", "minres"),
    "modal": ("eigh", "eigsh", "lanczos", "lobpcg"),
    "nonlinear_static": ("newton_raphson", "modified_newton", "newton_line_search", "arc_length"),
    "geometric_nonlinear_static": ("newton_raphson",),
    "transient_dynamic": ("newmark", "newmark_average_acceleration"),
    "harmonic_response": ("direct_frequency", "harmonic_direct"),
}

DYNAMIC_ANALYSIS_TYPES = {"modal", "transient_dynamic", "harmonic_response"}


@dataclass(frozen=True)
class AnalysisSettings:
    """Requested analysis family, method and method parameters."""

    type: str = "linear_static"
    method: str = "direct"
    parameters: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: str | dict[str, Any] | None) -> "AnalysisSettings":
        if raw is None:
            return cls()
        if isinstance(raw, str):
            analysis_type = raw.lower()
            return cls(type=analysis_type, method=DEFAULT_METHODS.get(analysis_type, "direct"))
        analysis_type = str(raw.get("type", "linear_static")).lower()
        method = str(raw.get("method", DEFAULT_METHODS.get(analysis_type, "direct"))).lower()
        parameters = dict(raw.get("parameters", {}))
        for key, value in raw.items():
            if key not in {"type", "method", "parameters"}:
                parameters[key] = value
        settings = cls(type=analysis_type, method=method, parameters=parameters)
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.type not in SUPPORTED_METHODS:
            raise ValueError(f"Unsupported analysis type {self.type!r}.")
        if self.method not in SUPPORTED_METHODS[self.type]:
            allowed = ", ".join(SUPPORTED_METHODS[self.type])
            raise ValueError(f"Unsupported method {self.method!r} for {self.type}; allowed: {allowed}.")
        mass_formulation = self.parameters.get("mass_formulation")
        if self.type in DYNAMIC_ANALYSIS_TYPES and mass_formulation is not None:
            normalized = str(mass_formulation).strip().lower()
            if normalized != "consistent":
                raise ValueError(
                    "Only mass_formulation='consistent' is supported for finite elements; "
                    "lumped element mass remains outside the qualified scope; explicit "
                    "concentrated_masses are handled separately as experimental entities."
                )
        if self.type == "transient_dynamic" and "postprocess_mode" in self.parameters:
            postprocess_mode = str(self.parameters["postprocess_mode"]).lower()
            if postprocess_mode not in {"full", "summary"}:
                raise ValueError("transient_dynamic postprocess_mode must be 'full' or 'summary'.")

    def with_overrides(self, *, analysis_type: str | None = None, method: str | None = None) -> "AnalysisSettings":
        next_type = (analysis_type or self.type).lower()
        next_method = (method or (DEFAULT_METHODS[next_type] if next_type != self.type else self.method)).lower()
        updated = replace(
            self,
            type=next_type,
            method=next_method,
        )
        updated.validate()
        return updated


def available_methods() -> dict[str, tuple[str, ...]]:
    """Return supported methods grouped by analysis type."""
    return SUPPORTED_METHODS.copy()
