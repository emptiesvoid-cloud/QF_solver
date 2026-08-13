"""Strict JSON validation for springs and concentrated masses."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from solveur.core.dofs import DOF_ORDER
from solveur.io.schema_values import is_int, is_number, is_numeric_matrix, is_numeric_vector, reject_unknown


class DiscreteEntitySchemaValidator:
    """Validate discrete mechanical entities without constructing the model."""

    def validate(
        self,
        springs: Any,
        masses: Any,
        node_count: int,
        errors: list[str],
    ) -> None:
        self._springs(springs, node_count, errors)
        self._masses(masses, node_count, errors)

    def _springs(self, value: Any, node_count: int, errors: list[str]) -> None:
        if not isinstance(value, list):
            errors.append("springs must be a list.")
            return
        for index, item in enumerate(value):
            path = f"springs[{index}]"
            if not isinstance(item, Mapping):
                errors.append(f"{path} must be an object.")
                continue
            reject_unknown(
                path,
                item,
                {
                    "node_a",
                    "node_b",
                    "dofs",
                    "stiffness",
                    "stiffness_matrix",
                    "coordinate_system",
                    "orientation",
                },
                errors,
            )
            self._node(f"{path}.node_a", item.get("node_a"), node_count, errors)
            if item.get("node_b") is not None:
                self._node(f"{path}.node_b", item["node_b"], node_count, errors)
                if item.get("node_a") == item.get("node_b"):
                    errors.append(f"{path}.node_b must differ from node_a.")
            dofs = item.get("dofs")
            if (
                not isinstance(dofs, Sequence)
                or isinstance(dofs, (str, bytes))
                or not dofs
                or any(str(name).upper() not in DOF_ORDER for name in dofs)
            ):
                errors.append(f"{path}.dofs must be a non-empty list of valid DOF names.")
                continue
            if len({str(name).upper() for name in dofs}) != len(dofs):
                errors.append(f"{path}.dofs must not contain duplicates.")
            has_stiffness = "stiffness" in item
            has_matrix = "stiffness_matrix" in item
            if has_stiffness == has_matrix:
                errors.append(f"{path} must define exactly one of stiffness or stiffness_matrix.")
                continue
            matrix = self._spring_matrix(path, item, len(dofs), errors)
            if matrix is not None:
                self._positive_semidefinite(f"{path}.stiffness", matrix, errors)
            system = str(item.get("coordinate_system", "global")).lower()
            if system not in {"global", "local"}:
                errors.append(f"{path}.coordinate_system must be 'global' or 'local'.")
            if system == "local":
                self._orientation(path, item.get("orientation"), errors)
            elif "orientation" in item:
                errors.append(f"{path}.orientation is only valid for a local spring.")

    def _masses(self, value: Any, node_count: int, errors: list[str]) -> None:
        if not isinstance(value, list):
            errors.append("concentrated_masses must be a list.")
            return
        for index, item in enumerate(value):
            path = f"concentrated_masses[{index}]"
            if not isinstance(item, Mapping):
                errors.append(f"{path} must be an object.")
                continue
            reject_unknown(path, item, {"node", "mass", "center_of_mass", "inertia"}, errors)
            self._node(f"{path}.node", item.get("node"), node_count, errors)
            if not is_number(item.get("mass")) or float(item["mass"]) <= 0.0:
                errors.append(f"{path}.mass must be a strictly positive finite number.")
            if "center_of_mass" in item and not is_numeric_vector(item["center_of_mass"], 3):
                errors.append(f"{path}.center_of_mass must contain exactly 3 finite numbers.")
            if "inertia" in item:
                if not is_numeric_matrix(item["inertia"], 3, 3):
                    errors.append(f"{path}.inertia must be a finite 3x3 matrix.")
                else:
                    inertia = np.asarray(item["inertia"], dtype=float)
                    if not np.allclose(inertia, inertia.T, rtol=0.0, atol=1.0e-12):
                        errors.append(f"{path}.inertia must be symmetric.")
                    else:
                        self._positive_semidefinite(f"{path}.inertia", inertia, errors)
                        moments = np.linalg.eigvalsh(inertia)
                        tolerance = max(1.0, float(np.max(abs(moments)))) * 1.0e-12
                        if moments[-1] > moments[0] + moments[1] + tolerance:
                            errors.append(f"{path}.inertia violates the principal-moment triangle inequality.")

    @staticmethod
    def _spring_matrix(
        path: str,
        item: Mapping[str, Any],
        size: int,
        errors: list[str],
    ) -> np.ndarray | None:
        value = item.get("stiffness_matrix", item.get("stiffness"))
        if is_number(value):
            return np.diag([float(value)] * size)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            if len(value) == size and all(is_number(component) for component in value):
                return np.diag(np.asarray(value, dtype=float))
            if is_numeric_matrix(value, size, size):
                matrix = np.asarray(value, dtype=float)
                if not np.allclose(matrix, matrix.T, rtol=0.0, atol=1.0e-12):
                    errors.append(f"{path}.stiffness_matrix must be symmetric.")
                    return None
                return matrix
        errors.append(f"{path}.stiffness must be a scalar, a {size}-vector or a symmetric {size}x{size} matrix.")
        return None

    @staticmethod
    def _orientation(path: str, value: Any, errors: list[str]) -> None:
        if not is_numeric_matrix(value, 3, 3):
            errors.append(f"{path}.orientation must be a finite 3x3 matrix for a local spring.")
            return
        rotation = np.asarray(value, dtype=float)
        if not np.allclose(rotation.T @ rotation, np.eye(3), rtol=0.0, atol=1.0e-10):
            errors.append(f"{path}.orientation must be orthonormal.")
        if np.linalg.det(rotation) <= 0.0:
            errors.append(f"{path}.orientation must be right-handed.")

    @staticmethod
    def _positive_semidefinite(path: str, matrix: np.ndarray, errors: list[str]) -> None:
        scale = max(1.0, float(np.max(np.abs(matrix))))
        if np.min(np.linalg.eigvalsh(matrix)) < -1.0e-12 * scale:
            errors.append(f"{path} must be positive semidefinite.")

    @staticmethod
    def _node(path: str, value: Any, node_count: int, errors: list[str]) -> None:
        if not is_int(value) or not 0 <= int(value) < node_count:
            errors.append(f"{path} must reference an existing node.")
