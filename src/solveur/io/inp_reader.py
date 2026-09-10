"""Fail-closed reader for the bounded Abaqus/CalculiX ``.inp`` subset."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from solveur.core.errors import InputValidationError, MeshValidationError
from solveur.core.model import FiniteElementModel
from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.tet4 import Tet4Element
from solveur.elements.solid.wedge6 import Wedge6Element
from solveur.io.manifest import sha256
from solveur.mesh.validation import MeshValidator
from solveur.version import DISPLAY_NAME, __version__


INP_ELEMENT_MAPPING: dict[str, tuple[str, int]] = {
    "C3D4": ("TET4", 4),
    "C3D6": ("WEDGE6", 6),
    "C3D8": ("HEX8", 8),
}
_DOF_NAMES = ("UX", "UY", "UZ")
_INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")
_MAX_GENERATED_SET_MEMBERS = 1_000_000


@dataclass(frozen=True)
class _Card:
    name: str
    parameters: dict[str, str | bool]
    lines: tuple[tuple[int, str], ...]
    line_number: int


@dataclass(frozen=True)
class InpImportReport:
    """Machine-readable provenance and mapping report for one ``.inp`` import."""

    status: str
    solver_name: str
    solver_version: str
    source_path: str
    source_sha256: str
    analysis: str
    node_count: int
    element_count: int
    elements_by_family: dict[str, int]
    node_sets: dict[str, int]
    element_sets: dict[str, int]
    materials: tuple[str, ...]
    sections: dict[str, str]
    boundary_records: int
    cload_records: int
    keyword_counts: dict[str, int]
    element_mapping: dict[str, str]
    label_to_index: dict[str, int]
    element_label_to_index: dict[str, int]
    units_policy: str
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InpImportResult:
    """Imported QF model together with original labels and the import report."""

    model: FiniteElementModel
    report: InpImportReport
    node_sets: dict[str, tuple[int, ...]]
    element_sets: dict[str, tuple[int, ...]]
    node_labels: tuple[int, ...]
    element_labels: tuple[int, ...]


class InpModelImporter:
    """Import only the predeclared, common Abaqus/CalculiX input subset."""

    def import_model(self, path: str | Path) -> InpImportResult:
        source = Path(path).resolve()
        if not source.is_file():
            raise InputValidationError(f"INP input does not exist: {source}")
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise InputValidationError(f"Unable to read INP input {source}: {exc}") from exc
        return self.from_text(text, source_path=source, source_sha256=sha256(source))

    def from_text(
        self,
        text: str,
        *,
        source_path: str | Path = "<memory>",
        source_sha256: str = "memory",
    ) -> InpImportResult:
        if not isinstance(text, str) or not text.strip():
            raise InputValidationError("INP input must contain at least one keyword card.")
        cards = _parse_cards(text)
        parsed = _parse_deck(cards)
        result = _build_model(parsed, source_path=source_path, source_sha256=source_sha256)
        return result


def _parse_cards(text: str) -> list[_Card]:
    cards: list[_Card] = []
    current_name: str | None = None
    current_parameters: dict[str, str | bool] = {}
    current_lines: list[tuple[int, str]] = []
    current_line_number = 0

    def finish() -> None:
        nonlocal current_name, current_parameters, current_lines, current_line_number
        if current_name is not None:
            cards.append(
                _Card(
                    name=current_name,
                    parameters=dict(current_parameters),
                    lines=tuple(current_lines),
                    line_number=current_line_number,
                )
            )
        current_name = None
        current_parameters = {}
        current_lines = []
        current_line_number = 0

    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("**"):
            continue
        if line.startswith("*"):
            finish()
            current_name, current_parameters = _parse_card_header(line, line_number)
            current_line_number = line_number
            continue
        if current_name is None:
            raise InputValidationError(f"INP data line {line_number} appears before the first keyword card.")
        current_lines.append((line_number, line))
    finish()
    if not cards:
        raise InputValidationError("INP input contains no keyword cards.")
    return cards


def _parse_card_header(line: str, line_number: int) -> tuple[str, dict[str, str | bool]]:
    pieces = [piece.strip() for piece in line[1:].split(",")]
    name = pieces[0].upper()
    if not name:
        raise InputValidationError(f"INP keyword at line {line_number} has no name.")
    parameters: dict[str, str | bool] = {}
    for piece in pieces[1:]:
        if not piece:
            continue
        if "=" in piece:
            key, value = (part.strip().upper() for part in piece.split("=", 1))
            if not key or not value:
                raise InputValidationError(f"Malformed INP parameter at line {line_number}: {piece!r}.")
            if key in parameters:
                raise InputValidationError(f"Duplicate INP parameter {key!r} at line {line_number}.")
            parameters[key] = value
        else:
            key = piece.upper()
            if key != "GENERATE":
                raise InputValidationError(f"Unsupported bare INP parameter {piece!r} at line {line_number}.")
            if key in parameters:
                raise InputValidationError(f"Duplicate INP parameter GENERATE at line {line_number}.")
            parameters[key] = True
    return name, parameters


def _parse_deck(cards: list[_Card]) -> dict[str, Any]:
    nodes: dict[int, tuple[float, float, float]] = {}
    node_sets: dict[str, list[int]] = defaultdict(list)
    elements: list[dict[str, Any]] = []
    element_sets: dict[str, list[int]] = defaultdict(list)
    materials: dict[str, dict[str, float | str]] = {}
    sections: dict[str, str] = {}
    boundary: list[tuple[int, str, tuple[str, ...]]] = []
    cloads: list[tuple[int, str, float, int]] = []
    keyword_counts: dict[str, int] = defaultdict(int)
    warnings: list[str] = []
    active_material: str | None = None
    inside_step = False
    step_count = 0
    static_count = 0

    for card in cards:
        keyword_counts[card.name] += 1
        if card.name in {"HEADING", "PREPRINT"}:
            warnings.append(f"Ignored metadata card {card.name} at line {card.line_number}.")
            continue
        if card.name not in {
            "NODE",
            "ELEMENT",
            "NSET",
            "ELSET",
            "MATERIAL",
            "ELASTIC",
            "SOLID SECTION",
            "BOUNDARY",
            "CLOAD",
            "STEP",
            "STATIC",
            "END STEP",
        }:
            raise InputValidationError(
                f"Unsupported INP keyword {card.name!r} at line {card.line_number}; input is fail-closed."
            )
        if active_material is not None and card.name != "ELASTIC":
            raise InputValidationError(
                f"*MATERIAL at line {card.line_number} must be followed immediately by *ELASTIC."
            )

        if card.name == "NODE":
            _validate_parameters(card, {"NSET"}, {"NSET"} & set(card.parameters))
            _parse_nodes(card, nodes, node_sets)
        elif card.name == "ELEMENT":
            _validate_parameters(card, {"TYPE", "ELSET"}, {"TYPE"})
            _parse_elements(card, elements, element_sets)
        elif card.name == "NSET":
            _validate_parameters(card, {"NSET", "GENERATE"}, {"NSET"})
            _parse_set(card, node_sets)
        elif card.name == "ELSET":
            _validate_parameters(card, {"ELSET", "GENERATE"}, {"ELSET"})
            _parse_set(card, element_sets)
        elif card.name == "MATERIAL":
            _validate_parameters(card, {"NAME"}, {"NAME"})
            active_material = _normalize_name(str(card.parameters["NAME"]), "material", card.line_number)
            if active_material in materials:
                raise InputValidationError(f"Duplicate material {active_material!r} at line {card.line_number}.")
        elif card.name == "ELASTIC":
            _validate_parameters(card, set(), set())
            if active_material is None:
                raise InputValidationError(f"*ELASTIC at line {card.line_number} has no active *MATERIAL.")
            values = _flatten_numeric_lines(card, expected=None)
            if len(values) != 2:
                raise InputValidationError(
                    f"*ELASTIC at line {card.line_number} requires exactly E and nu, got {len(values)} values."
                )
            young, poisson = values
            if young <= 0.0 or not -1.0 < poisson < 0.5:
                raise InputValidationError(
                    f"Invalid isotropic elastic properties at line {card.line_number}: E={young}, nu={poisson}."
                )
            materials[active_material] = {"type": "isotropic_3d", "E": young, "nu": poisson}
            active_material = None
        elif card.name == "SOLID SECTION":
            _validate_parameters(card, {"ELSET", "MATERIAL"}, {"ELSET", "MATERIAL"})
            if any(line.strip() for _, line in card.lines):
                raise InputValidationError(f"Unsupported *SOLID SECTION data at line {card.line_number}.")
            elset = _normalize_name(str(card.parameters["ELSET"]), "ELSET", card.line_number)
            material = _normalize_name(str(card.parameters["MATERIAL"]), "material", card.line_number)
            if elset in sections:
                raise InputValidationError(f"Duplicate *SOLID SECTION assignment for ELSET {elset!r}.")
            sections[elset] = material
        elif card.name == "STEP":
            _validate_parameters(card, set(), set())
            if card.lines:
                raise InputValidationError(f"*STEP at line {card.line_number} cannot contain data lines.")
            if inside_step or step_count:
                raise InputValidationError("The bounded INP subset allows exactly one non-nested *STEP.")
            inside_step = True
            step_count += 1
        elif card.name == "STATIC":
            _validate_parameters(card, set(), set())
            if not inside_step:
                raise InputValidationError(f"*STATIC at line {card.line_number} is outside *STEP.")
            if static_count:
                raise InputValidationError("The bounded INP subset allows exactly one *STATIC card.")
            values = _flatten_numeric_lines(card, expected=None)
            if len(values) > 4:
                raise InputValidationError(f"*STATIC at line {card.line_number} has too many control values.")
            static_count += 1
        elif card.name == "BOUNDARY":
            _validate_parameters(card, set(), set())
            if not inside_step:
                raise InputValidationError(f"*BOUNDARY at line {card.line_number} is outside *STEP.")
            boundary.extend(_parse_boundary(card))
        elif card.name == "CLOAD":
            _validate_parameters(card, set(), set())
            if not inside_step:
                raise InputValidationError(f"*CLOAD at line {card.line_number} is outside *STEP.")
            cloads.extend(_parse_cload(card))
        elif card.name == "END STEP":
            _validate_parameters(card, set(), set())
            if card.lines:
                raise InputValidationError(f"*END STEP at line {card.line_number} cannot contain data lines.")
            if not inside_step:
                raise InputValidationError("*END STEP has no open *STEP.")
            inside_step = False

    if active_material is not None:
        raise InputValidationError(f"Material {active_material!r} has no *ELASTIC card.")
    if inside_step or step_count != 1 or static_count != 1:
        raise InputValidationError("The bounded INP subset requires exactly one closed *STEP containing *STATIC.")
    if not nodes:
        raise InputValidationError("INP input has no nodes.")
    if not elements:
        raise InputValidationError("INP input has no supported solid elements.")
    return {
        "nodes": nodes,
        "node_sets": dict(node_sets),
        "elements": elements,
        "element_sets": dict(element_sets),
        "materials": materials,
        "sections": sections,
        "boundary": boundary,
        "cloads": cloads,
        "keyword_counts": dict(keyword_counts),
        "warnings": tuple(warnings),
    }


def _validate_parameters(card: _Card, allowed: set[str], required: set[str]) -> None:
    unknown = sorted(set(card.parameters) - allowed)
    if unknown:
        raise InputValidationError(f"Unsupported parameters {unknown} on *{card.name} at line {card.line_number}.")
    missing = sorted(required - set(card.parameters))
    if missing:
        raise InputValidationError(f"*{card.name} at line {card.line_number} requires parameters {missing}.")


def _parse_nodes(card: _Card, nodes: dict[int, tuple[float, float, float]], node_sets: dict[str, list[int]]) -> None:
    nset = (
        _normalize_name(str(card.parameters["NSET"]), "NSET", card.line_number)
        if "NSET" in card.parameters
        else None
    )
    for line_number, line in card.lines:
        values = _split_nonempty(line)
        if len(values) != 4:
            raise InputValidationError(f"Malformed *NODE row at line {line_number}; expected label,x,y,z.")
        label = _parse_positive_int(values[0], f"node label at line {line_number}")
        if label in nodes:
            raise InputValidationError(f"Duplicate node label {label} at line {line_number}.")
        coordinates = tuple(_parse_finite_float(value, f"node {label} coordinate") for value in values[1:])
        nodes[label] = coordinates  # type: ignore[assignment]
        if nset is not None:
            _append_members(node_sets, nset, [label], f"NSET {nset!r}")


def _parse_elements(card: _Card, elements: list[dict[str, Any]], element_sets: dict[str, list[int]]) -> None:
    raw_type = str(card.parameters["TYPE"]).upper()
    if raw_type not in INP_ELEMENT_MAPPING:
        raise InputValidationError(
            f"Unsupported INP element type {raw_type!r} at line {card.line_number}; no silent mapping is allowed."
        )
    family, node_count = INP_ELEMENT_MAPPING[raw_type]
    elset = (
        _normalize_name(str(card.parameters["ELSET"]), "ELSET", card.line_number)
        if "ELSET" in card.parameters
        else None
    )
    tokens: list[tuple[str, int]] = []
    for line_number, line in card.lines:
        tokens.extend((token, line_number) for token in _split_nonempty(line))
    width = node_count + 1
    if not tokens or len(tokens) % width:
        raise InputValidationError(
            f"Malformed *ELEMENT {raw_type} at line {card.line_number}; records need {width} integer fields."
        )
    for offset in range(0, len(tokens), width):
        row = tokens[offset : offset + width]
        label = _parse_positive_int(row[0][0], f"element label at line {row[0][1]}")
        if any(item["id"] == label for item in elements):
            raise InputValidationError(f"Duplicate element label {label} at line {row[0][1]}.")
        connectivity = tuple(
            _parse_positive_int(token, f"element {label} connectivity at line {line_number}")
            for token, line_number in row[1:]
        )
        if len(set(connectivity)) != len(connectivity):
            raise MeshValidationError(f"Element {label} has duplicate connectivity nodes.")
        elements.append({"id": label, "inp_type": raw_type, "family": family, "nodes": connectivity})
        if elset is not None:
            _append_members(element_sets, elset, [label], f"ELSET {elset!r}")


def _parse_set(card: _Card, sets: dict[str, list[int]]) -> None:
    key = "NSET" if card.name == "NSET" else "ELSET"
    name = _normalize_name(str(card.parameters[key]), key, card.line_number)
    generated = bool(card.parameters.get("GENERATE", False))
    members: list[int] = []
    if generated:
        for line_number, line in card.lines:
            values = _split_nonempty(line)
            if len(values) != 3:
                raise InputValidationError(f"Generated *{card.name} row at line {line_number} needs start,end,increment.")
            start = _parse_positive_int(values[0], f"generated {key} start at line {line_number}")
            end = _parse_positive_int(values[1], f"generated {key} end at line {line_number}")
            increment = _parse_positive_int(values[2], f"generated {key} increment at line {line_number}")
            if end < start:
                raise InputValidationError(f"Generated {key} range at line {line_number} must be ascending.")
            count = (end - start) // increment + 1
            if count > _MAX_GENERATED_SET_MEMBERS:
                raise InputValidationError(f"Generated {key} range at line {line_number} is too large.")
            members.extend(range(start, end + 1, increment))
    else:
        for line_number, line in card.lines:
            values = _split_nonempty(line)
            if not values:
                continue
            members.extend(_parse_positive_int(value, f"{key} member at line {line_number}") for value in values)
    if not members:
        raise InputValidationError(f"*{card.name} {name!r} cannot be empty.")
    _append_members(sets, name, members, f"{key} {name!r}")


def _parse_boundary(card: _Card) -> list[tuple[int, str, tuple[str, ...]]]:
    records: list[tuple[int, str, tuple[str, ...]]] = []
    for line_number, line in card.lines:
        values = _split_nonempty(line)
        if len(values) not in {2, 3, 4}:
            raise InputValidationError(f"Malformed *BOUNDARY row at line {line_number}.")
        target = values[0]
        first = _parse_dof(values[1], line_number)
        last = first
        prescribed = 0.0
        if len(values) == 3:
            if _INTEGER_PATTERN.fullmatch(values[2]) and 1 <= int(values[2]) <= 3:
                last = _parse_dof(values[2], line_number)
            else:
                prescribed = _parse_finite_float(values[2], f"BOUNDARY value at line {line_number}")
        elif len(values) == 4:
            last = _parse_dof(values[2], line_number)
            prescribed = _parse_finite_float(values[3], f"BOUNDARY value at line {line_number}")
        if last < first:
            raise InputValidationError(f"*BOUNDARY DOF range is descending at line {line_number}.")
        if prescribed != 0.0:
            raise InputValidationError(
                f"Nonzero prescribed displacement {prescribed} at line {line_number} is outside the bounded QF subset."
            )
        records.append((line_number, target, tuple(_DOF_NAMES[index - 1] for index in range(first, last + 1))))
    return records


def _parse_cload(card: _Card) -> list[tuple[int, str, str, float]]:
    records: list[tuple[int, str, str, float]] = []
    for line_number, line in card.lines:
        values = _split_nonempty(line)
        if len(values) != 3:
            raise InputValidationError(f"Malformed *CLOAD row at line {line_number}; expected target,dof,value.")
        dof = _parse_dof(values[1], line_number)
        value = _parse_finite_float(values[2], f"CLOAD value at line {line_number}")
        records.append((line_number, values[0], _DOF_NAMES[dof - 1], value))
    return records


def _build_model(parsed: dict[str, Any], *, source_path: str | Path, source_sha256: str) -> InpImportResult:
    nodes: dict[int, tuple[float, float, float]] = parsed["nodes"]
    node_sets: dict[str, list[int]] = parsed["node_sets"]
    elements: list[dict[str, Any]] = parsed["elements"]
    element_sets: dict[str, list[int]] = parsed["element_sets"]
    materials: dict[str, dict[str, float | str]] = parsed["materials"]
    sections: dict[str, str] = parsed["sections"]
    node_labels = tuple(sorted(nodes))
    element_labels = tuple(int(item["id"]) for item in elements)
    node_label_to_index = {label: index for index, label in enumerate(node_labels)}
    element_label_to_index = {label: index for index, label in enumerate(element_labels)}
    element_ids = set(element_labels)

    for name, members in node_sets.items():
        _validate_set_members(name, members, set(node_labels), "NSET")
    for name, members in element_sets.items():
        _validate_set_members(name, members, element_ids, "ELSET")
    for elset, material in sections.items():
        if elset not in element_sets:
            raise InputValidationError(f"*SOLID SECTION references missing ELSET {elset!r}.")
        if material not in materials:
            raise InputValidationError(f"*SOLID SECTION references missing MATERIAL {material!r}.")

    assignments: dict[int, str] = {}
    for elset, material in sections.items():
        for element_id in element_sets[elset]:
            previous = assignments.get(element_id)
            if previous is not None:
                raise MeshValidationError(
                    f"Element {element_id} receives conflicting material assignments {previous!r}/{material!r}."
                )
            assignments[element_id] = material
    missing_material = sorted(element_ids - assignments.keys())
    if missing_material:
        raise InputValidationError(f"Elements without a SOLID SECTION material: {missing_material[:8]}.")

    model_elements: list[dict[str, Any]] = []
    family_counts: dict[str, int] = defaultdict(int)
    for item in elements:
        element_id = int(item["id"])
        family = str(item["family"])
        labels = tuple(int(label) for label in item["nodes"])
        if any(label not in nodes for label in labels):
            missing = sorted(set(labels) - set(nodes))
            raise MeshValidationError(f"Element {element_id} references missing node labels {missing}.")
        coordinates = np.asarray([nodes[label] for label in labels], dtype=float)
        _validate_geometry(family, coordinates, element_id)
        model_elements.append(
            {
                "type": family,
                "nodes": [node_label_to_index[label] for label in labels],
                "material": assignments[element_id],
            }
        )
        family_counts[family] += 1

    fixed_by_node: dict[int, set[str]] = defaultdict(set)
    for line_number, target, dofs in parsed["boundary"]:
        for label in _resolve_target(target, node_sets, set(node_labels), "NSET", line_number):
            fixed_by_node[label].update(dofs)
    fixed_dofs = [
        {"node": node_label_to_index[label], "dofs": [dof for dof in _DOF_NAMES if dof in fixed_by_node[label]]}
        for label in sorted(fixed_by_node)
    ]

    loads: list[dict[str, Any]] = []
    for line_number, target, dof, value in parsed["cloads"]:
        for label in _resolve_target(target, node_sets, set(node_labels), "NSET", line_number):
            loads.append({"node": node_label_to_index[label], "dof": dof, "value": value})

    model = FiniteElementModel.from_raw(
        nodes=[list(nodes[label]) for label in node_labels],
        elements=model_elements,
        materials={name: dict(values) for name, values in materials.items()},
        fixed_dofs=fixed_dofs,
        loads=loads,
        analysis={"type": "linear_static", "method": "direct"},
        units={"system": "USER_CONSISTENT"},
        verification_profile="engineering",
    )
    mesh_report = MeshValidator().validate(model)
    if mesh_report.status == "FAIL":
        raise MeshValidationError("Imported INP model is invalid: " + "; ".join(mesh_report.errors))
    report = InpImportReport(
        status="WARNING" if parsed["warnings"] or mesh_report.warnings else "PASS",
        solver_name=DISPLAY_NAME,
        solver_version=__version__,
        source_path=_portable_input_path(source_path),
        source_sha256=source_sha256,
        analysis="linear_static",
        node_count=model.node_count,
        element_count=len(model.elements),
        elements_by_family=dict(sorted(family_counts.items())),
        node_sets={name: len(values) for name, values in sorted(node_sets.items())},
        element_sets={name: len(values) for name, values in sorted(element_sets.items())},
        materials=tuple(sorted(materials)),
        sections=dict(sorted(sections.items())),
        boundary_records=len(fixed_dofs),
        cload_records=len(loads),
        keyword_counts=dict(sorted(parsed["keyword_counts"].items())),
        element_mapping={key: value[0] for key, value in sorted(INP_ELEMENT_MAPPING.items())},
        label_to_index={str(label): index for label, index in node_label_to_index.items()},
        element_label_to_index={str(label): index for label, index in element_label_to_index.items()},
        units_policy="USER_CONSISTENT / NO_AUTOMATIC_CONVERSION",
        warnings=tuple(parsed["warnings"]) + tuple(mesh_report.warnings),
    )
    return InpImportResult(
        model=model,
        report=report,
        node_sets={name: tuple(values) for name, values in sorted(node_sets.items())},
        element_sets={name: tuple(values) for name, values in sorted(element_sets.items())},
        node_labels=node_labels,
        element_labels=element_labels,
    )


def _validate_geometry(family: str, coordinates: np.ndarray, element_id: int) -> None:
    try:
        if family == "TET4":
            span = max(float(np.max(np.ptp(coordinates, axis=0))), 1.0)
            volume = Tet4Element.signed_volume(coordinates)
            if not math.isfinite(volume) or volume <= 1.0e-14 * span**3:
                raise ValueError(f"signed volume {volume:.6e} is not positive")
        elif family == "WEDGE6":
            Wedge6Element.validate_geometry(coordinates)
        elif family == "HEX8":
            Hex8Element.validate_geometry(coordinates)
        else:
            raise ValueError(f"unsupported internal family {family!r}")
    except ValueError as exc:
        raise MeshValidationError(f"Invalid orientation/Jacobian for {family} element {element_id}: {exc}") from exc


def _validate_set_members(name: str, members: list[int], valid: set[int], kind: str) -> None:
    if not members:
        raise InputValidationError(f"{kind} {name!r} is empty.")
    missing = sorted(set(members) - valid)
    if missing:
        raise InputValidationError(f"{kind} {name!r} references missing labels {missing[:8]}.")


def _resolve_target(target: str, sets: dict[str, list[int]], valid: set[int], kind: str, line_number: int) -> tuple[int, ...]:
    if _INTEGER_PATTERN.fullmatch(target):
        label = _parse_positive_int(target, f"target at line {line_number}")
        if label not in valid:
            raise InputValidationError(f"{kind} target node label {label} at line {line_number} does not exist.")
        return (label,)
    name = _normalize_name(target, kind, line_number)
    if name not in sets:
        raise InputValidationError(f"{kind} {name!r} at line {line_number} does not exist.")
    return tuple(sets[name])


def _append_members(sets: dict[str, list[int]], name: str, members: list[int], description: str) -> None:
    current = sets[name]
    duplicates = sorted(set(current).intersection(members))
    if duplicates:
        raise InputValidationError(f"Duplicate members {duplicates[:8]} in {description}.")
    current.extend(members)


def _flatten_numeric_lines(card: _Card, expected: int | None) -> list[float]:
    values: list[float] = []
    for line_number, line in card.lines:
        values.extend(_parse_finite_float(token, f"*{card.name} value at line {line_number}") for token in _split_nonempty(line))
    if expected is not None and len(values) != expected:
        raise InputValidationError(f"*{card.name} at line {card.line_number} has {len(values)} values, expected {expected}.")
    return values


def _split_nonempty(line: str) -> list[str]:
    return [piece.strip() for piece in line.split(",") if piece.strip()]


def _parse_positive_int(value: str, description: str) -> int:
    if not _INTEGER_PATTERN.fullmatch(value):
        raise InputValidationError(f"{description} must be a positive integer, got {value!r}.")
    parsed = int(value)
    if parsed <= 0:
        raise InputValidationError(f"{description} must be positive, got {parsed}.")
    return parsed


def _parse_finite_float(value: str, description: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{description} must be numeric, got {value!r}.") from exc
    if not math.isfinite(parsed):
        raise InputValidationError(f"{description} must be finite, got {value!r}.")
    return parsed


def _parse_dof(value: str, line_number: int) -> int:
    if not _INTEGER_PATTERN.fullmatch(value):
        raise InputValidationError(f"DOF at line {line_number} must be an integer from 1 to 3.")
    dof = int(value)
    if dof not in {1, 2, 3}:
        raise InputValidationError(f"DOF at line {line_number} must be in 1..3, got {dof}.")
    return dof


def _normalize_name(value: str, kind: str, line_number: int) -> str:
    name = value.strip().upper()
    if not name:
        raise InputValidationError(f"Empty {kind} name at line {line_number}.")
    return name


def _portable_input_path(path: str | Path) -> str:
    raw = str(path)
    if raw == "<memory>":
        return raw
    candidate = Path(raw)
    return candidate.name if candidate.is_absolute() else candidate.as_posix()


__all__ = ["INP_ELEMENT_MAPPING", "InpImportReport", "InpImportResult", "InpModelImporter"]
