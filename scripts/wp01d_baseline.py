"""Archive the WP01-D adaptive and arc-length baseline before migration edits.

This runner records the current continuation behaviour at the WP01-D start
commit.  It is deliberately an evidence helper, not a new qualification
solver or a replacement for the focused pytest cases.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

import numpy as np
from scipy.sparse import eye

from solveur.api import solve_model
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.controls import AdaptiveLoadControls
from solveur.core.nonlinear.iteration import solve_adaptive_full_newton
from solveur.core.nonlinear.state import NonlinearState, deterministic_state_digest
from solveur.core.nonlinear.solver import NonlinearStaticSolver
from wp01c_baseline import (
    _geometric_hex8_model,
    _geometric_tet4_model,
)
from solveur.verification.robustness_nonlinear_solids import _refinement_model
from solveur.contact.entities import FrictionlessContact


BASELINE_SHA = "9bc07ea5d4e7878702fca58ef7e90af53b039247"


def nonlinear_tet4_model(method: str = "newton_raphson") -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        analysis={
            "type": "nonlinear_static",
            "method": method,
            "load_steps": 5,
            "max_iterations": 50,
            "tolerance": 1.0e-9,
        },
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "rubber"}],
        materials={"rubber": {"type": "nonlinear_isotropic_3d", "E": 1000.0, "nu": 0.25, "hardening": 1.0e6}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": 10.0}],
    )


def elastoplastic_tet4_model() -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        analysis={
            "type": "nonlinear_static",
            "method": "newton_line_search",
            "load_steps": 5,
            "max_iterations": 80,
            "tolerance": 1.0e-9,
        },
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "plastic"}],
        materials={
            "plastic": {
                "type": "von_mises_elastoplastic_3d",
                "E": 1000.0,
                "nu": 0.25,
                "yield_stress": 5.0,
                "hardening_modulus": 100.0,
            }
        },
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": 10.0}],
    )


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _result_record(name: str, model: FiniteElementModel) -> dict[str, Any]:
    result = solve_model(model, enforce_policy=False)
    payload = result.to_dict()
    solver = payload.get("solver", {})
    steps = list(solver.get("steps", solver.get("increments", [])))
    final_step = steps[-1] if steps else {}
    load_factor = final_step.get("load_factor", solver.get("load_path", [1.0])[-1])
    state_payload = {
        "displacements": payload.get("displacements", []),
        "load_factor": load_factor,
        "material_states": payload.get("material_states", []),
        "continuation": {
            "arc_length_radius": [step.get("arc_length_radius") for step in steps],
            "load_factors": [step.get("load_factor") for step in steps],
        },
    }
    return {
        "name": name,
        "status": result.status,
        "analysis": result.analysis,
        "method": result.method,
        "displacements": payload.get("displacements", []),
        "material_states": payload.get("material_states", []),
        "load_factor": load_factor,
        "accepted_step_count": len(steps),
        "rejected_increment_count": int(solver.get("rejected_increments", 0)),
        "cutback_count": sum(int(step.get("load_step_cutbacks", 0)) for step in steps),
        "newton_iteration_count": sum(int(step.get("iterations", 0)) for step in steps),
        "residual_histories": [step.get("residual_history", []) for step in steps],
        "arc_radius_history": [step.get("arc_length_radius") for step in steps],
        "load_factor_history": [step.get("load_factor") for step in steps],
        "rejection_log": solver.get("rejection_log", []),
        "continuation_state_observation": state_payload["continuation"],
        "state_digest": deterministic_state_digest(state_payload),
        "solver_steps": steps,
        "checkpoint_files": solver.get("checkpoint_files", []),
        "equilibrium": payload.get("audit", {}).get("equilibrium", {}),
    }


def _optional_result_record(name: str, factory) -> dict[str, Any]:
    try:
        return _result_record(name, factory())
    except InputValidationError as error:
        return {
            "name": name,
            "status": "NOT_SUPPORTED_AT_BASELINE",
            "reason": str(error),
        }
def _adaptive_j2() -> FiniteElementModel:
    model = elastoplastic_tet4_model()
    model.analysis.parameters.update(
        {
            "adaptive_load_steps": True,
            "initial_load_increment": 0.25,
            "min_load_increment": 0.0625,
            "max_load_increment": 0.5,
            "cutback_factor": 0.5,
            "growth_factor": 1.5,
            "max_cutbacks": 8,
        }
    )
    return model


def _adaptive_penalty_contact() -> FiniteElementModel:
    model = _refinement_model("TET4", 1)
    model.contacts.append(FrictionlessContact(slave_node=1, master_nodes=(0, 3, 4)))
    model.analysis = replace(
        model.analysis,
        parameters={
            **model.analysis.parameters,
            "adaptive_load_steps": True,
            "initial_load_increment": 0.25,
            "min_load_increment": 0.0625,
            "max_load_increment": 0.5,
            "cutback_factor": 0.5,
            "growth_factor": 1.5,
            "contact_mode": "penalty",
            "contact_penalty": 1.0e6,
        },
    )
    return model


class _RejectOnceAssembly:
    ndof = 2

    def __init__(self) -> None:
        self.calls = 0

    def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
        self.calls += 1
        if self.calls == 1:
            raise NumericalConvergenceError(
                "controlled failed increment",
                reason=NonlinearFailureReason.MAX_ITERATIONS,
            )
        return np.array([displacement[0], 0.0]), eye(2, format="csr")


class _AlwaysFailAssembly:
    ndof = 2

    def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
        raise NumericalConvergenceError(
            "controlled failed increment",
            reason=NonlinearFailureReason.MAX_ITERATIONS,
        )


def _adaptive_controls(**overrides: object) -> AdaptiveLoadControls:
    parameters: dict[str, object] = {
        "initial_load_increment": 1.0,
        "min_load_increment": 0.1,
        "max_load_increment": 1.0,
        "cutback_factor": 0.5,
        "growth_factor": 1.0,
        "grow_below_iterations": 2,
        "shrink_above_iterations": 10,
        "max_cutbacks": 4,
    }
    parameters.update(overrides)
    return AdaptiveLoadControls.from_parameters(parameters, load_steps=1, max_iterations=5)


def _adaptive_failure_record(minimum_increment: bool = False) -> dict[str, Any]:
    assembly: object = _AlwaysFailAssembly()
    controls = _adaptive_controls(
        min_load_increment=0.75 if minimum_increment else 0.1,
        max_cutbacks=4 if minimum_increment else 2,
    )
    displacement = np.array([0.0, 0.0])
    before = NonlinearState(displacement=displacement).digest
    try:
        solve_adaptive_full_newton(
            assembly,  # type: ignore[arg-type]
            np.array([1.0, 0.0]),
            np.array([1]),
            increments=1,
            tolerance=1.0e-8,
            max_iterations=5,
            controls=controls,
        )
    except NumericalConvergenceError as error:
        return {
            "name": "adaptive_minimum_increment" if minimum_increment else "adaptive_max_cutbacks",
            "reason": error.reason.value if error.reason is not None else None,
            "diagnostics": _jsonable(error.diagnostics),
            "accepted_digest_before": before,
            "accepted_digest_after": NonlinearState(displacement=displacement).digest,
        }
    raise RuntimeError("The expected adaptive failure unexpectedly converged.")


def _arc_reject_once_record() -> dict[str, Any]:
    model = nonlinear_tet4_model(method="arc_length")
    model.analysis.parameters.update(
        {
            "arc_length_radius": 0.1,
            "max_arc_length_radius": 0.1,
            "min_arc_length_radius": 1.0e-6,
            "arc_length_shrink_factor": 0.5,
        }
    )
    original = NonlinearStaticSolver._solve_arc_length_step
    marker = {"rejected": False}

    def reject_once(self, *args: Any, **kwargs: Any):
        if not marker["rejected"]:
            marker["rejected"] = True
            raise NumericalConvergenceError(
                "controlled arc-length rejection",
                reason=NonlinearFailureReason.ARC_LENGTH_FAILURE,
            )
        return original(self, *args, **kwargs)

    with patch.object(NonlinearStaticSolver, "_solve_arc_length_step", reject_once):
        record = _result_record("arc_length_rejected_step_radius_shrink", model)
    return record


def build_baseline(source_sha: str = BASELINE_SHA) -> dict[str, Any]:
    cases = [
        _result_record("adaptive_small_strain_j2", _adaptive_j2()),
        _result_record("adaptive_geometric_tet4", replace(_geometric_tet4_model(), analysis=replace(_geometric_tet4_model().analysis, parameters={**_geometric_tet4_model().analysis.parameters, "adaptive_load_steps": True, "initial_load_increment": 0.25, "min_load_increment": 0.0625, "max_load_increment": 0.5, "growth_factor": 1.5}))),
        _result_record("adaptive_geometric_hex8", replace(_geometric_hex8_model(), analysis=replace(_geometric_hex8_model().analysis, parameters={**_geometric_hex8_model().analysis.parameters, "adaptive_load_steps": True, "initial_load_increment": 0.25, "min_load_increment": 0.0625, "max_load_increment": 0.5, "growth_factor": 1.5}))),
        _optional_result_record("adaptive_penalty_contact", _adaptive_penalty_contact),
    ]
    arc = nonlinear_tet4_model(method="arc_length")
    cases.append(_result_record("arc_length_monotonic", arc))
    turning = nonlinear_tet4_model(method="arc_length")
    turning.analysis.parameters.update(
        {
            "arc_length_stop_mode": "max_steps",
            "max_arc_steps": 6,
            "arc_length_allow_load_factor_turning": True,
            "arc_length_load_factor_limit": 2.0,
            "arc_length_radius": 0.05,
            "max_arc_length_radius": 0.2,
        }
    )
    cases.append(_result_record("arc_length_turning_point", turning))
    adaptive_radius = nonlinear_tet4_model(method="arc_length")
    adaptive_radius.analysis.parameters.update(
        {
            "arc_length_stop_mode": "max_steps",
            "max_arc_steps": 6,
            "arc_length_allow_load_factor_turning": True,
            "arc_length_load_factor_limit": 5.0,
            "arc_length_radius": 0.05,
            "max_arc_length_radius": 0.2,
            "min_arc_length_radius": 1.0e-6,
            "adaptive_arc_length": True,
            "arc_length_growth_factor": 2.0,
            "arc_length_shrink_factor": 0.5,
            "arc_length_grow_below_iterations": 10,
            "arc_length_shrink_above_iterations": 50,
        }
    )
    cases.append(_result_record("arc_length_adaptive_radius", adaptive_radius))
    cases.append(_arc_reject_once_record())
    with TemporaryDirectory() as directory:
        checkpoint_model = nonlinear_tet4_model(method="arc_length")
        checkpoint_model.analysis.parameters.update(
            {
                "max_arc_steps": 12,
                "checkpoint_path": str(Path(directory) / "arc.npz"),
                "checkpoint_interval": 1,
                "checkpoint_keep_steps": True,
            }
        )
        cases.append(_result_record("arc_length_checkpoint_compatible", checkpoint_model))
    return {
        "baseline_sha": source_sha,
        "scope": "WP01-D adaptive load-control and arc-length lifecycle baseline",
        "cases": cases,
        "failure_cases": [
            _adaptive_failure_record(False),
            _adaptive_failure_record(True),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("qualification/0_2_9/wp01_d_baseline.json"))
    parser.add_argument("--source-sha", default=BASELINE_SHA)
    args = parser.parse_args()
    payload = _jsonable(build_baseline(args.source_sha))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"baseline_sha": args.source_sha, "cases": [case["name"] for case in payload["cases"]]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
