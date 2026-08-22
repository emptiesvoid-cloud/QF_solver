"""Strict JSON loaders for solver-neutral V&V studies and results."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from solveur.core.errors import InputValidationError
from solveur.verification.vnv_types import (
    VnvConvergenceSpec,
    VnvLevel,
    VnvNormalizedResult,
    VnvQuantitySpec,
    VnvQuantityValue,
    VnvStudy,
)


IDENTIFIER = re.compile(r"^[A-Z0-9][A-Z0-9_-]*$")
ARTIFACT_KEY = re.compile(r"^[a-z][a-z0-9_]*$")
DECISIONS = {"pending", "accepted", "accepted_with_reservations", "rejected"}
REVIEW_MODES = {"self_review", "independent_review"}
METRICS = {"relative_error", "absolute_error"}


class VnvStudyLoader:
    """Load and validate one controlled comparison protocol."""

    def load(self, path: str | Path) -> VnvStudy:
        source = Path(path).resolve()
        data = _read_object(source, "V&V study")
        _reject_unknown(
            data,
            {
                "schema_version",
                "study_id",
                "title",
                "scope",
                "subject",
                "units_system",
                "author",
                "validation",
                "reference",
                "quantities",
                "levels",
                "convergence",
                "acceptance",
            },
            "V&V study",
        )
        _schema_version(data, "V&V study")
        identifier = _identifier(data.get("study_id"), "study_id")
        title = _text(data.get("title"), "title")
        scope = _text(data.get("scope"), "scope")
        subject = _string_map(data.get("subject"), "subject", required=("kind", "name", "maturity"))
        units_system = _text(data.get("units_system"), "units_system")
        author = _string_map(data.get("author"), "author", required=("name", "role"))
        validation = self._validation(data.get("validation"), author)
        reference = _string_map(
            data.get("reference"),
            "reference",
            required=("kind", "solver", "version", "manual_citation", "case"),
        )
        if any("A_RENSEIGNER" in item for item in reference.values()):
            raise InputValidationError("V&V reference contains an A_RENSEIGNER placeholder.")
        quantities = self._quantities(data.get("quantities"))
        levels = self._levels(data.get("levels"), source.parent)
        convergence = self._convergence(data.get("convergence", []), quantities, levels)
        acceptance = _object(data.get("acceptance", {}), "acceptance")
        _reject_unknown(acceptance, {"deformation_requirement"}, "acceptance")
        deformation_requirement = str(acceptance.get("deformation_requirement", "finest"))
        if deformation_requirement not in {"none", "finest", "all"}:
            raise InputValidationError("acceptance.deformation_requirement must be none, finest or all.")
        return VnvStudy(
            source,
            identifier,
            title,
            scope,
            subject,
            units_system,
            author,
            validation,
            reference,
            quantities,
            levels,
            convergence,
            deformation_requirement,
        )

    @staticmethod
    def _validation(value: Any, author: dict[str, str]) -> dict[str, Any]:
        data = _object(value, "validation")
        _reject_unknown(data, {"validator", "mode", "decision", "date", "comments"}, "validation")
        validator = _string_map(data.get("validator"), "validation.validator", required=("name", "role"))
        mode = _text(data.get("mode"), "validation.mode")
        decision = _text(data.get("decision"), "validation.decision")
        if mode not in REVIEW_MODES:
            raise InputValidationError(f"validation.mode must be one of {sorted(REVIEW_MODES)}.")
        if decision not in DECISIONS:
            raise InputValidationError(f"validation.decision must be one of {sorted(DECISIONS)}.")
        same_person = validator["name"].casefold() == author["name"].casefold()
        if same_person and mode != "self_review":
            raise InputValidationError("The author and validator are identical; validation.mode must be self_review.")
        date = data.get("date")
        if decision != "pending" and (not isinstance(date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date)):
            raise InputValidationError("A YYYY-MM-DD validation.date is required for a completed owner decision.")
        comments = str(data.get("comments", ""))
        if decision == "accepted_with_reservations" and not comments.strip():
            raise InputValidationError("accepted_with_reservations requires explicit validation.comments.")
        return {
            "validator": validator,
            "mode": mode,
            "independence": "not_independent" if same_person else "independent",
            "decision": decision,
            "date": date,
            "comments": comments,
        }

    @staticmethod
    def _quantities(value: Any) -> tuple[VnvQuantitySpec, ...]:
        rows = _nonempty_list(value, "quantities")
        records: list[VnvQuantitySpec] = []
        identifiers: set[str] = set()
        for index, raw in enumerate(rows):
            data = _object(raw, f"quantities[{index}]")
            _reject_unknown(data, {"id", "label", "metric", "limit", "absolute_floor", "extraction"}, f"quantities[{index}]")
            identifier = _identifier(data.get("id"), f"quantities[{index}].id", upper=False)
            if identifier in identifiers:
                raise InputValidationError(f"Duplicate V&V quantity {identifier!r}.")
            metric = _text(data.get("metric"), f"quantities[{index}].metric")
            if metric not in METRICS:
                raise InputValidationError(f"Quantity metric must be one of {sorted(METRICS)}.")
            records.append(
                VnvQuantitySpec(
                    identifier,
                    _text(data.get("label"), f"quantities[{index}].label"),
                    metric,
                    _positive(data.get("limit"), f"quantities[{index}].limit"),
                    _nonnegative(data.get("absolute_floor", 1.0e-15), f"quantities[{index}].absolute_floor"),
                    _string_map(
                        data.get("extraction"),
                        f"quantities[{index}].extraction",
                        required=("location", "component", "reduction"),
                    ),
                )
            )
            identifiers.add(identifier)
        return tuple(records)

    @staticmethod
    def _levels(value: Any, root: Path) -> tuple[VnvLevel, ...]:
        rows = _nonempty_list(value, "levels")
        records: list[VnvLevel] = []
        identifiers: set[str] = set()
        sizes: list[float] = []
        for index, raw in enumerate(rows):
            data = _object(raw, f"levels[{index}]")
            _reject_unknown(
                data,
                {"id", "characteristic_size", "qf_result", "reference_result"},
                f"levels[{index}]",
            )
            identifier = _identifier(data.get("id"), f"levels[{index}].id", upper=False)
            if identifier in identifiers:
                raise InputValidationError(f"Duplicate V&V mesh level {identifier!r}.")
            size = _positive(data.get("characteristic_size"), f"levels[{index}].characteristic_size")
            records.append(
                VnvLevel(
                    identifier,
                    size,
                    _path(root, data.get("qf_result"), f"levels[{index}].qf_result"),
                    _path(root, data.get("reference_result"), f"levels[{index}].reference_result"),
                )
            )
            identifiers.add(identifier)
            sizes.append(size)
        if len(set(sizes)) != len(sizes):
            raise InputValidationError("Mesh characteristic sizes must be unique.")
        if any(fine >= coarse for coarse, fine in zip(sizes, sizes[1:])):
            raise InputValidationError("V&V levels must be ordered from coarse to fine with decreasing size.")
        return tuple(records)

    @staticmethod
    def _convergence(
        value: Any,
        quantities: tuple[VnvQuantitySpec, ...],
        levels: tuple[VnvLevel, ...],
    ) -> tuple[VnvConvergenceSpec, ...]:
        rows = _list(value, "convergence")
        known = {item.identifier for item in quantities}
        records: list[VnvConvergenceSpec] = []
        seen: set[str] = set()
        if rows and len(levels) < 3:
            raise InputValidationError("A convergence study requires at least three mesh levels.")
        for index, raw in enumerate(rows):
            data = _object(raw, f"convergence[{index}]")
            _reject_unknown(
                data,
                {"quantity", "require_monotonic", "minimum_order", "finest_error_limit"},
                f"convergence[{index}]",
            )
            quantity = _identifier(data.get("quantity"), f"convergence[{index}].quantity", upper=False)
            if quantity not in known or quantity in seen:
                raise InputValidationError(f"Invalid or duplicate convergence quantity {quantity!r}.")
            minimum = data.get("minimum_order")
            records.append(
                VnvConvergenceSpec(
                    quantity,
                    bool(data.get("require_monotonic", True)),
                    None if minimum is None else _finite(minimum, f"convergence[{index}].minimum_order"),
                    _positive(data.get("finest_error_limit"), f"convergence[{index}].finest_error_limit"),
                )
            )
            seen.add(quantity)
        return tuple(records)


class VnvResultLoader:
    """Load one QF_solver or external-solver normalized result."""

    def load(self, path: str | Path, *, study: VnvStudy, role: str) -> VnvNormalizedResult:
        source = Path(path).resolve()
        data = _read_object(source, f"{role} normalized result")
        _reject_unknown(
            data,
            {
                "schema_version",
                "case_id",
                "producer",
                "units_system",
                "mesh",
                "quantities",
                "diagnostics",
                "visualization",
                "artifacts",
            },
            f"{role} normalized result",
        )
        _schema_version(data, f"{role} normalized result")
        case_id = _identifier(data.get("case_id"), "case_id")
        if case_id != study.identifier:
            raise InputValidationError(f"Result case_id {case_id!r} does not match study {study.identifier!r}.")
        producer = _string_map(data.get("producer"), "producer", required=("name", "version", "run_id"))
        expected = "QF_solver" if role == "qf" else study.reference["solver"]
        if producer["name"].casefold() != expected.casefold():
            raise InputValidationError(f"{role} producer must be {expected!r}, got {producer['name']!r}.")
        units_system = _text(data.get("units_system"), "units_system")
        if units_system != study.units_system:
            raise InputValidationError(
                f"Result units_system {units_system!r} does not match study {study.units_system!r}."
            )
        mesh = _numeric_map(data.get("mesh"), "mesh")
        quantities = self._quantities(data.get("quantities"))
        artifacts = self._artifacts(data.get("artifacts", {}), source.parent)
        return VnvNormalizedResult(
            source,
            case_id,
            producer,
            units_system,
            mesh,
            quantities,
            _object(data.get("diagnostics", {}), "diagnostics"),
            self._visualization(data.get("visualization")),
            artifacts,
        )

    @staticmethod
    def _quantities(value: Any) -> dict[str, VnvQuantityValue]:
        data = _object(value, "quantities")
        if not data:
            raise InputValidationError("Normalized result quantities cannot be empty.")
        records: dict[str, VnvQuantityValue] = {}
        for identifier, raw in data.items():
            key = _identifier(identifier, "quantity id", upper=False)
            row = _object(raw, f"quantities.{key}")
            _reject_unknown(row, {"value", "unit"}, f"quantities.{key}")
            records[key] = VnvQuantityValue(
                _finite(row.get("value"), f"quantities.{key}.value"),
                _text(row.get("unit"), f"quantities.{key}.unit"),
            )
        return records

    @staticmethod
    def _artifacts(value: Any, root: Path) -> dict[str, Path]:
        data = _object(value, "artifacts")
        records: dict[str, Path] = {}
        for key, raw in data.items():
            if not ARTIFACT_KEY.fullmatch(str(key)):
                raise InputValidationError(f"Invalid artifact key {key!r}.")
            records[str(key)] = _path(root, raw, f"artifacts.{key}")
        return records

    @staticmethod
    def _visualization(value: Any) -> dict[str, Any]:
        data = _object(value, "visualization")
        _reject_unknown(data, {"deformation_scale", "field", "view", "undeformed_overlay"}, "visualization")
        return {
            "deformation_scale": _positive(data.get("deformation_scale"), "visualization.deformation_scale"),
            "field": _text(data.get("field"), "visualization.field"),
            "view": _text(data.get("view"), "visualization.view"),
            "undeformed_overlay": bool(data.get("undeformed_overlay", True)),
        }


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        return _object(json.loads(path.read_text(encoding="utf-8")), label)
    except OSError as exc:
        raise InputValidationError(f"Cannot read {label} {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise InputValidationError(f"Malformed JSON in {label} {path}: {exc}") from exc


def _schema_version(data: dict[str, Any], label: str) -> None:
    if data.get("schema_version") != 1:
        raise InputValidationError(f"{label} schema_version must be 1.")


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputValidationError(f"{label} must be a JSON object.")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise InputValidationError(f"{label} must be a JSON array.")
    return value


def _nonempty_list(value: Any, label: str) -> list[Any]:
    records = _list(value, label)
    if not records:
        raise InputValidationError(f"{label} cannot be empty.")
    return records


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError(f"{label} must be a non-empty string.")
    return value.strip()


def _identifier(value: Any, label: str, *, upper: bool = True) -> str:
    text = _text(value, label)
    candidate = text.upper() if upper else text
    pattern = IDENTIFIER if upper else re.compile(r"^[a-z0-9][a-z0-9_-]*$")
    if not pattern.fullmatch(candidate):
        raise InputValidationError(f"{label} has invalid identifier {text!r}.")
    return candidate


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise InputValidationError(f"{label} must be numeric.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{label} must be numeric.") from exc
    if not math.isfinite(number):
        raise InputValidationError(f"{label} must be finite.")
    return number


def _positive(value: Any, label: str) -> float:
    number = _finite(value, label)
    if number <= 0.0:
        raise InputValidationError(f"{label} must be strictly positive.")
    return number


def _nonnegative(value: Any, label: str) -> float:
    number = _finite(value, label)
    if number < 0.0:
        raise InputValidationError(f"{label} must be non-negative.")
    return number


def _path(root: Path, value: Any, label: str) -> Path:
    path = Path(_text(value, label))
    return (root / path).resolve() if not path.is_absolute() else path.resolve()


def _string_map(value: Any, label: str, *, required: tuple[str, ...]) -> dict[str, str]:
    data = _object(value, label)
    missing = [key for key in required if key not in data]
    if missing:
        raise InputValidationError(f"{label} misses required fields {missing}.")
    return {str(key): _text(item, f"{label}.{key}") for key, item in data.items()}


def _numeric_map(value: Any, label: str) -> dict[str, int | float]:
    data = _object(value, label)
    records: dict[str, int | float] = {}
    for key, raw in data.items():
        number = _nonnegative(raw, f"{label}.{key}")
        records[str(key)] = int(number) if number.is_integer() else number
    return records


def _reject_unknown(data: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise InputValidationError(f"{label} contains unsupported fields {unknown}.")
