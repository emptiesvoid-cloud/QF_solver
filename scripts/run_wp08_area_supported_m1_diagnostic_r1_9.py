"""Freeze and run the prospective WP08 area-supported R1.9 contact campaign.

This experimental runner cannot award WP08 points; M1, M2, and M3 remain gated,
independent references, or replays.  Each M1 load case runs in its own child
process; all code inputs are source-hash-bound before the first solve.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.prepare_wp08_area_supported_benchmark import (  # noqa: E402
    FRICTION_COEFFICIENT,
    HEIGHT_M,
    INITIAL_GAP_M,
    LENGTH_M,
    MESH_LEVELS,
    NORMAL_RESULTANT_N,
    POISSON_RATIO,
    SLIP_TANGENTIAL_RESULTANT_N,
    STICK_TANGENTIAL_RESULTANT_N,
    TANGENTIAL_STIFFNESS_DENSITY_N_PER_M3,
    WIDTH_M,
    MeshLevel,
    _surface_geometry,
)

POLICY_DIGEST_CONTEXT = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"
ARTIFACT_ID = "QF-029-WP08-AREA-SUPPORTED-CONTACT-DIAGNOSTIC-R1.9"
CONTRACT_DOCUMENT_REL = Path(
    "docs/verification/0_2_9/wp08-area-supported-contact-requalification-r1-9.md"
)
M1_LOAD_STEPS = [
    {"normal_factor": 0.25, "tangential_factor": 0.0},
    {"normal_factor": 0.50, "tangential_factor": 0.0},
    {"normal_factor": 0.75, "tangential_factor": 0.0},
    {"normal_factor": 1.00, "tangential_factor": 0.0},
    {"normal_factor": 1.00, "tangential_factor": 0.25},
    {"normal_factor": 1.00, "tangential_factor": 0.50},
    {"normal_factor": 1.00, "tangential_factor": 0.75},
    {"normal_factor": 1.00, "tangential_factor": 1.00},
]


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_safe(value: Any) -> Any:
    """Convert NumPy scalars/arrays recursively before strict JSON writing."""
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported value in strict diagnostic JSON: {type(value).__name__}")


def _write_json(path: Path, value: object, *, exclusive: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8", newline="\n") as stream:
        json.dump(_json_safe(value), stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _source_inventory() -> dict[str, str]:
    files = {
        path
        for folder in (ROOT / "src", ROOT / "scripts")
        for path in folder.rglob("*.py")
        if "__pycache__" not in path.parts
    }
    files.update(
        ROOT / relative
        for relative in (
            "tests/unit/test_contact_sparse_stick_assembly.py",
            "tests/unit/test_contact_surface_tangential_stiffness.py",
            "tests/unit/test_frictional_contact.py",
            "tests/unit/test_frictional_contact_structural_limit.py",
            "tests/unit/test_contact_surface_lumped_penalty.py",
            "tests/unit/test_wp08d_mixed_open_active_slip.py",
            "tests/unit/test_wp08d_active_set_remediation.py",
            "tests/unit/test_wp08b_frictional_identities_rollback.py",
            "tests/unit/test_wp08c_friction_tangent_dissipation.py",
            "tests/unit/test_wp08_area_supported_m1_runner.py",
            "tests/unit/test_wp08_area_supported_m2_m3_runner.py",
            "tests/unit/test_wp08_area_supported_m1_runner_r1_9.py",
            "tests/unit/test_wp08_area_supported_m2_m3_runner_r1_9.py",
            "tests/unit/test_wp08_area_supported_benchmark_preflight.py",
            "tests/unit/test_frictional_contact_family_survey.py",
            "tests/unit/test_wp08_area_supported_m4_runner.py",
            "tests/unit/test_wp08d_phase1_runner.py",
            "tests/unit/test_wp08d_independent_reference.py",
        )
    )
    if any(not path.is_file() for path in files):
        raise FileNotFoundError("A source or targeted-test file is missing from the R1.9 freeze inventory.")
    return {path.relative_to(ROOT).as_posix(): _sha(path) for path in sorted(files)}


def _git_state() -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

    return {
        "branch": git("branch", "--show-current"),
        "head": git("rev-parse", "HEAD"),
        "porcelain_status": git("status", "--porcelain"),
    }


def _level(name: str) -> MeshLevel:
    for level in MESH_LEVELS:
        if level.name == name:
            return level
    raise ValueError(f"Unknown mesh level: {name}")


def _raw_contact_arrays(
    *,
    body: np.ndarray,
    master: np.ndarray,
    slave_nodes: tuple[int, ...],
    active_nodes: list[int],
    area_by_node: Mapping[int, float],
    rows: list[dict[str, Any]],
    displacement: np.ndarray,
    equilibrium: Mapping[str, Any],
) -> dict[str, np.ndarray]:
    """Serialize M1 arrays using the same comparison schema as M2/M3."""
    required_equilibrium = (
        "reaction_resultant",
        "reaction_moment_about_origin",
        "force_balance_relative_error",
        "moment_balance_relative_error",
    )
    missing = [name for name in required_equilibrium if name not in equilibrium]
    if missing:
        raise ValueError(f"M1 audit is missing required equilibrium fields: {missing}")
    pressure = np.asarray([float(row.get("pressure", 0.0)) for row in rows], dtype=float)
    normal = np.asarray([row.get("normal", [0.0, 0.0, 0.0]) for row in rows], dtype=float).reshape((-1, 3))
    tangent_local = np.asarray([row.get("tangential_force", [0.0, 0.0]) for row in rows], dtype=float).reshape((-1, 2))
    tangent_global: np.ndarray = np.zeros((len(rows), 3), dtype=float)
    for index, row in enumerate(rows):
        tangent_global[index] = (
            tangent_local[index, 0] * np.asarray(row.get("tangent_one", [0.0, 0.0, 0.0]), dtype=float)
            + tangent_local[index, 1] * np.asarray(row.get("tangent_two", [0.0, 0.0, 0.0]), dtype=float)
        )
    slave_ids = np.asarray([int(row.get("slave_node", -1)) for row in rows], dtype=np.int64)
    return {
        "displacement": np.asarray(displacement, dtype=float),
        "node_coordinates": np.vstack((np.asarray(body, dtype=float), np.asarray(master, dtype=float))),
        "body_node_count": np.asarray([len(body)], dtype=np.int64),
        "slave_nodes": np.asarray(slave_nodes, dtype=np.int64),
        "contact_pressure": pressure,
        "contact_gap": np.asarray([float(row.get("gap", 0.0)) for row in rows], dtype=float),
        "contact_states": np.asarray([str(row.get("tangential_state", "unknown")) for row in rows], dtype=str),
        "contact_tangential_force": tangent_local,
        "contact_slave_nodes": slave_ids,
        "contact_active": np.asarray([bool(row.get("active", False)) for row in rows], dtype=bool),
        "contact_normal": normal,
        "contact_normal_force": -pressure[:, None] * normal,
        "contact_tangential_force_local": tangent_local,
        "contact_tangential_force_global": tangent_global,
        "contact_reference_area": np.asarray(
            [
                float(row.get("reference_slave_area", area_by_node.get(int(node), 0.0)))
                for row, node in zip(rows, slave_ids, strict=True)
            ],
            dtype=float,
        ),
        "active_slave_nodes": np.asarray(active_nodes, dtype=np.int64),
        "reference_slave_area": np.asarray([area_by_node[node] for node in slave_nodes], dtype=float),
        "reaction_resultant": np.asarray(equilibrium["reaction_resultant"], dtype=float),
        "reaction_moment": np.asarray(equilibrium["reaction_moment_about_origin"], dtype=float),
        "force_balance_relative_error": np.asarray([equilibrium["force_balance_relative_error"]], dtype=float),
        "moment_balance_relative_error": np.asarray([equilibrium["moment_balance_relative_error"]], dtype=float),
    }


def build_m1_model(case: str) -> Any:
    """Build the frozen candidate M1 model without solving it."""
    if case not in {"stick_target", "slip_target"}:
        raise ValueError("case must be stick_target or slip_target")
    from solveur.core.model import FiniteElementModel
    from solveur.contact.measures import reference_surface_areas

    level = _level("M1")
    body, tets, slave_faces, slave_nodes, fixed_nodes = _surface_geometry(level)
    body_count = len(body)
    master = np.asarray(
        [
            [LENGTH_M + INITIAL_GAP_M, 0.0, 0.0],
            [LENGTH_M + INITIAL_GAP_M, 0.0, HEIGHT_M],
            [LENGTH_M + INITIAL_GAP_M, WIDTH_M, HEIGHT_M],
            [LENGTH_M + INITIAL_GAP_M, WIDTH_M, 0.0],
        ],
        dtype=float,
    )
    nodes = np.vstack((body, master))
    master_ids = tuple(range(body_count, body_count + 4))
    master_faces = ((master_ids[0], master_ids[1], master_ids[2]), (master_ids[0], master_ids[2], master_ids[3]))
    areas = reference_surface_areas(nodes, slave_faces)
    patch_area = sum(areas.values())
    tangential_resultant = (
        STICK_TANGENTIAL_RESULTANT_N if case == "stick_target" else SLIP_TANGENTIAL_RESULTANT_N
    )
    loads: list[dict[str, Any]] = []
    load_kinds: list[str] = []
    for node in slave_nodes:
        share = areas[node] / patch_area
        loads.append({"node": node, "dof": "UX", "value": NORMAL_RESULTANT_N * share})
        load_kinds.append("normal")
        loads.append({"node": node, "dof": "UY", "value": tangential_resultant * share})
        load_kinds.append("tangential")
    history = [
        [
            float(
                step["normal_factor"]
                if kind == "normal"
                else step["tangential_factor"]
            )
            for kind in load_kinds
        ]
        for step in M1_LOAD_STEPS
    ]
    fixed_nodes_all = tuple(fixed_nodes) + master_ids
    contacts = [
        {
            "name": "wp08_area_supported_fixed_search",
            "slave_nodes": list(slave_nodes),
            "slave_patch_faces": [list(face) for face in slave_faces],
            "master_nodes": list(master_faces[0]),
            "master_faces": [list(face) for face in master_faces],
            "friction_coefficient": FRICTION_COEFFICIENT,
            "tangential_stiffness_mode": "surface",
            "tangential_stiffness": TANGENTIAL_STIFFNESS_DENSITY_N_PER_M3,
            "gap_tolerance": 1.0e-10,
        }
    ]
    elements = [{"type": "TET4", "nodes": list(tet), "material": "elastic"} for tet in tets]
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=elements,
        materials={"elastic": {"type": "isotropic_3d", "E": 1.0e6, "nu": POISSON_RATIO}},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes_all],
        loads=loads,
        contacts=contacts,
        analysis={
            "type": "linear_static",
            "method": "direct",
            "contact_max_iterations": 25,
            "contact_friction_tolerance": 1.0e-9,
            "contact_load_history": history,
            "contact_search_mode": "initial",
            "contact_emit_step_checkpoints": True,
        },
    )


def _contract(
    output: Path, *, owner_authorized: bool = False
) -> tuple[dict[str, Any], dict[str, str], str]:
    inventory = _source_inventory()
    source_digest = _canonical_sha(inventory)
    _write_json(output / "source_file_manifest.json", inventory)
    state = _git_state()
    contract_document = ROOT / CONTRACT_DOCUMENT_REL
    if not contract_document.is_file():
        raise FileNotFoundError(f"R1.9 contract document is missing: {contract_document}")
    contract = {
        "schema": "qf.wp08.area_supported_contact_diagnostic_contract.v1",
        "artifact_id": ARTIFACT_ID,
        "status": "FROZEN_EXPERIMENTAL_M1_M2_M3_DIAGNOSTIC_NOT_FORMAL",
        "contract_document_path": CONTRACT_DOCUMENT_REL.as_posix(),
        "contract_document_sha256": _sha(contract_document),
        "frozen_utc": _utc(),
        "git": state,
        "source_manifest": "source_file_manifest.json",
        "source_file_count": len(inventory),
        "source_bundle_sha256": source_digest,
        "policy_digest_context_only": POLICY_DIGEST_CONTEXT,
        "governing_policy_enforced": False,
        "owner_authorization": {
            "execution_authorized": owner_authorized,
            "authorization_required_for_freeze": True,
            "recorded_from": (
                "Explicit Owner authorization recorded at R1.9 freeze time."
                if owner_authorized
                else "PENDING; no R1.9 structural execution is authorized by this draft."
            ),
            "scope": "One serial R1.9 M1/M2/M3 diagnostic campaign; no formal qualification or point award.",
        },
        "scope": "Serial stick-target and slip-target diagnostic solves on M1, M2, then M3; stop after any failed gate, with M3 only if both M2 cases pass.",
        "formal_wp08_qualification": False,
        "points_awarded": False,
        "production_mechanics_changed_for_this_benchmark": True,
        "contact_mechanics_revision": "R1.7 post-root tangential reclassification and zero-pressure-open semantics; R1.8 bounded normal-complementarity correction; R1.9 per-contact scaled residual convergence and deterministic refinement",
        "solver_implementation_revision": "support-local sparse rank-one stick assembly; frozen stick matrix and analytic Jacobian for slip roots; deterministic seed tried before the unchanged enumeration cap; coupled-root complementarity proposals update the normal active set with cycle detection; coupled projection convergence is gated by the maximum per-contact normalized residual, with existing semismooth/globalized refinement used when needed",
        "implementation_scope": "algorithmic contact correction only; R1.8 reuses the existing 25-iteration active-set limit; R1.9 replaces aggregate root stopping with the maximum per-contact scaled residual and refines under the unchanged 1e-9 tolerance; geometry, mesh, material, loads, boundary conditions, contact area weights, kappa, tolerances, thresholds, and fallback policy unchanged",
        "previous_revision": {
            "revision": "R1.8",
            "status": "M1_M2_PASS_M3_SLIP_FAIL_CLOSED",
            "m1_contract_sha256": "36a22027493c54c16c660bf9d1ef2ef6cac8f4fcc185334dacacf3e8416ff0b3",
            "m1_source_bundle_sha256": "87e943b825b3751312a5d247b2ddfe7e3ff66b5af6bd317cee1f77f4cb6a5527",
            "m1_final_sha256": "1016530a89b471a3a52bedca4499ec71a378407e779e7d906e36b185fa67230d",
            "m2_m3_contract_sha256": "9a445acdfaea7a4edea709fc7458f791a0fa7a153e57badac0fa8b8c38786104",
            "m2_m3_freeze_binding_canonical_sha256": "b5044f1354d63927c57bc8ad815285d9c099163e2d8f6b129c3e0029ccd76fe9",
            "m2_m3_freeze_binding_file_sha256": "a8215839e20d92857b0f88f3e0ff69ba691ce69766d8ea3bd079ffba9c7fd47f",
            "m2_m3_execution_binding_canonical_sha256": "eb10fac231a05cb1f299ba18f526963f0457e672dcda0156ee1e4c31a784eae9",
            "m2_m3_execution_binding_file_sha256": "b9df0278cbdbc921c31ed69d4224297be70d43c2f5d7adb7b1ae01618ad11b74",
            "m2_m3_runner_sha256": "508e599d6b7f80480e7dd487220841c16ae2d95aeb6b27a6fca97d6fcf3f0220",
            "m2_m3_final_sha256": "0e39832b0ec6df63d49a74bc69fdd552ea29fd05482af903faa53dc7e271786a",
            "m3_slip_failure_sha256": "f2eb4698778bf01e002425cbed873a078e122bba0dbcbe4bccb5577a493446b0",
            "m3_slip_failure_cause": "M3 slip step 8: the coupled candidate's contact 1 slip-cone alignment residual was 2.0834372780912926e-8 N against a 1.1809752086004155e-8 N admissibility limit; aggregate root scaling accepted a state later rejected by the per-contact physical gate",
            "preserved_without_rewrite": True,
        },
        "historical_revision_r1_7": {
            "contract_sha256": "45485b3107eb62d0e10e14cf56279dbafb76e37f76c29bdc9cc62dc583a00e09",
            "m2_m3_contract_sha256": "71d0e3d3e37423b6a918a431b152aa8e2493be07d5bbdeb22de61907d6269916",
            "execution_binding_sha256": "87ded663cc20b8aade614fa908aa1c051f015813a5a10bc84c68479be0ecbf0d",
            "final_sha256": "6c6ef2679909926c2aea5187e8fc01fc9d0b98259864e80ed8f83eee183b9b80",
            "source_bundle_sha256": "e32b6a3c969a1c81404cbde63f3678ce3f2d8c33f750ba09ccc43678d3108797",
            "m3_slip_failure_sha256": "04b2a9d1d47f60270af7ccd8cf72cb87e59df58865a655e488c474b6756679f9",
            "m3_slip_failure_cause": "step 8: direct set cycled; active-slip scaled residual 1.500134741e-09 exceeded 1e-9; coupled seed was attempted but rejected because contact 3 had negative gap while omitted from the normal active set",
            "preserved_without_rewrite": True,
        },
        "historical_revision_r1_6": {
            "contract_sha256": "64915350e85c55b9920ff46916cade62bbe27f56ee1cbffdcd2cb59f74412526",
            "final_sha256": "693ec8bc0c94466c39daab38f01f608bb5f674caa4f61164d613ff522abbeb1e",
            "source_bundle_sha256": "1a9614b3669d37f83cb4e6dfd2c91f4a45df3d8c89496399cc6f8f9ac736f142",
            "m3_slip_failure_sha256": "af9594aaf3434b63e129bcdce623a12983ced1c028dd4124bcfd0b21e87daee7",
            "preserved_without_rewrite": True,
        },
        "thresholds_changed": False,
        "geometry_m": {"length_x": LENGTH_M, "width_y": WIDTH_M, "height_z": HEIGHT_M},
        "material": {"type": "isotropic_linear_elastic", "young_modulus_Pa": 1.0e6, "poisson_ratio": POISSON_RATIO},
        "boundary_conditions": {
            "fixed_face": "x=0, all body face nodes, UX/UY/UZ",
            "master_nodes": "all four rigid metadata nodes fixed in UX/UY/UZ",
            "slave_face": "complete x=2 body boundary face; no slave node is fixed",
        },
        "contact": {
            "normal_route": "existing fixed-search node-to-triangle",
            "master_plane_x_m": LENGTH_M + INITIAL_GAP_M,
            "initial_gap_m": INITIAL_GAP_M,
            "master_normal": [-1.0, 0.0, 0.0],
            "friction_coefficient": FRICTION_COEFFICIENT,
            "tangential_law": "reference T3 tributary area, K_i=kappa*A_i, no redistribution",
            "kappa_N_per_m3": TANGENTIAL_STIFFNESS_DENSITY_N_PER_M3,
            "search_mode": "initial",
        },
        "mesh": {"level": "M1", "subdivision": {"nx": 2, "ny": 1, "nz": 1}, "element": "TET4"},
        "load_path": {
            "steps": M1_LOAD_STEPS,
            "normal_resultant_N": [NORMAL_RESULTANT_N, 0.0, 0.0],
            "tangential_direction": [0.0, 1.0, 0.0],
            "normal_ramp_then_tangential_ramp": True,
            "cases": {
                "stick_target": {"tangential_resultant_N": STICK_TANGENTIAL_RESULTANT_N},
                "slip_target": {"tangential_resultant_N": SLIP_TANGENTIAL_RESULTANT_N},
            },
        },
        "predeclared_m1_diagnostic_gates": {
            "both_solves_converged": True,
            "accepted_load_steps_per_case": 8,
            "terminal_active_slave_nodes": "all 4 M1 slave nodes",
            "terminal_active_support_affine_rank": 2,
            "terminal_active_area_fraction": 1.0,
            "stick_target_terminal_states": "all stick",
            "slip_target_terminal_states": "all slip",
            "failure_action": "record evidence and stop; do not run M2/M3",
        },
        "predeclared_m2_m3_execution_gates": {
            "all_cases_sequential": True,
            "both_m1_cases_required_before_m2": True,
            "both_m2_cases_required_before_m3": True,
            "accepted_load_steps_per_case": 8,
            "active_support_affine_rank": 2,
            "terminal_stick_or_slip_state_must_match_case": True,
            "mesh_refinement_classification": "DESCRIPTIVE_ONLY_NO_FROZEN_CONVERGENCE_THRESHOLD",
            "failure_action": "preserve artifacts and stop downstream cases; no retry, no parameter change",
        },
        "reference_and_replay": "NOT_RUN_IN_THIS_DIAGNOSTIC_CAMPAIGN; no independent global FEM reference or formal replay claim",
        "m2_m3_authorized": owner_authorized,
        "full_test_suite": False,
    }
    return contract, inventory, source_digest


def freeze(output: Path, *, owner_authorized: bool = False) -> int:
    output = output.resolve()
    if not owner_authorized:
        raise PermissionError("R1.9 freeze requires explicit Owner authorization for this new mechanics revision.")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite frozen evidence directory: {output}")
    output.mkdir(parents=True, exist_ok=False)
    contract, inventory, source_digest = _contract(output, owner_authorized=owner_authorized)
    contract_path = output / "contract.json"
    _write_json(contract_path, contract)
    binding = {
        "artifact_id": ARTIFACT_ID,
        "frozen_utc": contract["frozen_utc"],
        "contract_path": "contract.json",
        "contract_sha256": _sha(contract_path),
        "source_manifest_path": "source_file_manifest.json",
        "source_manifest_canonical_sha256": _canonical_sha(inventory),
        "source_bundle_sha256": source_digest,
        "git": contract["git"],
        "status": "FROZEN_R1_9_CONTACT_CAMPAIGN_DIAGNOSTIC",
    }
    _write_json(output / "freeze_binding.json", binding)
    print(json.dumps(binding, indent=2, sort_keys=True))
    return 0


def _verify_frozen(output: Path) -> tuple[dict[str, Any], str]:
    contract_path = output / "contract.json"
    binding_path = output / "freeze_binding.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    if _sha(contract_path) != binding.get("contract_sha256"):
        raise RuntimeError("Frozen diagnostic contract hash mismatch.")
    inventory_path = output / str(binding["source_manifest_path"])
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    source_digest = _canonical_sha(inventory)
    if source_digest != binding.get("source_bundle_sha256") or inventory != _source_inventory():
        raise RuntimeError("Frozen source tree differs from its source manifest.")
    return contract, str(binding["contract_sha256"])


def _worker(case: str, output: Path, expected_contract_sha: str) -> int:
    output = output.resolve()
    contract, contract_sha = _verify_frozen(output)
    if contract_sha != expected_contract_sha:
        raise RuntimeError("Worker contract SHA does not match frozen binding.")
    case_dir = output / "M1" / case
    if case_dir.exists():
        raise FileExistsError(f"Refusing to overwrite diagnostic result: {case_dir}")
    case_dir.mkdir(parents=True, exist_ok=False)
    from solveur.api.public import solve_model
    from solveur.core.telemetry.jsonl import JsonlSink
    from solveur.core.telemetry.observer import TelemetryEmitter
    from solveur.contact.measures import reference_surface_areas

    body, tets, slave_faces, slave_nodes, _ = _surface_geometry(_level("M1"))
    area_by_node = reference_surface_areas(body, slave_faces)
    patch_area = sum(area_by_node.values())
    telemetry_path = case_dir / "telemetry.jsonl"
    sink = JsonlSink(telemetry_path, fsync=True, sink_identifier="wp08_area_m1")
    telemetry = TelemetryEmitter(
        analysis_id=f"{ARTIFACT_ID}-{case}",
        analysis_type="linear_static",
        route="linear_static",
        sinks=(sink,),
        metadata={
            "campaign_contract_sha256": contract_sha,
            "source_bundle_sha256": contract["source_bundle_sha256"],
            "mesh": "M1",
            "case": case,
        },
    )
    started_perf = perf_counter()
    result_path = case_dir / "result.json"
    try:
        model = build_m1_model(case)
        result = solve_model(model, enforce_policy=False, telemetry=telemetry)
        elapsed = perf_counter() - started_perf
        payload = result.to_dict()
        contact = payload.get("solver", {}).get("contact", {})
        rows = contact.get("contacts", []) if isinstance(contact, dict) else []
        active_rows = [row for row in rows if bool(row.get("active", False))]
        active_nodes = sorted({int(row["slave_node"]) for row in active_rows if "slave_node" in row})
        active_states = sorted({str(row.get("tangential_state", "unknown")) for row in active_rows})
        active_area = sum(area_by_node.get(node, 0.0) for node in active_nodes)
        active_coordinates = body[active_nodes] if active_nodes else np.empty((0, 3), dtype=float)
        support_rank = (
            int(np.linalg.matrix_rank(active_coordinates - np.mean(active_coordinates, axis=0)))
            if len(active_nodes) >= 2
            else 0
        )
        load_steps = contact.get("load_steps", []) if isinstance(contact, dict) else []
        converged = bool(payload.get("solver", {}).get("converged", False))
        expected_state = "stick" if case == "stick_target" else "slip"
        gates = {
            "solver_converged": converged,
            "all_8_load_steps_recorded": len(load_steps) == 8,
            "all_4_slave_nodes_active": len(active_nodes) == len(slave_nodes),
            "active_support_rank_2": support_rank == 2,
            "active_area_fraction_1": bool(
                np.isclose(active_area / patch_area, 1.0, rtol=0.0, atol=1.0e-12)
            ),
            "expected_terminal_tangential_state": active_states == [expected_state],
        }
        diagnostic = {
            "case": case,
            "status": "PASS_DIAGNOSTIC_GATES" if all(gates.values()) else "FAIL_CLOSED_DIAGNOSTIC_GATE",
            "elapsed_seconds": elapsed,
            "solver_converged": converged,
            "solver_residual_norm": payload.get("solver", {}).get("residual_norm"),
            "load_step_count": len(load_steps),
            "active_slave_nodes": active_nodes,
            "active_slave_node_count": len(active_nodes),
            "active_support_affine_rank": support_rank,
            "active_area_m2": active_area,
            "active_area_fraction": active_area / patch_area,
            "terminal_active_states": active_states,
            "expected_terminal_state": expected_state,
            "fallback_count": None,
            "fallback_count_note": "Not exposed in this result schema; no zero-fallback claim.",
            "gates": gates,
        }
        payload.update(
            {
                "artifact_id": ARTIFACT_ID,
                "case": case,
                "execution_kind": "EXPERIMENTAL_M1_M2_M3_CONTACT_DIAGNOSTIC_R1_9",
                "formal_wp08_qualification": False,
                "points_awarded": False,
                "contract_sha256": contract_sha,
                "source_bundle_sha256": contract["source_bundle_sha256"],
                "policy_digest_context_only": POLICY_DIGEST_CONTEXT,
                "diagnostic": diagnostic,
            }
        )
        _write_json(result_path, payload)
        master = np.asarray(
            [
                [LENGTH_M + INITIAL_GAP_M, 0.0, 0.0],
                [LENGTH_M + INITIAL_GAP_M, 0.0, HEIGHT_M],
                [LENGTH_M + INITIAL_GAP_M, WIDTH_M, HEIGHT_M],
                [LENGTH_M + INITIAL_GAP_M, WIDTH_M, 0.0],
            ],
            dtype=float,
        )
        equilibrium = payload.get("audit", {}).get("equilibrium", {})
        raw_arrays = _raw_contact_arrays(
            body=body,
            master=master,
            slave_nodes=tuple(slave_nodes),
            active_nodes=active_nodes,
            area_by_node=area_by_node,
            rows=rows,
            displacement=np.asarray(result.displacements, dtype=float),
            equilibrium=equilibrium,
        )
        np.savez_compressed(
            case_dir / "raw.npz",
            displacement=raw_arrays["displacement"],
            node_coordinates=raw_arrays["node_coordinates"],
            body_node_count=raw_arrays["body_node_count"],
            slave_nodes=raw_arrays["slave_nodes"],
            contact_pressure=raw_arrays["contact_pressure"],
            contact_gap=raw_arrays["contact_gap"],
            contact_states=raw_arrays["contact_states"],
            contact_tangential_force=raw_arrays["contact_tangential_force"],
            contact_slave_nodes=raw_arrays["contact_slave_nodes"],
            contact_active=raw_arrays["contact_active"],
            contact_normal=raw_arrays["contact_normal"],
            contact_normal_force=raw_arrays["contact_normal_force"],
            contact_tangential_force_local=raw_arrays["contact_tangential_force_local"],
            contact_tangential_force_global=raw_arrays["contact_tangential_force_global"],
            contact_reference_area=raw_arrays["contact_reference_area"],
            active_slave_nodes=raw_arrays["active_slave_nodes"],
            reference_slave_area=raw_arrays["reference_slave_area"],
            reaction_resultant=raw_arrays["reaction_resultant"],
            reaction_moment=raw_arrays["reaction_moment"],
            force_balance_relative_error=raw_arrays["force_balance_relative_error"],
            moment_balance_relative_error=raw_arrays["moment_balance_relative_error"],
        )
        _write_json(case_dir / "progress.json", {"status": "COMPLETED", **diagnostic})
        return 0 if all(gates.values()) else 3
    except BaseException as error:
        reason = getattr(error, "reason", None)
        _write_json(
            case_dir / "failure.json",
            {
                "case": case,
                "error_type": type(error).__name__,
                "error": str(error),
                "reason": getattr(reason, "value", reason),
                "diagnostics": getattr(error, "diagnostics", None),
                "contract_sha256": contract_sha,
            },
        )
        raise
    finally:
        telemetry.close()


def _invoke(output: Path, case: str, contract_sha: str) -> dict[str, Any]:
    logs = output / "_process_logs"
    logs.mkdir(exist_ok=True)
    stdout_path = logs / f"{case}.stdout.log"
    stderr_path = logs / f"{case}.stderr.log"
    command = [
        sys.executable,
        "-B",
        str(Path(__file__).resolve()),
        "--worker",
        "--output-root",
        str(output),
        "--case",
        case,
        "--contract-sha256",
        contract_sha,
    ]
    started = _utc()
    child_started = perf_counter()
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        child = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr, text=False)
        exit_code = child.wait()
    record = {
        "case": case,
        "execution_kind": "EXPERIMENTAL_M1_M2_M3_CONTACT_DIAGNOSTIC_R1_9",
        "pid": child.pid,
        "command": command,
        "started_utc": started,
        "ended_utc": _utc(),
        "elapsed_seconds": perf_counter() - child_started,
        "exit_code": exit_code,
        "contract_sha256": contract_sha,
        "stdout_path": stdout_path.relative_to(output).as_posix(),
        "stdout_sha256": _sha(stdout_path),
        "stderr_path": stderr_path.relative_to(output).as_posix(),
        "stderr_sha256": _sha(stderr_path),
    }
    _write_json(logs / f"{case}.process.json", record)
    return record


def execute_m1(output: Path) -> int:
    output = output.resolve()
    contract, contract_sha = _verify_frozen(output)
    if contract.get("m2_m3_authorized") is not True:
        raise RuntimeError("M2/M3 execution is not authorized by the frozen campaign contract.")
    if (output / "M1").exists() or (output / "_process_logs").exists():
        raise FileExistsError("M1 outputs already exist; refusing to overwrite or rerun.")
    records: list[dict[str, Any]] = []
    case_status: dict[str, str] = {}
    for case in ("stick_target", "slip_target"):
        if case == "slip_target" and case_status.get("stick_target") != "PASS_DIAGNOSTIC_GATES":
            case_status[case] = "NOT_RUN_PREVIOUS_M1_CASE_FAILED"
            _write_json(
                output / "progress.json",
                {
                    "status": "RUNNING",
                    "completed_cases": list(case_status),
                    "case_status": case_status,
                    "processes": records,
                    "m2_m3_started": False,
                },
                exclusive=False,
            )
            continue
        record = _invoke(output, case, contract_sha)
        records.append(record)
        result_path = output / "M1" / case / "result.json"
        if record["exit_code"] == 0 and result_path.is_file():
            result = json.loads(result_path.read_text(encoding="utf-8"))
            case_status[case] = str(result.get("diagnostic", {}).get("status", "UNKNOWN"))
        else:
            case_status[case] = "FAIL_CLOSED_PROCESS_OR_RESULT"
        _write_json(
            output / "progress.json",
            {
                "status": "RUNNING",
                "completed_cases": list(case_status),
                "case_status": case_status,
                "processes": records,
                "m2_m3_started": False,
            },
            exclusive=False,
        )
    all_pass = all(value == "PASS_DIAGNOSTIC_GATES" for value in case_status.values())
    final = {
        "artifact_id": ARTIFACT_ID,
        "status": "M1_DIAGNOSTIC_PASS_M2_M3_READY" if all_pass else "M1_DIAGNOSTIC_FAIL_CLOSED_M2_M3_STOPPED",
        "formal_wp08_qualification": False,
        "points_awarded": False,
        "contract_sha256": contract_sha,
        "source_bundle_sha256": contract["source_bundle_sha256"],
        "cases": case_status,
        "processes": records,
        "m2_m3_run": False,
        "m2_m3_authorized": True,
        "independent_reference_run": False,
        "replay_run": False,
        "full_test_suite_run": False,
    }
    _write_json(output / "final.json", final)
    _write_json(output / "progress.json", {"status": "COMPLETED", **final}, exclusive=False)
    print(json.dumps(final, indent=2, sort_keys=True))
    return 0 if all_pass else 3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--owner-authorized", choices=("yes", "no"), default="no")
    parser.add_argument("--execute-m1", action="store_true")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--case", choices=("stick_target", "slip_target"))
    parser.add_argument("--contract-sha256")
    args = parser.parse_args()
    if args.freeze:
        return freeze(args.output_root, owner_authorized=args.owner_authorized == "yes")
    if args.execute_m1:
        return execute_m1(args.output_root)
    if args.worker and args.case and args.contract_sha256:
        return _worker(args.case, args.output_root, args.contract_sha256)
    parser.error("Choose --freeze, --execute-m1, or a complete --worker invocation.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
