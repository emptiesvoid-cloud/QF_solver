import numpy as np

from solveur.core.model import FiniteElementModel
from solveur.mesh.quality import MeshQuality, MeshQualityThresholds
from solveur.mesh.validation import MeshValidator


def _tet10_validation_model():
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
    return FiniteElementModel.from_raw(
        nodes=nodes,
        elements=[{"type": "TET10", "nodes": list(range(10)), "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (0, 2, 3, 6, 7, 9)],
        loads=[{"node": 1, "dof": "UX", "value": 1000.0}],
    )


def valid_tet4_model():
    return FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": 1000.0}],
    )


def test_mesh_validation_accepts_valid_tet4():
    report = MeshValidator().validate(valid_tet4_model())
    assert report.status == "PASS"
    assert report.details["component_count"] == 1
    assert report.details["components"][0]["fixed_dof_count"] == 9
    assert report.details["components"][0]["fixed_translation_node_count"] == 3
    assert report.details["element_quality"][0]["aspect_ratio"] > 0.0
    assert report.details["mechanical_rank"]["checked"] is True
    assert report.details["mechanical_rank"]["zero_mode_count"] == 0
    assert report.to_dict()["details"]["element_types"] == {"TET4": 1}


def test_mesh_quality_cache_reuses_unchanged_geometry_and_invalidates_on_mutation(monkeypatch):
    model = valid_tet4_model()
    validator = MeshValidator()
    original = MeshQuality.tet_metrics
    calls = 0

    def counted(coords):
        nonlocal calls
        calls += 1
        return original(coords)

    monkeypatch.setattr(MeshQuality, "tet_metrics", staticmethod(counted))
    first = validator.validate(model)
    second = validator.validate(model)
    assert first.details["element_quality"] == second.details["element_quality"]
    assert calls == 1

    model.nodes[1, 0] = 1.1
    validator.validate(model)
    assert calls == 2


def test_mesh_validation_rejects_inverted_tet4():
    model = FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 2, 1, 3], "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
    )
    report = MeshValidator().validate(model)
    assert report.status == "FAIL"
    assert "volume" in report.errors[0]
    assert report.details["element_quality"][0]["quality_status"] == "FAIL"


def test_mesh_validation_rejects_incompatible_dof():
    model = FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
        fixed_dofs=[{"node": 0, "dofs": ["RX"]}],
    )
    report = MeshValidator().validate(model)
    assert report.status == "FAIL"
    assert "not active" in report.errors[0]


def test_mesh_validation_accepts_tet10():
    model = FiniteElementModel.from_raw(
        nodes=[
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
        ],
        elements=[{"type": "TET10", "nodes": list(range(10)), "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}},
        fixed_dofs=[{"node": 0, "dofs": ["UX", "UY", "UZ"]}],
    )
    report = MeshValidator().validate(model)
    assert report.status in {"PASS", "WARNING"}
    assert report.details["components"][0]["fixed_translation_node_count"] == 1
    assert report.details["mechanical_rank"]["checked"] is True
    assert report.details["mechanical_rank"]["zero_mode_count"] > 0
    quality = report.details["element_quality"][0]
    assert quality["mid_edge_deviation_ratio_max"] == 0.0
    assert np.isclose(quality["sampled_jacobian_ratio"], 1.0)


def test_mesh_validation_warns_on_misplaced_tet10_midside_node():
    model = _tet10_validation_model()
    model.nodes[4, 2] = 0.1
    report = MeshValidator().validate(model)
    quality = report.details["element_quality"][0]
    assert report.status == "WARNING"
    assert quality["mid_edge_deviation_ratio_max"] > 0.05
    assert quality["sampled_jacobian_min"] > 0.0
    assert any("midside node" in warning for warning in report.warnings)


def test_mesh_validation_rejects_curved_tet10_with_sampled_negative_jacobian():
    model = _tet10_validation_model()
    model.nodes[4, 2] = 1.0
    report = MeshValidator().validate(model)
    assert report.status == "FAIL"
    assert any("sampled Jacobian" in error for error in report.errors)
    assert report.details["element_quality"][0]["quality_status"] == "FAIL"


def test_mesh_validation_warns_on_unconstrained_component():
    model = FiniteElementModel.from_raw(
        nodes=[
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
            [3, 0, 0],
            [4, 0, 0],
            [3, 1, 0],
            [3, 0, 1],
        ],
        elements=[
            {"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"},
            {"type": "TET4", "nodes": [4, 5, 6, 7], "material": "steel"},
        ],
        materials={"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
    )
    report = MeshValidator().validate(model)
    assert report.status == "WARNING"
    assert report.details["component_count"] == 2
    assert report.details["components"][1]["fixed_dof_count"] == 0
    assert any("Component 1 has no fixed dof" in warning for warning in report.warnings)


def test_mesh_validation_reports_low_tet_quality_metrics():
    model = FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [10, 0, 0], [0, 0.1, 0], [0, 0, 0.1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
    )
    report = MeshValidator().validate(model)
    quality = report.details["element_quality"][0]
    assert report.status == "WARNING"
    assert quality["aspect_ratio"] > 20.0
    assert any("aspect ratio" in warning for warning in report.warnings)


def test_mesh_validation_reports_tet10_radius_ratio_and_thresholds():
    model = FiniteElementModel.from_raw(
        nodes=[
            [0, 0, 0],
            [10, 0, 0],
            [0, 0.1, 0],
            [0, 0, 0.1],
            [5, 0, 0],
            [5, 0.05, 0],
            [0, 0.05, 0],
            [0, 0, 0.05],
            [5, 0, 0.05],
            [0, 0.05, 0.05],
        ],
        elements=[{"type": "TET10", "nodes": list(range(10)), "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
            {"node": 6, "dofs": ["UX", "UY", "UZ"]},
            {"node": 7, "dofs": ["UX", "UY", "UZ"]},
            {"node": 9, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": 1000.0}],
    )
    report = MeshValidator().validate(model)
    quality = report.details["element_quality"][0]
    assert report.status == "WARNING"
    assert quality["quality_status"] == "WARNING"
    assert quality["radius_ratio"] < report.details["quality_thresholds"]["tet_min_radius_ratio"]
    assert "radius_ratio" in quality
    assert any("radius ratio" in warning for warning in report.warnings)


def test_mesh_validation_can_relax_quality_thresholds():
    model = FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [10, 0, 0], [0, 0.1, 0], [0, 0, 0.1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": 1000.0}],
    )
    thresholds = MeshQualityThresholds(
        tet_min_quality=0.0,
        tet_min_radius_ratio=0.0,
        tet_max_aspect_ratio=200.0,
        tet_min_relative_volume=0.0,
    )
    report = MeshValidator(thresholds).validate(model)
    assert report.status == "PASS"
    assert report.details["element_quality"][0]["quality_status"] == "PASS"
    assert report.details["quality_thresholds"]["tet_max_aspect_ratio"] == 200.0


def test_mesh_validation_reports_mitc4_planarity_metrics():
    model = FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [1, 1, 0.02], [0, 1, 0]],
        elements=[{"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "skin"}],
        materials={"skin": {"type": "shell_isotropic", "E": 1000.0, "nu": 0.25, "t": 0.1}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]},
        ],
    )
    report = MeshValidator().validate(model)
    quality = report.details["element_quality"][0]
    assert report.status == "WARNING"
    assert quality["planarity"] > 0.0
    assert any("non-planar MITC4" in warning for warning in report.warnings)


def test_mesh_validation_reports_mitc4_warpage_metrics():
    model = FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [1, 1, 0.2], [0, 1, -0.2]],
        elements=[{"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "skin"}],
        materials={"skin": {"type": "shell_isotropic", "E": 1000.0, "nu": 0.25, "t": 0.1}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]},
        ],
    )
    report = MeshValidator().validate(model)
    quality = report.details["element_quality"][0]
    assert report.status == "WARNING"
    assert quality["quality_status"] == "WARNING"
    assert quality["warpage_degrees"] > report.details["quality_thresholds"]["mitc4_max_warpage_degrees"]
    assert any("warped MITC4" in warning for warning in report.warnings)
