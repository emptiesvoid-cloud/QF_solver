"""Entity JSON schema validation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from solveur.elements.registry import ElementRegistry
from solveur.io.schema_values import is_number as _is_number



class JsonSchemaEntityMixin:
    def _validate_nodes(self, value: Any, errors: list[str]) -> int:
        if not isinstance(value, list):
            errors.append("nodes must be a list of [x, y, z] coordinates.")
            return 0
        if not value:
            errors.append("nodes must not be empty.")
        for index, node in enumerate(value):
            path = f"nodes[{index}]"
            if not isinstance(node, Sequence) or isinstance(node, (str, bytes)) or len(node) != 3:
                errors.append(f"{path} must be a list of exactly 3 numeric coordinates.")
                continue
            for coord_index, coord in enumerate(node):
                if not _is_number(coord):
                    errors.append(f"{path}[{coord_index}] must be a finite number.")
        return len(value)


    def _validate_elements(self, value: Any, materials: set[str], node_count: int, errors: list[str]) -> None:
        if not isinstance(value, list):
            errors.append("elements must be a list.")
            return
        for index, element in enumerate(value):
            path = f"elements[{index}]"
            if not isinstance(element, Mapping):
                errors.append(f"{path} must be an object.")
                continue
            self._reject_unknown(path, element, {"type", "nodes", "material"}, errors)
            self._require_fields(path, element, ("type", "nodes", "material"), errors)
            element_type = self._element_type(path, element.get("type"), errors)
            spec = None
            if element_type:
                try:
                    spec = ElementRegistry.get(element_type)
                except ValueError:
                    errors.append(f"{path}.type {element_type!r} is unsupported.")
            self._validate_element_nodes(
                path, element.get("nodes"), node_count, spec.node_count if spec else None, errors
            )
            material = element.get("material")
            if not isinstance(material, str) or not material:
                errors.append(f"{path}.material must be a non-empty string.")
            elif material not in materials:
                errors.append(f"{path}.material references unknown material {material!r}.")


    def _validate_fixed_dofs(self, value: Any, node_count: int, errors: list[str]) -> None:
        if not isinstance(value, list):
            errors.append("fixed_dofs must be a list when provided.")
            return
        for index, item in enumerate(value):
            path = f"fixed_dofs[{index}]"
            if not isinstance(item, Mapping):
                errors.append(f"{path} must be an object.")
                continue
            self._reject_unknown(path, item, {"node", "dofs"}, errors)
            self._require_fields(path, item, ("node", "dofs"), errors)
            self._validate_node_index(f"{path}.node", item.get("node"), node_count, errors)
            dofs = item.get("dofs")
            if not isinstance(dofs, list) or not dofs:
                errors.append(f"{path}.dofs must be a non-empty list.")
                continue
            for dof_index, dof in enumerate(dofs):
                self._validate_dof_name(f"{path}.dofs[{dof_index}]", dof, errors)


    def _validate_loads(self, value: Any, node_count: int, errors: list[str]) -> None:
        if not isinstance(value, list):
            errors.append("loads must be a list when provided.")
            return
        for index, item in enumerate(value):
            path = f"loads[{index}]"
            if not isinstance(item, Mapping):
                errors.append(f"{path} must be an object.")
                continue
            self._reject_unknown(path, item, {"node", "dof", "value"}, errors)
            self._require_fields(path, item, ("node", "dof", "value"), errors)
            self._validate_node_index(f"{path}.node", item.get("node"), node_count, errors)
            self._validate_dof_name(f"{path}.dof", item.get("dof"), errors)
            if "value" in item and not _is_number(item["value"]):
                errors.append(f"{path}.value must be a finite number.")
