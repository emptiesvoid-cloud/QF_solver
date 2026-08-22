import numpy as np
import pytest

from solveur.compat.mitc4.element import MITC4Element
from solveur.compat.mitc4.material import ShellMaterial
from solveur.compat.mitc4.mesh import MeshFactory

from solveur.api import check_mesh, solve_model
from solveur.core.model import FiniteElementModel
from solveur.core.qualification import model_maturity
from solveur.io.schema import JsonSchemaValidator
from solveur.materials import ClassicalLaminate, LaminaPly, LaminateShellMaterial, OrthotropicLamina
from solveur.materials.factory import MaterialFactory
from solveur.post.stress import StressPostProcessor
from solveur.verification.traceability import scope_for_model


COORDS = np.array([[0.0, 0.0, 0.0], [1.2, 0.0, 0.0], [1.2, 0.8, 0.0], [0.0, 0.8, 0.0]])


def ply_definition(angle: float, *, isotropic: bool = False) -> dict[str, object]:
    if isotropic:
        young = 70.0e9
        poisson = 0.3
        shear = young / (2.0 * (1.0 + poisson))
        return {
            "name": f"iso-{angle:g}",
            "E1": young,
            "E2": young,
            "nu12": poisson,
            "G12": shear,
            "G13": shear,
            "G23": shear,
            "density": 2700.0,
            "thickness": 0.01,
            "angle_deg": angle,
        }
    return {
        "name": f"carbon-{angle:g}",
        "E1": 135.0e9,
        "E2": 10.0e9,
        "nu12": 0.3,
        "G12": 5.0e9,
        "G13": 4.5e9,
        "G23": 3.8e9,
        "density": 1600.0,
        "thickness": 0.125e-3,
        "angle_deg": angle,
    }


def material_definition(angles: list[float], *, isotropic: bool = False) -> dict[str, object]:
    return {
        "type": "shell_laminate",
        "plies": [ply_definition(angle, isotropic=isotropic) for angle in angles],
        "shear_factor": 5.0 / 6.0,
        "drilling_scale": 1.0e-4,
    }


def model(angles: list[float], *, analysis: str = "linear_static") -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=COORDS.tolist(),
        elements=[{"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "laminate"}],
        materials={"laminate": material_definition(angles)},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]} for node in (0, 3)],
        loads=[{"node": 1, "dof": "UX", "value": 1000.0}, {"node": 2, "dof": "UX", "value": 1000.0}],
        analysis={"type": analysis, "modes": 1} if analysis == "modal" else analysis,
    )


def test_single_equivalent_isotropic_ply_matches_validated_isotropic_element():
    definition = material_definition([0.0], isotropic=True)
    laminate = MaterialFactory.create(definition)
    assert isinstance(laminate, LaminateShellMaterial)
    ply = definition["plies"][0]
    isotropic = ShellMaterial(
        E=float(ply["E1"]),
        nu=float(ply["nu12"]),
        t=float(ply["thickness"]),
        density=float(ply["density"]),
    )
    reference = MITC4Element(isotropic)
    candidate = MITC4Element(laminate)
    assert np.allclose(candidate.stiffness(COORDS), reference.stiffness(COORDS), rtol=2.0e-14, atol=1.0e-5)
    assert np.allclose(candidate.stiffness_components(COORDS)["coupling"], 0.0, atol=1.0e-12)


def test_unsymmetric_laminate_adds_symmetric_membrane_bending_coupling():
    material = MaterialFactory.create(material_definition([0.0, 90.0]))
    assert isinstance(material, LaminateShellMaterial)
    element = MITC4Element(material)
    components = element.stiffness_components(COORDS)
    assert np.linalg.norm(material.coupling_matrix) > 0.0
    assert np.linalg.norm(components["coupling"]) > 0.0
    assert np.allclose(components["coupling"], components["coupling"].T)
    stiffness = element.stiffness(COORDS)
    assert np.allclose(stiffness, stiffness.T)
    displacement = np.linspace(-1.0e-4, 2.0e-4, 24)
    assert 0.5 * displacement @ stiffness @ displacement > 0.0


def test_transverse_shear_matrix_is_positive_and_orientation_sensitive():
    lamina = OrthotropicLamina(135.0e9, 10.0e9, 0.3, 5.0e9, G13=6.0e9, G23=3.0e9)
    zero = lamina.transformed_transverse_shear(0.0)
    ninety = lamina.transformed_transverse_shear(90.0)
    assert np.allclose(zero, np.diag([6.0e9, 3.0e9]))
    assert np.allclose(ninety, np.diag([3.0e9, 6.0e9]), rtol=0.0, atol=1.0e-5)
    assert np.all(np.linalg.eigvalsh(zero) > 0.0)


def test_static_laminate_model_solves_and_reports_ply_stresses():
    candidate = model([0.0, 90.0, 90.0, 0.0])
    report = check_mesh(candidate)
    assert report.status in {"PASS", "WARNING"}
    result = solve_model(candidate)
    assert result.status == "PASS"
    assert np.all(np.isfinite(result.displacements))
    element = result.element_results[0]
    assert len(element["ply_results"]) == 12
    assert {item["location"] for item in element["ply_results"]} == {"lower", "middle", "upper"}
    assert len(element["shell_faces"]) == 2
    assert [item["section_position"] for item in element["shell_faces"]] == ["shell_down", "shell_up"]
    sections = element["shell_sections"]
    assert sections["axis"] == "local_e3"
    assert sections["shell_down"]["z"] < 0.0
    assert sections["shell_up"]["z"] > 0.0
    assert len(sections["shell_middle"]) == 2
    assert sections["middle_is_interface"] is True


def test_postprocessor_resultants_include_abd_coupling():
    candidate = model([0.0, 90.0])
    dofs = candidate.dof_manager()
    displacement = np.linspace(-2.0e-4, 3.0e-4, dofs.ndof)
    result = StressPostProcessor().element_results(candidate, dofs, displacement)[0]
    material = MaterialFactory.create(candidate.materials["laminate"])
    strain = np.asarray(result["membrane_strain"])
    curvature = np.asarray(result["curvature"])
    expected_n, expected_m = material.laminate.resultants(strain, curvature)
    assert np.allclose(result["membrane_force"], expected_n)
    assert np.allclose(result["bending_moment"], expected_m)


def test_schema_factory_maturity_and_scope_keep_laminate_experimental():
    definition = material_definition([0.0, 90.0])
    raw = {
        "nodes": COORDS.tolist(),
        "elements": [{"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "laminate"}],
        "materials": {"laminate": definition},
    }
    JsonSchemaValidator().validate(raw)
    candidate = model([0.0, 90.0])
    assert model_maturity(candidate)["overall"] == "experimental"
    assert scope_for_model(candidate) is None


def test_dynamic_laminate_with_positive_ply_density_is_admitted_for_internal_vnv():
    report = check_mesh(model([0.0, 90.0], analysis="modal"))
    assert report.status == "PASS"
    assert report.errors == []


def test_laminate_schema_rejects_missing_transverse_shear():
    definition = material_definition([0.0])
    del definition["plies"][0]["G13"]
    raw = {
        "nodes": COORDS.tolist(),
        "elements": [{"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "laminate"}],
        "materials": {"laminate": definition},
    }
    with pytest.raises(Exception, match="G13"):
        JsonSchemaValidator().validate(raw)


def test_laminate_shell_requires_transverse_shear_for_every_ply():
    lamina = OrthotropicLamina(135.0e9, 10.0e9, 0.3, 5.0e9)
    stack = ClassicalLaminate((LaminaPly(lamina, 0.125e-3, 0.0),))
    with pytest.raises(ValueError, match="G13 and G23"):
        LaminateShellMaterial(stack)


@pytest.mark.parametrize("thickness_ratio", [1.0e-2, 1.0e-3])
def test_unidirectional_laminate_avoids_shear_locking(thickness_ratio: float):
    length = 1.0
    width = 0.1
    thickness = length * thickness_ratio
    force = 1.0
    mesh = MeshFactory.rectangular_plate(16, 2, length, width)
    ply = ply_definition(0.0)
    ply["thickness"] = thickness / 4.0
    definition = {"type": "shell_laminate", "plies": [dict(ply, name=f"ply-{index}") for index in range(4)]}
    left = [index for index, point in enumerate(mesh.nodes) if abs(point[0]) <= 1.0e-12]
    tip = [index for index, point in enumerate(mesh.nodes) if abs(point[0] - length) <= 1.0e-12]
    candidate = FiniteElementModel.from_raw(
        nodes=mesh.nodes,
        elements=[{"type": "MITC4", "nodes": quad, "material": "laminate"} for quad in mesh.quads],
        materials={"laminate": definition},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]} for node in left],
        loads=[{"node": node, "dof": "UZ", "value": -force / len(tip)} for node in tip],
    )
    result = solve_model(candidate)
    displacement = np.mean([result.displacements[result.dofs.index(node, "UZ")] for node in tip])
    material = MaterialFactory.create(definition)
    bending = material.bending_matrix
    effective_bending = bending[0, 0] - bending[0, 1] ** 2 / bending[1, 1]
    effective_shear = material.shear_matrix[0, 0]
    reference = -force * (
        length**3 / (3.0 * effective_bending * width) + length / (effective_shear * width)
    )
    assert displacement / reference >= 0.99
    assert displacement == pytest.approx(reference, rel=3.0e-3)


def test_laminate_element_is_objective_under_global_rotation():
    material = MaterialFactory.create(material_definition([0.0, 45.0, -45.0, 90.0]))
    angle = np.deg2rad(37.0)
    rotation = np.array(
        [
            [np.cos(angle), -np.sin(angle), 0.0],
            [np.sin(angle), np.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    reference = MITC4Element(material).stiffness(COORDS)
    rotated = MITC4Element(material).stiffness(COORDS @ rotation.T)
    assert np.allclose(np.linalg.eigvalsh(reference), np.linalg.eigvalsh(rotated), rtol=2.0e-10, atol=1.0e-5)


def test_folded_laminate_shell_assembles_and_solves():
    nodes = [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 0.8, 0.0],
        [0.0, 0.8, 0.0],
        [1.8, 0.0, 0.4],
        [1.8, 0.8, 0.4],
    ]
    definition = material_definition([0.0, 45.0, -45.0, 90.0])
    for ply in definition["plies"]:
        ply["thickness"] = 0.01
    candidate = FiniteElementModel.from_raw(
        nodes=nodes,
        elements=[
            {"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "laminate"},
            {"type": "MITC4", "nodes": [1, 4, 5, 2], "material": "laminate"},
        ],
        materials={"laminate": definition},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]} for node in (0, 3)],
        loads=[{"node": node, "dof": "UZ", "value": -100.0} for node in (4, 5)],
    )
    result = solve_model(candidate)
    assert result.status == "PASS"
    assert np.all(np.isfinite(result.displacements))
    assert len(result.element_results) == 2
    assert all(len(item["ply_results"]) == 12 for item in result.element_results)


def _with_allowables(definition: dict[str, object]) -> dict[str, object]:
    for ply in definition["plies"]:
        ply["strengths"] = {
            "Xt": 1500.0e6,
            "Xc": 1200.0e6,
            "Yt": 50.0e6,
            "Yc": 200.0e6,
            "S12": 75.0e6,
        }
        ply["strain_allowables"] = {
            "e1t": 0.015,
            "e1c": 0.012,
            "e2t": 0.005,
            "e2c": 0.02,
            "g12": 0.03,
        }
    return definition


def test_schema_and_factory_accept_documented_ply_allowables():
    definition = _with_allowables(material_definition([0.0, 90.0]))
    raw = {
        "nodes": COORDS.tolist(),
        "elements": [{"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "laminate"}],
        "materials": {"laminate": definition},
    }
    JsonSchemaValidator().validate(raw)
    material = MaterialFactory.create(definition)
    assert isinstance(material, LaminateShellMaterial)
    assert material.laminate.plies[0].strengths.Xt == pytest.approx(1500.0e6)
    assert material.laminate.plies[1].strain_allowables.g12 == pytest.approx(0.03)


def test_postprocessor_reports_failure_indices_and_critical_ply():
    candidate = model([0.0, 90.0, 90.0, 0.0])
    candidate.materials["laminate"] = _with_allowables(candidate.materials["laminate"])
    dofs = candidate.dof_manager()
    displacement = np.zeros(dofs.ndof)
    for node in (1, 2):
        displacement[dofs.index(node, "UX")] = 2.0e-3
    result = StressPostProcessor().element_results(candidate, dofs, displacement)[0]
    assert result["failure_summary"]["interpretation"] == "non_degrading_first_ply_indicator"
    assert set(result["failure_summary"]["critical_by_criterion"]) == {
        "maximum_stress",
        "maximum_strain",
        "tsai_hill",
        "tsai_wu",
    }
    for point in result["ply_results"]:
        assert set(point["failure_indices"]) == {
            "maximum_stress",
            "maximum_strain",
            "tsai_hill",
            "tsai_wu",
        }


def test_failure_prediction_does_not_degrade_linear_stiffness():
    plain = MaterialFactory.create(material_definition([0.0]))
    assessed = MaterialFactory.create(_with_allowables(material_definition([0.0])))
    assert np.array_equal(MITC4Element(plain).stiffness(COORDS), MITC4Element(assessed).stiffness(COORDS))


@pytest.mark.parametrize(
    "mutator,match",
    [
        (lambda ply: ply.update(strengths={"Xt": 1.0}), "Xc"),
        (
            lambda ply: ply.update(
                strengths={"Xt": 1.0, "Xc": 1.0, "Yt": 1.0, "Yc": 1.0, "S12": -1.0}
            ),
            "S12",
        ),
        (lambda ply: ply.update(strain_allowables={"e1t": 1.0}), "e1c"),
    ],
)
def test_schema_rejects_incomplete_or_invalid_allowables(mutator, match: str):
    definition = material_definition([0.0])
    mutator(definition["plies"][0])
    raw = {
        "nodes": COORDS.tolist(),
        "elements": [{"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "laminate"}],
        "materials": {"laminate": definition},
    }
    with pytest.raises(Exception, match=match):
        JsonSchemaValidator().validate(raw)
