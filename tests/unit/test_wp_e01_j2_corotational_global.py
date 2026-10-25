from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from time import perf_counter

import numpy as np
import pytest

from solveur.core.assembly.nonlinear import assemble_internal_tangent, build_nonlinear_assembly_plan
from solveur.core.nonlinear.material_state import initial_material_states
from solveur.core.nonlinear.state import deterministic_state_digest
from solveur.core.nonlinear.solver import NonlinearStaticSolver
from solveur.elements.solid.corotational_j2 import (
    CORRECTED_COROTATIONAL_J2,
    CORRECTED_TANGENT_POLAR_ANALYTIC_VERSION,
    CORRECTED_TANGENT_STRATEGY_VERSION,
)
from solveur.verification.robustness_mesh import _refinement_model


@pytest.mark.parametrize("family", ("TET4", "HEX8", "HEX20"))
def test_global_analytic_assembly_full_free_dof_basis_and_plastic_history(family: str) -> None:
    base = _refinement_model(family, 1)
    parameters = {
        **base.analysis.parameters,
        "kinematics": "corotational_j2",
        "corotational_formulation": CORRECTED_COROTATIONAL_J2,
        "j2_corotational_tangent": "analytic_experimental",
    }
    model = replace(base, analysis=replace(base.analysis, parameters=parameters))
    dofs = model.dof_manager()
    plan = build_nonlinear_assembly_plan(model, dofs)
    def uniaxial_x_displacement(axial_strain: float) -> np.ndarray:
        displacement = np.zeros(dofs.ndof)
        for node, coordinates in enumerate(model.nodes):
            displacement[dofs.index(node, "UX")] = axial_strain * float(coordinates[0])
        return displacement

    preload_displacement = uniaxial_x_displacement(2.0e-3)
    initial = initial_material_states(model)
    accepted_hash = deterministic_state_digest(initial)
    _, _, plastic_history = assemble_internal_tangent(
        model, dofs, preload_displacement, initial, plan=plan
    )
    assert deterministic_state_digest(initial) == accepted_hash
    alpha_pre = np.asarray(
        [point["equivalent_plastic_strain"] for points in plastic_history.values() for point in points]
    )
    assert np.max(alpha_pre) > 0.0

    tangent_displacement = uniaxial_x_displacement(2.5e-3)
    force, tangent, _ = assemble_internal_tangent(
        model, dofs, tangent_displacement, plastic_history, plan=plan
    )
    base_branch_statuses = [
        entry.element.last_corrected_tangent_diagnostics["numerical_status"] for entry in plan.elements
    ]
    assert all(status == "SMOOTH_PLASTIC" for status in base_branch_statuses), base_branch_statuses
    existing_parameters = {key: value for key, value in parameters.items() if key != "j2_corotational_tangent"}
    existing_model = replace(base, analysis=replace(base.analysis, parameters=existing_parameters))
    existing_plan = build_nonlinear_assembly_plan(existing_model, dofs)
    existing_force, _, _ = assemble_internal_tangent(
        existing_model, dofs, tangent_displacement, plastic_history, plan=existing_plan
    )
    force_gap = float(np.linalg.norm(force - existing_force) / max(np.linalg.norm(force), 1.0))
    np.testing.assert_allclose(force, existing_force, rtol=2.0e-12, atol=2.0e-12)
    direction_rng = np.random.default_rng(2911 + len(family))
    fixed = {
        dofs.index(condition.node, name)
        for condition in model.fixed_dofs
        for name in condition.dofs
    }
    free = np.asarray([index for index in range(dofs.ndof) if index not in fixed], dtype=int)
    if family == "TET4":
        directions = [np.eye(dofs.ndof)[index] for index in free]
    else:
        directions = []
        for _ in range(4):
            direction = np.zeros(dofs.ndof)
            direction[free] = direction_rng.normal(size=free.size)
            direction /= np.linalg.norm(direction)
            directions.append(direction)
    errors = []
    step = 2.0e-7
    for direction in directions:
        plus, _, _ = assemble_internal_tangent(
            model, dofs, tangent_displacement + step * direction, plastic_history, plan=plan
        )
        minus, _, _ = assemble_internal_tangent(
            model, dofs, tangent_displacement - step * direction, plastic_history, plan=plan
        )
        observed = (plus - minus) / (2.0 * step)
        action = np.asarray(tangent @ direction).reshape(-1)
        errors.append(float(np.linalg.norm(observed - action) / max(np.linalg.norm(action), 1.0)))
    assert max(errors) < 2.0e-5, {"family": family, "errors": errors, "force_norm": float(np.linalg.norm(force))}

    history_snapshot = deepcopy(plastic_history)
    unload_displacement = uniaxial_x_displacement(1.99e-3)
    _, _, unloaded = assemble_internal_tangent(
        model, dofs, unload_displacement, plastic_history, plan=plan
    )
    assert deterministic_state_digest(plastic_history) == deterministic_state_digest(history_snapshot)
    alpha_unload = np.asarray(
        [point["equivalent_plastic_strain"] for points in unloaded.values() for point in points]
    )
    np.testing.assert_allclose(alpha_unload, alpha_pre, rtol=0.0, atol=2.0e-12)

    reload_displacement = uniaxial_x_displacement(2.01e-3)
    for node, coordinates in enumerate(model.nodes):
        reload_displacement[dofs.index(node, "UY")] = 2.0e-5 * float(coordinates[0]) * float(coordinates[2])
    _, _, reloaded = assemble_internal_tangent(
        model, dofs, reload_displacement, unloaded, plan=plan
    )
    alpha_reload = np.asarray(
        [point["equivalent_plastic_strain"] for points in reloaded.values() for point in points]
    )
    assert np.all(alpha_reload >= alpha_unload - 2.0e-12)
    print(
        "E01_CORO_GLOBAL_HISTORY_METRICS="
        + json.dumps(
            {
                "family": family,
                "force_map_relative_gap_at_plastic_state": force_gap,
                "max_tangent_action_relative_error": max(errors),
                "free_dof_count": int(free.size),
                "directions_checked": len(directions),
                "base_branch_statuses": base_branch_statuses,
                "max_preload_peeq": float(np.max(alpha_pre)),
                "max_unload_peeq": float(np.max(alpha_unload)),
                "max_reload_peeq": float(np.max(alpha_reload)),
                "history_input_immutable": True,
                "sequence": "plastic_preload_elastic_unload_nonproportional_reload",
            },
            sort_keys=True,
        )
    )


@pytest.mark.parametrize("family", ("TET4", "HEX8", "HEX20"))
def test_newton_analytic_experimental_vs_corrected_fd(family: str) -> None:
    base = _refinement_model(family, 1)
    common_parameters = {
        **base.analysis.parameters,
        "kinematics": "corotational_j2",
        "corotational_formulation": CORRECTED_COROTATIONAL_J2,
        "max_iterations": 35,
        "tolerance": 1.0e-8,
    }
    loads = [replace(load, value=load.value * 0.25) for load in base.loads]
    outcomes = {}
    for name, strategy in (
        ("corrected_fd", None),
        ("analytic_experimental", "analytic_experimental"),
    ):
        parameters = dict(common_parameters)
        if strategy is not None:
            parameters["j2_corotational_tangent"] = strategy
        model = replace(
            base,
            analysis=replace(base.analysis, method="newton_line_search", parameters=parameters),
            loads=loads,
        )
        started = perf_counter()
        result = NonlinearStaticSolver().solve(model)
        elapsed = perf_counter() - started
        assert result.status == "PASS", {"family": family, "strategy": name, "solver": result.solver}
        peeq = max(
            float(point["equivalent_plastic_strain"])
            for points in result.material_states.values()
            for point in points
        )
        assert peeq > 0.0
        steps = result.solver["steps"]
        assert all(step["state_committed"] for step in steps)
        outcomes[name] = {
            "result": result,
            "elapsed_seconds": elapsed,
            "max_peeq": peeq,
            "iterations": int(sum(int(step["iterations"]) for step in steps)),
            "cutbacks": int(result.solver.get("rejected_increments", 0)),
            "max_residual_norm": float(max(float(step["residual_norm"]) for step in steps)),
        }

    fd = outcomes["corrected_fd"]["result"]
    analytic = outcomes["analytic_experimental"]["result"]
    assert fd.solver["tangent_strategy_version"] == CORRECTED_TANGENT_STRATEGY_VERSION
    assert analytic.solver["tangent_strategy_version"] == CORRECTED_TANGENT_POLAR_ANALYTIC_VERSION
    assert "tangent_relative_step" in fd.solver
    assert "tangent_relative_step" not in analytic.solver
    metrics = {
        "family": family,
        "displacement_relative_gap": float(
            np.linalg.norm(analytic.displacements - fd.displacements)
            / max(np.linalg.norm(fd.displacements), 1.0)
        ),
        "max_peeq_absolute_gap": abs(outcomes["analytic_experimental"]["max_peeq"] - outcomes["corrected_fd"]["max_peeq"]),
        "corrected_fd": {
            key: value for key, value in outcomes["corrected_fd"].items() if key != "result"
        },
        "analytic_experimental": {
            key: value for key, value in outcomes["analytic_experimental"].items() if key != "result"
        },
        "interpretation": "experimental comparison; no Owner acceptance band applied",
    }
    print("E01_CORO_NEWTON_METRICS=" + json.dumps(metrics, sort_keys=True))
