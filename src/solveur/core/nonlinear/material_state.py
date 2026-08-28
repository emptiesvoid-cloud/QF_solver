"""Path-dependent material state storage for nonlinear analyses."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
from typing import Any

import numpy as np

from solveur.core.errors import NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.elements.registry import ElementRegistry
from solveur.elements.solid.tet10 import Tet10Element
from solveur.materials.factory import MaterialFactory


MaterialStateTable = dict[int, list[dict[str, Any]]]


@dataclass
class StateTransaction:
    """Generic trial/committed transaction for nonlinear subsystem state.

    The committed object is preserved in place when it is a mapping, list or
    NumPy array so
    existing callers holding a reference cannot observe an accidental replace.
    This contract is intentionally independent of material names and can be
    reused for contact and continuation state.
    """

    committed: Any
    trial: Any | None = None
    _committed_digest_before_trial: str | None = field(default=None, init=False, repr=False)

    def begin_trial(self) -> Any:
        """Create a detached trial state from the committed state."""
        self._committed_digest_before_trial = state_digest(self.committed)
        self.trial = deepcopy(self.committed)
        return self.trial

    def commit(self) -> None:
        """Commit the trial while preserving the committed container identity."""
        if self.trial is None:
            raise RuntimeError("Cannot commit a state transaction without a trial.")
        self._ensure_committed_intact()
        _replace_state(self.committed, self.trial)
        self.trial = None
        self._committed_digest_before_trial = None

    def rollback(self) -> None:
        """Discard the trial state without touching committed state."""
        self._ensure_committed_intact()
        self.trial = None
        self._committed_digest_before_trial = None

    def _ensure_committed_intact(self) -> None:
        expected = self._committed_digest_before_trial
        if expected is None:
            return
        observed = state_digest(self.committed)
        if observed != expected:
            raise NumericalConvergenceError(
                "Committed nonlinear state changed during a trial transaction.",
                reason=NonlinearFailureReason.STATE_CORRUPTION,
                diagnostics={
                    "transaction": "generic",
                    "committed_digest_before_trial": expected,
                    "committed_digest_observed": observed,
                },
            )

    @property
    def committed_digest(self) -> str:
        """Return a deterministic digest useful for adversarial rollback tests."""
        return state_digest(self.committed)

    @property
    def trial_digest(self) -> str | None:
        """Return the trial digest, or ``None`` when no trial exists."""
        return None if self.trial is None else state_digest(self.trial)


@dataclass
class MaterialStateSession:
    """Transaction around committed and trial integration-point states."""

    committed: MaterialStateTable
    trial: MaterialStateTable | None = None
    _committed_digest_before_trial: str | None = field(default=None, init=False, repr=False)

    def begin_trial(self) -> MaterialStateTable:
        """Create a detached trial view from the last committed state."""
        self._committed_digest_before_trial = state_digest(self.committed)
        self.trial = copy_material_states(self.committed)
        return self.trial

    def commit(self) -> None:
        """Commit the current trial or reject an incomplete transaction."""
        if self.trial is None:
            raise RuntimeError("Cannot commit a material state session without a trial.")
        self._ensure_committed_intact()
        commit_material_states(self.committed, self.trial)
        self.trial = None
        self._committed_digest_before_trial = None

    def rollback(self) -> None:
        """Discard the current trial without touching committed state."""
        self._ensure_committed_intact()
        self.trial = None
        self._committed_digest_before_trial = None

    def _ensure_committed_intact(self) -> None:
        expected = self._committed_digest_before_trial
        if expected is None:
            return
        observed = state_digest(self.committed)
        if observed != expected:
            raise NumericalConvergenceError(
                "Committed material state changed during a trial transaction.",
                reason=NonlinearFailureReason.STATE_CORRUPTION,
                diagnostics={
                    "transaction": "material",
                    "committed_digest_before_trial": expected,
                    "committed_digest_observed": observed,
                },
            )


def state_digest(state: Any) -> str:
    """Hash nested state, including NumPy arrays, without exposing addresses."""
    payload = json.dumps(_canonical_state(state), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def state_is_finite(state: Any) -> bool:
    """Return whether every numeric value in a nested state is finite."""
    if isinstance(state, dict):
        return all(state_is_finite(value) for value in state.values())
    if isinstance(state, (list, tuple)):
        return all(state_is_finite(value) for value in state)
    if isinstance(state, np.ndarray):
        return bool(np.all(np.isfinite(state)))
    if isinstance(state, (bool, int, float, np.number)):
        return bool(np.isfinite(state))
    return True


def _canonical_state(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _canonical_state(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonical_state(item) for item in value]
    if hasattr(value, "tolist"):
        return _canonical_state(value.tolist())
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    raise TypeError(f"Unsupported state value {type(value).__name__!r} for deterministic digest.")


def _replace_state(target: Any, source: Any) -> None:
    if isinstance(target, dict) and isinstance(source, dict):
        target.clear()
        target.update(deepcopy(source))
        return
    if isinstance(target, list) and isinstance(source, list):
        target[:] = deepcopy(source)
        return
    if isinstance(target, np.ndarray) and isinstance(source, np.ndarray):
        if target.shape != source.shape:
            raise TypeError("StateTransaction.commit requires matching array shapes.")
        target[...] = source
        return
    raise TypeError("StateTransaction.commit requires matching mapping, list or array state.")


def initial_material_states(model: FiniteElementModel) -> MaterialStateTable:
    """Create empty integration-point states for path-dependent materials."""
    table: MaterialStateTable = {}
    for index, definition in enumerate(model.elements):
        material = MaterialFactory.create(model.materials[definition.material])
        if not hasattr(material, "initial_state"):
            continue
        if definition.type == "TET10":
            quadrature = model.analysis.parameters.get("tet10_nonlinear_quadrature", "hammer4")
            element = Tet10Element(material, nonlinear_quadrature=str(quadrature))
            count = int(element.nonlinear_integration_point_count)
        else:
            element = ElementRegistry.get(definition.type).factory(material)
            count = int(getattr(element, "integration_point_count", 0))
        if count > 0:
            table[index] = [deepcopy(material.initial_state()) for _ in range(count)]
    return table


def copy_material_states(states: MaterialStateTable | None) -> MaterialStateTable:
    """Return a detached copy safe for trial Newton iterations."""
    return deepcopy(states or {})


def commit_material_states(target: MaterialStateTable, source: MaterialStateTable) -> None:
    """Replace committed states with converged trial states."""
    target.clear()
    target.update(copy_material_states(source))


def material_states_to_dict(states: MaterialStateTable | None) -> list[dict[str, Any]]:
    """Serialize integration-point material states for result JSON."""
    rows: list[dict[str, Any]] = []
    for element_index in sorted((states or {}).keys()):
        points = []
        for point_index, state in enumerate(states[element_index]):
            points.append({"index": point_index, **_jsonable_state(state)})
        rows.append({"element": element_index, "integration_points": points})
    return rows


def _jsonable_state(state: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in state.items():
        if key in {"strain", "plastic_dissipation"}:
            continue
        if isinstance(value, (bool, str)):
            output[key] = value
        elif isinstance(value, (int, float)):
            output[key] = float(value)
        elif isinstance(value, list):
            output[key] = [float(item) if isinstance(item, (int, float)) else item for item in value]
    return output
