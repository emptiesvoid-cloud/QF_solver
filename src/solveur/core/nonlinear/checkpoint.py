"""Storage-neutral nonlinear checkpoint contracts.

Schema v2 is deliberately expressed in terms of one accepted
``NonlinearState``.  The legacy v1 dataclass remains available as a
compatibility input, but new persistence is promoted to v2 by the storage
adapter.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol, cast

import numpy as np

from solveur.core.errors import InfrastructureError, InputValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.material_state import MaterialStateTable, copy_material_states
from solveur.core.nonlinear.state import NonlinearState, deterministic_state_digest
from solveur.io.checkpoint_common import checkpoint_signature
from solveur.io.model_writer import model_to_dict


@dataclass(frozen=True)
class NonlinearCheckpoint:
    """Legacy schema-v1 committed nonlinear state.

    This type is retained so callers that construct historical checkpoint
    records keep working. ``NpzNonlinearCheckpointStore.save`` promotes it to
    :class:`NonlinearCheckpointV2` before writing.
    """

    model_signature: str
    completed_step: int
    load_factor: float
    displacement: np.ndarray
    material_states: MaterialStateTable
    continuation_state: dict[str, object] = field(default_factory=dict)
    schema_version: int = 1

    def validate(self, expected_dofs: int | None = None) -> None:
        if self.schema_version != 1 or not self.model_signature:
            raise InputValidationError("Unsupported or incomplete nonlinear checkpoint metadata.")
        if self.completed_step < 0 or not np.isfinite(self.load_factor):
            raise InputValidationError("Nonlinear checkpoint step or load factor is invalid.")
        if self.displacement.ndim != 1 or not np.all(np.isfinite(self.displacement)):
            raise InputValidationError("Nonlinear checkpoint displacement must be a finite vector.")
        if expected_dofs is not None and self.displacement.size != expected_dofs:
            raise InputValidationError(
                f"Nonlinear checkpoint has {self.displacement.size} dofs; the model requires {expected_dofs}."
            )
        _validate_material_states(self.material_states)
        if not isinstance(self.continuation_state, dict) or not _finite_tree(self.continuation_state):
            raise InputValidationError("Nonlinear checkpoint continuation state is invalid.")


@dataclass(frozen=True)
class NonlinearCheckpointV2:
    """Schema-v2 representation of exactly one accepted ``NonlinearState``."""

    model_signature: str
    completed_step: int
    accepted_state: NonlinearState
    state_topology: dict[str, Any]
    component_digests: dict[str, str]
    composite_digest: str
    migration_metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 2
    state_schema_version: int = 1

    @classmethod
    def from_state(
        cls,
        *,
        model_signature: str,
        completed_step: int,
        state: NonlinearState,
        state_topology: dict[str, Any] | None = None,
        migration_metadata: dict[str, Any] | None = None,
    ) -> "NonlinearCheckpointV2":
        prepared = state.detached_copy()
        prepared.validate()
        if not model_signature:
            raise InputValidationError("Schema-v2 nonlinear checkpoint requires a model signature.")
        if completed_step < 0:
            raise InputValidationError("Schema-v2 nonlinear checkpoint step must be non-negative.")
        topology = deepcopy(state_topology or build_state_topology(None, prepared))
        checkpoint = cls(
            model_signature=str(model_signature),
            completed_step=int(completed_step),
            accepted_state=prepared,
            state_topology=topology,
            component_digests=prepared.component_digests,
            composite_digest=prepared.digest,
            migration_metadata=deepcopy(migration_metadata or {}),
        )
        checkpoint.validate()
        return checkpoint

    # Compatibility projections used by the pre-v2 solver session. All
    # values originate in the one accepted composite state above.
    @property
    def load_factor(self) -> float:
        return self.accepted_state.load_factor

    @property
    def displacement(self) -> np.ndarray:
        return self.accepted_state.displacement

    @property
    def material_states(self) -> MaterialStateTable:
        material = cast(Mapping[int, list[dict[str, Any]]], self.accepted_state.material_state)
        return dict(material)

    @property
    def continuation_state(self) -> dict[str, object]:
        return cast(dict[str, object], self.accepted_state.continuation_state)

    @property
    def contact_state(self) -> dict[str | int, Any]:
        return dict(self.accepted_state.contact_state)

    @property
    def accepted_increment_metadata(self) -> dict[str | int, Any]:
        return dict(self.accepted_state.accepted_increment_metadata)

    def validate(
        self,
        expected_dofs: int | None = None,
        *,
        expected_model_signature: str | None = None,
        expected_topology: dict[str, Any] | None = None,
    ) -> None:
        if self.schema_version != 2 or self.state_schema_version != self.accepted_state.schema_version:
            raise InputValidationError("Unsupported or incomplete schema-v2 nonlinear checkpoint metadata.")
        if not self.model_signature or self.completed_step < 0:
            raise InputValidationError("Schema-v2 nonlinear checkpoint metadata is invalid.")
        if expected_model_signature is not None and self.model_signature != expected_model_signature:
            raise InputValidationError("Nonlinear checkpoint does not match the requested model signature.")
        try:
            self.accepted_state.validate()
        except (TypeError, ValueError) as exc:
            if "finite" in str(exc).lower():
                raise _state_corruption("Schema-v2 checkpoint contains a non-finite accepted state.", exc) from exc
            raise InputValidationError("Schema-v2 checkpoint contains an invalid accepted state.") from exc
        if expected_dofs is not None and self.accepted_state.displacement.size != expected_dofs:
            raise InputValidationError(
                f"Nonlinear checkpoint has {self.accepted_state.displacement.size} dofs; the model requires {expected_dofs}."
            )
        if not isinstance(self.state_topology, dict):
            raise InputValidationError("Schema-v2 checkpoint state topology is invalid.")
        _validate_state_topology_payload(self.state_topology, self.accepted_state, expected_dofs)
        if expected_topology is not None and deterministic_state_digest(self.state_topology) != deterministic_state_digest(
            expected_topology
        ):
            raise InputValidationError("Schema-v2 checkpoint state topology does not match the model.")
        expected_components = self.accepted_state.component_digests
        if self.component_digests != expected_components:
            raise _state_corruption("Schema-v2 checkpoint component digest mismatch.")
        if self.composite_digest != self.accepted_state.digest:
            raise _state_corruption("Schema-v2 checkpoint composite digest mismatch.")


def _state_corruption(message: str, cause: Exception | None = None) -> NumericalConvergenceError:
    error = NumericalConvergenceError(message, reason=NonlinearFailureReason.STATE_CORRUPTION)
    if cause is not None:
        error.diagnostics["cause"] = str(cause)
    return error


class NonlinearCheckpointStore(Protocol):
    """Persistence boundary injected into the nonlinear solver."""

    def signature(self, payload: dict[str, object]) -> str: ...

    def load(
        self,
        path: str | Path,
        *,
        model: FiniteElementModel | None = None,
        expected_model_signature: str | None = None,
        expected_legacy_model_signature: str | None = None,
        expected_dofs: int | None = None,
        expected_topology: dict[str, Any] | None = None,
    ) -> NonlinearCheckpointV2: ...

    def save(
        self,
        path: str | Path,
        checkpoint: NonlinearCheckpoint | NonlinearCheckpointV2,
        *,
        keep_step: bool = False,
    ) -> tuple[Path, ...]: ...


@dataclass(frozen=True)
class NonlinearCheckpointSettings:
    """Validated checkpoint controls for fixed nonlinear load paths."""

    path: str | None
    interval: int
    keep_steps: bool
    restart_from: str | None

    @classmethod
    def from_parameters(cls, parameters: dict[str, object], total_steps: int) -> "NonlinearCheckpointSettings":
        path = _optional_npz_path(parameters.get("checkpoint_path"), "checkpoint_path")
        restart = _optional_npz_path(parameters.get("restart_from"), "restart_from")
        keep = parameters.get("checkpoint_keep_steps", False)
        if not isinstance(keep, bool):
            raise InputValidationError("checkpoint_keep_steps must be a boolean.")
        raw_interval = parameters.get("checkpoint_interval", total_steps)
        if isinstance(raw_interval, bool) or not isinstance(raw_interval, int) or raw_interval <= 0:
            raise InputValidationError("checkpoint_interval must be a positive integer.")
        if "checkpoint_interval" in parameters and path is None:
            raise InputValidationError("checkpoint_interval requires checkpoint_path.")
        if keep and path is None:
            raise InputValidationError("checkpoint_keep_steps requires checkpoint_path.")
        return cls(path, raw_interval, keep, restart)

    @property
    def enabled(self) -> bool:
        return self.path is not None or self.restart_from is not None

    def should_save(self, step: int, total_steps: int, *, final: bool = False) -> bool:
        """Return whether an accepted step should be persisted.

        Adaptive continuation does not know its final accepted-step number in
        advance.  ``final`` lets that controller force the terminal accepted
        state into the canonical checkpoint without changing the interval
        semantics for fixed load control.
        """

        return self.path is not None and (step % self.interval == 0 or step == total_steps or final)


@dataclass
class NonlinearCheckpointSession:
    """Coordinate signature validation, restart and atomic saves."""

    settings: NonlinearCheckpointSettings
    store: NonlinearCheckpointStore | None
    signature: str
    total_steps: int
    restart_step: int = 0
    files: list[str] = field(default_factory=list)
    model: FiniteElementModel | None = field(default=None, repr=False)
    persisted_signature: str = field(default="", init=False)

    @classmethod
    def create(
        cls,
        model: FiniteElementModel,
        total_steps: int,
        store: NonlinearCheckpointStore | None,
    ) -> "NonlinearCheckpointSession":
        settings = NonlinearCheckpointSettings.from_parameters(model.analysis.parameters, total_steps)
        if settings.enabled and store is None:
            raise InfrastructureError("Nonlinear checkpoint persistence is not configured.")
        signature = store.signature(_signature_payload(model)) if settings.enabled and store else ""
        return cls(settings, store, signature, total_steps, model=model)

    def restore_state(
        self,
        initial_state: NonlinearState,
        *,
        load_factors: list[float] | None = None,
        load_factor_limit: float | None = None,
        require_continuation: bool = False,
        allow_variable_step_count: bool = False,
    ) -> NonlinearState:
        """Restore one detached accepted composite state atomically.

        The store performs decoding, schema, topology and digest validation
        before this method returns.  No caller-owned displacement or material
        mapping is modified while a restore is being validated.
        """

        initial = initial_state.detached_copy()
        if self.settings.restart_from is None:
            self.restart_step = 0
            return initial
        if self.store is None:
            raise InfrastructureError("Nonlinear checkpoint persistence is not configured.")

        if self.model is not None:
            checkpoint = self.store.load(
                self.settings.restart_from,
                model=self.model,
                expected_legacy_model_signature=self.signature,
                expected_dofs=int(initial.displacement.size),
            )
        else:
            checkpoint = self.store.load(
                self.settings.restart_from,
                expected_model_signature=self.signature,
                expected_dofs=int(initial.displacement.size),
            )
        checkpoint.validate(initial.displacement.size)
        if self.model is None and checkpoint.model_signature != self.signature:
            raise InputValidationError("Nonlinear checkpoint does not match the physical model or load path.")
        if not allow_variable_step_count and checkpoint.completed_step > self.total_steps:
            raise InputValidationError("Nonlinear checkpoint is beyond the requested load path.")

        if load_factors is not None:
            expected_factor = 0.0 if checkpoint.completed_step == 0 else load_factors[checkpoint.completed_step - 1]
            if not np.isclose(checkpoint.load_factor, expected_factor, rtol=0.0, atol=1.0e-14):
                raise InputValidationError("Nonlinear checkpoint load-factor metadata is inconsistent.")
        if load_factor_limit is not None:
            limit = abs(float(load_factor_limit))
            if not np.isfinite(limit) or limit <= 0.0:
                raise InputValidationError("Nonlinear checkpoint load-factor limit must be finite and positive.")
            if abs(checkpoint.load_factor) > limit + 1.0e-12:
                raise InputValidationError("Nonlinear checkpoint load factor is outside the requested continuation envelope.")
        if require_continuation and not checkpoint.continuation_state:
            raise InputValidationError("Nonlinear checkpoint does not contain continuation state.")

        _validate_state_topology(initial.material_state, checkpoint.material_states)
        self.restart_step = checkpoint.completed_step
        self.persisted_signature = checkpoint.model_signature
        return checkpoint.accepted_state.detached_copy()

    def restore(
        self,
        displacement: np.ndarray,
        material_states: MaterialStateTable,
        load_factors: list[float],
    ) -> tuple[np.ndarray, MaterialStateTable]:
        restored = self.restore_state(
            NonlinearState(
                displacement=displacement,
                material_state=material_states,
            ),
            load_factors=load_factors,
        )
        return restored.displacement.copy(), copy_material_states(restored.material_state)

    def restore_continuation(
        self,
        displacement: np.ndarray,
        material_states: MaterialStateTable,
        target_load_factor: float,
        load_factor_limit: float | None = None,
    ) -> tuple[np.ndarray, MaterialStateTable, dict[str, object] | None]:
        """Restore an arc-length checkpoint without assuming a fixed load path."""

        restored = self.restore_state(
            NonlinearState(
                displacement=displacement,
                material_state=material_states,
            ),
            load_factor_limit=(
                float(load_factor_limit)
                if load_factor_limit is not None
                else max(abs(target_load_factor), 1.0)
            ),
            require_continuation=True,
        )
        return (
            restored.displacement.copy(),
            copy_material_states(restored.material_state),
            dict(restored.continuation_state),
        )

    def save_state(
        self,
        step: int,
        accepted_state: NonlinearState,
        *,
        final: bool = False,
        migration_metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Persist one already accepted composite state as schema v2."""

        if not self.settings.should_save(step, self.total_steps, final=final):
            return
        if self.store is None or self.settings.path is None:
            raise InfrastructureError("Nonlinear checkpoint persistence is not configured.")
        prepared = accepted_state.detached_copy()
        prepared.validate()
        topology = build_state_topology(self.model, prepared)
        signature = (
            model_signature_v2(self.model, topology)
            if self.model is not None
            else self.signature
        )
        checkpoint = NonlinearCheckpointV2.from_state(
            model_signature=signature,
            completed_step=step,
            state=prepared,
            state_topology=topology,
            migration_metadata={
                "writer": "NonlinearCheckpointSession.save_state",
                "source_schema_version": 2,
                **dict(migration_metadata or {}),
            },
        )
        written = self.store.save(self.settings.path, checkpoint, keep_step=self.settings.keep_steps)
        self.persisted_signature = checkpoint.model_signature
        self.files.extend(str(path) for path in written if str(path) not in self.files)

    def save(
        self,
        step: int,
        load_factor: float,
        displacement: np.ndarray,
        material_states: MaterialStateTable,
        continuation_state: dict[str, object] | None = None,
    ) -> None:
        self.save_state(
            step,
            NonlinearState(
                displacement=displacement,
                load_factor=load_factor,
                material_state=copy_material_states(material_states),
                continuation_state=dict(continuation_state or {}),
            ),
        )


def _signature_payload(model: FiniteElementModel) -> dict[str, object]:
    """Legacy signature retained for pre-v2 solver-session compatibility."""

    excluded = {"checkpoint_path", "checkpoint_interval", "checkpoint_keep_steps", "restart_from"}
    parameters = {key: value for key, value in model.analysis.parameters.items() if key not in excluded}
    return {
        "schema_version": model.schema_version,
        "units": model.units,
        "nodes": model.nodes.tolist(),
        "elements": [asdict(element) for element in model.elements],
        "materials": model.materials,
        "fixed_dofs": [asdict(condition) for condition in model.fixed_dofs],
        "loads": [asdict(load) for load in model.loads],
        "distributed_loads": [asdict(load) for load in model.distributed_loads],
        "analysis": {"type": model.analysis.type, "method": model.analysis.method, "parameters": parameters},
    }


def model_signature_v2(model: FiniteElementModel, state_topology: dict[str, Any] | None = None) -> str:
    """Return the v2 physical model signature."""

    payload = _json_safe(model_to_dict(model))
    payload.pop("verification_profile", None)
    parameters = dict(payload["analysis"]["parameters"])
    excluded = {
        "checkpoint_path",
        "checkpoint_interval",
        "checkpoint_keep_steps",
        "restart_from",
        "output_path",
        "output_dir",
        "results_path",
        "report_path",
        "cache_dir",
    }
    payload["analysis"]["parameters"] = {key: value for key, value in parameters.items() if key not in excluded}
    topology = state_topology or {
        "dof_count": int(model.dof_manager().ndof),
        "material": {"source": "model", "element_count": len(model.elements)},
        "contact": {"pair_count": len(model.contacts)},
        "continuation": {"analysis_method": model.analysis.method},
    }
    payload["state_topology"] = deepcopy(topology)
    payload["dof_count"] = int(model.dof_manager().ndof)
    return checkpoint_signature(payload, label="Nonlinear v2")


def build_state_topology(model: FiniteElementModel | None, state: NonlinearState) -> dict[str, Any]:
    """Build deterministic topology metadata for an accepted state."""

    material_entries = []
    for element, points in sorted(state.material_state.items(), key=lambda item: (type(item[0]).__name__, str(item[0]))):
        material_entries.append(
            {
                "key_type": "int" if isinstance(element, int) else "str",
                "element_id": int(element) if isinstance(element, int) else str(element),
                "integration_point_count": len(points) if isinstance(points, list) else None,
            }
        )
    contacts = getattr(model, "contacts", []) if model is not None else []
    stateful_contact_required = any(float(getattr(contact, "friction_coefficient", 0.0)) > 0.0 for contact in contacts)
    contact_mode = "stateful-required" if stateful_contact_required else ("stateless" if contacts else "empty")
    return {
        "dof_count": int(model.dof_manager().ndof) if model is not None else int(state.displacement.size),
        "material": {"entries": material_entries},
        "contact": {
            "mode": contact_mode,
            "pair_count": len(contacts),
            "state_entry_count": len(state.contact_state),
        },
        "continuation": {"keys": sorted(str(key) for key in state.continuation_state)},
    }


def migrate_v1_checkpoint(
    checkpoint: NonlinearCheckpoint,
    *,
    model: FiniteElementModel | None = None,
    expected_dofs: int | None = None,
    state_topology: dict[str, Any] | None = None,
    expected_model_signature: str | None = None,
    expected_legacy_model_signature: str | None = None,
) -> NonlinearCheckpointV2:
    """Migrate a bounded v1 checkpoint without inventing contact history."""

    checkpoint.validate(expected_dofs)
    if (
        expected_legacy_model_signature is not None
        and checkpoint.model_signature != expected_legacy_model_signature
    ):
        raise InputValidationError("Legacy nonlinear checkpoint does not match the physical model or load path.")
    contacts = getattr(model, "contacts", []) if model is not None else []
    if any(float(getattr(contact, "friction_coefficient", 0.0)) > 0.0 for contact in contacts):
        raise InputValidationError(
            "Schema-v1 checkpoint is ambiguous for a stateful contact model; contact history was not persisted."
        )
    state = NonlinearState(
        displacement=checkpoint.displacement,
        load_factor=checkpoint.load_factor,
        material_state=cast(Mapping[str | int, Any], checkpoint.material_states),
        contact_state={},
        continuation_state=cast(Mapping[str | int, Any], checkpoint.continuation_state),
        accepted_increment_metadata={
            "migration_source_schema": 1,
            "historical_metadata_available": False,
        },
    )
    topology = state_topology or build_state_topology(model, state)
    signature = model_signature_v2(model, topology) if model is not None else checkpoint.model_signature
    if expected_model_signature is not None and signature != expected_model_signature:
        raise InputValidationError("Migrated nonlinear checkpoint does not match the requested model signature.")
    return NonlinearCheckpointV2.from_state(
        model_signature=signature,
        completed_step=checkpoint.completed_step,
        state=state,
        state_topology=topology,
        migration_metadata={"source_schema_version": 1, "bounded_contact_policy": "contact-free-or-stateless-only"},
    )


def _validate_state_topology_payload(
    topology: dict[str, Any], state: NonlinearState, expected_dofs: int | None
) -> None:
    if topology.get("dof_count") != int(state.displacement.size):
        raise InputValidationError("Schema-v2 checkpoint DOF topology does not match the accepted state.")
    if expected_dofs is not None and topology.get("dof_count") != expected_dofs:
        raise InputValidationError("Schema-v2 checkpoint DOF topology does not match the model.")
    expected = build_state_topology(None, state)
    if deterministic_state_digest(topology.get("material", {})) != deterministic_state_digest(expected["material"]):
        raise InputValidationError("Schema-v2 checkpoint material-state topology is invalid.")
    continuation = topology.get("continuation", {})
    if sorted(str(key) for key in state.continuation_state) != continuation.get("keys", []):
        raise InputValidationError("Schema-v2 checkpoint continuation topology is invalid.")
    contact = topology.get("contact", {})
    if contact.get("state_entry_count") != len(state.contact_state):
        raise InputValidationError("Schema-v2 checkpoint contact-state topology is invalid.")


def _validate_state_topology(expected: MaterialStateTable, restored: MaterialStateTable) -> None:
    expected_shape = {element: len(points) for element, points in expected.items()}
    restored_shape = {element: len(points) for element, points in restored.items()}
    if restored_shape != expected_shape:
        raise InputValidationError("Nonlinear checkpoint material-state topology does not match the model.")


def _optional_npz_path(value: object, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError(f"{name} must be a non-empty path string.")
    if Path(value).suffix.lower() != ".npz":
        raise InputValidationError(f"{name} must use the .npz format.")
    return value


def _validate_material_states(states: MaterialStateTable) -> None:
    if not isinstance(states, dict):
        raise InputValidationError("Nonlinear checkpoint material states must be a mapping.")
    for element, points in states.items():
        if not isinstance(element, int) or element < 0 or not isinstance(points, list):
            raise InputValidationError("Nonlinear checkpoint material-state topology is invalid.")
        for state in points:
            if not isinstance(state, dict) or not _finite_tree(state):
                raise InputValidationError("Nonlinear checkpoint contains invalid material-state values.")


def _finite_tree(value: object) -> bool:
    if isinstance(value, bool) or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return bool(np.isfinite(float(value)))
    if isinstance(value, list):
        return all(_finite_tree(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _finite_tree(item) for key, item in value.items())
    return False


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value
