"""Sparse internal-force and tangent assembly for nonlinear solids."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from time import perf_counter
from scipy.sparse import coo_matrix, csr_matrix

from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.nonlinear.material_state import MaterialStateTable, state_is_finite
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.model import FiniteElementModel
from solveur.core.assembly.sparse import SparseCsrAccumulator
from solveur.contact.solver import assemble_penalty_contact
from solveur.elements.registry import ElementRegistry, ElementSpec
from solveur.elements.solid.total_lagrangian_j2 import (
    TotalLagrangianJ2Hex8Element,
    TotalLagrangianJ2Hex20Element,
    TotalLagrangianJ2Tet10Element,
    TotalLagrangianJ2Tet4Element,
)
from solveur.elements.solid.tet10 import Tet10Element
from solveur.materials.factory import MaterialFactory


@dataclass(frozen=True)
class NonlinearAssemblyElement:
    """Reusable, state-independent data for one nonlinear element."""

    definition_type: str
    material_name: str
    coordinates: np.ndarray
    global_dofs: np.ndarray
    spec: ElementSpec
    element: object


@dataclass(frozen=True)
class NonlinearAssemblyPlan:
    """Cached element objects and DDL maps for one nonlinear model solve.

    Material history is deliberately not stored here.  Trial and committed
    integration-point states remain owned by ``MaterialStateTable``; the plan
    only caches immutable material parameters and stateless element kernels.
    """

    model_token: int
    dofs_token: int
    node_count: int
    ndof: int
    kinematics: str
    nonlinear_quadrature: str
    elements: tuple[NonlinearAssemblyElement, ...]

    def matches(self, model: FiniteElementModel, dofs: DofManager) -> bool:
        """Return whether the plan is safe to reuse for ``model`` and ``dofs``."""
        kinematics = str(model.analysis.parameters.get("kinematics", "small_strain")).lower()
        quadrature = str(
            model.analysis.parameters.get("tet10_nonlinear_quadrature", "hammer4")
        ).lower()
        return (
            self.model_token == id(model)
            and self.dofs_token == id(dofs)
            and self.node_count == model.node_count
            and self.ndof == dofs.ndof
            and len(self.elements) == len(model.elements)
            and self.kinematics == kinematics
            and self.nonlinear_quadrature == quadrature
        )


def _create_nonlinear_element(
    spec: ElementSpec,
    material: object,
    element_type: str,
    finite_kinematics: str,
    nonlinear_quadrature: str,
) -> object:
    """Create one nonlinear kernel while keeping formulation dispatch local."""
    if finite_kinematics in {"total_lagrangian", "total_lagrangian_j2"}:
        element_class = {
            "TET4": TotalLagrangianJ2Tet4Element,
            "TET10": TotalLagrangianJ2Tet10Element,
            "HEX8": TotalLagrangianJ2Hex8Element,
            "HEX20": TotalLagrangianJ2Hex20Element,
        }.get(element_type)
        if element_class is None:
            raise InputValidationError(
                "total_lagrangian supports TET4, TET10, HEX8 and HEX20."
            )
        if element_type == "TET10":
            return element_class(material, nonlinear_quadrature=nonlinear_quadrature)
        return element_class(material)
    if element_type == "TET10":
        return Tet10Element(material, nonlinear_quadrature=nonlinear_quadrature)
    return spec.factory(material)


def build_nonlinear_assembly_plan(
    model: FiniteElementModel,
    dofs: DofManager,
) -> NonlinearAssemblyPlan:
    """Prepare reusable nonlinear element kernels without retaining matrices."""
    finite_kinematics = str(model.analysis.parameters.get("kinematics", "small_strain")).lower()
    nonlinear_quadrature = str(
        model.analysis.parameters.get("tet10_nonlinear_quadrature", "hammer4")
    ).lower()
    material_cache: dict[str, object] = {}
    entries: list[NonlinearAssemblyElement] = []
    for definition in model.elements:
        spec = ElementRegistry.get(definition.type)
        material = material_cache.get(definition.material)
        if material is None:
            material = MaterialFactory.create(model.materials[definition.material])
            material_cache[definition.material] = material
        coordinates = np.asarray(model.nodes[list(definition.nodes)], dtype=float)
        global_dofs = np.asarray(
            [
                index
                for node in definition.nodes
                for index in dofs.node_indices(node, spec.dofs)
            ],
            dtype=np.int64,
        )
        entries.append(
            NonlinearAssemblyElement(
                definition_type=str(definition.type),
                material_name=str(definition.material),
                coordinates=coordinates,
                global_dofs=global_dofs,
                spec=spec,
                element=_create_nonlinear_element(
                    spec,
                    material,
                    str(definition.type),
                    finite_kinematics,
                    nonlinear_quadrature,
                ),
            )
        )
    return NonlinearAssemblyPlan(
        model_token=id(model),
        dofs_token=id(dofs),
        node_count=model.node_count,
        ndof=dofs.ndof,
        kinematics=finite_kinematics,
        nonlinear_quadrature=nonlinear_quadrature,
        elements=tuple(entries),
    )


def assemble_internal_tangent(
    model: FiniteElementModel,
    dofs: DofManager,
    displacement: np.ndarray,
    material_states: MaterialStateTable | None = None,
    *,
    contact_diagnostics: dict[str, object] | None = None,
    timing: dict[str, float | int] | None = None,
    plan: NonlinearAssemblyPlan | None = None,
) -> tuple[np.ndarray, csr_matrix, MaterialStateTable]:
    """Assemble nonlinear internal force and tangent without dense intermediates."""
    if plan is not None and not plan.matches(model, dofs):
        raise InputValidationError("Nonlinear assembly plan does not match the supplied model and DDL map.")
    if timing is not None:
        timing.setdefault("element_kernel_calls", 0)
        timing.setdefault("contact_assembly_calls", 0)
        timing.setdefault("element_cache_hits", 0)
        timing.setdefault("element_cache_misses", 0)
        timing.setdefault("reference_cache_hits", 0)
        timing.setdefault("reference_cache_misses", 0)
        timing.setdefault("sparse_chunk_count", 0)
        timing.setdefault("sparse_peak_chunk_entries", 0)
        timing.setdefault("sparse_peak_chunk_bytes_estimate", 0)
        timing.setdefault("sparse_accumulator_levels", 0)
        timing.setdefault("tangent_nnz", 0)
        for key in (
            "element_setup_seconds",
            "element_kernel_seconds",
            "element_scatter_seconds",
            "sparse_conversion_seconds",
            "contact_assembly_seconds",
        ):
            timing.setdefault(key, 0.0)
    chunk_size = _nonlinear_assembly_chunk_size(model)
    sparse_accumulator = SparseCsrAccumulator((dofs.ndof, dofs.ndof))
    chunk_rows: list[np.ndarray] = []
    chunk_cols: list[np.ndarray] = []
    chunk_values: list[np.ndarray] = []
    chunk_entry_count = 0
    chunk_peak_entries = 0
    chunk_peak_bytes_estimate = 0
    sparse_chunk_count = 0
    internal = np.zeros(dofs.ndof, dtype=float)
    updated_states: MaterialStateTable = {}
    finite_kinematics = str(model.analysis.parameters.get("kinematics", "small_strain")).lower()
    for element_index, definition in enumerate(model.elements):
        setup_started = perf_counter()
        prepared = plan.elements[element_index] if plan is not None else None
        if prepared is not None:
            spec = prepared.spec
            element = prepared.element
            coords = prepared.coordinates
            edofs = prepared.global_dofs
            if timing is not None:
                timing["element_cache_hits"] = int(timing["element_cache_hits"]) + 1
        else:
            spec = ElementRegistry.get(definition.type)
            material = MaterialFactory.create(model.materials[definition.material])
            element = _create_nonlinear_element(
                spec,
                material,
                str(definition.type),
                finite_kinematics,
                str(model.analysis.parameters.get("tet10_nonlinear_quadrature", "hammer4")),
            )
            coords = model.nodes[list(definition.nodes)]
            edofs = np.asarray(
                [
                    index
                    for node in definition.nodes
                    for index in dofs.node_indices(node, spec.dofs)
                ],
                dtype=np.int64,
            )
            if timing is not None:
                timing["element_cache_misses"] = int(timing["element_cache_misses"]) + 1
        if timing is not None:
            timing["element_setup_seconds"] = float(timing["element_setup_seconds"]) + (
                perf_counter() - setup_started
            )
        if not hasattr(element, "internal_force_and_tangent"):
            raise InputValidationError(f"Element {definition.type} does not support nonlinear static analysis.")
        local_u = displacement[edofs]
        states = (material_states or {}).get(element_index)
        element_states: object = {}
        reference_cache_info = getattr(element, "reference_geometry_cache_info", None)
        reference_cache_before = (
            dict(reference_cache_info()) if callable(reference_cache_info) else None
        )
        try:
            kernel_started = perf_counter()
            if hasattr(element, "internal_force_tangent_state"):
                local_internal, local_tangent, element_states = element.internal_force_tangent_state(
                    coords, local_u, states
                )
                if element_states:
                    updated_states[element_index] = element_states
            else:
                local_internal, local_tangent = element.internal_force_and_tangent(coords, local_u)
            if timing is not None:
                timing["element_kernel_seconds"] = float(timing["element_kernel_seconds"]) + (
                    perf_counter() - kernel_started
                )
        except NumericalConvergenceError:
            raise
        except ValueError as error:
            message = str(error)
            lowered = message.lower()
            reason = (
                NonlinearFailureReason.MATERIAL_UPDATE_FAILURE
                if "material" in lowered or "constitutive" in lowered
                else NonlinearFailureReason.INVALID_ELEMENT
            )
            raise NumericalConvergenceError(
                f"Nonlinear element {element_index} update failed: {message}",
                reason=reason,
                diagnostics={"element_index": element_index, "element_type": definition.type},
            ) from error
        if timing is not None and reference_cache_before is not None:
            reference_cache_after = dict(reference_cache_info())
            timing["reference_cache_hits"] = int(timing["reference_cache_hits"]) + (
                int(reference_cache_after.get("hits", 0))
                - int(reference_cache_before.get("hits", 0))
            )
            timing["reference_cache_misses"] = int(timing["reference_cache_misses"]) + (
                int(reference_cache_after.get("misses", 0))
                - int(reference_cache_before.get("misses", 0))
            )
        if not np.all(np.isfinite(local_internal)) or not np.all(np.isfinite(local_tangent)):
            raise NumericalConvergenceError(
                f"Element {element_index} produced a non-finite nonlinear force or tangent.",
                reason=NonlinearFailureReason.NAN_DETECTED,
                diagnostics={"element_index": element_index},
            )
        if not state_is_finite(element_states):
            raise NumericalConvergenceError(
                f"Element {element_index} produced a non-finite material state.",
                reason=NonlinearFailureReason.NAN_DETECTED,
                diagnostics={"element_index": element_index, "state": "trial"},
            )
        scatter_started = perf_counter()
        local_internal = np.asarray(local_internal, dtype=float)
        local_tangent = np.asarray(local_tangent, dtype=float)
        if local_internal.shape != (edofs.size,) or local_tangent.shape != (edofs.size, edofs.size):
            raise NumericalConvergenceError(
                f"Element {element_index} returned an invalid local nonlinear shape.",
                reason=NonlinearFailureReason.INVALID_ELEMENT,
                diagnostics={
                    "element_index": element_index,
                    "element_type": definition.type,
                    "internal_shape": list(local_internal.shape),
                    "tangent_shape": list(local_tangent.shape),
                },
            )
        internal[edofs] += local_internal
        local_size = int(edofs.size)
        chunk_rows.append(np.repeat(edofs, local_size))
        chunk_cols.append(np.tile(edofs, local_size))
        chunk_values.append(local_tangent.reshape(-1))
        chunk_entry_count += int(local_tangent.size)
        chunk_peak_entries = max(chunk_peak_entries, chunk_entry_count)
        chunk_peak_bytes_estimate = max(
            chunk_peak_bytes_estimate,
            _sparse_chunk_bytes_estimate(chunk_entry_count),
        )
        if chunk_entry_count >= chunk_size or element_index == len(model.elements) - 1:
            sparse_started = perf_counter()
            chunk_matrix = coo_matrix(
                (
                    np.concatenate(chunk_values),
                    (np.concatenate(chunk_rows), np.concatenate(chunk_cols)),
                ),
                shape=(dofs.ndof, dofs.ndof),
            ).tocsr()
            sparse_accumulator.add(chunk_matrix)
            if timing is not None:
                timing["sparse_conversion_seconds"] = float(timing["sparse_conversion_seconds"]) + (
                    perf_counter() - sparse_started
                )
            sparse_chunk_count += 1
            chunk_rows.clear()
            chunk_cols.clear()
            chunk_values.clear()
            chunk_entry_count = 0
        if timing is not None:
            timing["element_scatter_seconds"] = float(timing["element_scatter_seconds"]) + (
                perf_counter() - scatter_started
            )
            timing["element_kernel_calls"] = int(timing["element_kernel_calls"]) + 1
    sparse_started = perf_counter()
    tangent = sparse_accumulator.finalize()
    if timing is not None:
        timing["sparse_conversion_seconds"] = float(timing["sparse_conversion_seconds"]) + (
            perf_counter() - sparse_started
        )
        timing["sparse_chunk_count"] = int(sparse_chunk_count)
        timing["sparse_peak_chunk_entries"] = int(chunk_peak_entries)
        timing["sparse_peak_chunk_bytes_estimate"] = int(chunk_peak_bytes_estimate)
        timing["sparse_accumulator_levels"] = int(sparse_accumulator.occupied_levels)
    contact_mode = str(model.analysis.parameters.get("contact_mode", "")).lower()
    if contact_diagnostics is not None:
        contact_diagnostics.clear()
        contact_diagnostics.update(
            {
                "search_mode": None,
                "active_contacts": [],
                "gaps": [],
                "master_face_indices": [],
                "finite_sliding": False,
                "projection_clamped": [],
                "closest_distances": [],
                "projection_modes": [],
            }
        )
    if model.contacts:
        if contact_mode != "penalty":
            raise InputValidationError(
                "Nonlinear contact requires explicit analysis parameter contact_mode='penalty'."
            )
        contact_started = perf_counter()
        contact_internal, contact_tangent, details = assemble_penalty_contact(
            model,
            dofs,
            displacement,
            penalty=float(model.analysis.parameters.get("contact_penalty", 1.0e6)),
        )
        if timing is not None:
            timing["contact_assembly_seconds"] = float(timing["contact_assembly_seconds"]) + (
                perf_counter() - contact_started
            )
            timing["contact_assembly_calls"] = int(timing["contact_assembly_calls"]) + 1
        internal += contact_internal
        tangent = tangent + contact_tangent
        if contact_diagnostics is not None:
            contact_diagnostics.update(
                {
                    "search_mode": details.get("search_mode"),
                    "active_contacts": list(details.get("active_contacts", [])),
                    "gaps": list(details.get("gaps", [])),
                    "master_face_indices": list(details.get("master_face_indices", [])),
                    "penalty": details.get("penalty"),
                    "maximum_penetration": details.get("maximum_penetration", 0.0),
                    "tangent_nnz": details.get("tangent_nnz", int(contact_tangent.nnz)),
                    "finite_sliding": details.get("finite_sliding", False),
                    "projection_clamped": list(details.get("projection_clamped", [])),
                    "closest_distances": list(details.get("closest_distances", [])),
                    "projection_modes": list(details.get("projection_modes", [])),
                }
            )
    if timing is not None:
        timing["tangent_nnz"] = int(tangent.nnz)
    return internal, tangent, updated_states


def _nonlinear_assembly_chunk_size(model: FiniteElementModel) -> int:
    """Return the bounded sparse chunk size for nonlinear tangent assembly."""

    value = model.analysis.parameters.get("nonlinear_assembly_chunk_size", 256)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise InputValidationError("nonlinear_assembly_chunk_size must be a positive integer.")
    return int(value)


def _sparse_chunk_bytes_estimate(entry_count: int) -> int:
    """Estimate the temporary CSR staging buffers for one assembly chunk.

    The estimate covers the source and concatenated row, column and value
    buffers. It deliberately excludes allocator overhead and the final CSR
    accumulator, so benchmark reports must label it as an estimate rather
    than a process-RSS measurement.
    """

    if entry_count <= 0:
        return 0
    bytes_per_entry = 2 * np.dtype(np.int64).itemsize + np.dtype(np.float64).itemsize
    return int(2 * entry_count * bytes_per_entry)
