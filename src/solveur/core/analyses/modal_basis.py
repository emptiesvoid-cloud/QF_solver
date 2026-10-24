"""Reusable, operator-bound modal bases for the bounded WP00 dynamic scope.

WP04 prepares eigenvectors and projected operators only.  It deliberately
does not solve harmonic or transient response equations.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Mapping, Sequence

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import ArpackNoConvergence

from solveur.core.analyses.dynamic_controls import RayleighDampingDefinition, rayleigh_damping_definition
from solveur.core.analyses.modal import ModalAnalysisSolver
from solveur.core.analyses.modal_basis_damping import ModalDamping
from solveur.core.analyses.modal_basis_numerics import (
    CLUSTER_RELATIVE_GAP as _CLUSTER_RELATIVE_GAP,
    CLUSTER_ZETA_SPREAD_MAX as _CLUSTER_ZETA_SPREAD_MAX,
    DEGENERATE_ROTATION_RELATIVE_SPAN as _DEGENERATE_ROTATION_RELATIVE_SPAN,
    FLOAT_TINY as _FLOAT_TINY,
    MASS_ORTHOGONALITY_MAX as _MASS_ORTHOGONALITY_MAX,
    MODAL_RESIDUAL_MAX as _MODAL_RESIDUAL_MAX,
    SUBSPACE_EQUIVALENCE_TOL as _SUBSPACE_EQUIVALENCE_TOL,
    SYMMETRY_TOL as _SYMMETRY_TOL,
    array_digest as _array_digest,
    detect_clusters as _detect_clusters,
    finite_nonnegative as _finite_nonnegative,
    finite_vector as _finite_vector,
    json_snapshot as _json_snapshot,
    mass_metric_subspace_equivalent as _mass_metric_subspace_equivalent,
    mass_normalize_and_handle_degenerate_subspaces as _mass_normalize_and_handle_degenerate_subspaces,
    modal_zeta_values as _modal_zeta_values,
    positive_definite_screen as _positive_definite_screen,
    relative_modal_residual as _relative_modal_residual,
    relative_sparse_symmetry_error as _relative_sparse_symmetry_error,
    require_small_symmetric as _require_small_symmetric,
    require_sparse_finite_square as _require_sparse_finite_square,
    readonly as _readonly,
    validate_positive_int as _validate_positive_int,
    validate_projected_damping as _validate_projected_damping,
)
from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.io.checkpoint_common import checkpoint_signature

if TYPE_CHECKING:
    from solveur.core.analyses.excitation_channels import BoundExcitationChannels


MODAL_BASIS_CONTRACT = "qf-modal-basis/v1"
_IDENTITY_DOMAIN = "qf-modal-basis-identity/v1"
_EIGENSOLVER_TOL = 1.0e-10
_EIGENSOLVER_MAXITER = 5000
_DENSE_MODAL_MAX_DOFS = 2000
_DAMPING_PROJECTION_LEGACY = "legacy_direct"
_DAMPING_PROJECTION_RAYLEIGH_STRUCTURED = "rayleigh_structured"


class ModalBasis:
    """Immutable-by-interface mass-normalized basis bound to one K/M identity.

    Modes are columns in ``PreparedDynamicSystem`` reduced coordinates.  The
    preparation object is not retained; later consumers must pass the same
    operator identity when projecting a force or reconstructing full modes.
    """

    def __init__(
        self,
        *,
        operator_identity: str,
        dof_signature: tuple[tuple[int, tuple[str, ...]], ...],
        system_size: int,
        eigenvalues: np.ndarray,
        modes: np.ndarray,
        projected_mass: np.ndarray,
        projected_stiffness: np.ndarray,
        clusters: tuple[tuple[int, ...], ...],
        diagnostics: Mapping[str, object],
        extraction: Mapping[str, object],
    ) -> None:
        self._operator_identity = operator_identity
        self._dof_signature = tuple((int(node), tuple(names)) for node, names in dof_signature)
        self._system_size = int(system_size)
        self._eigenvalues = _readonly(eigenvalues, dtype=np.float64)
        self._modes = _readonly(modes, dtype=np.float64)
        self._projected_mass = _readonly(projected_mass, dtype=np.float64)
        self._projected_stiffness = _readonly(projected_stiffness, dtype=np.float64)
        self._clusters = tuple(tuple(int(index) for index in cluster) for cluster in clusters)
        self._diagnostics = _json_snapshot(dict(diagnostics), "modal basis diagnostics")
        self._extraction = _json_snapshot(dict(extraction), "modal basis extraction metadata")
        self._frequencies_hz = _readonly(np.sqrt(self._eigenvalues) / (2.0 * math.pi), dtype=np.float64)
        eigenvalue_digest = _array_digest(self._eigenvalues)
        modes_digest = _array_digest(self._modes)
        self._basis_identity = checkpoint_signature(
            {
                "identity_domain": _IDENTITY_DOMAIN,
                "contract": MODAL_BASIS_CONTRACT,
                "operator_identity": self._operator_identity,
                "dof_signature": [[node, list(names)] for node, names in self._dof_signature],
                "system_size": self._system_size,
                "extraction": self._extraction,
                "normalization": "Phi.T M Phi checked and stored explicitly",
                "clusters": [list(cluster) for cluster in self._clusters],
                "eigenvalues_sha256": eigenvalue_digest,
                "modes_sha256": modes_digest,
                "projected_mass_sha256": _array_digest(self._projected_mass),
                "projected_stiffness_sha256": _array_digest(self._projected_stiffness),
            },
            label="WP04 modal basis identity",
        )

    @classmethod
    def from_prepared(
        cls,
        prepared: PreparedDynamicSystem,
        *,
        mode_count: int,
        method: str = "eigsh",
        dense_limit: int = _DENSE_MODAL_MAX_DOFS,
    ) -> "ModalBasis":
        """Extract the lowest ``mode_count`` admissible modes from prepared K/M."""
        if not isinstance(prepared, PreparedDynamicSystem):
            raise InputValidationError("ModalBasis requires a PreparedDynamicSystem.")
        _validate_positive_int(mode_count, "mode_count")
        _validate_positive_int(dense_limit, "dense_limit")
        selected_method = str(method).strip().lower()
        if selected_method not in {"dense", "eigsh", "lobpcg"}:
            raise InputValidationError("ModalBasis method must be 'dense', 'eigsh' or 'lobpcg'.")

        stiffness = prepared.stiffness
        mass = prepared.mass
        if stiffness.shape != mass.shape or stiffness.shape[0] != prepared.reduced_size:
            raise InputValidationError("Prepared K/M dimensions do not match the prepared reduced DOF system.")
        _require_sparse_finite_square(stiffness, "stiffness")
        _require_sparse_finite_square(mass, "mass")
        k_symmetry = _relative_sparse_symmetry_error(stiffness)
        m_symmetry = _relative_sparse_symmetry_error(mass)
        if k_symmetry > _SYMMETRY_TOL or m_symmetry > _SYMMETRY_TOL:
            raise InputValidationError(
                "ModalBasis requires symmetric K/M in its contracted domain; "
                f"relative errors are K={k_symmetry:.3e}, M={m_symmetry:.3e}."
            )
        mass_screen = _positive_definite_screen(mass, "mass")
        stiffness_screen = _positive_definite_screen(stiffness, "stiffness")
        return cls._from_operators(
            stiffness,
            mass,
            operator_identity=prepared.operator_identity,
            dof_signature=prepared.dof_signature,
            requested_modes=mode_count,
            method=selected_method,
            dense_limit=dense_limit,
            spectral_screens={"mass": mass_screen, "stiffness": stiffness_screen},
        )

    @classmethod
    def _from_operators(
        cls,
        stiffness: object,
        mass: object,
        *,
        operator_identity: str,
        dof_signature: tuple[tuple[int, tuple[str, ...]], ...],
        requested_modes: int,
        method: str,
        dense_limit: int,
        spectral_screens: Mapping[str, object] | None = None,
    ) -> "ModalBasis":
        """Matrix-level constructor used by from_prepared and analytical tests."""
        k_matrix = csr_matrix(stiffness, dtype=np.float64, copy=True)
        m_matrix = csr_matrix(mass, dtype=np.float64, copy=True)
        _require_sparse_finite_square(k_matrix, "stiffness")
        _require_sparse_finite_square(m_matrix, "mass")
        n = int(k_matrix.shape[0])
        _validate_positive_int(requested_modes, "mode_count")
        if requested_modes > n:
            raise InputValidationError(f"mode_count={requested_modes} exceeds the available system size {n}.")
        if not operator_identity:
            raise InputValidationError("ModalBasis requires a non-empty operator identity.")
        lookahead_count = min(requested_modes + 1, n)
        if lookahead_count >= n - 1 and n > dense_limit:
            raise InputValidationError(
                "Sparse extraction cannot verify the requested cluster boundary without a dense spectrum; "
                "reduce the requested count or explicitly raise dense_limit for a bounded system."
            )
        if method == "dense" and n > dense_limit:
            raise InputValidationError(
                f"Dense modal extraction refused for {n} reduced DOFs; configured limit={dense_limit}."
            )

        try:
            values, vectors, backend = ModalAnalysisSolver._solve_eigenproblem(
                k_matrix,
                m_matrix,
                lookahead_count,
                "eigsh" if method == "dense" else method,
                dense_limit=dense_limit,
                which="SA",
                tolerance=_EIGENSOLVER_TOL,
                maxiter=_EIGENSOLVER_MAXITER,
                prefer_dense=method == "dense",
            )
        except InputValidationError:
            raise
        except (np.linalg.LinAlgError, ArpackNoConvergence, RuntimeError, ValueError) as exc:
            raise NumericalConvergenceError(f"Modal basis eigen extraction failed: {exc}") from exc
        values = np.asarray(values, dtype=np.float64).reshape(-1)
        vectors = np.asarray(vectors, dtype=np.float64)
        if vectors.ndim != 2 or vectors.shape != (n, values.size):
            raise NumericalConvergenceError("Modal eigensolver returned inconsistent eigenpair dimensions.")
        if values.size != lookahead_count or not np.all(np.isfinite(values)) or not np.all(np.isfinite(vectors)):
            raise NumericalConvergenceError("Modal eigensolver returned missing or non-finite eigenpairs.")
        order = np.argsort(values, kind="stable")
        values = values[order]
        vectors = vectors[:, order]
        if np.any(values <= 0.0):
            raise InputValidationError(
                "ModalBasis excludes rigid, zero, and non-positive eigenvalues; the prepared stiffness must be positive definite."
            )

        observed_clusters = _detect_clusters(values)
        if requested_modes < n and any(
            requested_modes - 1 in cluster and requested_modes in cluster for cluster in observed_clusters
        ):
            raise InputValidationError(
                "Requested mode_count cuts an identified modal cluster; choose a count ending at a cluster boundary."
            )
        selected_values = values[:requested_modes].copy()
        selected_vectors = vectors[:, :requested_modes].copy()
        selected_clusters = tuple(
            tuple(index for index in cluster if index < requested_modes)
            for cluster in observed_clusters
            if cluster[0] < requested_modes
        )
        selected_vectors = _mass_normalize_and_handle_degenerate_subspaces(
            selected_vectors,
            selected_values,
            m_matrix,
            selected_clusters,
        )
        gram = selected_vectors.T @ (m_matrix @ selected_vectors)
        projected_mass = np.asarray(gram, dtype=np.float64)
        projected_stiffness = np.asarray(selected_vectors.T @ (k_matrix @ selected_vectors), dtype=np.float64)
        if not np.all(np.isfinite(projected_mass)) or not np.all(np.isfinite(projected_stiffness)):
            raise NumericalConvergenceError("Modal projection produced non-finite reduced operators.")
        mass_orthogonality = float(np.linalg.norm(projected_mass - np.eye(requested_modes), ord="fro"))
        projected_k_error = float(
            np.linalg.norm(projected_stiffness - np.diag(selected_values), ord="fro")
            / max(float(np.linalg.norm(projected_stiffness, ord="fro")), _FLOAT_TINY)
        )
        if mass_orthogonality > _MASS_ORTHOGONALITY_MAX:
            raise NumericalConvergenceError(
                "Extracted modes do not satisfy the contracted mass-orthogonality tolerance: "
                f"{mass_orthogonality:.3e} > {_MASS_ORTHOGONALITY_MAX:.3e}."
            )
        residuals = np.asarray(
            [
                _relative_modal_residual(k_matrix, m_matrix, value, selected_vectors[:, i])
                for i, value in enumerate(selected_values)
            ],
            dtype=np.float64,
        )
        if not np.all(np.isfinite(residuals)) or float(np.max(residuals, initial=0.0)) > _MODAL_RESIDUAL_MAX:
            raise NumericalConvergenceError(
                "Modal eigenpair residual exceeds the preregistered tolerance: "
                f"{float(np.max(residuals, initial=0.0)):.3e} > {_MODAL_RESIDUAL_MAX:.3e}."
            )
        if projected_k_error > _MODAL_RESIDUAL_MAX:
            raise NumericalConvergenceError(
                "Projected stiffness is inconsistent with the extracted eigenpairs: "
                f"relative error={projected_k_error:.3e}."
            )
        _require_small_symmetric(projected_mass, "projected mass")
        _require_small_symmetric(projected_stiffness, "projected stiffness")
        extraction = {
            "method_requested": method,
            "backend_used": backend,
            "requested_mode_count": requested_modes,
            "lookahead_mode_count": lookahead_count,
            "system_size": n,
            "dense_limit": dense_limit,
            "eigensolver_relative_tolerance": _EIGENSOLVER_TOL,
            "eigensolver_max_iterations": _EIGENSOLVER_MAXITER,
            "contract": MODAL_BASIS_CONTRACT,
        }
        diagnostics = {
            "status": "PASS",
            "spectral_domain": "NUMERICALLY_SCREENED_SYMMETRIC_POSITIVE_DEFINITE",
            "spectral_screens": _json_snapshot(dict(spectral_screens or {}), "spectral screens"),
            "dof_count": n,
            "mode_count": requested_modes,
            "frequencies_hz": (np.sqrt(selected_values) / (2.0 * math.pi)).tolist(),
            "eigenvalues_rad2_s2": selected_values.tolist(),
            "relative_modal_residuals": residuals.tolist(),
            "maximum_relative_modal_residual": float(np.max(residuals, initial=0.0)),
            "mass_orthogonality_frobenius_error": mass_orthogonality,
            "projected_stiffness_relative_eigenpair_error": projected_k_error,
            "modal_clusters_1_based": [list(index + 1 for index in cluster) for cluster in selected_clusters],
            "cluster_relative_gap_tolerance": _CLUSTER_RELATIVE_GAP,
            "degenerate_subspace_rotation_relative_span": _DEGENERATE_ROTATION_RELATIVE_SPAN,
            "mode_selection": "lowest positive eigenvalues; no silent count increase",
            "truncation": {
                "is_full_basis": requested_modes == n,
                "unrepresented_dof_modes": n - requested_modes,
                "represented_frequency_band_hz": [
                    float(np.sqrt(selected_values[0]) / (2.0 * math.pi)),
                    float(np.sqrt(selected_values[-1]) / (2.0 * math.pi)),
                ],
                "higher_spectrum_unrepresented": requested_modes < n,
                "accuracy_claim": "none; modal residual is not a full physical truncation-error estimate",
                "residual_flexibility": "NOT_IMPLEMENTED; OPTION-A is outside WP04",
            },
        }
        return cls(
            operator_identity=operator_identity,
            dof_signature=dof_signature,
            system_size=n,
            eigenvalues=selected_values,
            modes=selected_vectors,
            projected_mass=projected_mass,
            projected_stiffness=projected_stiffness,
            clusters=selected_clusters,
            diagnostics=diagnostics,
            extraction=extraction,
        )

    @property
    def operator_identity(self) -> str:
        return self._operator_identity

    @property
    def dof_signature(self) -> tuple[tuple[int, tuple[str, ...]], ...]:
        return self._dof_signature

    @property
    def basis_identity(self) -> str:
        return self._basis_identity

    @property
    def system_size(self) -> int:
        return self._system_size

    @property
    def maturity(self) -> str:
        return "EXPERIMENTAL"

    @property
    def numerical_status(self) -> str:
        return "PASS"

    @property
    def mode_count(self) -> int:
        return int(self._eigenvalues.size)

    @property
    def is_full_basis(self) -> bool:
        return self.mode_count == self._system_size

    @property
    def eigenvalues(self) -> np.ndarray:
        return _readonly(self._eigenvalues, dtype=np.float64)

    @property
    def frequencies_hz(self) -> np.ndarray:
        return _readonly(self._frequencies_hz, dtype=np.float64)

    @property
    def modes(self) -> np.ndarray:
        return _readonly(self._modes, dtype=np.float64)

    @property
    def projected_mass(self) -> np.ndarray:
        return _readonly(self._projected_mass, dtype=np.float64)

    @property
    def projected_stiffness(self) -> np.ndarray:
        return _readonly(self._projected_stiffness, dtype=np.float64)

    @property
    def clusters(self) -> tuple[tuple[int, ...], ...]:
        """Cluster mode indices, one-based for user-facing diagnostics."""
        return tuple(tuple(index + 1 for index in cluster) for cluster in self._clusters)

    @property
    def diagnostics(self) -> dict[str, object]:
        return _json_snapshot(self._diagnostics, "modal basis diagnostics")

    @property
    def extraction(self) -> dict[str, object]:
        return _json_snapshot(self._extraction, "modal basis extraction metadata")

    @property
    def result_availability(self) -> dict[str, object]:
        """Availability contract for this operator/basis-only WP04 result."""
        return {
            "eigenvalues": {
                "status": "AVAILABLE",
                "computed": True,
                "retained": True,
                "reconstructible": True,
                "exportable": "NOT_IMPLEMENTED_IN_WP04",
                "quantity_scope": "linear generalized eigenvalues and natural frequencies",
            },
            "reduced_modes": {
                "status": "AVAILABLE",
                "computed": True,
                "retained": True,
                "reconstructible": True,
                "exportable": "NOT_IMPLEMENTED_IN_WP04",
                "quantity_scope": "mass-normalized vectors in prepared reduced coordinates",
            },
            "full_mode_shapes": {
                "status": "NOT_COMPUTED",
                "computed": False,
                "retained": False,
                "reconstructible": True,
                "exportable": "NOT_IMPLEMENTED_IN_WP04",
                "requires": "the same compatible PreparedDynamicSystem",
            },
            "physical_reactions": {
                "status": "NOT_COMPUTED",
                "computed": False,
                "retained": False,
                "reconstructible": False,
                "exportable": False,
                "reason": "WP04 constructs a basis and operators only; it solves no response equilibrium.",
            },
            "stress": {
                "status": "NOT_APPLICABLE",
                "computed": False,
                "retained": False,
                "reconstructible": False,
                "exportable": False,
                "reason": "No forced response or stress recovery is implemented in WP04.",
            },
        }

    @property
    def dense_storage_bytes(self) -> dict[str, int]:
        return {
            "modes": int(self._modes.nbytes),
            "projected_mass": int(self._projected_mass.nbytes),
            "projected_stiffness": int(self._projected_stiffness.nbytes),
            "total_basis_owned_arrays": int(
                self._modes.nbytes + self._projected_mass.nbytes + self._projected_stiffness.nbytes
            ),
        }

    def assert_compatible(self, prepared: PreparedDynamicSystem) -> None:
        if not isinstance(prepared, PreparedDynamicSystem):
            raise InputValidationError("Modal basis compatibility requires a PreparedDynamicSystem.")
        if prepared.operator_identity != self.operator_identity or prepared.dof_signature != self.dof_signature:
            raise InputValidationError("Modal basis is stale or belongs to different prepared K/M operators.")
        if prepared.reduced_size != self.system_size:
            raise InputValidationError("Modal basis dimensions do not match the prepared reduced system.")

    def full_modes(self, prepared: PreparedDynamicSystem) -> np.ndarray:
        """Reconstruct full-DOF modes on demand without retaining a model reference."""
        self.assert_compatible(prepared)
        result = np.column_stack([prepared.expand_state(self._modes[:, index]) for index in range(self.mode_count)])
        return _readonly(result, dtype=np.float64)

    def project_rhs(self, reduced_rhs: np.ndarray, prepared: PreparedDynamicSystem) -> np.ndarray:
        """Project a prepared reduced-space real or complex RHS, without solving it."""
        self.assert_compatible(prepared)
        values = _finite_vector(reduced_rhs, self.system_size, "reduced RHS")
        projected = self._modes.T @ values
        if not np.all(np.isfinite(projected)):
            raise InputValidationError("Modal RHS projection produced non-finite values.")
        return np.asarray(projected)

    def project_full_rhs(self, full_rhs: np.ndarray, prepared: PreparedDynamicSystem) -> np.ndarray:
        self.assert_compatible(prepared)
        full_size = sum(len(names) for _, names in prepared.dof_signature)
        return self.project_rhs(prepared.reduce_load(_finite_vector(full_rhs, full_size, "full RHS")), prepared)

    def project_real_excitation(
        self,
        channels: "BoundExcitationChannels",
        prepared: PreparedDynamicSystem,
        *,
        time_s: float,
        step: int = 0,
        steps: int = 1,
        dt: float = 0.01,
    ) -> np.ndarray:
        self.assert_compatible(prepared)
        channels._require_prepared(prepared)
        return self.project_rhs(
            channels.reduced_real_rhs(prepared, time_s=time_s, step=step, steps=steps, dt=dt), prepared
        )

    def project_harmonic_excitation(
        self,
        channels: "BoundExcitationChannels",
        prepared: PreparedDynamicSystem,
        *,
        frequency_hz: float | None = None,
    ) -> np.ndarray:
        self.assert_compatible(prepared)
        channels._require_prepared(prepared)
        return self.project_rhs(channels.reduced_harmonic_rhs(prepared, frequency_hz=frequency_hz), prepared)

    def participation(
        self, influence_vectors: Mapping[str, np.ndarray], prepared: PreparedDynamicSystem
    ) -> dict[str, object]:
        """Return mass participation for explicit reduced-coordinate influences."""
        self.assert_compatible(prepared)
        mass = prepared.mass
        result: dict[str, object] = {}
        for name, raw_vector in sorted(influence_vectors.items()):
            if not isinstance(name, str) or not name.strip():
                raise InputValidationError("Participation influence names must be non-empty strings.")
            influence = _finite_vector(raw_vector, self.system_size, f"influence vector {name!r}")
            total = float(influence @ (mass @ influence))
            if not math.isfinite(total) or total <= 0.0:
                raise InputValidationError(f"Influence vector {name!r} must have positive generalized mass.")
            modal_generalized_force = np.asarray(self._modes.T @ (mass @ influence), dtype=np.float64)
            effective_mass = modal_generalized_force**2
            ratios = effective_mass / total
            cumulative = np.cumsum(ratios)
            result[name] = {
                "effective_modal_mass": effective_mass.tolist(),
                "participating_mass_ratio": ratios.tolist(),
                "cumulative_participating_mass_ratio": cumulative.tolist(),
                "total_generalized_mass": total,
                "represented_ratio": float(cumulative[-1]) if cumulative.size else 0.0,
                "interpretation_limit": "not a guarantee of local response or stress accuracy",
            }
        return result

    def subspace_equivalent(
        self,
        other: "ModalBasis",
        prepared: PreparedDynamicSystem,
        *,
        tolerance: float = _SUBSPACE_EQUIVALENCE_TOL,
    ) -> bool:
        """Compare mass-metric subspaces independent of sign/order/rotation."""
        if not isinstance(other, ModalBasis):
            raise InputValidationError("Subspace comparison requires another ModalBasis.")
        self.assert_compatible(prepared)
        other.assert_compatible(prepared)
        tol = _finite_nonnegative(tolerance, "subspace equivalence tolerance")
        if self.mode_count != other.mode_count:
            return False
        return _mass_metric_subspace_equivalent(
            self._modes,
            other._modes,
            self._eigenvalues,
            other._eigenvalues,
            prepared.mass,
            tolerance=tol,
        )

    def rayleigh_damping(
        self,
        prepared: PreparedDynamicSystem,
        *,
        alpha: float,
        beta: float,
        projection_method: str = _DAMPING_PROJECTION_LEGACY,
    ) -> "ModalDamping":
        """Project declared Rayleigh damping with an explicit numerical route.

        ``legacy_direct`` preserves the historical ``Phi.T @ (C @ Phi)``
        contract. ``rayleigh_structured`` contracts the already projected
        physical K/M operators and is valid only because this API constructs
        C from the declared Rayleigh coefficients.
        """
        self.assert_compatible(prepared)
        _finite_nonnegative(alpha, "Rayleigh alpha")
        _finite_nonnegative(beta, "Rayleigh beta")
        definition = rayleigh_damping_definition({"rayleigh_alpha": alpha, "rayleigh_beta": beta})
        return self._project_rayleigh_definition(prepared, definition, projection_method=projection_method)

    def rayleigh_damping_from_parameters(
        self,
        prepared: PreparedDynamicSystem,
        parameters: Mapping[str, object],
        *,
        projection_method: str = _DAMPING_PROJECTION_LEGACY,
    ) -> "ModalDamping":
        """Resolve a Rayleigh definition and apply the explicitly selected route."""
        self.assert_compatible(prepared)
        if not isinstance(parameters, Mapping):
            raise InputValidationError("Rayleigh damping parameters must be a mapping.")
        definition = rayleigh_damping_definition(dict(parameters))
        return self._project_rayleigh_definition(prepared, definition, projection_method=projection_method)

    def _project_rayleigh_definition(
        self,
        prepared: PreparedDynamicSystem,
        definition: RayleighDampingDefinition,
        *,
        projection_method: str = _DAMPING_PROJECTION_LEGACY,
    ) -> "ModalDamping":
        if not isinstance(projection_method, str):
            raise InputValidationError("Rayleigh projection_method must be a string.")
        method = projection_method.strip().lower()
        if method not in {_DAMPING_PROJECTION_LEGACY, _DAMPING_PROJECTION_RAYLEIGH_STRUCTURED}:
            raise InputValidationError(
                "Rayleigh projection_method must be 'legacy_direct' or 'rayleigh_structured'."
            )
        c_physical = (definition.alpha * prepared.mass + definition.beta * prepared.stiffness).tocsr()
        expected = definition.alpha * self._projected_mass + definition.beta * self._projected_stiffness
        direct = np.asarray(self._modes.T @ (c_physical @ self._modes), dtype=np.float64)
        if method == _DAMPING_PROJECTION_LEGACY:
            # Preserve the historical fail-closed ordering as well as output.
            _validate_projected_damping(direct)
        elif direct.shape != expected.shape or not np.all(np.isfinite(direct)):
            raise NumericalConvergenceError("Direct Rayleigh projection is non-finite or has inconsistent dimensions.")
        consistency_scale = direct if method == _DAMPING_PROJECTION_LEGACY else expected
        relative_error = float(
            np.linalg.norm(direct - expected, ord="fro")
            / max(float(np.linalg.norm(consistency_scale, ord="fro")), _FLOAT_TINY)
        )
        if not math.isfinite(relative_error) or relative_error > _MODAL_RESIDUAL_MAX:
            raise NumericalConvergenceError("Projected Rayleigh damping disagrees with projected K/M.")
        if method == _DAMPING_PROJECTION_LEGACY:
            # Keep the historical gate and output unchanged unless callers
            # explicitly select the structurally equivalent Rayleigh route.
            projected = direct
        else:
            # This identity is valid only for the Rayleigh definition above.
            # It does not average or repair a computed matrix: each reduced
            # operator comes from the already validated K/M modal projections.
            projected = np.asarray(expected, dtype=np.float64)
            _validate_projected_damping(projected)
        return ModalDamping(
            matrix=projected,
            source="RAYLEIGH_PHYSICAL_PROJECTED",
            basis_identity=self.basis_identity,
            operator_identity=self.operator_identity,
            parameters=(
                definition.to_dict()
                if method == _DAMPING_PROJECTION_LEGACY
                else {
                    **definition.to_dict(),
                    "projection_method": method,
                    "direct_projection_relative_consistency_error": relative_error,
                }
            ),
            reaction_availability="NOT_COMPUTED",
            reaction_reason="A full-space equilibrium consumer has not reconstructed physical reactions.",
        )

    def prescribed_modal_damping(
        self,
        zeta: float | Sequence[float] | np.ndarray,
    ) -> "ModalDamping":
        """Build an explicit reduced modal damping operator.

        Within an identified cluster, one common damping ratio is required and
        a scalar block based on the cluster mean ``zeta*omega`` is used.  This
        separately identified invariant cluster operator avoids arbitrary
        damping under rotations of a degenerate modal subspace.
        """
        ratios = _modal_zeta_values(zeta, self.mode_count)
        omega = np.sqrt(self._eigenvalues)
        diagonal = 2.0 * ratios * omega
        matrix = np.diag(diagonal)
        cluster_records: list[dict[str, object]] = []
        for cluster in self._clusters:
            if len(cluster) < 2:
                continue
            cluster_ratios = ratios[np.asarray(cluster, dtype=int)]
            spread = float(np.ptp(cluster_ratios))
            if spread > _CLUSTER_ZETA_SPREAD_MAX:
                raise InputValidationError(
                    "Prescribed modal damping ratios must be equal within every identified modal cluster; "
                    f"cluster={tuple(index + 1 for index in cluster)}, spread={spread:.3e}."
                )
            common_zeta = float(np.mean(cluster_ratios))
            invariant_coefficient = float(2.0 * np.mean(cluster_ratios * omega[np.asarray(cluster, dtype=int)]))
            matrix[np.ix_(cluster, cluster)] = np.eye(len(cluster)) * invariant_coefficient
            cluster_records.append(
                {
                    "modes_1_based": [index + 1 for index in cluster],
                    "common_zeta": common_zeta,
                    "invariant_scalar_damping_coefficient": invariant_coefficient,
                    "operator": "2*mean(zeta_j*omega_j)*I",
                }
            )
        _validate_projected_damping(matrix)
        return ModalDamping(
            matrix=matrix,
            source="PRESCRIBED_MODAL_REDUCED_MODEL",
            basis_identity=self.basis_identity,
            operator_identity=self.operator_identity,
            parameters={
                "zeta_by_mode": ratios.tolist(),
                "frequency_source": "sqrt(eigenvalue) in rad/s",
                "cluster_policy": "equal zeta and invariant scalar block for each identified cluster",
                "cluster_records": cluster_records,
            },
            reaction_availability="UNAVAILABLE",
            reaction_reason="Prescribed modal damping is a reduced model, not a complete physical full-space C matrix.",
        )
