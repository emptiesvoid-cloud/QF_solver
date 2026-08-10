"""Analytical tests for consistent distributed-load integration."""

from __future__ import annotations

import math

import numpy as np
import pytest

from solveur.core.assembler import GlobalAssembler
from solveur.core.analysis import AnalysisSettings
from solveur.core.dynamic import NewmarkDynamicSolver
from solveur.core.errors import InputValidationError
from solveur.core.harmonic import HarmonicResponseSolver
from solveur.core.model import FiniteElementModel
from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.loads.entities import BodyLoad, GravityLoad, SurfaceLoad
from solveur.loads.integration import DistributedLoadIntegrator, load_balance
from solveur.mesh.validation import MeshValidator


TET4_NODES = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
TET10_NODES = [
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
SHELL_NODES = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]


def test_json_reader_parses_supported_distributed_loads():
    data = _tet4_json(
        [
            {"type": "gravity", "acceleration": [0, 0, -9.81]},
            {"type": "body_force", "value": [1, 2, 3], "elements": [0]},
            {"type": "pressure", "element": 0, "face": 1, "value": 12.0},
            {
                "type": "surface_traction",
                "element": 0,
                "face": 2,
                "value": [3, 2, 1],
                "coordinate_system": "local",
            },
        ]
    )
    model = JsonModelReader().from_dict(data)
    assert len(model.distributed_loads) == 4
    assert isinstance(model.distributed_loads[0], GravityLoad)
    assert isinstance(model.distributed_loads[1], BodyLoad)
    assert isinstance(model.distributed_loads[2], SurfaceLoad)
    assert model.distributed_loads[2].type == "pressure"


@pytest.mark.parametrize(
    ("load", "message"),
    [
        ({"type": "unknown", "value": 1.0}, "unsupported"),
        ({"type": "pressure", "element": 0, "value": 1.0}, "face must be an integer"),
        ({"type": "surface_traction", "element": 0, "face": 0, "value": [1, 2]}, "three finite"),
        ({"type": "pressure", "element": 0, "face": 7, "value": 1.0}, "from 0 to 3"),
        ({"type": "pressure", "element": 0, "face": 0, "value": 1.0, "follower": True}, "future"),
        (
            {"type": "pressure", "element": 0, "face": 0, "value": 1.0, "coordinate_system": "polar"},
            "coordinate_system",
        ),
        ({"type": "body_force", "value": [1, 0, 0], "elements": [4]}, "existing element"),
        (
            {"type": "surface_traction", "element": 0, "face": 0, "value": [1, 0, 0], "coordinate_system": "polar"},
            "coordinate_system",
        ),
    ],
)
def test_json_reader_rejects_invalid_distributed_loads(load, message):
    with pytest.raises(InputValidationError, match=message):
        JsonModelReader().from_dict(_tet4_json([load]))


def test_shell_face_validation_handles_non_scalar_face_cleanly():
    data = _shell_json([{"type": "pressure", "element": 0, "face": [0], "value": 1.0}])
    with pytest.raises(InputValidationError, match="omitted or zero"):
        JsonModelReader().from_dict(data)

    model = _shell_model([])
    model.distributed_loads = [
        SurfaceLoad(
            element=0,
            kind="pressure",
            value=1.0,
            face=[0],  # type: ignore[arg-type]
        )
    ]
    report = MeshValidator().validate(model)
    assert report.status == "FAIL"
    assert any("MITC4 face" in error for error in report.errors)


def test_json_shell_density_enables_gravity_integration():
    data = _shell_json([{"type": "gravity", "acceleration": [0.0, 0.0, -10.0]}])
    data["materials"]["skin"]["density"] = 10.0
    model = JsonModelReader().from_dict(data)
    vector, assembler = _assemble(model)
    assert np.allclose(assembler.last_load_diagnostics["resultant"], [0.0, 0.0, -10.0])
    assert np.isclose(np.sum(vector.reshape(4, 6)[:, 2]), -10.0)


def test_raw_model_parser_rejects_unknown_distributed_load_type():
    with pytest.raises(InputValidationError, match="unsupported type"):
        _tet4_model([{"type": "not_a_load"}])


def test_sparse_distributed_load_contribution_matches_dense_contract():
    model = _tet4_model(
        [{"type": "surface_traction", "element": 0, "face": 1, "value": [3.0, -2.0, 1.0]}]
    )
    dofs = model.dof_manager()
    integrator = DistributedLoadIntegrator()
    dense = integrator.integrate(model, dofs, model.distributed_loads[0], 0)
    sparse = integrator.integrate_sparse(model, dofs, model.distributed_loads[0], 0)
    reconstructed = np.zeros(dofs.ndof)
    reconstructed[sparse.indices] = sparse.values
    assert reconstructed == pytest.approx(dense.vector)
    assert sparse.details == dense.details


def test_tet4_pressure_has_exact_consistent_nodal_forces_and_balance():
    model = _tet4_model([{"type": "pressure", "element": 0, "face": 1, "value": 2.0}])
    vector, assembler = _assemble(model)
    nodal = vector.reshape(4, 3)
    expected = np.zeros((4, 3))
    expected[[0, 2, 3], 0] = 1.0 / 3.0
    assert np.allclose(nodal, expected, atol=1.0e-14)
    assert np.allclose(assembler.last_load_diagnostics["resultant"], [1.0, 0.0, 0.0])
    assert np.allclose(assembler.last_load_diagnostics["moment_about_origin"], [0.0, 1.0 / 3.0, -1.0 / 3.0])


def test_tet10_pressure_uses_quadratic_consistent_face_distribution():
    model = _tet10_model([{"type": "pressure", "element": 0, "face": 1, "value": 2.0}])
    vector, assembler = _assemble(model)
    nodal = vector.reshape(10, 3)
    assert np.allclose(nodal[[0, 2, 3], 0], 0.0, atol=1.0e-14)
    assert np.allclose(nodal[[6, 7, 9], 0], 1.0 / 3.0, atol=1.0e-14)
    assert np.allclose(nodal[:, 1:], 0.0, atol=1.0e-14)
    assert np.allclose(assembler.last_load_diagnostics["resultant"], [1.0, 0.0, 0.0], atol=1.0e-14)
    assert assembler.last_load_diagnostics["contributions"][0]["nonzero_dof_count"] == 3


def test_tet10_curved_pressure_preserves_high_order_resultant_and_moment():
    nodes = np.asarray(TET10_NODES, dtype=float)
    nodes[4:] += np.asarray(
        [[0.0, 0.04, 0.01], [0.02, 0.02, 0.03], [0.03, 0.0, 0.01],
         [0.03, 0.01, 0.0], [0.01, 0.03, 0.02], [0.02, 0.01, 0.03]]
    )
    model = _tet10_model(
        [{"type": "pressure", "element": 0, "face": 1, "value": 2.0}],
        nodes=nodes.tolist(),
    )

    _, assembler = _assemble(model)

    np.testing.assert_allclose(
        assembler.last_load_diagnostics["resultant"],
        [1.0266666666666666, 0.013333333333333334, 0.013333333333333326],
        rtol=0.0,
        atol=1.0e-14,
    )
    np.testing.assert_allclose(
        assembler.last_load_diagnostics["moment_about_origin"],
        [0.00021333333333333504, 0.35365333333333343, -0.3532266666666668],
        rtol=0.0,
        atol=1.0e-14,
    )


def test_tet4_local_surface_traction_uses_oriented_face_basis():
    load = {
        "type": "surface_traction",
        "element": 0,
        "face": 1,
        "value": [2.0, 3.0, 4.0],
        "coordinate_system": "local",
    }
    model = _tet4_model([load])
    vector, assembler = _assemble(model)
    expected_resultant = np.array([-2.0, 1.5, 1.0])
    expected = np.zeros((4, 3))
    expected[[0, 2, 3]] = expected_resultant / 3.0
    assert np.allclose(vector.reshape(4, 3), expected, atol=1.0e-14)
    assert np.allclose(assembler.last_load_diagnostics["resultant"], expected_resultant)


@pytest.mark.parametrize(
    ("load", "expected_nodal", "expected_resultant"),
    [
        ({"type": "gravity", "acceleration": [0, 0, -10]}, [0.0, 0.0, -2.5], [0.0, 0.0, -10.0]),
        ({"type": "body_force", "value": [6, 0, 0]}, [0.25, 0.0, 0.0], [1.0, 0.0, 0.0]),
    ],
)
def test_tet4_volume_loads_conserve_analytical_resultant(load, expected_nodal, expected_resultant):
    model = _tet4_model([load], density=6.0)
    vector, assembler = _assemble(model)
    assert np.allclose(vector.reshape(4, 3), np.tile(expected_nodal, (4, 1)))
    assert np.allclose(assembler.last_load_diagnostics["resultant"], expected_resultant)


def test_tet10_gravity_conserves_mass_with_consistent_quadratic_weights():
    model = _tet10_model([{"type": "gravity", "acceleration": [0, 0, -10]}], density=6.0)
    vector, assembler = _assemble(model)
    nodal_z = vector.reshape(10, 3)[:, 2]
    assert np.allclose(nodal_z[:4], 0.5, atol=1.0e-13)
    assert np.allclose(nodal_z[4:], -2.0, atol=1.0e-13)
    assert np.isclose(np.sum(nodal_z), -10.0)
    assert np.allclose(assembler.last_load_diagnostics["resultant"], [0.0, 0.0, -10.0])


def test_mitc4_gravity_uses_density_area_and_thickness():
    model = _shell_model([{"type": "gravity", "acceleration": [0, 0, -10]}], density=10.0, thickness=0.1)
    vector, assembler = _assemble(model)
    translations = vector.reshape(4, 6)[:, :3]
    assert np.allclose(translations, np.tile([0.0, 0.0, -2.5], (4, 1)))
    assert np.allclose(vector.reshape(4, 6)[:, 3:], 0.0)
    assert np.allclose(assembler.last_load_diagnostics["resultant"], [0.0, 0.0, -10.0])


def test_mitc4_pressure_is_objective_under_rigid_rotation():
    pressure = 8.0
    angle = math.radians(37.0)
    rotation = np.array(
        [
            [math.cos(angle), 0.0, math.sin(angle)],
            [0.0, 1.0, 0.0],
            [-math.sin(angle), 0.0, math.cos(angle)],
        ]
    )
    nodes = (np.asarray(SHELL_NODES, dtype=float) @ rotation.T).tolist()
    model = _shell_model([{"type": "pressure", "element": 0, "value": pressure}], nodes=nodes)
    vector, assembler = _assemble(model)
    expected_resultant = rotation @ np.array([0.0, 0.0, -pressure])
    translations = vector.reshape(4, 6)[:, :3]
    assert np.allclose(translations, np.tile(expected_resultant / 4.0, (4, 1)), atol=1.0e-13)
    assert np.allclose(assembler.last_load_diagnostics["resultant"], expected_resultant, atol=1.0e-13)


def test_mitc4_local_surface_traction_follows_element_basis():
    load = {
        "type": "surface_traction",
        "element": 0,
        "value": [2.0, 3.0, 4.0],
        "coordinate_system": "local",
    }
    model = _shell_model([load])
    vector, assembler = _assemble(model)
    assert np.allclose(vector.reshape(4, 6)[:, :3], np.tile([0.5, 0.75, 1.0], (4, 1)))
    assert np.allclose(assembler.last_load_diagnostics["resultant"], [2.0, 3.0, 4.0])


def test_mitc4_edge_traction_is_consistent_per_unit_length():
    load = {"type": "edge_traction", "element": 0, "edge": 1, "value": [4.0, 0.0, 0.0]}
    model = _shell_model([load])
    vector, assembler = _assemble(model)
    nodal = vector.reshape(4, 6)
    assert np.allclose(nodal[[1, 2], 0], [2.0, 2.0])
    assert np.allclose(nodal[[0, 3], 0], 0.0)
    assert np.allclose(assembler.last_load_diagnostics["resultant"], [4.0, 0.0, 0.0])


def test_load_balance_includes_nodal_couples_and_preserves_vector_order():
    model = _shell_model(
        [{"type": "body_force", "value": [10.0, 0.0, 0.0]}],
        density=1.0,
        thickness=0.1,
        nodal_loads=[{"node": 0, "dof": "RZ", "value": 5.0}],
    )
    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    vectors = assembler.assemble_load_vectors(model, dofs)
    assert len(vectors) == 2
    assert np.count_nonzero(vectors[0]) == 1
    resultant, moment = load_balance(model, dofs, np.sum(vectors, axis=0))
    assert np.allclose(resultant, [1.0, 0.0, 0.0])
    assert np.allclose(moment, [0.0, 0.0, 4.5])
    assert [item["type"] for item in assembler.last_load_diagnostics["contributions"]] == ["nodal", "body_force"]


def test_static_load_assembly_does_not_retain_one_global_vector_per_load():
    model = _tet4_model(
        [
            {"type": "body_force", "value": [6.0, 0.0, 0.0]},
            {"type": "body_force", "value": [0.0, 6.0, 0.0]},
        ]
    )
    assembler = GlobalAssembler()
    total = assembler.assemble_loads(model, model.dof_manager())
    assert total.shape == (12,)
    assert np.allclose(assembler.last_load_vector, total)
    assert assembler.last_load_vectors == []

    vectors = assembler.assemble_load_vectors(model, model.dof_manager())
    assert len(vectors) == 2
    assert np.allclose(sum(vectors), total)


def test_mesh_validator_rejects_gravity_without_density_and_follower_pressure():
    gravity = _tet4_model([{"type": "gravity", "acceleration": [0, 0, -9.81]}], density=None)
    gravity_report = MeshValidator().validate(gravity)
    assert gravity_report.status == "FAIL"
    assert any("gravity requires positive density" in error for error in gravity_report.errors)

    follower = _tet4_model(
        [{"type": "pressure", "element": 0, "face": 0, "value": 1.0, "follower": True}]
    )
    follower_report = MeshValidator().validate(follower)
    assert follower_report.status == "FAIL"
    assert any("follower loads" in error for error in follower_report.errors)


def test_static_solver_exposes_distributed_load_balance_in_solver_and_audit():
    model = _tet4_model(
        [{"type": "pressure", "element": 0, "face": 0, "value": 1000.0}],
        fixed=True,
    )
    result = LinearStaticSolver().solve(model)
    data = result.to_dict()
    assert data["status"] == "PASS"
    assert data["solver"]["load_assembly"]["distributed_load_count"] == 1
    assert data["audit"]["load_assembly"] == data["solver"]["load_assembly"]
    assert np.linalg.norm(data["audit"]["load_assembly"]["resultant"]) > 0.0
    assert data["audit"]["equilibrium"]["free_relative_residual"] < 1.0e-10
    assert data["audit"]["equilibrium"]["force_balance_relative_error"] < 1.0e-12
    assert data["audit"]["equilibrium"]["moment_balance_relative_error"] < 1.0e-12


def test_tet4_body_force_reactions_balance_closed_form_resultant():
    model = _tet4_model(
        [{"type": "body_force", "value": [6000.0, 0.0, 0.0]}],
        fixed=True,
    )
    result = LinearStaticSolver().solve(model).to_dict()
    equilibrium = result["audit"]["equilibrium"]
    assert result["audit"]["load_assembly"]["resultant"] == pytest.approx([1000.0, 0.0, 0.0])
    assert equilibrium["external_resultant"] == pytest.approx([1000.0, 0.0, 0.0])
    assert equilibrium["reaction_resultant"] == pytest.approx([-1000.0, 0.0, 0.0])
    assert equilibrium["force_imbalance"] == pytest.approx([0.0, 0.0, 0.0], abs=1.0e-12)
    assert equilibrium["force_balance_relative_error"] < 1.0e-12


def test_newmark_uses_distributed_load_vector_and_audits_it():
    model = _tet4_model(
        [{"type": "pressure", "element": 0, "face": 0, "value": 1000.0}],
        density=6.0,
        fixed=True,
    )
    model.analysis = AnalysisSettings.from_raw(
        {"type": "transient_dynamic", "method": "newmark", "time_step": 1.0e-3, "steps": 2}
    )
    result = NewmarkDynamicSolver().solve(model)
    assert result.status == "PASS"
    assert result.solver["load_assembly"]["distributed_load_count"] == 1
    assert result.audit.load_assembly["resultant"] == result.solver["load_assembly"]["resultant"]
    assert np.all(np.isfinite(result.displacements))


def test_zero_hz_harmonic_pressure_matches_static_solution():
    static_model = _tet4_model(
        [{"type": "pressure", "element": 0, "face": 0, "value": 1000.0}],
        density=6.0,
        fixed=True,
    )
    static_result = LinearStaticSolver().solve(static_model)
    harmonic_model = _tet4_model(
        [{"type": "pressure", "element": 0, "face": 0, "value": 1000.0}],
        density=6.0,
        fixed=True,
    )
    harmonic_model.analysis = AnalysisSettings.from_raw(
        {"type": "harmonic_response", "method": "direct_frequency", "frequencies_hz": [0.0]}
    )
    harmonic_result = HarmonicResponseSolver().solve(harmonic_model)
    assert harmonic_result.status == "PASS"
    assert np.allclose(harmonic_result.responses[0].real, static_result.displacements, rtol=1.0e-12, atol=1.0e-15)
    assert harmonic_result.solver["load_assembly"]["distributed_load_count"] == 1


def _assemble(model: FiniteElementModel) -> tuple[np.ndarray, GlobalAssembler]:
    assembler = GlobalAssembler()
    vector = assembler.assemble_loads(model, model.dof_manager())
    return vector, assembler


def _tet4_model(
    distributed_loads: list[dict[str, object]],
    *,
    density: float | None = 6.0,
    fixed: bool = False,
) -> FiniteElementModel:
    material: dict[str, object] = {"type": "isotropic_3d", "E": 1000.0, "nu": 0.25}
    if density is not None:
        material["density"] = density
    fixed_dofs = []
    if fixed:
        fixed_dofs = [
            {"node": node, "dofs": ["UX", "UY", "UZ"]}
            for node in (0, 2, 3)
        ]
    return FiniteElementModel.from_raw(
        nodes=TET4_NODES,
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "material"}],
        materials={"material": material},
        fixed_dofs=fixed_dofs,
        distributed_loads=distributed_loads,
    )


def _tet10_model(
    distributed_loads: list[dict[str, object]],
    *,
    density: float = 6.0,
    nodes: list[list[float]] | None = None,
) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=nodes or TET10_NODES,
        elements=[{"type": "TET10", "nodes": list(range(10)), "material": "material"}],
        materials={"material": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.25, "density": density}},
        distributed_loads=distributed_loads,
    )


def _shell_model(
    distributed_loads: list[dict[str, object]],
    *,
    density: float = 1.0,
    thickness: float = 0.1,
    nodes: list[list[float]] | None = None,
    nodal_loads: list[dict[str, object]] | None = None,
) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=nodes or SHELL_NODES,
        elements=[{"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "skin"}],
        materials={
            "skin": {
                "type": "shell_isotropic",
                "E": 1000.0,
                "nu": 0.25,
                "t": thickness,
                "density": density,
            }
        },
        loads=nodal_loads,
        distributed_loads=distributed_loads,
    )


def _tet4_json(distributed_loads: list[dict[str, object]]) -> dict[str, object]:
    return {
        "analysis": "linear_static",
        "nodes": TET4_NODES,
        "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "material"}],
        "materials": {
            "material": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.25, "density": 6.0}
        },
        "distributed_loads": distributed_loads,
    }


def _shell_json(distributed_loads: list[dict[str, object]]) -> dict[str, object]:
    return {
        "analysis": "linear_static",
        "nodes": SHELL_NODES,
        "elements": [{"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "skin"}],
        "materials": {"skin": {"type": "shell_isotropic", "E": 1000.0, "nu": 0.25, "t": 0.1}},
        "distributed_loads": distributed_loads,
    }
