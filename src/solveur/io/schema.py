"""Strict validation for JSON model dictionaries."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from solveur.core.dofs import DOF_ORDER
from solveur.core.errors import InputValidationError
from solveur.io.contact_schema import ContactSchemaValidator
from solveur.io.constraint_schema import ConstraintSchemaValidator
from solveur.io.discrete_schema import DiscreteEntitySchemaValidator
from solveur.io.load_schema import DistributedLoadSchemaValidator
from solveur.io.schema_values import (
    is_int as _is_int,
    is_number as _is_number,
    reject_unknown,
    require_fields,
)
from solveur.io.schema_analysis import JsonSchemaAnalysisMixin
from solveur.io.schema_entities import JsonSchemaEntityMixin


class JsonSchemaValidator(JsonSchemaAnalysisMixin, JsonSchemaEntityMixin):
    """Validate input shape before building finite element model objects."""

    _top_level_fields = {
        "analysis",
        "schema_version",
        "units",
        "verification_profile",
        "nodes",
        "elements",
        "materials",
        "fixed_dofs",
        "loads",
        "distributed_loads",
        "springs",
        "concentrated_masses",
        "multipoint_constraints",
        "rbe2",
        "rbe3",
        "contacts",
    }
    _verification_profiles = {"quick", "engineering", "strict", "qualification"}
    _material_fields = {
        "beam_isotropic": {
            "type",
            "E",
            "G",
            "nu",
            "A",
            "Iy",
            "Iz",
            "J",
            "kappa_y",
            "kappa_z",
            "density",
            "rho",
            "reference_vector",
        },
        "isotropic_3d": {"type", "E", "nu", "density", "rho"},
        "orthotropic_3d": {
            "type",
            "E1",
            "E2",
            "E3",
            "nu12",
            "nu13",
            "nu23",
            "G12",
            "G13",
            "G23",
            "density",
            "rho",
            "orientation",
            "e1",
            "e2_hint",
            "orientation_field",
        },
        "composite_orthotropic_3d": {
            "type",
            "E1",
            "E2",
            "E3",
            "nu12",
            "nu13",
            "nu23",
            "G12",
            "G13",
            "G23",
            "density",
            "rho",
            "orientation",
            "e1",
            "e2_hint",
            "orientation_field",
            "provenance",
            "homogenization",
            "layup",
            "fiber_volume_fraction",
            "strengths",
        },
        "nonlinear_isotropic_3d": {"type", "E", "nu", "density", "rho", "hardening"},
        "von_mises_elastoplastic_3d": {"type", "E", "nu", "density", "rho", "yield_stress", "hardening_modulus", "H"},
        "shell_isotropic": {"type", "E", "nu", "t", "shear_factor", "drilling_scale", "density", "rho"},
        "orthotropic_lamina": {"type", "E1", "E2", "nu12", "G12", "G13", "G23", "density", "rho"},
        "shell_laminate": {
            "type",
            "plies",
            "shear_factor",
            "drilling_scale",
            "reference_direction",
        },
    }
    def validate(self, data: Any) -> None:
        """Raise ValueError when the JSON data does not match the v1 schema."""
        errors: list[str] = []
        if not isinstance(data, Mapping):
            raise InputValidationError("JSON root must be an object.")
        self._reject_unknown("root", data, self._top_level_fields, errors)
        self._require_fields("root", data, ("nodes", "elements", "materials"), errors)
        self._validate_schema_version(data.get("schema_version", 1), errors)
        self._validate_units(data.get("units", {"system": "SI"}), errors)
        self._validate_verification_profile(data.get("verification_profile", "engineering"), errors)
        self._validate_qualification_units(
            data.get("units", {"system": "SI"}), data.get("verification_profile", "engineering"), errors
        )
        node_count = self._validate_nodes(data.get("nodes"), errors)
        materials = self._validate_materials(data.get("materials", {}), errors)
        self._validate_analysis(data.get("analysis", "linear_static"), errors)
        self._validate_elements(data.get("elements", []), materials, node_count, errors)
        self._validate_fixed_dofs(data.get("fixed_dofs", []), node_count, errors)
        self._validate_loads(data.get("loads", []), node_count, errors)
        DistributedLoadSchemaValidator().validate(data.get("distributed_loads", []), data.get("elements"), errors)
        DiscreteEntitySchemaValidator().validate(
            data.get("springs", []),
            data.get("concentrated_masses", []),
            node_count,
            errors,
        )
        ConstraintSchemaValidator().validate(data.get("multipoint_constraints", []), node_count, errors)
        ConstraintSchemaValidator().validate_rbes(data.get("rbe2", []), data.get("rbe3", []), node_count, errors)
        ContactSchemaValidator().validate(data.get("contacts", []), node_count, errors)
        if not data.get("elements") and not data.get("springs"):
            errors.append("root must define at least one finite element or spring.")
        if errors:
            raise InputValidationError("Invalid model JSON:\n- " + "\n- ".join(errors))





    @staticmethod
    def _validate_schema_version(value: Any, errors: list[str]) -> None:
        if not _is_int(value):
            errors.append("schema_version must be an integer when provided.")
            return
        if int(value) != 1:
            errors.append(f"schema_version {value!r} is unsupported; only version 1 is accepted.")

    @staticmethod
    def _validate_units(value: Any, errors: list[str]) -> None:
        if not isinstance(value, Mapping):
            errors.append("units must be an object when provided.")
            return
        allowed = {"system", "length", "force", "mass", "time", "stress"}
        JsonSchemaValidator._reject_unknown("units", value, allowed, errors)
        for key, unit in value.items():
            if not isinstance(unit, str) or not unit:
                errors.append(f"units.{key} must be a non-empty string.")

    def _validate_verification_profile(self, value: Any, errors: list[str]) -> None:
        if not isinstance(value, str):
            errors.append("verification_profile must be a string when provided.")
            return
        if value.lower() not in self._verification_profiles:
            allowed = ", ".join(sorted(self._verification_profiles))
            errors.append(f"verification_profile {value!r} is unsupported; allowed: {allowed}.")

    @staticmethod
    def _validate_qualification_units(units: Any, profile: Any, errors: list[str]) -> None:
        if not isinstance(profile, str) or profile.lower() != "qualification" or not isinstance(units, Mapping):
            return
        expected = {"system": "SI", "length": "m", "force": "N", "mass": "kg", "time": "s", "stress": "Pa"}
        if str(units.get("system", "SI")).upper() != "SI":
            errors.append("qualification profile accepts only the SI unit system.")
        for key, canonical in expected.items():
            if key != "system" and key in units and units[key] != canonical:
                errors.append(f"qualification profile requires units.{key}={canonical!r}; got {units[key]!r}.")

    @staticmethod
    def _validate_rayleigh(params: Mapping[str, Any], errors: list[str]) -> None:
        for key in ("rayleigh_alpha", "rayleigh_beta"):
            if key in params and (not _is_number(params[key]) or float(params[key]) < 0.0):
                errors.append(f"analysis.{key} must be a non-negative finite number.")

    @staticmethod
    def _validate_modal_damping_targets(params: Mapping[str, Any], errors: list[str]) -> None:
        if "modal_damping_targets" not in params:
            return
        if "rayleigh_alpha" in params or "rayleigh_beta" in params:
            errors.append("analysis.modal_damping_targets cannot be combined with Rayleigh coefficients.")
        targets = params["modal_damping_targets"]
        if not isinstance(targets, list) or len(targets) != 2:
            errors.append("analysis.modal_damping_targets must contain exactly two targets.")
            return
        for index, target in enumerate(targets):
            path = f"analysis.modal_damping_targets[{index}]"
            if not isinstance(target, Mapping) or set(target) != {
                "frequency_hz",
                "damping_ratio",
            }:
                errors.append(f"{path} must contain frequency_hz and damping_ratio.")
                continue
            if not _is_number(target["frequency_hz"]) or float(target["frequency_hz"]) <= 0.0:
                errors.append(f"{path}.frequency_hz must be a positive finite number.")
            if not _is_number(target["damping_ratio"]) or float(target["damping_ratio"]) < 0.0:
                errors.append(f"{path}.damping_ratio must be a non-negative finite number.")

    @staticmethod
    def _validate_load_factors_by_load(value: Any, errors: list[str]) -> None:
        if not isinstance(value, Mapping):
            errors.append("analysis.load_factors_by_load must be an object keyed by load index.")
            return
        for key, factors in value.items():
            path = f"analysis.load_factors_by_load[{key!r}]"
            if not str(key).isdigit():
                errors.append(f"{path} key must be a non-negative integer index.")
            if not isinstance(factors, list) or not factors:
                errors.append(f"{path} must be a non-empty list.")
                continue
            if any(not _is_number(factor) for factor in factors):
                errors.append(f"{path} must contain finite numeric factors.")

    @staticmethod
    def _validate_load_table(value: Any, errors: list[str]) -> None:
        if not isinstance(value, list) or not value:
            errors.append("analysis.load_table must be a non-empty list of time/factor objects.")
            return
        previous_time: float | None = None
        for index, item in enumerate(value):
            path = f"analysis.load_table[{index}]"
            if not isinstance(item, Mapping) or set(item) != {"time", "factor"}:
                errors.append(f"{path} must contain exactly time and factor.")
                continue
            if not _is_number(item["time"]) or float(item["time"]) < 0.0:
                errors.append(f"{path}.time must be a non-negative finite number.")
            if not _is_number(item["factor"]):
                errors.append(f"{path}.factor must be a finite number.")
            if _is_number(item["time"]):
                current_time = float(item["time"])
                if previous_time is not None and current_time <= previous_time:
                    errors.append("analysis.load_table times must be strictly increasing.")
                previous_time = current_time

    @staticmethod
    def _require_any(path: str, value: Mapping[str, Any], names: tuple[str, ...], errors: list[str]) -> None:
        if not any(name in value for name in names):
            errors.append(f"{path} must define one of: {', '.join(names)}.")

    @staticmethod
    def _positive_number(path: str, value: Any, errors: list[str]) -> None:
        if not _is_number(value) or float(value) <= 0.0:
            errors.append(f"{path} must be a positive finite number.")

    @staticmethod
    def _nonnegative_number(path: str, value: Any, errors: list[str]) -> None:
        if not _is_number(value) or float(value) < 0.0:
            errors.append(f"{path} must be a non-negative finite number.")

    @staticmethod
    def _positive_int(path: str, value: Any, errors: list[str]) -> None:
        if not _is_int(value) or int(value) <= 0:
            errors.append(f"{path} must be a positive integer.")

    @staticmethod
    def _nonnegative_int(path: str, value: Any, errors: list[str]) -> None:
        if not _is_int(value) or int(value) < 0:
            errors.append(f"{path} must be a non-negative integer.")

    @staticmethod
    def _element_type(path: str, value: Any, errors: list[str]) -> str | None:
        if not isinstance(value, str) or not value:
            errors.append(f"{path}.type must be a non-empty string.")
            return None
        return value.upper()

    @staticmethod
    def _validate_element_nodes(
        path: str, value: Any, node_count: int, expected_count: int | None, errors: list[str]
    ) -> None:
        if not isinstance(value, list):
            errors.append(f"{path}.nodes must be a list of node indices.")
            return
        if expected_count is not None and len(value) != expected_count:
            errors.append(f"{path}.nodes must contain exactly {expected_count} node indices.")
        for node_position, node in enumerate(value):
            JsonSchemaValidator._validate_node_index(f"{path}.nodes[{node_position}]", node, node_count, errors)

    @staticmethod
    def _validate_node_index(path: str, value: Any, node_count: int, errors: list[str]) -> None:
        if not _is_int(value):
            errors.append(f"{path} must be an integer node index.")
            return
        if node_count and not 0 <= int(value) < node_count:
            errors.append(f"{path} references node {value}, outside 0..{node_count - 1}.")

    @staticmethod
    def _validate_dof_name(path: str, value: Any, errors: list[str]) -> None:
        if isinstance(value, str):
            if value.upper() not in DOF_ORDER:
                errors.append(f"{path} has unknown dof name {value!r}.")
            return
        if _is_int(value):
            if not 0 <= int(value) < len(DOF_ORDER):
                errors.append(f"{path} has unknown dof index {value}.")
            return
        errors.append(f"{path} must be a dof name or integer index.")

    @staticmethod
    def _require_fields(path: str, value: Mapping[str, Any], required: tuple[str, ...], errors: list[str]) -> None:
        require_fields(path, value, required, errors)

    @staticmethod
    def _reject_unknown(
        path: str, value: Mapping[str, Any], allowed: set[str], errors: list[str], *, allow_extra: bool = False
    ) -> None:
        if allow_extra:
            return
        reject_unknown(path, value, allowed, errors)
