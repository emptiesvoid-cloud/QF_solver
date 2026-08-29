"""Shared corpus and opt-in controls for the TL robustness R&D runner."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PERSISTENT_IDS = {
    "HEX8_m4_a7_compression_l0.2_n16_d0.12",
    "HEX8_m4_a10_compression_l0.2_n16_d0.12",
    "HEX8_m4_a10_compression_l0.2_n8_d0.12",
    "HEX8_m4_a10_compression_l0.2_n32_d0.12",
}


class LightRecordingAssembly:
    """Record solver-call metadata without retaining every sparse tangent."""

    def __init__(self, assembly: Any) -> None:
        self.assembly = assembly
        self.ndof = assembly.ndof
        self.calls: list[dict[str, Any]] = []
        self.last_successful_displacement: np.ndarray | None = None
        self._previous_displacement: np.ndarray | None = None

    def assemble(
        self, displacement: np.ndarray, *, tangent_required: bool = True
    ) -> tuple[np.ndarray, Any]:
        values = np.asarray(displacement, dtype=float).copy()
        call: dict[str, Any] = {
            "displacement_norm": float(np.linalg.norm(values)),
            "displacement_max": float(np.max(np.abs(values))) if values.size else 0.0,
            "displacement_sha256": hashlib.sha256(values.tobytes()).hexdigest(),
            "tangent_required": tangent_required,
            "status": "EXCEPTION",
        }
        if self._previous_displacement is not None:
            call["displacement_increment_norm"] = float(
                np.linalg.norm(values - self._previous_displacement)
            )
        else:
            call["displacement_increment_norm"] = None
        try:
            internal, tangent = self.assembly.assemble(values, tangent_required=tangent_required)
        except Exception as exc:
            call.update({"exception_type": type(exc).__name__, "exception": str(exc)})
            self.calls.append(call)
            self._previous_displacement = values
            raise
        call.update(
            {
                "status": "SUCCESS",
                "internal_force_norm": float(np.linalg.norm(internal)),
                "tangent_nnz": int(tangent.nnz) if tangent is not None else 0,
            }
        )
        self.calls.append(call)
        self._previous_displacement = values
        self.last_successful_displacement = values.copy()
        return internal, tangent


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def git_dirty() -> bool:
    return bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())


def _case(
    family: str,
    aspect: float,
    mode: str,
    increments: int = 16,
    *,
    case_group: str,
) -> dict[str, Any]:
    return {
        "id": f"{family}_m4_a{aspect:g}_{mode}_l0.2_n{increments}_d0.12",
        "family": family,
        "cells": 4,
        "mesh_level": 4,
        "aspect": aspect,
        "mode": mode,
        "load_scale": 0.2,
        "increments": increments,
        "distortion": 0.12,
        "angle": 0.0,
        "group": case_group,
    }


def experiment_cases() -> list[dict[str, Any]]:
    return [
        _case("HEX8", 7.0, "compression", case_group="persistent_failure"),
        _case("HEX8", 10.0, "compression", case_group="persistent_failure"),
        _case("HEX8", 10.0, "compression", 8, case_group="persistent_failure"),
        _case("HEX8", 10.0, "compression", 32, case_group="persistent_failure"),
        _case("TET4", 6.0, "compression", case_group="stable_reference"),
        _case("HEX8", 6.0, "compression", case_group="stable_reference"),
        _case("TET4", 10.0, "compression", case_group="degraded_reference"),
        _case("HEX8", 10.0, "bending_z", case_group="degraded_reference"),
    ]


MECHANISMS: dict[str, dict[str, Any]] = {
    "baseline": {"description": "Existing default path; no experimental controls."},
    "system_scaling": {
        "description": "Symmetric diagonal equation scaling.",
        "parameters": {"experimental_system_scaling": "symmetric_diagonal"},
    },
    "residual_row_scaling": {
        "description": "Row-maximum scaling of the Newton linear equations.",
        "parameters": {"experimental_residual_scaling": "row_max"},
    },
    "splu_colamd": {
        "description": "SciPy sparse LU with COLAMD ordering.",
        "parameters": {
            "experimental_linear_solver": "splu",
            "experimental_linear_permutation": "COLAMD",
        },
    },
    "splu_natural": {
        "description": "SciPy sparse LU with NATURAL ordering.",
        "parameters": {
            "experimental_linear_solver": "splu",
            "experimental_linear_permutation": "NATURAL",
        },
    },
    "line_search_off": {
        "description": "Negative-control experiment with the existing line search disabled.",
        "parameters": {"experimental_line_search": "off"},
    },
    "line_search_armijo": {
        "description": "Armijo line search using the existing assembly contract.",
        "parameters": {
            "experimental_line_search": "armijo",
            "experimental_line_search_min_alpha": 1.0e-6,
            "experimental_line_search_max_reductions": 20,
            "experimental_line_search_c": 1.0e-4,
        },
    },
    "adaptive_cutback": {
        "description": "Existing adaptive driver with a more conservative opt-in retry policy.",
        "adaptive_parameters": {
            "min_load_increment": 1.0e-4,
            "cutback_factor": 0.25,
            "growth_factor": 1.0,
            "max_cutbacks": 8,
        },
    },
    "adaptive_growth": {
        "description": "Existing adaptive driver with measured growth after easy increments.",
        "adaptive_parameters": {
            "min_load_increment": 1.0e-4,
            "max_load_increment": 1.0,
            "cutback_factor": 0.5,
            "growth_factor": 1.5,
            "grow_below_iterations": 25,
            "shrink_above_iterations": 50,
            "max_cutbacks": 25,
        },
    },
}
