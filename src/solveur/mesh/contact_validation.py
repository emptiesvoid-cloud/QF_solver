"""Model-level admissibility checks for the first frictionless-contact scope."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from solveur.core.errors import InputValidationError

if TYPE_CHECKING:
    from solveur.core.model import FiniteElementModel


def frictionless_contact_errors(model: "FiniteElementModel") -> list[str]:
    """Return blocking errors for unsupported contact combinations or geometry."""
    if not model.contacts:
        return []
    errors: list[str] = []
    common_penalty = (
        model.analysis.type in {"nonlinear_static", "geometric_nonlinear_static"}
        and str(model.analysis.parameters.get("contact_mode", "")).lower() == "penalty"
        and not any(contact.friction_coefficient > 0.0 for contact in model.contacts)
    )
    if model.analysis.type != "linear_static" and not common_penalty:
        errors.append(
            "Frictionless contact is supported for linear_static or explicit nonlinear/geometric "
            "nonlinear "
            "contact_mode='penalty' only."
        )
    if not common_penalty and model.analysis.method not in {"direct", "spsolve"}:
        errors.append("Frictionless contact currently requires the direct sparse method.")
    if model.multipoint_constraints or model.rbe2 or model.rbe3:
        errors.append("Frictionless contact cannot yet be combined with MPC or RBE links.")
    search_mode = str(model.analysis.parameters.get("contact_search_mode", "initial")).lower()
    if search_mode not in {"initial", "updated"}:
        errors.append("contact_search_mode must be 'initial' or 'updated'.")
    elif search_mode == "updated" and any(contact.friction_coefficient > 0.0 for contact in model.contacts):
        errors.append("Updated contact search is not yet available with frictional contact.")
    finite_sliding = model.analysis.parameters.get("contact_finite_sliding", False)
    if not isinstance(finite_sliding, bool):
        errors.append("contact_finite_sliding must be a boolean.")
        finite_sliding = False
    elif finite_sliding:
        if not common_penalty:
            errors.append(
                "contact_finite_sliding currently requires the common frictionless penalty path."
            )
        if search_mode != "updated":
            errors.append("contact_finite_sliding requires contact_search_mode='updated'.")
    _validate_positive_integer(model.analysis.parameters, "contact_max_iterations", errors)
    if common_penalty:
        _validate_positive_float(model.analysis.parameters, "contact_penalty", errors)
        _validate_positive_float(model.analysis.parameters, "contact_max_penetration", errors)
    if search_mode == "updated":
        _validate_positive_integer(model.analysis.parameters, "contact_search_max_iterations", errors)
        _validate_positive_float(model.analysis.parameters, "contact_search_tolerance", errors)
    for index, contact in enumerate(model.contacts):
        try:
            contact.geometry(model.nodes, allow_clamped_projection=finite_sliding)
        except InputValidationError as exc:
            errors.append(f"Contact {index}: {exc}")
    return errors


def _validate_positive_integer(parameters: dict[str, object], name: str, errors: list[str]) -> None:
    """Report an invalid iteration cap before the contact solver starts."""
    if name not in parameters:
        return
    try:
        value = _numeric_parameter(parameters[name])
    except (TypeError, ValueError):
        errors.append(f"{name} must be a positive integer.")
        return
    if not math.isfinite(value) or value <= 0.0 or not value.is_integer():
        errors.append(f"{name} must be a positive integer.")


def _validate_positive_float(parameters: dict[str, object], name: str, errors: list[str]) -> None:
    """Report an invalid contact-search tolerance before the solver starts."""
    if name not in parameters:
        return
    try:
        value = _numeric_parameter(parameters[name])
    except (TypeError, ValueError):
        errors.append(f"{name} must be a positive finite number.")
        return
    if not math.isfinite(value) or value <= 0.0:
        errors.append(f"{name} must be a positive finite number.")


def _numeric_parameter(value: object) -> float:
    """Decode JSON-compatible scalar input without accepting arbitrary objects."""
    if isinstance(value, bool):
        raise ValueError("Boolean values are not numerical contact settings.")
    if isinstance(value, (str, int, float)):
        return float(value)
    raise TypeError("Contact settings must be JSON scalar values.")
