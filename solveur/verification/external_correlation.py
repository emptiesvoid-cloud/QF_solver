"""Controlled comparisons with externally published solver results."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ABAQUS_REFERENCE = (
    PROJECT_ROOT / "qualification" / "vnv" / "references" / "abaqus_mitc4_static.json"
)
DEFAULT_NAFEMS_13H_REFERENCE = (
    PROJECT_ROOT
    / "qualification"
    / "vnv"
    / "references"
    / "abaqus_nafems_13h_harmonic.json"
)


class ExternalReferenceError(ValueError):
    """Report an invalid or incomplete external reference record."""


def load_abaqus_mitc4_static_reference(path: str | Path | None = None) -> dict[str, Any]:
    """Load and validate the controlled Abaqus MITC4 static reference."""
    source = Path(path) if path is not None else DEFAULT_ABAQUS_REFERENCE
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExternalReferenceError(f"cannot read external reference {source}: {exc}") from exc
    _validate_reference(data)
    return data


def compare_pinched_cylinder(
    qf_run: dict[str, Any],
    reference: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare the finest QF_solver response with published Abaqus S4R data."""
    external = reference or load_abaqus_mitc4_static_reference()
    points = qf_run.get("points")
    if not isinstance(points, list) or not points:
        raise ExternalReferenceError("QF_solver pinched-cylinder run has no convergence points")
    qf_finest = points[-1]
    abaqus_finest = external["regular_mesh_results"][-1]
    qf_value = _positive_float(qf_finest.get("value"), "QF_solver finest displacement")
    abaqus_value = _positive_float(abaqus_finest.get("displacement"), "Abaqus displacement")
    limit = _positive_float(
        external["comparison_policy"].get("relative_difference_limit"),
        "comparison limit",
    )
    difference = abs(qf_value - abaqus_value) / abaqus_value
    return {
        "status": "PASS" if difference <= limit else "FAIL",
        "evidence_level": "published_vendor_result",
        "comparison_type": external["comparison_policy"]["type"],
        "reference_id": external["reference_id"],
        "source": external["source"],
        "reference_displacement": external["case"]["reference_displacement"],
        "qf_solver": {
            "mesh": qf_finest["mesh"],
            "element_count": qf_finest["element_count"],
            "displacement": qf_value,
        },
        "abaqus_s4r": {
            "mesh": abaqus_finest["mesh"],
            "dofs": abaqus_finest["dofs"],
            "displacement": abaqus_value,
        },
        "relative_difference": difference,
        "relative_difference_limit": limit,
        "published_convergence": external["regular_mesh_results"],
        "limitations": external["comparison_policy"]["limitations"],
    }


def load_abaqus_nafems_13h_reference(path: str | Path | None = None) -> dict[str, Any]:
    """Load the controlled Abaqus/NAFEMS harmonic plate reference."""
    source = Path(path) if path is not None else DEFAULT_NAFEMS_13H_REFERENCE
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExternalReferenceError(f"cannot read external reference {source}: {exc}") from exc
    _validate_harmonic_reference(data)
    return data


def compare_nafems_13h(
    qf_run: dict[str, Any],
    reference: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare QF_solver peak displacement/frequency to NAFEMS and Abaqus S4R."""
    external = reference or load_abaqus_nafems_13h_reference()
    qf_displacement = _positive_float(qf_run.get("peak_displacement_mm"), "QF peak displacement")
    qf_frequency = _positive_float(qf_run.get("peak_frequency_hz"), "QF peak frequency")
    qf_stress = _positive_float(qf_run.get("peak_stress_n_mm2"), "QF peak stress")
    residual = _nonnegative_float(qf_run.get("max_relative_residual"), "QF relative residual")
    abaqus = next(row for row in external["abaqus_direct_results"] if row["element"] == "S4R")
    abaqus_s4 = next(row for row in external["abaqus_direct_results"] if row["element"] == "S4")
    nafems = external["nafems_reference"]
    policy = external["comparison_policy"]
    differences = {
        "abaqus_displacement": _relative_difference(qf_displacement, abaqus["peak_displacement_mm"]),
        "abaqus_frequency": _relative_difference(qf_frequency, abaqus["peak_frequency_hz"]),
        "abaqus_stress": _relative_difference(qf_stress, abaqus["peak_stress_n_mm2"]),
        "abaqus_s4_displacement": _relative_difference(
            qf_displacement,
            abaqus_s4["peak_displacement_mm"],
        ),
        "abaqus_s4_frequency": _relative_difference(qf_frequency, abaqus_s4["peak_frequency_hz"]),
        "abaqus_s4_stress": _relative_difference(qf_stress, abaqus_s4["peak_stress_n_mm2"]),
        "nafems_displacement": _relative_difference(qf_displacement, nafems["peak_displacement_mm"]),
        "nafems_frequency": _relative_difference(qf_frequency, nafems["peak_frequency_hz"]),
        "nafems_stress": _relative_difference(qf_stress, nafems["peak_stress_n_mm2"]),
    }
    checks = {
        "abaqus_peak_displacement": differences["abaqus_displacement"]
        <= float(policy["qf_to_abaqus_displacement_relative_limit"]),
        "abaqus_peak_frequency": differences["abaqus_frequency"]
        <= float(policy["qf_to_abaqus_frequency_relative_limit"]),
        "abaqus_peak_stress": differences["abaqus_stress"]
        <= float(policy["qf_to_abaqus_stress_relative_limit"]),
        "abaqus_s4_peak_displacement": differences["abaqus_s4_displacement"]
        <= float(policy["qf_to_abaqus_displacement_relative_limit"]),
        "abaqus_s4_peak_frequency": differences["abaqus_s4_frequency"]
        <= float(policy["qf_to_abaqus_frequency_relative_limit"]),
        "abaqus_s4_peak_stress": differences["abaqus_s4_stress"]
        <= float(policy["qf_to_abaqus_stress_relative_limit"]),
        "nafems_peak_displacement": differences["nafems_displacement"]
        <= float(policy["qf_to_nafems_displacement_relative_limit"]),
        "nafems_peak_frequency": differences["nafems_frequency"]
        <= float(policy["qf_to_nafems_frequency_relative_limit"]),
        "nafems_peak_stress": differences["nafems_stress"]
        <= float(policy["qf_to_nafems_stress_relative_limit"]),
        "harmonic_residual": residual <= float(policy["relative_residual_limit"]),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "evidence_level": "published_vendor_and_nafems_result",
        "comparison_type": policy["type"],
        "reference_id": external["reference_id"],
        "source": external["source"],
        "qf_solver": {
            "peak_displacement_mm": qf_displacement,
            "peak_frequency_hz": qf_frequency,
            "peak_stress_n_mm2": qf_stress,
            "max_relative_residual": residual,
        },
        "abaqus_s4r": abaqus,
        "abaqus_s4": abaqus_s4,
        "nafems": nafems,
        "relative_differences": differences,
        "checks": checks,
        "limitations": policy["limitations"],
    }


def _validate_reference(data: object) -> None:
    if not isinstance(data, dict):
        raise ExternalReferenceError("external reference root must be an object")
    for key in ("reference_id", "publisher", "source", "case", "regular_mesh_results", "comparison_policy"):
        if key not in data:
            raise ExternalReferenceError(f"external reference is missing '{key}'")
    source = data["source"]
    if not isinstance(source, dict) or not str(source.get("url", "")).startswith("https://"):
        raise ExternalReferenceError("external reference must provide an HTTPS source URL")
    rows = data["regular_mesh_results"]
    if not isinstance(rows, list) or len(rows) < 2:
        raise ExternalReferenceError("external reference needs at least two convergence rows")
    reference = _positive_float(data["case"].get("reference_displacement"), "reference displacement")
    previous_dofs = -1
    for row in rows:
        if not isinstance(row, dict):
            raise ExternalReferenceError("external convergence row must be an object")
        dofs = int(row.get("dofs", -1))
        displacement = _positive_float(row.get("displacement"), "Abaqus displacement")
        reported_error = row.get("reported_error_percent")
        if not isinstance(reported_error, (int, float)) or isinstance(reported_error, bool):
            raise ExternalReferenceError("Abaqus reported error must be numeric")
        calculated_error = 100.0 * (displacement - reference) / reference
        if abs(calculated_error - float(reported_error)) > 0.15:
            raise ExternalReferenceError("Abaqus displacement and reported error are inconsistent")
        if dofs <= previous_dofs:
            raise ExternalReferenceError("Abaqus convergence rows must have increasing dof counts")
        previous_dofs = dofs


def _validate_harmonic_reference(data: object) -> None:
    if not isinstance(data, dict):
        raise ExternalReferenceError("harmonic external reference root must be an object")
    for key in (
        "reference_id",
        "publisher",
        "source",
        "model",
        "nafems_reference",
        "abaqus_direct_results",
        "comparison_policy",
    ):
        if key not in data:
            raise ExternalReferenceError(f"harmonic external reference is missing '{key}'")
    source = data["source"]
    if not isinstance(source, dict) or not str(source.get("url", "")).startswith("https://"):
        raise ExternalReferenceError("harmonic external reference must provide an HTTPS source URL")
    rows = data["abaqus_direct_results"]
    if not isinstance(rows, list) or {row.get("element") for row in rows if isinstance(row, dict)} != {"S4", "S4R"}:
        raise ExternalReferenceError("harmonic external reference must contain S4 and S4R direct results")
    for row in [data["nafems_reference"], *rows]:
        if not isinstance(row, dict):
            raise ExternalReferenceError("harmonic reference result must be an object")
        _positive_float(row.get("peak_displacement_mm"), "harmonic peak displacement")
        _positive_float(row.get("peak_frequency_hz"), "harmonic peak frequency")
    sweep = data["model"].get("frequency_sweep_hz", {})
    if int(sweep.get("count", 0)) < 2:
        raise ExternalReferenceError("harmonic reference frequency sweep must contain at least two points")


def _relative_difference(first: object, second: object) -> float:
    reference = _positive_float(second, "external comparison reference")
    return abs(float(first) - reference) / reference


def _positive_float(value: object, label: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or float(value) <= 0.0
    ):
        raise ExternalReferenceError(f"{label} must be a positive number")
    return float(value)


def _nonnegative_float(value: object, label: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or float(value) < 0.0
    ):
        raise ExternalReferenceError(f"{label} must be a non-negative number")
    return float(value)
