"""Strict JSON validation for bounded node-to-triangle contact."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from solveur.io.schema_values import is_int, is_number, reject_unknown


class ContactSchemaValidator:
    """Validate the V1 frictionless-contact input representation."""

    def validate(self, value: Any, node_count: int, errors: list[str]) -> None:
        if not isinstance(value, list):
            errors.append("contacts must be a list.")
            return
        for index, item in enumerate(value):
            path = f"contacts[{index}]"
            if not isinstance(item, Mapping):
                errors.append(f"{path} must be an object.")
                continue
            reject_unknown(
                path,
                item,
                {
                    "name",
                    "slave_node",
                    "slave_nodes",
                    "master_nodes",
                    "master_faces",
                    "gap_tolerance",
                    "friction_coefficient",
                    "tangential_stiffness",
                },
                errors,
            )
            has_slave_node = "slave_node" in item
            has_slave_nodes = "slave_nodes" in item
            if has_slave_node == has_slave_nodes:
                errors.append(f"{path} must define exactly one of slave_node or slave_nodes.")
            slave_nodes: set[int] = set()
            if has_slave_node:
                slave = item.get("slave_node")
                if not is_int(slave):
                    errors.append(f"{path}.slave_node must reference an existing node.")
                elif not 0 <= int(cast(Any, slave)) < node_count:
                    errors.append(f"{path}.slave_node must reference an existing node.")
                else:
                    slave_nodes.add(int(cast(Any, slave)))
            elif has_slave_nodes:
                raw_slaves = item.get("slave_nodes")
                if not isinstance(raw_slaves, Sequence) or isinstance(raw_slaves, (str, bytes)) or not raw_slaves:
                    errors.append(f"{path}.slave_nodes must contain one or more node indices.")
                else:
                    for node_index, node in enumerate(raw_slaves):
                        if not is_int(node) or not 0 <= int(cast(Any, node)) < node_count:
                            errors.append(f"{path}.slave_nodes[{node_index}] must reference an existing node.")
                        else:
                            slave_nodes.add(int(cast(Any, node)))
                    if len(slave_nodes) != len(raw_slaves):
                        errors.append(f"{path}.slave_nodes must not contain duplicates.")
            has_nodes = "master_nodes" in item
            has_faces = "master_faces" in item
            if has_nodes == has_faces:
                errors.append(f"{path} must define exactly one of master_nodes or master_faces.")
            elif has_nodes:
                self._validate_face(item["master_nodes"], f"{path}.master_nodes", slave_nodes, node_count, errors)
            else:
                faces = item["master_faces"]
                if not isinstance(faces, Sequence) or isinstance(faces, (str, bytes)) or len(faces) == 0:
                    errors.append(f"{path}.master_faces must contain one or more triangular faces.")
                else:
                    seen: set[tuple[object, ...]] = set()
                    for face_index, face in enumerate(faces):
                        face_path = f"{path}.master_faces[{face_index}]"
                        if isinstance(face, Sequence) and not isinstance(face, (str, bytes)):
                            marker = tuple(repr(value) for value in face)
                            if marker in seen:
                                errors.append(f"{face_path} duplicates an earlier master face.")
                            seen.add(marker)
                        self._validate_face(face, face_path, slave_nodes, node_count, errors)
            if "gap_tolerance" in item and (not is_number(item["gap_tolerance"]) or float(item["gap_tolerance"]) <= 0.0):
                errors.append(f"{path}.gap_tolerance must be a positive finite number.")
            coefficient = item.get("friction_coefficient", 0.0)
            coefficient_value = float(cast(Any, coefficient)) if is_number(coefficient) else 0.0
            if not is_number(coefficient) or coefficient_value < 0.0:
                errors.append(f"{path}.friction_coefficient must be a non-negative finite number.")
            if coefficient_value > 0.0:
                stiffness = item.get("tangential_stiffness")
                if not is_number(stiffness) or float(cast(Any, stiffness)) <= 0.0:
                    errors.append(
                        f"{path}.tangential_stiffness must be a positive finite number when friction_coefficient is positive."
                    )
            elif "tangential_stiffness" in item and (
                not is_number(item["tangential_stiffness"]) or float(item["tangential_stiffness"]) <= 0.0
            ):
                errors.append(f"{path}.tangential_stiffness must be a positive finite number when supplied.")
            if "name" in item and not isinstance(item["name"], str):
                errors.append(f"{path}.name must be a string.")

    @staticmethod
    def _validate_face(value: Any, path: str, slave_nodes: set[int], node_count: int, errors: list[str]) -> None:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 3:
            errors.append(f"{path} must contain exactly three node indices.")
            return
        if len(set(value)) != 3:
            errors.append(f"{path} must not contain duplicates.")
        for node_index, node in enumerate(value):
            if not is_int(node) or not 0 <= int(node) < node_count:
                errors.append(f"{path}[{node_index}] must reference an existing node.")
            elif int(cast(Any, node)) in slave_nodes:
                errors.append(f"{path}[{node_index}] must differ from slave node(s).")
