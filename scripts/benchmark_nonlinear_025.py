"""Run a small reproducible 0.2.5 nonlinear cost characterization.

This benchmark is deliberately separate from CI and does not assert a speed
target. It records solver cost, sparse structure, Newton diagnostics and a
portable peak allocation estimate for the regular two-cell J2 benchmark used
by the 0.2.5 V&V campaign. The kinematics can be selected explicitly to
characterize the small-strain and experimental finite-kinematic paths. Repeated
runs also report timing variability and optional RSS deltas for profiling.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
import tracemalloc
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from solveur.api import solve_model
from solveur.contact.entities import FrictionlessContact
from solveur.core.model import FiniteElementModel
from solveur.verification.robustness_nonlinear_solids import ELEMENT_TYPES, _refinement_model


def _git_provenance() -> dict[str, object]:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        sha, dirty = "unknown", None
    return {"sha": sha, "worktree_dirty": dirty}


def _rss_bytes() -> int | None:
    try:
        import psutil

        return int(psutil.Process().memory_info().rss)
    except (ImportError, OSError):
        return None


BENCHMARK_PATHS = (
    "load_control",
    "geometric_static",
    "arc_length",
    "arc_length_finite_kinematic",
    "contact",
    "finite_sliding",
    "coupled",
)


def _benchmark_model(family: str, kinematics: str, path: str):
    """Build one explicitly named nonlinear benchmark path."""
    if path not in BENCHMARK_PATHS:
        raise ValueError(f"Unsupported nonlinear benchmark path {path!r}.")
    if path in {"contact", "finite_sliding", "coupled"} and family != "TET4":
        raise ValueError("The bounded contact, finite-sliding and coupled benchmark paths currently require TET4.")
    if path == "arc_length" and family != "TET4":
        raise ValueError("The legacy bounded arc-length benchmark currently requires TET4.")
    if path == "arc_length_finite_kinematic":
        model = _refinement_model(family, 1)
        parameters = dict(model.analysis.parameters)
        parameters.pop("load_path", None)
        parameters.update(
            {
                "kinematics": "total_lagrangian_j2",
                "target_load_factor": 0.5,
                # HEX20 needs a longer continuation budget on this bounded
                # medium-size path; the solver still stops at the signed target.
                "max_arc_steps": 512,
                "arc_length_stop_mode": "target_load",
                "adaptive_arc_length": True,
                "arc_length_growth_factor": 1.5,
                "arc_length_shrink_factor": 0.5,
                "max_arc_length_radius": 0.1,
                "max_iterations": 60,
                "tolerance": 1.0e-7,
            }
        )
        return replace(model, analysis=replace(model.analysis, method="arc_length", parameters=parameters))
    if path == "arc_length":
        if kinematics != "small_strain":
            raise ValueError("The bounded arc-length benchmark uses small-strain kinematics.")
        return FiniteElementModel.from_raw(
            nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
            elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "rubber"}],
            materials={"rubber": {"type": "nonlinear_isotropic_3d", "E": 1000.0, "nu": 0.25, "hardening": 1.0e6}},
            fixed_dofs=[
                {"node": 0, "dofs": ["UX", "UY", "UZ"]},
                {"node": 2, "dofs": ["UX", "UY", "UZ"]},
                {"node": 3, "dofs": ["UX", "UY", "UZ"]},
            ],
            loads=[{"node": 1, "dof": "UX", "value": 10.0}],
            analysis={
                "type": "nonlinear_static",
                "method": "arc_length",
                "load_steps": 5,
                "max_iterations": 50,
                "tolerance": 1.0e-9,
                "max_arc_steps": 12,
                "target_load_factor": 1.0,
            },
        )
    if path == "finite_sliding":
        model = FiniteElementModel.from_raw(
            nodes=[
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [1.0, 1.0, 0.0],
                [0.0, 1.0, 0.0],
                [1.2, 0.25, -0.1],
            ],
            elements=[],
            materials={},
            fixed_dofs=[
                {"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(4)
            ] + [{"node": 4, "dofs": ["UX", "UY"]}],
            loads=[{"node": 4, "dof": "UZ", "value": -1.0}],
            springs=[{"node_a": 4, "dofs": ["UZ"], "stiffness": 1000.0}],
            analysis={
                "type": "nonlinear_static",
                "method": "newton_raphson",
                "load_path": [1.0],
                "max_iterations": 20,
                "tolerance": 1.0e-8,
                "contact_mode": "penalty",
                "contact_penalty": 1000.0,
                "contact_search_mode": "updated",
                "contact_finite_sliding": True,
            },
        )
        model.contacts.append(
            FrictionlessContact(
                name="finite_sliding_surface",
                slave_node=4,
                master_nodes=(0, 1, 2),
                master_faces=((0, 1, 2), (0, 2, 3)),
            )
        )
        return model
    if path == "geometric_static":
        model = _refinement_model(family, 1)
        model.materials["j2"] = {
            "type": "isotropic_3d",
            "E": 1000.0,
            "nu": 0.3,
        }
        model.analysis = replace(
            model.analysis,
            type="geometric_nonlinear_static",
            method="newton_raphson",
            parameters={
                "load_increments": 6,
                "max_iterations": 40,
                "tolerance": 1.0e-8,
            },
        )
        return model
    cells = 1 if path != "load_control" else 2
    model = _refinement_model(family, cells)
    parameters = dict(model.analysis.parameters)
    if path in {"contact", "coupled"}:
        model.contacts.append(FrictionlessContact(slave_node=1, master_nodes=(0, 3, 4)))
        model.analysis = replace(
            model.analysis,
            parameters={
                **parameters,
                "kinematics": "total_lagrangian_j2" if path == "coupled" else kinematics,
                "contact_mode": "penalty",
                "contact_search_mode": "updated",
                "contact_penalty": 1.0e6,
                "load_steps": 2,
            },
        )
    elif kinematics != "small_strain":
        parameters["kinematics"] = kinematics
        model.analysis = replace(model.analysis, parameters=parameters)
    return model


def _run_once(
    family: str,
    kinematics: str = "small_strain",
    *,
    path: str = "load_control",
) -> dict[str, object]:
    model = _benchmark_model(family, kinematics, path)
    effective_kinematics = (
        "total_lagrangian_stvk"
        if path == "geometric_static"
        else str(model.analysis.parameters.get("kinematics", kinematics)).lower()
    )
    tracemalloc.start()
    rss_before = _rss_bytes()
    started = time.perf_counter()
    result = None
    failure: dict[str, object] | None = None
    try:
        result = solve_model(model, enforce_policy=False)
    except Exception as error:  # benchmark evidence must record failures, not hide them
        failure = {
            "type": type(error).__name__,
            "reason": getattr(getattr(error, "reason", None), "value", getattr(error, "reason", None)),
            "diagnostics": dict(getattr(error, "diagnostics", {})),
        }
    finally:
        elapsed = time.perf_counter() - started
        _, peak_allocated = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    rss_after = _rss_bytes()
    data = result.to_dict() if result is not None else {"solver": {"steps": []}}
    solver_data = data["solver"]
    steps = solver_data.get("steps") or solver_data.get("increments") or []
    assembly_seconds = (
        sum(float(step["assembly_seconds"]) for step in steps if "assembly_seconds" in step)
        if any("assembly_seconds" in step for step in steps)
        else None
    )
    linear_solve_seconds = (
        sum(float(step["linear_solve_seconds"]) for step in steps if "linear_solve_seconds" in step)
        if any("linear_solve_seconds" in step for step in steps)
        else None
    )
    line_search_seconds = (
        sum(float(step["line_search_seconds"]) for step in steps if "line_search_seconds" in step)
        if any("line_search_seconds" in step for step in steps)
        else None
    )
    component_timing = {
        key: (
            sum(float(step[key]) for step in steps if key in step)
            if any(key in step for step in steps)
            else None
        )
        for key in (
            "element_setup_seconds",
            "element_kernel_seconds",
            "element_scatter_seconds",
            "sparse_conversion_seconds",
            "contact_assembly_seconds",
        )
    }
    element_kernel_calls = [int(step["element_kernel_calls"]) for step in steps if "element_kernel_calls" in step]
    contact_assembly_calls = [
        int(step["contact_assembly_calls"]) for step in steps if "contact_assembly_calls" in step
    ]
    element_cache_hits = [int(step["element_cache_hits"]) for step in steps if "element_cache_hits" in step]
    element_cache_misses = [
        int(step["element_cache_misses"]) for step in steps if "element_cache_misses" in step
    ]
    reference_cache_hits = [
        int(step["reference_cache_hits"]) for step in steps if "reference_cache_hits" in step
    ]
    reference_cache_misses = [
        int(step["reference_cache_misses"]) for step in steps if "reference_cache_misses" in step
    ]
    assembly_metrics = solver_data.get("sparse_assembly", {})
    sparse_chunk_counts = [
        int(step.get("sparse_chunk_count", assembly_metrics.get("sparse_chunk_count", 0)))
        for step in steps
    ]
    sparse_peak_chunk_entries = [
        int(step.get("sparse_peak_chunk_entries", assembly_metrics.get("sparse_peak_chunk_entries", 0)))
        for step in steps
    ]
    sparse_peak_chunk_bytes_estimates = [
        int(
            step.get(
                "sparse_peak_chunk_bytes_estimate",
                assembly_metrics.get("sparse_peak_chunk_bytes_estimate", 0),
            )
        )
        for step in steps
    ]
    sparse_accumulator_levels = [
        int(step.get("sparse_accumulator_levels", assembly_metrics.get("sparse_accumulator_levels", 0)))
        for step in steps
    ]
    tangent_nnz = [int(step["tangent_nnz"]) for step in steps if "tangent_nnz" in step]
    finite_sliding_steps = [
        int(bool(step.get("contact_finite_sliding", False))) for step in steps
    ]
    projection_clamped_counts = [
        sum(bool(value) for value in step.get("contact_projection_clamped", []))
        for step in steps
    ]
    projection_modes = sorted(
        {
            str(mode)
            for step in steps
            for mode in step.get("contact_projection_modes", [])
        }
    )
    return {
        "element": family,
        "kinematics": effective_kinematics,
        "path": path,
        "status": (
            "PASS"
            if result is not None and str(result.status).upper() in {"PASS", "SUCCESS"}
            else "FAIL"
        ),
        "node_count": int(result.node_count) if result is not None else None,
        "element_count": int(result.element_count) if result is not None else None,
        "dof_count": int(result.displacements.size) if result is not None else None,
        "newton_iterations": int(sum(int(step["iterations"]) for step in steps)) if steps else None,
        "maximum_relative_residual": max(float(step["relative_residual"]) for step in steps) if steps else None,
        "final_displacement_norm": float(np.linalg.norm(result.displacements)) if result is not None else None,
        "final_peeq": (
            float(steps[-1]["equivalent_plastic_strain_max"])
            if steps and "equivalent_plastic_strain_max" in steps[-1]
            else None
        ),
        "final_plastic_dissipation": (
            float(steps[-1]["plastic_dissipation_max"])
            if steps and "plastic_dissipation_max" in steps[-1]
            else None
        ),
        "elapsed_seconds": float(elapsed),
        "python_peak_allocated_bytes": int(peak_allocated),
        "rss_before_bytes": rss_before,
        "rss_after_bytes": rss_after,
        "failure": failure,
        "sparse_path": True,
        "assembly_seconds": assembly_seconds,
        "linear_solve_seconds": linear_solve_seconds,
        "line_search_seconds": line_search_seconds,
        **component_timing,
        "max_element_kernel_calls": max(element_kernel_calls) if element_kernel_calls else None,
        "max_contact_assembly_calls": max(contact_assembly_calls) if contact_assembly_calls else None,
        "element_cache_hits": sum(element_cache_hits) if element_cache_hits else None,
        "element_cache_misses": sum(element_cache_misses) if element_cache_misses else None,
        "reference_cache_hits": sum(reference_cache_hits) if reference_cache_hits else None,
        "reference_cache_misses": sum(reference_cache_misses) if reference_cache_misses else None,
        "max_sparse_chunk_count": max(sparse_chunk_counts) if sparse_chunk_counts else None,
        "max_sparse_peak_chunk_entries": max(sparse_peak_chunk_entries) if sparse_peak_chunk_entries else None,
        "max_sparse_peak_chunk_bytes_estimate": (
            max(sparse_peak_chunk_bytes_estimates) if sparse_peak_chunk_bytes_estimates else None
        ),
        "max_sparse_accumulator_levels": max(sparse_accumulator_levels) if sparse_accumulator_levels else None,
        "max_tangent_nnz": max(tangent_nnz) if tangent_nnz else None,
        "finite_sliding_steps": sum(finite_sliding_steps) if finite_sliding_steps else 0,
        "projection_clamped_count": sum(projection_clamped_counts) if projection_clamped_counts else 0,
        "projection_modes": projection_modes,
        "notes": [
            "tracemalloc measures Python allocations and is not a total-RSS substitute.",
            "Component timings are observational and exclude final post-processing.",
        ],
    }


def run_campaign(
    families: list[str],
    repeats: int,
    output: Path | None = None,
    *,
    kinematics: str = "small_strain",
    path: str = "load_control",
) -> dict[str, Any]:
    """Run the requested element families and return raw samples plus summaries."""
    if repeats < 1:
        raise ValueError("repeats must be positive")
    if kinematics not in {"small_strain", "total_lagrangian_j2"}:
        raise ValueError("Unsupported benchmark kinematics.")
    if path not in BENCHMARK_PATHS:
        raise ValueError(f"Unsupported nonlinear benchmark path {path!r}.")
    samples: list[dict[str, object]] = []
    for family in families:
        for repetition in range(repeats):
            if path == "load_control":
                row = _run_once(family) if kinematics == "small_strain" else _run_once(family, kinematics)
            else:
                row = _run_once(family, kinematics, path=path)
            row["repeat"] = repetition + 1
            samples.append(row)
    def mean_optional(rows: list[dict[str, object]], key: str) -> float | None:
        values = [float(row[key]) for row in rows if row.get(key) is not None]
        return float(np.mean(values)) if values else None

    def std_optional(rows: list[dict[str, object]], key: str) -> float | None:
        values = [float(row[key]) for row in rows if row.get(key) is not None]
        return float(np.std(values, ddof=1 if len(values) > 1 else 0)) if values else None

    def median_optional(rows: list[dict[str, object]], key: str) -> float | None:
        values = [float(row[key]) for row in rows if row.get(key) is not None]
        return float(np.median(values)) if values else None

    def max_rss(row: dict[str, object]) -> float | None:
        values = [float(row[key]) for key in ("rss_before_bytes", "rss_after_bytes") if row.get(key) is not None]
        return max(values) if values else None

    summary: list[dict[str, object]] = []
    for family in families:
        rows = [row for row in samples if row["element"] == family]
        elapsed_values = [float(row["elapsed_seconds"]) for row in rows]
        mean_elapsed = float(np.mean(elapsed_values))
        elapsed_stddev = std_optional(rows, "elapsed_seconds")
        rss_values = [value for row in rows if (value := max_rss(row)) is not None]
        rss_deltas = [
            float(row["rss_after_bytes"]) - float(row["rss_before_bytes"])
            for row in rows
            if row.get("rss_before_bytes") is not None and row.get("rss_after_bytes") is not None
        ]
        summary.append(
            {
                "element": family,
                "kinematics": rows[0].get("kinematics", kinematics),
                "path": path,
                "repeats": len(rows),
                "successful_repeats": sum(str(row.get("status")) == "PASS" for row in rows),
                "failed_repeats": sum(str(row.get("status")) != "PASS" for row in rows),
                "mean_elapsed_seconds": mean_elapsed,
                "median_elapsed_seconds": float(np.median(elapsed_values)),
                "min_elapsed_seconds": min(elapsed_values),
                "max_elapsed_seconds": max(elapsed_values),
                "elapsed_stddev_seconds": elapsed_stddev,
                "elapsed_coefficient_variation": (
                    elapsed_stddev / mean_elapsed if elapsed_stddev is not None and mean_elapsed > 0.0 else None
                ),
                "max_python_peak_allocated_bytes": max(int(row["python_peak_allocated_bytes"]) for row in rows),
                "max_rss_bytes": max(rss_values) if rss_values else None,
                "mean_rss_delta_bytes": float(np.mean(rss_deltas)) if rss_deltas else None,
                "dof_count": rows[0]["dof_count"],
                "newton_iterations": rows[0]["newton_iterations"],
                "mean_assembly_seconds": mean_optional(rows, "assembly_seconds"),
                "median_assembly_seconds": median_optional(rows, "assembly_seconds"),
                "mean_linear_solve_seconds": mean_optional(rows, "linear_solve_seconds"),
                "median_linear_solve_seconds": median_optional(rows, "linear_solve_seconds"),
                "mean_line_search_seconds": mean_optional(rows, "line_search_seconds"),
                "median_line_search_seconds": median_optional(rows, "line_search_seconds"),
                "mean_element_setup_seconds": mean_optional(rows, "element_setup_seconds"),
                "median_element_setup_seconds": median_optional(rows, "element_setup_seconds"),
                "mean_element_kernel_seconds": mean_optional(rows, "element_kernel_seconds"),
                "median_element_kernel_seconds": median_optional(rows, "element_kernel_seconds"),
                "mean_element_scatter_seconds": mean_optional(rows, "element_scatter_seconds"),
                "median_element_scatter_seconds": median_optional(rows, "element_scatter_seconds"),
                "mean_sparse_conversion_seconds": mean_optional(rows, "sparse_conversion_seconds"),
                "median_sparse_conversion_seconds": median_optional(rows, "sparse_conversion_seconds"),
                "mean_contact_assembly_seconds": mean_optional(rows, "contact_assembly_seconds"),
                "median_contact_assembly_seconds": median_optional(rows, "contact_assembly_seconds"),
                "mean_element_cache_hits": mean_optional(rows, "element_cache_hits"),
                "mean_element_cache_misses": mean_optional(rows, "element_cache_misses"),
                "mean_reference_cache_hits": mean_optional(rows, "reference_cache_hits"),
                "mean_reference_cache_misses": mean_optional(rows, "reference_cache_misses"),
                "max_sparse_chunk_count": max(
                    (int(row["max_sparse_chunk_count"]) for row in rows if row.get("max_sparse_chunk_count") is not None),
                    default=None,
                ),
                "max_sparse_peak_chunk_entries": max(
                    (
                        int(row["max_sparse_peak_chunk_entries"])
                        for row in rows
                        if row.get("max_sparse_peak_chunk_entries") is not None
                    ),
                    default=None,
                ),
                "max_sparse_peak_chunk_bytes_estimate": max(
                    (
                        int(row["max_sparse_peak_chunk_bytes_estimate"])
                        for row in rows
                        if row.get("max_sparse_peak_chunk_bytes_estimate") is not None
                    ),
                    default=None,
                ),
                "max_sparse_accumulator_levels": max(
                    (
                        int(row["max_sparse_accumulator_levels"])
                        for row in rows
                        if row.get("max_sparse_accumulator_levels") is not None
                    ),
                    default=None,
                ),
                "max_element_kernel_calls": max(
                    (int(row["max_element_kernel_calls"]) for row in rows if row.get("max_element_kernel_calls") is not None),
                    default=None,
                ),
                "max_contact_assembly_calls": max(
                    (int(row["max_contact_assembly_calls"]) for row in rows if row.get("max_contact_assembly_calls") is not None),
                    default=None,
                ),
                "max_tangent_nnz": max(
                    (int(row["max_tangent_nnz"]) for row in rows if row.get("max_tangent_nnz") is not None),
                    default=None,
                ),
                "max_finite_sliding_steps": max(
                    (int(row["finite_sliding_steps"]) for row in rows if row.get("finite_sliding_steps") is not None),
                    default=None,
                ),
                "max_projection_clamped_count": max(
                    (
                        int(row["projection_clamped_count"])
                        for row in rows
                        if row.get("projection_clamped_count") is not None
                    ),
                    default=None,
                ),
                "projection_modes": sorted(
                    {
                        str(mode)
                        for row in rows
                        for mode in row.get("projection_modes", [])
                    }
                ),
            }
        )
    effective_campaign_kinematics = (
        "total_lagrangian_j2" if path == "arc_length_finite_kinematic" else kinematics
    )
    report: dict[str, Any] = {
        "schema_version": 2,
        "campaign": "qf-solver-nonlinear-performance-0.2.5a0",
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "provenance": _git_provenance(),
        },
        "families": families,
        "kinematics": effective_campaign_kinematics,
        "path": path,
        "repeats": repeats,
        "samples": samples,
        "summary": summary,
        "limitations": [
            "Engineering-medium regular samples only: two-cell J2 for load-control and a one-level Total-Lagrangian StVK mesh for geometric_static.",
            "No scaling or release qualification claim is made.",
            "Component timings are observational and do not assert a performance target.",
            "External solver correlation and clean-SHA repeatability remain separate gates.",
        ],
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--families", nargs="+", choices=ELEMENT_TYPES, default=list(ELEMENT_TYPES))
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument(
        "--kinematics",
        choices=("small_strain", "total_lagrangian_j2"),
        default="small_strain",
    )
    parser.add_argument("--path", choices=BENCHMARK_PATHS, default="load_control")
    parser.add_argument("--output", type=Path, default=Path("results/benchmark_0_2_5/nonlinear.json"))
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    report = run_campaign(
        list(args.families),
        args.repeats,
        args.output,
        kinematics=args.kinematics,
        path=args.path,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
