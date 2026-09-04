"""Mechanical and integration checks for the BEAM2 element."""

import math

import numpy as np
import pytest

from solveur.core.modal import ModalAnalysisSolver
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.core.solver import LinearStaticSolver
from solveur.elements.beam.beam2 import Beam2Element
from solveur.io.schema import JsonSchemaValidator
from solveur.materials.beam import BeamSectionMaterial
from solveur.mesh.validation import MeshValidator


E = 210.0e9
NU = 0.3
G = E / (2.0 * (1.0 + NU))
A = 0.01
IY = 2.0e-6
IZ = 3.0e-6
J = 5.0e-6
RHO = 7800.0
LENGTH = 2.0


def beam_material(*, density: float = RHO) -> BeamSectionMaterial:
    return BeamSectionMaterial(E=E, G=G, A=A, Iy=IY, Iz=IZ, J=J, density=density)


def beam_model(load_dof: str = "UY", load_value: float = 1000.0) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[0.0, 0.0, 0.0], [LENGTH, 0.0, 0.0]],
        elements=[{"type": "BEAM2", "nodes": [0, 1], "material": "beam"}],
        materials={
            "beam": {
                "type": "beam_isotropic",
                "E": E,
                "nu": NU,
                "A": A,
                "Iy": IY,
                "Iz": IZ,
                "J": J,
                "density": RHO,
                "reference_vector": [0.0, 1.0, 0.0],
            }
        },
        fixed_dofs=[{"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}],
        loads=[{"node": 1, "dof": load_dof, "value": load_value}],
    )


def modal_beam_model() -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        analysis={"type": "modal", "method": "eigh", "modes": 6},
        nodes=[[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]],
        elements=[{"type": "BEAM2", "nodes": [0, 1], "material": "beam"}],
        materials={
            "beam": {
                "type": "beam_isotropic",
                "E": E,
                "nu": NU,
                "A": A,
                "Iy": IY,
                "Iz": IZ,
                "J": J,
                "density": RHO,
                "reference_vector": [0.0, 1.0, 0.0],
            }
        },
        fixed_dofs=[{"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}],
    )


def test_beam2_stiffness_is_symmetric_with_six_rigid_modes() -> None:
    element = Beam2Element(beam_material())
    stiffness = element.stiffness(np.array([[0.0, 0.0, 0.0], [LENGTH, 0.0, 0.0]]))
    eigenvalues = np.linalg.eigvalsh(stiffness)
    tolerance = np.max(np.abs(eigenvalues)) * 1.0e-10
    assert stiffness.shape == (12, 12)
    assert np.allclose(stiffness, stiffness.T)
    assert np.count_nonzero(np.abs(eigenvalues) <= tolerance) == 6
    assert np.all(eigenvalues[6:] > 0.0)


@pytest.mark.parametrize(
    ("dof", "inertia", "rotation_dof", "rotation_sign"),
    [("UY", IZ, "RZ", 1.0), ("UZ", IY, "RY", -1.0)],
)
def test_beam2_cantilever_matches_timoshenko_tip_solution(
    dof: str, inertia: float, rotation_dof: str, rotation_sign: float
) -> None:
    force = 1000.0
    result = LinearStaticSolver().solve(beam_model(dof, force))
    tip = result.dofs.index(1, dof)
    rotation = result.dofs.index(1, rotation_dof)
    kappa = 5.0 / 6.0
    expected_displacement = force * LENGTH**3 / (3.0 * E * inertia) + force * LENGTH / (kappa * G * A)
    expected_rotation = rotation_sign * force * LENGTH**2 / (2.0 * E * inertia)
    assert result.displacements[tip] == pytest.approx(expected_displacement, rel=1.0e-12)
    assert result.displacements[rotation] == pytest.approx(expected_rotation, rel=1.0e-12)
    assert result.mesh_report.status == "PASS"


def test_beam2_axial_and_torsional_compliance() -> None:
    axial_force = 2000.0
    axial = LinearStaticSolver().solve(beam_model("UX", axial_force))
    torque = 500.0
    torsion = LinearStaticSolver().solve(beam_model("RX", torque))
    assert axial.displacements[axial.dofs.index(1, "UX")] == pytest.approx(
        axial_force * LENGTH / (E * A), rel=1.0e-12
    )
    assert torsion.displacements[torsion.dofs.index(1, "RX")] == pytest.approx(
        torque * LENGTH / (G * J), rel=1.0e-12
    )


def test_beam2_consistent_mass_has_total_translational_mass_and_is_rotation_invariant() -> None:
    element = Beam2Element(beam_material())
    local_coords = np.array([[0.0, 0.0, 0.0], [LENGTH, 0.0, 0.0]])
    rotated_coords = np.array([[1.0, -2.0, 0.5], [1.0, -2.0, 0.5 + LENGTH]])
    local_mass = element.mass(local_coords)
    rotated_mass = element.mass(rotated_coords)
    rigid_x = np.zeros(12)
    rigid_x[[0, 6]] = 1.0
    rigid_z = np.zeros(12)
    rigid_z[[2, 8]] = 1.0
    expected_mass = RHO * A * LENGTH
    assert rigid_x @ local_mass @ rigid_x == pytest.approx(expected_mass)
    assert rigid_z @ rotated_mass @ rigid_z == pytest.approx(expected_mass)
    assert np.all(np.linalg.eigvalsh(local_mass) > 0.0)
    assert local_mass[1, 5] != 0.0
    assert local_mass[2, 4] != 0.0


def test_beam2_modal_bending_and_torsion_match_slender_beam_references() -> None:
    result = ModalAnalysisSolver().solve(modal_beam_model())
    expected_bending = sorted(
        (1.875104068711961**2) / (2.0 * math.pi * 10.0**2) * math.sqrt(E * inertia / (RHO * A))
        for inertia in (IY, IZ)
    )
    # One linear torsion element has k = GJ/L and m_tip = rho J L / 3.
    expected_torsion = math.sqrt(3.0 * G / (RHO * 10.0**2)) / (2.0 * math.pi)
    assert result.frequencies_hz[:2] == pytest.approx(expected_bending, rel=1.0e-2)
    assert result.frequencies_hz[4] == pytest.approx(expected_torsion, rel=1.0e-12)
    assert result.solver["max_relative_residual"] <= 1.0e-10


def test_beam2_postprocessing_reports_local_end_equilibrium() -> None:
    force = 1000.0
    result = LinearStaticSolver().solve(beam_model("UY", force))
    recovered = result.element_results[0]
    node_1 = recovered["local_end_forces"]["node_1"]
    node_2 = recovered["local_end_forces"]["node_2"]
    assert recovered["type"] == "BEAM2"
    assert recovered["length"] == pytest.approx(LENGTH)
    assert node_1[1] == pytest.approx(-force)
    assert node_2[1] == pytest.approx(force)
    assert node_1[5] == pytest.approx(-force * LENGTH)
    assert node_2[5] == pytest.approx(0.0, abs=1.0e-9)
    assert result.audit.post_results[0]["calculation_frame"] == "beam2_local"


def test_beam2_uniform_line_load_matches_timoshenko_cantilever_solution() -> None:
    load = 750.0
    model = beam_model()
    model.loads = []
    model.distributed_loads = FiniteElementModel.from_raw(
        nodes=[[0.0, 0.0, 0.0], [LENGTH, 0.0, 0.0]],
        elements=[{"type": "BEAM2", "nodes": [0, 1], "material": "beam"}],
        materials=model.materials,
        distributed_loads=[
            {"type": "line_load", "element": 0, "value": [0.0, load, 0.0], "coordinate_system": "local"}
        ],
    ).distributed_loads
    result = LinearStaticSolver().solve(model)
    expected = load * LENGTH**4 / (8.0 * E * IZ)
    expected += load * LENGTH**2 / (2.0 * (5.0 / 6.0) * G * A)
    assert result.displacements[result.dofs.index(1, "UY")] == pytest.approx(expected, rel=1.0e-12)
    assembly = result.solver["load_assembly"]
    assert assembly["resultant"] == pytest.approx([0.0, load * LENGTH, 0.0])
    assert assembly["moment_about_origin"] == pytest.approx([0.0, 0.0, load * LENGTH**2 / 2.0])


def test_beam2_schema_and_mesh_reject_invalid_sections_and_geometry() -> None:
    data = {
        "analysis": "linear_static",
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        "elements": [{"type": "BEAM2", "nodes": [0, 1], "material": "beam"}],
        "materials": {"beam": {"type": "beam_isotropic", "E": E, "A": A, "Iy": IY, "Iz": IZ, "J": J}},
    }
    with pytest.raises(InputValidationError, match="requires G or nu"):
        JsonSchemaValidator().validate(data)
    model = beam_model()
    model.nodes[1] = model.nodes[0]
    report = MeshValidator().validate(model)
    assert report.status == "FAIL"
    assert any("BEAM2 length" in message for message in report.errors)


def test_beam2_rejects_reference_vector_parallel_to_axis() -> None:
    model = beam_model()
    model.materials["beam"]["reference_vector"] = [1.0, 0.0, 0.0]
    report = MeshValidator().validate(model)
    assert report.status == "FAIL"
    assert any("parallel" in message for message in report.errors)
