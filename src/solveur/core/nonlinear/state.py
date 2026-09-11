"""Formulation-neutral nonlinear state and accepted-increment transactions.

This module deliberately stores only evolving solve state.  Meshes, element
connectivity, immutable material definitions and global matrices remain owned
by model/assembly objects and are never copied by a transaction.
"""

from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Mapping

import numpy as np

from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.contracts import NonlinearFailureReason


_STATE_SCHEMA_VERSION = 1


@dataclass
class NonlinearState:
    """Detached evolving state for one nonlinear accepted or trial increment.

    The payload is intentionally formulation-neutral.  Empty material, contact
    and continuation mappings are valid: a stateless contribution does not pay
    for artificial history.  Inputs are detached on construction, but the
    state remains inspectable/mutable within a transaction so accidental
    external accepted-state mutation can be detected rather than overwritten.
    """

    displacement: np.ndarray
    load_factor: float = 0.0
    material_state: Mapping[str | int, Any] = field(default_factory=dict)
    contact_state: Mapping[str | int, Any] = field(default_factory=dict)
    continuation_state: Mapping[str | int, Any] = field(default_factory=dict)
    accepted_increment_metadata: Mapping[str | int, Any] = field(default_factory=dict)
    schema_version: int = _STATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        displacement = np.array(self.displacement, copy=True)
        # Preserve floating-point precision in detached snapshots.  Integer
        # displacement inputs are converted because nonlinear updates are
        # floating-point operations and must not fail on in-place correction.
        if displacement.dtype.kind not in "fc":
            displacement = displacement.astype(float)
        self.displacement = displacement
        self.load_factor = float(self.load_factor)
        self.material_state = _detach_mapping(self.material_state, "material_state")
        self.contact_state = _detach_mapping(self.contact_state, "contact_state")
        self.continuation_state = _detach_mapping(self.continuation_state, "continuation_state")
        self.accepted_increment_metadata = _detach_mapping(
            self.accepted_increment_metadata, "accepted_increment_metadata"
        )
        self.validate()

    def detached_copy(self) -> NonlinearState:
        """Return a full detached copy suitable for a trial transaction."""
        return NonlinearState(
            displacement=self.displacement,
            load_factor=self.load_factor,
            material_state=self.material_state,
            contact_state=self.contact_state,
            continuation_state=self.continuation_state,
            accepted_increment_metadata=self.accepted_increment_metadata,
            schema_version=self.schema_version,
        )

    def validate(self) -> None:
        """Validate finite scalar/vector data and canonical state payloads."""
        if self.schema_version != _STATE_SCHEMA_VERSION:
            raise ValueError(f"Unsupported nonlinear state schema version {self.schema_version!r}.")
        if (
            self.displacement.ndim != 1
            or self.displacement.dtype.hasobject
            or not np.issubdtype(self.displacement.dtype, np.number)
            or not np.all(np.isfinite(self.displacement))
        ):
            raise ValueError("NonlinearState displacement must be a finite one-dimensional NumPy vector.")
        if not np.isfinite(self.load_factor):
            raise ValueError("NonlinearState load_factor must be finite.")
        _validate_payload(self.material_state, "material_state")
        _validate_payload(self.contact_state, "contact_state")
        _validate_payload(self.continuation_state, "continuation_state")
        _validate_payload(self.accepted_increment_metadata, "accepted_increment_metadata")

    @property
    def component_digests(self) -> dict[str, str]:
        """Return deterministic component digests for rollback and evidence."""
        return {
            "displacement": deterministic_state_digest(self.displacement),
            "load_factor": deterministic_state_digest(self.load_factor),
            "material_state": deterministic_state_digest(self.material_state),
            "contact_state": deterministic_state_digest(self.contact_state),
            "continuation_state": deterministic_state_digest(self.continuation_state),
            "accepted_increment_metadata": deterministic_state_digest(self.accepted_increment_metadata),
        }

    @property
    def digest(self) -> str:
        """Return a deterministic digest of the complete composite state."""
        return deterministic_state_digest(
            {
                "schema_version": self.schema_version,
                "displacement": self.displacement,
                "load_factor": self.load_factor,
                "material_state": self.material_state,
                "contact_state": self.contact_state,
                "continuation_state": self.continuation_state,
                "accepted_increment_metadata": self.accepted_increment_metadata,
            }
        )


@dataclass
class NonlinearStateTransaction:
    """Atomic accepted-increment transaction around a :class:`NonlinearState`.

    A commit prepares and validates a detached replacement before publishing it.
    The accepted object is replaced as one composite state, so a caller cannot
    observe a material/contact/continuation partial commit through this API.
    """

    _accepted_state: NonlinearState
    _trial_state: NonlinearState | None = field(default=None, init=False, repr=False)
    _accepted_digest_before_trial: str | None = field(default=None, init=False, repr=False)
    _commit_count: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        self._accepted_state = self._accepted_state.detached_copy()

    @property
    def accepted_state(self) -> NonlinearState:
        """Return the current accepted state for inspection.

        The transaction detects any external mutation of this object while a
        trial is open.  Callers requiring isolation should use ``detached_copy``.
        """
        return self._accepted_state

    @property
    def trial_state(self) -> NonlinearState | None:
        """Return the detached open trial, if any."""
        return self._trial_state

    @property
    def commit_count(self) -> int:
        """Return accepted commits performed by this transaction."""
        return self._commit_count

    @property
    def accepted_component_digests(self) -> dict[str, str]:
        return dict(self._accepted_state.component_digests)

    @property
    def accepted_digest(self) -> str:
        return self._accepted_state.digest

    def begin_trial(self) -> NonlinearState:
        """Open a detached trial state without changing the accepted state."""
        if self._trial_state is not None:
            raise RuntimeError("A nonlinear state trial is already active.")
        self._accepted_state.validate()
        self._accepted_digest_before_trial = self._accepted_state.digest
        self._trial_state = self._accepted_state.detached_copy()
        return self._trial_state

    def replace_trial(self, state: NonlinearState) -> NonlinearState:
        """Replace the trial with a detached, validated candidate state."""
        self._require_trial()
        prepared = state.detached_copy()
        prepared.validate()
        self._trial_state = prepared
        return self._trial_state

    def commit(self) -> NonlinearState:
        """Publish a complete valid trial state or leave accepted state intact."""
        trial = self._require_trial()
        self._ensure_accepted_intact()
        try:
            prepared = trial.detached_copy()
            prepared.validate()
        except (TypeError, ValueError) as exc:
            raise NumericalConvergenceError(
                "Nonlinear state commit validation failed; accepted state was not published.",
                reason=NonlinearFailureReason.STATE_CORRUPTION,
                diagnostics={"transaction": "composite", "stage": "prepare_commit", "error": str(exc)},
            ) from exc

        self._accepted_state = prepared
        self._trial_state = None
        self._accepted_digest_before_trial = None
        self._commit_count += 1
        return self._accepted_state

    def rollback(self) -> None:
        """Discard a trial after proving the accepted state was not corrupted."""
        self._require_trial()
        self._ensure_accepted_intact()
        self._trial_state = None
        self._accepted_digest_before_trial = None

    def _require_trial(self) -> NonlinearState:
        if self._trial_state is None:
            raise RuntimeError("A nonlinear state transaction requires begin_trial() first.")
        return self._trial_state

    def _ensure_accepted_intact(self) -> None:
        expected = self._accepted_digest_before_trial
        if expected is None:
            return
        observed = self._accepted_state.digest
        if observed != expected:
            raise NumericalConvergenceError(
                "Accepted composite nonlinear state changed during an open trial.",
                reason=NonlinearFailureReason.STATE_CORRUPTION,
                diagnostics={
                    "transaction": "composite",
                    "accepted_digest_before_trial": expected,
                    "accepted_digest_observed": observed,
                },
            )


def deterministic_state_digest(value: Any) -> str:
    """Hash supported state data independent of addresses, repr or map order."""
    payload = json.dumps(_canonical_payload(value), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _detach_mapping(value: Mapping[str | int, Any], name: str) -> dict[str | int, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"NonlinearState {name} must be a mapping.")
    return deepcopy(dict(value))


def _validate_payload(value: Any, path: str) -> None:
    if value is None or isinstance(value, (str, bool, np.bool_, int, np.integer)):
        return
    if isinstance(value, (float, np.floating)):
        if not np.isfinite(value):
            raise ValueError(f"NonlinearState {path} contains a non-finite scalar.")
        return
    if isinstance(value, np.ndarray):
        if value.dtype.hasobject or not (
            np.issubdtype(value.dtype, np.number) or np.issubdtype(value.dtype, np.bool_)
        ):
            raise TypeError(f"NonlinearState {path} array must have a non-object numeric dtype.")
        if not np.all(np.isfinite(value)):
            raise ValueError(f"NonlinearState {path} array contains non-finite values.")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            _validate_mapping_key(key, path)
            _validate_payload(item, f"{path}[{key!r}]")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_payload(item, f"{path}[{index}]")
        return
    raise TypeError(f"Unsupported nonlinear state payload at {path}: {type(value).__name__}.")


def _validate_mapping_key(key: Any, path: str) -> None:
    if not isinstance(key, (str, int, np.integer)):
        raise TypeError(f"NonlinearState {path} mapping keys must be strings or integers.")


def _canonical_payload(value: Any) -> Any:
    _validate_payload(value, "digest")
    if value is None:
        return {"type": "none"}
    if isinstance(value, (bool, np.bool_)):
        return {"type": "bool", "value": bool(value)}
    if isinstance(value, str):
        return {"type": "str", "value": value}
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return {"type": "int", "value": str(int(value))}
    if isinstance(value, (float, np.floating)):
        return {"type": "float", "value": float(value).hex()}
    if isinstance(value, np.ndarray):
        contiguous = np.ascontiguousarray(value)
        return {
            "type": "ndarray",
            "dtype": contiguous.dtype.str,
            "shape": list(contiguous.shape),
            "data_base64": base64.b64encode(contiguous.tobytes(order="C")).decode("ascii"),
        }
    if isinstance(value, Mapping):
        items = [(_canonical_mapping_key(key), _canonical_payload(item)) for key, item in value.items()]
        return {"type": "mapping", "entries": sorted(items, key=lambda item: json.dumps(item[0], sort_keys=True))}
    if isinstance(value, list):
        return {"type": "list", "items": [_canonical_payload(item) for item in value]}
    if isinstance(value, tuple):
        return {"type": "tuple", "items": [_canonical_payload(item) for item in value]}
    raise TypeError(f"Unsupported nonlinear state value {type(value).__name__!r} for deterministic digest.")


def _canonical_mapping_key(key: Any) -> dict[str, str]:
    _validate_mapping_key(key, "digest")
    if isinstance(key, str):
        return {"type": "str", "value": key}
    return {"type": "int", "value": str(int(key))}


def canonical_state_payload(value: Any) -> Any:
    """Return the typed, JSON-safe representation used by state persistence."""

    return _canonical_payload(value)


def _decode_mapping_key(payload: Any) -> str | int:
    if not isinstance(payload, dict) or payload.get("type") not in {"str", "int"}:
        raise ValueError("Invalid canonical mapping key payload")
    if payload["type"] == "str":
        return str(payload["value"])
    return int(payload["value"])


def decode_canonical_state_payload(payload: Any) -> Any:
    """Decode a payload produced by :func:`canonical_state_payload`.

    The decoder accepts only the frozen nonlinear-state types and never
    deserializes arbitrary Python objects or pickle data.
    """

    if not isinstance(payload, dict):
        raise ValueError("Canonical state payload must be a mapping")
    payload_type = payload.get("type")
    if payload_type == "none":
        return None
    if payload_type == "bool":
        return bool(payload["value"])
    if payload_type == "str":
        return str(payload["value"])
    if payload_type == "int":
        return int(payload["value"])
    if payload_type == "float":
        return float.fromhex(str(payload["value"]))
    if payload_type == "ndarray":
        dtype: np.dtype = np.dtype(str(payload["dtype"]))
        if dtype.hasobject or not (
            np.issubdtype(dtype, np.number) or np.issubdtype(dtype, np.bool_)
        ):
            raise ValueError("Canonical arrays must have a numeric non-object dtype")
        shape = tuple(int(axis) for axis in payload["shape"])
        if any(axis < 0 for axis in shape):
            raise ValueError("Canonical array shape cannot contain negative axes")
        raw = base64.b64decode(str(payload["data_base64"]), validate=True)
        expected_size = dtype.itemsize
        for axis in shape:
            expected_size *= axis
        if len(raw) != expected_size:
            raise ValueError("Canonical array byte count does not match its shape")
        return np.frombuffer(raw, dtype=dtype).copy().reshape(shape)
    if payload_type == "mapping":
        entries = payload.get("entries")
        if not isinstance(entries, list):
            raise ValueError("Canonical mapping entries must be a list")
        result: dict[str | int, Any] = {}
        for entry in entries:
            if not isinstance(entry, list) or len(entry) != 2:
                raise ValueError("Invalid canonical mapping entry")
            key = _decode_mapping_key(entry[0])
            if key in result:
                raise ValueError("Duplicate canonical mapping key")
            result[key] = decode_canonical_state_payload(entry[1])
        return result
    if payload_type == "list":
        items = payload.get("items")
        if not isinstance(items, list):
            raise ValueError("Canonical list items must be a list")
        return [decode_canonical_state_payload(item) for item in items]
    if payload_type == "tuple":
        items = payload.get("items")
        if not isinstance(items, list):
            raise ValueError("Canonical tuple items must be a list")
        return tuple(decode_canonical_state_payload(item) for item in items)
    raise ValueError(f"Unsupported canonical state payload type: {payload_type!r}")
