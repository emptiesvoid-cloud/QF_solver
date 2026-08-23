from __future__ import annotations

import numpy as np

from solveur.core.analysis import AnalysisSettings
from solveur.core.model import BoundaryCondition, ElementDefinition, FiniteElementModel, NodalLoad
from solveur.elements.discrete import ConcentratedMass, SpringDefinition
from solveur.loads.entities import BodyLoad, EdgeLoad, GravityLoad, LineLoad, SurfaceLoad
from solveur.mesh.validation import MeshValidator


def _model(elements: list[ElementDefinition], *, nodes: np.ndarray | None = None, analysis: str = "linear_static") -> FiniteElementModel:
    return FiniteElementModel(
        nodes=np.asarray(nodes if nodes is not None else [[0.0, 0.0, 0.0]] * 4),
        elements=elements,
        materials={"solid": {"type": "isotropic_3d", "E": 1.0, "nu": 0.3}},
        analysis=AnalysisSettings.from_raw(analysis),
    )


def test_mesh_validator_reports_empty_nonfinite_and_duplicate_nodes() -> None:
    errors: list[str] = []
    MeshValidator._check_nodes(_model([] , nodes=np.empty((0, 3))), errors)
    assert "no node" in errors[0]
    errors = []
    MeshValidator._check_nodes(_model([], nodes=np.asarray([[0.0, 0.0, 0.0], [np.nan, 0.0, 0.0]])), errors)
    assert any("non-finite" in item for item in errors)
    errors = []
    MeshValidator._check_nodes(_model([], nodes=np.zeros((2, 3))), errors)
    assert any("duplicate" in item for item in errors)


def test_mesh_validator_reports_element_connectivity_contracts() -> None:
    validator = MeshValidator()
    errors: list[str] = []
    warnings: list[str] = []
    validator._check_elements(_model([ElementDefinition("UNKNOWN", (0,), "solid")]), errors, warnings)
    assert errors
    errors = []
    validator._check_elements(_model([ElementDefinition("TET4", (0, 1, 2), "solid")]), errors, warnings)
    assert "expects" in errors[0]
    errors = []
    validator._check_elements(_model([ElementDefinition("TET4", (0, 1, 1, 3), "solid")]), errors, warnings)
    assert "repeated" in errors[0]
    errors = []
    validator._check_elements(_model([ElementDefinition("TET4", (0, 1, 2, 9), "solid")]), errors, warnings)
    assert "outside" in errors[0]


def test_mesh_validator_reports_missing_and_incompatible_materials() -> None:
    errors: list[str] = []
    model = _model([ElementDefinition("TET4", (0, 1, 2, 3), "missing")])
    MeshValidator._check_materials(model, errors)
    assert "unknown material" in errors[0]
    errors = []
    model = _model([ElementDefinition("TET4", (0, 1, 2, 3), "solid")])
    model.materials["solid"] = {"type": "shell_isotropic", "E": 1.0, "nu": 0.3}
    MeshValidator._check_materials(model, errors)
    assert "expected" in errors[0]


def test_mesh_validator_reports_dynamic_density_and_nonlinear_element_limits() -> None:
    errors: list[str] = []
    beam = ElementDefinition("BEAM2", (0, 1), "solid")
    MeshValidator._check_analysis_requirements(_model([beam], analysis="nonlinear_static"), errors)
    assert "TET4/TET10" in errors[0]
    errors = []
    tet = ElementDefinition("TET4", (0, 1, 2, 3), "solid")
    model = _model([tet], analysis="modal")
    MeshValidator._check_analysis_requirements(model, errors)
    assert "positive density" in errors[0]


def test_mesh_validator_covers_distributed_load_rejections() -> None:
    elements = [
        ElementDefinition("TET4", (0, 1, 2, 3), "solid"),
        ElementDefinition("MITC4", (0, 1, 2, 3), "solid"),
        ElementDefinition("BEAM2", (0, 1), "solid"),
    ]
    model = _model(elements)
    model.materials["solid"]["density"] = 1.0
    model.distributed_loads = [
        GravityLoad((np.nan, 0.0, 0.0), elements=(0,)),
        BodyLoad((1.0, 0.0, 0.0), elements=(0,), coordinate_system="bad"),
        BodyLoad((1.0, 0.0, 0.0), elements=(0,), coordinate_system="local"),
        SurfaceLoad(99, "pressure", 1.0),
        SurfaceLoad(0, "pressure", 1.0, face=4, follower=True, coordinate_system="bad"),
        SurfaceLoad(0, "surface_traction", (1.0, 2.0, 3.0), face=4),
        EdgeLoad(0, 0, (1.0, 2.0, 3.0)),
        EdgeLoad(1, 4, (np.nan, 0.0, 0.0), coordinate_system="bad"),
        LineLoad(1, (np.nan, 0.0, 0.0), coordinate_system="bad"),
        object(),
    ]
    errors: list[str] = []
    MeshValidator._check_distributed_loads(model, errors)
    assert len(errors) >= 10
    assert any("unsupported distributed load object" in item for item in errors)


def test_mesh_validator_covers_discrete_entity_rejections() -> None:
    model = _model([])
    model.springs = [
        SpringDefinition(9, ("UX",), ((1.0,),)),
        SpringDefinition(0, ("UX",), ((1.0,),), node_b=0),
        SpringDefinition(0, ("UX", "UX"), ((1.0, 0.0), (0.0, 1.0))),
        SpringDefinition(0, ("UX",), ((np.nan,),)),
    ]
    model.concentrated_masses = [ConcentratedMass(9, 1.0), ConcentratedMass(0, -1.0)]
    errors: list[str] = []
    MeshValidator._check_discrete_entities(model, errors)
    assert len(errors) >= 5
    assert any("outside" in item for item in errors)
    assert any("strictly positive" in item for item in errors)


def test_mesh_validator_element_geometry_reports_shell_and_beam_failures() -> None:
    validator = MeshValidator()
    errors: list[str] = []
    validator._check_element_geometry(0, "MITC4", np.zeros((4, 3)), errors, [])
    validator._check_element_geometry(1, "MITC3", np.zeros((3, 3)), errors, [])
    validator._check_element_geometry(2, "BEAM2", np.zeros((2, 3)), errors, [])
    assert len(errors) == 3
    assert any("MITC4" in item for item in errors)
    assert any("MITC3" in item for item in errors)
    assert any("BEAM2" in item for item in errors)


def test_mesh_validator_checks_invalid_nodal_conditions_and_component_counts() -> None:
    model = _model([])
    model.fixed_dofs = [BoundaryCondition(99, ("UX",)), BoundaryCondition(0, ("UX",))]
    model.loads = [NodalLoad(99, "UX", 1.0), NodalLoad(0, "UX", 1.0)]
    class Dofs:
        ndof = 12

        @staticmethod
        def has(node, dof):
            return node == 0 and dof == "UX"

    errors: list[str] = []
    warnings: list[str] = []
    MeshValidator._check_conditions(model, Dofs(), errors, warnings)
    assert any("invalid node" in item for item in errors)
    assert any("Fewer than three" in item for item in warnings)
    details = {"components": [{"index": 0, "nodes": [0, 1], "element_types": {"TET4": 1}}]}
    MeshValidator._check_component_constraints(model, Dofs(), details, warnings)
    assert details["components"][0]["fixed_dof_count"] == 1
    assert details["components"][0]["load_count"] == 1


def test_mesh_validator_skips_mechanical_rank_for_large_models() -> None:
    model = _model([])
    details: dict[str, object] = {}
    warnings: list[str] = []
    class LargeDofs:
        ndof = 181

    MeshValidator._check_mechanical_rank(model, LargeDofs(), details, warnings)
    assert details["mechanical_rank"] == {"checked": False, "reason": "model too large", "ndof": 181}
