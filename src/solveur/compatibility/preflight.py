"""Fail-closed compatibility checks before assembly and solve dispatch."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from solveur.compatibility.descriptors import (
    ElementCapabilityDescriptor,
    get_element_descriptor,
    normalize_element_name,
)


ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = ROOT / "qualification" / "0_2_7" / "capability_registry_v2.json"
ANALYSIS_ALIASES = {
    "static": "linear_static",
    "newmark": "transient_dynamic",
    "dynamic": "transient_dynamic",
    "harmonic": "harmonic_response",
    "buckling": "linear_buckling",
    "nonlinear": "nonlinear_static",
    "tl": "geometric_nonlinear_static",
}
MATERIAL_ALIASES = {
    "elastic": "isotropic_3d",
    "solid_elastic": "isotropic_3d",
    "j2": "von_mises_elastoplastic_3d",
    "small_strain_j2": "von_mises_elastoplastic_3d",
    "finite_kinematic_j2": "finite_kinematic_j2",
    "finite-kinematic-j2": "finite_kinematic_j2",
}
NOT_QUALIFIED_MATERIALS = {"finite_kinematic_j2"}
STATUS_CODES = {"SUPPORTED_ROUTE", "EXPERIMENTAL_ROUTE", "NOT_QUALIFIED_ROUTE", "UNSUPPORTED_ROUTE"}


@dataclass(frozen=True)
class CompatibilityResult:
    """Stable structured result for one technical combination check."""

    status: str
    reason: str
    message: str
    element_family: str | None
    analysis: str | None
    material_model: str | None
    formulation_or_route: str | None = None
    registry_maturity: str | None = None

    @property
    def ok(self) -> bool:
        return self.status != "UNSUPPORTED_ROUTE"

    def as_dict(self) -> dict[str, str | None]:
        return {
            "status": self.status,
            "reason": self.reason,
            "message": self.message,
            "element_family": self.element_family,
            "analysis": self.analysis,
            "material_model": self.material_model,
            "formulation_or_route": self.formulation_or_route,
            "registry_maturity": self.registry_maturity,
        }


class CompatibilityError(ValueError):
    """Raised when a model contains a technically unsupported combination."""

    def __init__(self, result: CompatibilityResult) -> None:
        self.result = result
        super().__init__(f"{result.reason}: {result.message}")


@dataclass(frozen=True)
class ModelCompatibilityReport:
    """Combined preflight result for all model elements and load categories."""

    results: tuple[CompatibilityResult, ...]

    @property
    def status(self) -> str:
        if any(result.status == "UNSUPPORTED_ROUTE" for result in self.results):
            return "UNSUPPORTED_ROUTE"
        if any(result.status == "NOT_QUALIFIED_ROUTE" for result in self.results):
            return "NOT_QUALIFIED_ROUTE"
        if any(result.status == "EXPERIMENTAL_ROUTE" for result in self.results):
            return "EXPERIMENTAL_ROUTE"
        return "SUPPORTED_ROUTE"

    @property
    def ok(self) -> bool:
        return all(result.ok for result in self.results)

    def raise_for_error(self) -> None:
        for result in self.results:
            if not result.ok:
                raise CompatibilityError(result)


def _normalize_analysis(value: str) -> str:
    key = str(value).strip().lower()
    return ANALYSIS_ALIASES.get(key, key)


def _normalize_material(value: str) -> str:
    key = str(value).strip().lower()
    return MATERIAL_ALIASES.get(key, key)


@lru_cache(maxsize=1)
def _registry_rows() -> tuple[dict[str, Any], ...]:
    try:
        payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    return tuple(row for row in payload.get("records", []) if row.get("record_kind") == "combination")


def _registry_maturity(element: str, analysis: str) -> str | None:
    for row in _registry_rows():
        if row.get("element_family") == element and row.get("analysis") == analysis:
            return str(row.get("qualification_state", "")) or None
    return None


def _result(
    status: str,
    reason: str,
    message: str,
    element: str | None,
    analysis: str | None,
    material: str | None,
    route: str | None,
    maturity: str | None = None,
) -> CompatibilityResult:
    if status not in STATUS_CODES:
        raise ValueError(f"Invalid compatibility status {status!r}.")
    return CompatibilityResult(status, reason, message, element, analysis, material, route, maturity)


def _route_status(
    descriptor: ElementCapabilityDescriptor,
    analysis: str,
    material: str,
    route: str | None,
) -> CompatibilityResult:
    element = descriptor.canonical_name
    if analysis not in descriptor.supported_analyses:
        return _result(
            "UNSUPPORTED_ROUTE", "ANALYSIS_NOT_SUPPORTED", f"{element} does not declare analysis {analysis!r}.",
            element, analysis, material, route,
        )
    if material not in descriptor.supported_material_families:
        return _result(
            "UNSUPPORTED_ROUTE", "MATERIAL_NOT_SUPPORTED", f"{element} does not declare material {material!r}.",
            element, analysis, material, route,
        )
    if route == "arc_length" and analysis != "nonlinear_static":
        return _result(
            "UNSUPPORTED_ROUTE", "FORMULATION_NOT_SUPPORTED", "arc_length requires nonlinear_static.",
            element, analysis, material, route,
        )
    if material in NOT_QUALIFIED_MATERIALS:
        return _result(
            "NOT_QUALIFIED_ROUTE", "MATERIAL_NOT_QUALIFIED", f"{material} is present as research inventory, not a qualified route.",
            element, analysis, material, route, "NOT_QUALIFIED",
        )
    maturity = _registry_maturity(element, analysis)
    if maturity == "NOT_QUALIFIED":
        return _result(
            "NOT_QUALIFIED_ROUTE", "REGISTRY_NOT_QUALIFIED", f"{element} + {analysis} is explicitly not qualified.",
            element, analysis, material, route, maturity,
        )
    if route == "arc_length" or maturity == "EXPERIMENTAL" or maturity is None:
        reason = "EXPERIMENTAL_ROUTE" if route == "arc_length" or maturity == "EXPERIMENTAL" else "NO_REGISTRY_COMBINATION"
        return _result(
            "EXPERIMENTAL_ROUTE", reason, f"{element} + {analysis} is technically declared but remains experimental/bounded by its registry state.",
            element, analysis, material, route, maturity,
        )
    return _result(
        "SUPPORTED_ROUTE", "SUPPORTED_COMBINATION", f"{element} + {analysis} is declared and has an active bounded registry record.",
        element, analysis, material, route, maturity,
    )


def check_compatibility(
    element_family: str,
    analysis: str,
    material_model: str,
    *,
    formulation_or_route: str | None = None,
    load_categories: tuple[str, ...] = (),
    backend: str | None = None,
) -> CompatibilityResult:
    """Check one combination and return a deterministic structured outcome."""

    normalized_analysis = _normalize_analysis(analysis)
    normalized_material = _normalize_material(material_model)
    try:
        descriptor = get_element_descriptor(element_family)
    except KeyError:
        return _result("UNSUPPORTED_ROUTE", "UNKNOWN_ELEMENT", f"Unknown element family {element_family!r}.", None, normalized_analysis, normalized_material, formulation_or_route)
    if backend is not None and backend not in {"scipy_sparse", "scipy_dense", "auto"}:
        return _result("UNSUPPORTED_ROUTE", "BACKEND_NOT_SUPPORTED", f"Backend {backend!r} is not declared for {descriptor.canonical_name}.", descriptor.canonical_name, normalized_analysis, normalized_material, formulation_or_route)
    result = _route_status(descriptor, normalized_analysis, normalized_material, formulation_or_route)
    if not result.ok:
        return result
    unsupported_loads = sorted(set(load_categories) - set(descriptor.supported_load_categories))
    if unsupported_loads:
        return _result("UNSUPPORTED_ROUTE", "LOAD_NOT_SUPPORTED", f"{descriptor.canonical_name} does not declare load category/categories {unsupported_loads!r}.", descriptor.canonical_name, normalized_analysis, normalized_material, formulation_or_route, result.registry_maturity)
    return result


def get_maturity(element_family: str, analysis: str, material_model: str = "isotropic_3d") -> str | None:
    """Return registry qualification state without inferring it from code."""

    element = normalize_element_name(element_family)
    return _registry_maturity(element, _normalize_analysis(analysis))


def explain_compatibility(**kwargs: Any) -> dict[str, str | None]:
    return check_compatibility(**kwargs).as_dict()


def _load_categories(model: Any) -> tuple[str, ...]:
    categories: list[str] = ["nodal"] if getattr(model, "loads", []) else []
    for load in getattr(model, "distributed_loads", []):
        load_type = str(getattr(load, "type", "")).lower()
        categories.append("surface_traction" if load_type == "surface_traction" else load_type)
    if getattr(model, "contacts", []):
        categories.append("frictionless_contact")
    return tuple(dict.fromkeys(categories))


def preflight_model(model: Any) -> ModelCompatibilityReport:
    """Build a model report before any assembly or solver is entered."""

    analysis_settings = getattr(model, "analysis", None)
    analysis = str(getattr(analysis_settings, "type", "linear_static"))
    method = str(getattr(analysis_settings, "method", ""))
    route = "arc_length" if method == "arc_length" else analysis
    loads = _load_categories(model)
    results: list[CompatibilityResult] = []
    for element in getattr(model, "elements", []):
        material_data = getattr(model, "materials", {}).get(element.material)
        if not isinstance(material_data, dict):
            results.append(_result("UNSUPPORTED_ROUTE", "MATERIAL_REFERENCE_MISSING", f"Material reference {element.material!r} is not defined.", str(element.type).upper(), _normalize_analysis(analysis), None, route))
            continue
        result = check_compatibility(
            element.type,
            analysis,
            str(material_data.get("type", "")),
            formulation_or_route=route,
            load_categories=loads,
        )
        results.append(result)
    if not results and (getattr(model, "springs", []) or getattr(model, "concentrated_masses", [])):
        results.append(check_compatibility("DISCRETE", analysis, "discrete_linear", load_categories=loads))
    if not results:
        results.append(_result("UNSUPPORTED_ROUTE", "NO_ELEMENTS_OR_ENTITIES", "Model has no compatible finite elements or discrete entities.", None, _normalize_analysis(analysis), None, route))
    return ModelCompatibilityReport(tuple(results))
