"""Validation rules specific to shell-laminate ply definitions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from solveur.io.schema_values import is_number, reject_unknown, require_fields


def validate_laminate_plies(path: str, value: Any, errors: list[str]) -> None:
    if not isinstance(value, list) or not value:
        errors.append(f"{path}.plies must be a non-empty list.")
        return
    allowed = {
        "name",
        "E1",
        "E2",
        "nu12",
        "G12",
        "G13",
        "G23",
        "density",
        "rho",
        "thickness",
        "angle_deg",
        "strengths",
        "strain_allowables",
    }
    required = ("E1", "E2", "nu12", "G12", "G13", "G23", "thickness")
    for index, ply in enumerate(value):
        ply_path = f"{path}.plies[{index}]"
        if not isinstance(ply, Mapping):
            errors.append(f"{ply_path} must be an object.")
            continue
        reject_unknown(ply_path, ply, allowed, errors)
        require_fields(ply_path, ply, required, errors)
        if "name" in ply and (not isinstance(ply["name"], str) or not ply["name"]):
            errors.append(f"{ply_path}.name must be a non-empty string.")
        for field in allowed - {"name", "strengths", "strain_allowables"}:
            if field in ply and not is_number(ply[field]):
                errors.append(f"{ply_path}.{field} must be a finite number.")
        if "strengths" in ply:
            _validate_ply_strengths(f"{ply_path}.strengths", ply["strengths"], errors)
        if "strain_allowables" in ply:
            _validate_ply_strain_allowables(
                f"{ply_path}.strain_allowables",
                ply["strain_allowables"],
                errors,
            )
        for field in ("E1", "E2", "G12", "G13", "G23", "thickness"):
            if field in ply and is_number(ply[field]) and float(ply[field]) <= 0.0:
                errors.append(f"{ply_path}.{field} must be positive.")
        for field in ("density", "rho"):
            if field in ply and is_number(ply[field]) and float(ply[field]) < 0.0:
                errors.append(f"{ply_path}.{field} must be non-negative.")
        if all(field in ply and is_number(ply[field]) for field in ("E1", "E2", "nu12")):
            e1 = float(ply["E1"])
            e2 = float(ply["E2"])
            nu12 = float(ply["nu12"])
            if e1 > 0.0 and e2 > 0.0 and 1.0 - nu12 * nu12 * e2 / e1 <= 0.0:
                errors.append(f"{ply_path} must satisfy 1 - nu12 * nu21 > 0.")


def _validate_ply_strengths(path: str, value: Any, errors: list[str]) -> None:
    required = {"Xt", "Xc", "Yt", "Yc", "S12"}
    allowed = required | {"f12_star"}
    if not isinstance(value, Mapping):
        errors.append(f"{path} must be an object.")
        return
    reject_unknown(path, value, allowed, errors)
    require_fields(path, value, tuple(sorted(required)), errors)
    for field in allowed:
        if field in value and not is_number(value[field]):
            errors.append(f"{path}.{field} must be a finite number.")
    for field in required:
        if field in value and is_number(value[field]) and float(value[field]) <= 0.0:
            errors.append(f"{path}.{field} must be positive.")
    if "f12_star" in value and is_number(value["f12_star"]):
        coefficient = float(value["f12_star"])
        if not -1.0 < coefficient < 1.0:
            errors.append(f"{path}.f12_star must lie strictly between -1 and 1.")


def _validate_ply_strain_allowables(path: str, value: Any, errors: list[str]) -> None:
    required = {"e1t", "e1c", "e2t", "e2c", "g12"}
    if not isinstance(value, Mapping):
        errors.append(f"{path} must be an object.")
        return
    reject_unknown(path, value, required, errors)
    require_fields(path, value, tuple(sorted(required)), errors)
    for field in required:
        if field in value and not is_number(value[field]):
            errors.append(f"{path}.{field} must be a finite number.")
        elif field in value and float(value[field]) <= 0.0:
            errors.append(f"{path}.{field} must be positive.")
