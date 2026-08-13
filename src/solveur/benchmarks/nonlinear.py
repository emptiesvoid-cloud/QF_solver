"""Meshed experimental J2 material benchmark."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.benchmarks.support import BenchmarkContext, free_residual, run_status, upper_check
from solveur.benchmarks.types import BenchmarkRun
from solveur.core.router import AnalysisRouter


def run_j2_bar(context: BenchmarkContext) -> BenchmarkRun:
    """Load a multi-element bar beyond yield and compare the uniaxial path."""
    mesh = BenchmarkMeshFactory().box_tetra(
        context.root / "j2_bar_tet4.msh",
        length=1.0,
        width=0.2,
        height=0.2,
        mesh_size=0.18,
        anchors=True,
    )
    young, yield_stress, hardening, applied = 210.0e9, 250.0e6, 1.0e9, 300.0e6
    setup: dict[str, Any] = {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "units": {"system": "SI"},
        "verification_profile": context.profile,
        "analysis": {
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "load_steps": 6,
            "max_iterations": 30,
            "tolerance": 1.0e-9,
        },
        "materials": {
            "j2": {
                "type": "von_mises_elastoplastic_3d",
                "E": young,
                "nu": 0.3,
                "yield_stress": yield_stress,
                "hardening_modulus": hardening,
                "density": 7800.0,
            }
        },
        "groups": [
            {
                "name": "domain",
                "dimension": 3,
                "actions": [{"type": "elements", "element_type": "TET4", "material": "j2"}],
            },
            {
                "name": "x_min",
                "dimension": 2,
                "actions": [{"type": "fixed_dofs", "dofs": ["UX"]}],
            },
            {
                "name": "anchor_origin",
                "dimension": 0,
                "actions": [{"type": "fixed_dofs", "dofs": ["UY", "UZ"]}],
            },
            {
                "name": "anchor_xy",
                "dimension": 0,
                "actions": [{"type": "fixed_dofs", "dofs": ["UZ"]}],
            },
            {
                "name": "x_max",
                "dimension": 2,
                "actions": [{"type": "surface_traction", "value": [applied, 0.0, 0.0]}],
            },
        ],
    }
    model, result, files = context.import_and_solve(mesh, setup)
    data = result.to_dict()
    stresses = np.asarray([row["stress"] for row in data["element_results"]], dtype=float)
    mean_sigma = float(np.mean(stresses[:, 0]))
    stress_error = abs((mean_sigma - applied) / applied)
    plastic_values = _collect_scalars(data.get("material_states", {}), "equivalent_plastic_strain")
    expected_plastic = (applied - yield_stress) / hardening
    mean_plastic = float(np.mean(plastic_values)) if plastic_values else 0.0
    plastic_error = abs(mean_plastic - expected_plastic) / expected_plastic
    step_sensitivity = _load_step_sensitivity(model, result, mean_plastic)
    steps = data["solver"]["steps"]
    residual = free_residual(result)
    criteria = context.descriptor.criteria
    checks = [
        upper_check("uniaxial-stress", stress_error, criteria["relative_stress_error_max"]),
        upper_check("uniaxial-plastic-strain", plastic_error, criteria["relative_plastic_strain_error_max"]),
        upper_check("load-step-sensitivity", step_sensitivity, criteria["load_step_sensitivity_max"]),
        upper_check("free-residual", residual, criteria["free_residual_max"]),
        upper_check("step-residual", max(float(step["relative_residual"]) for step in steps), 1.0e-7),
    ]
    return context.finalize(
        BenchmarkRun(
            context.descriptor,
            run_status(checks, expected_warning=True),
            {
                "applied_axial_stress": applied,
                "mean_axial_stress": mean_sigma,
                "relative_stress_error": stress_error,
                "expected_uniaxial_equivalent_plastic_strain": expected_plastic,
                "mean_equivalent_plastic_strain": mean_plastic,
                "relative_plastic_strain_error": plastic_error,
                "load_step_sensitivity": step_sensitivity,
                "load_step_counts": [3, 6, 12],
                "converged_steps": len(steps),
                "max_step_iterations": max(int(step["iterations"]) for step in steps),
                "free_relative_residual": residual,
            },
            checks,
            files,
            "Experimental small-displacement J2 benchmark; not qualification-eligible.",
        )
    )


def _collect_scalars(value: object, key: str) -> list[float]:
    found: list[float] = []
    if isinstance(value, dict):
        for name, item in value.items():
            if name == key and isinstance(item, (int, float)):
                found.append(float(item))
            else:
                found.extend(_collect_scalars(item, key))
    elif isinstance(value, list):
        for item in value:
            found.extend(_collect_scalars(item, key))
    return found


def _load_step_sensitivity(model: object, baseline_result: object, baseline_value: float) -> float:
    values = {6: baseline_value}
    original_analysis = model.analysis
    try:
        for load_steps in (3, 12):
            parameters = dict(original_analysis.parameters)
            parameters["load_steps"] = load_steps
            model.analysis = replace(original_analysis, parameters=parameters)
            result = AnalysisRouter().solve(model)
            plastic = _collect_scalars(result.to_dict().get("material_states", {}), "equivalent_plastic_strain")
            values[load_steps] = float(np.mean(plastic))
    finally:
        model.analysis = original_analysis
    scale = max(abs(baseline_value), np.finfo(float).tiny)
    return max(abs(value - baseline_value) / scale for value in values.values())
