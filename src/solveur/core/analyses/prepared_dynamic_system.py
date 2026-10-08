"""Instance-local preparation of sparse linear dynamic operators.

This is an internal WP02 facility.  It deliberately owns a private model
snapshot and has no process-global cache or public serialization contract.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import fields, is_dataclass
import json
from typing import Any, Mapping

import numpy as np
from scipy.sparse import csr_matrix, issparse

from solveur.core.analyses.dynamic_reduction import DynamicDofReducer
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.assembly.plan import AssemblyPlan
from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.elements.discrete import ConcentratedMass
from solveur.elements.registry import ElementRegistry
from solveur.io.checkpoint_common import checkpoint_signature
from solveur.io.manifest import content_digest


_IDENTITY_SCHEMA = "qf-physical-identity/v1"
_OPERATOR_SCHEMA = "qf-operator-identity/v1"
_EXCITATION_SCHEMA = "qf-excitation-identity/v1"
_ASSEMBLY_SEMANTICS = "GlobalAssembler.assemble_stiffness_and_mass/v1"
_SUPPORTED_ELEMENTS = {"TET4", "TET10", "HEX8", "HEX20", "BEAM2"}
_DYNAMIC_ANALYSES = {"modal", "harmonic_response", "transient_dynamic"}
_EXCITATION_PARAMETER_KEYS = (
    "load_function",
    "load_frequency_hz",
    "chirp_start_hz",
    "chirp_end_hz",
    "load_table",
    "load_factors",
    "load_factors_by_load",
    "frequencies_hz",
    "frequency_start_hz",
    "frequency_stop_hz",
    "frequency_count",
    "start_hz",
    "stop_hz",
    "count",
)


class PreparedDynamicSystem:
    """Immutable-by-interface sparse K/M preparation for one physical model.

    ``prepare`` snapshots the caller's model, assembles paired K/M once, then
    applies the existing dynamic DDL reducer.  Matrix and mapping properties
    return copies; no mutable user object or global cache is retained.
    """

    def __init__(
        self,
        *,
        model_snapshot: FiniteElementModel,
        dofs: DofManager,
        plan: AssemblyPlan,
        reducer: DynamicDofReducer,
        source_sha: str,
        assembler_default_chunk_size: int,
        stiffness_full: csr_matrix,
        mass_full: csr_matrix,
        physical_identity: str,
        operator_identity: str,
        excitation_identity: str,
        identity_document: str,
        assembly_diagnostics: dict[str, object],
    ) -> None:
        self._model_snapshot = model_snapshot
        self._dof_signature = tuple(sorted((int(node), tuple(names)) for node, names in dofs.node_dofs.items()))
        self._assembler_default_chunk_size = int(assembler_default_chunk_size)
        self._plan = plan
        self._reducer = reducer
        self._source_sha = source_sha
        self._stiffness_full = _freeze_sparse(stiffness_full)
        self._mass_full = _freeze_sparse(mass_full)
        if not issparse(reducer.stiffness) or not issparse(reducer.mass):
            raise InputValidationError("Prepared dynamic operators must remain sparse.")
        self._stiffness_reduced = _freeze_sparse(csr_matrix(reducer.stiffness))
        self._mass_reduced = _freeze_sparse(csr_matrix(reducer.mass))
        self._physical_identity = physical_identity
        self._operator_identity = operator_identity
        self._excitation_identity = excitation_identity
        self._identity_document = identity_document
        self._assembly_diagnostics = deepcopy(assembly_diagnostics)

    @classmethod
    def prepare(
        cls,
        model: FiniteElementModel,
        *,
        source_sha: str,
        assembler: GlobalAssembler | None = None,
    ) -> "PreparedDynamicSystem":
        """Validate, snapshot, and assemble the supported linear dynamic scope."""
        if not isinstance(model, FiniteElementModel):
            raise InputValidationError("PreparedDynamicSystem requires a FiniteElementModel.")
        if (
            not isinstance(source_sha, str)
            or len(source_sha) not in {40, 64}
            or any(character not in "0123456789abcdef" for character in source_sha.lower())
        ):
            raise InputValidationError("PreparedDynamicSystem requires an explicit full source SHA.")
        source_sha = source_sha.lower()
        _validate_admissible_model(model)
        snapshot = deepcopy(model)
        # The cloned coordinates are not exposed; making them read-only also
        # prevents accidental mutation through AssemblyPlan coordinate views.
        snapshot.nodes.setflags(write=False)
        dofs = snapshot.dof_manager()
        physical_document = _physical_identity_document(snapshot, dofs)
        physical_identity = _identity_hash(_IDENTITY_SCHEMA, physical_document)

        selected_assembler = assembler or GlobalAssembler()
        plan = selected_assembler.prepare_plan(snapshot, dofs)
        stiffness, mass, stiffness_diagnostics, mass_diagnostics = selected_assembler.assemble_stiffness_and_mass(
            snapshot, dofs, plan=plan
        )
        for name, matrix in (("stiffness", stiffness), ("mass", mass)):
            if matrix.shape != (dofs.ndof, dofs.ndof) or not np.all(np.isfinite(matrix.data)):
                raise InputValidationError(
                    f"Prepared dynamic {name} operator has an invalid shape or non-finite entries."
                )
        fixed = selected_assembler.fixed_indices(snapshot, dofs)
        reducer = DynamicDofReducer.from_system(snapshot, dofs, mass, stiffness, fixed)
        reduced_stiffness = csr_matrix(reducer.stiffness)
        reduced_mass = csr_matrix(reducer.mass)
        operator_document = {
            "physical_identity": physical_identity,
            "source_sha": source_sha,
            "assembly_semantics": _ASSEMBLY_SEMANTICS,
            "assembler_default_chunk_size": int(selected_assembler.chunk_size),
            "assembly_chunk_size": int(plan.chunk_size),
            "full_dof_signature": [[node, list(names)] for node, names in sorted(dofs.node_dofs.items())],
            "fixed_dof_indices": fixed.tolist(),
            "reduction": {
                "free": reducer.free.tolist(),
                "physical": reducer.physical.tolist(),
                "massless": reducer.massless.tolist(),
                "transform_sha256": _sparse_content_hash(csr_matrix(reducer.transform)),
            },
            "stiffness_full_sha256": _sparse_content_hash(stiffness),
            "mass_full_sha256": _sparse_content_hash(mass),
            "stiffness_reduced_sha256": _sparse_content_hash(reduced_stiffness),
            "mass_reduced_sha256": _sparse_content_hash(reduced_mass),
        }
        operator_identity = _identity_hash(_OPERATOR_SCHEMA, operator_document)
        excitation_identity = excitation_identity_for(snapshot)
        diagnostics = {
            "stiffness": stiffness_diagnostics,
            "mass": mass_diagnostics,
            "reduction": deepcopy(reducer.diagnostics),
            "cache_scope": "INSTANCE_LOCAL_ONLY",
            "assembly_plan_lifetime": "PREPARED_SYSTEM_INSTANCE",
            "assembly_count": 1,
            "factorization_cache": "NOT_CREATED_IN_WP02",
            "global_cache": False,
            "positive_definiteness": "NOT_ASSERTED_BY_PREPARATION; METHOD_CONTRACT_MUST_CHECK",
        }
        identity_document = json.dumps(physical_document, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return cls(
            model_snapshot=snapshot,
            dofs=dofs,
            plan=plan,
            reducer=reducer,
            source_sha=source_sha,
            assembler_default_chunk_size=selected_assembler.chunk_size,
            stiffness_full=stiffness,
            mass_full=mass,
            physical_identity=physical_identity,
            operator_identity=operator_identity,
            excitation_identity=excitation_identity,
            identity_document=identity_document,
            assembly_diagnostics=diagnostics,
        )

    @property
    def physical_snapshot(self) -> bytes:
        """Canonical immutable JSON bytes for the physical input snapshot."""
        return self._identity_document.encode("utf-8")

    @property
    def source_sha(self) -> str:
        return self._source_sha

    @property
    def physical_identity(self) -> str:
        return self._physical_identity

    @property
    def operator_identity(self) -> str:
        return self._operator_identity

    @property
    def excitation_identity(self) -> str:
        return self._excitation_identity

    @property
    def element_families(self) -> tuple[str, ...]:
        return tuple(sorted({str(element.type).upper() for element in self._model_snapshot.elements}))

    @property
    def dof_signature(self) -> tuple[tuple[int, tuple[str, ...]], ...]:
        return self._dof_signature

    @property
    def stiffness_full(self) -> csr_matrix:
        return self._stiffness_full.copy()

    @property
    def mass_full(self) -> csr_matrix:
        return self._mass_full.copy()

    @property
    def stiffness(self) -> csr_matrix:
        """Reduced stiffness matrix (fixed DDL and supported reduction applied)."""
        return self._stiffness_reduced.copy()

    @property
    def mass(self) -> csr_matrix:
        """Reduced mass matrix (fixed DDL and supported reduction applied)."""
        return self._mass_reduced.copy()

    @property
    def reduction_transform(self) -> csr_matrix:
        return csr_matrix(self._reducer.transform, copy=True)

    @property
    def free_dof_indices(self) -> np.ndarray:
        return self._readonly_array(self._reducer.free)

    @property
    def fixed_dof_indices(self) -> np.ndarray:
        return np.setdiff1d(np.arange(self._reducer.full_size), self._reducer.free)

    @property
    def reduced_size(self) -> int:
        return self._reducer.reduced_size

    @property
    def assembly_plan_fingerprint(self) -> str:
        return self._plan.fingerprint

    @property
    def assembly_diagnostics(self) -> dict[str, object]:
        return deepcopy(self._assembly_diagnostics)

    @property
    def sparse_storage_bytes(self) -> dict[str, int]:
        return {
            "stiffness_full": _sparse_storage_bytes(self._stiffness_full),
            "mass_full": _sparse_storage_bytes(self._mass_full),
            "stiffness_reduced": _sparse_storage_bytes(self._stiffness_reduced),
            "mass_reduced": _sparse_storage_bytes(self._mass_reduced),
        }

    def matches_operator_inputs(self, model: FiniteElementModel) -> bool:
        """Return whether the model's physical/operator inputs match this K/M.

        Loads and other excitation values are intentionally excluded.
        Unsupported or incomplete candidate models never match.
        """
        try:
            _validate_admissible_model(model)
            configured_chunk_size = int(
                model.analysis.parameters.get("assembly_chunk_size", self._assembler_default_chunk_size)
            )
            if configured_chunk_size <= 0 or configured_chunk_size != self._plan.chunk_size:
                return False
            candidate_dofs = model.dof_manager()
            candidate = _identity_hash(_IDENTITY_SCHEMA, _physical_identity_document(model, candidate_dofs))
        except (InputValidationError, KeyError, TypeError, ValueError):
            return False
        return candidate == self.physical_identity

    def require_compatible(self, model: FiniteElementModel) -> None:
        if not self.matches_operator_inputs(model):
            raise InputValidationError(
                "Prepared dynamic operators do not match the current physical model; re-prepare K/M."
            )

    def reduce_state(self, full_vector: np.ndarray) -> np.ndarray:
        return self._reducer.reduce_state(full_vector)

    def reduce_load(self, full_vector: np.ndarray) -> np.ndarray:
        """Project a real or complex full-space RHS without reassembling K/M.

        The existing reducer is real-valued.  Its linear map is applied
        independently to real and imaginary parts so harmonic phasors are
        preserved without introducing a separate reduction formulation.
        """
        try:
            raw = np.asarray(full_vector)
            if raw.shape != (self._reducer.full_size,):
                raise InputValidationError(
                    f"Prepared load vector must have shape ({self._reducer.full_size},)."
                )
            contains_complex = np.iscomplexobj(raw) or (
                raw.dtype.kind == "O"
                and any(isinstance(value, (complex, np.complexfloating)) for value in raw.flat)
            )
            values = np.asarray(raw, dtype=np.complex128 if contains_complex else np.float64)
        except (TypeError, ValueError, OverflowError) as exc:
            raise InputValidationError("Prepared load vector must contain finite numeric values.") from exc
        if not np.all(np.isfinite(values)):
            raise InputValidationError("Prepared load vector must contain finite numeric values.")
        if contains_complex:
            reduced = self._reducer.reduce_load(values.real) + 1j * self._reducer.reduce_load(values.imag)
            if not np.all(np.isfinite(reduced)):
                raise InputValidationError("Reduced complex load vector contains non-finite values.")
            return np.asarray(reduced, dtype=np.complex128)
        return self._reducer.reduce_load(np.asarray(values, dtype=np.float64))

    def expand_state(self, reduced_vector: np.ndarray, full_load: np.ndarray | None = None) -> np.ndarray:
        return self._reducer.expand_state(reduced_vector, full_load)

    @staticmethod
    def _readonly_array(values: np.ndarray) -> np.ndarray:
        result = np.asarray(values, dtype=int).copy()
        result.setflags(write=False)
        return result


def excitation_identity_for(model: FiniteElementModel) -> str:
    """Return a load-only identity, separate from the physical K/M identity."""
    parameters = model.analysis.parameters
    document: dict[str, object] = {
        "nodal_loads": [_plain(load) for load in model.loads],
        "distributed_loads": [_plain(load) for load in model.distributed_loads],
        "temporal_load_definition": {
            key: _plain(parameters[key]) for key in _EXCITATION_PARAMETER_KEYS if key in parameters
        },
    }
    return _identity_hash(_EXCITATION_SCHEMA, document)


def _validate_admissible_model(model: FiniteElementModel) -> None:
    if model.analysis.type not in _DYNAMIC_ANALYSES:
        raise InputValidationError(
            "PreparedDynamicSystem supports modal, harmonic_response, or transient_dynamic models only."
        )
    if not model.elements:
        raise InputValidationError("PreparedDynamicSystem requires at least one supported element.")
    if model.multipoint_constraints or model.rbe2 or model.rbe3 or model.contacts:
        raise InputValidationError("PreparedDynamicSystem does not support MPC/RBE constraints or contact in WP02.")
    structural_dofs: dict[int, set[str]] = {node: set() for node in range(model.node_count)}
    for element in model.elements:
        family = str(element.type).upper()
        if family not in _SUPPORTED_ELEMENTS:
            raise InputValidationError(f"PreparedDynamicSystem does not support element family {family!r}.")
        spec = ElementRegistry.get(family)
        material = model.materials.get(element.material)
        if not isinstance(material, Mapping):
            raise InputValidationError(f"PreparedDynamicSystem material {element.material!r} is missing or invalid.")
        expected_type = "beam_isotropic" if family == "BEAM2" else "isotropic_3d"
        if str(material.get("type", "")).lower() != expected_type:
            raise InputValidationError(
                f"PreparedDynamicSystem {family} requires {expected_type} material; got {material.get('type')!r}."
            )
        try:
            density = float(material.get("density", material.get("rho", 0.0)))
        except (TypeError, ValueError) as exc:
            raise InputValidationError("PreparedDynamicSystem requires finite positive material density.") from exc
        if not np.isfinite(density) or density <= 0.0:
            raise InputValidationError("PreparedDynamicSystem requires finite positive material density.")
        for node in element.nodes:
            if node < 0 or node >= model.node_count:
                raise InputValidationError(f"PreparedDynamicSystem element references invalid node {node}.")
            structural_dofs[int(node)].update(spec.dofs)

    for spring in model.springs:
        if not set(spring.active_dofs()).issubset(structural_dofs.get(spring.node_a, set())):
            raise InputValidationError(
                "PreparedDynamicSystem springs may use only structural DDL already present at node_a."
            )
        if spring.node_b is not None and not set(spring.active_dofs()).issubset(
            structural_dofs.get(spring.node_b, set())
        ):
            raise InputValidationError(
                "PreparedDynamicSystem springs may use only structural DDL already present at node_b."
            )
    for mass in model.concentrated_masses:
        if not isinstance(mass, ConcentratedMass):
            raise InputValidationError(
                "PreparedDynamicSystem accepts concentrated masses only; rotating disks are outside WP02."
            )
        if not set(mass.active_dofs()).issubset(structural_dofs.get(mass.node, set())):
            raise InputValidationError(
                "PreparedDynamicSystem concentrated masses may use only structural DDL already present."
            )


def _physical_identity_document(model: FiniteElementModel, dofs: DofManager) -> dict[str, object]:
    used_materials = sorted({element.material for element in model.elements})
    dof_signature = [[int(node), list(names)] for node, names in sorted(dofs.node_dofs.items())]
    elements = [_plain(element) for element in model.elements]
    fixed = [_plain(condition) for condition in model.fixed_dofs]
    springs = [_plain(spring) for spring in model.springs]
    masses = [_plain(mass) for mass in model.concentrated_masses]
    return {
        "identity_schema": _IDENTITY_SCHEMA,
        "model_schema_version": int(model.schema_version),
        "units": _plain(model.units),
        "coordinates": _plain(model.nodes),
        "elements": _sort_canonical(elements),
        "materials": {name: _plain(model.materials[name]) for name in used_materials},
        "fixed_dofs": _sort_canonical(fixed),
        "active_dof_signature": dof_signature,
        "springs": _sort_canonical(springs),
        "concentrated_masses": _sort_canonical(masses),
        "constraints": {
            "multipoint": [],
            "rbe2": [],
            "rbe3": [],
            "contacts": [],
        },
    }


def _identity_hash(schema: str, payload: dict[str, object]) -> str:
    # Reuse the repository's deterministic checkpoint canonicalizer.  The
    # identity family/schema envelope provides the WP01 domain separation.
    return checkpoint_signature(
        {"identity_domain": schema, "identity_schema_version": 1, "payload": payload},
        label="Prepared dynamic identity",
    )


def _sparse_content_hash(matrix: csr_matrix) -> str:
    canonical = csr_matrix(matrix, dtype=np.float64, copy=True)
    canonical.sum_duplicates()
    canonical.eliminate_zeros()
    canonical.sort_indices()
    shape = np.asarray(canonical.shape, dtype="<i8").tobytes()
    indptr = np.asarray(canonical.indptr, dtype="<i8").tobytes()
    indices = np.asarray(canonical.indices, dtype="<i8").tobytes()
    data = np.asarray(canonical.data, dtype="<f8").tobytes()
    return content_digest(b"qf-csr-f64/v1\0" + shape + indptr + indices + data)


def _sparse_storage_bytes(matrix: csr_matrix) -> int:
    return int(matrix.data.nbytes + matrix.indices.nbytes + matrix.indptr.nbytes)


def _freeze_sparse(matrix: csr_matrix) -> csr_matrix:
    result = csr_matrix(matrix, copy=True)
    result.sum_duplicates()
    result.eliminate_zeros()
    result.sort_indices()
    result.data.setflags(write=False)
    result.indices.setflags(write=False)
    result.indptr.setflags(write=False)
    return result


def _sort_canonical(values: list[object]) -> list[object]:
    return sorted(values, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))


def _plain(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, np.ndarray):
        return _plain(value.tolist())
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise InputValidationError("Prepared identity requires string mapping keys.")
        return {key: _plain(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        if not np.isfinite(number):
            raise InputValidationError("Prepared identity does not accept non-finite values.")
        return number
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise InputValidationError(f"Prepared identity cannot canonicalize {type(value).__name__}.")
