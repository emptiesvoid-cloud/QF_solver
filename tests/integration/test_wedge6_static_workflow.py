"""Targeted WP08 tests for the experimental WEDGE6 static vertical slice."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from solveur.api import import_gmsh_model, solve_model
from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.core.model import FiniteElementModel
from solveur.io.evidence_writer import EvidenceBundleWriter
from solveur.io.json_reader import JsonModelReader
from solveur.loads.entities import BodyLoad, SurfaceLoad
from solveur.loads.integration import DistributedLoadIntegrator
from solveur.mesh.validation import MeshValidator


NODES = [
    [0.0, 0.0, 0.0],
    [2.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
    [2.0, 0.0, 1.0],
    [0.0, 1.0, 1.0],
]
MATERIALS = {"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}}


def _model(
    *,
    nodes: list[list[float]] | None = None,
    elements: list[dict[str, object]] | None = None,
    fixed_dofs: list[dict[str, object]] | None = None,
    loads: list[dict[str, object]] | None = None,
    distributed_loads: list[dict[str, object]] | None = None,
    multipoint_constraints: list[dict[str, object]] | None = None,
) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=nodes or NODES,
        elements=elements or [{"type": "WEDGE6", "nodes": list(range(6)), "material": "steel"}],
        materials=MATERIALS,
        fixed_dofs=fixed_dofs,
        loads=loads,
        distributed_loads=distributed_loads,
        multipoint_constraints=multipoint_constraints,
        analysis="linear_static",
    )


def _fixed_triangle() -> list[dict[str, object]]:
    return [{"node": index, "dofs": ["UX", "UY", "UZ"]} for index in range(3)]


def _integrated_resultant(load: object, model: FiniteElementModel | None = None) -> np.ndarray:
    active_model = model or _model()
    integrated = DistributedLoadIntegrator().integrate_sparse(
        active_model, active_model.dof_manager(), load, 0  # type: ignore[arg-type]
    )
    return np.asarray(integrated.details["resultant"], dtype=float)


def test_gmsh_wedge6_static_workflow_maps_faces_loads_and_results(tmp_path: Path) -> None:
    pytest.importorskip("gmsh")
    mesh = BenchmarkMeshFactory().discrete_wedge6_prism(
        tmp_path / "wedge6.msh", length=2.0, width=1.0, height=1.0
    )
    setup = {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "units": {"system": "SI"},
        "verification_profile": "engineering",
        "analysis": "linear_static",
        "materials": MATERIALS,
        "groups": [
            {
                "name": "domain",
                "dimension": 3,
                "actions": [
                    {"type": "elements", "element_type": "WEDGE6", "material": "steel"},
                    {"type": "body_force", "value": [0.0, 0.0, -10.0]},
                ],
            },
            {
                "name": "tri_bottom",
                "dimension": 2,
                "actions": [{"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ"]}],
            },
            {"name": "tri_top", "dimension": 2, "actions": [{"type": "pressure", "value": 2.0}]},
            {
                "name": "quad_side_12",
                "dimension": 2,
                "actions": [{"type": "surface_traction", "value": [0.0, 0.0, -3.0]}],
            },
            {
                "name": "loaded_node",
                "dimension": 0,
                "actions": [{"type": "nodal_load", "dof": "UX", "value": 1.0}],
            },
        ],
    }
    setup_path = tmp_path / "wedge6.setup.json"
    setup_path.write_text(json.dumps(setup), encoding="utf-8")

    imported = import_gmsh_model(mesh, setup_path)
    assert imported.report.status == "WARNING"
    assert imported.report.element_family == "WEDGE6"
    assert imported.report.orientation_repairs == 0
    assert imported.report.action_counts == {
        "body_force": 1,
        "elements": 1,
        "fixed_dofs": 3,
        "nodal_load": 1,
        "pressure": 1,
        "surface_traction": 1,
    }
    assert [load.face for load in imported.model.distributed_loads if load.type != "body_force"] == [1, 2]

    result = solve_model(imported.model, enforce_policy=False)
    assert result.status == "PASS"
    assert np.isfinite(result.displacements).all()
    assert len(result.element_results) == 1
    assert len(result.element_results[0]["integration_points"]) == 6
    assert len(result.element_results[0]["nodal_results"]) == 6
    assert np.isfinite(float(result.element_results[0]["strain_energy"]))
    assert float(result.element_results[0]["strain_energy"]) >= 0.0
    assert result.audit is not None
    assert result.audit.equilibrium["force_balance_relative_error"] < 1.0e-12
    assert result.audit.equilibrium["moment_balance_relative_error"] < 1.0e-12
    json.dumps(result.to_dict())


def test_wedge6_tri_quad_surface_and_body_resultants_use_canonical_faces() -> None:
    assert _integrated_resultant(BodyLoad((0.0, 0.0, -10.0))) == pytest.approx((0.0, 0.0, -10.0))
    assert _integrated_resultant(SurfaceLoad(0, "pressure", 2.0, face=1)) == pytest.approx((0.0, 0.0, -2.0))
    assert _integrated_resultant(SurfaceLoad(0, "pressure", 3.0, face=2)) == pytest.approx((0.0, 6.0, 0.0))
    assert _integrated_resultant(SurfaceLoad(0, "surface_traction", (0.0, 0.0, -3.0), face=2)) == pytest.approx(
        (0.0, 0.0, -6.0)
    )


def test_wedge6_multi_element_static_patch_and_reactions() -> None:
    nodes = NODES + [[0.0, 0.0, 2.0], [2.0, 0.0, 2.0], [0.0, 1.0, 2.0]]
    elements = [
        {"type": "WEDGE6", "nodes": [0, 1, 2, 3, 4, 5], "material": "steel"},
        {"type": "WEDGE6", "nodes": [3, 4, 5, 6, 7, 8], "material": "steel"},
    ]
    model = _model(
        nodes=nodes,
        elements=elements,
        fixed_dofs=_fixed_triangle(),
        loads=[{"node": 6, "dof": "UX", "value": 1.0}, {"node": 7, "dof": "UX", "value": 1.0}],
        distributed_loads=[{"type": "pressure", "element": 1, "face": 1, "value": 10.0}],
    )
    result = solve_model(model, enforce_policy=False)
    assert result.status == "PASS"
    assert result.element_count == 2
    assert np.isfinite(result.displacements).all()
    assert result.audit is not None
    assert result.audit.equilibrium["force_balance_relative_error"] < 1.0e-12
    assert result.audit.equilibrium["moment_balance_relative_error"] < 1.0e-12


def test_wedge6_existing_constraint_path_supports_prescribed_displacement() -> None:
    model = _model(
        fixed_dofs=_fixed_triangle(),
        multipoint_constraints=[
            {
                "name": "prescribed_relative_uz",
                "terms": [
                    {"node": 5, "dof": "UZ", "coefficient": 1.0},
                    {"node": 3, "dof": "UZ", "coefficient": -1.0},
                ],
                "value": 1.0e-6,
            }
        ],
    )
    result = solve_model(model, enforce_policy=False)
    assert result.status == "PASS"
    assert result.audit is not None
    assert result.audit.equilibrium["constraint_forces"]["constraint_violation_max_abs"] == pytest.approx(0.0)


def test_wedge6_invalid_surface_face_fails_before_solve() -> None:
    model = _model(
        fixed_dofs=_fixed_triangle(),
        distributed_loads=[{"type": "pressure", "element": 0, "face": 5, "value": 1.0}],
    )
    report = MeshValidator().validate(model)
    assert report.status == "FAIL"
    assert any("face must be an integer from 0 to 4" in error for error in report.errors)


def test_wedge6_evidence_input_roundtrip_preserves_distributed_loads(tmp_path: Path) -> None:
    model = _model(
        fixed_dofs=_fixed_triangle(),
        distributed_loads=[{"type": "body_force", "value": [0.0, 0.0, -2.0]}],
    )
    result = solve_model(model, enforce_policy=False)
    bundle = EvidenceBundleWriter().write(
        model=model,
        result=result,
        directory=tmp_path / "evidence",
        include_csv=False,
    )
    restored = JsonModelReader().read(bundle["input"])
    assert restored.distributed_loads == model.distributed_loads
    assert bundle["vtu"].is_file()
