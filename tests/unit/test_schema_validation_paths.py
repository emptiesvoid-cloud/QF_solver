from __future__ import annotations

import numpy as np

from solveur.io.schema import JsonSchemaValidator


def _errors() -> list[str]:
    return []


def test_transient_validation_covers_checkpoint_damping_and_tables() -> None:
    validator = JsonSchemaValidator()
    errors = _errors()
    validator._validate_analysis(
        {
            "type": "transient_dynamic",
            "method": "newmark",
            "parameters": {
                "dt": 0.01,
                "steps": 4,
                "newmark_beta": 0.25,
                "newmark_gamma": 0.5,
                "rayleigh_alpha": 0.01,
                "rayleigh_beta": 0.002,
                "load_table": [{"time": 0.0, "factor": 0.0}, {"time": 1.0, "factor": 1.0}],
                "load_factors_by_load": {"0": [0.0, 1.0]},
                "checkpoint_path": "state.npz",
                "checkpoint_interval": 2,
                "checkpoint_keep_steps": True,
            },
        },
        errors,
    )
    assert errors == []


def test_transient_validation_reports_unstable_and_malformed_controls() -> None:
    validator = JsonSchemaValidator()
    errors = _errors()
    validator._validate_analysis(
        {
            "type": "transient_dynamic",
            "parameters": {
                "dt": -1.0,
                "steps": 0,
                "newmark_beta": 0.01,
                "newmark_gamma": 0.1,
                "rayleigh_alpha": -1.0,
                "modal_damping_targets": [{"frequency_hz": 0.0, "damping_ratio": -1.0}],
                "load_table": [{"time": 1.0, "factor": "bad"}, {"time": 0.0, "factor": 1.0}],
                "load_factors_by_load": {"bad": [], "1": ["bad"]},
                "checkpoint_path": "state.txt",
                "checkpoint_interval": 0,
                "checkpoint_keep_steps": "yes",
            },
        },
        errors,
    )
    assert any("unconditionally stable" in error for error in errors)
    assert any("modal_damping_targets must contain exactly two" in error for error in errors)
    assert any("checkpoint_path must use the .npz format" in error for error in errors)
    assert any("load_table times must be strictly increasing" in error for error in errors)
    assert any("load_factors_by_load" in error for error in errors)


def test_dynamic_load_function_variants_and_required_parameters() -> None:
    validator = JsonSchemaValidator()
    for params in ({"load_function": "constant"}, {"load_function": "linear_ramp"}, {"load_function": "sine", "load_frequency_hz": 2.0}, {"load_function": "half_sine_pulse", "pulse_duration": 0.5}, {"load_function": "linear_chirp", "chirp_start_hz": 0.0, "chirp_end_hz": 3.0, "chirp_duration": 1.0}):
        errors = _errors()
        validator._validate_dynamic_load_function(params, errors)
        assert errors == []

    errors = _errors()
    validator._validate_dynamic_load_function({"load_function": "unknown"}, errors)
    validator._validate_dynamic_load_function({"load_function": "sine"}, errors)
    validator._validate_dynamic_load_function({"load_function": "half_sine_pulse", "pulse_duration": 0.0}, errors)
    validator._validate_dynamic_load_function(
        {"load_function": "linear_chirp", "chirp_start_hz": -1.0, "chirp_end_hz": 0.0, "chirp_duration": 0.0},
        errors,
    )
    assert len(errors) >= 5


def test_harmonic_modal_and_nonlinear_parameter_paths() -> None:
    validator = JsonSchemaValidator()
    harmonic_errors = _errors()
    validator._validate_analysis(
        {"type": "harmonic_response", "parameters": {"frequencies_hz": [0.0, 10.0], "rayleigh_alpha": 0.0}},
        harmonic_errors,
    )
    assert harmonic_errors == []

    modal_errors = _errors()
    validator._validate_analysis(
        {
            "type": "modal",
            "parameters": {"modes": 2, "dense_modal_max_dofs": 10, "modal_shift_hz": 1.0, "arpack_which": "SM", "arpack_maxiter": 10, "arpack_ncv": 4},
        },
        modal_errors,
    )
    assert modal_errors == []

    invalid_modal = _errors()
    validator._validate_analysis(
        {"type": "modal", "parameters": {"modes": 2, "modal_shift_hz": 1.0, "modal_shift_eigenvalue": 2.0, "arpack_which": "XX", "arpack_ncv": 1}},
        invalid_modal,
    )
    assert any("modal_shift" in error for error in invalid_modal)
    assert any("arpack_which" in error for error in invalid_modal)
    assert any("arpack_ncv" in error for error in invalid_modal)

    nonlinear_errors = _errors()
    validator._validate_analysis(
        {
            "type": "nonlinear_static",
            "method": "arc_length",
            "parameters": {
                "load_steps": 2,
                "load_path": [0.0, 1.0],
                "adaptive_load_steps": True,
                "nonlinear_assembly_chunk_size": 64,
            },
        },
        nonlinear_errors,
    )
    assert any("load_path" in error for error in nonlinear_errors)

    invalid_arc_length_errors = _errors()
    validator._validate_analysis(
        {
            "type": "nonlinear_static",
            "method": "arc_length",
            "parameters": {
                "arc_length_stop_mode": "unknown",
                "arc_length_allow_load_factor_turning": "yes",
                "arc_length_growth_factor": 0.5,
                "arc_length_shrink_factor": 1.0,
                "min_arc_length_radius": 0.2,
                "max_arc_length_radius": 0.1,
                "arc_length_load_factor_limit": 2.0,
            },
        },
        invalid_arc_length_errors,
    )
    assert any("arc_length_stop_mode" in error for error in invalid_arc_length_errors)
    assert any("arc_length_allow_load_factor_turning" in error for error in invalid_arc_length_errors)
    assert any("arc_length_growth_factor" in error for error in invalid_arc_length_errors)
    assert any("arc_length_shrink_factor" in error for error in invalid_arc_length_errors)
    assert any("max_arc_length_radius" in error for error in invalid_arc_length_errors)
    geometric_errors = _errors()
    validator._validate_analysis(
        {"type": "geometric_nonlinear_static", "parameters": {"load_increments": 2, "max_iterations": 0, "tolerance": 0.0}},
        geometric_errors,
    )
    assert len(geometric_errors) == 3

    invalid_chunk_errors = _errors()
    validator._validate_analysis(
        {"type": "nonlinear_static", "parameters": {"nonlinear_assembly_chunk_size": 0}},
        invalid_chunk_errors,
    )
    assert any("nonlinear_assembly_chunk_size" in error for error in invalid_chunk_errors)

    buckling_errors = _errors()
    validator._validate_analysis(
        {
            "type": "linear_buckling",
            "parameters": {
                "preload_factor": 0.0,
                "maximum_factor": -1.0,
                "load_increments": 0,
                "eigensolver_maxiter": 0,
                "nonlinear_assembly_chunk_size": 0,
            },
        },
        buckling_errors,
    )
    assert any("preload_factor" in error for error in buckling_errors)
    assert any("maximum_factor" in error for error in buckling_errors)
    assert any("load_increments" in error for error in buckling_errors)
    assert any("eigensolver_maxiter" in error for error in buckling_errors)
    assert any("nonlinear_assembly_chunk_size" in error for error in buckling_errors)


def test_orthotropic_material_orientation_variants_and_composite_metadata() -> None:
    validator = JsonSchemaValidator()
    common = {
        "type": "orthotropic_3d",
        "E1": 10.0,
        "E2": 8.0,
        "E3": 7.0,
        "nu12": 0.2,
        "nu13": 0.2,
        "nu23": 0.2,
        "G12": 3.0,
        "G13": 3.0,
        "G23": 3.0,
    }
    for orientation in (
        {"orientation": np.eye(3).tolist()},
        {"e1": [1.0, 0.0, 0.0], "e2_hint": [0.0, 1.0, 0.0]},
        {"orientation_field": {"type": "cylindrical_tangent", "origin": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, 1.0]}},
    ):
        errors = _errors()
        validator._validate_materials({"mat": {**common, **orientation}}, errors)
        assert errors == []

    composite = {**common, "type": "composite_orthotropic_3d", "homogenization": "rule_of_mixtures", "provenance": {"source": "unit"}}
    errors = _errors()
    validator._validate_materials({"composite": composite}, errors)
    assert errors == []

    errors = _errors()
    validator._validate_materials(
        {
            "bad": {
                **common,
                "E1": 0.0,
                "density": -1.0,
                "orientation": [[1.0]],
                "e1": [1.0, 0.0, 0.0],
                "orientation_field": "bad",
            }
        },
        errors,
    )
    assert any("must define only one" in error for error in errors)
    assert any("must be positive" in error for error in errors)
    assert any("orientation" in error for error in errors)


def test_element_boundary_load_and_units_validation_paths() -> None:
    validator = JsonSchemaValidator()
    errors = _errors()
    validator._validate_elements(
        [
            {"type": "TET4", "nodes": [0, 1, 2], "material": "missing", "extra": 1},
            {"type": "UNKNOWN", "nodes": "bad", "material": 3},
            "bad",
        ],
        {"steel"},
        4,
        errors,
    )
    validator._validate_fixed_dofs(["bad", {"node": 99, "dofs": []}], 4, errors)
    validator._validate_loads(["bad", {"node": 99, "dof": "BAD", "value": "bad"}], 4, errors)
    assert any("unsupported" in error for error in errors)
    assert any("outside" in error for error in errors)
    assert any("dof" in error.lower() for error in errors)

    validator._validate_units({"system": "SI", "length": "m", "unknown": "x"}, errors)
    validator._validate_units("SI", errors)
    validator._validate_schema_version("1", errors)
    validator._validate_schema_version(2, errors)
    validator._validate_verification_profile("unknown", errors)
    validator._validate_verification_profile(3, errors)
    validator._validate_qualification_units({"system": "cgs", "length": "cm"}, "qualification", errors)
    assert any("unsupported" in error for error in errors)
