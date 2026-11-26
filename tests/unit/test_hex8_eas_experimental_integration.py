from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

from solveur.compatibility import preflight_model
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.elements.registry import ElementRegistry
from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.hex8_eas_experimental import (
    HEX8_EAS_EXPERIMENTAL,
    HEX8_EAS_FORMULATION_ID,
    Hex8EASExperimentalElement,
    hex8_eas_scope_errors,
)
from solveur.materials.solid import SolidMaterial
from solveur.mesh.validation import MeshValidator
from solveur.mesh.quality_contract import VALID, assess_element
from solveur.post.stress import StressPostProcessor
from solveur.io.vtu_writer import VtuResultWriter
from solveur.io.json_reader import JsonModelReader


def _unit_hex() -> np.ndarray:
    return np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
        ],
        dtype=float,
    )


def _warped_hex() -> np.ndarray:
    coords = _unit_hex()
    x, y, z = coords.T.copy()
    coords[:, 0] += 0.10 * y * z
    coords[:, 1] += 0.06 * x * z
    coords[:, 2] += 0.04 * x * y
    return coords


def _model(
    *,
    element_type: str = HEX8_EAS_EXPERIMENTAL,
    analysis: str | dict[str, object] = "linear_static",
    material_type: str = "isotropic_3d",
    coords: np.ndarray | None = None,
    nu: float = 0.3,
    fully_fixed: bool = False,
    distributed_loads: list[dict[str, object]] | None = None,
) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=(coords if coords is not None else _unit_hex()).tolist(),
        elements=[{"type": element_type, "nodes": list(range(8)), "material": "solid"}],
        materials={"solid": {"type": material_type, "E": 210.0e9, "nu": nu, "density": 7800.0}},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(8)] if fully_fixed else [],
        distributed_loads=distributed_loads or [],
        analysis=analysis,
    )


def _engineering_strain(gradient: np.ndarray) -> np.ndarray:
    return np.asarray(
        [
            gradient[0, 0],
            gradient[1, 1],
            gradient[2, 2],
            gradient[0, 1] + gradient[1, 0],
            gradient[1, 2] + gradient[2, 1],
            gradient[0, 2] + gradient[2, 0],
        ],
        dtype=float,
    )


def test_hex8_eas_explicit_registry_assembly_and_default_hex8_are_separate() -> None:
    material = SolidMaterial(E=210.0e9, nu=0.3)
    eas_model = _model(fully_fixed=True, distributed_loads=[{"type": "body_force", "value": [1.0, 0.0, 0.0], "elements": [0]}])
    dofs = eas_model.dof_manager()
    spec = ElementRegistry.get(HEX8_EAS_EXPERIMENTAL)
    assert spec.factory(material).__class__ is Hex8EASExperimentalElement
    eas_local = spec.factory(material).stiffness(eas_model.nodes)
    assembled = GlobalAssembler().assemble_stiffness(eas_model, dofs).toarray()
    assert np.allclose(assembled, eas_local, rtol=2.0e-14, atol=2.0e-6)
    for coords in (_unit_hex(), _warped_hex()):
        for poisson in (0.3, 0.4999):
            assembly_model = _model(coords=coords, nu=poisson, fully_fixed=True)
            assembly_dofs = assembly_model.dof_manager()
            local = ElementRegistry.get(HEX8_EAS_EXPERIMENTAL).factory(
                SolidMaterial(E=210.0e9, nu=poisson)
            ).stiffness(coords)
            global_matrix = GlobalAssembler().assemble_stiffness(assembly_model, assembly_dofs).toarray()
            assert np.allclose(global_matrix, local, rtol=2.0e-14, atol=2.0e-6)
    with pytest.raises(InputValidationError, match="does not provide a mass matrix"):
        GlobalAssembler().assemble_stiffness_and_mass(eas_model, dofs)
    assert np.isclose(GlobalAssembler().assemble_loads(eas_model, dofs)[0::3].sum(), 1.0)
    surface_model = _model(
        fully_fixed=True,
        distributed_loads=[
            {"type": "surface_traction", "element": 0, "face": 0, "value": [0.0, 0.0, -2.0]}
        ],
    )
    assert np.isclose(GlobalAssembler().assemble_loads(surface_model, surface_model.dof_manager())[2::3].sum(), -2.0)

    standard_model = _model(element_type="HEX8", fully_fixed=True)
    standard_spec = ElementRegistry.get("HEX8")
    assert standard_spec.factory(material).__class__ is Hex8Element
    standard_local = standard_spec.factory(material).stiffness(standard_model.nodes)
    standard_global = GlobalAssembler().assemble_stiffness(standard_model, standard_model.dof_manager()).toarray()
    assert np.array_equal(standard_global, standard_local)
    assert HEX8_EAS_EXPERIMENTAL != "HEX8"
    decoded = JsonModelReader().from_dict(
        {
            "nodes": _unit_hex().tolist(),
            "elements": [{"type": HEX8_EAS_EXPERIMENTAL, "nodes": list(range(8)), "material": "solid"}],
            "materials": {"solid": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
        }
    )
    assert decoded.elements[0].type == HEX8_EAS_EXPERIMENTAL


def test_hex8_eas_affine_patch_rigid_modes_and_force_tangent_consistency() -> None:
    gradient = np.asarray([[0.010, 0.020, -0.015], [-0.030, 0.005, 0.025], [0.012, -0.018, 0.008]])
    for coords in (_unit_hex(), _warped_hex()):
        for poisson in (0.3, 0.4999):
            material = SolidMaterial(E=210.0e9, nu=poisson)
            element = Hex8EASExperimentalElement(material)
            tangent = element.stiffness(coords)
            scale = float(np.linalg.norm(tangent, ord=np.inf))
            assert np.all(np.isfinite(tangent))
            assert np.allclose(tangent, tangent.T, rtol=0.0, atol=2.0e-14 * scale)
            for axis in np.eye(3):
                translation = np.tile(axis, 8)
                assert np.linalg.norm(tangent @ translation) / scale < 2.0e-11
                rotation = np.concatenate([np.cross(axis, point) for point in coords])
                assert np.linalg.norm(tangent @ rotation) / (scale * max(np.linalg.norm(rotation), 1.0)) < 2.0e-11

            displacement = np.concatenate([gradient @ point + [0.2, -0.1, 0.05] for point in coords])
            recovered = element.recover(coords, displacement)
            expected = _engineering_strain(gradient)
            assert np.allclose(recovered["strains"], np.tile(expected, (8, 1)), rtol=2.0e-9, atol=2.0e-11)
            assert np.linalg.norm(recovered["enhanced_variables"]) < 1.0e-8
            assert np.allclose(recovered["internal_force"], tangent @ displacement, rtol=2.0e-9, atol=2.0e-5)
            assert np.isclose(recovered["energy"], 0.5 * displacement @ (tangent @ displacement), rtol=2.0e-9)

            probe = np.sin(np.arange(24, dtype=float) + 0.4)
            center = np.cos(np.arange(24, dtype=float) * 0.31) * 2.0e-4
            step = 1.0e-5
            plus = element.recover(coords, center + step * probe)["internal_force"]
            minus = element.recover(coords, center - step * probe)["internal_force"]
            directional = (plus - minus) / (2.0 * step)
            assert np.allclose(directional, tangent @ probe, rtol=2.0e-8, atol=2.0e-4)


def test_hex8_eas_refuses_invalid_condensation_geometry_and_material_inputs() -> None:
    element = Hex8EASExperimentalElement(SolidMaterial(E=210.0e9, nu=0.3))
    with pytest.raises(InputValidationError, match=r"finite \(8, 3\)"):
        element.stiffness(np.full((8, 3), np.nan))
    with pytest.raises(ValueError, match="Jacobian|geometry"):
        element.stiffness(np.zeros((8, 3)))
    thin = _unit_hex()
    thin[:, 2] *= 1.0e-6
    with pytest.raises(InputValidationError, match="condensed block condition"):
        element.stiffness(thin)
    with pytest.raises(TypeError, match="SolidMaterial"):
        Hex8EASExperimentalElement(object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="parameters must be finite"):
        Hex8EASExperimentalElement(SolidMaterial(E=float("nan"), nu=0.3))
    with pytest.raises(ValueError, match="parameters must be finite"):
        Hex8EASExperimentalElement(SolidMaterial(E=210.0e9, nu=0.3, density=float("nan")))


def test_hex8_eas_scope_and_compatibility_preflight_fail_closed() -> None:
    assert assess_element(0, HEX8_EAS_EXPERIMENTAL, _unit_hex()).classification == VALID
    valid = _model(fully_fixed=True)
    report = MeshValidator().validate(valid)
    assert report.status != "FAIL", report.errors
    assert not hex8_eas_scope_errors(valid)
    compatibility = preflight_model(valid)
    assert compatibility.status == "EXPERIMENTAL_ROUTE"
    assert compatibility.results[0].registry_maturity is None

    nonlinear = _model(analysis={"type": "nonlinear_static", "method": "newton_raphson"})
    assert any("linear_static only" in message for message in hex8_eas_scope_errors(nonlinear))
    with pytest.raises(InputValidationError, match="linear_static only"):
        GlobalAssembler().assemble_stiffness(nonlinear, nonlinear.dof_manager())
    assert preflight_model(nonlinear).status == "UNSUPPORTED_ROUTE"

    non_direct = _model(analysis={"type": "linear_static", "method": "cg"})
    assert any("requires analysis method 'direct'" in message for message in hex8_eas_scope_errors(non_direct))
    buckling = _model(analysis={"type": "linear_buckling", "method": "eigsh"})
    assert any("linear_static only" in message for message in hex8_eas_scope_errors(buckling))

    unsupported_material = _model(material_type="orthotropic_3d")
    assert any("isotropic_3d" in message for message in hex8_eas_scope_errors(unsupported_material))
    assert MeshValidator().validate(unsupported_material).status == "FAIL"

    mixed = FiniteElementModel.from_raw(
        nodes=np.vstack((_unit_hex(), _unit_hex() + [2.0, 0.0, 0.0])).tolist(),
        elements=[
            {"type": HEX8_EAS_EXPERIMENTAL, "nodes": list(range(8)), "material": "solid"},
            {"type": "HEX8", "nodes": list(range(8, 16)), "material": "solid"},
        ],
        materials={"solid": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
        analysis="linear_static",
    )
    assert any("homogeneous EAS-only" in message for message in hex8_eas_scope_errors(mixed))
    edge_load = _model(
        distributed_loads=[{"type": "edge_traction", "element": 0, "edge": 0, "value": [1.0, 0.0, 0.0]}]
    )
    assert any("does not support distributed load" in message for message in hex8_eas_scope_errors(edge_load))


def test_hex8_eas_postprocessing_exports_recovered_state_energy_and_experimental_label(tmp_path) -> None:
    model = _model(coords=_warped_hex(), nu=0.4999, fully_fixed=True)
    dofs: DofManager = model.dof_manager()
    displacement = np.sin(np.arange(24, dtype=float) * 0.27) * 1.0e-5
    result = StressPostProcessor().element_results(model, dofs, displacement)[0]
    assert result["formulation_id"] == HEX8_EAS_FORMULATION_ID
    assert result["maturity"] == "EXPERIMENTAL"
    assert result["qualification_status"] == "NOT_ASSESSED"
    assert len(result["enhanced_variables"]) == 6
    assert len(result["integration_points"]) == 8
    assert all("enhanced_strain" in point and "volumetric_energy_density" in point for point in result["integration_points"])
    assert np.allclose(result["internal_force"], result["matrix_force"], rtol=2.0e-9, atol=2.0e-5)
    assert result["strain_energy"] == pytest.approx(result["deviatoric_energy"] + result["volumetric_energy"])
    json.dumps(result, allow_nan=False)

    visual_result = SimpleNamespace(dofs=dofs, displacements=displacement, element_results=[result], nodal_results=[])
    target = tmp_path / "eas-result.vtu"
    VtuResultWriter().write(visual_result, model, target)
    assert "ExperimentalFormulationFlag" in target.read_text(encoding="utf-8")

    standard_model = _model(element_type="HEX8", coords=_warped_hex(), fully_fixed=True)
    standard_dofs = standard_model.dof_manager()
    standard_displacement = np.zeros(standard_dofs.ndof)
    standard_result = StressPostProcessor().element_results(
        standard_model, standard_dofs, standard_displacement
    )
    standard_visual_result = SimpleNamespace(
        dofs=standard_dofs,
        displacements=standard_displacement,
        element_results=standard_result,
        nodal_results=[],
    )
    standard_target = tmp_path / "standard-result.vtu"
    VtuResultWriter().write(standard_visual_result, standard_model, standard_target)
    assert "ExperimentalFormulationFlag" not in standard_target.read_text(encoding="utf-8")
