"""Independent exact modal propagation for piecewise-linear transient loads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.linalg import eigh, expm

from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.analyses.dynamic_reduction import DynamicDofReducer
from solveur.core.model import FiniteElementModel


@dataclass(frozen=True)
class ModalOracleHistory:
    """Selected responses produced by exact state-space propagation."""

    times: np.ndarray
    displacement_probe: np.ndarray
    velocity_probe: np.ndarray
    stress_probe: np.ndarray | None


class PiecewiseLinearModalOracle:
    """Propagate ``M u'' + C u' + K u = f(t)`` exactly per load segment.

    The spatial system is diagonalized with mass-normalized eigenvectors. On
    every interval the modal force is affine in time and the augmented state
    ``[q, qdot, p, pdot]`` is advanced with a matrix exponential. This oracle
    therefore does not reuse the Newmark recurrence being verified.
    """

    def __init__(
        self,
        model: FiniteElementModel,
        *,
        rayleigh_alpha: float = 0.0,
        rayleigh_beta: float = 0.0,
    ) -> None:
        assembler = GlobalAssembler()
        dofs = model.dof_manager()
        stiffness = assembler.assemble_stiffness(model, dofs)
        mass = assembler.assemble_mass(model, dofs)
        fixed = assembler.fixed_indices(model, dofs)
        reducer = DynamicDofReducer.from_system(model, dofs, mass, stiffness, fixed)
        values, vectors = eigh(reducer.stiffness.toarray(), reducer.mass.toarray())
        positive = values > max(float(np.max(np.abs(values))), 1.0) * 1.0e-12
        self.model = model
        self.dofs = dofs
        self.reducer = reducer
        self.eigenvalues = np.asarray(values[positive], dtype=float)
        self.modes = np.asarray(vectors[:, positive], dtype=float)
        self.modal_damping = rayleigh_alpha + rayleigh_beta * self.eigenvalues

    def propagate(
        self,
        full_load: np.ndarray,
        load_factors: np.ndarray,
        time_step: float,
        *,
        displacement_probe_index: int,
        stress_probe: Callable[[np.ndarray], float] | None = None,
    ) -> ModalOracleHistory:
        """Return exact responses at all load-table times after ``t=0``."""
        factors = np.asarray(load_factors, dtype=float)
        if factors.ndim != 1 or factors.size < 2 or not np.all(np.isfinite(factors)):
            raise ValueError("load_factors must be a finite vector including t=0")
        if not np.isfinite(time_step) or time_step <= 0.0:
            raise ValueError("time_step must be finite and positive")
        reduced_load = self.reducer.reduce_load(np.asarray(full_load, dtype=float))
        modal_load = np.asarray(self.modes.T @ reduced_load, dtype=float)
        transitions = np.asarray(
            [
                expm(
                    np.asarray(
                        [
                            [0.0, 1.0, 0.0, 0.0],
                            [-value, -damping, 1.0, 0.0],
                            [0.0, 0.0, 0.0, 1.0],
                            [0.0, 0.0, 0.0, 0.0],
                        ]
                    )
                    * time_step
                )
                for value, damping in zip(
                    self.eigenvalues, self.modal_damping, strict=True
                )
            ]
        )
        q = np.zeros(self.eigenvalues.size)
        velocity = np.zeros_like(q)
        displacement_values: list[float] = []
        velocity_values: list[float] = []
        stress_values: list[float] = []
        for left, right in zip(factors[:-1], factors[1:], strict=True):
            force_left = modal_load * left
            force_slope = modal_load * (right - left) / time_step
            states = np.column_stack((q, velocity, force_left, force_slope))
            advanced = np.einsum("nij,nj->ni", transitions, states)
            q = advanced[:, 0]
            velocity = advanced[:, 1]
            full_u = self.reducer.expand_state(self.modes @ q, full_load * right)
            full_v = self.reducer.expand_state(self.modes @ velocity)
            displacement_values.append(float(full_u[displacement_probe_index]))
            velocity_values.append(float(full_v[displacement_probe_index]))
            if stress_probe is not None:
                stress_values.append(float(stress_probe(full_u)))
        return ModalOracleHistory(
            times=time_step * np.arange(1, factors.size, dtype=float),
            displacement_probe=np.asarray(displacement_values),
            velocity_probe=np.asarray(velocity_values),
            stress_probe=np.asarray(stress_values) if stress_probe is not None else None,
        )
