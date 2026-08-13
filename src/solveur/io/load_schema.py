"""Strict schema validation for distributed load definitions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite
from typing import Any


class DistributedLoadSchemaValidator:
    """Validate load-specific fields against target element topology."""

    def validate(self, value: Any, elements: Any, errors: list[str]) -> None:
        if not isinstance(value, list):
            errors.append("distributed_loads must be a list when provided.")
            return
        definitions = elements if isinstance(elements, list) else []
        for index, item in enumerate(value):
            path = f"distributed_loads[{index}]"
            if not isinstance(item, Mapping):
                errors.append(f"{path} must be an object.")
                continue
            load_type = item.get("type")
            if not isinstance(load_type, str):
                errors.append(f"{path}.type must be a string.")
                continue
            load_type = load_type.lower()
            if load_type == "gravity":
                self._fields(path, item, {"type", "acceleration", "elements"}, {"type", "acceleration"}, errors)
                self._vector(f"{path}.acceleration", item.get("acceleration"), errors)
                self._targets(path, item.get("elements", "all"), len(definitions), errors)
            elif load_type == "body_force":
                self._fields(
                    path, item, {"type", "value", "elements", "coordinate_system"}, {"type", "value"}, errors
                )
                self._vector(f"{path}.value", item.get("value"), errors)
                self._targets(path, item.get("elements", "all"), len(definitions), errors)
                self._coordinate_system(path, item.get("coordinate_system", "global"), errors)
            elif load_type in {"pressure", "surface_traction"}:
                self._surface(path, item, load_type, definitions, errors)
            elif load_type == "edge_traction":
                self._edge(path, item, definitions, errors)
            elif load_type == "line_load":
                self._line(path, item, definitions, errors)
            else:
                errors.append(f"{path}.type {load_type!r} is unsupported.")

    def _surface(
        self,
        path: str,
        item: Mapping[str, Any],
        load_type: str,
        elements: list[Any],
        errors: list[str],
    ) -> None:
        allowed = {"type", "element", "face", "value", "coordinate_system", "follower"}
        self._fields(path, item, allowed, {"type", "element", "value"}, errors)
        element_type = self._element(path, item.get("element"), elements, errors)
        face = item.get("face")
        if element_type in {"TET4", "TET10"} and (not _is_int(face) or not 0 <= int(face) <= 3):
            errors.append(f"{path}.face must be an integer from 0 to 3 for {element_type}.")
        if element_type in {"MITC3", "MITC4"} and face is not None and face != 0:
            errors.append(f"{path}.face must be omitted or zero for {element_type}.")
        if load_type == "pressure":
            if not _is_number(item.get("value")):
                errors.append(f"{path}.value must be a finite scalar pressure.")
        else:
            self._vector(f"{path}.value", item.get("value"), errors)
        self._coordinate_system(path, item.get("coordinate_system", "global"), errors)
        follower = item.get("follower", False)
        if not isinstance(follower, bool):
            errors.append(f"{path}.follower must be a boolean.")
        elif follower:
            errors.append(f"{path}.follower=true is reserved for a future large-transformation formulation.")

    def _edge(self, path: str, item: Mapping[str, Any], elements: list[Any], errors: list[str]) -> None:
        allowed = {"type", "element", "edge", "value", "coordinate_system"}
        self._fields(path, item, allowed, {"type", "element", "edge", "value"}, errors)
        element_type = self._element(path, item.get("element"), elements, errors)
        if element_type is not None and element_type not in {"MITC3", "MITC4"}:
            errors.append(f"{path} edge_traction is supported for shell elements only.")
        edge = item.get("edge")
        maximum = 2 if element_type == "MITC3" else 3
        if not _is_int(edge) or not 0 <= int(edge) <= maximum:
            errors.append(f"{path}.edge must be an integer from 0 to {maximum}.")
        self._vector(f"{path}.value", item.get("value"), errors)
        self._coordinate_system(path, item.get("coordinate_system", "global"), errors)

    def _line(self, path: str, item: Mapping[str, Any], elements: list[Any], errors: list[str]) -> None:
        allowed = {"type", "element", "value", "coordinate_system"}
        self._fields(path, item, allowed, {"type", "element", "value"}, errors)
        element_type = self._element(path, item.get("element"), elements, errors)
        if element_type is not None and element_type != "BEAM2":
            errors.append(f"{path} line_load is supported for BEAM2 only.")
        self._vector(f"{path}.value", item.get("value"), errors)
        self._coordinate_system(path, item.get("coordinate_system", "global"), errors)

    @staticmethod
    def _element(path: str, value: Any, elements: list[Any], errors: list[str]) -> str | None:
        if not _is_int(value) or not 0 <= int(value) < len(elements):
            errors.append(f"{path}.element must reference an existing element.")
            return None
        element = elements[int(value)]
        return str(element.get("type", "")).upper() if isinstance(element, Mapping) else None

    @staticmethod
    def _targets(path: str, value: Any, element_count: int, errors: list[str]) -> None:
        if value == "all":
            return
        if not isinstance(value, list) or not value:
            errors.append(f"{path}.elements must be 'all' or a non-empty list of element indices.")
            return
        for position, index in enumerate(value):
            if not _is_int(index) or not 0 <= int(index) < element_count:
                errors.append(f"{path}.elements[{position}] must reference an existing element.")

    @staticmethod
    def _vector(path: str, value: Any, errors: list[str]) -> None:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 3:
            errors.append(f"{path} must contain exactly three finite components.")
            return
        if any(not _is_number(component) for component in value):
            errors.append(f"{path} must contain exactly three finite components.")

    @staticmethod
    def _coordinate_system(path: str, value: Any, errors: list[str]) -> None:
        if not isinstance(value, str) or value.lower() not in {"global", "local"}:
            errors.append(f"{path}.coordinate_system must be 'global' or 'local'.")

    @staticmethod
    def _fields(
        path: str,
        item: Mapping[str, Any],
        allowed: set[str],
        required: set[str],
        errors: list[str],
    ) -> None:
        unknown = sorted(str(key) for key in item if key not in allowed)
        if unknown:
            errors.append(f"{path} has unknown field(s): {', '.join(unknown)}.")
        for name in sorted(required):
            if name not in item:
                errors.append(f"{path}.{name} is required.")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
