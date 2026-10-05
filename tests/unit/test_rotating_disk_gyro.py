"""GYRO-02 local disk formulation and assembly invariants."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.core.assembly.rotating_disk_gyro import RotatingDiskGyroAssembler
from solveur.core.dofs import DOF_ORDER, DofManager
from solveur.core.errors import InputValidationError
from solveur.core.model import AnalysisSettings, ElementDefinition, FiniteElementModel
from solveur.elements.discrete import RotatingDisk


def _dofs() -> DofManager:
    return DofManager.from_node_requirements({0: set(DOF_ORDER), 1: set(DOF_ORDER)})


def _model(disks: list[RotatingDisk]) -> FiniteElementModel:
    return FiniteElementModel(
        nodes=np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        elements=[ElementDefinition("BEAM2", (0, 1), "unused")],
        materials={"unused": {}},
        concentrated_masses=disks,
        analysis=AnalysisSettings(type="rotating_modal", method="dense_qep"),
    )


def test_disk_mass_and_unit_speed_gyro_blocks_match_contract() -> None:
    disk = RotatingDisk(1, 2.0, 0.01, 0.02, (1.0, 0.0, 0.0))
    mass = disk.matrix()
    gyro = disk.gyroscopic_matrix()

    assert mass[:3, :3] == pytest.approx(2.0 * np.eye(3))
    assert mass[3:, 3:] == pytest.approx(np.diag([0.02, 0.01, 0.01]))
    assert mass[:3, 3:] == pytest.approx(np.zeros((3, 3)))
    assert gyro[4:, 4:] == pytest.approx(np.asarray([[0.0, 0.02], [-0.02, 0.0]]))
    assert gyro[:3, :3] == pytest.approx(np.zeros((3, 3)))
    assert gyro.T == pytest.approx(-gyro)


def test_assembled_gyro_uses_same_global_dof_map_and_has_zero_quadratic_work() -> None:
    disks = [RotatingDisk(1, 1.0, 0.01, 0.02, (1.0, 0.0, 0.0))]
    dofs = _dofs()
    matrix = RotatingDiskGyroAssembler().assemble(_model(disks), dofs).toarray()
    local_indices = dofs.node_indices(1, ("RY", "RZ"))
    assert matrix[np.ix_(local_indices, local_indices)] == pytest.approx(
        np.asarray([[0.0, 0.02], [-0.02, 0.0]])
    )
    for seed in (2, 17, 2026):
        vector = np.random.default_rng(seed).standard_normal(dofs.ndof)
        assert float(vector @ matrix @ vector) == pytest.approx(0.0, abs=1.0e-14)


def test_disk_mass_and_gyro_are_covariant_under_global_frame_rotation() -> None:
    angle = np.pi / 2.0
    rotation = np.asarray(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
    )
    transform = np.zeros((6, 6))
    transform[:3, :3] = rotation
    transform[3:, 3:] = rotation
    disk_x = RotatingDisk(1, 1.0, 0.01, 0.02, (1.0, 0.0, 0.0))
    disk_y = RotatingDisk(1, 1.0, 0.01, 0.02, tuple(rotation @ np.asarray([1.0, 0.0, 0.0])))

    assert disk_y.matrix() == pytest.approx(transform @ disk_x.matrix() @ transform.T, abs=1.0e-14)
    assert disk_y.gyroscopic_matrix() == pytest.approx(
        transform @ disk_x.gyroscopic_matrix() @ transform.T, abs=1.0e-14
    )


def test_gyro_assembly_rejects_unknown_discrete_entity() -> None:
    model = _model([])
    model.concentrated_masses = [object()]  # type: ignore[list-item]
    with pytest.raises(InputValidationError, match="unsupported entity"):
        RotatingDiskGyroAssembler().assemble(model, _dofs())


@pytest.mark.parametrize(
    "values",
    [
        (0.0, 0.01, 0.02, (1.0, 0.0, 0.0)),
        (1.0, 0.0, 0.02, (1.0, 0.0, 0.0)),
        (1.0, 0.01, 0.0, (1.0, 0.0, 0.0)),
        (1.0, 0.01, 0.021, (1.0, 0.0, 0.0)),
        (1.0, 0.01, 0.02, (0.0, 0.0, 0.0)),
    ],
)
def test_rotating_disk_invalid_inertias_or_axis_fail_closed(values: tuple[object, ...]) -> None:
    with pytest.raises(InputValidationError):
        RotatingDisk(1, *values)  # type: ignore[arg-type]
