from dataclasses import dataclass

import numpy as np
import pytest

from solveur.core.assembly_plan import AssemblyPlan, _canonicalize
from solveur.core.assembler import GlobalAssembler
from solveur.core.errors import InputValidationError
from solveur.core.model import BoundaryCondition
from tests.unit.test_mesh_validation import valid_tet4_model


def test_assembly_plan_reuses_global_dof_maps_for_stiffness_and_mass() -> None:
    model = valid_tet4_model()
    model.materials["steel"]["density"] = 7800.0
    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    plan = assembler.prepare_plan(model, dofs)

    stiffness = assembler.assemble_stiffness(model, dofs, plan=plan)
    stiffness_diagnostics = dict(assembler.last_diagnostics)
    mass = assembler.assemble_mass(model, dofs, plan=plan)
    mass_diagnostics = dict(assembler.last_diagnostics)

    assert plan.matches(model, dofs)
    assert plan.build_seconds >= 0.0
    assert stiffness_diagnostics["assembly_plan_reused"] is True
    assert mass_diagnostics["assembly_plan_reused"] is True
    assert float(stiffness_diagnostics["assembly_phase_seconds"]["assembly_plan"]) == 0.0
    assert float(mass_diagnostics["assembly_phase_seconds"]["assembly_plan"]) == 0.0
    assert np.all(np.isfinite(stiffness.data))
    assert np.all(np.isfinite(mass.data))
    assert len(plan.fingerprint) == 64
    assert plan.chunk_size == 256


def test_paired_assembly_reuses_one_chunk_pattern_for_k_and_m() -> None:
    model = valid_tet4_model()
    model.materials["steel"]["density"] = 7800.0
    dofs = model.dof_manager()
    assembler = GlobalAssembler(chunk_size=1)

    stiffness, mass, stiffness_diagnostics, mass_diagnostics = assembler.assemble_stiffness_and_mass(model, dofs)
    reference_stiffness = GlobalAssembler().assemble_stiffness(model, dofs)
    reference_mass = GlobalAssembler().assemble_mass(model, dofs)

    np.testing.assert_allclose(stiffness.toarray(), reference_stiffness.toarray())
    np.testing.assert_allclose(mass.toarray(), reference_mass.toarray())
    assert stiffness_diagnostics["paired_assembly"] is True
    assert mass_diagnostics["shared_chunk_pattern"] is True
    assert stiffness_diagnostics["assembly_index_dtype"] == "int32"
    assert mass_diagnostics["assembly_index_dtype"] == "int32"
    assert stiffness_diagnostics["final_nnz"] == stiffness.nnz
    assert mass_diagnostics["final_nnz"] == mass.nnz
    assert int(mass_diagnostics["assembly_peak_memory_estimate_bytes"]) > 0


def test_assembly_memory_budget_can_refuse_a_large_temporary_chunk() -> None:
    model = valid_tet4_model()
    model.analysis.parameters.update(
        {
            "assembly_memory_budget_mb": 1.0e-9,
            "enforce_assembly_memory_budget": True,
        }
    )
    with pytest.raises(InputValidationError, match="assembly_memory_budget"):
        GlobalAssembler().assemble_stiffness(model, model.dof_manager())


def test_assembly_memory_budget_warns_without_changing_default_execution() -> None:
    model = valid_tet4_model()
    model.analysis.parameters["assembly_memory_budget_mb"] = 0.001
    with pytest.warns(RuntimeWarning, match="assembly_memory_budget"):
        matrix = GlobalAssembler().assemble_stiffness(model, model.dof_manager())
    assert matrix.nnz > 0


def test_assembly_plan_rejects_a_different_model() -> None:
    model = valid_tet4_model()
    dofs = model.dof_manager()
    plan = GlobalAssembler().prepare_plan(model, dofs)
    other_model = valid_tet4_model()

    with pytest.raises(InputValidationError, match="does not match"):
        GlobalAssembler().assemble_stiffness(other_model, other_model.dof_manager(), plan=plan)


def test_assembly_plan_fingerprint_is_stable_for_equivalent_models() -> None:
    first = valid_tet4_model()
    second = valid_tet4_model()

    first_plan = GlobalAssembler(chunk_size=8).prepare_plan(first, first.dof_manager())
    second_plan = GlobalAssembler(chunk_size=8).prepare_plan(second, second.dof_manager())

    assert first_plan.fingerprint == second_plan.fingerprint
    assert first_plan.chunk_size == second_plan.chunk_size == 8


def test_assembly_plan_rejects_changed_content_or_chunk_size() -> None:
    model = valid_tet4_model()
    dofs = model.dof_manager()
    plan = GlobalAssembler(chunk_size=8).prepare_plan(model, dofs)

    model.fixed_dofs.append(BoundaryCondition(node=0, dofs=("UX",)))

    assert not plan.matches(model, dofs, chunk_size=8)
    assert not plan.matches(model, dofs, chunk_size=16)


def test_assembly_plan_canonicalization_handles_supported_model_values() -> None:
    @dataclass(frozen=True)
    class Marker:
        label: str
        value: np.float64

    encoded = _canonicalize(
        {
            "array": np.asarray([[1, 2]], dtype=np.int32),
            "marker": Marker("x", np.float64(2.5)),
            "items": (np.int64(3), "a"),
            "set": {"b", "a"},
        }
    )

    assert encoded["array"]["dtype"] == "int32"
    assert encoded["array"]["shape"] == [1, 2]
    assert encoded["marker"] == {"label": "x", "value": 2.5}
    assert encoded["items"] == [3, "a"]
    assert encoded["set"] == ["a", "b"]


def test_assembly_plan_build_rejects_non_positive_chunk_size() -> None:
    model = valid_tet4_model()
    with pytest.raises(ValueError, match="chunk_size"):
        AssemblyPlan.build(model, model.dof_manager(), chunk_size=0)
