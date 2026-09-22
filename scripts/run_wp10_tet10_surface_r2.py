"""WP10 TET10 R2 production runner for M1/M2 evidence.

M3 is executed by a fresh invocation of this runner and checked by the
separate JSON-only replay verifier.  The independent reference intentionally
does not import this module or any production contact routine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from solveur.api import solve_model
from solveur.contact.entities import FrictionlessContact
from solveur.core.model import FiniteElementModel

from scripts import run_wp10_tet10_surface_m1 as base


CONTRACT = ROOT / "qualification" / "0_2_9" / "wp10_tet10_surface_r2_contract.json"
ELEMENT_TYPE = base.ELEMENT_TYPE
POLICY_DIGEST = base.POLICY_DIGEST
PLANE_X = 1.02
PENALTY = 1.0e6


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


def _model(cells: int, *, with_contact: bool) -> tuple[FiniteElementModel, int, dict[str, object]]:
    nodes, elements = base.mesh_refinement_mesh(ELEMENT_TYPE, cells)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    distributed_loads, surface_metadata = base._boundary_surface_loads(nodes, elements)
    loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
    if loaded_nodes.size == 0:
        raise RuntimeError("TET10 R2 model has no x=1 boundary nodes.")

    fixed = [
        {"node": int(node), "dofs": ["UX", "UY", "UZ"]}
        for node in fixed_nodes
    ]
    model_nodes = nodes
    slave = int(loaded_nodes[0])
    master_start: int | None = None
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
            {"type": ELEMENT_TYPE, "nodes": item, "material": "j2"}
            for item in elements
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
        distributed_loads=distributed_loads,
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "load_path": list(base.LOAD_PATH),
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
        if master_start is None:
            raise RuntimeError("Contact master nodes were not created.")
        master_face = (master_start, master_start + 1, master_start + 2)
        model.contacts.append(
            FrictionlessContact(
                name="wp10_tet10_r2_fixed_master_plane",
                slave_node=slave,
                master_nodes=master_face,
                master_faces=(master_face,),
            )
        )
        surface_metadata = {
            **surface_metadata,
            "contact": {
                "slave_node": slave,
                "master_nodes": list(master_face),
                "plane_x": PLANE_X,
                "initial_gap": float(model.contacts[0].geometry(model.nodes)[2]),
                "penalty": PENALTY,
                "finite_sliding": False,
            },
        }
    return model, slave, surface_metadata


def _compact_result(result: Any, model: FiniteElementModel, slave: int) -> dict[str, object]:
    compact = base._compact_result(result, model)
    payload = result.to_dict()
    raw_steps = payload["solver"]["steps"]
    compact_steps = cast(list[dict[str, object]], compact["steps"])
    for compact_step, raw_step in zip(compact_steps, raw_steps, strict=True):
        compact_step["contact_gaps"] = [
            float(value) for value in raw_step.get("contact_gaps", [])
        ]
        compact_step["contact_active_contacts"] = [
            int(value) for value in raw_step.get("contact_active_contacts", [])
        ]
    slave_dof = result.dofs.index(slave, "UX")
    return {
        **compact,
        "slave_node": slave,
        "slave_ux_dof": int(slave_dof),
        "displacements": np.asarray(result.displacements, dtype=float).tolist(),
    }


def _failure_record(mode: str, level: str, cells: int, exc: Exception) -> dict[str, object]:
    return {
        "case": mode,
        "mode": mode,
        "level": level,
        "cells_x": cells,
        "status": "FAIL_CLOSED",
        "execution_sha": _git_sha(),
        "runner_sha": json.loads(CONTRACT.read_text(encoding="utf-8"))["runner_sha"],
        "contract_sha256": _sha256(CONTRACT),
        "policy_digest": POLICY_DIGEST,
        "element_type": ELEMENT_TYPE,
        "error_type": type(exc).__name__,
        "error": str(exc),
        "m2_allowed": False,
        "m3_allowed": False,
    }


def run_case(mode: str, level: str, output: Path) -> dict[str, object]:
    mode = mode.upper()
    level = level.upper()
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("status") != "R2_EXECUTION_AUTHORIZED":
        raise RuntimeError("WP10 TET10 R2 contract is not execution-authorized.")
    if mode == "M1" and level not in base.LEVEL_CELLS:
        raise ValueError(f"Unsupported M1 level {level!r}.")
    if mode == "M2" and level != "H3":
        raise ValueError("WP10 TET10 R2 M2 is frozen on H3 only.")
    if mode not in {"M1", "M2"}:
        raise ValueError(f"Unsupported production mode {mode!r}.")
    cells = base.LEVEL_CELLS[level]
    try:
        model, slave, surface_metadata = _model(cells, with_contact=mode == "M2")
        load_metadata = base._load_metadata(model)
        result = solve_model(model, enforce_policy=False)
        compact = _compact_result(result, model, slave)
        record: dict[str, object] = {
            "case": mode,
            "mode": mode,
            "level": level,
            "cells_x": cells,
            "status": "PASS_CANDIDATE" if compact["status"] == "PASS" else "FAIL_CLOSED",
            "execution_sha": _git_sha(),
            "runner_sha": contract["runner_sha"],
            "contract_sha256": _sha256(CONTRACT),
            "policy_digest": POLICY_DIGEST,
            "element_type": ELEMENT_TYPE,
            "kinematics": "corotational_j2",
            "contact": "frictionless_penalty_initial_search" if mode == "M2" else "disabled",
            "frozen_inputs": {
                "load_path": list(base.LOAD_PATH),
                "reference_resultant": base.REFERENCE_RESULTANT,
                "plane_x": PLANE_X if mode == "M2" else None,
                "penalty": PENALTY if mode == "M2" else None,
                "finite_sliding": False,
            },
            "surface_load": surface_metadata,
            "load_balance": load_metadata,
            "result": compact,
            "fallback_count": int(cast(int, compact["fallback_count"])),
            "fallback_evidence": "per-step fallback_used field",
            "m3_allowed": bool(mode == "M2" and compact["status"] == "PASS"),
        }
    except Exception as exc:  # preserve every real failure
        record = _failure_record(mode, level, cells, exc)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("M1", "M2"), required=True)
    parser.add_argument("--level", choices=tuple(base.LEVEL_CELLS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = run_case(args.mode, args.level, args.output)
    return 0 if record["status"] == "PASS_CANDIDATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
