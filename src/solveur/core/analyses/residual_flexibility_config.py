"""Strict opt-in configuration for the experimental WP-D01 harmonic method."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

from solveur.core.errors import InputValidationError


RESIDUAL_FLEXIBILITY_CONFIG_SCHEMA = "qf-harmonic-residual-flexibility-config/v1"
RESIDUAL_FLEXIBILITY_METHOD = "mode_acceleration"


@dataclass(frozen=True)
class ResidualFlexibilityConfig:
    enabled: bool = False
    method: str = RESIDUAL_FLEXIBILITY_METHOD


def residual_flexibility_config(
    parameters: Mapping[str, Any],
    *,
    analysis_type: str,
    method: str,
) -> ResidualFlexibilityConfig:
    """Validate the versioned option; an absent option preserves WP05 v1."""
    if not isinstance(parameters, Mapping):
        raise InputValidationError("Analysis parameters must be a mapping.")
    if "residual_flexibility" not in parameters:
        return ResidualFlexibilityConfig()
    raw = parameters["residual_flexibility"]
    if not isinstance(raw, Mapping):
        raise InputValidationError("analysis.parameters.residual_flexibility must be an object.")
    expected = {"schema", "enabled", "method"}
    if set(raw) != expected:
        missing = sorted(expected.difference(raw))
        extra = sorted(set(raw).difference(expected))
        raise InputValidationError(
            "analysis.parameters.residual_flexibility must define exactly schema, enabled and method "
            f"(missing={missing}, extra={extra})."
        )
    if raw.get("schema") != RESIDUAL_FLEXIBILITY_CONFIG_SCHEMA:
        raise InputValidationError("Unsupported residual-flexibility configuration schema.")
    enabled = raw.get("enabled")
    if not isinstance(enabled, bool):
        raise InputValidationError("analysis.parameters.residual_flexibility.enabled must be a boolean.")
    selected_method = raw.get("method")
    if selected_method != RESIDUAL_FLEXIBILITY_METHOD:
        raise InputValidationError(
            "analysis.parameters.residual_flexibility.method must be 'mode_acceleration'."
        )
    if not enabled:
        return ResidualFlexibilityConfig(enabled=False)
    if (analysis_type, method) != ("harmonic_response", "modal_superposition"):
        raise InputValidationError(
            "WP-D01 residual flexibility is supported only for harmonic_response/modal_superposition."
        )
    if "uniform_base_acceleration" in parameters:
        raise InputValidationError("WP-D01 residual flexibility does not support WP07 base acceleration.")
    if str(parameters.get("reduced_damping_model", "rayleigh_physical_projected")).strip().lower() != (
        "rayleigh_physical_projected"
    ):
        raise InputValidationError("WP-D01 supports physical Rayleigh damping only.")
    unsupported_damping = {"modal_damping_ratios", "modal_damping_targets", "damping_model"}.intersection(parameters)
    if unsupported_damping:
        raise InputValidationError(
            "WP-D01 does not support prescribed-modal or non-proportional damping settings: "
            + ", ".join(sorted(unsupported_damping))
            + "."
        )
    return ResidualFlexibilityConfig(enabled=True)


def validate_residual_flexibility_schema(
    parameters: Mapping[str, Any], *, analysis_type: str, method: str
) -> list[str]:
    """Return schema-facing errors while sharing runtime option semantics."""
    try:
        residual_flexibility_config(parameters, analysis_type=analysis_type, method=method)
    except InputValidationError as exc:
        return [str(exc)]
    return []


def residual_flexibility_implementation_hashes() -> dict[str, str]:
    """Fingerprint the D01 core, WP05 adapter, and identity dependencies."""
    source_root = Path(__file__).resolve().parents[2]
    relative_files = (
        "core/analyses/dynamic_reduction.py",
        "core/analyses/excitation_channels.py",
        "core/analyses/modal_basis.py",
        "core/analyses/modal_basis_damping.py",
        "core/analyses/modal_basis_numerics.py",
        "core/analyses/prepared_dynamic_system.py",
        "core/analyses/reduced_harmonic.py",
        "core/analyses/residual_flexibility.py",
        "core/analyses/residual_flexibility_config.py",
        "core/analyses/residual_flexibility_results.py",
        "core/analyses/settings.py",
        "io/checkpoint_common.py",
        "io/schema_analysis.py",
    )
    return {
        relative_path: hashlib.sha256((source_root / relative_path).read_bytes()).hexdigest()
        for relative_path in relative_files
    }
