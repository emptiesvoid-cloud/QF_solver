"""Bounded frictionless-penalty evaluation and restart contracts.

The contact mechanics implementation remains in :mod:`solveur.contact.solver`.
This module adds a storage-neutral result view and a semantic configuration
signature without introducing contact history or changing the numerical path.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
from scipy.sparse import csr_matrix

from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.state import deterministic_state_digest


CONTACT_EVALUATION_SCHEMA_VERSION = 1
PENALTY_CONTACT_RESTART_SCHEMA_VERSION = 1
PENALTY_CONTACT_STATE_SEMANTICS = "PURE_STATELESS_FROM_TRIAL_U"
ACTIVE_SET_MIDSOLVE_RESTART = "UNSUPPORTED"
UPDATED_SEARCH_RESTART = "UNQUALIFIED_RESTART"

_CONTACT_PARAMETER_NAMES = (
    "contact_max_penetration",
    "contact_max_iterations",
    "contact_search_max_iterations",
    "contact_search_tolerance",
    "contact_friction_tolerance",
)


@dataclass(frozen=True)
class ContactEvaluation:
    """One detached view of a fixed-normal penalty contact evaluation.

    ``internal_force`` and ``tangent`` are the arrays returned by the existing
    assembly.  They are intentionally not copied here; the result object adds
    semantic structure without doubling large numerical buffers.  Callers
    must treat the arrays as read-only after construction.
    """

    internal_force: np.ndarray
    tangent: csr_matrix
    details: Mapping[str, object]
    schema_version: int = CONTACT_EVALUATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        force = np.asarray(self.internal_force)
        if (
            force.ndim != 1
            or force.dtype.hasobject
            or not np.issubdtype(force.dtype, np.number)
            or not np.all(np.isfinite(force))
        ):
            raise InputValidationError("Contact evaluation internal force must be a finite vector.")
        tangent = self.tangent if isinstance(self.tangent, csr_matrix) else csr_matrix(self.tangent)
        if tangent.data.size and not np.all(np.isfinite(tangent.data)):
            raise InputValidationError("Contact evaluation tangent must contain finite values.")
        if self.schema_version != CONTACT_EVALUATION_SCHEMA_VERSION:
            raise InputValidationError("Unsupported contact evaluation schema version.")
        if not isinstance(self.details, Mapping):
            raise InputValidationError("Contact evaluation details must be a mapping.")
        _validate_finite_payload(self.details, "contact evaluation details")
        object.__setattr__(self, "internal_force", force)
        object.__setattr__(self, "tangent", tangent)
        object.__setattr__(self, "details", dict(self.details))

    @classmethod
    def from_legacy(
        cls,
        internal_force: np.ndarray,
        tangent: csr_matrix,
        details: Mapping[str, object],
    ) -> "ContactEvaluation":
        """Wrap the existing ``assemble_penalty_contact`` return contract."""

        normalized = dict(details)
        normalized.update(normalized_contact_diagnostics(normalized))
        return cls(internal_force, tangent, normalized)

    @property
    def active_contacts(self) -> tuple[int, ...]:
        """Return active contact indices without exposing a mutable list."""

        value = self.details.get("active_contacts", ())
        if not isinstance(value, (list, tuple)):
            raise InputValidationError("Contact evaluation active_contacts must be a sequence.")
        return tuple(int(index) for index in value)

    @property
    def gaps(self) -> tuple[float, ...]:
        """Return the signed gap for each evaluated contact."""

        value = self.details.get("gaps", ())
        if not isinstance(value, (list, tuple, np.ndarray)):
            raise InputValidationError("Contact evaluation gaps must be a sequence.")
        return tuple(float(gap) for gap in value)

    @property
    def diagnostics(self) -> dict[str, object]:
        """Return stable common diagnostic names for the evaluation."""

        return normalized_contact_diagnostics(self.details)

    def as_legacy(self) -> tuple[np.ndarray, csr_matrix, dict[str, object]]:
        """Project back to the historical three-value assembly contract."""

        return self.internal_force, self.tangent, dict(self.details)


def evaluate_penalty_contact(
    model: FiniteElementModel,
    dofs: DofManager,
    displacement: np.ndarray,
    *,
    penalty: float,
) -> ContactEvaluation:
    """Evaluate penalty contact through the unchanged legacy mechanics path."""

    # Keep the import local so the result contract can be imported by the
    # existing solver without creating a module cycle.
    from solveur.contact.solver import assemble_penalty_contact

    internal, tangent, details = assemble_penalty_contact(
        model,
        dofs,
        displacement,
        penalty=penalty,
    )
    return ContactEvaluation.from_legacy(internal, tangent, details)


def normalized_contact_diagnostics(details: Mapping[str, object]) -> dict[str, object]:
    """Map legacy penalty details to stable, additive diagnostic names."""

    active = details.get("active_contacts", ())
    gaps = details.get("gaps", ())
    if not isinstance(active, (list, tuple)):
        raise InputValidationError("Contact details active_contacts must be a sequence.")
    if not isinstance(gaps, (list, tuple, np.ndarray)):
        raise InputValidationError("Contact details gaps must be a sequence.")
    gap_values = [float(gap) for gap in gaps]
    if not all(np.isfinite(gap) for gap in gap_values):
        raise InputValidationError("Contact details gaps must be finite.")
    maximum = details.get("maximum_penetration", max((max(-gap, 0.0) for gap in gap_values), default=0.0))
    force_norm = details.get("contact_force_norm", 0.0)
    tangent_nnz = details.get("tangent_nnz", 0)
    maximum_value = _finite_float(maximum, "maximum_penetration")
    force_value = _finite_float(force_norm, "contact_force_norm")
    try:
        tangent_value = int(cast(Any, tangent_nnz))
    except (TypeError, ValueError) as error:
        raise InputValidationError("Contact details tangent_nnz must be an integer.") from error
    if tangent_value < 0:
        raise InputValidationError("Contact details tangent_nnz must be non-negative.")
    search_mode = details.get("search_mode")
    return {
        "contact_active_count": len(active),
        "contact_minimum_gap": min(gap_values, default=0.0),
        "contact_maximum_penetration": maximum_value,
        "contact_force_norm": force_value,
        "contact_tangent_nnz": tangent_value,
        "contact_search_mode": search_mode,
    }


def contact_configuration_payload(
    model: FiniteElementModel,
    *,
    penalty: float,
) -> dict[str, object]:
    """Build the semantic fixed-search configuration used by the digest.

    Nodal coordinates are deliberately not included: the surrounding
    nonlinear checkpoint/model signature owns physical geometry.  This digest
    covers contact topology and parameters only and is independent of Python
    object identity or mapping insertion order.
    """

    penalty_value = _positive_finite_float(penalty, "penalty")
    parameters = model.analysis.parameters
    search_mode = str(parameters.get("contact_search_mode", "initial")).lower()
    if search_mode not in {"initial", "updated"}:
        raise InputValidationError("contact_search_mode must be 'initial' or 'updated'.")
    finite_sliding = parameters.get("contact_finite_sliding", False)
    if not isinstance(finite_sliding, bool):
        raise InputValidationError("contact_finite_sliding must be a boolean.")
    contacts: list[dict[str, object]] = []
    for contact in model.contacts:
        tangential_stiffness = contact.tangential_stiffness
        contacts.append(
            {
                "name": str(contact.name),
                "slave_node": int(contact.slave_node),
                "slave_nodes": [int(node) for node in contact.slave_nodes],
                "master_nodes": [int(node) for node in contact.master_nodes],
                "master_faces": [[int(node) for node in face] for face in contact.faces],
                "gap_tolerance": _positive_finite_float(contact.gap_tolerance, "gap_tolerance"),
                "friction_coefficient": _finite_float(contact.friction_coefficient, "friction_coefficient"),
                "tangential_stiffness": (
                    None
                    if tangential_stiffness is None
                    else _positive_finite_float(tangential_stiffness, "tangential_stiffness")
                ),
            }
        )
    contact_parameters: dict[str, object] = {
        "contact_mode": str(parameters.get("contact_mode", "")).lower(),
        "contact_search_mode": search_mode,
        "contact_finite_sliding": finite_sliding,
        "penalty": penalty_value,
        "contact_penalty_parameter": _optional_finite_float(parameters.get("contact_penalty"), "contact_penalty"),
    }
    for name in _CONTACT_PARAMETER_NAMES:
        value = parameters.get(name)
        if name.endswith("iterations") and value is not None:
            contact_parameters[name] = _positive_integer(value, name)
        else:
            contact_parameters[name] = _optional_finite_float(value, name)
    return {
        "schema_version": PENALTY_CONTACT_RESTART_SCHEMA_VERSION,
        "contract": "WP07-B-FIXED-SEARCH-PENALTY-CONTACT",
        "analysis_type": str(model.analysis.type),
        "analysis_method": str(model.analysis.method),
        "contacts": contacts,
        "parameters": contact_parameters,
    }


def contact_configuration_digest(model: FiniteElementModel, *, penalty: float) -> str:
    """Return a deterministic digest of contact topology/configuration."""

    return deterministic_state_digest(contact_configuration_payload(model, penalty=penalty))


@dataclass(frozen=True)
class PenaltyContactRestartMetadata:
    """Bounded compatibility metadata for stateless penalty restart."""

    contact_configuration_digest: str
    analysis_type: str
    search_mode: str
    finite_sliding: bool
    accepted_state_digest: str | None = None
    schema_version: int = PENALTY_CONTACT_RESTART_SCHEMA_VERSION
    state_semantics: str = PENALTY_CONTACT_STATE_SEMANTICS

    def __post_init__(self) -> None:
        if self.schema_version != PENALTY_CONTACT_RESTART_SCHEMA_VERSION:
            raise InputValidationError("Unsupported penalty contact restart metadata schema version.")
        if not self.contact_configuration_digest:
            raise InputValidationError("Penalty contact restart metadata requires a configuration digest.")
        if not isinstance(self.finite_sliding, bool):
            raise InputValidationError("Penalty contact restart finite_sliding must be boolean.")
        if self.accepted_state_digest is not None and not self.accepted_state_digest:
            raise InputValidationError("Penalty contact restart accepted state digest cannot be empty.")
        if self.state_semantics != PENALTY_CONTACT_STATE_SEMANTICS:
            raise InputValidationError("Unsupported penalty contact restart state semantics.")

    @classmethod
    def from_model(
        cls,
        model: FiniteElementModel,
        *,
        penalty: float,
        accepted_state_digest: str | None = None,
    ) -> "PenaltyContactRestartMetadata":
        parameters = model.analysis.parameters
        search_mode = str(parameters.get("contact_search_mode", "initial")).lower()
        finite_sliding = parameters.get("contact_finite_sliding", False)
        if search_mode not in {"initial", "updated"} or not isinstance(finite_sliding, bool):
            raise InputValidationError("Penalty contact restart metadata has invalid search configuration.")
        return cls(
            contact_configuration_digest=contact_configuration_digest(model, penalty=penalty),
            analysis_type=str(model.analysis.type),
            search_mode=search_mode,
            finite_sliding=finite_sliding,
            accepted_state_digest=accepted_state_digest,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "PenaltyContactRestartMetadata":
        if not isinstance(payload, Mapping):
            raise InputValidationError("Penalty contact restart metadata must be a mapping.")
        required = {
            "contact_configuration_digest",
            "analysis_type",
            "search_mode",
            "finite_sliding",
            "state_semantics",
            "schema_version",
        }
        if not required.issubset(payload):
            raise InputValidationError("Penalty contact restart metadata is incomplete.")
        schema_version = payload["schema_version"]
        if isinstance(schema_version, bool) or not isinstance(schema_version, int):
            raise InputValidationError("Penalty contact restart metadata schema_version is invalid.")
        finite_sliding = payload["finite_sliding"]
        if not isinstance(finite_sliding, bool):
            raise InputValidationError("Penalty contact restart metadata finite_sliding is invalid.")
        accepted_state_digest = payload.get("accepted_state_digest")
        if accepted_state_digest is not None and not isinstance(accepted_state_digest, str):
            raise InputValidationError("Penalty contact restart accepted state digest is invalid.")
        return cls(
            contact_configuration_digest=str(payload["contact_configuration_digest"]),
            analysis_type=str(payload["analysis_type"]),
            search_mode=str(payload["search_mode"]),
            finite_sliding=finite_sliding,
            accepted_state_digest=accepted_state_digest,
            schema_version=schema_version,
            state_semantics=str(payload["state_semantics"]),
        )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe metadata record."""

        return {
            "schema_version": self.schema_version,
            "state_semantics": self.state_semantics,
            "contact_configuration_digest": self.contact_configuration_digest,
            "analysis_type": self.analysis_type,
            "search_mode": self.search_mode,
            "finite_sliding": self.finite_sliding,
            "accepted_state_digest": self.accepted_state_digest,
        }

    def validate_compatible(self, model: FiniteElementModel, *, penalty: float) -> None:
        """Reject a restart when semantic contact configuration changed."""

        expected = type(self).from_model(model, penalty=penalty)
        if (
            self.schema_version != expected.schema_version
            or self.contact_configuration_digest != expected.contact_configuration_digest
            or self.analysis_type != expected.analysis_type
            or self.search_mode != expected.search_mode
            or self.finite_sliding != expected.finite_sliding
            or self.state_semantics != expected.state_semantics
        ):
            raise InputValidationError(
                "Penalty contact restart metadata is incompatible with the current contact configuration."
            )


def validate_penalty_contact_restart_metadata(
    payload: Mapping[str, object],
    model: FiniteElementModel,
    *,
    penalty: float,
) -> PenaltyContactRestartMetadata:
    """Decode and validate bounded penalty restart metadata."""

    metadata = PenaltyContactRestartMetadata.from_dict(payload)
    metadata.validate_compatible(model, penalty=penalty)
    return metadata


def reject_active_set_mid_solve_restart() -> None:
    """Fail closed rather than implying active-set checkpoint support."""

    raise InputValidationError("MID_SOLVE_ACTIVE_SET_RESTART is unsupported for linear active-set contact.")


def updated_search_restart_status() -> str:
    """Return the explicit research-only restart classification."""

    return UPDATED_SEARCH_RESTART


def _finite_float(value: object, name: str) -> float:
    try:
        result = float(cast(Any, value))
    except (TypeError, ValueError) as error:
        raise InputValidationError(f"{name} must be finite.") from error
    if not np.isfinite(result):
        raise InputValidationError(f"{name} must be finite.")
    return result


def _positive_finite_float(value: object, name: str) -> float:
    result = _finite_float(value, name)
    if result <= 0.0:
        raise InputValidationError(f"{name} must be finite and positive.")
    return result


def _optional_finite_float(value: object, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise InputValidationError(f"{name} must be finite when configured.")
    return _finite_float(value, name)


def _positive_integer(value: object, name: str) -> int:
    if isinstance(value, bool):
        raise InputValidationError(f"{name} must be a positive integer.")
    try:
        numeric = float(cast(Any, value))
    except (TypeError, ValueError) as error:
        raise InputValidationError(f"{name} must be a positive integer.") from error
    if not np.isfinite(numeric) or numeric <= 0.0 or not numeric.is_integer():
        raise InputValidationError(f"{name} must be a positive integer.")
    return int(numeric)


def _validate_finite_payload(value: Any, path: str) -> None:
    if value is None or isinstance(value, (str, bool, int, np.bool_, np.integer)):
        return
    if isinstance(value, (float, np.floating)):
        if not np.isfinite(value):
            raise InputValidationError(f"{path} contains a non-finite scalar.")
        return
    if isinstance(value, np.ndarray):
        if value.dtype.hasobject or not np.issubdtype(value.dtype, np.number):
            raise InputValidationError(f"{path} array must be numeric.")
        if not np.all(np.isfinite(value)):
            raise InputValidationError(f"{path} array contains a non-finite value.")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            _validate_finite_payload(item, f"{path}[{key!r}]")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_finite_payload(item, f"{path}[{index}]")
        return
    raise InputValidationError(f"{path} contains unsupported value type {type(value).__name__}.")
