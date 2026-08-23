import numpy as np
import pytest

from solveur.api import inspect_model, list_methods, solve_model
from solveur.core.harmonic import frequency_grid
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.elements.solid.tet4 import Tet4Element
from solveur.materials.solid import NonlinearSolidMaterial, SolidMaterial
from tests.unit.test_mesh_validation import valid_tet4_model


def modal_tet4_model():
    return FiniteElementModel.from_raw(
        analysis={"type": "modal", "method": "eigh", "modes": 3},
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
    )


def nonlinear_tet4_model(method="newton_raphson"):
    return FiniteElementModel.from_raw(
        analysis={
            "type": "nonlinear_static",
            "method": method,
            "load_steps": 5,
            "max_iterations": 50,
            "tolerance": 1.0e-9,
        },
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "rubber"}],
        materials={"rubber": {"type": "nonlinear_isotropic_3d", "E": 1000.0, "nu": 0.25, "hardening": 1.0e6}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": 10.0}],
    )


def transient_tet4_model():
    return FiniteElementModel.from_raw(
        analysis={
            "type": "transient_dynamic",
            "method": "newmark",
            "time_step": 0.01,
            "steps": 8,
            "rayleigh_alpha": 0.02,
            "load_function": "linear_ramp",
        },
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.25, "density": 10.0}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
    )


def transient_sdof_tet4_model():
    return FiniteElementModel.from_raw(
        analysis={
            "type": "transient_dynamic",
            "method": "newmark",
            "time_step": 0.001,
            "steps": 40,
            "rayleigh_alpha": 0.0,
            "rayleigh_beta": 0.0,
            "load_factors": [0.0],
            "initial_displacements": [{"node": 1, "dof": "UX", "value": 1.0e-3}],
        },
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.25, "density": 10.0}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 1, "dofs": ["UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[],
    )


def harmonic_tet4_model():
    return FiniteElementModel.from_raw(
        analysis={
            "type": "harmonic_response",
            "method": "direct_frequency",
            "frequencies_hz": [0.0, 5.0, 10.0],
            "rayleigh_alpha": 0.05,
        },
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.25, "density": 10.0}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
    )


def harmonic_sdof_tet4_model():
    return FiniteElementModel.from_raw(
        analysis={
            "type": "harmonic_response",
            "method": "direct_frequency",
            "frequencies_hz": [0.0, 2.0, 8.0],
            "rayleigh_alpha": 0.05,
        },
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.25, "density": 10.0}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 1, "dofs": ["UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
    )


def elastoplastic_tet4_model():
    return FiniteElementModel.from_raw(
        analysis={
            "type": "nonlinear_static",
            "method": "newton_line_search",
            "load_steps": 5,
            "max_iterations": 80,
            "tolerance": 1.0e-9,
        },
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "plastic"}],
        materials={
            "plastic": {
                "type": "von_mises_elastoplastic_3d",
                "E": 1000.0,
                "nu": 0.25,
                "yield_stress": 5.0,
                "hardening_modulus": 100.0,
            }
        },
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": 10.0}],
    )


def test_tet4_mass_and_stress_recovery():
    coords = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
    element = Tet4Element(SolidMaterial(E=210.0e9, nu=0.3, density=7800.0))
    mass = element.mass(coords)
    assert mass.shape == (12, 12)
    assert np.isclose(mass.sum(), 3.0 * 7800.0 / 6.0)
    displacement = np.zeros(12)
    displacement[3] = 1.0e-4
    stress = element.stress(coords, displacement)
    assert stress.shape == (6,)
    assert Tet4Element.von_mises(stress) > 0.0


def test_tet4_nonlinear_internal_force_and_tangent():
    coords = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
    element = Tet4Element(NonlinearSolidMaterial(E=1000.0, nu=0.25, hardening=1.0e6))
    displacement = np.zeros(12)
    displacement[3] = 1.0e-2
    internal, tangent = element.internal_force_and_tangent(coords, displacement)
    assert internal.shape == (12,)
    assert tangent.shape == (12, 12)
    assert np.allclose(tangent, tangent.T)


def test_linear_static_can_use_cg_and_outputs_stress():
    model = valid_tet4_model()
    model.analysis = model.analysis.with_overrides(method="cg")
    result = solve_model(model)
    assert result.method == "cg"
    assert result.solver["converged"] is True
    assert np.isclose(result.solver["residual_history"][-1], result.solver["residual_norm"])
    assert result.element_results[0]["von_mises"] > 0.0
    assert len(result.element_results[0]["principal_stress"]) == 3
    assert len(result.element_results[0]["principal_strain"]) == 3
    assert "hydrostatic_pressure" in result.element_results[0]
    assert len(result.element_results[0]["integration_points"]) == 1
    assert len(result.nodal_results) == model.node_count
    assert result.nodal_results[0]["contributing_element_count"] == 1
    assert len(result.nodal_results[0]["principal_stress"]) == 3


def test_linear_static_can_use_bicgstab_with_jacobi():
    model = valid_tet4_model()
    model.analysis = {"type": "linear_static", "method": "bicgstab", "preconditioner": "jacobi"}
    result = solve_model(model)
    assert result.method == "bicgstab"
    assert result.solver["preconditioner"] == "jacobi"
    assert result.solver["converged"] is True


def test_linear_static_can_use_minres():
    model = valid_tet4_model()
    model.analysis = {"type": "linear_static", "method": "minres", "preconditioner": "jacobi"}
    result = solve_model(model)
    assert result.method == "minres"
    assert result.solver["converged"] is True


def test_linear_static_can_use_gmres_with_ilu():
    model = valid_tet4_model()
    model.analysis = {"type": "linear_static", "method": "gmres", "preconditioner": "ilu"}
    result = solve_model(model)
    assert result.method == "gmres"
    assert result.solver["preconditioner"] == "ilu"
    assert result.solver["converged"] is True


def test_modal_analysis_returns_positive_frequencies():
    result = solve_model(modal_tet4_model())
    data = result.to_dict()
    assert data["analysis"] == "modal"
    assert len(data["modes"]) == 3
    assert all(mode["frequency_hz"] > 0.0 for mode in data["modes"])
    assert data["solver"]["max_relative_residual"] < 1.0e-10
    assert data["solver"]["mass_orthogonality_error"] < 1.0e-10
    assert data["solver"]["stiffness_diagonal_error"] < 1.0e-10
    assert data["solver"]["effective_modal_mass"]["total_direction_mass"]["UX"] > 0.0
    assert data["solver"]["dense_conversion_used"] is True
    assert data["solver"]["dense_modal_max_dofs"] == 2000
    assert data["solver"]["arpack"]["shift_eigenvalue"] == 0.0
    assert data["solver"]["assembly"]["stiffness"]["chunk_count"] == 1


def test_modal_eigenpair_refinement_reports_residual_improvement():
    model = modal_tet4_model()
    model.analysis = {
        "type": "modal",
        "method": "eigh",
        "modes": 3,
        "modal_eigenpair_refinement_iterations": 1,
    }
    result = solve_model(model)
    refinement = result.solver["eigenpair_refinement"]
    assert refinement["iterations_requested"] == 1
    assert refinement["iterations_performed"] == 1
    assert refinement["maximum_residual_after"] <= refinement["maximum_residual_before"]
    assert result.solver["max_relative_residual"] < 1.0e-10


def test_transient_dynamic_newmark_returns_time_history():
    result = solve_model(transient_tet4_model())
    data = result.to_dict()
    assert data["status"] == "PASS"
    assert data["analysis"] == "transient_dynamic"
    assert data["method"] == "newmark"
    assert len(data["solver"]["time_history"]) == 8
    assert data["solver"]["time_history"][-1]["time"] == 0.08
    assert data["max_displacement"] > 0.0
    assert data["solver"]["time_history"][-1]["kinetic_energy"] >= 0.0
    assert data["solver"]["time_history"][-1]["strain_energy"] >= 0.0
    assert "total_energy" in data["solver"]["time_history"][-1]
    assert data["solver"]["effective_factorization_reused"] is True
    assert data["solver"]["effective_factorization_count"] == 1
    assert data["solver"]["effective_factorization_solve_count"] == 8
    assert data["solver"]["effective_factorization_seconds"] >= 0.0
    assert data["solver"]["effective_factorization_solve_seconds_total"] >= 0.0
    assert data["solver"]["effective_factorization_last_solve_seconds"] >= 0.0
    assert data["solver"]["linear_execution"]["effective_matrix_nnz"] > 0
    assert data["solver"]["linear_selection"]["recommended_method"] == "cg"
    assert data["solver"]["linear_execution"]["used_method"] == "splu_reuse"
    assert data["solver"]["linear_execution"]["factorization_reused"] is True
    assert data["audit"]["solver_selection"] == data["solver"]["linear_selection"]
    assert data["audit"]["equilibrium"]["free_relative_residual"] < 1.0e-8
    assert data["element_results"][0]["von_mises"] > 0.0


def test_transient_dynamic_newmark_conserves_energy_without_damping():
    model = transient_tet4_model()
    model.analysis.parameters.update(
        {
            "steps": 60,
            "rayleigh_alpha": 0.0,
            "rayleigh_beta": 0.0,
            "load_factors": [0.0],
            "initial_displacements": [{"node": 1, "dof": "UX", "value": 1.0e-3}],
        }
    )
    model.loads = []
    data = solve_model(model).to_dict()
    drifts = [abs(row["relative_energy_drift"]) for row in data["solver"]["time_history"]]
    assert max(drifts) < 1.0e-10
    assert data["solver"]["time_history"][-1]["total_energy"] > 0.0


def test_transient_dynamic_iterative_method_does_not_create_direct_factorization():
    model = transient_tet4_model()
    model.analysis.parameters.update({"linear_method": "cg", "rtol": 1.0e-12})
    data = solve_model(model).to_dict()
    assert data["solver"]["effective_factorization_reused"] is False
    assert data["solver"]["effective_factorization_count"] == 0
    assert data["solver"]["effective_factorization_solve_count"] == 0
    assert data["solver"]["linear_selection"]["recommended_method"] == "cg"
    assert data["solver"]["linear_execution"]["used_method"] == "cg"


def test_transient_dynamic_applies_configured_direct_memory_gate():
    model = transient_tet4_model()
    model.analysis.parameters.update(
        {"direct_memory_budget_mb": 1.0e-9, "enforce_direct_memory_budget": True}
    )
    with pytest.raises(InputValidationError, match="Direct solver refused"):
        solve_model(model)


def test_transient_dynamic_sdof_matches_closed_form_initial_energy():
    data = solve_model(transient_sdof_tet4_model()).to_dict()
    volume = 1.0 / 6.0
    young = 1000.0
    poisson = 0.25
    constrained_modulus = young * (1.0 - poisson) / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
    expected_energy = 0.5 * volume * constrained_modulus * (1.0e-3) ** 2
    energies = [row["total_energy"] for row in data["solver"]["time_history"]]
    drifts = [abs(row["relative_energy_drift"]) for row in data["solver"]["time_history"]]
    assert data["audit"]["equilibrium"]["free_dof_count"] == 1
    assert np.isclose(energies[0], expected_energy, rtol=1.0e-12, atol=0.0)
    assert np.isclose(energies[-1], expected_energy, rtol=1.0e-10, atol=0.0)
    assert max(drifts) < 1.0e-10
    assert data["solver"]["time_history"][-1]["dynamic_residual_norm"] < 1.0e-10


def test_transient_dynamic_accepts_tabulated_load_factor():
    model = transient_tet4_model()
    model.analysis.parameters.update(
        {
            "steps": 4,
            "time_step": 0.25,
            "load_table": [
                {"time": 0.0, "factor": 0.0},
                {"time": 0.5, "factor": 1.0},
                {"time": 1.0, "factor": 0.0},
            ],
        }
    )
    data = solve_model(model).to_dict()
    factors = [row["load_factor"] for row in data["solver"]["time_history"]]
    assert factors == [0.5, 1.0, 0.5, 0.0]
    assert data["solver"]["load_definition"] == "load_table"


def test_transient_dynamic_restarts_from_intermediate_checkpoint(tmp_path):
    model = transient_tet4_model()
    checkpoint = tmp_path / "newmark_state.npz"
    model.analysis.parameters.update(
        {"checkpoint_path": str(checkpoint), "checkpoint_interval": 2, "checkpoint_keep_steps": True}
    )
    complete = solve_model(model)
    intermediate = tmp_path / "newmark_state.step00000004.npz"
    assert intermediate.is_file()

    restarted_model = transient_tet4_model()
    restarted_model.analysis.parameters["restart_from"] = str(intermediate)
    restarted = solve_model(restarted_model)

    np.testing.assert_allclose(restarted.displacements, complete.displacements, rtol=1.0e-12, atol=1.0e-14)
    np.testing.assert_allclose(restarted.velocities, complete.velocities, rtol=1.0e-12, atol=1.0e-14)
    np.testing.assert_allclose(restarted.accelerations, complete.accelerations, rtol=1.0e-12, atol=1.0e-14)
    assert restarted.solver["restart_used"] is True
    assert restarted.solver["restart_step"] == 4
    assert restarted.solver["history_is_partial"] is True
    assert [row["step"] for row in restarted.solver["time_history"]] == [5, 6, 7, 8]


def test_transient_dynamic_rejects_checkpoint_from_modified_model(tmp_path):
    model = transient_tet4_model()
    checkpoint = tmp_path / "newmark_state.npz"
    model.analysis.parameters["checkpoint_path"] = str(checkpoint)
    solve_model(model)

    changed = transient_tet4_model()
    changed.loads[0] = type(changed.loads[0])(node=1, dof="UX", value=2.0)
    changed.analysis.parameters["restart_from"] = str(checkpoint)
    with pytest.raises(InputValidationError, match="does not match"):
        solve_model(changed)


def test_harmonic_frequency_grid_accepts_list_and_range():
    assert np.allclose(frequency_grid({"frequencies_hz": [0.0, 2.5, 5.0]}), [0.0, 2.5, 5.0])
    assert np.allclose(frequency_grid({"frequency_start_hz": 1.0, "frequency_stop_hz": 3.0, "frequency_count": 3}), [1.0, 2.0, 3.0])


def test_harmonic_response_zero_frequency_matches_static_solution():
    harmonic = solve_model(harmonic_tet4_model()).to_dict()
    static_model = harmonic_tet4_model()
    static_model.analysis = {"type": "linear_static", "method": "direct"}
    static = solve_model(static_model)
    dof_index = static.dofs.index(1, "UX")
    zero_frequency = harmonic["frequency_response"][0]["displacements"][1]["dofs"]["UX"]
    assert harmonic["status"] == "PASS"
    assert harmonic["analysis"] == "harmonic_response"
    assert harmonic["solver"]["frequency_count"] == 3
    assert harmonic["solver"]["max_residual_norm"] < 1.0e-10
    selection = harmonic["solver"]["linear_selection"]
    assert selection["used_method"] == "spsolve"
    assert selection["frequency_count"] == 3
    assert selection["samples"][0]["matrix_contract"]["real"] is True
    assert selection["samples"][1]["matrix_contract"]["real"] is False
    assert harmonic["audit"]["solver_selection"] == selection
    assert np.isclose(zero_frequency["real"], static.displacements[dof_index])
    assert np.isclose(zero_frequency["amplitude"], abs(static.displacements[dof_index]))


def test_harmonic_sdof_matches_closed_form_amplitude_and_phase():
    data = solve_model(harmonic_sdof_tet4_model()).to_dict()
    stiffness = (1.0 / 6.0) * 1000.0 * (1.0 - 0.25) / ((1.0 + 0.25) * (1.0 - 2.0 * 0.25))
    mass = 10.0 * (1.0 / 6.0) / 10.0
    damping = 0.05 * mass
    for row in data["frequency_response"]:
        omega = 2.0 * np.pi * row["frequency_hz"]
        expected = 1.0 / complex(stiffness - omega**2 * mass, omega * damping)
        ux = row["displacements"][1]["dofs"]["UX"]
        assert np.isclose(ux["real"], expected.real, rtol=1.0e-12, atol=1.0e-14)
        assert np.isclose(ux["imag"], expected.imag, rtol=1.0e-12, atol=1.0e-14)
        assert np.isclose(ux["amplitude"], abs(expected), rtol=1.0e-12, atol=1.0e-14)
        assert np.isclose(ux["phase_degrees"], np.degrees(np.angle(expected)), atol=1.0e-10)
    assert data["solver"]["max_residual_norm"] < 1.0e-10


def test_harmonic_applies_configured_direct_memory_gate():
    model = harmonic_tet4_model()
    model.analysis.parameters.update(
        {"direct_memory_budget_mb": 1.0e-9, "enforce_direct_memory_budget": True}
    )
    with pytest.raises(InputValidationError, match="Direct solver refused"):
        solve_model(model)


def test_nonlinear_static_newton_solves_true_nonlinear_tet4():
    result = solve_model(nonlinear_tet4_model())
    data = result.to_dict()
    assert data["analysis"] == "nonlinear_static"
    assert data["solver"]["steps"][-1]["relative_residual"] < 1.0e-9
    assert data["audit"]["equilibrium"]["free_residual_norm"] < 1.0e-8
    assert data["audit"]["equilibrium"]["load_factor"] == 1.0
    assert data["element_results"][0]["von_mises"] > 0.0
    assert data["nodal_results"]


def test_nonlinear_static_solves_von_mises_elastoplastic_tet4():
    result = solve_model(elastoplastic_tet4_model())
    data = result.to_dict()
    element = data["element_results"][0]
    assert data["status"] == "PASS"
    assert element["material_state"]["model"] == "von_mises_isotropic_hardening"
    assert element["equivalent_plastic_strain"] > 0.0
    assert element["integration_points"][0]["equivalent_plastic_strain"] > 0.0
    assert data["nodal_results"][0]["equivalent_plastic_strain"] > 0.0
    assert data["solver"]["path_dependent_material_state"] is True
    assert len(data["material_states"]) == 1
    point_state = data["material_states"][0]["integration_points"][0]
    assert np.isclose(point_state["equivalent_plastic_strain"], element["equivalent_plastic_strain"])
    assert np.allclose(point_state["plastic_strain"], element["plastic_strain"])
    assert data["solver"]["steps"][-1]["relative_residual"] < 1.0e-9
    assert any(check["name"].endswith("equivalent_plastic_strain_nonnegative") for check in data["audit"]["checks"])


def test_modified_newton_is_available_for_nonlinear_static():
    result = solve_model(nonlinear_tet4_model(method="modified_newton"))
    assert result.status == "PASS"


def test_newton_line_search_is_available_for_nonlinear_static():
    result = solve_model(nonlinear_tet4_model(method="newton_line_search"))
    data = result.to_dict()
    assert data["status"] == "PASS"
    assert "line_search_reductions" in data["solver"]["steps"][-1]


def test_nonlinear_adaptive_load_steps_solve():
    model = nonlinear_tet4_model(method="newton_line_search")
    model.analysis.parameters.update(
        {
            "adaptive_load_steps": True,
            "initial_load_increment": 1.0,
            "min_load_increment": 0.05,
            "max_load_increment": 1.0,
            "max_iterations": 6,
        }
    )
    result = solve_model(model)
    data = result.to_dict()
    assert data["solver"]["adaptive_load_steps"] is True
    assert data["solver"]["steps"][-1]["load_factor"] == 1.0
    assert data["solver"]["steps"][-1]["relative_residual"] < 1.0e-9


def test_arc_length_solves_proportional_nonlinear_path():
    model = nonlinear_tet4_model(method="arc_length")
    model.analysis.parameters.update({"load_steps": 5, "max_arc_steps": 12, "target_load_factor": 1.0})
    result = solve_model(model)
    data = result.to_dict()
    assert data["solver"]["arc_length"] is True
    assert abs(data["solver"]["steps"][-1]["load_factor"] - 1.0) < 1.0e-3
    assert data["solver"]["steps"][-1]["relative_residual"] < 1.0e-9


def test_available_methods_include_literature_families():
    methods = list_methods()
    assert "cg" in methods["linear_static"]
    assert "bicgstab" in methods["linear_static"]
    assert "minres" in methods["linear_static"]
    assert "newton_line_search" in methods["nonlinear_static"]
    assert "newton_raphson" in methods["nonlinear_static"]
    assert "lanczos" in methods["modal"]
    assert "newmark" in methods["transient_dynamic"]
    assert "direct_frequency" in methods["harmonic_response"]


def test_inspect_model_returns_white_box_audit_without_solving():
    audit = inspect_model(valid_tet4_model())
    data = audit.to_dict()
    assert data["mesh_status"] == "PASS"
    assert data["ndof"] == 12
    assert data["dof_map"][0]["dofs"]["UX"] == 0
    assert data["element_dofs"][0]["global_dof_indices"] == list(range(12))
    assert data["element_audits"][0]["global_dof_indices"] == list(range(12))
    assert data["element_audits"][0]["matrices"][0]["rank_estimate"] > 0
    assert data["matrices"][0]["name"] == "stiffness"
    assert {check["name"] for check in data["checks"]} >= {"mesh_validation", "boundary_has_fixed_dofs"}
