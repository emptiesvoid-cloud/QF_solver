"""Opt-in numerical robustness controls for nonlinear R&D experiments."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, cast
import warnings

import numpy as np
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import MatrixRankWarning, splu, spsolve

from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.contracts import NonlinearFailureReason


_PARAMETER_KEYS = {
    "experimental_linear_solver",
    "experimental_linear_permutation",
    "experimental_system_scaling",
    "experimental_residual_scaling",
    "experimental_line_search",
    "experimental_line_search_min_alpha",
    "experimental_line_search_max_reductions",
    "experimental_line_search_c",
}
_PERMUTATIONS = {"NATURAL", "MMD_ATA", "MMD_AT_PLUS_A", "COLAMD"}

ROBUSTNESS_POLICY_ID = "qf-solver-unified-robustness"
ROBUSTNESS_POLICY_VERSION = 1


class RobustnessPolicySource(str, Enum):
    """Origin of a robustness policy recorded in nonlinear diagnostics."""

    PUBLIC_DEFAULT = "PUBLIC_DEFAULT"
    EXPERIMENTAL_OVERRIDE = "EXPERIMENTAL_OVERRIDE"
    COMPATIBILITY_ADAPTER = "COMPATIBILITY_ADAPTER"


@dataclass(frozen=True)
class StagnationDecision:
    """Deterministic result of one residual-history stagnation decision."""

    decision: str
    reason: NonlinearFailureReason | None
    residual_window: tuple[float, ...]
    window_size: int
    plateau_threshold: float
    initial_window_residual: float | None
    final_window_residual: float | None
    relative_change: float | None
    convergence_tolerance: float | None
    policy_id: str = ROBUSTNESS_POLICY_ID
    policy_version: int = ROBUSTNESS_POLICY_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return stable, JSON-compatible stagnation diagnostics."""
        return {
            "decision": self.decision,
            "reason": self.reason.value if self.reason is not None else None,
            "window": list(self.residual_window),
            "residual_window": list(self.residual_window),
            "window_size": self.window_size,
            "plateau_threshold": self.plateau_threshold,
            "initial_window_residual": self.initial_window_residual,
            "final_window_residual": self.final_window_residual,
            "relative_change": self.relative_change,
            "convergence_tolerance": self.convergence_tolerance,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
        }


@dataclass(frozen=True)
class LineSearchEvaluation:
    """One detached line-search merit evaluation supplied by an adapter."""

    merit: float
    payload: object | None = None
    diagnostics: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LineSearchResult:
    """Deterministic result of the single common line-search policy loop."""

    accepted: bool
    factor: float | None
    reductions: int
    merit_history: tuple[float, ...]
    accepted_factors: tuple[float, ...]
    initial_merit: float
    min_alpha: float
    max_reductions: int
    armijo_c: float | None
    policy_source: str
    failure_reason: NonlinearFailureReason | None = None
    payload: object | None = None
    trial_diagnostics: tuple[Mapping[str, Any], ...] = ()
    policy_id: str = ROBUSTNESS_POLICY_ID
    policy_version: int = ROBUSTNESS_POLICY_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return stable line-search diagnostics without serializing payloads."""
        return {
            "accepted": self.accepted,
            "factor": self.factor,
            "accepted_factor": self.factor,
            "reductions": self.reductions,
            "total_reductions": self.reductions,
            "merit_history": list(self.merit_history),
            "accepted_factors": list(self.accepted_factors),
            "initial_merit": self.initial_merit,
            "min_alpha": self.min_alpha,
            "max_reductions": self.max_reductions,
            "armijo_c": self.armijo_c,
            "policy_source": self.policy_source,
            "failure_reason": self.failure_reason.value if self.failure_reason is not None else None,
            "trial_diagnostics": [dict(item) for item in self.trial_diagnostics],
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
        }


class UnifiedNonlinearRobustnessController:
    """Single formulation-neutral authority for stagnation and line search.

    The controller evaluates residual histories and detached merit callbacks;
    it never owns FEM physics or mutates a nonlinear accepted/trial state.
    Adapters may supply an explicit experimental or compatibility policy, but
    the policy loop and diagnostic schema remain common.
    """

    def __init__(
        self,
        *,
        policy_source: str | RobustnessPolicySource = RobustnessPolicySource.PUBLIC_DEFAULT,
        stagnation_enabled: bool = True,
        stagnation_window: int = 4,
        plateau_threshold: float = 1.0e-10,
        line_search_enabled: bool = True,
        min_alpha: float = 1.0e-4,
        max_reductions: int = 12,
        armijo_c: float | None = None,
    ) -> None:
        source = policy_source.value if isinstance(policy_source, RobustnessPolicySource) else str(policy_source)
        if source not in {item.value for item in RobustnessPolicySource}:
            raise ValueError(f"Unknown nonlinear robustness policy source {source!r}.")
        if stagnation_window < 1:
            raise ValueError("stagnation_window must be positive.")
        if not isfinite(float(plateau_threshold)) or not 0.0 <= float(plateau_threshold) < 1.0:
            raise ValueError("plateau_threshold must be finite and in [0, 1).")
        if not isfinite(float(min_alpha)) or not 0.0 <= float(min_alpha) <= 1.0:
            raise ValueError("min_alpha must be finite and in [0, 1].")
        if int(max_reductions) < 0:
            raise ValueError("max_reductions must be non-negative.")
        if armijo_c is not None and (not isfinite(float(armijo_c)) or not 0.0 <= float(armijo_c) < 1.0):
            raise ValueError("armijo_c must be None or finite in [0, 1).")
        self.policy_source = source
        self.stagnation_enabled = bool(stagnation_enabled)
        self.stagnation_window = int(stagnation_window)
        self.plateau_threshold = float(plateau_threshold)
        self.line_search_enabled = bool(line_search_enabled)
        self.min_alpha = float(min_alpha)
        self.max_reductions = int(max_reductions)
        self.armijo_c = None if armijo_c is None else float(armijo_c)

    @classmethod
    def from_options(
        cls,
        options: NonlinearRobustnessOptions | None,
        *,
        line_search_enabled: bool = True,
    ) -> "UnifiedNonlinearRobustnessController":
        """Build the common controller from explicit or public-default options."""
        if options is None:
            return cls(
                policy_source=RobustnessPolicySource.PUBLIC_DEFAULT,
                line_search_enabled=line_search_enabled,
            )
        if options.line_search == "off":
            return cls(
                policy_source=RobustnessPolicySource.EXPERIMENTAL_OVERRIDE,
                line_search_enabled=False,
            )
        if options.line_search == "existing":
            # Preserve the historical helper discrepancy as an explicit
            # compatibility configuration while using the common policy loop.
            return cls(
                policy_source=RobustnessPolicySource.EXPERIMENTAL_OVERRIDE,
                line_search_enabled=line_search_enabled,
                min_alpha=0.0,
                max_reductions=14,
                armijo_c=None,
            )
        return cls(
            policy_source=RobustnessPolicySource.EXPERIMENTAL_OVERRIDE,
            line_search_enabled=line_search_enabled,
            min_alpha=options.line_search_min_alpha,
            max_reductions=options.line_search_max_reductions,
            armijo_c=options.line_search_c,
        )

    def configuration_diagnostics(
        self,
        *,
        stagnation: Mapping[str, Any] | None = None,
        line_search: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return the policy identity and current deterministic diagnostics."""
        if line_search is None:
            line_items: list[Mapping[str, Any]] = []
        elif isinstance(line_search, Mapping):
            line_items = [line_search]
        else:
            line_items = list(line_search)
        return {
            "policy_id": ROBUSTNESS_POLICY_ID,
            "policy_version": ROBUSTNESS_POLICY_VERSION,
            "policy_source": self.policy_source,
            "stagnation": dict(stagnation or {
                "decision": "NOT_EVALUATED",
                "window_size": self.stagnation_window,
                "plateau_threshold": self.plateau_threshold,
                "policy_id": ROBUSTNESS_POLICY_ID,
                "policy_version": ROBUSTNESS_POLICY_VERSION,
            }),
            "line_search": {
                "enabled": self.line_search_enabled,
                "min_alpha": self.min_alpha,
                "max_reductions": self.max_reductions,
                "armijo_c": self.armijo_c,
                "policy_source": self.policy_source,
                "policy_id": ROBUSTNESS_POLICY_ID,
                "policy_version": ROBUSTNESS_POLICY_VERSION,
                "events": [dict(item) for item in line_items],
            },
        }

    def stagnation_decision(
        self,
        residual_history: Sequence[float],
        *,
        converged: bool = False,
        convergence_tolerance: float | None = None,
    ) -> StagnationDecision:
        """Evaluate the frozen four-sample residual plateau contract."""
        values = tuple(float(value) for value in residual_history)
        window = values[-self.stagnation_window:]
        if any(np.isinf(value) for value in values):
            return StagnationDecision(
                "NONFINITE",
                NonlinearFailureReason.INF_DETECTED,
                window,
                self.stagnation_window,
                self.plateau_threshold,
                window[0] if window else None,
                window[-1] if window else None,
                None,
                convergence_tolerance,
            )
        if any(np.isnan(value) for value in values):
            return StagnationDecision(
                "NONFINITE",
                NonlinearFailureReason.NAN_DETECTED,
                window,
                self.stagnation_window,
                self.plateau_threshold,
                window[0] if window else None,
                window[-1] if window else None,
                None,
                convergence_tolerance,
            )
        if converged:
            return StagnationDecision(
                "CONVERGED",
                None,
                window,
                self.stagnation_window,
                self.plateau_threshold,
                window[0] if window else None,
                window[-1] if window else None,
                None,
                convergence_tolerance,
            )
        if not self.stagnation_enabled:
            decision = "DISABLED"
        elif len(values) < self.stagnation_window:
            decision = "INSUFFICIENT_HISTORY"
        else:
            initial = window[0]
            final = window[-1]
            denominator = max(abs(initial), float(np.finfo(float).tiny))
            relative_change = (initial - final) / denominator
            if final >= initial * (1.0 - self.plateau_threshold):
                return StagnationDecision(
                    "STAGNATION",
                    NonlinearFailureReason.CONVERGENCE_STAGNATION,
                    window,
                    self.stagnation_window,
                    self.plateau_threshold,
                    initial,
                    final,
                    float(relative_change),
                    convergence_tolerance,
                )
            return StagnationDecision(
                "CONTINUE",
                None,
                window,
                self.stagnation_window,
                self.plateau_threshold,
                initial,
                final,
                float(relative_change),
                convergence_tolerance,
            )
        return StagnationDecision(
            decision,
            None,
            window,
            self.stagnation_window,
            self.plateau_threshold,
            window[0] if window else None,
            window[-1] if window else None,
            None,
            convergence_tolerance,
        )

    # Short aliases keep the contract discoverable without introducing another
    # policy implementation.
    check_stagnation = stagnation_decision
    evaluate_stagnation = stagnation_decision

    def line_search(
        self,
        initial_merit: float,
        evaluate: Callable[[float], LineSearchEvaluation | tuple[object, ...] | float],
        *,
        raise_on_failure: bool = True,
    ) -> LineSearchResult:
        """Run the one common alpha=1, halve-until-accepted policy loop."""
        initial = float(initial_merit)
        if not np.isfinite(initial):
            reason = NonlinearFailureReason.INF_DETECTED if np.isinf(initial) else NonlinearFailureReason.NAN_DETECTED
            raise NumericalConvergenceError(
                "Nonlinear line-search initial merit is non-finite.",
                reason=reason,
                diagnostics={
                    "policy_id": ROBUSTNESS_POLICY_ID,
                    "policy_version": ROBUSTNESS_POLICY_VERSION,
                    "policy_source": self.policy_source,
                    "initial_merit": None,
                },
            )
        if not self.line_search_enabled:
            result = LineSearchResult(
                accepted=False,
                factor=None,
                reductions=0,
                merit_history=(),
                accepted_factors=(),
                initial_merit=initial,
                min_alpha=self.min_alpha,
                max_reductions=self.max_reductions,
                armijo_c=self.armijo_c,
                policy_source=self.policy_source,
                failure_reason=NonlinearFailureReason.LINE_SEARCH_FAILURE,
                policy_id=ROBUSTNESS_POLICY_ID,
                policy_version=ROBUSTNESS_POLICY_VERSION,
            )
            if raise_on_failure:
                self._raise_line_search_failure(result)
            return result

        alpha = 1.0
        merits: list[float] = []
        trial_diagnostics: list[Mapping[str, Any]] = []
        last_payload: object | None = None
        for reductions in range(self.max_reductions + 1):
            try:
                evaluation = self._coerce_evaluation(evaluate(alpha))
            except (ValueError, FloatingPointError) as exc:
                evaluation = LineSearchEvaluation(
                    merit=float("inf"),
                    diagnostics={"evaluation_error": str(exc)},
                )
            merit = float(evaluation.merit)
            merits.append(merit)
            trial_diagnostics.append(dict(evaluation.diagnostics))
            last_payload = evaluation.payload
            if np.isfinite(merit):
                if self.armijo_c is None:
                    accepted = merit < initial
                else:
                    accepted = merit <= (1.0 - self.armijo_c * alpha) * initial
                if accepted:
                    result = LineSearchResult(
                        accepted=True,
                        factor=alpha,
                        reductions=reductions,
                        merit_history=tuple(merits),
                        accepted_factors=(alpha,),
                        initial_merit=initial,
                        min_alpha=self.min_alpha,
                        max_reductions=self.max_reductions,
                        armijo_c=self.armijo_c,
                        policy_source=self.policy_source,
                        payload=last_payload,
                        trial_diagnostics=tuple(trial_diagnostics),
                    )
                    return result
            alpha *= 0.5
            if alpha < self.min_alpha:
                break

        result = LineSearchResult(
            accepted=False,
            factor=None,
            reductions=max(len(merits) - 1, 0),
            merit_history=tuple(merits),
            accepted_factors=(),
            initial_merit=initial,
            min_alpha=self.min_alpha,
            max_reductions=self.max_reductions,
            armijo_c=self.armijo_c,
            policy_source=self.policy_source,
            failure_reason=NonlinearFailureReason.LINE_SEARCH_FAILURE,
            payload=None,
            trial_diagnostics=tuple(trial_diagnostics),
        )
        if raise_on_failure:
            self._raise_line_search_failure(result)
        return result

    @staticmethod
    def _coerce_evaluation(value: LineSearchEvaluation | tuple[object, ...] | float) -> LineSearchEvaluation:
        if isinstance(value, LineSearchEvaluation):
            return value
        if isinstance(value, tuple):
            if len(value) == 2:
                return LineSearchEvaluation(float(cast(Any, value[0])), value[1])
            if len(value) == 3:
                diagnostics = value[2]
                if not isinstance(diagnostics, Mapping):
                    raise TypeError("Line-search evaluation diagnostics must be a mapping.")
                return LineSearchEvaluation(float(cast(Any, value[0])), value[1], diagnostics)
            raise TypeError("Line-search tuple evaluations must contain two or three values.")
        return LineSearchEvaluation(float(cast(Any, value)))

    @staticmethod
    def _raise_line_search_failure(result: LineSearchResult) -> None:
        raise NumericalConvergenceError(
            "Nonlinear line search failed to satisfy its merit condition.",
            reason=NonlinearFailureReason.LINE_SEARCH_FAILURE,
            diagnostics=result.to_dict(),
        )


@dataclass(frozen=True)
class NonlinearRobustnessOptions:
    """Validated, opt-in controls used only by robustness experiments."""

    linear_solver: str = "spsolve"
    linear_permutation: str = "COLAMD"
    system_scaling: str = "none"
    residual_scaling: str = "none"
    line_search: str = "existing"
    line_search_min_alpha: float = 1.0e-4
    line_search_max_reductions: int = 14
    line_search_c: float = 1.0e-4

    @classmethod
    def from_parameters(cls, parameters: dict[str, object]) -> "NonlinearRobustnessOptions | None":
        """Return controls only when an explicit experimental parameter is present."""
        if not _PARAMETER_KEYS.intersection(parameters):
            return None
        options = cls(
            linear_solver=str(parameters.get("experimental_linear_solver", "spsolve")).lower(),
            linear_permutation=str(parameters.get("experimental_linear_permutation", "COLAMD")).upper(),
            system_scaling=str(parameters.get("experimental_system_scaling", "none")).lower(),
            residual_scaling=str(parameters.get("experimental_residual_scaling", "none")).lower(),
            line_search=str(parameters.get("experimental_line_search", "existing")).lower(),
            line_search_min_alpha=float(cast(Any, parameters.get("experimental_line_search_min_alpha", 1.0e-4))),
            line_search_max_reductions=int(cast(Any, parameters.get("experimental_line_search_max_reductions", 14))),
            line_search_c=float(cast(Any, parameters.get("experimental_line_search_c", 1.0e-4))),
        )
        options.validate()
        return options

    def validate(self) -> None:
        if self.linear_solver not in {"spsolve", "splu"}:
            raise ValueError("experimental_linear_solver must be 'spsolve' or 'splu'.")
        if self.linear_permutation not in _PERMUTATIONS:
            raise ValueError("experimental_linear_permutation is not a supported SciPy permutation.")
        if self.system_scaling not in {"none", "symmetric_diagonal"}:
            raise ValueError("experimental_system_scaling must be 'none' or 'symmetric_diagonal'.")
        if self.residual_scaling not in {"none", "row_max"}:
            raise ValueError("experimental_residual_scaling must be 'none' or 'row_max'.")
        if self.system_scaling != "none" and self.residual_scaling != "none":
            raise ValueError("Use one experimental linear scaling mechanism at a time.")
        if self.line_search not in {"existing", "off", "armijo"}:
            raise ValueError("experimental_line_search must be 'existing', 'off' or 'armijo'.")
        if not isfinite(self.line_search_min_alpha) or not 0.0 < self.line_search_min_alpha <= 1.0:
            raise ValueError("experimental_line_search_min_alpha must be in (0, 1].")
        if self.line_search_max_reductions < 0:
            raise ValueError("experimental_line_search_max_reductions must be non-negative.")
        if not isfinite(self.line_search_c) or not 0.0 <= self.line_search_c < 1.0:
            raise ValueError("experimental_line_search_c must be in [0, 1).")

    def to_dict(self) -> dict[str, Any]:
        return {
            "linear_solver": self.linear_solver,
            "linear_permutation": self.linear_permutation,
            "system_scaling": self.system_scaling,
            "residual_scaling": self.residual_scaling,
            "line_search": self.line_search,
            "line_search_min_alpha": self.line_search_min_alpha,
            "line_search_max_reductions": self.line_search_max_reductions,
            "line_search_c": self.line_search_c,
        }


def solve_scaled_system(
    matrix: csr_matrix,
    rhs: np.ndarray,
    options: NonlinearRobustnessOptions,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Solve one reduced Newton system with an explicitly selected experiment."""
    options.validate()
    values = csr_matrix(matrix)
    vector = np.asarray(rhs, dtype=float)
    if values.shape[0] != values.shape[1] or vector.shape != (values.shape[0],):
        raise ValueError("Experimental nonlinear linear system has incompatible dimensions.")
    if not np.all(np.isfinite(values.data)) or not np.all(np.isfinite(vector)):
        raise ValueError("Experimental nonlinear linear system must be finite.")

    factors = np.ones(values.shape[0], dtype=float)
    scaling = "none"
    if options.system_scaling == "symmetric_diagonal":
        diagonal = np.abs(values.diagonal())
        active = diagonal > 0.0
        factors[active] = 1.0 / np.sqrt(diagonal[active])
        effective = diags(factors) @ values @ diags(factors)
        effective_rhs = factors * vector
        scaling = options.system_scaling
    elif options.residual_scaling == "row_max":
        row_max = np.asarray(np.abs(values).sum(axis=1)).ravel()
        active = row_max > 0.0
        factors[active] = 1.0 / row_max[active]
        effective = diags(factors) @ values
        effective_rhs = factors * vector
        scaling = options.residual_scaling
    else:
        effective = values
        effective_rhs = vector

    if options.linear_solver == "splu":
        solution = splu(effective.tocsc(), permc_spec=options.linear_permutation).solve(effective_rhs)
        backend = "scipy.sparse.linalg.splu"
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("error", MatrixRankWarning)
            solution = spsolve(effective.tocsc(), effective_rhs, permc_spec=options.linear_permutation)
        backend = "scipy.sparse.linalg.spsolve"

    if options.system_scaling == "symmetric_diagonal":
        solution = factors * solution
    solution = np.asarray(solution, dtype=float)
    if not np.all(np.isfinite(solution)):
        raise ValueError("Experimental nonlinear linear solve returned a non-finite correction.")
    return solution, {
        "backend": backend,
        "permutation": options.linear_permutation,
        "scaling": scaling,
        "factor_min": float(np.min(factors)) if factors.size else 1.0,
        "factor_max": float(np.max(factors)) if factors.size else 1.0,
    }
