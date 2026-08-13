"""Strict input validation for linear multi-point constraints."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from solveur.core.dofs import DOF_ORDER
from solveur.io.schema_values import is_int, is_number, reject_unknown


class ConstraintSchemaValidator:
    """Validate the ordered affine MPC representation used by JSON models."""

    def validate(self, value: Any, node_count: int, errors: list[str]) -> None:
        if not isinstance(value, list):
            errors.append("multipoint_constraints must be a list.")
            return
        for index, item in enumerate(value):
            self._constraint(index, item, node_count, errors)

    def validate_rbes(self, rbe2: Any, rbe3: Any, node_count: int, errors: list[str]) -> None:
        """Validate high-level links before they are expanded into MPC equations."""
        self._rbe2(rbe2, node_count, errors)
        self._rbe3(rbe3, node_count, errors)

    @staticmethod
    def _rbe2(value: Any, node_count: int, errors: list[str]) -> None:
        if not isinstance(value, list):
            errors.append("rbe2 must be a list.")
            return
        for index, item in enumerate(value):
            path = f"rbe2[{index}]"
            if not isinstance(item, Mapping):
                errors.append(f"{path} must be an object.")
                continue
            reject_unknown(path, item, {"name", "master", "slaves", "tie_rotations"}, errors)
            master = item.get("master")
            if not is_int(master) or not 0 <= int(master) < node_count:
                errors.append(f"{path}.master must reference an existing node.")
            slaves = item.get("slaves")
            if not isinstance(slaves, Sequence) or isinstance(slaves, (str, bytes)) or not slaves:
                errors.append(f"{path}.slaves must be a non-empty list of nodes.")
                continue
            if len(set(slaves)) != len(slaves):
                errors.append(f"{path}.slaves must not contain duplicates.")
            for slave_index, slave in enumerate(slaves):
                if not is_int(slave) or not 0 <= int(slave) < node_count:
                    errors.append(f"{path}.slaves[{slave_index}] must reference an existing node.")
                elif slave == master:
                    errors.append(f"{path}.slaves[{slave_index}] must differ from master.")
            if "tie_rotations" in item and not isinstance(item["tie_rotations"], bool):
                errors.append(f"{path}.tie_rotations must be boolean.")
            if "name" in item and not isinstance(item["name"], str):
                errors.append(f"{path}.name must be a string.")

    @staticmethod
    def _rbe3(value: Any, node_count: int, errors: list[str]) -> None:
        if not isinstance(value, list):
            errors.append("rbe3 must be a list.")
            return
        for index, item in enumerate(value):
            path = f"rbe3[{index}]"
            if not isinstance(item, Mapping):
                errors.append(f"{path} must be an object.")
                continue
            reject_unknown(path, item, {"name", "reference", "independents", "dofs", "mode"}, errors)
            reference = item.get("reference")
            if not is_int(reference) or not 0 <= int(reference) < node_count:
                errors.append(f"{path}.reference must reference an existing node.")
            independents = item.get("independents")
            if not isinstance(independents, Sequence) or isinstance(independents, (str, bytes)) or not independents:
                errors.append(f"{path}.independents must be a non-empty list.")
                continue
            nodes: list[int] = []
            weights: list[float] = []
            for entry_index, entry in enumerate(independents):
                entry_path = f"{path}.independents[{entry_index}]"
                if not isinstance(entry, Mapping):
                    errors.append(f"{entry_path} must be an object.")
                    continue
                reject_unknown(entry_path, entry, {"node", "weight"}, errors)
                node = entry.get("node")
                if not is_int(node) or not 0 <= int(node) < node_count:
                    errors.append(f"{entry_path}.node must reference an existing node.")
                else:
                    nodes.append(int(node))
                    if node == reference:
                        errors.append(f"{entry_path}.node must differ from reference.")
                weight = entry.get("weight")
                if not is_number(weight):
                    errors.append(f"{entry_path}.weight must be a finite number.")
                else:
                    weights.append(float(weight))
            if len(nodes) != len(set(nodes)):
                errors.append(f"{path}.independents must not repeat nodes.")
            if weights and abs(sum(weights)) <= 1.0e-14:
                errors.append(f"{path}.independents weights must have a non-zero sum.")
            mode = str(item.get("mode", "rigid_body_projection")).lower()
            if mode not in {"rigid_body_projection", "weighted"}:
                errors.append(f"{path}.mode must be 'rigid_body_projection' or 'weighted'.")
            if mode == "rigid_body_projection" and weights and any(weight <= 0.0 for weight in weights):
                errors.append(f"{path}.independents weights must be strictly positive for rigid_body_projection.")
            dofs = item.get("dofs", DOF_ORDER)
            if not isinstance(dofs, Sequence) or isinstance(dofs, (str, bytes)) or not dofs:
                errors.append(f"{path}.dofs must be a non-empty list of DOF names.")
            elif any(not isinstance(dof, str) or dof.upper() not in DOF_ORDER for dof in dofs):
                errors.append(f"{path}.dofs must contain valid DOF names.")
            elif len({dof.upper() for dof in dofs}) != len(dofs):
                errors.append(f"{path}.dofs must not contain duplicates.")
            elif mode == "rigid_body_projection" and tuple(dof.upper() for dof in dofs) != DOF_ORDER:
                errors.append(f"{path}.dofs must contain all six DOFs for rigid_body_projection.")

    @staticmethod
    def _constraint(index: int, item: Any, node_count: int, errors: list[str]) -> None:
        path = f"multipoint_constraints[{index}]"
        if not isinstance(item, Mapping):
            errors.append(f"{path} must be an object.")
            return
        reject_unknown(path, item, {"name", "terms", "value"}, errors)
        terms = item.get("terms")
        if not isinstance(terms, Sequence) or isinstance(terms, (str, bytes)) or len(terms) < 2:
            errors.append(f"{path}.terms must contain at least two ordered terms.")
            return
        if "value" in item and not is_number(item["value"]):
            errors.append(f"{path}.value must be a finite number.")
        if "name" in item and not isinstance(item["name"], str):
            errors.append(f"{path}.name must be a string.")
        seen: set[tuple[int, str]] = set()
        for term_index, term in enumerate(terms):
            term_path = f"{path}.terms[{term_index}]"
            if not isinstance(term, Mapping):
                errors.append(f"{term_path} must be an object.")
                continue
            reject_unknown(term_path, term, {"node", "dof", "coefficient"}, errors)
            node = term.get("node")
            if not is_int(node) or not 0 <= int(node) < node_count:
                errors.append(f"{term_path}.node must reference an existing node.")
            dof = term.get("dof")
            if not isinstance(dof, str) or dof.upper() not in DOF_ORDER:
                errors.append(f"{term_path}.dof must be a valid DOF name.")
                continue
            key = (int(node), dof.upper()) if is_int(node) else (-1, dof.upper())
            if key in seen:
                errors.append(f"{path}.terms must not repeat node/DOF pairs.")
            seen.add(key)
            coefficient = term.get("coefficient")
            if not is_number(coefficient):
                errors.append(f"{term_path}.coefficient must be a finite number.")
            elif term_index == 0 and abs(float(coefficient)) <= 1.0e-14:
                errors.append(f"{term_path}.coefficient must be non-zero for the dependent DOF.")
