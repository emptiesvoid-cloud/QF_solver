"""Small, deterministic edge matrix for backend-adjacent contracts."""

from __future__ import annotations

import numpy as np
import pytest
from solveur.core.dynamic_history import _relative_energy_drift, validated_history_probes, validated_shell_stress_probes
from solveur.core.dofs import DofManager, SOLID_DOFS
from solveur.core.rbe import Rbe2Definition, Rbe3Definition, rbe2_constraints, rbe3_constraints
from solveur.elements.discrete import ConcentratedMass, SpringDefinition
from solveur.elements.shell.mitc3_condensation import condense_matrix, condensation_transform, recover_internal
from solveur.elements.shell.mitc4.material import ShellMaterial
from solveur.core.model import FiniteElementModel


def _dofs() -> DofManager:
    return DofManager.from_node_requirements({0: set(SOLID_DOFS), 1: set(SOLID_DOFS)})


@pytest.mark.parametrize(
    "definition, message",
    [
        (Rbe2Definition(0, ()), "at least one slave"),
        (Rbe2Definition(0, (1, 1)), "slave nodes must be unique"),
        (Rbe2Definition(0, (0,)), "cannot also be a slave"),
        (Rbe2Definition(4, (1,)), "existing node"),
        (Rbe2Definition(0, (4,)), "existing node"),
    ],
)
def test_rbe2_rejects_invalid_topology(definition: Rbe2Definition, message: str) -> None:
    with pytest.raises(Exception, match=message):
        rbe2_constraints(np.zeros((2, 3)), definition)


def test_rbe2_ties_rotations_and_drops_zero_offset_terms() -> None:
    rows = rbe2_constraints(
        np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        Rbe2Definition(0, (1,), tie_rotations=True),
    )
    assert len(rows) == 6
    assert all(row.name.startswith("rbe2:slave_1") for row in rows)


@pytest.mark.parametrize(
    "definition, nodes, message",
    [
        (Rbe3Definition(0, ()), None, "at least one independent"),
        (Rbe3Definition(0, ((1, 1.0), (1, 2.0))), None, "independent nodes must be unique"),
        (Rbe3Definition(0, ((1, 0.0),)), None, "non-zero sum"),
        (Rbe3Definition(0, ((1, float("nan")),)), None, "finite"),
        (Rbe3Definition(0, ((1, 1.0),), dofs=("BAD",)), None, "valid generalized"),
        (Rbe3Definition(0, ((1, 1.0),), mode="other"), None, "rigid_body_projection"),
        (Rbe3Definition(0, ((1, 1.0),)), None, "requires node coordinates"),
        (Rbe3Definition(0, ((1, 1.0),), dofs=("UX",)), np.zeros((2, 3)), "requires all six"),
        (Rbe3Definition(0, ((1, -1.0),) * 1), np.zeros((2, 3)), "strictly positive"),
    ],
)
def test_rbe3_rejects_invalid_modes_weights_and_geometry(
    definition: Rbe3Definition, nodes: np.ndarray | None, message: str
) -> None:
    with pytest.raises(Exception, match=message):
        rbe3_constraints(nodes, definition)


def test_rbe3_rejects_reference_and_independent_aliases() -> None:
    with pytest.raises(Exception, match="reference"):
        rbe3_constraints(np.zeros((7, 3)), Rbe3Definition(7, tuple((node, 1.0) for node in range(1, 7))))
    with pytest.raises(Exception, match="differ"):
        rbe3_constraints(np.zeros((6, 3)), Rbe3Definition(0, tuple((node, 1.0) for node in range(6))))


@pytest.mark.parametrize("entries", ["bad", [{"node": 0}], [{"node": 0, "dof": "UX", "label": ""}], [{"node": 0, "dof": "UX", "label": "a"}, {"node": 0, "dof": "UX", "label": "a"}]])
def test_history_probe_validation_rejects_malformed_entries(entries: object) -> None:
    with pytest.raises(Exception):
        validated_history_probes(_dofs(), entries)


def test_history_probe_validation_accepts_default_labels_and_rejects_unavailable_dofs() -> None:
    probes = validated_history_probes(_dofs(), [{"node": 0, "dof": "UX"}, {"node": 1, "dof": "UY", "label": "tip"}])
    assert [entry[0] for entry in probes] == ["node_0_UX", "tip"]
    with pytest.raises(Exception, match="unavailable"):
        validated_history_probes(_dofs(), [{"node": 99, "dof": "UX"}])


@pytest.mark.parametrize(
    "entries, message",
    [("bad", "list"), ([{"node": 0, "component": "S11"}], "adjacent shell"), ([{"node": 0, "component": "BAD"}], "component")],
)
def test_shell_stress_probe_validation_rejects_non_shell_or_bad_components(entries: object, message: str) -> None:
    if entries != [{"node": 0, "component": "BAD"}]:
        model = FiniteElementModel.from_raw(
            nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
            elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "m"}],
            materials={"m": {"type": "isotropic_3d", "E": 1.0, "nu": 0.3}},
        )
    else:
        model = FiniteElementModel.from_raw(
            nodes=[[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]],
            elements=[{"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "m"}],
            materials={"m": {"type": "shell_isotropic", "E": 1.0, "nu": 0.3, "t": 0.1}},
        )
    with pytest.raises(Exception, match=message):
        validated_shell_stress_probes(model, entries)


def test_history_probe_scalar_helpers_and_shell_probe_optional_paths() -> None:
    assert validated_history_probes(_dofs(), None) == []
    assert validated_shell_stress_probes(FiniteElementModel.from_raw(nodes=[[0, 0, 0]], elements=[], materials={}), None) == []
    assert _relative_energy_drift(1.0, 0.0) == 0.0
    assert _relative_energy_drift(2.0, 1.0) == 1.0


def test_mitc3_condensation_valid_projection_and_recovery() -> None:
    stiffness = np.eye(20)
    transform = condensation_transform(stiffness)
    assert transform.shape == (20, 18)
    reduced = condense_matrix(stiffness, transform)
    assert reduced.shape == (18, 18)
    recovered = recover_internal(np.ones(18), transform)
    assert recovered.shape == (2,)


@pytest.mark.parametrize(
    "matrix, retained, message",
    [(np.eye(3)[:, :2], 1, "square"), (np.eye(3), 0, "retained"), (np.eye(3), 3, "retained")],
)
def test_mitc3_condensation_rejects_invalid_partition(matrix: np.ndarray, retained: int, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        condensation_transform(matrix, retained)


def test_mitc3_condensation_rejects_singular_internal_block_and_bad_recovery() -> None:
    singular = np.zeros((20, 20))
    with pytest.raises(ValueError, match="ill-conditioned|singular"):
        condensation_transform(singular)
    with pytest.raises(ValueError, match="incompatible"):
        recover_internal(np.ones(17), np.eye(20, 18))


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"E": 0.0, "nu": 0.3, "t": 1.0}, "Young"),
        ({"E": 1.0, "nu": 0.5, "t": 1.0}, "Poisson"),
        ({"E": 1.0, "nu": 0.3, "t": 0.0}, "thickness"),
        ({"E": 1.0, "nu": 0.3, "t": 1.0, "shear_factor": 0.0}, "shear_factor"),
        ({"E": 1.0, "nu": 0.3, "t": 1.0, "drilling_scale": -1.0}, "drilling"),
        ({"E": 1.0, "nu": 0.3, "t": 1.0, "density": -1.0}, "density"),
    ],
)
def test_mitc4_shell_material_rejects_nonphysical_parameters(kwargs: dict[str, float], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ShellMaterial(**kwargs)


def test_mitc4_shell_material_matrices_and_scalars_are_consistent() -> None:
    material = ShellMaterial(E=100.0, nu=0.25, t=0.2, density=2.0)
    assert material.G == pytest.approx(40.0)
    assert material.membrane_matrix.shape == (3, 3)
    assert material.bending_matrix.shape == (3, 3)
    assert material.shear_matrix.shape == (2, 2)
    assert material.drilling_stiffness == pytest.approx(material.drilling_scale * material.E * material.t)


def test_discrete_spring_and_mass_matrix_contracts_cover_local_and_invalid_paths() -> None:
    local = SpringDefinition(0, ("UX", "RY"), ((2.0, 0.0), (0.0, 3.0)), coordinate_system="local", orientation=tuple(np.eye(3)))
    assert local.active_dofs() == ("UX", "UY", "UZ", "RX", "RY", "RZ")
    assert local.nodal_stiffness().shape == (6, 6)
    with pytest.raises(Exception, match="orientation"):
        SpringDefinition(0, ("UX",), ((1.0,),), coordinate_system="local").nodal_stiffness()
    with pytest.raises(Exception, match="symmetric"):
        SpringDefinition(0, ("UX", "UY"), ((1.0, 1.0), (0.0, 1.0))).nodal_stiffness()
    assert ConcentratedMass(0, 2.0).matrix().shape == (3, 3)
    assert ConcentratedMass(0, 2.0, center_of_mass=(1.0, 0.0, 0.0), inertia=tuple(tuple(row) for row in np.eye(3))).matrix().shape == (6, 6)
    with pytest.raises(Exception, match="strictly positive"):
        ConcentratedMass(0, 0.0).matrix()
