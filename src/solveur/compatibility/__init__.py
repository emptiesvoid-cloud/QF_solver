"""Technical compatibility descriptors and preflight API."""

from solveur.compatibility.descriptors import (
    DESCRIPTORS,
    ElementCapabilityDescriptor,
    get_element_descriptor,
    get_supported_analyses,
    get_supported_loads,
    normalize_element_name,
)
from solveur.compatibility.preflight import (
    CompatibilityError,
    CompatibilityResult,
    ModelCompatibilityReport,
    check_compatibility,
    explain_compatibility,
    get_maturity,
    preflight_model,
)

__all__ = [
    "DESCRIPTORS",
    "ElementCapabilityDescriptor",
    "CompatibilityError",
    "CompatibilityResult",
    "ModelCompatibilityReport",
    "check_compatibility",
    "explain_compatibility",
    "get_element_descriptor",
    "get_maturity",
    "get_supported_analyses",
    "get_supported_loads",
    "normalize_element_name",
    "preflight_model",
]
