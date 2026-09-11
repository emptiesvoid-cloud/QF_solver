"""Archive the WP01-C numerical baseline before migration edits.

This runner is intentionally limited to the fixed load-control routes named by
WP01-C.  It records immutable, JSON-safe diagnostics at the baseline commit;
it is not a replacement for the targeted V&V tests.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix

from solveur.api import solve_model
from solveur.contact.entities import FrictionlessContact
from solveur.core.errors import NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.iteration import solve_full_newton
from solveur.core.nonlinear.state import deterministic_state_digest
from solveur.verification.robustness_nonlinear_solids import _refinement_model
from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh


def _j2_model() -> FiniteElementModel:
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


def _geometric_tet4_model() -> FiniteElementModel:
    nodes, elements = _structured_tet4_mesh(2, 1, 1, 2.0, 0.5, 0.5)
    fixed = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    tip = np.flatnonzero(np.isclose(nodes[:, 0], 2.0))
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "TET4", "nodes": row.tolist(), "material": "solid"} for row in elements],
        materials={"solid": {"type": "isotropic_3d", "E": 1.0e6, "nu": 0.3}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed],
        loads=[{"node": int(node), "dof": "UZ", "value": -1.0 / len(tip)} for node in tip],
        analysis={
            "type": "geometric_nonlinear_static",
            "method": "newton_raphson",
            "parameters": {"load_increments": 10},
        },
    )


BASELINE_SHA = "ad7ee6bd469aa770929fd7a1d46f56da5e9bba1a"


def _geometric_hex8_model() -> FiniteElementModel:
    nodes = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
        ]
    )
    fixed = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "HEX8", "nodes": list(range(8)), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1.0e6, "nu": 0.3}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed],
        loads=[{"node": int(node), "dof": "UX", "value": 1.0 / len(loaded)} for node in loaded],
        analysis={
            "type": "geometric_nonlinear_static",
            "method": "newton_raphson",
            "parameters": {"load_increments": 6},
        },
    )


def _geometric_penalty_contact_model() -> FiniteElementModel:
    nodes, elements = _structured_tet4_mesh(2, 1, 1, 2.0, 0.5, 0.5)
    fixed = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    tip = np.flatnonzero(np.isclose(nodes[:, 0], 2.0))
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "TET4", "nodes": row.tolist(), "material": "solid"} for row in elements],
        materials={"solid": {"type": "isotropic_3d", "E": 1.0e6, "nu": 0.3}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed],
        loads=[{"node": int(node), "dof": "UZ", "value": -1.0 / len(tip)} for node in tip],
        analysis={
            "type": "geometric_nonlinear_static",
            "method": "newton_raphson",
            "parameters": {
                "load_increments": 10,
                "contact_mode": "penalty",
                "contact_penalty": 1.0e6,
            },
        },
    )
    # The slave is initially separated from the x=0 master plane.  This is a
    # deliberate composition baseline, not a new contact qualification case.
    model.contacts.append(FrictionlessContact(slave_node=int(tip[0]), master_nodes=(0, 2, 1)))
    return model


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, csr_matrix):
        return {
            "shape": list(value.shape),
            "indptr": value.indptr.tolist(),
            "indices": value.indices.tolist(),
            "data": value.data.tolist(),
        }
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _case_record(name: str, model: FiniteElementModel) -> dict[str, Any]:
    result = solve_model(model, enforce_policy=False)
    payload = result.to_dict()
    solver = payload.get("solver", {})
    steps = list(solver.get("steps", solver.get("increments", [])))
    final_step = steps[-1] if steps else {}
    material_states = payload.get("material_states", [])
    contact_keys = (
        "contact_mode",
        "contact_search_mode",
        "contact_active_contacts",
        "contact_gaps",
        "contact_tangent_nnz",
        "contact_master_face_indices",
        "contact_finite_sliding",
        "contact_projection_clamped",
        "contact_closest_distances",
        "contact_projection_modes",
    )
    return {
        "name": name,
        "status": result.status,
        "analysis": result.analysis,
        "method": result.method,
        "displacement": payload["displacements"],
        "load_factor": final_step.get("load_factor", solver.get("load_path", [1.0])[-1]),
        "residual": {
            "norm": final_step.get("residual_norm", final_step.get("residual_final")),
            "relative": final_step.get("relative_residual"),
            "history": final_step.get("residual_history", []),
        },
        "equilibrium": payload.get("audit", {}).get("equilibrium", {}),
        "reactions": payload.get("audit", {}).get("vectors", []),
        "material_states": material_states,
        "material_state_digest": deterministic_state_digest(material_states),
        "contact_diagnostics": {
            key: final_step.get(key, solver.get(key))
            for key in contact_keys
            if final_step.get(key, solver.get(key)) is not None
        },
        "iteration_count": final_step.get("iterations", solver.get("newton_iterations")),
        "solver_step": final_step,
    }


class _SingularAssembly:
    ndof = 2

    def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
        return np.zeros(2), csr_matrix((2, 2))


def _failure_record() -> dict[str, Any]:
    try:
        solve_full_newton(
            _SingularAssembly(),
            np.array([1.0, 0.0]),
            np.array([1]),
            increments=1,
            tolerance=1.0e-8,
            max_iterations=3,
        )
    except NumericalConvergenceError as error:
        return {
            "name": "full_newton_singular_tangent",
            "status": "EXPECTED_FAILURE",
            "failure_reason": error.reason.value if error.reason is not None else None,
            "diagnostics": _jsonable(error.diagnostics),
        }
    raise RuntimeError("The baseline failure case unexpectedly converged.")


def build_baseline() -> dict[str, Any]:
    cases = [
        _case_record("small_strain_j2_nonlinear_static", _j2_model()),
        _case_record("geometric_nonlinear_tet4", _geometric_tet4_model()),
        _case_record("geometric_nonlinear_hex8", _geometric_hex8_model()),
    ]
    penalty = _refinement_model("TET4", 1)
    penalty.contacts.append(FrictionlessContact(slave_node=1, master_nodes=(0, 3, 4)))
    penalty.analysis = replace(
        penalty.analysis,
        parameters={**penalty.analysis.parameters, "contact_mode": "penalty", "contact_penalty": 1.0e6},
    )
    cases.append(_case_record("frictionless_penalty_contact_composition", penalty))
    cases.append(_case_record("geometric_penalty_contact_composition", _geometric_penalty_contact_model()))
    return {
        "baseline_sha": BASELINE_SHA,
        "scope": "WP01-C fixed load-control migration baseline",
        "cases": cases,
        "failure_cases": [_failure_record()],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("qualification/0_2_9/wp01_c_baseline.json"),
    )
    args = parser.parse_args()
    payload = _jsonable(build_baseline())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"baseline_sha": BASELINE_SHA, "cases": [case["name"] for case in payload["cases"]]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
