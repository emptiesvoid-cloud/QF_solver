"""Canonical definition of one controlled V&V case."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Mapping


_CASE_ID = re.compile(r"^VNV026-[A-Z0-9]{2,3}-[A-Z0-9-]+$")
_EXECUTION_STATES = {"READY", "PLANNED", "DEFERRED", "BLOCKED"}


class VnvCaseError(ValueError):
    """Raised when a V&V case definition violates the controlled schema."""


@dataclass(frozen=True)
class VnvCase:
    """A stable, machine-readable V&V case definition.

    The schema intentionally permits a ``PLANNED`` case with no input model.
    That makes the future corpus visible without pretending that an unbuilt
    model has already produced evidence.
    """

    case_id: str
    title: str
    family: str
    capability: str
    maturity_target: str
    description: str
    analysis_type: str
    execution_state: str
    ci_profiles: tuple[str, ...]
    tags: tuple[str, ...]
    geometry: Mapping[str, Any] = field(default_factory=dict)
    element_family: str | None = None
    element_order: int | None = None
    mesh_strategy: str | None = None
    mesh_levels: tuple[str, ...] = ()
    material: Mapping[str, Any] = field(default_factory=dict)
    kinematics: str | None = None
    load_definition: Mapping[str, Any] = field(default_factory=dict)
    boundary_conditions: Mapping[str, Any] = field(default_factory=dict)
    solver_configuration: Mapping[str, Any] = field(default_factory=dict)
    oracle_types: tuple[str, ...] = ()
    oracle_ids: tuple[str, ...] = ()
    metrics: tuple[str, ...] = ()
    tolerance_ids: tuple[str, ...] = ()
    expected_behaviour: str = ""
    expected_failure: str | None = None
    random_seed: int | None = None
    cost_profile: str = "SMOKE"
    source_reference: str = ""
    known_limitations: tuple[str, ...] = ()
    input_model: str | None = None
    factory_id: str | None = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "VnvCase":
        """Create a validated definition from authoritative JSON data."""

        case_id = _text(raw, "case_id")
        if not _CASE_ID.fullmatch(case_id):
            raise VnvCaseError(f"Invalid 0.2.6 case id: {case_id!r}.")
        execution_state = _text(raw, "execution_state").upper()
        if execution_state not in _EXECUTION_STATES:
            raise VnvCaseError(f"{case_id}: unsupported execution_state {execution_state!r}.")
        profiles = _strings(raw.get("ci_profiles"), case_id, "ci_profiles")
        if not profiles:
            raise VnvCaseError(f"{case_id}: ci_profiles must not be empty.")
        input_model = _optional_text(raw.get("input_model"), case_id, "input_model")
        if execution_state == "READY" and not input_model:
            raise VnvCaseError(f"{case_id}: READY cases require input_model.")
        if execution_state != "READY" and input_model:
            raise VnvCaseError(f"{case_id}: only READY cases may define input_model.")
        seed = raw.get("random_seed")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
            raise VnvCaseError(f"{case_id}: random_seed must be an integer when supplied.")
        return cls(
            case_id=case_id,
            title=_text(raw, "title"),
            family=_text(raw, "family"),
            capability=_text(raw, "capability"),
            maturity_target=_text(raw, "maturity_target"),
            description=_text(raw, "description"),
            analysis_type=_text(raw, "analysis_type"),
            execution_state=execution_state,
            ci_profiles=profiles,
            tags=_strings(raw.get("tags"), case_id, "tags"),
            geometry=_mapping(raw.get("geometry"), case_id, "geometry"),
            element_family=_optional_text(raw.get("element_family"), case_id, "element_family"),
            element_order=raw.get("element_order"),
            mesh_strategy=_optional_text(raw.get("mesh_strategy"), case_id, "mesh_strategy"),
            mesh_levels=_strings(raw.get("mesh_levels", ()), case_id, "mesh_levels"),
            material=_mapping(raw.get("material"), case_id, "material"),
            kinematics=_optional_text(raw.get("kinematics"), case_id, "kinematics"),
            load_definition=_mapping(raw.get("load_definition"), case_id, "load_definition"),
            boundary_conditions=_mapping(raw.get("boundary_conditions"), case_id, "boundary_conditions"),
            solver_configuration=_mapping(raw.get("solver_configuration"), case_id, "solver_configuration"),
            oracle_types=_strings(raw.get("oracle_types", ()), case_id, "oracle_types"),
            oracle_ids=_strings(raw.get("oracle_ids", ()), case_id, "oracle_ids"),
            metrics=_strings(raw.get("metrics", ()), case_id, "metrics"),
            tolerance_ids=_strings(raw.get("tolerance_ids", ()), case_id, "tolerance_ids"),
            expected_behaviour=str(raw.get("expected_behaviour", "")),
            expected_failure=_optional_text(raw.get("expected_failure"), case_id, "expected_failure"),
            random_seed=seed,
            cost_profile=str(raw.get("cost_profile", "SMOKE")).upper(),
            source_reference=str(raw.get("source_reference", "")),
            known_limitations=_strings(raw.get("known_limitations", ()), case_id, "known_limitations"),
            input_model=input_model,
            factory_id=_optional_text(raw.get("factory_id"), case_id, "factory_id"),
        )

    def to_mapping(self) -> dict[str, Any]:
        """Return a JSON-compatible representation with stable list ordering."""

        return {
            "case_id": self.case_id,
            "title": self.title,
            "family": self.family,
            "capability": self.capability,
            "maturity_target": self.maturity_target,
            "description": self.description,
            "geometry": dict(self.geometry),
            "element_family": self.element_family,
            "element_order": self.element_order,
            "mesh_strategy": self.mesh_strategy,
            "mesh_levels": list(self.mesh_levels),
            "material": dict(self.material),
            "kinematics": self.kinematics,
            "analysis_type": self.analysis_type,
            "load_definition": dict(self.load_definition),
            "boundary_conditions": dict(self.boundary_conditions),
            "solver_configuration": dict(self.solver_configuration),
            "oracle_types": list(self.oracle_types),
            "oracle_ids": list(self.oracle_ids),
            "metrics": list(self.metrics),
            "tolerance_ids": list(self.tolerance_ids),
            "expected_behaviour": self.expected_behaviour,
            "expected_failure": self.expected_failure,
            "random_seed": self.random_seed,
            "cost_profile": self.cost_profile,
            "ci_profiles": list(self.ci_profiles),
            "source_reference": self.source_reference,
            "tags": list(self.tags),
            "known_limitations": list(self.known_limitations),
            "execution_state": self.execution_state,
            "input_model": self.input_model,
            "factory_id": self.factory_id,
        }


def _text(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise VnvCaseError(f"Case field {key!r} must be a non-empty string.")
    return value.strip()


def _optional_text(value: Any, case_id: str, key: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise VnvCaseError(f"{case_id}: {key} must be a non-empty string when supplied.")
    return value.strip()


def _strings(value: Any, case_id: str, key: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise VnvCaseError(f"{case_id}: {key} must be a list of non-empty strings.")
    return tuple(item.strip() for item in value)


def _mapping(value: Any, case_id: str, key: str) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise VnvCaseError(f"{case_id}: {key} must be an object.")
    return value
