from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest
from scipy.sparse import issparse

from solveur.api import solve_model
from solveur.core.analyses.dynamic_checkpoint import DynamicCheckpoint
from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem, excitation_identity_for
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.elements.discrete import ConcentratedMass, RotatingDisk, SpringDefinition
from solveur.io.dynamic_checkpoint import NpzDynamicCheckpointStore


_TEST_SOURCE_SHA = "a" * 40


def _dynamic_model(family: str = "TET4") -> FiniteElementModel:
    if family == "TET4":
        nodes = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
        connectivity = list(range(4))
        fixed_nodes = [0, 2, 3]
    elif family == "TET10":
        nodes = [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
            [0.5, 0, 0],
            [0.5, 0.5, 0],
            [0, 0.5, 0],
            [0, 0, 0.5],
            [0.5, 0, 0.5],
            [0, 0.5, 0.5],
        ]
        connectivity = list(range(10))
        fixed_nodes = [0, 2, 3, 6, 7, 9]
    elif family == "HEX8":
        nodes = [
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 1],
            [1, 1, 1],
            [0, 1, 1],
        ]
        connectivity = list(range(8))
        fixed_nodes = [0, 3, 4, 7]
    elif family == "HEX20":
        corners = np.asarray(
            [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]], dtype=float
        )
        edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
        nodes = np.vstack([corners, [(corners[a] + corners[b]) / 2 for a, b in edges]]).tolist()
        connectivity = list(range(20))
        fixed_nodes = [0, 3, 4, 7, 9, 10, 15, 17]
    elif family == "BEAM2":
        nodes = [[0, 0, 0], [1, 0, 0]]
        connectivity = [0, 1]
        fixed_nodes = [0]
    else:
        raise AssertionError(family)

    material = (
        {
            "type": "beam_isotropic",
            "E": 210.0e9,
            "nu": 0.3,
            "A": 0.01,
            "Iy": 1.0e-5,
            "Iz": 1.0e-5,
            "J": 2.0e-5,
            "density": 7800.0,
        }
        if family == "BEAM2"
        else {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}
    )
    fixed_dofs = [
        {"node": node, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"] if family == "BEAM2" else ["UX", "UY", "UZ"]}
        for node in fixed_nodes
    ]
    return FiniteElementModel.from_raw(
        analysis={"type": "transient_dynamic", "method": "newmark", "time_step": 0.01, "steps": 2},
        nodes=nodes,
        elements=[{"type": family, "nodes": connectivity, "material": "mat"}],
        materials={"mat": material},
        fixed_dofs=fixed_dofs,
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
    )


class _CountingAssembler(GlobalAssembler):
    def __init__(self) -> None:
        super().__init__()
        self.paired_assemblies = 0

    def assemble_stiffness_and_mass(self, *args, **kwargs):
        self.paired_assemblies += 1
        return super().assemble_stiffness_and_mass(*args, **kwargs)


@pytest.mark.parametrize("family", ["TET4", "TET10", "HEX8", "HEX20", "BEAM2"])
def test_prepared_operators_match_legacy_assembly_and_remain_sparse(family: str) -> None:
    model = _dynamic_model(family)
    direct_assembler = GlobalAssembler()
    dofs = model.dof_manager()
    direct_k, direct_m, _, _ = direct_assembler.assemble_stiffness_and_mass(model, dofs)

    prepared = PreparedDynamicSystem.prepare(model, source_sha=_TEST_SOURCE_SHA)

    assert np.allclose((prepared.stiffness_full - direct_k).toarray(), 0.0, rtol=0.0, atol=1.0e-12)
    assert np.allclose((prepared.mass_full - direct_m).toarray(), 0.0, rtol=0.0, atol=1.0e-12)
    free = prepared.free_dof_indices
    assert np.allclose((prepared.stiffness - direct_k[free, :][:, free]).toarray(), 0.0, rtol=0.0, atol=1.0e-12)
    assert np.allclose((prepared.mass - direct_m[free, :][:, free]).toarray(), 0.0, rtol=0.0, atol=1.0e-12)
    assert issparse(prepared.stiffness) and issparse(prepared.mass)
    assert prepared.element_families == (family,)
    storage = prepared.sparse_storage_bytes
    assert storage["stiffness_full"] > 0 and storage["mass_full"] > 0


def test_prepared_system_assembles_once_and_excitation_does_not_invalidate_operators() -> None:
    model = _dynamic_model()
    assembler = _CountingAssembler()
    prepared = PreparedDynamicSystem.prepare(model, source_sha=_TEST_SOURCE_SHA, assembler=assembler)
    original_excitation = prepared.excitation_identity
    changed_load = deepcopy(model)
    changed_load.loads[0] = type(changed_load.loads[0])(node=1, dof="UX", value=7.0)
    changed_history = deepcopy(model)
    changed_history.analysis.parameters["load_factors"] = [0.0, 1.0]

    assert prepared.matches_operator_inputs(changed_load)
    assert excitation_identity_for(changed_load) != original_excitation
    assert prepared.matches_operator_inputs(changed_history)
    assert excitation_identity_for(changed_history) != original_excitation
    prepared.require_compatible(changed_load)
    assert assembler.paired_assemblies == 1
    assert prepared.assembly_diagnostics["assembly_count"] == 1
    assert prepared.assembly_diagnostics["cache_scope"] == "INSTANCE_LOCAL_ONLY"
    assert prepared.assembly_diagnostics["global_cache"] is False
    assert prepared.assembly_diagnostics["factorization_cache"] == "NOT_CREATED_IN_WP02"


def test_assembly_option_change_does_not_reuse_an_incompatible_operator_identity() -> None:
    model = _dynamic_model()
    prepared = PreparedDynamicSystem.prepare(model, source_sha=_TEST_SOURCE_SHA)
    changed = deepcopy(model)
    changed.analysis.parameters["assembly_chunk_size"] = 32
    assert not prepared.matches_operator_inputs(changed)


@pytest.mark.parametrize(
    "mutation",
    ["coordinates", "material", "boundary", "mass", "spring"],
)
def test_physical_mutation_invalidates_prepared_identity(mutation: str) -> None:
    model = _dynamic_model()
    prepared = PreparedDynamicSystem.prepare(model, source_sha=_TEST_SOURCE_SHA)
    changed = deepcopy(model)
    if mutation == "coordinates":
        changed.nodes[1, 0] += 0.125
    elif mutation == "material":
        changed.materials["mat"]["E"] *= 1.01
    elif mutation == "boundary":
        changed.fixed_dofs.append(type(changed.fixed_dofs[0])(node=1, dofs=("UZ",)))
    elif mutation == "mass":
        changed.concentrated_masses.append(ConcentratedMass(node=1, mass=0.5))
    elif mutation == "spring":
        changed.springs.append(SpringDefinition(node_a=1, dofs=("UX",), stiffness=((25.0,),)))

    assert not prepared.matches_operator_inputs(changed)
    with pytest.raises(InputValidationError, match="do not match"):
        prepared.require_compatible(changed)


def test_snapshot_and_operator_accessors_do_not_expose_mutable_source_or_cache() -> None:
    model = _dynamic_model()
    prepared = PreparedDynamicSystem.prepare(model, source_sha=_TEST_SOURCE_SHA)
    frozen_snapshot = prepared.physical_snapshot
    expected_k = prepared.stiffness_full.toarray()
    expected_mass = prepared.mass_full.toarray()

    model.nodes[1, 0] = 9.0
    model.materials["mat"]["E"] = 1.0
    exported = prepared.stiffness_full
    exported.data[:] = 0.0

    assert prepared.physical_snapshot == frozen_snapshot
    np.testing.assert_array_equal(prepared.stiffness_full.toarray(), expected_k)
    np.testing.assert_array_equal(prepared.mass_full.toarray(), expected_mass)
    assert not prepared.matches_operator_inputs(model)
    assert prepared.physical_snapshot.__class__ is bytes


@pytest.mark.parametrize("family", ["MITC4", "WEDGE6"])
def test_prepared_system_fails_closed_outside_wp02_element_scope(family: str) -> None:
    model = _dynamic_model()
    model.elements[0] = type(model.elements[0])(type=family, nodes=model.elements[0].nodes, material="mat")
    with pytest.raises(InputValidationError, match="does not support element family"):
        PreparedDynamicSystem.prepare(model, source_sha=_TEST_SOURCE_SHA)


def test_prepared_system_rejects_rotating_disks_and_new_discrete_dofs() -> None:
    beam = _dynamic_model("BEAM2")
    beam.concentrated_masses.append(
        RotatingDisk(node=1, mass=1.0, diametral_inertia=0.1, polar_inertia=0.2, axis_global=(1.0, 0.0, 0.0))
    )
    with pytest.raises(InputValidationError, match="rotating disks are outside WP02"):
        PreparedDynamicSystem.prepare(beam, source_sha=_TEST_SOURCE_SHA)

    solid = _dynamic_model()
    solid.springs.append(SpringDefinition(node_a=1, dofs=("RX",), stiffness=((25.0,),)))
    with pytest.raises(InputValidationError, match="structural DDL already present"):
        PreparedDynamicSystem.prepare(solid, source_sha=_TEST_SOURCE_SHA)


@pytest.mark.parametrize("mutation", ["mass", "spring"])
def test_newmark_restart_rejects_checkpoint_after_discrete_physics_mutation(tmp_path, mutation: str) -> None:
    model = _dynamic_model()
    checkpoint_path = tmp_path / f"newmark-{mutation}.npz"
    model.analysis.parameters.update({"checkpoint_path": str(checkpoint_path), "checkpoint_interval": 1})
    solve_model(model)

    changed = _dynamic_model()
    if mutation == "mass":
        changed.concentrated_masses.append(ConcentratedMass(node=1, mass=0.5))
    else:
        changed.springs.append(SpringDefinition(node_a=1, dofs=("UX",), stiffness=((25.0,),)))
    changed.analysis.parameters["restart_from"] = str(checkpoint_path)
    with pytest.raises(InputValidationError, match="does not match"):
        solve_model(changed)


def test_newmark_old_checkpoint_is_readable_but_not_safe_to_resume(tmp_path) -> None:
    model = _dynamic_model()
    dofs = model.dof_manager()
    checkpoint_path = tmp_path / "legacy-newmark.npz"
    legacy = DynamicCheckpoint(
        model_signature="legacy-unversioned-signature",
        completed_step=1,
        time=0.01,
        time_step=0.01,
        beta=0.25,
        gamma=0.5,
        initial_energy=0.0,
        displacement=np.zeros(dofs.ndof),
        velocity=np.zeros(dofs.ndof),
        acceleration=np.zeros(dofs.ndof),
    )
    store = NpzDynamicCheckpointStore()
    store.save(checkpoint_path, legacy)
    assert store.load(checkpoint_path).model_signature == "legacy-unversioned-signature"

    model.analysis.parameters["restart_from"] = str(checkpoint_path)
    with pytest.raises(InputValidationError, match="readable but not safe to resume"):
        solve_model(model)


def test_prepared_identity_is_deterministic_and_dof_maps_are_defensive() -> None:
    model = _dynamic_model()
    first = PreparedDynamicSystem.prepare(model, source_sha=_TEST_SOURCE_SHA)
    second = PreparedDynamicSystem.prepare(model, source_sha=_TEST_SOURCE_SHA)
    assert first.physical_identity == second.physical_identity
    assert first.operator_identity == second.operator_identity
    assert first.assembly_plan_fingerprint == second.assembly_plan_fingerprint
    with pytest.raises(AttributeError):
        first.physical_identity = "changed"  # type: ignore[misc]
    third = PreparedDynamicSystem.prepare(model, source_sha="b" * 40)
    assert third.physical_identity == first.physical_identity
    assert third.operator_identity != first.operator_identity
    mapping = first.free_dof_indices
    with pytest.raises(ValueError):
        mapping[0] = 99
    assert first.free_dof_indices[0] != 99
