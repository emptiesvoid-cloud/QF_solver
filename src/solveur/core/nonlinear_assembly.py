"""Sparse internal-force and tangent assembly for nonlinear solids."""

from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix

from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.material_state import MaterialStateTable
from solveur.core.nonlinear_contracts import NonlinearFailureReason
from solveur.core.model import FiniteElementModel
from solveur.elements.registry import ElementRegistry
from solveur.materials.factory import MaterialFactory


def assemble_internal_tangent(
    model: FiniteElementModel,
    dofs: DofManager,
    displacement: np.ndarray,
    material_states: MaterialStateTable | None = None,
) -> tuple[np.ndarray, csr_matrix, MaterialStateTable]:
    """Assemble nonlinear internal force and tangent without dense intermediates."""
    rows: list[int] = []
    cols: list[int] = []
    vals: list[float] = []
    internal = np.zeros(dofs.ndof, dtype=float)
    updated_states: MaterialStateTable = {}
    for element_index, definition in enumerate(model.elements):
        spec = ElementRegistry.get(definition.type)
        material = MaterialFactory.create(model.materials[definition.material])
        element = spec.factory(material)
        if not hasattr(element, "internal_force_and_tangent"):
            raise InputValidationError(f"Element {definition.type} does not support nonlinear static analysis.")
        coords = model.nodes[list(definition.nodes)]
        edofs: list[int] = []
        for node in definition.nodes:
            edofs.extend(dofs.node_indices(node, spec.dofs))
        local_u = displacement[edofs]
        states = (material_states or {}).get(element_index)
        if hasattr(element, "internal_force_tangent_state"):
            local_internal, local_tangent, element_states = element.internal_force_tangent_state(coords, local_u, states)
            if element_states:
                updated_states[element_index] = element_states
        else:
            local_internal, local_tangent = element.internal_force_and_tangent(coords, local_u)
        if not np.all(np.isfinite(local_internal)) or not np.all(np.isfinite(local_tangent)):
            raise NumericalConvergenceError(
                f"Element {element_index} produced a non-finite nonlinear force or tangent.",
                reason=NonlinearFailureReason.NAN_DETECTED,
                diagnostics={"element_index": element_index},
            )
        internal[edofs] += local_internal
        rr, cc = np.meshgrid(edofs, edofs, indexing="ij")
        rows.extend(rr.ravel().tolist())
        cols.extend(cc.ravel().tolist())
        vals.extend(local_tangent.ravel().tolist())
    tangent = coo_matrix((vals, (rows, cols)), shape=(dofs.ndof, dofs.ndof)).tocsr()
    return internal, tangent, updated_states
