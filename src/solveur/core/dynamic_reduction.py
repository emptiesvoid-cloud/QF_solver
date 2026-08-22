"""Invariant reduction of massless shell drilling degrees of freedom."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import csc_matrix, csr_matrix, eye, lil_matrix
from scipy.sparse.linalg import LinearOperator, SuperLU, splu, spsolve

from solveur.elements.shell.mitc4 import MITC4Element

from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.elements.shell.mitc3 import Mitc3ShellElement
from solveur.elements.shell.frames import director_frame, rotation_subspace_is_invariant


@dataclass
class DynamicDofReducer:
    """Condense free shell directions that carry no physical inertia.

    Rotations are first expressed in deterministic nodal director frames.  A
    drilling coordinate is condensed only when its assembled mass row is null
    within tolerance.  Curved assemblies whose nodal rotations have physical
    inertia therefore remain in the dynamic system.
    """

    full_size: int
    free: np.ndarray
    transform: csr_matrix
    physical: np.ndarray
    massless: np.ndarray
    mass: csr_matrix
    stiffness: object
    stiffness_pd: csr_matrix
    stiffness_dp: csr_matrix
    stiffness_dd: csc_matrix | None
    drilling_factor: SuperLU | None
    diagnostics: dict[str, object]

    @classmethod
    def from_system(
        cls,
        model: FiniteElementModel,
        dofs: DofManager,
        mass: csr_matrix,
        stiffness: csr_matrix,
        fixed: np.ndarray,
    ) -> "DynamicDofReducer":
        free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
        if free.size == 0:
            raise InputValidationError("No free degree of freedom remains after boundary conditions.")
        transform, drilling_candidates = _free_nodal_transform(model, dofs, free, fixed)
        mass_free = (transform @ mass[free, :][:, free] @ transform.T).tocsr()
        stiffness_free = (transform @ stiffness[free, :][:, free] @ transform.T).tocsr()
        row_mass = np.asarray(abs(mass_free).sum(axis=1)).ravel()
        reference = max(float(row_mass.max(initial=0.0)), 1.0)
        # Faceted curved shells can leave round-off-level inertia in the
        # nodal drilling direction after the director-frame transformation.
        # Condense that leakage instead of turning it into a badly conditioned
        # physical modal coordinate; the element mass formulation remains
        # exactly massless in drilling.
        tolerance = _positive_tolerance(model, "drilling_mass_tolerance", 1.0e-10)
        massless = np.array(
            [index for index in drilling_candidates if row_mass[index] <= tolerance * reference], dtype=int
        )
        physical = np.setdiff1d(np.arange(free.size, dtype=int), massless)
        if physical.size == 0:
            raise NumericalConvergenceError("Dynamic reduction found no inertial degree of freedom.")

        mass_pp = mass_free[physical, :][:, physical].tocsr()
        stiffness_pp = stiffness_free[physical, :][:, physical].tocsr()
        empty = csr_matrix((physical.size, 0), dtype=float)
        if massless.size == 0:
            return cls(
                dofs.ndof,
                free,
                transform,
                physical,
                massless,
                mass_pp,
                stiffness_pp,
                empty,
                empty.T.tocsr(),
                None,
                None,
                _diagnostics(drilling_candidates, massless, row_mass, reference, tolerance, stiffness_pp),
            )

        mass_coupling = mass_free[massless, :]
        coupling_ratio = float(abs(mass_coupling).sum()) / max(float(abs(mass_free).sum()), 1.0)
        if coupling_ratio > 10.0 * tolerance:
            raise NumericalConvergenceError(
                "A candidate shell drilling direction carries non-negligible mass; "
                f"relative coupling={coupling_ratio:.6e}."
            )
        stiffness_pd = stiffness_free[physical, :][:, massless].tocsr()
        stiffness_dp = stiffness_free[massless, :][:, physical].tocsr()
        stiffness_dd = stiffness_free[massless, :][:, massless].tocsc()
        try:
            factor = splu(stiffness_dd)
        except (RuntimeError, ValueError) as exc:
            raise NumericalConvergenceError(
                "Shell drilling condensation failed; verify drilling_scale and shell constraints."
            ) from exc
        lazy = _lazy_condensation_enabled(model)
        if lazy:
            condensed_stiffness: object = LazyCondensedStiffness(
                stiffness_pp,
                stiffness_pd,
                stiffness_dp,
                factor,
                np.asarray(stiffness_dd.diagonal(), dtype=float),
            )
        else:
            transfer = spsolve(stiffness_dd, stiffness_dp.tocsc())
            transfer = transfer.tocsr() if hasattr(transfer, "tocsr") else csr_matrix(transfer)
            condensed_stiffness = (stiffness_pp - stiffness_pd @ transfer).tocsr()
            condensed_stiffness = (0.5 * (condensed_stiffness + condensed_stiffness.T)).tocsr()
        return cls(
            dofs.ndof,
            free,
            transform,
            physical,
            massless,
            mass_pp,
            condensed_stiffness,
            stiffness_pd,
            stiffness_dp,
            stiffness_dd,
            factor,
            _diagnostics(
                drilling_candidates,
                massless,
                row_mass,
                reference,
                tolerance,
                condensed_stiffness,
                coupling_ratio,
                lazy=lazy,
            ),
        )

    @property
    def reduced_size(self) -> int:
        return int(self.physical.size)

    @property
    def has_condensation(self) -> bool:
        return bool(self.massless.size)

    def reduce_state(self, full_vector: np.ndarray) -> np.ndarray:
        """Express a global state in the retained dynamic coordinates."""
        local = np.asarray(self.transform @ np.asarray(full_vector, dtype=float)[self.free]).ravel()
        return local[self.physical]

    def reduce_load(self, full_vector: np.ndarray) -> np.ndarray:
        """Return the statically equivalent load on retained coordinates."""
        local = np.asarray(self.transform @ np.asarray(full_vector, dtype=float)[self.free]).ravel()
        reduced = local[self.physical].copy()
        if self.has_condensation:
            drilling = self._solve_drilling(local[self.massless])
            reduced -= np.asarray(self.stiffness_pd @ drilling).ravel()
        return reduced

    def expand_state(self, reduced: np.ndarray, full_load: np.ndarray | None = None) -> np.ndarray:
        """Reconstruct a full global state, including algebraic drilling rotations."""
        local = np.zeros(self.free.size, dtype=float)
        local[self.physical] = np.asarray(reduced, dtype=float)
        if self.has_condensation:
            drilling_load = np.zeros(self.massless.size, dtype=float)
            if full_load is not None:
                transformed_load = np.asarray(
                    self.transform @ np.asarray(full_load, dtype=float)[self.free]
                ).ravel()
                drilling_load = transformed_load[self.massless]
            rhs = drilling_load - np.asarray(self.stiffness_dp @ local[self.physical]).ravel()
            local[self.massless] = self._solve_drilling(rhs)
        full = np.zeros(self.full_size, dtype=float)
        full[self.free] = np.asarray(self.transform.T @ local).ravel()
        return full

    def expand_complex_state(
        self,
        reduced: np.ndarray,
        full_load: np.ndarray | None = None,
        *,
        stiffness_factor: complex = 1.0 + 0.0j,
    ) -> np.ndarray:
        """Reconstruct a complex harmonic state including algebraic drilling.

        ``stiffness_factor`` is the scalar multiplying every stiffness block
        in the harmonic impedance.  For Rayleigh damping it is
        ``1 + 1j * omega * rayleigh_beta``.  Only a direct drilling load is
        divided by this factor; the displacement transfer remains static.
        """
        factor = complex(stiffness_factor)
        if not np.isfinite(factor.real) or not np.isfinite(factor.imag) or abs(factor) <= 1.0e-30:
            raise InputValidationError("Harmonic stiffness factor must be finite and non-zero.")
        local = np.zeros(self.free.size, dtype=complex)
        local[self.physical] = np.asarray(reduced, dtype=complex)
        if self.has_condensation:
            drilling_load = np.zeros(self.massless.size, dtype=complex)
            if full_load is not None:
                transformed_load = np.asarray(
                    self.transform @ np.asarray(full_load, dtype=complex)[self.free]
                ).ravel()
                drilling_load = transformed_load[self.massless]
            rhs = drilling_load / factor - np.asarray(self.stiffness_dp @ local[self.physical]).ravel()
            local[self.massless] = self._solve_drilling_complex(rhs)
        full = np.zeros(self.full_size, dtype=complex)
        full[self.free] = np.asarray(self.transform.T @ local).ravel()
        return full

    def _solve_drilling(self, rhs: np.ndarray) -> np.ndarray:
        if self.drilling_factor is None:
            return np.zeros(0, dtype=float)
        result = np.asarray(self.drilling_factor.solve(np.asarray(rhs, dtype=float))).ravel()
        if not np.all(np.isfinite(result)):
            raise NumericalConvergenceError("Shell drilling reconstruction produced non-finite values.")
        return result

    def _solve_drilling_complex(self, rhs: np.ndarray) -> np.ndarray:
        if self.drilling_factor is None:
            return np.zeros(0, dtype=complex)
        values = np.asarray(rhs, dtype=complex)
        result = self._solve_drilling(values.real) + 1j * self._solve_drilling(values.imag)
        if not np.all(np.isfinite(result)):
            raise NumericalConvergenceError("Shell complex drilling reconstruction produced non-finite values.")
        return result


def _free_nodal_transform(
    model: FiniteElementModel,
    dofs: DofManager,
    free: np.ndarray,
    fixed: np.ndarray,
) -> tuple[csr_matrix, list[int]]:
    transform = lil_matrix(eye(free.size, format="csr"))
    free_position = {int(global_index): local for local, global_index in enumerate(free)}
    fixed_set = {int(index) for index in fixed}
    directors = _shell_node_directors(model)
    candidates: list[int] = []
    for node, director in directors.items():
        indices = [dofs.index(node, name) for name in ("RX", "RY", "RZ")]
        fixed_flags = [index in fixed_set for index in indices]
        if all(fixed_flags):
            continue
        frame = director_frame(director)
        if any(fixed_flags) and not rotation_subspace_is_invariant(frame, fixed_flags):
            raise InputValidationError(
                "Partial rotational constraints must align with the nodal shell director "
                f"frame at node {node}."
            )
        free_components = [component for component, is_fixed in enumerate(fixed_flags) if not is_fixed]
        positions = [free_position[indices[component]] for component in free_components]
        subframe = frame[np.ix_(free_components, free_components)]
        transform[np.ix_(positions, positions)] = subframe
        if 2 in free_components:
            candidates.append(positions[free_components.index(2)])
    return transform.tocsr(), candidates


def _shell_node_directors(model: FiniteElementModel) -> dict[int, np.ndarray]:
    weighted: dict[int, np.ndarray] = {}
    for definition in model.elements:
        if definition.type not in {"MITC3", "MITC4"}:
            continue
        coords = model.nodes[list(definition.nodes)]
        if definition.type == "MITC3":
            frame = Mitc3ShellElement.local_frame(coords)
            weight = max(
                float(np.linalg.norm(np.cross(coords[1] - coords[0], coords[2] - coords[0]))),
                1.0e-30,
            )
        else:
            frame = MITC4Element.local_frame(coords)
            weight = max(
                float(np.linalg.norm(np.cross(coords[2] - coords[0], coords[3] - coords[1]))),
                1.0e-30,
            )
        for node in definition.nodes:
            weighted[int(node)] = weighted.get(int(node), np.zeros(3)) + weight * frame[2]
    directors: dict[int, np.ndarray] = {}
    for node, value in weighted.items():
        norm = float(np.linalg.norm(value))
        if norm <= 1.0e-14:
            raise InputValidationError(f"Cannot construct a consistent shell nodal director at node {node}.")
        directors[node] = value / norm
    return directors


def _positive_tolerance(model: FiniteElementModel, name: str, default: float) -> float:
    try:
        value = float(model.analysis.parameters.get(name, default))
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{name} must be a finite positive number.") from exc
    if not np.isfinite(value) or value <= 0.0:
        raise InputValidationError(f"{name} must be a finite positive number.")
    return value


def _lazy_condensation_enabled(model: FiniteElementModel) -> bool:
    value = model.analysis.parameters.get("lazy_drilling_condensation", False)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class LazyCondensedStiffness(LinearOperator):
    """Apply the exact drilling Schur complement without materializing it."""

    def __init__(
        self,
        physical_stiffness: csr_matrix,
        stiffness_pd: csr_matrix,
        stiffness_dp: csr_matrix,
        drilling_factor: SuperLU,
        drilling_diagonal: np.ndarray,
    ) -> None:
        self.physical_stiffness = physical_stiffness
        self.stiffness_pd = stiffness_pd
        self.stiffness_dp = stiffness_dp
        self.drilling_factor = drilling_factor
        self.drilling_diagonal = np.asarray(drilling_diagonal, dtype=float)
        super().__init__(dtype=np.dtype(float), shape=physical_stiffness.shape)

    def _matvec(self, vector: np.ndarray) -> np.ndarray:
        rhs = np.asarray(self.stiffness_dp @ vector, dtype=float).ravel()
        correction = self.drilling_factor.solve(rhs)
        return np.asarray(self.physical_stiffness @ vector - self.stiffness_pd @ correction).ravel()

    def _matmat(self, vectors: np.ndarray) -> np.ndarray:
        rhs = np.asarray(self.stiffness_dp @ vectors, dtype=float)
        correction = self.drilling_factor.solve(rhs)
        return np.asarray(self.physical_stiffness @ vectors - self.stiffness_pd @ correction)

    def _rmatvec(self, vector: np.ndarray) -> np.ndarray:
        return self._matvec(vector)

    def _rmatmat(self, vectors: np.ndarray) -> np.ndarray:
        return self._matmat(vectors)


def _diagnostics(
    candidates: list[int],
    massless: np.ndarray,
    row_mass: np.ndarray,
    reference: float,
    tolerance: float,
    stiffness: object,
    coupling_ratio: float = 0.0,
    *,
    lazy: bool = False,
) -> dict[str, object]:
    candidate_ratios = [float(row_mass[index] / reference) for index in candidates]
    return {
        "strategy": "consistent_mass_static_drilling_condensation",
        "candidate_drilling_dof_count": len(candidates),
        "condensed_drilling_dof_count": int(massless.size),
        "retained_dof_count": int(stiffness.shape[0]),
        "drilling_mass_tolerance": tolerance,
        "maximum_candidate_mass_row_ratio": max(candidate_ratios, default=0.0),
        "condensed_mass_coupling_ratio": coupling_ratio,
        "condensed_stiffness_nnz": None if lazy else int(stiffness.nnz),
        "lazy_condensation": lazy,
    }
