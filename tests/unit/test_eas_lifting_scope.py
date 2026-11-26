"""Relèvement externe et garde des appuis EAS, sans résolution FEM."""

from types import SimpleNamespace
from xml.etree import ElementTree

import numpy as np
import pytest

from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.elements.solid.hex8_eas_experimental import Hex8EASExperimentalElement, hex8_eas_scope_errors
from solveur.io.json_reader import JsonModelReader
from solveur.io.vtu_writer import VtuResultWriter
from solveur.materials.solid import SolidMaterial
from solveur.post.stress import StressPostProcessor


def _input(family="HEX8_EAS_EXPERIMENTAL"):
    return {
        "nodes": [[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]],
        "elements": [{"type": family, "nodes": list(range(8)), "material": "m"}],
        "materials": {"m": {"type": "isotropic_3d", "E": 1e6, "nu": 0.3}},
        "fixed_dofs": [{"node": 0, "dofs": ["UX", "UY", "UZ"]}],
    }


def test_eas_raw_and_json_reject_prescribed_fixed_values():
    raw = _input()
    raw["fixed_dofs"][0]["value"] = 0.001
    with pytest.raises(InputValidationError, match="zero displacement only"):
        FiniteElementModel.from_raw(**raw)
    with pytest.raises(InputValidationError, match="value"):
        JsonModelReader().from_dict(raw)
    # Other element routes keep their existing raw-model behavior.
    raw["elements"][0]["type"] = "HEX8"
    assert FiniteElementModel.from_raw(**raw).fixed_dofs[0].dofs == ("UX", "UY", "UZ")


def test_eas_mpc_prescribed_displacement_is_explicitly_outside_scope():
    from solveur.core.constraints import ConstraintTerm, LinearConstraint

    model = FiniteElementModel.from_raw(**_input())
    model.multipoint_constraints.append(
        LinearConstraint(
            terms=(ConstraintTerm(node=1, dof="UX", coefficient=1.0),
                   ConstraintTerm(node=2, dof="UX", coefficient=-1.0)),
            value=0.001,
        )
    )
    assert any("multi-point constraints" in error for error in hex8_eas_scope_errors(model))


def test_model_interfaces_reject_unrecognized_volume_lift():
    raw = _input()
    raw["displacement_lift"] = [[0.001, 0.0, 0.0]] * 8
    with pytest.raises(TypeError, match="displacement_lift"):
        FiniteElementModel.from_raw(**raw)
    with pytest.raises(InputValidationError, match="displacement_lift"):
        JsonModelReader().from_dict(raw)


@pytest.mark.parametrize("family", ["HEX8_EAS_EXPERIMENTAL", "HEX8"])
def test_external_lift_requires_physical_field_for_stresses_and_vtu(tmp_path, family):
    model = FiniteElementModel.from_raw(**_input(family))
    dofs = model.dof_manager()
    coords = model.nodes
    w = np.zeros(24)
    lift = np.column_stack((0.001 * coords[:, 0], np.zeros(8), np.zeros(8))).ravel()
    u = w + lift
    post = StressPostProcessor()
    physical = post.element_results(model, dofs, u)
    correction = post.element_results(model, dofs, w)
    assert not np.allclose(physical[0]["stress"], correction[0]["stress"])
    if family == "HEX8_EAS_EXPERIMENTAL":
        element = Hex8EASExperimentalElement(SolidMaterial(E=1e6, nu=0.3))
        expected = element.recover(coords, u)
        np.testing.assert_allclose(
            [point["stress"] for point in physical[0]["integration_points"]], expected["stresses"]
        )
        np.testing.assert_allclose(physical[0]["enhanced_variables"], expected["enhanced_variables"])
        np.testing.assert_allclose(physical[0]["internal_force"], expected["internal_force"])
        assert physical[0]["strain_energy"] == pytest.approx(expected["energy"])
        assert expected["energy"] > 0
        assert correction[0]["strain_energy"] == pytest.approx(0.0)
        tangent = element.stiffness(coords)
        loads = np.arange(24, dtype=float)
        effective_loads = loads - tangent @ lift
        np.testing.assert_allclose(tangent @ w - effective_loads, tangent @ u - loads, atol=1e-12)
    # The writer exports exactly the displacement and fields it receives.
    result = SimpleNamespace(dofs=dofs, displacements=u, element_results=physical, nodal_results=[])
    output = tmp_path / "physical.vtu"
    VtuResultWriter().write(result, model, output)
    tree = ElementTree.parse(output)
    array = tree.find(".//PointData/DataArray[@Name='Displacement']")
    assert array is not None and array.text is not None
    np.testing.assert_allclose(np.fromstring(array.text, sep=" "), u)
