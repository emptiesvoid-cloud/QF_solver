"""Reduced damping contracts for reusable modal bases."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from solveur.core.errors import InputValidationError
from solveur.core.analyses.modal_basis_numerics import array_digest, json_snapshot, readonly
from solveur.io.checkpoint_common import checkpoint_signature


class ModalDamping:
    """Immutable reduced damping operator with explicit physical provenance."""

    def __init__(
        self,
        *,
        matrix: np.ndarray,
        source: str,
        basis_identity: str,
        operator_identity: str,
        parameters: Mapping[str, object],
        reaction_availability: str,
        reaction_reason: str,
    ) -> None:
        values = np.asarray(matrix, dtype=np.float64)
        if values.ndim != 2 or values.shape[0] != values.shape[1] or not np.all(np.isfinite(values)):
            raise InputValidationError("Reduced damping must be a finite square matrix.")
        self._matrix = readonly(values, dtype=np.float64)
        self._source = str(source)
        self._basis_identity = str(basis_identity)
        self._operator_identity = str(operator_identity)
        self._parameters = json_snapshot(dict(parameters), "damping provenance")
        self._reaction_availability = str(reaction_availability)
        self._reaction_reason = str(reaction_reason)
        self._identity = checkpoint_signature(
            {
                "identity_domain": "qf-modal-damping-identity/v1",
                "source": self._source,
                "basis_identity": self._basis_identity,
                "operator_identity": self._operator_identity,
                "parameters": self._parameters,
                "matrix_sha256": array_digest(self._matrix),
            },
            label="WP04 modal damping identity",
        )

    @property
    def matrix(self) -> np.ndarray:
        return readonly(self._matrix, dtype=np.float64)

    @property
    def identity(self) -> str:
        return self._identity

    @property
    def source(self) -> str:
        return self._source

    @property
    def basis_identity(self) -> str:
        return self._basis_identity

    @property
    def operator_identity(self) -> str:
        return self._operator_identity

    @property
    def parameters(self) -> dict[str, object]:
        return json_snapshot(self._parameters, "damping provenance")

    @property
    def reaction_availability(self) -> str:
        return self._reaction_availability

    @property
    def reaction_reason(self) -> str:
        return self._reaction_reason
