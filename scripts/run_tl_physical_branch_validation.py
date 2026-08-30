"""Capture accepted TL equilibrium branches for diagnostic comparison.

The harness reuses the existing adaptive Full Newton driver.  Runtime
instrumentation exposes accepted trial states without changing solver source,
formulation, controls, or convergence criteria.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from run_tl_failure_isolation import _external, _fixed_indices, _model  # noqa: E402
from solveur.core.assembly.geometric import build_total_lagrangian_assembly  # noqa: E402
from solveur.core.analyses.geometric_nonlinear import _newton_dead_load  # noqa: E402
from solveur.core.errors import NumericalConvergenceError  # noqa: E402
from solveur.core.nonlinear import iteration as nonlinear_iteration  # noqa: E402
from solveur.core.nonlinear.controls import AdaptiveLoadControls  # noqa: E402


OUTPUT = ROOT / ".tmp_tl_physical_branch_validation"
TOLERANCE = 1.0e-8
MAX_ITERATIONS = 200
BASELINES = (
    {
        "id": "HEX8_m4_a10_compression_l0.2_n8_d0.12",
        "family": "HEX8",
        "cells": 4,
        "mode": "compression",
        "aspect": 10.0,
        "load_scale": 0.2,
        "increments": 8,
        "distortion": 0.12,
        "angle": 0.0,
    },
    {
        "id": "HEX8_m4_a10_compression_l0.2_n16_d0.12",
        "family": "HEX8",
        "cells": 4,
        "mode": "compression",
        "aspect": 10.0,
        "load_scale": 0.2,
        "increments": 16,
        "distortion": 0.12,
        "angle": 0.0,
    },
    {
        "id": "HEX8_m4_a10_compression_l0.2_n32_d0.12",
        "family": "HEX8",
        "cells": 4,
        "mode": "compression",
        "aspect": 10.0,
        "load_scale": 0.2,
        "increments": 32,
        "distortion": 0.12,
        "angle": 0.0,
    },
)


def _git_head() -> str:
    return subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=ROOT, text=True).strip()


def _git_dirty() -> bool:
    return bool(subprocess.check_output(("git", "status", "--porcelain"), cwd=ROOT, text=True).strip())


def _controls(increments: int) -> AdaptiveLoadControls:
    return AdaptiveLoadControls.from_parameters(
        {
            "initial_load_increment": 1.0 / increments,
            "min_load_increment": 1.0e-6,
            "max_load_increment": 1.0 / increments,
            "cutback_factor": 0.25,
            "growth_factor": 1.0,
            "max_cutbacks": 64,
        },
        load_steps=increments,
        max_iterations=MAX_ITERATIONS,
    )


def _finite_difference_error(assembly: Any, displacement: np.ndarray, tangent: Any, seed: int) -> float:
    direction = np.random.default_rng(seed).normal(size=displacement.size)
    direction /= np.linalg.norm(direction)
    step = 1.0e-7
    plus = assembly.assemble(displacement + step * direction, tangent_required=False)[0]
    minus = assembly.assemble(displacement - step * direction, tangent_required=False)[0]
    numerical = (plus - minus) / (2.0 * step)
    matrix = tangent.toarray() if hasattr(tangent, "toarray") else np.asarray(tangent)
    return float(np.linalg.norm(matrix @ direction - numerical) / max(np.linalg.norm(numerical), 1.0e-15))


def _determinant_samples(assembly: Any, displacement: np.ndarray) -> np.ndarray:
    if hasattr(assembly, "_reference_data") and hasattr(assembly, "_local_displacements"):
        local_values = assembly._local_displacements(displacement)
        values: list[float] = []
        for element_index, local_displacement in enumerate(local_values):
            for _, _, gradients, _ in assembly._reference_data[element_index]:
                deformation = assembly._deformation_gradient(local_displacement, gradients)
                values.append(float(np.linalg.det(deformation)))
        return np.asarray(values, dtype=float)
    return np.asarray(assembly.deformation_determinants(displacement), dtype=float)


def _von_mises(stress: np.ndarray) -> np.ndarray:
    identity = np.eye(3)
    deviatoric = stress - np.trace(stress, axis1=1, axis2=2)[:, None, None] * identity / 3.0
    return np.sqrt(1.5 * np.einsum("nij,nij->n", deviatoric, deviatoric))


class _AttemptContext:
    def __init__(self, assembly: Any, model: Any, fixed: np.ndarray, external: np.ndarray, loaded_nodes: np.ndarray) -> None:
        self.assembly = assembly
        self.model = model
        self.fixed = fixed
        self.external = external
        self.loaded_nodes = loaded_nodes
        self.attempts: list[dict[str, Any]] = []

    def _target_factor(self, target: np.ndarray) -> float:
        denominator = float(np.dot(self.external, self.external))
        return float(np.dot(target, self.external) / denominator) if denominator else 0.0

    def record_success(
        self,
        offset: np.ndarray,
        target: np.ndarray,
        trial_delta: np.ndarray,
        diagnostics: dict[str, Any],
    ) -> None:
        displacement = np.asarray(offset + trial_delta, dtype=float).copy()
        row = self._state_row(displacement, target, diagnostics)
        row.update({"attempt_status": "SUCCESS", "committed_displacement": np.asarray(offset).tolist()})
        self.attempts.append(row)

    def record_failure(self, offset: np.ndarray, target: np.ndarray, error: Exception) -> None:
        diagnostics = getattr(error, "diagnostics", {})
        self.attempts.append(
            {
                "attempt_status": "FAILURE",
                "load_factor": self._target_factor(target),
                "committed_displacement_hash": hashlib.sha256(np.asarray(offset, dtype=float).tobytes()).hexdigest(),
                "failure_reason": getattr(getattr(error, "reason", None), "value", str(getattr(error, "reason", type(error).__name__))),
                "failure_diagnostics": _json_safe(diagnostics),
            }
        )

    def _state_row(self, displacement: np.ndarray, target: np.ndarray, diagnostics: dict[str, Any]) -> dict[str, Any]:
        internal, tangent = self.assembly.assemble(displacement, tangent_required=True)
        free = np.setdiff1d(np.arange(self.assembly.ndof), self.fixed)
        residual = target - internal
        reduced_tangent = tangent[free][:, free].toarray()
        eigenvalues = np.linalg.eigvalsh(0.5 * (reduced_tangent + reduced_tangent.T))
        states = self.assembly.element_states(displacement)
        determinants = _determinant_samples(self.assembly, displacement)
        displacement_matrix = displacement.reshape((-1, 3))
        loaded = displacement_matrix[self.loaded_nodes]
        row: dict[str, Any] = {
            "load_factor": self._target_factor(target),
            "displacement": displacement.tolist(),
            "displacement_sha256": hashlib.sha256(displacement.tobytes()).hexdigest(),
            "displacement_norm": float(np.linalg.norm(displacement)),
            "displacement_max": float(np.max(np.abs(displacement))),
            "loaded_mean_displacement": np.mean(loaded, axis=0).tolist(),
            "loaded_mean_ux": float(np.mean(loaded[:, 0])),
            "reaction_vector_fixed": (internal[self.fixed] - target[self.fixed]).tolist(),
            "reaction_norm_fixed": float(np.linalg.norm(internal[self.fixed] - target[self.fixed])),
            "residual_norm_free": float(np.linalg.norm(residual[free])),
            "relative_residual_free": float(np.linalg.norm(residual[free]) / max(np.linalg.norm(target[free]), 1.0)),
            "strain_energy": float(self.assembly.strain_energy(displacement)),
            "det_f_min": float(np.min(determinants)),
            "det_f_max": float(np.max(determinants)),
            "tangent_min_eigenvalue": float(np.min(eigenvalues)),
            "tangent_max_eigenvalue": float(np.max(eigenvalues)),
            "tangent_condition_number": float(np.linalg.cond(reduced_tangent)),
            "tangent_fd_relative_error": _finite_difference_error(self.assembly, displacement, tangent, int(len(self.attempts) + 260700)),
            "von_mises_min": float(np.min(_von_mises(states["cauchy_stress"]))),
            "von_mises_max": float(np.max(_von_mises(states["cauchy_stress"]))),
            "iterations": diagnostics.get("increments", [{}])[0].get("iterations"),
            "residual_initial": diagnostics.get("increments", [{}])[0].get("residual_initial"),
            "residual_final": diagnostics.get("increments", [{}])[0].get("residual_final"),
            "residual_history": diagnostics.get("increments", [{}])[0].get("residual_history", []),
            "line_search_iterations": diagnostics.get("increments", [{}])[0].get("diagnostics", {}).get("line_search_iterations", 0),
        }
        return _json_safe(row)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, (np.floating, np.integer, np.bool_)):
        return value.item()
    return value


def _run_case(definition: dict[str, Any]) -> dict[str, Any]:
    model, _, _, _, loaded_nodes = _model(
        definition["family"],
        definition["cells"],
        definition["mode"],
        definition["load_scale"],
        definition["increments"],
        distortion=definition["distortion"],
        angle=definition["angle"],
        aspect=definition["aspect"],
    )
    dofs = model.dof_manager()
    fixed = _fixed_indices(model, dofs)
    external = _external(model, dofs)
    assembly = build_total_lagrangian_assembly(model)
    context = _AttemptContext(assembly, model, fixed, external, loaded_nodes)
    original_offset = nonlinear_iteration._OffsetNonlinearAssembly
    original_full_newton = nonlinear_iteration.solve_full_newton

    class ObservedOffset(original_offset):
        def __init__(self, wrapped: Any, offset: np.ndarray) -> None:
            super().__init__(wrapped, offset)
            self.observation_context = context

    def observed_full_newton(assembly_arg: Any, external_arg: np.ndarray, fixed_arg: np.ndarray, **kwargs: Any) -> tuple[np.ndarray, dict[str, Any]]:
        if not isinstance(assembly_arg, ObservedOffset):
            return original_full_newton(assembly_arg, external_arg, fixed_arg, **kwargs)
        try:
            result = original_full_newton(assembly_arg, external_arg, fixed_arg, **kwargs)
        except Exception as exc:
            context.record_failure(assembly_arg.offset, external_arg, exc)
            raise
        context.record_success(assembly_arg.offset, external_arg, result[0], result[1])
        return result

    nonlinear_iteration._OffsetNonlinearAssembly = ObservedOffset
    nonlinear_iteration.solve_full_newton = observed_full_newton
    try:
        try:
            displacement, diagnostics = _newton_dead_load(
                assembly,
                external,
                fixed,
                increments=int(definition["increments"]),
                tolerance=TOLERANCE,
                max_iterations=MAX_ITERATIONS,
                determinant_assembly=assembly,
                adaptive_controls=_controls(int(definition["increments"])),
            )
            status = "SUCCESS"
            failure = None
        except NumericalConvergenceError as exc:
            displacement = np.asarray(exc.diagnostics.get("last_displacement", np.zeros(assembly.ndof)), dtype=float)
            diagnostics = dict(exc.diagnostics)
            status = "FAILURE"
            failure = {
                "reason": getattr(exc.reason, "value", str(exc.reason)),
                "diagnostics": _json_safe(exc.diagnostics),
            }
    finally:
        nonlinear_iteration._OffsetNonlinearAssembly = original_offset
        nonlinear_iteration.solve_full_newton = original_full_newton

    accepted = [row for row in context.attempts if row.get("attempt_status") == "SUCCESS"]
    rejected = [row for row in context.attempts if row.get("attempt_status") == "FAILURE"]
    return _json_safe(
        {
            "id": definition["id"],
            "definition": definition,
            "status": status,
            "failure": failure,
            "diagnostics": diagnostics,
            "accepted_states": accepted,
            "attempts": context.attempts,
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "final_displacement": np.asarray(displacement, dtype=float).tolist(),
        }
    )


def run(output: Path = OUTPUT) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "DIAGNOSTIC_ONLY",
        "study_id": "TL-PHYSICAL-BRANCH-VALIDATION-026",
        "source_sha": _git_head(),
        "dirty_at_start": _git_dirty(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "solver_controls": {
            "tolerance": TOLERANCE,
            "max_iterations": MAX_ITERATIONS,
            "initial_increment": "1/increments",
            "min_load_increment": 1.0e-6,
            "max_load_increment": "1/increments",
            "cutback_factor": 0.25,
            "growth_factor": 1.0,
            "max_cutbacks": 64,
        },
        "cases": [],
    }
    for definition in BASELINES:
        print(definition["id"], flush=True)
        case = _run_case(definition)
        report["cases"].append(case)
        (output / f"{definition['id']}.json").write_text(json.dumps(case, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report["sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.glob("*.json"))
    }
    (output / "summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    report = run(args.output.resolve())
    print(
        json.dumps(
            {
                "source_sha": report["source_sha"],
                "dirty_at_start": report["dirty_at_start"],
                "cases": len(report["cases"]),
                "successes": sum(case["status"] == "SUCCESS" for case in report["cases"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
