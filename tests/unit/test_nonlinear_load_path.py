from dataclasses import replace

import numpy as np
import pytest
from scipy.sparse import eye

from solveur.api import solve_model
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.nonlinear import NonlinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from tests.unit.test_analysis_features import elastoplastic_tet4_model


def test_signed_nonlinear_load_path_commits_each_cyclic_state():
    model = elastoplastic_tet4_model()
    expected_path = [0.5, 1.0, 0.0, -1.0, 0.0, 1.0]
    model.analysis.parameters["load_path"] = expected_path

    data = solve_model(model).to_dict()
    steps = data["solver"]["steps"]
    plastic = np.asarray([step["equivalent_plastic_strain_max"] for step in steps])

    assert data["solver"]["load_path"] == expected_path
    assert [step["load_increment"] for step in steps] == pytest.approx([0.5, 0.5, -1.0, -1.0, 1.0, 1.0])
    assert all(step["state_committed"] for step in steps)
    assert all(step["work_diagnostics_available"] for step in steps)
    assert all(np.isfinite(step["incremental_internal_work"]) for step in steps)
    assert all(np.isfinite(step["incremental_external_work"]) for step in steps)
    assert max(step["relative_work_imbalance"] for step in steps) < 1.0e-12
    assert all(step["cumulative_correction_norm"] >= step["last_correction_norm"] for step in steps)
    assert np.all(np.diff(plastic) >= 0.0)
    assert plastic[-1] > plastic[1]
    assert data["audit"]["equilibrium"]["load_factor"] == 1.0


def test_adaptive_rejection_rolls_back_displacement_and_material_state(monkeypatch):
    original = NonlinearStaticSolver._solve_load_step
    observations = {"calls": 0, "clean_retry": False}

    def reject_once(self, model, dofs, displacement, free, target_load, material_states, *args, **kwargs):
        observations["calls"] += 1
        if observations["calls"] == 1:
            displacement[free] = 123.0
            material_states[0][0]["equivalent_plastic_strain"] = 999.0
            raise NumericalConvergenceError("controlled rejected increment")
        if observations["calls"] == 2:
            observations["clean_retry"] = bool(
                np.allclose(displacement, 0.0)
                and material_states[0][0]["equivalent_plastic_strain"] == 0.0
            )
        return original(
            self,
            model,
            dofs,
            displacement,
            free,
            target_load,
            material_states,
            *args,
            **kwargs,
        )

    monkeypatch.setattr(NonlinearStaticSolver, "_solve_load_step", reject_once)
    model = elastoplastic_tet4_model()
    model.analysis.parameters.update(
        {
            "adaptive_load_steps": True,
            "initial_load_increment": 1.0,
            "min_load_increment": 0.1,
            "max_load_increment": 1.0,
            "cutback_factor": 0.5,
        }
    )

    data = solve_model(model).to_dict()

    assert observations["clean_retry"] is True
    assert data["solver"]["rejected_increments"] == 1
    assert data["solver"]["rejection_log"] == [
        {
            "base_load_factor": 0.0,
            "rejected_increment": 1.0,
            "retry_increment": 0.5,
        }
    ]
    assert data["solver"]["steps"][0]["load_step_cutbacks"] == 1
    assert data["material_states"][0]["integration_points"][0]["equivalent_plastic_strain"] < 1.0


@pytest.mark.parametrize(
    ("parameters", "message"),
    [
        ({"initial_load_increment": 0.0}, "strictly positive"),
        ({"min_load_increment": 0.6, "initial_load_increment": 0.5}, "must satisfy"),
        ({"cutback_factor": 1.0}, "strictly between"),
        ({"growth_factor": 0.9}, "greater than or equal"),
        ({"grow_below_iterations": 5, "shrink_above_iterations": 5}, "thresholds"),
        ({"max_cutbacks": -1}, "greater than or equal"),
    ],
)
def test_adaptive_load_controls_reject_invalid_parameters(parameters, message):
    model = elastoplastic_tet4_model()
    model.analysis.parameters.update({"adaptive_load_steps": True, **parameters})

    with pytest.raises(InputValidationError, match=message):
        solve_model(model)


def test_adaptive_load_steps_stop_after_maximum_cutbacks(monkeypatch):
    def reject_always(*args, **kwargs):
        raise NumericalConvergenceError("controlled rejected increment")

    monkeypatch.setattr(NonlinearStaticSolver, "_solve_load_step", reject_always)
    model = elastoplastic_tet4_model()
    model.analysis.parameters.update(
        {
            "adaptive_load_steps": True,
            "initial_load_increment": 1.0,
            "min_load_increment": 1.0e-6,
            "max_load_increment": 1.0,
            "cutback_factor": 0.5,
            "max_cutbacks": 2,
        }
    )

    with pytest.raises(NumericalConvergenceError, match="exceeded max_cutbacks=2"):
        solve_model(model)


def test_adaptive_load_steps_grow_after_fast_convergence():
    model = elastoplastic_tet4_model()
    model.analysis.parameters.update(
        {
            "adaptive_load_steps": True,
            "initial_load_increment": 0.25,
            "min_load_increment": 0.05,
            "max_load_increment": 0.75,
            "growth_factor": 2.0,
            "grow_below_iterations": 10,
            "shrink_above_iterations": 20,
        }
    )

    steps = solve_model(model).to_dict()["solver"]["steps"]

    assert [step["load_increment"] for step in steps] == pytest.approx([0.25, 0.5, 0.25])


def test_line_search_zero_crossing_uses_reference_load_norm(monkeypatch):
    model = elastoplastic_tet4_model()
    model.analysis = replace(model.analysis, method="newton_line_search")
    dofs = model.dof_manager()
    displacement = np.zeros(dofs.ndof)
    free = np.arange(dofs.ndof)

    def numerical_noise(*args, **kwargs):
        internal = np.full(dofs.ndof, 1.0e-7 / np.sqrt(dofs.ndof))
        return internal, eye(dofs.ndof, format="csr"), {}

    monkeypatch.setattr(NonlinearStaticSolver, "_assemble_internal_tangent", numerical_noise)
    step = NonlinearStaticSolver()._solve_load_step(
        model,
        dofs,
        displacement,
        free,
        np.zeros(dofs.ndof),
        {},
        1,
        0.0,
        -1.0,
        None,
        5,
        1.0e-8,
        "direct",
        1.0e-4,
        12,
        1.0e-4,
        reference_force_norm=1.0e8,
    )

    assert step.iterations == 0
    assert step.relative_residual == pytest.approx(1.0e-15)


@pytest.mark.parametrize("path", [[], [1.0, float("nan")], "not-a-list"])
def test_json_rejects_invalid_nonlinear_load_path(path):
    model = {
        "analysis": {"type": "nonlinear_static", "method": "newton_raphson", "load_path": path},
        "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "j2"}],
        "materials": {
            "j2": {
                "type": "von_mises_elastoplastic_3d",
                "E": 1000.0,
                "nu": 0.25,
                "yield_stress": 5.0,
                "hardening_modulus": 100.0,
            }
        },
    }
    with pytest.raises(InputValidationError, match="load_path"):
        JsonModelReader().from_dict(model)


def test_nonlinear_load_path_rejects_adaptive_combination():
    model = elastoplastic_tet4_model()
    model.analysis.parameters.update({"load_path": [0.5, 1.0], "adaptive_load_steps": True})

    with pytest.raises(InputValidationError, match="not yet compatible"):
        solve_model(model)
