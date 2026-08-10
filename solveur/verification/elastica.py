"""Analytical-numerical Euler elastica references for V&V campaigns."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_bvp


@dataclass(frozen=True)
class CantileverElasticaResult:
    """Dead-load planar elastica response of an inextensible cantilever."""

    tip_x: float
    tip_z: float
    tip_rotation: float
    converged: bool
    nodes: int


def solve_cantilever_elastica(
    *, young: float, inertia: float, length: float, transverse_load: float, points: int = 401
) -> CantileverElasticaResult:
    """Solve the Euler-Bernoulli cantilever elastica under a vertical tip load."""
    if min(young, inertia, length, transverse_load) <= 0.0:
        raise ValueError("Elastica parameters must be strictly positive.")
    if points < 21:
        raise ValueError("Elastica reference requires at least 21 points.")
    coordinate = np.linspace(0.0, length, points)
    stiffness = young * inertia
    load_ratio = transverse_load / stiffness
    rotation = -0.5 * load_ratio * coordinate * (2.0 * length - coordinate)
    curvature = -load_ratio * (length - coordinate)
    initial = np.vstack(
        (
            rotation,
            curvature,
            coordinate,
            np.cumsum(np.sin(rotation)) * length / (points - 1),
        )
    )

    def equations(_coordinate: np.ndarray, state: np.ndarray) -> np.ndarray:
        theta = state[0]
        return np.vstack((state[1], load_ratio * np.cos(theta), np.cos(theta), np.sin(theta)))

    def boundary(left: np.ndarray, right: np.ndarray) -> np.ndarray:
        return np.array((left[0], right[1], left[2], left[3]))

    solution = solve_bvp(equations, boundary, coordinate, initial, tol=1.0e-10, max_nodes=10000)
    if not solution.success:
        raise RuntimeError(f"Euler elastica reference did not converge: {solution.message}")
    tip = solution.sol(np.array([length]))[:, 0]
    return CantileverElasticaResult(
        tip_x=float(tip[2]),
        tip_z=float(tip[3]),
        tip_rotation=float(tip[0]),
        converged=True,
        nodes=int(solution.x.size),
    )
