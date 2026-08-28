"""Qualification profiles and maturity metadata for trustable solver use."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any

from solveur.version import __version__


class RunVerdict(str, Enum):
    """Machine-readable acceptance verdict distinct from numerical status."""

    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


PROFILES = ("quick", "engineering", "strict", "qualification")

MATURITY_BY_ANALYSIS = {
    "linear_static": "stable",
    "modal": "stable_after_reinforced_tests",
    "transient_dynamic": "stable_after_reinforced_tests",
    "harmonic_response": "stable_after_reinforced_tests",
    "nonlinear_static": "experimental",
    "geometric_nonlinear_static": "research",
    "linear_buckling": "research",
}

MATURITY_BY_ELEMENT = {
    "BEAM2": "experimental",
    "TET4": "stable",
    "MITC4": "stable",
    "MITC3": "experimental",
    "TET10": "stable_after_reinforced_tests",
    "HEX8": "stable_after_reinforced_tests",
    "HEX20": "stable_after_reinforced_tests",
}

MATURITY_BY_MATERIAL = {
    "beam_isotropic": "experimental",
    "isotropic_3d": "stable",
    "shell_isotropic": "stable",
    "orthotropic_lamina": "experimental",
    "shell_laminate": "experimental",
    "orthotropic_3d": "research",
    "composite_orthotropic_3d": "research",
    "nonlinear_isotropic_3d": "experimental",
    "von_mises_elastoplastic_3d": "experimental",
}

MATURITY_BY_METHOD = {
    "arc_length": "experimental",
    "newton_raphson": "experimental",
    "modified_newton": "experimental",
    "newton_line_search": "experimental",
}

EVIDENCE_LEVEL_BY_PROFILE = {
    "quick": "developer_smoke",
    "engineering": "engineering_review",
    "strict": "strict_review",
    "qualification": "qualification_candidate",
}

TET4_LINEAR_STATIC_DOMAIN = {
    "material_type": "isotropic_3d",
    "young_modulus": {"minimum_exclusive": 0.0, "unit": "Pa"},
    "poisson_ratio": {"minimum": 0.0, "maximum": 0.45},
    "tet_min_quality": 5.0e-2,
    "tet_min_radius_ratio": 5.0e-2,
    "tet_max_aspect_ratio": 20.0,
    "reduced_stiffness_condition_estimate_max": 1.0e12,
}


@dataclass(frozen=True)
class VerificationProfile:
    """Threshold and evidence policy chosen for one run."""

    name: str
    fail_on_warning: bool
    allow_experimental: bool
    required_evidence_level: str


def verification_profile(name: str | None) -> VerificationProfile:
    """Return normalized profile settings."""
    normalized = (name or "engineering").lower()
    if normalized not in PROFILES:
        allowed = ", ".join(PROFILES)
        raise ValueError(f"Unsupported verification profile {name!r}; allowed: {allowed}.")
    return VerificationProfile(
        name=normalized,
        fail_on_warning=normalized in {"strict", "qualification"},
        allow_experimental=normalized != "qualification",
        required_evidence_level=EVIDENCE_LEVEL_BY_PROFILE[normalized],
    )


def model_maturity(model: object) -> dict[str, Any]:
    """Classify the maturity of features used by a model."""
    analysis = getattr(getattr(model, "analysis", None), "type", "")
    method = getattr(getattr(model, "analysis", None), "method", "")
    elements = sorted({getattr(element, "type", "") for element in getattr(model, "elements", [])})
    material_data = getattr(model, "materials", {})
    used_materials = sorted({getattr(element, "material", "") for element in getattr(model, "elements", [])})
    material_types = sorted(
        {
            str(material_data.get(name, {}).get("type", ""))
            for name in used_materials
            if isinstance(material_data, dict)
        }
    )
    maturities = [MATURITY_BY_ANALYSIS.get(analysis, "research")]
    maturities.extend(MATURITY_BY_ELEMENT.get(element, "research") for element in elements)
    maturities.extend(MATURITY_BY_MATERIAL.get(material, "research") for material in material_types)
    discrete: dict[str, str] = {}
    if getattr(model, "springs", []):
        discrete["springs"] = "experimental"
        maturities.append("experimental")
    if getattr(model, "concentrated_masses", []):
        discrete["concentrated_masses"] = "experimental"
        maturities.append("experimental")
    if getattr(model, "multipoint_constraints", []):
        discrete["multipoint_constraints"] = "experimental"
        maturities.append("experimental")
    if getattr(model, "rbe2", []):
        discrete["rbe2"] = "experimental"
        maturities.append("experimental")
    if getattr(model, "rbe3", []):
        discrete["rbe3"] = "experimental"
        maturities.append("experimental")
    contacts = getattr(model, "contacts", [])
    if contacts:
        has_friction = any(float(getattr(contact, "friction_coefficient", 0.0)) > 0.0 for contact in contacts)
        discrete["frictional_contact" if has_friction else "frictionless_contact"] = "experimental"
        maturities.append("experimental")
    if method in MATURITY_BY_METHOD:
        maturities.append(MATURITY_BY_METHOD[method])
    overall = _lowest_maturity(maturities)
    return {
        "overall": overall,
        "analysis": MATURITY_BY_ANALYSIS.get(analysis, "research"),
        "method": MATURITY_BY_METHOD.get(method, "stable"),
        "elements": {element: MATURITY_BY_ELEMENT.get(element, "research") for element in elements},
        "discrete_entities": discrete,
    }


def qualification_metadata(model: object) -> dict[str, Any]:
    """Build stable metadata written in audits and evidence bundles."""
    from solveur.verification.traceability import model_traceability_summary

    profile = verification_profile(getattr(model, "verification_profile", "engineering"))
    return {
        "solver_version": __version__,
        "schema_version": int(getattr(model, "schema_version", 1)),
        "units": dict(getattr(model, "units", {"system": "SI"})),
        "verification_profile": profile.name,
        "evidence_level": profile.required_evidence_level,
        "maturity": model_maturity(model),
        "qualification_domain": model_qualification_domain(model),
        "traceability": model_traceability_summary(model),
    }


def model_qualification_domain(model: object) -> dict[str, Any]:
    """Report whether a model lies inside the bounded TET4 qualification domain."""
    analysis = getattr(getattr(model, "analysis", None), "type", "")
    elements = list(getattr(model, "elements", []))
    element_types = sorted({str(getattr(element, "type", "")) for element in elements})
    if analysis != "linear_static" or element_types != ["TET4"]:
        return {
            "name": "tet4-linear-static-v1",
            "status": "NOT_APPLICABLE",
            "reason": "Domain applies only to linear_static models containing TET4 elements exclusively.",
            "limits": dict(TET4_LINEAR_STATIC_DOMAIN),
        }

    materials = getattr(model, "materials", {})
    used_names = sorted({str(getattr(element, "material", "")) for element in elements})
    violations: list[str] = []
    observations: list[dict[str, Any]] = []
    for name in used_names:
        raw = materials.get(name, {}) if isinstance(materials, dict) else {}
        material_type = str(raw.get("type", ""))
        young = _finite_float(raw.get("E"))
        poisson = _finite_float(raw.get("nu"))
        observations.append({"name": name, "type": material_type, "E": young, "nu": poisson})
        if material_type != TET4_LINEAR_STATIC_DOMAIN["material_type"]:
            violations.append(f"Material {name!r} must use type 'isotropic_3d'.")
        if young is None or young <= 0.0:
            violations.append(f"Material {name!r} requires a finite Young modulus E > 0 Pa.")
        if poisson is None or not 0.0 <= poisson <= 0.45:
            violations.append(f"Material {name!r} requires 0 <= nu <= 0.45 in the bounded TET4 domain.")
    return {
        "name": "tet4-linear-static-v1",
        "status": "WARNING" if violations else "PASS",
        "limits": dict(TET4_LINEAR_STATIC_DOMAIN),
        "materials": observations,
        "violations": violations,
    }


def qualification_summary(result: object, model: object | None = None) -> dict[str, Any]:
    """Return a machine-readable trust verdict for a result or audit."""
    audit = getattr(result, "audit", result)
    data = audit.to_dict() if hasattr(audit, "to_dict") else {}
    checks = data.get("checks", [])
    fail_count = sum(1 for check in checks if check.get("status") == "FAIL")
    warning_count = sum(1 for check in checks if check.get("status") == "WARNING")
    metadata = data.get("qualification", {})
    if model is not None:
        metadata = qualification_metadata(model)
    profile = verification_profile(metadata.get("verification_profile", "engineering"))
    maturity = metadata.get("maturity", {}).get("overall", "research")
    units = metadata.get("units", {"system": "SI"})
    traceability = metadata.get("traceability", {})
    qualification_domain = metadata.get("qualification_domain", {})
    blocking_errors: list[str] = []
    warnings: list[str] = []
    if fail_count:
        blocking_errors.append(f"{fail_count} audit check(s) failed.")
    if warning_count:
        message = f"{warning_count} audit warning(s) present."
        if profile.fail_on_warning:
            blocking_errors.append(message)
        else:
            warnings.append(message)
    if maturity in {"experimental", "research"}:
        message = f"Maturity {maturity!r} is used under profile {profile.name!r}."
        if not profile.allow_experimental:
            blocking_errors.append(f"Maturity {maturity!r} is not allowed by qualification profile.")
        elif profile.fail_on_warning:
            blocking_errors.append(message)
        else:
            warnings.append(message)
    if profile.name == "qualification":
        blocking_errors.extend(_qualification_unit_errors(units))
    if qualification_domain.get("status") == "WARNING":
        domain_messages = list(qualification_domain.get("violations", []))
        message = "Qualification domain violation: " + "; ".join(domain_messages)
        if profile.fail_on_warning:
            blocking_errors.append(message)
        else:
            warnings.append(message)
    if traceability and traceability.get("status") != "PASS":
        scope = traceability.get("scope", "unscoped")
        message = f"Qualification scope {scope!r} is not readiness PASS."
        if profile.fail_on_warning:
            blocking_errors.append(message)
        else:
            warnings.append(message)
    status = RunVerdict.FAIL if blocking_errors else (RunVerdict.WARNING if warnings else RunVerdict.PASS)
    return {
        "status": status.value,
        "run_verdict": status.value,
        "blocking_errors": blocking_errors,
        "warnings": warnings,
        "trust_score": _trust_score(status.value, fail_count, warning_count, maturity),
        "trust_score_non_certifying": True,
        "evidence_level": profile.required_evidence_level,
        "verification_profile": profile.name,
        "maturity": metadata.get("maturity", {}),
        "qualification_domain": qualification_domain,
    }


def run_verdict(result: object, model: object | None = None) -> RunVerdict:
    """Return the enforced run verdict for a result and optional model."""
    return RunVerdict(qualification_summary(result, model)["status"])


def enforce_qualification_policy(result: object, model: object | None = None) -> object:
    """Raise when the selected profile rejects a numerically completed run."""
    from solveur.core.errors import QualificationGateError

    summary = qualification_summary(result, model)
    if summary["status"] == RunVerdict.FAIL.value:
        details = "; ".join(summary["blocking_errors"]) or "Qualification policy rejected the run."
        raise QualificationGateError(details, result=result, summary=summary)
    return result


def _lowest_maturity(values: list[str]) -> str:
    rank = {"stable": 0, "stable_after_reinforced_tests": 1, "experimental": 2, "research": 3}
    return max(values or ["research"], key=lambda item: rank.get(item, 3))


def _trust_score(status: str, fail_count: int, warning_count: int, maturity: str) -> float:
    score = 1.0
    score -= 0.35 * fail_count
    score -= 0.08 * warning_count
    score -= {"stable": 0.0, "stable_after_reinforced_tests": 0.1, "experimental": 0.25, "research": 0.45}.get(
        maturity, 0.45
    )
    if status == "FAIL":
        score = min(score, 0.49)
    return float(max(0.0, min(1.0, score)))


def _qualification_unit_errors(units: object) -> list[str]:
    if not isinstance(units, dict):
        return ["Qualification profile requires explicit SI unit metadata."]
    errors: list[str] = []
    if str(units.get("system", "SI")).upper() != "SI":
        errors.append("Qualification profile accepts only the SI unit system.")
    canonical = {"length": "m", "force": "N", "mass": "kg", "time": "s", "stress": "Pa"}
    for name, expected in canonical.items():
        if name in units and units[name] != expected:
            errors.append(f"Qualification profile requires units.{name}={expected!r}.")
    return errors


def _finite_float(value: object) -> float | None:
    try:
        converted = float(str(value))
    except (TypeError, ValueError):
        return None
    return converted if math.isfinite(converted) else None
