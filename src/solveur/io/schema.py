"""Strict validation for JSON model dictionaries."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from solveur.core.analysis import SUPPORTED_METHODS
from solveur.core.dofs import DOF_ORDER
from solveur.core.errors import InputValidationError
from solveur.elements.registry import ElementRegistry
from solveur.io.contact_schema import ContactSchemaValidator
from solveur.io.constraint_schema import ConstraintSchemaValidator
from solveur.io.discrete_schema import DiscreteEntitySchemaValidator
from solveur.io.laminate_schema import validate_laminate_plies
from solveur.io.load_schema import DistributedLoadSchemaValidator
from solveur.io.schema_values import (
    is_int as _is_int,
    is_number as _is_number,
    is_numeric_matrix as _is_numeric_matrix,
    is_numeric_vector as _is_numeric_vector,
    reject_unknown,
    require_fields,
)
class JsonSchemaValidator:
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
    def _validate_nodes(self, value: Any, errors: list[str]) -> int:
        if not isinstance(value, list):
            errors.append("nodes must be a list of [x, y, z] coordinates.")
            return 0
        if not value:
            errors.append("nodes must not be empty.")
        for index, node in enumerate(value):
            path = f"nodes[{index}]"
            if not isinstance(node, Sequence) or isinstance(node, (str, bytes)) or len(node) != 3:
                errors.append(f"{path} must be a list of exactly 3 numeric coordinates.")
                continue
            for coord_index, coord in enumerate(node):
                if not _is_number(coord):
                    errors.append(f"{path}[{coord_index}] must be a finite number.")
        return len(value)
    def _validate_materials(self, value: Any, errors: list[str]) -> set[str]:
        if not isinstance(value, Mapping):
            errors.append("materials must be an object keyed by material name.")
            return set()
        names: set[str] = set()
        for name, material in value.items():
            path = f"materials.{name}"
            if not isinstance(name, str) or not name:
                errors.append("materials keys must be non-empty strings.")
                continue
            names.add(name)
            if not isinstance(material, Mapping):
                errors.append(f"{path} must be an object.")
                continue
            material_type = str(material.get("type", "")).lower()
            allowed_fields = self._material_fields.get(material_type)
            if allowed_fields is None:
                errors.append(f"{path}.type has unsupported material type {material.get('type')!r}.")
                continue
            self._reject_unknown(path, material, allowed_fields, errors)
            if material_type == "beam_isotropic":
                required = ("type", "E", "A", "Iy", "Iz", "J")
            elif material_type == "shell_isotropic":
                required = ("type", "E", "nu", "t")
            elif material_type == "orthotropic_lamina":
                required = ("type", "E1", "E2", "nu12", "G12")
            elif material_type in {"orthotropic_3d", "composite_orthotropic_3d"}:
                required = ("type", "E1", "E2", "E3", "nu12", "nu13", "nu23", "G12", "G13", "G23")
            elif material_type == "shell_laminate":
                required = ("type", "plies")
            elif material_type == "von_mises_elastoplastic_3d":
                required = ("type", "E", "nu", "yield_stress")
            else:
                required = ("type", "E", "nu")
            self._require_fields(path, material, required, errors)
            structured_fields = {
                "type",
                "plies",
                "orientation",
                "e1",
                "e2_hint",
                "orientation_field",
                "reference_direction",
                "reference_vector",
                "provenance",
                "homogenization",
                "layup",
                "strengths",
            }
            numeric_fields = tuple(field for field in allowed_fields if field not in structured_fields)
            for field in numeric_fields:
                if field in material and not _is_number(material[field]):
                    errors.append(f"{path}.{field} must be a finite number.")
            if material_type == "shell_laminate":
                validate_laminate_plies(path, material.get("plies"), errors)
                if "shear_factor" in material and _is_number(material["shear_factor"]):
                    if float(material["shear_factor"]) <= 0.0:
                        errors.append(f"{path}.shear_factor must be positive.")
                if "drilling_scale" in material and _is_number(material["drilling_scale"]):
                    if float(material["drilling_scale"]) < 0.0:
                        errors.append(f"{path}.drilling_scale must be non-negative.")
                if "reference_direction" in material:
                    direction = material["reference_direction"]
                    if not _is_numeric_vector(direction, 3):
                        errors.append(f"{path}.reference_direction must contain exactly 3 finite numbers.")
                    elif sum(float(value) ** 2 for value in direction) <= 1.0e-28:
                        errors.append(f"{path}.reference_direction must have a non-zero norm.")
            if material_type == "orthotropic_lamina" and (("G13" in material) != ("G23" in material)):
                errors.append(f"{path}.G13 and G23 must be defined together.")
            if material_type == "beam_isotropic":
                self._validate_beam_material(path, material, errors)
            if material_type in {"orthotropic_3d", "composite_orthotropic_3d"}:
                self._validate_orthotropic_solid(path, material, errors)
        return names
    @staticmethod
    def _validate_beam_material(path: str, material: Mapping[str, Any], errors: list[str]) -> None:
        if "G" not in material and "nu" not in material:
            errors.append(f"{path} requires G or nu.")
        for field in ("E", "G", "A", "Iy", "Iz", "J", "kappa_y", "kappa_z"):
            if field in material and _is_number(material[field]) and float(material[field]) <= 0.0:
                errors.append(f"{path}.{field} must be positive.")
        if "nu" in material and _is_number(material["nu"]) and not -1.0 < float(material["nu"]) < 0.5:
            errors.append(f"{path}.nu must satisfy -1 < nu < 0.5.")
        for field in ("density", "rho"):
            if field in material and _is_number(material[field]) and float(material[field]) < 0.0:
                errors.append(f"{path}.{field} must be non-negative.")
        if "reference_vector" in material:
            direction = material["reference_vector"]
            if not _is_numeric_vector(direction, 3):
                errors.append(f"{path}.reference_vector must contain exactly 3 finite numbers.")
            elif sum(float(value) ** 2 for value in direction) <= 1.0e-28:
                errors.append(f"{path}.reference_vector must be non-zero.")
    def _validate_orthotropic_solid(self, path: str, material: Mapping[str, Any], errors: list[str]) -> None:
        for field in ("E1", "E2", "E3", "G12", "G13", "G23"):
            if field in material and _is_number(material[field]) and float(material[field]) <= 0.0:
                errors.append(f"{path}.{field} must be positive.")
        for field in ("density", "rho"):
            if field in material and _is_number(material[field]) and float(material[field]) < 0.0:
                errors.append(f"{path}.{field} must be non-negative.")
        has_matrix = "orientation" in material
        has_e1 = "e1" in material
        has_e2 = "e2_hint" in material
        has_field = "orientation_field" in material
        if sum((has_matrix, has_e1 or has_e2, has_field)) > 1:
            errors.append(f"{path} must define only one of orientation, e1/e2_hint or orientation_field.")
        if has_e1 != has_e2:
            errors.append(f"{path}.e1 and e2_hint must be defined together.")
        if has_matrix and not _is_numeric_matrix(material["orientation"], 3, 3):
            errors.append(f"{path}.orientation must be a finite 3x3 numeric matrix.")
        for field in ("e1", "e2_hint"):
            if field in material and not _is_numeric_vector(material[field], 3):
                errors.append(f"{path}.{field} must contain exactly 3 finite numbers.")
        if has_field:
            field = material["orientation_field"]
            if not isinstance(field, Mapping):
                errors.append(f"{path}.orientation_field must be an object.")
            else:
                if set(field) != {"type", "origin", "axis"}:
                    errors.append(f"{path}.orientation_field must define only type, origin and axis.")
                if str(field.get("type", "")).lower() != "cylindrical_tangent":
                    errors.append(f"{path}.orientation_field.type must be 'cylindrical_tangent'.")
                for name in ("origin", "axis"):
                    if not _is_numeric_vector(field.get(name), 3):
                        errors.append(f"{path}.orientation_field.{name} must contain exactly 3 finite numbers.")
                    elif name == "axis" and sum(float(value) ** 2 for value in field[name]) <= 1.0e-28:
                        errors.append(f"{path}.orientation_field.{name} must be non-zero.")
        if str(material.get("type", "")).lower() == "composite_orthotropic_3d":
            if not isinstance(material.get("homogenization"), str) or not material.get("homogenization"):
                errors.append(f"{path}.homogenization must be a non-empty string.")
            if not isinstance(material.get("provenance"), Mapping):
                errors.append(f"{path}.provenance must be an object.")
    def _validate_analysis(self, value: Any, errors: list[str]) -> None:
        if isinstance(value, str):
            analysis_type = value.lower()
            method = None
            params: dict[str, Any] = {}
        elif isinstance(value, Mapping):
            allowed = {"type", "method", "parameters"}
            self._reject_unknown("analysis", value, allowed, errors, allow_extra=True)
            raw_type = value.get("type", "linear_static")
            raw_method = value.get("method")
            if not isinstance(raw_type, str):
                errors.append("analysis.type must be a string.")
                return
            if raw_method is not None and not isinstance(raw_method, str):
                errors.append("analysis.method must be a string.")
                return
            if "parameters" in value and not isinstance(value["parameters"], Mapping):
                errors.append("analysis.parameters must be an object when provided.")
            analysis_type = raw_type.lower()
            method = raw_method.lower() if raw_method is not None else None
            params = dict(value.get("parameters", {})) if isinstance(value.get("parameters", {}), Mapping) else {}
            params.update({str(key): item for key, item in value.items() if key not in allowed})
        else:
            errors.append("analysis must be a string or an object.")
            return
        if analysis_type not in SUPPORTED_METHODS:
            errors.append(f"analysis.type {analysis_type!r} is unsupported.")
            return
        if method is not None and method not in SUPPORTED_METHODS[analysis_type]:
            allowed = ", ".join(SUPPORTED_METHODS[analysis_type])
            errors.append(f"analysis.method {method!r} is unsupported for {analysis_type}; allowed: {allowed}.")
        self._validate_analysis_parameters(analysis_type, params, errors)
    def _validate_analysis_parameters(self, analysis_type: str, params: Mapping[str, Any], errors: list[str]) -> None:
        if "assembly_chunk_size" in params:
            self._positive_int("analysis.assembly_chunk_size", params["assembly_chunk_size"], errors)
        if analysis_type in {"nonlinear_static", "geometric_nonlinear_static", "linear_buckling"}:
            if "nonlinear_assembly_chunk_size" in params:
                self._positive_int(
                    "analysis.nonlinear_assembly_chunk_size",
                    params["nonlinear_assembly_chunk_size"],
                    errors,
                )
        if analysis_type == "transient_dynamic":
            self._require_any("analysis", params, ("time_step", "dt"), errors)
            self._require_any("analysis", params, ("steps", "time_steps"), errors)
            self._positive_number("analysis.time_step", params.get("time_step", params.get("dt")), errors)
            self._positive_int("analysis.steps", params.get("steps", params.get("time_steps")), errors)
            for key in ("newmark_beta", "newmark_gamma"):
                if key in params:
                    self._positive_number(f"analysis.{key}", params[key], errors)
            beta = params.get("newmark_beta", 0.25)
            gamma = params.get("newmark_gamma", 0.5)
            if _is_number(beta) and _is_number(gamma):
                minimum_beta = 0.25 * (float(gamma) + 0.5) ** 2
                if float(gamma) < 0.5 or float(beta) < minimum_beta:
                    errors.append(
                        "analysis Newmark parameters are not unconditionally stable; require "
                        "gamma >= 0.5 and beta >= 0.25 * (gamma + 0.5)^2."
                    )
            self._validate_rayleigh(params, errors)
            self._validate_modal_damping_targets(params, errors)
            if "load_table" in params:
                self._validate_load_table(params["load_table"], errors)
            if "load_factors_by_load" in params:
                self._validate_load_factors_by_load(params["load_factors_by_load"], errors)
            self._validate_dynamic_load_function(params, errors)
            for key in ("checkpoint_path", "restart_from"):
                if key in params and (not isinstance(params[key], str) or not str(params[key]).strip()):
                    errors.append(f"analysis.{key} must be a non-empty path string.")
                elif key in params and not str(params[key]).lower().endswith(".npz"):
                    errors.append(f"analysis.{key} must use the .npz format.")
            if "checkpoint_interval" in params:
                self._positive_int("analysis.checkpoint_interval", params["checkpoint_interval"], errors)
                if "checkpoint_path" not in params:
                    errors.append("analysis.checkpoint_interval requires analysis.checkpoint_path.")
            if "checkpoint_keep_steps" in params and not isinstance(params["checkpoint_keep_steps"], bool):
                errors.append("analysis.checkpoint_keep_steps must be a boolean.")
            if params.get("checkpoint_keep_steps") and "checkpoint_path" not in params:
                errors.append("analysis.checkpoint_keep_steps requires analysis.checkpoint_path.")
        if analysis_type == "harmonic_response":
            if "frequencies_hz" not in params:
                errors.append("analysis.frequencies_hz is required for harmonic_response.")
            elif not isinstance(params["frequencies_hz"], list) or not params["frequencies_hz"]:
                errors.append("analysis.frequencies_hz must be a non-empty list.")
            else:
                for index, frequency in enumerate(params["frequencies_hz"]):
                    if not _is_number(frequency) or float(frequency) < 0.0:
                        errors.append(f"analysis.frequencies_hz[{index}] must be a non-negative finite number.")
            self._validate_rayleigh(params, errors)
            self._validate_modal_damping_targets(params, errors)
        if analysis_type == "modal":
            if "modes" in params:
                self._positive_int("analysis.modes", params["modes"], errors)
            if "dense_modal_max_dofs" in params:
                self._positive_int("analysis.dense_modal_max_dofs", params["dense_modal_max_dofs"], errors)
            if "modal_shift_hz" in params and "modal_shift_eigenvalue" in params:
                errors.append("analysis must define only one of modal_shift_hz and modal_shift_eigenvalue.")
            for key in ("modal_shift_hz", "modal_shift_eigenvalue", "arpack_tolerance"):
                if key in params:
                    self._nonnegative_number(f"analysis.{key}", params[key], errors)
            for key in ("arpack_maxiter", "arpack_ncv"):
                if key in params:
                    self._positive_int(f"analysis.{key}", params[key], errors)
            if "arpack_which" in params:
                value = params["arpack_which"]
                if not isinstance(value, str) or value.upper() not in {"LM", "SM", "LA", "SA", "BE"}:
                    errors.append("analysis.arpack_which must be one of LM, SM, LA, SA or BE.")
            if _is_int(params.get("modes")) and _is_int(params.get("arpack_ncv")):
                if int(params["arpack_ncv"]) <= int(params["modes"]):
                    errors.append("analysis.arpack_ncv must be greater than analysis.modes.")
        if analysis_type == "nonlinear_static":
            if "load_steps" in params:
                self._positive_int("analysis.load_steps", params["load_steps"], errors)
            if "max_arc_steps" in params:
                self._positive_int("analysis.max_arc_steps", params["max_arc_steps"], errors)
            if "adaptive_arc_length" in params and not isinstance(params["adaptive_arc_length"], bool):
                errors.append("analysis.adaptive_arc_length must be a boolean.")
            if "arc_length_allow_load_factor_turning" in params and not isinstance(
                params["arc_length_allow_load_factor_turning"], bool
            ):
                errors.append("analysis.arc_length_allow_load_factor_turning must be a boolean.")
            if "arc_length_stop_mode" in params:
                stop_mode = params["arc_length_stop_mode"]
                if not isinstance(stop_mode, str) or stop_mode.lower() not in {"target_load", "max_steps"}:
                    errors.append("analysis.arc_length_stop_mode must be target_load or max_steps.")
            for key in (
                "min_arc_length_radius",
                "max_arc_length_radius",
                "arc_length_growth_factor",
                "arc_length_shrink_factor",
                "arc_length_load_factor_limit",
            ):
                if key in params:
                    self._positive_number(f"analysis.{key}", params[key], errors)
            if "arc_length_growth_factor" in params and _is_number(params["arc_length_growth_factor"]):
                if float(params["arc_length_growth_factor"]) < 1.0:
                    errors.append("analysis.arc_length_growth_factor must be greater than or equal to 1.")
            if "arc_length_shrink_factor" in params and _is_number(params["arc_length_shrink_factor"]):
                if not 0.0 < float(params["arc_length_shrink_factor"]) < 1.0:
                    errors.append("analysis.arc_length_shrink_factor must be strictly between 0 and 1.")
            if (
                _is_number(params.get("min_arc_length_radius"))
                and _is_number(params.get("max_arc_length_radius"))
                and float(params["max_arc_length_radius"]) < float(params["min_arc_length_radius"])
            ):
                errors.append("analysis.max_arc_length_radius must be at least min_arc_length_radius.")
            if "arc_length_grow_below_iterations" in params:
                self._nonnegative_int(
                    "analysis.arc_length_grow_below_iterations",
                    params["arc_length_grow_below_iterations"],
                    errors,
                )
            if "arc_length_shrink_above_iterations" in params:
                self._positive_int(
                    "analysis.arc_length_shrink_above_iterations",
                    params["arc_length_shrink_above_iterations"],
                    errors,
                )
            if (
                _is_int(params.get("arc_length_grow_below_iterations"))
                and _is_int(params.get("arc_length_shrink_above_iterations"))
                and int(params["arc_length_grow_below_iterations"])
                >= int(params["arc_length_shrink_above_iterations"])
            ):
                errors.append(
                    "analysis arc-length iteration thresholds must grow_below < shrink_above."
                )
            if "load_path" in params:
                path = params["load_path"]
                if not isinstance(path, list) or not path:
                    errors.append("analysis.load_path must be a non-empty list.")
                else:
                    for index, factor in enumerate(path):
                        if not _is_number(factor):
                            errors.append(f"analysis.load_path[{index}] must be a finite scalar.")
                if params.get("adaptive_load_steps"):
                    errors.append("analysis.load_path is not yet compatible with adaptive_load_steps.")
                if str(params.get("method", "")).lower() == "arc_length":
                    errors.append("analysis.load_path is not compatible with arc_length.")
            for key in ("checkpoint_path", "restart_from"):
                if key in params and (not isinstance(params[key], str) or not str(params[key]).strip()):
                    errors.append(f"analysis.{key} must be a non-empty path string.")
                elif key in params and not str(params[key]).lower().endswith(".npz"):
                    errors.append(f"analysis.{key} must use the .npz format.")
            if "checkpoint_interval" in params:
                self._positive_int("analysis.checkpoint_interval", params["checkpoint_interval"], errors)
                if "checkpoint_path" not in params:
                    errors.append("analysis.checkpoint_interval requires analysis.checkpoint_path.")
            if "checkpoint_keep_steps" in params and not isinstance(params["checkpoint_keep_steps"], bool):
                errors.append("analysis.checkpoint_keep_steps must be a boolean.")
            if params.get("checkpoint_keep_steps") and "checkpoint_path" not in params:
                errors.append("analysis.checkpoint_keep_steps requires analysis.checkpoint_path.")
            if params.get("adaptive_load_steps") and any(key in params for key in ("checkpoint_path", "restart_from")):
                errors.append("analysis nonlinear checkpoint/restart requires fixed load-control steps.")
        if analysis_type == "geometric_nonlinear_static":
            if "load_increments" in params:
                self._positive_int("analysis.load_increments", params["load_increments"], errors)
                if _is_int(params["load_increments"]) and int(params["load_increments"]) < 6:
                    errors.append("analysis.load_increments must be at least 6.")
            if "max_iterations" in params:
                self._positive_int("analysis.max_iterations", params["max_iterations"], errors)
            if "tolerance" in params:
                self._positive_number("analysis.tolerance", params["tolerance"], errors)
        if analysis_type == "linear_buckling":
            for key in (
                "preload_factor",
                "initial_factor",
                "maximum_factor",
                "factor_tolerance",
                "eigensolver_tolerance",
            ):
                if key in params:
                    self._positive_number(f"analysis.{key}", params[key], errors)
            for key in ("load_increments", "max_iterations", "bracket_iterations", "eigensolver_maxiter"):
                if key in params:
                    self._positive_int(f"analysis.{key}", params[key], errors)

    def _validate_dynamic_load_function(self, params: Mapping[str, Any], errors: list[str]) -> None:
        if any(key in params for key in ("load_table", "load_factors", "load_factors_by_load")):
            return
        kind = params.get("load_function", "constant")
        allowed = {"constant", "linear_ramp", "sine", "half_sine_pulse", "linear_chirp"}
        if not isinstance(kind, str) or kind.lower() not in allowed:
            errors.append(
                "analysis.load_function must be one of constant, linear_ramp, sine, half_sine_pulse or linear_chirp."
            )
            return
        required = {
            "sine": (("load_frequency_hz", False),),
            "half_sine_pulse": (("pulse_duration", True),),
            "linear_chirp": (
                ("chirp_start_hz", False),
                ("chirp_end_hz", True),
                ("chirp_duration", True),
            ),
        }.get(kind.lower(), ())
        for key, strictly_positive in required:
            if key not in params:
                errors.append(f"analysis.{key} is required for load_function {kind!r}.")
            elif strictly_positive:
                self._positive_number(f"analysis.{key}", params[key], errors)
            else:
                self._nonnegative_number(f"analysis.{key}", params[key], errors)

    def _validate_elements(self, value: Any, materials: set[str], node_count: int, errors: list[str]) -> None:
        if not isinstance(value, list):
            errors.append("elements must be a list.")
            return
        for index, element in enumerate(value):
            path = f"elements[{index}]"
            if not isinstance(element, Mapping):
                errors.append(f"{path} must be an object.")
                continue
            self._reject_unknown(path, element, {"type", "nodes", "material"}, errors)
            self._require_fields(path, element, ("type", "nodes", "material"), errors)
            element_type = self._element_type(path, element.get("type"), errors)
            spec = None
            if element_type:
                try:
                    spec = ElementRegistry.get(element_type)
                except ValueError:
                    errors.append(f"{path}.type {element_type!r} is unsupported.")
            self._validate_element_nodes(
                path, element.get("nodes"), node_count, spec.node_count if spec else None, errors
            )
            material = element.get("material")
            if not isinstance(material, str) or not material:
                errors.append(f"{path}.material must be a non-empty string.")
            elif material not in materials:
                errors.append(f"{path}.material references unknown material {material!r}.")

    def _validate_fixed_dofs(self, value: Any, node_count: int, errors: list[str]) -> None:
        if not isinstance(value, list):
            errors.append("fixed_dofs must be a list when provided.")
            return
        for index, item in enumerate(value):
            path = f"fixed_dofs[{index}]"
            if not isinstance(item, Mapping):
                errors.append(f"{path} must be an object.")
                continue
            self._reject_unknown(path, item, {"node", "dofs"}, errors)
            self._require_fields(path, item, ("node", "dofs"), errors)
            self._validate_node_index(f"{path}.node", item.get("node"), node_count, errors)
            dofs = item.get("dofs")
            if not isinstance(dofs, list) or not dofs:
                errors.append(f"{path}.dofs must be a non-empty list.")
                continue
            for dof_index, dof in enumerate(dofs):
                self._validate_dof_name(f"{path}.dofs[{dof_index}]", dof, errors)

    def _validate_loads(self, value: Any, node_count: int, errors: list[str]) -> None:
        if not isinstance(value, list):
            errors.append("loads must be a list when provided.")
            return
        for index, item in enumerate(value):
            path = f"loads[{index}]"
            if not isinstance(item, Mapping):
                errors.append(f"{path} must be an object.")
                continue
            self._reject_unknown(path, item, {"node", "dof", "value"}, errors)
            self._require_fields(path, item, ("node", "dof", "value"), errors)
            self._validate_node_index(f"{path}.node", item.get("node"), node_count, errors)
            self._validate_dof_name(f"{path}.dof", item.get("dof"), errors)
            if "value" in item and not _is_number(item["value"]):
                errors.append(f"{path}.value must be a finite number.")

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
