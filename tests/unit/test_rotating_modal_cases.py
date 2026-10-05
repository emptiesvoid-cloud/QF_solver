"""GYRO-01 zero-speed recovery against the classic modal implementation."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.core.analyses.modal import ModalAnalysisSolver
from solveur.core.analyses.rotating_modal import RotatingModalSolver
from solveur.core.analyses.settings import AnalysisSettings
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.dofs import DOF_ORDER
from solveur.core.model import BoundaryCondition, ElementDefinition, FiniteElementModel
from solveur.elements.discrete import ConcentratedMass, RotatingDisk


def _beam_material() -> dict[str, object]:
    radius = 0.05
    area = np.pi * radius**2
    inertia = area**2 / (4.0 * np.pi)
    return {
        "type": "beam_isotropic",
        "E": 210.0e9,
        "nu": 0.3,
        "A": area,
        "Iy": inertia,
        "Iz": inertia,
        "J": 2.0 * inertia,
        "density": 7800.0,
    }


def _model(*, rotating: bool) -> FiniteElementModel:
    disk: ConcentratedMass | RotatingDisk
    if rotating:
        disk = RotatingDisk(1, 1.0, 0.01, 0.02, (1.0, 0.0, 0.0))
        analysis = AnalysisSettings.from_raw(
            {
                "type": "rotating_modal",
                "method": "dense_qep",
                "parameters": {
                    "rotation": {
                        "axis_global": [1.0, 0.0, 0.0],
                        "speed_rad_s": 0.0,
                        "frame_convention": "global_fixed_right_hand_rule",
                    },
                    "modes": 6,
                },
            }
        )
    else:
        disk = ConcentratedMass(1, 1.0, inertia=((0.02, 0.0, 0.0), (0.0, 0.01, 0.0), (0.0, 0.0, 0.01)))
        analysis = AnalysisSettings(type="modal", method="eigh")
    return FiniteElementModel(
        nodes=np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        elements=[ElementDefinition("BEAM2", (0, 1), "beam")],
        materials={"beam": _beam_material()},
        fixed_dofs=[BoundaryCondition(0, DOF_ORDER)],
        concentrated_masses=[disk],
        analysis=analysis,
    )


def _frequency_clusters(values: np.ndarray, relative_gap: float) -> list[list[int]]:
    clusters: list[list[int]] = []
    for index, value in enumerate(values):
        if not clusters:
            clusters.append([index])
            continue
        previous = values[clusters[-1][-1]]
        scale = max(abs(float(previous)), abs(float(value)), np.finfo(float).tiny)
        if abs(float(value - previous)) <= relative_gap * scale:
            clusters[-1].append(index)
        else:
            clusters.append([index])
    return clusters


def test_gyro01_zero_speed_matches_modal_frequencies_multiplicity_and_subspaces() -> None:
    rotating_model = _model(rotating=True)
    reference_model = _model(rotating=False)
    rotating_result = RotatingModalSolver().solve(rotating_model)
    modal_result = ModalAnalysisSolver().solve(reference_model)
    selected = list(rotating_result.selected_mode_indices)
    gyro_frequencies = rotating_result.frequencies_hz[selected]
    modal_frequencies = modal_result.frequencies_hz[: len(selected)]

    assert len(gyro_frequencies) == len(modal_frequencies) == 6
    assert gyro_frequencies == pytest.approx(modal_frequencies, rel=1.0e-8, abs=1.0e-12)

    dofs = reference_model.dof_manager()
    _, mass, _, _ = GlobalAssembler().assemble_stiffness_and_mass(reference_model, dofs)
    mass = mass.toarray()
    for cluster in _frequency_clusters(modal_frequencies, 1.0e-8):
        modal_modes = modal_result.modes[:, cluster]
        gyro_indices = [selected[index] for index in cluster]
        gyro_modes = rotating_result.modes[:, gyro_indices]
        cross = modal_modes.conj().T @ mass @ gyro_modes
        singular_values = np.linalg.svd(cross, compute_uv=False)
        if len(cluster) == 1:
            assert float(singular_values[0] ** 2) >= 0.99999999
        else:
            assert float(np.min(singular_values)) >= 0.99999999
