"""Focused contract coverage for the strict model schema validator."""

from __future__ import annotations

import pytest

from solveur.core.errors import InputValidationError
from solveur.io.schema import JsonSchemaValidator


def _valid_model() -> dict:
    return {
        "schema_version": 1,
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        "materials": {"solid": {"type": "isotropic_3d", "E": 10.0, "nu": 0.3}},
    }


def test_validate_rejects_root_and_required_sections_with_all_diagnostics() -> None:
    validator = JsonSchemaValidator()

    with pytest.raises(InputValidationError, match="JSON root must be an object"):
        validator.validate(None)

    with pytest.raises(InputValidationError) as exc_info:
        validator.validate({"unknown": True, "nodes": [], "elements": [], "materials": {}})
    message = str(exc_info.value)
    assert "unknown field" in message
    assert "nodes must not be empty" in message
    assert "at least one finite element or spring" in message

    with pytest.raises(InputValidationError) as exc_info:
        validator.validate({"nodes": "bad", "elements": "bad", "materials": "bad"})
    assert "nodes must be a list" in str(exc_info.value)
    assert "elements must be a list" in str(exc_info.value)
    assert "materials must be an object" in str(exc_info.value)


def test_material_validator_covers_scalar_and_structured_edge_cases() -> None:
    validator = JsonSchemaValidator()

    errors: list[str] = []
    validator._validate_materials(
        {
            "beam": {
                "type": "beam_isotropic",
                "E": 0.0,
                "A": -1.0,
                "Iy": 1.0,
                "Iz": 1.0,
                "J": 1.0,
                "density": -1.0,
                "reference_vector": [0.0, 0.0, 0.0],
            },
            "lamina": {"type": "orthotropic_lamina", "E1": 1.0, "E2": 1.0, "nu12": 0.2, "G12": 1.0, "G13": 1.0},
            "composite": {
                "type": "composite_orthotropic_3d",
                "E1": 1.0,
                "E2": 1.0,
                "E3": 1.0,
                "nu12": 0.2,
                "nu13": 0.2,
                "nu23": 0.2,
                "G12": 1.0,
                "G13": 1.0,
                "G23": 1.0,
                "homogenization": "",
                "provenance": "missing-object",
            },
            "unknown": {"type": "not_a_material"},
        },
        errors,
    )
    assert any("requires G or nu" in error for error in errors)
    assert any("reference_vector must be non-zero" in error for error in errors)
    assert any("G13 and G23 must be defined together" in error for error in errors)
    assert any("homogenization must be a non-empty string" in error for error in errors)
    assert any("provenance must be an object" in error for error in errors)
    assert any("unsupported material type" in error for error in errors)


def test_nodes_and_material_shape_errors_are_explicit() -> None:
    validator = JsonSchemaValidator()
    errors: list[str] = []
    validator._validate_nodes("bad", errors)
    validator._validate_nodes([], errors)
    validator._validate_nodes([[0.0, 1.0], [0.0, 1.0, "bad"], [0.0, 1.0, float("inf")]], errors)
    validator._validate_materials(
        {
            1: "bad-key",
            "not_object": "bad-material",
            "bad_scalar": {"type": "isotropic_3d", "E": "bad", "nu": 0.3},
            "plastic": {"type": "von_mises_elastoplastic_3d", "E": 1.0, "nu": 0.3},
        },
        errors,
    )
    assert any("nodes must be a list" in error for error in errors)
    assert any("nodes must not be empty" in error for error in errors)
    assert any("exactly 3 numeric coordinates" in error for error in errors)
    assert any("finite number" in error for error in errors)
    assert any("keys must be non-empty strings" in error for error in errors)
    assert any("must be an object" in error for error in errors)
    assert any("must be a finite number" in error for error in errors)
    assert any("yield_stress is required" in error for error in errors)


def test_laminate_and_checkpoint_control_errors_cover_strict_paths() -> None:
    validator = JsonSchemaValidator()
    errors: list[str] = []
    validator._validate_materials(
        {
            "laminate": {
                "type": "shell_laminate",
                "plies": [],
                "shear_factor": 0.0,
                "drilling_scale": -1.0,
                "reference_direction": [0.0, 0.0, 0.0],
            }
        },
        errors,
    )
    validator._validate_analysis(
        {
            "type": "transient_dynamic",
            "parameters": {
                "assembly_chunk_size": 0,
                "checkpoint_path": "",
                "restart_from": "restart.txt",
                "checkpoint_interval": 2,
                "checkpoint_keep_steps": True,
            },
        },
        errors,
    )
    validator._validate_analysis(
        {
            "type": "nonlinear_static",
            "method": "arc_length",
            "parameters": {
                "load_steps": 0,
                "load_path": [1.0, "bad"],
                "adaptive_load_steps": True,
                "checkpoint_path": "",
                "checkpoint_interval": 1,
                "checkpoint_keep_steps": True,
            },
        },
        errors,
    )
    validator._validate_analysis(
        {"type": "transient_dynamic", "parameters": {"dt": 1.0, "steps": 1, "checkpoint_interval": 2}},
        errors,
    )
    assert any("plies" in error for error in errors)
    assert any("shear_factor must be positive" in error for error in errors)
    assert any("drilling_scale must be non-negative" in error for error in errors)
    assert any("reference_direction" in error for error in errors)
    assert any("assembly_chunk_size" in error for error in errors)
    assert any("checkpoint_path must be a non-empty" in error for error in errors)
    assert any("checkpoint_interval requires" in error for error in errors)
    assert any("load_path[1]" in error for error in errors)
    assert any("checkpoint/restart requires fixed" in error for error in errors)


def test_analysis_validator_covers_type_method_and_control_failures() -> None:
    validator = JsonSchemaValidator()
    errors: list[str] = []
    validator._validate_analysis(3, errors)
    validator._validate_analysis({"type": 3}, errors)
    validator._validate_analysis({"type": "linear_static", "method": 3}, errors)
    validator._validate_analysis({"type": "not_supported"}, errors)
    validator._validate_analysis({"type": "harmonic_response", "parameters": {"frequencies_hz": []}}, errors)
    validator._validate_analysis(
        {
            "type": "modal",
            "parameters": {
                "modes": 0,
                "dense_modal_max_dofs": 0,
                "modal_shift_hz": -1.0,
                "arpack_tolerance": -1.0,
                "arpack_maxiter": 0,
                "arpack_ncv": 1,
            },
        },
        errors,
    )
    validator._validate_analysis(
        {
            "type": "nonlinear_static",
            "parameters": {
                "checkpoint_path": "state.txt",
                "checkpoint_interval": 0,
                "checkpoint_keep_steps": True,
                "adaptive_load_steps": True,
            },
        },
        errors,
    )
    validator._validate_analysis(
        {"type": "geometric_nonlinear_static", "parameters": {"load_increments": 6, "max_iterations": 0, "tolerance": 0.0}},
        errors,
    )
    assert any("analysis must be a string or an object" in error for error in errors)
    assert any("analysis.type must be a string" in error for error in errors)
    assert any("analysis.method must be a string" in error for error in errors)
    assert any("is unsupported" in error for error in errors)
    assert any("frequencies_hz must be a non-empty list" in error for error in errors)
    assert any("modes must be a positive integer" in error for error in errors)
    assert any("checkpoint_path must use the .npz format" in error for error in errors)
    assert any("max_iterations" in error for error in errors)
    assert any("tolerance" in error for error in errors)
