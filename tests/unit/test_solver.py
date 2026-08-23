import numpy as np
import pytest

from solveur.core.assembler import GlobalAssembler
from solveur.core.errors import InputValidationError
from solveur.core.solver import LinearStaticSolver
from tests.unit.test_mesh_validation import valid_tet4_model


def test_assembler_builds_sparse_system():
    model = valid_tet4_model()
    dofs = model.dof_manager()
    stiffness = GlobalAssembler().assemble_stiffness(model, dofs)
    loads = GlobalAssembler().assemble_loads(model, dofs)
    assert stiffness.shape == (12, 12)
    assert loads.shape == (12,)
    assert np.count_nonzero(loads) == 1


def test_chunked_assembler_matches_single_chunk_for_stiffness_and_mass():
    model = valid_tet4_model()
    model.elements = model.elements * 5
    model.materials["steel"]["density"] = 7800.0
    dofs = model.dof_manager()
    chunked = GlobalAssembler(chunk_size=2)
    stiffness_chunked = chunked.assemble_stiffness(model, dofs)
    stiffness_diagnostics = dict(chunked.last_diagnostics)
    mass_chunked = chunked.assemble_mass(model, dofs)
    reference = GlobalAssembler(chunk_size=100)
    stiffness_reference = reference.assemble_stiffness(model, dofs)
    mass_reference = reference.assemble_mass(model, dofs)
    assert np.allclose(stiffness_chunked.toarray(), stiffness_reference.toarray())
    assert np.allclose(mass_chunked.toarray(), mass_reference.toarray())
    assert stiffness_diagnostics["chunk_count"] == 3
    assert stiffness_diagnostics["peak_chunk_entry_count"] == 2 * 12**2
    assert stiffness_diagnostics["accumulator_chunk_count"] == 3
    assert stiffness_diagnostics["accumulator_occupied_levels"] >= 1
    phases = stiffness_diagnostics["assembly_phase_seconds"]
    assert all(float(phases[name]) >= 0.0 for name in phases)
    assert chunked.last_diagnostics["matrix"] == "mass"
    assert chunked.last_diagnostics["chunk_count"] == 3


def test_chunked_assembler_rejects_invalid_model_chunk_size():
    model = valid_tet4_model()
    model.analysis.parameters["assembly_chunk_size"] = 0
    with pytest.raises(InputValidationError, match="assembly_chunk_size"):
        GlobalAssembler().assemble_stiffness(model, model.dof_manager())


def test_solver_solves_tet4_model():
    result = LinearStaticSolver().solve(valid_tet4_model())
    assert result.status == "PASS"
    assert result.ndof == 12
    assert result.max_displacement > 0.0


def test_solver_result_contains_white_box_audit():
    result = LinearStaticSolver().solve(valid_tet4_model())
    data = result.to_dict()
    assert data["audit"]["purpose"] == "white_box_solver_audit"
    assert data["audit"]["boundary"]["fixed_dof_count"] == 9
    assert data["audit"]["boundary"]["free_dof_count"] == 3
    assert data["audit"]["element_types"] == {"TET4": 1}
    assert data["audit"]["mesh_details"]["component_count"] == 1
    assert data["audit"]["mesh_details"]["components"][0]["fixed_translation_node_count"] == 3
    assert data["audit"]["vectors"][0]["name"] == "loads"
    element_audit = data["audit"]["element_audits"][0]
    assert element_audit["geometry"]["signed_corner_volume"] > 0.0
    assert element_audit["material_data"]["type"] == "isotropic_3d"
    assert element_audit["matrices"][0]["name"] == "local_stiffness"
    assert element_audit["matrices"][0]["is_symmetric"] is True
    post = data["audit"]["post_results"][0]
    assert post["type"] == "TET4"
    assert post["calculation_frame"] == "global"
    assert post["global_dof_indices"] == list(range(12))
    assert len(post["calculation_displacement"]) == 12
    assert np.all(np.isfinite(post["strain"]))
    assert np.all(np.isfinite(post["stress"]))
    assert post["von_mises"] >= 0.0
    equilibrium = data["audit"]["equilibrium"]
    assert equilibrium["free_residual_norm"] < 1.0e-8
    assert equilibrium["linear_energy_identity_relative_error"] < 1.0e-10
    assert equilibrium["external_resultant"] == pytest.approx([1000.0, 0.0, 0.0])
    assert equilibrium["reaction_resultant"] == pytest.approx([-1000.0, 0.0, 0.0])
    assert equilibrium["force_balance_relative_error"] < 1.0e-12
    assert equilibrium["moment_balance_relative_error"] < 1.0e-12
    assert len(equilibrium["reactions"]) == 9
    checks = {check["name"]: check["status"] for check in data["audit"]["checks"]}
    assert checks["mesh_validation"] == "PASS"
    assert checks["equilibrium:free_relative_residual"] == "PASS"
    assert checks["equilibrium:linear_energy_identity"] == "PASS"
    assert checks["equilibrium:global_force_balance"] == "PASS"
    assert checks["equilibrium:global_moment_balance"] == "PASS"
    assert checks["element:0:TET4:positive_volume"] == "PASS"
    assert checks["post:0:TET4:finite_calculation_displacement"] == "PASS"
    assert checks["post:0:TET4:finite_stress"] == "PASS"
    assert checks["post:0:TET4:von_mises_nonnegative"] == "PASS"
    assert checks["matrix:reduced_stiffness:positive_definite"] == "PASS"
    assert checks["matrix:reduced_stiffness:condition_estimate"] == "PASS"
    matrix_names = {matrix["name"] for matrix in data["audit"]["matrices"]}
    assert {"stiffness", "reduced_stiffness"} <= matrix_names
    reduced = next(matrix for matrix in data["audit"]["matrices"] if matrix["name"] == "reduced_stiffness")
    assert reduced["positive_definite_estimate"] is True
    assert reduced["condition_estimate"] > 0.0
