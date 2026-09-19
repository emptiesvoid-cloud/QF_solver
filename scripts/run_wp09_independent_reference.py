"""Compare the WP09 production kernel with an independent NumPy reference.

The reference module is deliberately imported separately from production
elements/materials.  This harness is a material-point and affine-element
cross-check; it is not an independent global FEM/Newton solve.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from solveur.elements.solid.corotational_j2 import (  # noqa: E402
    CorotationalJ2Hex8Element,
    CorotationalJ2Tet4Element,
)
from solveur.materials.solid import VonMisesElastoplasticMaterial  # noqa: E402
from solveur.verification import wp09_independent_reference as reference  # noqa: E402


FAMILIES = ("TET4", "HEX8")
LOAD_FACTORS = (0.0, 0.25, 0.5, 0.75, 1.0)
YOUNG = 1_000.0
POISSON = 0.3
YIELD = 2.0
HARDENING = 20.0
LOCAL_STRAIN_LIMIT = 0.05
DEFAULT_ROTATION_DEG = 50.0
PASS_TOLERANCE = 1.0e-11


def _rotation(angle: float) -> np.ndarray:
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return np.asarray(
        [[cosine, -sine, 0.0], [sine, cosine, 0.0], [0.0, 0.0, 1.0]],
        dtype=float,
    )


def _deformation_at_factor(factor: float, rotation_deg: float) -> np.ndarray:
    rotation = _rotation(math.radians(rotation_deg) * factor)
    stretch = np.diag([1.0 + 0.008 * factor, 1.0 - 0.004 * factor, 1.0])
    return rotation @ stretch


def _coords(family: str) -> np.ndarray:
    if family == "TET4":
        return np.asarray(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            dtype=float,
        )
    return np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
        ],
        dtype=float,
    )


def _relative_error(left: np.ndarray | float, right: np.ndarray | float) -> float:
    left_array = np.asarray(left, dtype=float)
    right_array = np.asarray(right, dtype=float)
    scale = np.maximum(np.abs(left_array), np.abs(right_array))
    meaningful = scale > 1.0e-8
    if not np.any(meaningful):
        return 0.0
    return float(np.max(np.abs(left_array[meaningful] - right_array[meaningful]) / scale[meaningful]))


def _absolute_error(left: np.ndarray | float, right: np.ndarray | float) -> float:
    return float(np.max(np.abs(np.asarray(left, dtype=float) - np.asarray(right, dtype=float))))


def _json_value(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def _production_history(family: str, rotation_deg: float) -> list[dict[str, Any]]:
    coordinates = _coords(family)
    material = VonMisesElastoplasticMaterial(
        E=YOUNG,
        nu=POISSON,
        yield_stress=YIELD,
        hardening_modulus=HARDENING,
    )
    element_class = CorotationalJ2Tet4Element if family == "TET4" else CorotationalJ2Hex8Element
    element = element_class(material, max_corotational_strain=LOCAL_STRAIN_LIMIT)
    committed: list[dict[str, Any]] | None = None
    rows: list[dict[str, Any]] = []
    for factor in LOAD_FACTORS:
        deformation = _deformation_at_factor(factor, rotation_deg)
        displacement = ((deformation - np.eye(3)) @ coordinates.T).T.ravel()
        points = element.integration_point_results(coordinates, displacement, committed)
        _, _, trial = element.internal_force_tangent_state(coordinates, displacement, committed)
        committed = deepcopy(trial)
        rows.append(
            {
                "factor": factor,
                "deformation_gradient": deformation,
                "points": points,
                "trial_states": committed,
            }
        )
    return rows


def _reference_history(rotation_deg: float) -> list[dict[str, Any]]:
    deformations = [_deformation_at_factor(factor, rotation_deg) for factor in LOAD_FACTORS]
    return reference.evaluate_corotational_history(
        deformations,
        young=YOUNG,
        poisson=POISSON,
        yield_stress=YIELD,
        hardening_modulus=HARDENING,
        max_strain_norm=LOCAL_STRAIN_LIMIT,
    )


def _compare_family(family: str, rotation_deg: float) -> dict[str, Any]:
    production = _production_history(family, rotation_deg)
    independent = _reference_history(rotation_deg)
    rows: list[dict[str, Any]] = []
    maxima = {
        "deformation_gradient": 0.0,
        "rotation": 0.0,
        "stretch": 0.0,
        "local_strain": 0.0,
        "local_stress": 0.0,
        "cauchy_stress": 0.0,
        "equivalent_plastic_strain": 0.0,
        "yield_function": 0.0,
        "plastic_dissipation": 0.0,
    }
    absolute_maxima = {name: 0.0 for name in maxima}
    for production_row, reference_row in zip(production, independent, strict=True):
        points = production_row["points"]
        states = production_row["trial_states"]
        production_arrays = {
            "deformation_gradient": np.asarray(production_row["deformation_gradient"]),
            "rotation": np.mean([np.asarray(point["corotation"]) for point in points], axis=0),
            "stretch": np.mean([np.asarray(point["right_stretch"]) for point in points], axis=0),
            "local_strain": np.mean([np.asarray(point["corotational_strain"]) for point in points], axis=0),
            "local_stress": np.mean([np.asarray(point["local_stress"]) for point in points], axis=0),
            "cauchy_stress": np.mean([np.asarray(point["cauchy_stress"]) for point in points], axis=0),
            "equivalent_plastic_strain": np.mean(
                [float(state["equivalent_plastic_strain"]) for state in states]
            ),
            "yield_function": np.mean([float(state["yield_function"]) for state in states]),
            "plastic_dissipation": np.mean([float(state["plastic_dissipation"]) for state in states]),
        }
        reference_arrays = {
            "deformation_gradient": np.asarray(reference_row["deformation_gradient"]),
            "rotation": np.asarray(reference_row["rotation"]),
            "stretch": np.asarray(reference_row["stretch"]),
            "local_strain": np.asarray(reference_row["local_strain"]),
            "local_stress": np.asarray(reference_row["local_stress"]),
            "cauchy_stress": np.asarray(reference_row["cauchy_stress"]),
            "equivalent_plastic_strain": float(reference_row["equivalent_plastic_strain"]),
            "yield_function": float(reference_row["yield_function"]),
            "plastic_dissipation": float(reference_row["plastic_dissipation"]),
        }
        errors = {
            name: _relative_error(production_arrays[name], reference_arrays[name])
            for name in maxima
        }
        absolute_errors = {
            name: _absolute_error(production_arrays[name], reference_arrays[name])
            for name in maxima
        }
        for name, error in errors.items():
            maxima[name] = max(maxima[name], error)
            absolute_maxima[name] = max(absolute_maxima[name], absolute_errors[name])
        rows.append(
            {
                "factor": production_row["factor"],
                "errors": errors,
                "absolute_errors": absolute_errors,
                "production": _json_value(production_arrays),
                "independent_reference": _json_value(reference_arrays),
            }
        )
    return {
        "family": family,
        "rows": rows,
        "max_relative_errors": maxima,
        "max_absolute_errors": absolute_maxima,
        "status": (
            "PASS"
            if max(maxima.values()) <= PASS_TOLERANCE and max(absolute_maxima.values()) <= 1.0e-10
            else "FAIL"
        ),
    }


def _git_value(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "UNAVAILABLE"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rotation-deg", type=float, default=DEFAULT_ROTATION_DEG)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    output = (
        args.output
        or ROOT / "qualification" / "0_2_9" / "wp09_independent_reference"
    ).resolve()
    output.mkdir(parents=True, exist_ok=True)
    source_path = ROOT / "src" / "solveur" / "verification" / "wp09_independent_reference.py"
    source_text = source_path.read_text(encoding="utf-8")
    independence_status = (
        "PASS"
        if "solveur.elements" not in source_text
        and "solveur.materials" not in source_text
        and "solveur.core" not in source_text
        else "FAIL"
    )
    family_results = [_compare_family(family, args.rotation_deg) for family in FAMILIES]
    summary: dict[str, Any] = {
        "status": (
            "PASS_INDEPENDENT_REFERENCE"
            if independence_status == "PASS" and all(row["status"] == "PASS" for row in family_results)
            else "FAIL_INDEPENDENT_REFERENCE"
        ),
        "classification": "BOUNDED_MATERIAL_POINT_AND_AFFINE_ELEMENT_REFERENCE_NOT_GLOBAL_FEM_SOLVE",
        "governing_branch": _git_value("branch", "--show-current"),
        "execution_sha": _git_value("rev-parse", "HEAD"),
        "working_tree": _git_value("status", "--short"),
        "independent_reference_module_sha256": _sha256(source_path),
        "independence_source_check": independence_status,
        "rotation_deg": args.rotation_deg,
        "load_factors": list(LOAD_FACTORS),
        "material": {
            "young": YOUNG,
            "poisson": POISSON,
            "yield_stress": YIELD,
            "hardening_modulus": HARDENING,
        },
        "families": family_results,
        "formal_qualification": {
            "authorized": False,
            "wp09_points": "0/8",
            "production_mechanics_changed": False,
        },
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report = [
        "# WP09 independent NumPy reference",
        "",
        f"Status: `{summary['status']}`",
        "",
        "This is an independent material-point/affine-element recomputation. "
        "It is not an independent global FEM/Newton solve.",
        "",
        f"Execution SHA: `{summary['execution_sha']}`",
        f"Reference module SHA-256: `{summary['independent_reference_module_sha256']}`",
        f"Rotation path: `{args.rotation_deg}` degrees",
        "",
        "| Family | Status | Max relative error |",
        "|---|---|---:|",
    ]
    for result in family_results:
        report.append(
            f"| {result['family']} | {result['status']} | "
            f"{max(result['max_relative_errors'].values()):.3e} |"
        )
    report.extend(
        [
            "",
            "Formal WP09 points remain `0/8`; no merge or push was performed.",
        ]
    )
    (output / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": summary["status"],
                "execution_sha": summary["execution_sha"],
                "families": [
                    {
                        "family": row["family"],
                        "status": row["status"],
                        "max_relative_errors": row["max_relative_errors"],
                        "max_absolute_errors": row["max_absolute_errors"],
                    }
                    for row in family_results
                ],
            },
            indent=2,
        )
    )
    return 0 if summary["status"] == "PASS_INDEPENDENT_REFERENCE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
