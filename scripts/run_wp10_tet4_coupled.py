"""WP10 extension runner for the bounded TET4 coupled route.

This is evidence tooling only.  It deliberately does not alter production
mechanics, thresholds, solver parameters, or fallback policy.  The reference
recomputes contact observables from the saved displacement result; it is not an
independent global FEM/Newton solve.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from solveur.api import solve_model
from solveur.contact.entities import FrictionlessContact
from solveur.core.model import FiniteElementModel
from solveur.verification.robustness_mesh import _refinement_model


CONTRACT = ROOT / "qualification" / "0_2_9" / "wp10_extension_contract.json"
POLICY_DIGEST = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"
ELEMENT_TYPE = "TET4"
PLANE_X = 1.02
PENALTY = 1.0e6
LOAD_PATH = (0.1, 0.2, 0.3, 0.5)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _model(with_contact: bool) -> tuple[FiniteElementModel, int]:
    base_model = _refinement_model(ELEMENT_TYPE, 1)
    nodes = np.asarray(base_model.nodes, dtype=float)
    loaded = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
    if loaded.size == 0:
        raise RuntimeError("TET4 extension model has no loaded x=1 nodes")
    fixed = [{"node": int(item.node), "dofs": list(item.dofs)} for item in base_model.fixed_dofs]
    model_nodes = nodes
    master_start = None
    if with_contact:
        master = np.asarray(
            [[PLANE_X, -0.5, -0.5], [PLANE_X, 1.5, -0.5], [PLANE_X, 0.5, 1.5]],
            dtype=float,
        )
        master_start = len(nodes)
        model_nodes = np.vstack((nodes, master))
        fixed.extend(
            {"node": master_start + index, "dofs": ["UX", "UY", "UZ"]}
            for index in range(3)
        )
    model = FiniteElementModel.from_raw(
        nodes=model_nodes.tolist(),
        elements=[
            {"type": item.type, "nodes": list(item.nodes), "material": item.material}
            for item in base_model.elements
        ],
        materials={
            "j2": {
                "type": "von_mises_elastoplastic_3d",
                "E": 1000.0,
                "nu": 0.3,
                "yield_stress": 0.02,
                "hardening_modulus": 10.0,
            }
        },
        fixed_dofs=fixed,
        loads=[{"node": int(node), "dof": "UX", "value": 0.5 / len(loaded)} for node in loaded],
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "load_path": list(LOAD_PATH),
            "max_iterations": 60,
            "tolerance": 1.0e-7,
            "kinematics": "corotational_j2",
            "corotational_max_local_strain": 0.05,
            "contact_mode": "penalty" if with_contact else "none",
            "contact_penalty": PENALTY,
            "contact_search_mode": "initial",
            "contact_finite_sliding": False,
            "contact_max_penetration": 0.05,
        },
    )
    if with_contact:
        assert master_start is not None
        model.contacts.append(
            FrictionlessContact(
                name="wp10_tet4_fixed_master_plane",
                slave_node=int(loaded[0]),
                master_nodes=(master_start, master_start + 1, master_start + 2),
                master_faces=((master_start, master_start + 1, master_start + 2),),
            )
        )
    return model, int(loaded[0])


def _compact_result(result: Any, model: FiniteElementModel, slave: int) -> dict[str, Any]:
    payload = result.to_dict()
    steps = payload["solver"]["steps"]
    slave_dof = result.dofs.index(slave, "UX")
    compact_steps = []
    for step in steps:
        compact_steps.append(
            {
                "step": int(step.get("step", len(compact_steps) + 1)),
                "load_factor": float(step.get("load_factor", 0.0)),
                "relative_residual": float(step.get("relative_residual", 0.0)),
                "iterations": int(step.get("iterations", 0)),
                "contact_gaps": [float(value) for value in step.get("contact_gaps", [])],
                "contact_active_contacts": [int(value) for value in step.get("contact_active_contacts", [])],
                "equivalent_plastic_strain_max": float(
                    step.get("equivalent_plastic_strain_max", 0.0)
                ),
            }
        )
    return {
        "status": str(result.status),
        "element_type": ELEMENT_TYPE,
        "node_count": int(model.node_count),
        "element_count": int(len(model.elements)),
        "dof_count": int(result.dofs.ndof),
        "slave_node": slave,
        "slave_ux_dof": int(slave_dof),
        "displacements": np.asarray(result.displacements, dtype=float).tolist(),
        "steps": compact_steps,
        "final_displacement_norm": float(np.linalg.norm(result.displacements)),
        "max_relative_residual": max(
            (row["relative_residual"] for row in compact_steps), default=0.0
        ),
        "max_peeq": max((row["equivalent_plastic_strain_max"] for row in compact_steps), default=0.0),
    }


def run_case(case: str, output: Path) -> dict[str, Any]:
    with_contact = case == "m2"
    model, slave = _model(with_contact)
    result = solve_model(model, enforce_policy=False)
    compact = _compact_result(result, model, slave)
    record = {
        "case": case.upper(),
        "status": "PASS_CANDIDATE" if compact["status"] == "PASS" else "FAIL_CLOSED",
        "source_sha": _git_sha(),
        "contract_sha256": _sha256(CONTRACT),
        "policy_digest": POLICY_DIGEST,
        "element_type": ELEMENT_TYPE,
        "kinematics": "corotational_j2",
        "contact": "frictionless_penalty_initial_search" if with_contact else "disabled",
        "frozen_inputs": {"load_path": list(LOAD_PATH), "penalty": PENALTY, "plane_x": PLANE_X},
        "result": compact,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def independent_reference(primary: Path, output: Path) -> dict[str, Any]:
    record = json.loads(primary.read_text(encoding="utf-8"))
    result = record["result"]
    dof = int(result["slave_ux_dof"])
    if record["case"] == "M1":
        rows = [
            {
                "step": step["step"],
                "recomputed_gap": 0.0,
                "production_gap": 0.0,
                "recomputed_penalty_force": 0.0,
                "gap_absolute_error": 0.0,
            }
            for step in result["steps"]
        ]
        passed = all(not step["contact_active_contacts"] for step in result["steps"])
    else:
        step = result["steps"][-1]
        displacement = float(result["displacements"][dof])
        gap = (1.0 + displacement) - PLANE_X
        production_gap = step["contact_gaps"][0] if step["contact_gaps"] else 0.0
        rows = [
            {
                "step": step["step"],
                "recomputed_gap": gap,
                "production_gap": production_gap,
                "recomputed_penalty_force": max(-gap, 0.0) * PENALTY,
                "gap_absolute_error": abs(gap - production_gap),
            }
        ]
        passed = bool(step["contact_active_contacts"]) and rows[0]["gap_absolute_error"] <= 1.0e-12
    reference = {
        "status": "PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION" if passed else "FAIL_CLOSED",
        "source_sha": record["source_sha"],
        "contract_sha256": record["contract_sha256"],
        "element_type": ELEMENT_TYPE,
        "independence": "contact gap and penalty recomputation; not an independent global FEM solve",
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(reference, indent=2), encoding="utf-8")
    return reference


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=("m1", "m2"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    record = run_case(args.case, args.output)
    if args.reference is not None:
        reference = independent_reference(args.output, args.reference)
        if reference["status"] != "PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION":
            return 2
    return 0 if record["status"] == "PASS_CANDIDATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
