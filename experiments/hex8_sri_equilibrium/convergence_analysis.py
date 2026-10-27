"""Pure post-processing for paired HEX8-SRI convergence evidence.

This module reads archived sidecar data only. It does not assemble matrices,
invoke a solver, or compute eigenvalues. Self-convergence indicators are
diagnostics; they are not a substitute for a qualified independent oracle.
"""

from __future__ import annotations

import csv
import hashlib
from html import escape
import json
import math
from pathlib import Path
from typing import Any, Iterable

from .campaign_spec import FORMULATIONS, MESH_LEVELS, POISSON_RATIOS


EXPECTED_UNITS = {
    "displacement": "m",
    "strain": "dimensionless",
    "energy": "J",
    "force": "N",
    "moment": "N·m",
    "time": "s",
}
OBSERVABLE_FIELDS = {
    "signed_mean_loaded_face_UZ_m": "m",
    "internal_energy_J": "J",
    "external_load_work_J": "J",
    "free_residual_l2_N": "N",
    "free_residual_relative": "dimensionless",
    "force_closure_relative": "dimensionless",
    "moment_closure_relative": "dimensionless",
    "condition_number_1_estimate_Kff": "dimensionless",
}
CSV_FIELDS = (
    "formulation",
    "poisson_ratio",
    "divisions_xyz",
    "element_count",
    "node_count",
    "dof_count",
    "signed_mean_loaded_face_UZ_m",
    "internal_energy_J",
    "external_load_work_J",
    "free_residual_l2_N",
    "free_residual_relative",
    "support_reaction_resultant_N",
    "force_closure_N",
    "force_closure_relative",
    "moment_closure_Nm",
    "moment_closure_relative",
    "condition_number_1_estimate_Kff",
    "relative_change_UZ_from_previous_level",
    "relative_change_energy_from_previous_level",
    "UZ_increment_from_previous_level_m",
    "energy_increment_from_previous_level_J",
    "UZ_self_convergence_indicator_order",
    "energy_self_convergence_indicator_order",
    "independent_reference_status",
    "UZ_relative_error_to_qualified_reference",
    "energy_relative_error_to_qualified_reference",
    "campaign_verdict",
)


def sha256_file(path: Path) -> str:
    """Hash one evidence file without modifying it."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_sidecar(path: Path, *, expected_sha256: str | None = None) -> dict[str, Any]:
    """Load one sidecar and optionally verify its externally recorded SHA-256."""
    path = Path(path)
    if expected_sha256 is not None and sha256_file(path) != expected_sha256:
        raise ValueError(f"INTEGRITY_MISMATCH: sidecar SHA-256 differs: {path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != "qfsolver-hex8-sri-convergence-sidecar-v1":
        raise ValueError(f"unsupported convergence sidecar schema: {path.name}")
    return value


def _case_key(record: dict[str, Any]) -> tuple[str, float, tuple[int, int, int]]:
    case = record.get("case", {})
    formulation = case.get("formulation")
    poisson_ratio = float(case.get("poisson_ratio", float("nan")))
    mesh_values = case.get("divisions_xyz")
    if formulation not in FORMULATIONS or poisson_ratio not in POISSON_RATIOS:
        raise ValueError("sidecar has an unregistered formulation or Poisson ratio")
    if not isinstance(mesh_values, list) or len(mesh_values) != 3:
        raise ValueError("sidecar mesh must contain three division counts")
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in mesh_values):
        raise ValueError("sidecar mesh divisions must be positive integers")
    mesh = tuple(int(value) for value in mesh_values)
    if mesh not in MESH_LEVELS:
        raise ValueError(f"sidecar uses an unregistered mesh: {mesh}")
    return formulation, poisson_ratio, mesh


def _require_finite_observables(record: dict[str, Any]) -> None:
    units = record.get("units", {})
    for name, expected_unit in EXPECTED_UNITS.items():
        if units.get(name) != expected_unit:
            raise ValueError(f"sidecar unit mismatch for {name}: {units.get(name)!r}")
    observables = record.get("observables", {})
    for name in OBSERVABLE_FIELDS:
        value = observables.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"sidecar observable {name} is missing or non-finite")


def _self_convergence_order(values: list[float]) -> float | None:
    """Return a three-level increment-ratio indicator for nested 2x meshes."""
    if len(values) < 3:
        return None
    coarse_increment = abs(values[-2] - values[-3])
    fine_increment = abs(values[-1] - values[-2])
    if coarse_increment <= 0.0 or fine_increment <= 0.0:
        return None
    return math.log(coarse_increment / fine_increment, 2.0)


def _relative_change(current: float, previous: float) -> float | None:
    scale = max(abs(current), abs(previous))
    if scale == 0.0:
        return 0.0
    return abs(current - previous) / scale


def analyze_sidecars(
    sidecars: Iterable[dict[str, Any]],
    *,
    qualified_references: dict[float, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Normalize evidence and compute paired-level differences.

    ``qualified_references`` may map nu to a record containing ``qualified``
    and finite ``signed_mean_loaded_face_UZ_m`` / ``internal_energy_J`` values.
    Errors are emitted only for an explicitly qualified reference with a
    positive uncertainty no greater than 0.5 percent for both observables.
    """
    references = qualified_references or {}
    by_key: dict[tuple[str, float, tuple[int, int, int]], dict[str, Any]] = {}
    for record in sidecars:
        key = _case_key(record)
        _require_finite_observables(record)
        if key in by_key:
            raise ValueError(f"duplicate convergence evidence for case {key}")
        by_key[key] = record

    groups: dict[tuple[str, float], list[tuple[tuple[int, int, int], dict[str, Any]]]] = {}
    for (formulation, nu, mesh), record in by_key.items():
        groups.setdefault((formulation, nu), []).append((mesh, record))

    output: list[dict[str, Any]] = []
    for (formulation, nu), entries in sorted(groups.items()):
        entries.sort(key=lambda item: MESH_LEVELS.index(item[0]))
        uz_values = [float(item[1]["observables"]["signed_mean_loaded_face_UZ_m"]) for item in entries]
        energy_values = [float(item[1]["observables"]["internal_energy_J"]) for item in entries]
        uz_order = _self_convergence_order(uz_values)
        energy_order = _self_convergence_order(energy_values)
        reference = references.get(nu, {})
        reference_ok = (
            reference.get("qualified") is True
            and math.isfinite(float(reference.get("relative_uncertainty_uz", float("inf"))))
            and math.isfinite(float(reference.get("relative_uncertainty_energy", float("inf"))))
            and 0.0 <= float(reference.get("relative_uncertainty_uz", float("inf")))
            and float(reference.get("relative_uncertainty_uz", float("inf"))) <= 0.005
            and 0.0 <= float(reference.get("relative_uncertainty_energy", float("inf")))
            and float(reference.get("relative_uncertainty_energy", float("inf"))) <= 0.005
        )
        ref_uz = float(reference["signed_mean_loaded_face_UZ_m"]) if reference_ok else None
        ref_energy = float(reference["internal_energy_J"]) if reference_ok else None
        if reference_ok and (
            not math.isfinite(ref_uz) or not math.isfinite(ref_energy) or ref_energy <= 0.0 or ref_uz == 0.0
        ):
            raise ValueError(f"qualified reference values are invalid for nu={nu}")

        for index, (mesh, record) in enumerate(entries):
            case = record["case"]
            obs = record["observables"]
            previous = entries[index - 1][1]["observables"] if index else None
            uz = float(obs["signed_mean_loaded_face_UZ_m"])
            energy = float(obs["internal_energy_J"])
            verdicts = record.get("criteria_verdicts", {})
            output.append(
                {
                    "formulation": formulation,
                    "poisson_ratio": nu,
                    "divisions_xyz": "x".join(str(value) for value in mesh),
                    "element_count": int(case["element_count"]),
                    "node_count": int(case["node_count"]),
                    "dof_count": int(case["dof_count"]),
                    "signed_mean_loaded_face_UZ_m": uz,
                    "internal_energy_J": energy,
                    "external_load_work_J": float(obs["external_load_work_J"]),
                    "free_residual_l2_N": float(obs["free_residual_l2_N"]),
                    "free_residual_relative": float(obs["free_residual_relative"]),
                    "support_reaction_resultant_N": json.dumps(
                        obs.get("support_reaction_resultant_N"), separators=(",", ":")
                    ),
                    "force_closure_N": json.dumps(obs.get("force_closure_N"), separators=(",", ":")),
                    "force_closure_relative": float(obs["force_closure_relative"]),
                    "moment_closure_Nm": json.dumps(obs.get("moment_closure_Nm"), separators=(",", ":")),
                    "moment_closure_relative": float(obs["moment_closure_relative"]),
                    "condition_number_1_estimate_Kff": float(obs["condition_number_1_estimate_Kff"]),
                    "relative_change_UZ_from_previous_level": (
                        _relative_change(uz, float(previous["signed_mean_loaded_face_UZ_m"])) if previous else None
                    ),
                    "relative_change_energy_from_previous_level": (
                        _relative_change(energy, float(previous["internal_energy_J"])) if previous else None
                    ),
                    "UZ_increment_from_previous_level_m": (
                        uz - float(previous["signed_mean_loaded_face_UZ_m"]) if previous else None
                    ),
                    "energy_increment_from_previous_level_J": (
                        energy - float(previous["internal_energy_J"]) if previous else None
                    ),
                    "UZ_self_convergence_indicator_order": uz_order,
                    "energy_self_convergence_indicator_order": energy_order,
                    "independent_reference_status": "QUALIFIED_REFERENCE"
                    if reference_ok
                    else "NOT_ASSESSED_NO_QUALIFIED_ORACLE",
                    "UZ_relative_error_to_qualified_reference": abs(uz - ref_uz) / abs(ref_uz)
                    if reference_ok
                    else None,
                    "energy_relative_error_to_qualified_reference": abs(energy - ref_energy) / abs(ref_energy)
                    if reference_ok
                    else None,
                    "campaign_verdict": " / ".join(f"{name}:{value}" for name, value in sorted(verdicts.items()))
                    or "NO_VERDICTS_RECORDED",
                }
            )
    return output


def write_analysis_csv(path: Path, rows: list[dict[str, Any]]) -> str:
    """Write a derived CSV without replacing any existing evidence."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return sha256_file(path)


def write_convergence_svg(
    path: Path,
    rows: list[dict[str, Any]],
    *,
    value_field: str,
    title: str,
    unit: str,
) -> str:
    """Write a dependency-free SVG from derived sidecar rows, without overwrite."""
    if value_field not in {"signed_mean_loaded_face_UZ_m", "internal_energy_J"}:
        raise ValueError("plot field must be a declared displacement or energy observable")
    if not rows:
        raise ValueError("cannot plot an empty convergence result")
    series: dict[tuple[str, float], list[dict[str, Any]]] = {}
    for row in rows:
        key = (str(row["formulation"]), float(row["poisson_ratio"]))
        series.setdefault(key, []).append(row)
    mesh_order = {"x".join(str(value) for value in mesh): index for index, mesh in enumerate(MESH_LEVELS)}
    values = [float(row[value_field]) for row in rows if row.get(value_field) is not None]
    if not values or any(not math.isfinite(value) for value in values):
        raise ValueError("plot values must be present and finite")

    width, height = 920, 560
    left, right, top, bottom = 90, 40, 60, 115
    plot_width = width - left - right
    plot_height = height - top - bottom
    minimum, maximum = min(values), max(values)
    if minimum == maximum:
        delta = max(abs(minimum) * 0.05, 1.0e-12)
        minimum -= delta
        maximum += delta
    else:
        delta = (maximum - minimum) * 0.05
        minimum -= delta
        maximum += delta

    def x_for_level(index: int) -> float:
        return left + index * plot_width / (len(MESH_LEVELS) - 1)

    def y_for_value(value: float) -> float:
        return top + (maximum - value) * plot_height / (maximum - minimum)

    palette = ("#1769aa", "#d1495b", "#2a9d8f", "#6a4c93", "#f4a261", "#264653")
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f"<title>{escape(title)}</title>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width / 2}" y="30" text-anchor="middle" font-family="sans-serif" font-size="18">{escape(title)}</text>',
    ]
    lines.extend(
        [
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#222"/>',
            f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" y2="{top + plot_height}" stroke="#222"/>',
            f'<text x="24" y="{top + plot_height / 2}" transform="rotate(-90 24 {top + plot_height / 2})" text-anchor="middle" font-family="sans-serif" font-size="13">{escape(unit)}</text>',
            f'<text x="{left + plot_width / 2}" y="{height - 20}" text-anchor="middle" font-family="sans-serif" font-size="13">Mesh divisions (x × y × z)</text>',
        ]
    )
    for tick_index in range(5):
        value = maximum - tick_index * (maximum - minimum) / 4.0
        y = y_for_value(value)
        lines.append(f'<line x1="{left - 4}" y1="{y:.2f}" x2="{left + plot_width}" y2="{y:.2f}" stroke="#dddddd"/>')
        lines.append(
            f'<text x="{left - 9}" y="{y + 4:.2f}" text-anchor="end" font-family="sans-serif" font-size="10">{value:.4g}</text>'
        )
    for index, mesh in enumerate(MESH_LEVELS):
        x = x_for_level(index)
        label = "x".join(str(value) for value in mesh)
        lines.append(
            f'<line x1="{x:.2f}" y1="{top + plot_height}" x2="{x:.2f}" y2="{top + plot_height + 5}" stroke="#222"/>'
        )
        lines.append(
            f'<text x="{x:.2f}" y="{top + plot_height + 22}" text-anchor="middle" font-family="sans-serif" font-size="11">{label}</text>'
        )
    legend_x = left
    legend_y = top + plot_height + 48
    for series_index, (key, items) in enumerate(sorted(series.items())):
        ordered = sorted(items, key=lambda row: mesh_order.get(str(row["divisions_xyz"]), len(MESH_LEVELS)))
        color = palette[series_index % len(palette)]
        points = []
        for row in ordered:
            mesh = str(row["divisions_xyz"])
            if mesh not in mesh_order:
                raise ValueError(f"plot row has an unknown mesh level: {mesh}")
            points.append((x_for_level(mesh_order[mesh]), y_for_value(float(row[value_field]))))
        if points:
            point_text = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
            lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{point_text}"/>')
            lines.extend(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.5" fill="{color}"/>' for x, y in points)
        label = f"{key[0]}, ν={key[1]:g}"
        legend_row, legend_column = divmod(series_index, 3)
        lx = legend_x + legend_column * 260
        ly = legend_y + legend_row * 18
        lines.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 20}" y2="{ly}" stroke="{color}" stroke-width="2"/>')
        lines.append(f'<text x="{lx + 26}" y="{ly + 4}" font-family="sans-serif" font-size="11">{escape(label)}</text>')
    lines.append("</svg>")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(lines) + "\n")
        stream.flush()
    return sha256_file(path)
