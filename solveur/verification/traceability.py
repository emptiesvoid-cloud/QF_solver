"""Machine-readable requirement traceability and qualification readiness."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from solveur.core.errors import InputValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_REGISTRY = PROJECT_ROOT / "qualification" / "requirements.json"
INSTALLED_REGISTRY = Path(sys.prefix) / "qualification" / "requirements.json"
DEFAULT_REGISTRY = PROJECT_REGISTRY if PROJECT_REGISTRY.is_file() else INSTALLED_REGISTRY
PROJECT_FORMULA_REGISTRY = PROJECT_ROOT / "qualification" / "formulas.json"
INSTALLED_FORMULA_REGISTRY = Path(sys.prefix) / "qualification" / "formulas.json"
DEFAULT_FORMULA_REGISTRY = (
    PROJECT_FORMULA_REGISTRY if PROJECT_FORMULA_REGISTRY.is_file() else INSTALLED_FORMULA_REGISTRY
)
REQUIRED_LINK_FIELDS = ("design", "code", "functions", "tests", "artifacts")
PATH_LINK_FIELDS = ("design", "code", "tests", "artifacts")
FORMULA_LINK_FIELDS = ("document", "section", "code", "functions", "tests", "reference_id", "reference")
MECHANICAL_PREFIXES = ("REQ-SOL-", "REQ-MOD-", "REQ-DYN-", "REQ-HAR-", "REQ-NL-", "REQ-COMP-")


def _declared_scope_names(path: Path = DEFAULT_REGISTRY) -> tuple[str, ...]:
    """Read CLI scope choices from the controlled registry, not a duplicate list."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    scopes = data.get("scopes", {}) if isinstance(data, dict) else {}
    return tuple(sorted(str(name) for name in scopes if isinstance(name, str)))


QUALIFICATION_SCOPES = _declared_scope_names()


@dataclass(frozen=True)
class ReadinessCheck:
    """One traceability readiness check."""

    identifier: str
    status: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"id": self.identifier, "status": self.status, "detail": self.detail}


@dataclass(frozen=True)
class QualificationReadiness:
    """Readiness verdict for one declared qualification scope."""

    status: str
    scope: str
    scope_status: str
    requirement_count: int
    covered_requirement_count: int
    formula_count: int
    covered_formula_count: int
    orphan_requirements: tuple[str, ...]
    orphan_formulas: tuple[str, ...]
    missing_paths: tuple[str, ...]
    missing_independent_references: tuple[str, ...]
    formula_issues: tuple[str, ...]
    checks: tuple[ReadinessCheck, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "scope": self.scope,
            "scope_status": self.scope_status,
            "requirement_count": self.requirement_count,
            "covered_requirement_count": self.covered_requirement_count,
            "formula_count": self.formula_count,
            "covered_formula_count": self.covered_formula_count,
            "orphan_requirements": list(self.orphan_requirements),
            "orphan_formulas": list(self.orphan_formulas),
            "missing_paths": list(self.missing_paths),
            "missing_independent_references": list(self.missing_independent_references),
            "formula_issues": list(self.formula_issues),
            "checks": [check.to_dict() for check in self.checks],
        }


@dataclass(frozen=True)
class FormulaTraceability:
    """Coverage report for controlled mechanical formulas."""

    status: str
    requested_count: int
    covered_count: int
    orphan_formulas: tuple[str, ...]
    issues: tuple[str, ...]
    checks: tuple[ReadinessCheck, ...]


class FormulaRegistry:
    """Validate formula-to-document, code, test and reference links."""

    def __init__(self, path: str | Path = DEFAULT_FORMULA_REGISTRY) -> None:
        self.path = Path(path)
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InputValidationError(f"Cannot load formula registry {self.path}: {exc}") from exc
        if not isinstance(data, dict) or int(data.get("schema_version", 0)) != 1:
            raise InputValidationError("Formula registry schema_version must be 1.")
        records = data.get("formulas")
        if not isinstance(records, list):
            raise InputValidationError("Formula registry must contain a formula list.")
        self.formulas = {
            str(item.get("id", "")): item
            for item in records
            if isinstance(item, dict) and item.get("id")
        }
        if len(self.formulas) != len(records):
            raise InputValidationError("Formula registry contains an invalid or duplicate formula id.")

    def validate(self, identifiers: list[str], requirement_ids: set[str]) -> FormulaTraceability:
        checks: list[ReadinessCheck] = []
        orphans: list[str] = []
        issues: list[str] = []
        covered = 0
        for identifier in identifiers:
            record = self.formulas.get(identifier)
            if record is None:
                orphans.append(identifier)
                checks.append(ReadinessCheck(f"FORMULA-{identifier}", "FAIL", "formula record missing"))
                continue
            record_issues = self._record_issues(record, requirement_ids)
            if record_issues:
                issues.extend(f"{identifier}:{issue}" for issue in record_issues)
                checks.append(ReadinessCheck(f"FORMULA-{identifier}", "FAIL", "; ".join(record_issues)))
            else:
                covered += 1
                checks.append(
                    ReadinessCheck(
                        f"FORMULA-{identifier}",
                        "PASS",
                        "document/code/function/test/reference links verified",
                    )
                )
        status = "PASS" if not orphans and not issues else "FAIL"
        return FormulaTraceability(
            status=status,
            requested_count=len(identifiers),
            covered_count=covered,
            orphan_formulas=tuple(sorted(set(orphans))),
            issues=tuple(sorted(set(issues))),
            checks=tuple(checks),
        )

    @staticmethod
    def _record_issues(record: dict[str, object], requirement_ids: set[str]) -> list[str]:
        issues = [f"missing {field}" for field in FORMULA_LINK_FIELDS if not record.get(field)]
        requirement = str(record.get("requirement", ""))
        if requirement not in requirement_ids:
            issues.append(f"unknown requirement {requirement!r}")
        document = _resolve_link(str(record.get("document", "")))
        if document is None:
            issues.append(f"missing document {record.get('document')!r}")
        elif str(record.get("section", "")) not in document.read_text(encoding="utf-8"):
            issues.append(f"missing section {record.get('section')!r}")
        code_paths = [_resolve_link(str(path)) for path in _as_list(record.get("code"))]
        test_paths = [_resolve_link(str(path)) for path in _as_list(record.get("tests"))]
        if any(path is None for path in code_paths):
            issues.append("missing code path")
        if any(path is None for path in test_paths):
            issues.append("missing test path")
        code_text = "\n".join(path.read_text(encoding="utf-8") for path in code_paths if path is not None)
        for symbol in _as_list(record.get("functions")):
            name = str(symbol).rsplit(".", 1)[-1]
            if not re.search(rf"\bdef\s+{re.escape(name)}\s*\(", code_text):
                issues.append(f"missing function {symbol}")
        reference = _resolve_link(str(record.get("reference", "")).split("#", 1)[0])
        if reference is None:
            issues.append(f"missing reference {record.get('reference')!r}")
        elif str(record.get("reference_id", "")) not in reference.read_text(encoding="utf-8"):
            issues.append(f"missing reference id {record.get('reference_id')!r}")
        return issues


class QualificationRegistry:
    """Load and evaluate the controlled requirement registry."""

    def __init__(self, path: str | Path = DEFAULT_REGISTRY, formula_path: str | Path | None = None) -> None:
        self.path = Path(path)
        self.formula_path = Path(formula_path) if formula_path is not None else self.path.with_name("formulas.json")
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InputValidationError(f"Cannot load qualification registry {self.path}: {exc}") from exc
        self.requirements = {
            str(item.get("id", "")): item
            for item in self.data.get("requirements", [])
            if isinstance(item, dict) and item.get("id")
        }

    @property
    def scopes(self) -> tuple[str, ...]:
        return tuple(sorted(self.data.get("scopes", {})))

    def readiness(self, scope: str) -> QualificationReadiness:
        scopes = self.data.get("scopes", {})
        if scope not in scopes:
            allowed = ", ".join(self.scopes)
            raise InputValidationError(f"Unknown qualification scope {scope!r}; allowed: {allowed}.")
        scope_data = scopes[scope]
        scope_status = str(scope_data.get("status", "development"))
        identifiers = [str(value) for value in scope_data.get("requirements", [])]
        checks: list[ReadinessCheck] = []
        orphans: list[str] = []
        missing_paths: list[str] = []
        missing_references: list[str] = []
        formula_identifiers: list[str] = []

        checks.append(
            ReadinessCheck(
                "SCOPE-CANDIDATE",
                "PASS" if scope_status in {"candidate", "qualified"} else "FAIL",
                f"scope_status={scope_status}",
            )
        )
        for identifier in identifiers:
            requirement = self.requirements.get(identifier)
            if requirement is None:
                orphans.append(identifier)
                checks.append(ReadinessCheck(f"REQ-{identifier}", "FAIL", "requirement record missing"))
                continue
            missing_fields = [field for field in REQUIRED_LINK_FIELDS if not requirement.get(field)]
            if missing_fields:
                orphans.append(identifier)
                checks.append(
                    ReadinessCheck(f"REQ-{identifier}", "FAIL", "missing links: " + ", ".join(missing_fields))
                )
            else:
                checks.append(
                    ReadinessCheck(
                        f"REQ-{identifier}",
                        "PASS",
                        "design/code/function/test/artifact links present",
                    )
                )
            for field in PATH_LINK_FIELDS:
                for relative in requirement.get(field, []):
                    if not _linked_path_exists(str(relative)):
                        missing_paths.append(f"{identifier}:{field}:{relative}")
            if identifier.startswith(MECHANICAL_PREFIXES) and not requirement.get("independent_references"):
                missing_references.append(identifier)
            formula_identifiers.extend(str(value) for value in requirement.get("formulas", []))

        formula_report = FormulaTraceability("PASS", 0, 0, (), (), ())
        if formula_identifiers:
            formula_report = FormulaRegistry(self.formula_path).validate(
                formula_identifiers,
                set(identifiers),
            )
            checks.extend(formula_report.checks)

        checks.append(
            ReadinessCheck(
                "TRACE-PATHS",
                "PASS" if not missing_paths else "FAIL",
                "all linked paths exist" if not missing_paths else f"{len(missing_paths)} linked path(s) missing",
            )
        )
        checks.append(
            ReadinessCheck(
                "MECHANICAL-REFERENCES",
                "PASS" if not missing_references else "FAIL",
                "independent references declared"
                if not missing_references
                else "missing for: " + ", ".join(missing_references),
            )
        )
        failures = any(item.status == "FAIL" for item in checks)
        covered = len(identifiers) - len(set(orphans))
        return QualificationReadiness(
            status="FAIL" if failures else "PASS",
            scope=scope,
            scope_status=scope_status,
            requirement_count=len(identifiers),
            covered_requirement_count=covered,
            formula_count=formula_report.requested_count,
            covered_formula_count=formula_report.covered_count,
            orphan_requirements=tuple(sorted(set(orphans))),
            orphan_formulas=formula_report.orphan_formulas,
            missing_paths=tuple(sorted(set(missing_paths))),
            missing_independent_references=tuple(sorted(set(missing_references))),
            formula_issues=formula_report.issues,
            checks=tuple(checks),
        )


def qualification_readiness(scope: str, registry_path: str | Path = DEFAULT_REGISTRY) -> QualificationReadiness:
    """Evaluate one controlled qualification scope."""
    return QualificationRegistry(registry_path).readiness(scope)


def scope_for_model(model: object) -> str | None:
    """Map a standard model to its declared progressive qualification scope."""
    analysis = str(getattr(getattr(model, "analysis", None), "type", ""))
    elements = list(getattr(model, "elements", []))
    element_types = {str(getattr(element, "type", "")) for element in elements}
    materials = getattr(model, "materials", {})
    material_types = {
        str(materials.get(str(getattr(element, "material", "")), {}).get("type", ""))
        for element in elements
        if isinstance(materials, dict) and str(getattr(element, "material", "")) in materials
    }
    isotropic_shell_scope = not material_types or material_types == {"shell_isotropic"}
    if analysis == "nonlinear_static":
        return "material-nonlinear"
    if analysis == "geometric_nonlinear_static" and element_types == {"TET4"}:
        return "tet4-total-lagrangian-structural-v2"
    if analysis == "modal" and element_types == {"MITC4"} and isotropic_shell_scope:
        return "mitc4-modal"
    if analysis == "transient_dynamic" and element_types == {"MITC4"} and isotropic_shell_scope:
        return "mitc4-transient-dynamic"
    if analysis == "harmonic_response" and element_types == {"MITC4"} and isotropic_shell_scope:
        return "mitc4-harmonic-response"
    if analysis == "modal" and element_types == {"MITC3"} and isotropic_shell_scope:
        return "mitc3-modal"
    if analysis == "transient_dynamic" and element_types == {"MITC3"} and isotropic_shell_scope:
        return "mitc3-transient-dynamic"
    if analysis == "harmonic_response" and element_types == {"MITC3"} and isotropic_shell_scope:
        return "mitc3-harmonic-response"
    if analysis == "modal" and element_types == {"TET4"}:
        return "tet4-modal"
    if analysis == "transient_dynamic" and element_types == {"TET4"}:
        return "tet4-transient-dynamic"
    if analysis == "harmonic_response" and element_types == {"TET4"}:
        return "tet4-harmonic-response"
    if analysis == "modal" and element_types == {"TET10"}:
        return "tet10-modal"
    if analysis == "transient_dynamic" and element_types == {"TET10"}:
        return "tet10-transient-dynamic"
    if analysis == "harmonic_response" and element_types == {"TET10"}:
        return "tet10-harmonic-response"
    if analysis in {"modal", "transient_dynamic", "harmonic_response"} and element_types == {"BEAM2"}:
        return "beam2-linear-dynamics"
    if (
        analysis in {"modal", "transient_dynamic", "harmonic_response"}
        and not element_types
        and (getattr(model, "springs", ()) or getattr(model, "concentrated_masses", ()))
    ):
        return "discrete-linear-dynamics"
    if analysis in {"modal", "transient_dynamic", "harmonic_response"}:
        return "linear-dynamics"
    if analysis == "linear_static" and element_types == {"TET4"}:
        return "tet4-linear-static"
    if analysis == "linear_static" and element_types == {"BEAM2"}:
        return "beam2-linear-static"
    if analysis == "linear_static" and element_types == {"TET10"}:
        return "tet10-linear-static"
    if analysis == "linear_static" and element_types == {"MITC4"} and isotropic_shell_scope:
        return "mitc4-linear-static"
    if analysis == "linear_static" and element_types == {"MITC3"}:
        if material_types == {"shell_laminate"}:
            return "mitc3-laminate-static"
        if isotropic_shell_scope:
            return "mitc3-linear-static"
    return None


def model_traceability_summary(model: object) -> dict[str, Any]:
    """Return compact evidence metadata for the model's declared scope."""
    scope = scope_for_model(model)
    if scope is None:
        return {
            "status": "FAIL",
            "scope": "unscoped",
            "reason": "No progressive qualification scope covers this feature combination.",
        }
    report = qualification_readiness(scope)
    return {
        "status": report.status,
        "scope": report.scope,
        "scope_status": report.scope_status,
        "requirement_count": report.requirement_count,
        "covered_requirement_count": report.covered_requirement_count,
        "formula_count": report.formula_count,
        "covered_formula_count": report.covered_formula_count,
        "orphan_requirements": list(report.orphan_requirements),
        "orphan_formulas": list(report.orphan_formulas),
    }


def _linked_path_exists(relative: str) -> bool:
    return any((base / relative).exists() for base in (PROJECT_ROOT, Path(sys.prefix)))


def _resolve_link(relative: str) -> Path | None:
    for base in (PROJECT_ROOT, Path(sys.prefix)):
        candidate = base / relative
        if candidate.is_file():
            return candidate
    return None


def _as_list(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []
