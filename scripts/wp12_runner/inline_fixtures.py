"""Static, versioned identities for inline scientific-test fixtures."""

from __future__ import annotations

import ast
import hashlib
import json
from typing import Any

from .contracts import ContractError


FIXTURE_SCHEMA = "qf-wp12-inline-fixture-v1"
PILOT_NODEID = (
    "tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form"
)


def _assignment_value(function: ast.FunctionDef, name: str) -> Any:
    for node in ast.walk(function):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        call = node.value
        if not isinstance(call, ast.Call) or not call.args:
            break
        if name == "stiffness":
            inner = call.args[0]
            if not isinstance(inner, ast.Call) or not inner.args:
                break
            call = inner
        try:
            value = ast.literal_eval(call.args[0])
        except (ValueError, TypeError) as exc:
            raise ContractError(f"inline fixture {name} is not a literal value") from exc
        return value
    raise ContractError(f"inline fixture assignment not found: {name}")


def _shape(value: Any) -> list[int]:
    if not isinstance(value, list):
        raise ContractError("inline fixture arrays must be nested lists")
    if not value:
        return [0]
    child_shapes = [_shape(item) if isinstance(item, list) else [] for item in value]
    if any(shape != child_shapes[0] for shape in child_shapes):
        raise ContractError("inline fixture array is ragged")
    return [len(value), *child_shapes[0]]


def _decimal_strings(value: Any) -> Any:
    if isinstance(value, list):
        return [_decimal_strings(item) for item in value]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError("inline fixture values must be finite numeric literals")
    if isinstance(value, float) and (value != value or value in {float("inf"), float("-inf")}):
        raise ContractError("non-finite inline fixture value")
    return repr(float(value))


def projection_pilot_fixture(source: bytes) -> dict[str, Any]:
    """Extract exactly the matrices assigned by the selected test function."""
    try:
        tree = ast.parse(source.decode("utf-8"))
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise ContractError("pilot test source is not valid UTF-8 Python") from exc
    functions = [
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == PILOT_NODEID.split("::")[-1]
    ]
    if len(functions) != 1:
        raise ContractError("pilot nodeid must resolve to exactly one top-level function")
    function = functions[0]
    arrays = []
    for name, dtype in (("stiffness", "float64/csr_matrix"), ("modes", "float64")):
        values = _assignment_value(function, name)
        arrays.append(
            {"name": name, "dtype": dtype, "shape": _shape(values), "decimal_values": _decimal_strings(values)}
        )
    return {
        "schema": FIXTURE_SCHEMA,
        "fixture_id": "WP12-1-PILOT-001-projection-matrices",
        "nodeid": PILOT_NODEID,
        "encoding": "UTF-8 JSON; sorted ASCII keys; compact separators; decimal float tokens encoded as strings; no newline",
        "arrays": arrays,
    }


def canonical_fixture_bytes(fixture: dict[str, Any]) -> bytes:
    if fixture.get("schema") != FIXTURE_SCHEMA:
        raise ContractError("unsupported inline-fixture schema")
    return json.dumps(fixture, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
        "utf-8"
    )


def fixture_sha256(fixture: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_fixture_bytes(fixture)).hexdigest()
