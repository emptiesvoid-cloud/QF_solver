"""Contracts shared by small-strain nonlinear solid mechanics."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Protocol, runtime_checkable

import numpy as np


class NonlinearFailureReason(str, Enum):
    """Machine-readable reasons for a failed nonlinear increment."""

    MAX_ITERATIONS = "MAX_ITERATIONS"
    MIN_INCREMENT_REACHED = "MIN_INCREMENT_REACHED"
    LINEAR_SOLVER_FAILURE = "LINEAR_SOLVER_FAILURE"
    SINGULAR_TANGENT = "SINGULAR_TANGENT"
    NAN_DETECTED = "NAN_DETECTED"
    MATERIAL_UPDATE_FAILURE = "MATERIAL_UPDATE_FAILURE"
    INVALID_ELEMENT = "INVALID_ELEMENT"
    STATE_CORRUPTION = "STATE_CORRUPTION"
    LINE_SEARCH_FAILURE = "LINE_SEARCH_FAILURE"


@dataclass(frozen=True)
class ConstitutiveResponse:
    """Immutable result of one constitutive trial evaluation."""

    stress: np.ndarray
    tangent: np.ndarray
    trial_state: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ConstitutiveModel(Protocol):
    """Protocol for a material law independent of element and global solver."""

    def evaluate(
        self,
        strain: np.ndarray,
        committed_state: Mapping[str, Any] | None = None,
    ) -> ConstitutiveResponse:
        """Return stress, algorithmic tangent and a detached trial state."""


def evaluate_constitutive(
    material: object,
    strain: np.ndarray,
    committed_state: Mapping[str, Any] | None = None,
) -> ConstitutiveResponse:
    """Adapt existing material APIs to the common constitutive contract.

    The adapter deliberately preserves the existing ``stress_tangent_state``
    semantics while allowing linear materials to use the simpler legacy API.
    It is the compatibility seam for the incremental element migration.
    """

    strain = np.asarray(strain, dtype=float)
    evaluate = getattr(material, "evaluate", None)
    if callable(evaluate):
        response = evaluate(strain, committed_state)
        if not isinstance(response, ConstitutiveResponse):
            raise TypeError("ConstitutiveModel.evaluate must return ConstitutiveResponse.")
        return response

    state_evaluator = getattr(material, "stress_tangent_state", None)
    if callable(state_evaluator):
        stress, tangent, trial_state = state_evaluator(strain, dict(committed_state or {}))
        return ConstitutiveResponse(
            np.asarray(stress, dtype=float),
            np.asarray(tangent, dtype=float),
            dict(trial_state),
            {"stateful": True},
        )

    stress, tangent = material.stress_tangent(strain)
    return ConstitutiveResponse(
        np.asarray(stress, dtype=float),
        np.asarray(tangent, dtype=float),
        {},
        {"stateful": False},
    )
