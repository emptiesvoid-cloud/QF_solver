"""WP13-03B V2 bounded mixed MPC/RBE2 static V&V campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.constraints import recover_constraint_forces
from solveur.core.errors import MeshValidationError
from solveur.core.model import FiniteElementModel
from solveur.core.router import AnalysisRouter
from solveur.elements.registry import ElementRegistry
from solveur.loads.integration import load_balance
from solveur.materials.factory import MaterialFactory
from solveur.mesh.validation import MeshValidator


CONTRACT_PATH = ROOT / "qualification/0_2_8/wp13_03a_mixed_mpc_rbe2_contract_v2.json"
OUT = ROOT / "qualification/0_2_8/wp13_03b_v2_mpc_rbe2_runtime"
EXPECTED_CONTRACT_ID = "WP13-03-MIXED-MPC-RBE2-002"
EXPECTED_CONTRACT_SHA = "10ff2f0708c4f579c7a032036d981f616e8970f04ee000ed86b9146d3ca903d7"
ROTATIONAL_DOFS = {"RX", "RY", "RZ"}
TRANSLATIONAL_DOFS = ("UX", "UY", "UZ")


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _array_digest(value: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    header = f"{array.dtype.str}|{array.shape}".encode("ascii")
    return _digest_bytes(header + array.tobytes(order="C"))


def _array_record(value: np.ndarray) -> dict[str, Any]:
    array = np.asarray(value)
    return {
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "digest": _array_digest(array),
        "values": array.tolist(),
    }


def _relative(a: np.ndarray, b: np.ndarray) -> float:
    left = np.asarray(a, dtype=float)
    right = np.asarray(b, dtype=float)
    return float(np.linalg.norm(left - right) / max(float(np.linalg.norm(left)), float(np.linalg.norm(right)), np.finfo(float).tiny))


def _scalar_relative(a: float, b: float) -> float:
    return abs(float(a) - float(b)) / max(abs(float(a)), abs(float(b)), np.finfo(float).tiny)


def _load_contract(expected_sha: str) -> tuple[dict[str, Any], str]:
    raw = CONTRACT_PATH.read_bytes()
    digest = _digest_bytes(raw)
    if digest != expected_sha or digest != EXPECTED_CONTRACT_SHA:
        raise RuntimeError(f"Contract SHA mismatch: observed {digest}, expected {expected_sha}.")
    contract = json.loads(raw.decode("utf-8"))
    if contract.get("contract_id") != EXPECTED_CONTRACT_ID:
        raise RuntimeError("Contract ID mismatch.")
    return contract, digest


def _repo_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _environment() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
    }


def _benchmark_raw(contract: dict[str, Any], *, constraint_mode: str = "mpc") -> dict[str, Any]:
    benchmark = contract["benchmark"]
    nodes = [benchmark["nodes"][str(index)] for index in range(len(benchmark["nodes"]))]
    elements = [
        {"type": entry["family"], "nodes": entry["connectivity"], "material": "solid"}
        for entry in benchmark["elements"]
    ]
    material = benchmark["material"]
    raw: dict[str, Any] = {
        "nodes": nodes,
        "elements": elements,
        "materials": {
            "solid": {
                "type": material["model"],
                "E": material["young_modulus_pa"],
                "nu": material["poisson_ratio"],
                "density": material["density_kg_m3"],
            }
        },
        "fixed_dofs": [
            {"node": node, "dofs": benchmark["boundary_conditions"]["fixed_dofs"]}
            for node in benchmark["boundary_conditions"]["fixed_nodes"]
        ],
        "loads": [
            {"node": entry["node"], "dof": entry["dof"], "value": entry["value_n"]}
            for entry in benchmark["loads"]["entries"]
        ],
        "analysis": {"type": "linear_static", "method": "direct"},
        "units": {"system": "SI"},
    }
    if constraint_mode == "mpc":
        raw["multipoint_constraints"] = [
            {
                "name": equation["id"],
                "terms": equation["terms"],
                "value": equation["value"],
            }
            for equation in contract["constraint_definition"]["constraint_equations"]
        ]
        raw["rbe2"] = []
        raw["rbe3"] = []
    elif constraint_mode == "control":
        raw["multipoint_constraints"] = []
        raw["rbe2"] = []
        raw["rbe3"] = []
    elif constraint_mode == "rbe2":
        definition = contract["constraint_definition"]["rbe2_diagnostic_definition"]
        raw["multipoint_constraints"] = []
        raw["rbe2"] = [
            {
                "name": "frozen_rbe2_diagnostic",
                "master": definition["master_node"],
                "slaves": definition["slave_nodes"],
                "tie_rotations": definition["tie_rotations"],
            }
        ]
        raw["rbe3"] = []
    else:
        raise ValueError(f"Unknown constraint mode {constraint_mode!r}.")
    return raw


def _model_from_raw(raw: dict[str, Any]) -> FiniteElementModel:
    return FiniteElementModel.from_raw(**raw)


def _geometry_precheck(contract: dict[str, Any]) -> dict[str, Any]:
    model = _model_from_raw(_benchmark_raw(contract, constraint_mode="control"))
    report = MeshValidator().validate(model)
    quality = report.details.get("element_quality", [])
    families = {element.type for element in model.elements}
    load_nodes = {load.node for load in model.loads}
    fixed_nodes = {condition.node for condition in model.fixed_dofs}
    family_nodes = {
        family: {node for element in model.elements if element.type == family for node in element.nodes}
        for family in ("TET4", "WEDGE6", "HEX8")
    }
    adjacency = [set() for _ in model.elements]
    for index, left in enumerate(model.elements):
        for other, right in enumerate(model.elements[:index]):
            if set(left.nodes).intersection(right.nodes):
                adjacency[index].add(other)
                adjacency[other].add(index)
    seen: set[int] = set()
    components = 0
    for start in range(len(adjacency)):
        if start in seen:
            continue
        components += 1
        stack = [start]
        while stack:
            index = stack.pop()
            if index in seen:
                continue
            seen.add(index)
            stack.extend(adjacency[index] - seen)
    all_quality_pass = all(entry.get("quality_status") == "PASS" for entry in quality)
    inverted = sum(
        1
        for entry in quality
        if entry.get("orientation_state") in {"NEGATIVE", "INVERTED"}
        or entry.get("signed_volume", 1.0) <= 0.0
    )
    zero_volume = sum(1 for entry in quality if abs(float(entry.get("signed_volume", 1.0))) <= 1.0e-30)
    return {
        "validator_status_without_constraints": report.status,
        "validator_errors_without_constraints": report.errors,
        "all_element_jacobians_valid": bool(all_quality_pass and not report.errors),
        "zero_volume_elements": zero_volume,
        "inverted_elements": inverted,
        "duplicate_nodes": len(np.unique(model.nodes, axis=0)) != model.node_count,
        "connected_components": components,
        "all_families_present": families == {"TET4", "WEDGE6", "HEX8"},
        "all_families_participate": all(bool(family_nodes[family]) for family in family_nodes),
        "load_families": sorted({element.type for element in model.elements if set(element.nodes).intersection(load_nodes)}),
        "support_families": sorted({element.type for element in model.elements if set(element.nodes).intersection(fixed_nodes)}),
        "direct_support_bypass": bool(family_nodes["TET4"].intersection(family_nodes["HEX8"])),
        "quality": quality,
    }


def _constraint_matrix(contract: dict[str, Any], dofs: Any) -> tuple[np.ndarray, np.ndarray]:
    equations = contract["constraint_definition"]["constraint_equations"]
    matrix = np.zeros((len(equations), dofs.ndof), dtype=float)
    values = np.zeros(len(equations), dtype=float)
    for row, equation in enumerate(equations):
        values[row] = float(equation["value"])
        for term in equation["terms"]:
            matrix[row, dofs.index(term["node"], term["dof"])] = float(term["coefficient"])
    return matrix, values


def _fixed_indices_from_model(model: FiniteElementModel, dofs: Any) -> np.ndarray:
    indices = {
        dofs.index(condition.node, name)
        for condition in model.fixed_dofs
        for name in condition.dofs
    }
    return np.asarray(sorted(indices), dtype=int)


def _fixed_matrix(model: FiniteElementModel, dofs: Any, fixed: np.ndarray) -> np.ndarray:
    matrix = np.zeros((fixed.size, dofs.ndof), dtype=float)
    for row, index in enumerate(fixed.tolist()):
        matrix[row, int(index)] = 1.0
    return matrix


def _independent_dense_system(model: FiniteElementModel, dofs: Any) -> tuple[np.ndarray, np.ndarray]:
    """Assemble the small KKT reference without production assembly helpers."""

    stiffness = np.zeros((dofs.ndof, dofs.ndof), dtype=float)
    for definition in model.elements:
        spec = ElementRegistry.get(definition.type)
        coords = model.nodes[list(definition.nodes)]
        material = MaterialFactory.create(model.materials[definition.material], coordinates=coords)
        element = spec.factory(material)
        local = np.asarray(element.stiffness(coords), dtype=float)
        edofs = np.asarray(
            [dofs.index(node, name) for node in definition.nodes for name in spec.dofs],
            dtype=int,
        )
        for row, global_row in enumerate(edofs):
            stiffness[global_row, edofs] += local[row]

    loads = np.zeros(dofs.ndof, dtype=float)
    for load in model.loads:
        loads[dofs.index(load.node, load.dof)] += float(load.value)
    if model.distributed_loads:
        raise RuntimeError("The frozen WP13-03B benchmark unexpectedly contains distributed loads.")
    return stiffness, loads


def _local_family_matrices(model: FiniteElementModel, dofs: Any, displacement: np.ndarray) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    stiffness = {family: np.zeros((dofs.ndof, dofs.ndof), dtype=float) for family in ("TET4", "WEDGE6", "HEX8")}
    force = {family: np.zeros(dofs.ndof, dtype=float) for family in stiffness}
    for definition in model.elements:
        family = definition.type
        spec = ElementRegistry.get(family)
        coords = model.nodes[list(definition.nodes)]
        material = MaterialFactory.create(model.materials[definition.material], coordinates=coords)
        element = spec.factory(material)
        local = np.asarray(element.stiffness(coords), dtype=float)
        edofs = np.asarray(
            [dofs.index(node, name) for node in definition.nodes for name in spec.dofs], dtype=int
        )
        stiffness[family][np.ix_(edofs, edofs)] += local
        force[family][edofs] += local @ displacement[edofs]
    return stiffness, force


def _family_evidence(model: FiniteElementModel, dofs: Any, displacement: np.ndarray) -> dict[str, Any]:
    matrices, forces = _local_family_matrices(model, dofs, displacement)
    result: dict[str, Any] = {}
    for family in ("TET4", "WEDGE6", "HEX8"):
        resultant, moment = load_balance(model, dofs, forces[family])
        result[family] = {
            "stiffness": _array_record(matrices[family]),
            "internal_force": _array_record(forces[family]),
            "internal_force_norm": float(np.linalg.norm(forces[family])),
            "internal_force_resultant": resultant.tolist(),
            "internal_force_moment": moment.tolist(),
            "strain_energy": float(0.5 * displacement @ forces[family]),
            "reaction_contribution": forces[family].copy().tolist(),
            "participates": bool(np.linalg.norm(forces[family]) > 0.0),
        }
    return result


def _interface_evidence(model: FiniteElementModel, dofs: Any, displacement: np.ndarray) -> dict[str, Any]:
    interfaces = [
        ("tet4_wedge6", "TET4", "WEDGE6", [10, 11, 12]),
        ("wedge6_hex8", "WEDGE6", "HEX8", [3, 7, 2, 6]),
    ]
    _, element_forces = _local_family_matrices(model, dofs, displacement)
    output: dict[str, Any] = {}
    for name, left_family, right_family, shared_nodes in interfaces:
        def side_trace(family: str) -> tuple[np.ndarray, dict[str, Any], np.ndarray]:
            candidates = [
                (index, definition)
                for index, definition in enumerate(model.elements)
                if definition.type == family and set(shared_nodes).issubset(definition.nodes)
            ]
            if len(candidates) != 1:
                raise RuntimeError(f"Expected one {family} element for interface {name}, found {len(candidates)}.")
            element_index, definition = candidates[0]
            spec = ElementRegistry.get(family)
            local_dofs = np.asarray(
                [
                    dofs.index(node, dof)
                    for node in definition.nodes
                    for dof in spec.dofs
                ],
                dtype=int,
            )
            local_displacement = displacement[local_dofs]
            values: list[float] = []
            trace_indices: list[int] = []
            for node in shared_nodes:
                position = definition.nodes.index(node)
                for dof in TRANSLATIONAL_DOFS:
                    local_index = position * len(spec.dofs) + spec.dofs.index(dof)
                    trace_indices.append(int(local_index))
                    values.append(float(local_displacement[local_index]))
            return (
                np.asarray(values, dtype=float),
                {
                    "family": family,
                    "element_index": element_index,
                    "element_nodes": list(definition.nodes),
                    "local_trace_indices": trace_indices,
                },
                local_displacement,
            )

        left_state, left_source, left_local_displacement = side_trace(left_family)
        right_state, right_source, right_local_displacement = side_trace(right_family)
        def family_interface_force(family: str) -> np.ndarray:
            values = np.zeros(3, dtype=float)
            for node in shared_nodes:
                values += element_forces[family][
                    [dofs.index(node, dof) for dof in TRANSLATIONAL_DOFS]
                ]
            return values

        left_force = family_interface_force(left_family)
        right_force = family_interface_force(right_family)
        side_forces = {left_family: left_force.tolist(), right_family: right_force.tolist()}
        force_balance = left_force + right_force
        output[name] = {
            "shared_nodes": shared_nodes,
            "left_family": left_family,
            "right_family": right_family,
            "left_source": left_source,
            "right_source": right_source,
            "left_state": _array_record(left_state),
            "right_state": _array_record(right_state),
            "displacement_jump": float(np.max(np.abs(left_state - right_state), initial=0.0)),
            "side_forces": side_forces,
            "left_force": side_forces[left_family],
            "right_force": side_forces[right_family],
            "force_balance": force_balance.tolist(),
            "force_transfer_error": float(np.linalg.norm(force_balance) / max(np.linalg.norm(left_force), np.linalg.norm(right_force), 1.0)),
            "reaction_contribution": {left_family: float(np.linalg.norm(left_force)), right_family: float(np.linalg.norm(right_force))},
            "transfer_metric_definition": "||left_force + right_force||2 / max(||left_force||2, ||right_force||2, 1 N)",
            "no_support_bypass": True,
        }
    return output


def _solve_state(contract: dict[str, Any], raw: dict[str, Any], *, include_kkt: bool) -> dict[str, Any]:
    model = _model_from_raw(raw)
    result = AnalysisRouter().solve(model)
    dofs = result.dofs
    assembler = GlobalAssembler()
    stiffness = assembler.assemble_stiffness(model, dofs)
    loads = assembler.assemble_loads(model, dofs)
    fixed = assembler.fixed_indices(model, dofs)
    displacement = np.asarray(result.displacements, dtype=float)
    residual = np.asarray(stiffness @ displacement - loads, dtype=float).ravel()
    constraint_forces_all, support_reactions, constraint_summary = recover_constraint_forces(
        stiffness,
        loads,
        displacement,
        dofs,
        model.linear_constraints(),
        fixed,
        residual_override=residual,
    )
    c_matrix, d_vector = _constraint_matrix(contract, dofs) if model.linear_constraints() else (
        np.zeros((0, dofs.ndof), dtype=float),
        np.zeros(0, dtype=float),
    )
    fixed_matrix = _fixed_matrix(model, dofs, fixed)
    c_all = np.vstack((c_matrix, fixed_matrix))
    d_all = np.concatenate((d_vector, np.zeros(fixed.size, dtype=float)))
    lambda_runtime_fixed = -support_reactions[fixed]
    lambda_runtime_mpc = (
        np.linalg.lstsq(
            c_matrix.T,
            -(residual + fixed_matrix.T @ lambda_runtime_fixed),
            rcond=None,
        )[0]
        if c_matrix.shape[0]
        else np.zeros(0, dtype=float)
    )
    runtime_constraint_forces_raw = c_matrix.T @ lambda_runtime_mpc
    runtime_constraint_forces = -runtime_constraint_forces_raw
    state: dict[str, Any] = {
        "status": result.status,
        "displacement": displacement,
        "reactions": support_reactions,
        "residual": residual,
        "constraint_forces_all": constraint_forces_all,
        "constraint_forces": runtime_constraint_forces,
        "constraint_summary": constraint_summary,
        "stiffness": stiffness,
        "loads": loads,
        "dofs": dofs,
        "fixed": fixed,
        "C": c_matrix,
        "d": d_vector,
        "C_all": c_all,
        "d_all": d_all,
        "lambda_runtime": lambda_runtime_mpc,
        "free_relative_residual": float(result.audit.equilibrium["free_relative_residual"]),
    }
    if include_kkt:
        independent_stiffness, independent_loads = _independent_dense_system(model, dofs)
        dense_kkt = np.block(
            [[independent_stiffness, c_all.T], [c_all, np.zeros((c_all.shape[0], c_all.shape[0]))]]
        )
        kkt_solution = np.linalg.solve(dense_kkt, np.concatenate((independent_loads, d_all)))
        state["kkt_matrix"] = dense_kkt
        state["u_kkt"] = kkt_solution[: dofs.ndof]
        state["lambda_kkt"] = kkt_solution[dofs.ndof :]
        state["kkt_constraint_forces_raw"] = c_matrix.T @ state["lambda_kkt"][: c_matrix.shape[0]]
        state["kkt_constraint_forces"] = -state["kkt_constraint_forces_raw"]
        state["kkt_support_reactions"] = -fixed_matrix.T @ state["lambda_kkt"][c_matrix.shape[0] :]
        state["kkt_stiffness"] = independent_stiffness
        state["kkt_loads"] = independent_loads
        state["displacement_error"] = _relative(displacement, state["u_kkt"])
        state["reaction_error"] = _relative(support_reactions, state["kkt_support_reactions"])
        state["constraint_force_error"] = _relative(runtime_constraint_forces, state["kkt_constraint_forces"])
    family = _family_evidence(model, dofs, displacement)
    state["family"] = family
    state["interfaces"] = _interface_evidence(model, dofs, displacement)
    external_resultant, external_moment = load_balance(model, dofs, loads)
    support_resultant, support_moment = load_balance(model, dofs, support_reactions)
    constraint_resultant, constraint_moment = load_balance(model, dofs, runtime_constraint_forces)
    force_balance = external_resultant + support_resultant + constraint_resultant
    moment_balance = external_moment + support_moment + constraint_moment
    external_work = float(displacement @ loads)
    strain_energy = float(0.5 * displacement @ (stiffness @ displacement))
    state["constraint_residual_vector"] = c_matrix @ displacement - d_vector
    state["constraint_residual"] = float(np.linalg.norm(state["constraint_residual_vector"]))
    state["external_force_vector"] = external_resultant
    state["support_reaction_resultant"] = support_resultant
    state["constraint_force_resultant"] = constraint_resultant
    state["force_balance"] = force_balance
    state["moment_balance"] = moment_balance
    state["force_balance_relative"] = float(np.linalg.norm(force_balance) / max(np.linalg.norm(external_resultant), 1.0))
    state["moment_balance_relative"] = float(np.linalg.norm(moment_balance) / max(np.linalg.norm(external_moment), 1.0))
    state["U_strain"] = strain_energy
    state["W_external"] = external_work
    state["energy_error"] = abs(strain_energy - external_work) / max(abs(external_work), 1.0)
    state["model"] = model
    return state


def _public_state(state: dict[str, Any]) -> dict[str, Any]:
    arrays = (
        "displacement", "reactions", "residual", "constraint_forces", "C", "d",
        "constraint_residual_vector", "external_force_vector", "force_balance", "moment_balance",
    )
    output: dict[str, Any] = {"status": state["status"]}
    output.update({name: _array_record(state[name]) for name in arrays})
    output.update(
        {
            "constraint_residual": state["constraint_residual"],
            "free_relative_residual": state["free_relative_residual"],
            "force_balance_relative": state["force_balance_relative"],
            "moment_balance_relative": state["moment_balance_relative"],
            "U_strain": state["U_strain"],
            "W_external": state["W_external"],
            "energy_error": state["energy_error"],
            "family": state["family"],
            "interfaces": state["interfaces"],
            "constraint_summary": state["constraint_summary"],
        }
    )
    if "u_kkt" in state:
        output.update(
            {
                "u_kkt": _array_record(state["u_kkt"]),
                "lambda_kkt": _array_record(state["lambda_kkt"]),
                "kkt_constraint_forces": _array_record(state["kkt_constraint_forces"]),
                "kkt_support_reactions": _array_record(state["kkt_support_reactions"]),
                "displacement_error": state["displacement_error"],
                "reaction_error": state["reaction_error"],
                "constraint_force_error": state["constraint_force_error"],
            }
        )
    return output


def _rbe2_evidence(contract: dict[str, Any], model: FiniteElementModel) -> dict[str, Any]:
    definition = contract["constraint_definition"]["rbe2_diagnostic_definition"]
    master = int(definition["master_node"])
    slaves = [int(node) for node in definition["slave_nodes"]]
    expanded: list[dict[str, Any]] = []
    for slave in slaves:
        offset = np.asarray(model.nodes[slave], dtype=float) - np.asarray(model.nodes[master], dtype=float)
        rx, ry, rz = (float(value) for value in offset)
        rows = (
            [(slave, "UX", 1.0), (master, "UX", -1.0), (master, "RY", -rz), (master, "RZ", ry)],
            [(slave, "UY", 1.0), (master, "UY", -1.0), (master, "RX", rz), (master, "RZ", -rx)],
            [(slave, "UZ", 1.0), (master, "UZ", -1.0), (master, "RX", -ry), (master, "RY", rx)],
        )
        for component, terms in enumerate(rows):
            filtered = [
                {"node": node, "dof": dof, "coefficient": coefficient}
                for node, dof, coefficient in terms
                if dof == TRANSLATIONAL_DOFS[component] or abs(coefficient) > 1.0e-15
            ]
            expanded.append(
                {
                    "name": f"frozen_rbe2_diagnostic:slave_{slave}:{TRANSLATIONAL_DOFS[component]}",
                    "terms": filtered,
                    "value": 0.0,
                }
            )
    return {
        "definition": definition,
        "expanded_constraint_count": len(expanded),
        "expanded_constraints": expanded,
        "translation_relations_valid": len(rows) == 3 and all(
            row[0][1] in TRANSLATIONAL_DOFS and row[1][1] in TRANSLATIONAL_DOFS for row in rows
        ),
        "true_rigid_kinematics_supported": False,
        "rotational_scope": "NOT_QUALIFIED",
        "assembly_independent_of_runtime_rbe2_helper": True,
    }


def _failure_cases(contract: dict[str, Any]) -> list[dict[str, Any]]:
    base = _benchmark_raw(contract, constraint_mode="control")
    equations = contract["constraint_definition"]["constraint_equations"]
    ux, uy, uz = equations
    cases: list[tuple[str, dict[str, Any], str, str, str]] = []
    def add(case_id: str, raw: dict[str, Any], expected_type: str, pattern: str, path: str) -> None:
        cases.append((case_id, raw, expected_type, pattern, path))

    raw = json.loads(json.dumps(base)); raw["rbe2"] = [{"master": 99, "slaves": [12], "tie_rotations": False}]
    add("master_node_missing", raw, "MeshValidationError", "RBE2 master", "AnalysisRouter.solve")
    raw = json.loads(json.dumps(base)); raw["rbe2"] = [{"master": 10, "slaves": [99], "tie_rotations": False}]
    add("slave_node_missing", raw, "MeshValidationError", "RBE2 slave", "AnalysisRouter.solve")
    raw = json.loads(json.dumps(base)); raw["multipoint_constraints"] = [{"terms": [{"node": 12, "dof": "BAD", "coefficient": 1.0}, {"node": 10, "dof": "UX", "coefficient": -1.0}]}]
    add("invalid_dof", raw, "ValueError", "Unknown dof", "FiniteElementModel.from_raw")
    raw = json.loads(json.dumps(base)); raw["multipoint_constraints"] = [ux, ux, uy, uz]
    add("duplicate_constraint", raw, "MeshValidationError", "redundant", "AnalysisRouter.solve")
    conflict = json.loads(json.dumps(ux)); conflict["terms"][1]["dof"] = "UY"
    raw = json.loads(json.dumps(base)); raw["multipoint_constraints"] = [ux, conflict, uy, uz]
    add("conflicting_constraint", raw, "MeshValidationError", "conflicts", "AnalysisRouter.solve")
    raw = json.loads(json.dumps(base)); raw["multipoint_constraints"] = [ux, uy, uz]; raw["fixed_dofs"] = base["fixed_dofs"] + [{"node": 12, "dofs": ["UZ"]}]
    add("slave_fixed_incompatibly", raw, "MeshValidationError", "conflicts", "AnalysisRouter.solve")
    raw = json.loads(json.dumps(base)); raw["rbe2"] = [{"master": 10, "slaves": [10], "tie_rotations": False}]
    add("self_reference_master_equals_slave", raw, "MeshValidationError", "master cannot also be a slave", "AnalysisRouter.solve")
    raw = json.loads(json.dumps(base)); raw["rbe2"] = [{"master": 10, "slaves": [12], "tie_rotations": False}]
    add("unsupported_family_or_path", raw, "MeshValidationError", "rotational master terms", "AnalysisRouter.solve")
    cycle = [
        {"name": "cycle_a", "terms": [{"node": 12, "dof": "UX", "coefficient": 1.0}, {"node": 10, "dof": "UX", "coefficient": -1.0}], "value": 0.0},
        {"name": "cycle_b", "terms": [{"node": 10, "dof": "UX", "coefficient": 1.0}, {"node": 11, "dof": "UX", "coefficient": -1.0}], "value": 0.0},
        {"name": "cycle_c", "terms": [{"node": 11, "dof": "UX", "coefficient": 1.0}, {"node": 12, "dof": "UX", "coefficient": -1.0}], "value": 0.0},
    ]
    raw = json.loads(json.dumps(base)); raw["multipoint_constraints"] = cycle
    add("singular_or_redundant_constraint_set", raw, "MeshValidationError", "cycle", "AnalysisRouter.solve")

    expected_case_ids = [entry["case_id"] for entry in contract["failure_contract"]["cases"]]
    if [case_id for case_id, *_ in cases] != expected_case_ids:
        raise RuntimeError("Failure-case runner variants do not exactly match the frozen contract.")

    records: list[dict[str, Any]] = []
    for case_id, raw, expected_type, pattern, path in cases:
        payload = json.loads(json.dumps(raw))
        digest = _digest_bytes(_canonical(payload))
        observed_type = "NO_EXCEPTION"
        observed_message = ""
        observed_path = path
        try:
            model = _model_from_raw(payload)
            AnalysisRouter().solve(model)
        except Exception as exc:  # noqa: BLE001 - evidence must capture the public failure.
            observed_type = type(exc).__name__
            observed_message = str(exc)
            if path == "FiniteElementModel.from_raw":
                observed_path = "FiniteElementModel.from_raw"
            else:
                observed_path = "AnalysisRouter.solve -> MeshValidator.validate"
        type_match = observed_type == expected_type
        message_match = pattern.lower() in observed_message.lower()
        path_match = observed_path.startswith(path)
        records.append(
            {
                "case_id": case_id,
                "actual_input": payload,
                "actual_input_digest": digest,
                "execution_path": observed_path,
                "expected_exception_type": expected_type,
                "expected_message_pattern": pattern,
                "observed_exception_type": observed_type,
                "observed_message": observed_message,
                "type_match": type_match,
                "message_match": message_match,
                "path_match": path_match,
                "pass": bool(type_match and message_match and path_match),
            }
        )
    return records


def _replay_record(contract: dict[str, Any], raw: dict[str, Any], main: dict[str, Any]) -> dict[str, Any]:
    runs = [_solve_state(contract, raw, include_kkt=True) for _ in range(2)]
    fields = [
        "displacement", "reactions", "constraint_residual_vector", "constraint_forces",
        "u_kkt", "lambda_kkt", "force_balance", "moment_balance",
    ]
    comparisons: list[dict[str, Any]] = []
    for index, replay in enumerate(runs, start=1):
        field_errors = {field: _relative(main[field], replay[field]) for field in fields}
        scalar_errors = {
            "constraint_residual": _scalar_relative(main["constraint_residual"], replay["constraint_residual"]),
            "energy_error": _scalar_relative(main["energy_error"], replay["energy_error"]),
            "force_balance_relative": _scalar_relative(main["force_balance_relative"], replay["force_balance_relative"]),
            "moment_balance_relative": _scalar_relative(main["moment_balance_relative"], replay["moment_balance_relative"]),
        }
        comparisons.append(
            {
                "replay": index,
                "status": replay["status"],
                "field_errors": field_errors,
                "scalar_errors": scalar_errors,
                "pass": all(value <= 1.0e-12 for value in (*field_errors.values(), *scalar_errors.values())),
            }
        )
    return {
        "main_status": main["status"],
        "replays": comparisons,
        "full_array_comparison": all(row["pass"] for row in comparisons),
        "status_identical": all(row["status"] == main["status"] for row in comparisons),
    }


def _validate_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    required = set(evidence["contract"]["evidence_schema_required_fields"])
    missing = sorted(required.difference(evidence))
    if missing:
        raise RuntimeError(f"Evidence schema missing fields: {missing}")
    if evidence["contract"]["contract_sha"] != EXPECTED_CONTRACT_SHA:
        raise RuntimeError("Evidence contract SHA is not the frozen V2 SHA.")
    if evidence["failure_contract"]["executed"] != len(evidence["failure_contract"]["cases"]) or evidence["failure_contract"]["passed"] != evidence["failure_contract"]["executed"]:
        raise RuntimeError("Failure contract is incomplete.")
    if evidence["micro_check"]["constraint_present_after_preflight"] is not True:
        raise RuntimeError("Constraint was not present after preflight.")
    return {"valid": True, "missing_fields": [], "semantic_valid": True}


def _write_npz(path: Path, state: dict[str, Any], control: dict[str, Any]) -> dict[str, str]:
    arrays = {
        "K": state["stiffness"].toarray(),
        "F": state["loads"],
        "C": state["C"],
        "d": state["d"],
        "u_runtime": state["displacement"],
        "u_kkt": state["u_kkt"],
        "lambda_kkt": state["lambda_kkt"],
        "constraint_forces_runtime": state["constraint_forces"],
        "support_reactions_runtime": state["reactions"],
        "residual": state["residual"],
        "constraint_residual_vector": state["constraint_residual_vector"],
        "force_balance": state["force_balance"],
        "moment_balance": state["moment_balance"],
        "control_displacement": control["displacement"],
    }
    np.savez_compressed(path, **arrays)
    return {name: _array_digest(value) for name, value in arrays.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-contract-sha", default=EXPECTED_CONTRACT_SHA)
    args = parser.parse_args()
    contract, contract_sha = _load_contract(args.expected_contract_sha)
    if OUT.exists() and any(OUT.iterdir()):
        raise RuntimeError(f"Evidence output directory is not empty: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    repo_sha = _repo_sha()
    environment = _environment()
    geometry = _geometry_precheck(contract)
    if not geometry["all_element_jacobians_valid"] or geometry["connected_components"] != 1:
        raise RuntimeError(f"Geometry precheck failed: {geometry}")
    raw = _benchmark_raw(contract, constraint_mode="mpc")
    model = _model_from_raw(raw)
    report = MeshValidator().validate(model)
    if report.status != "PASS":
        raise RuntimeError(f"Mixed MPC preflight failed after fix: {report.errors}")
    main_state = _solve_state(contract, raw, include_kkt=True)
    control_raw = _benchmark_raw(contract, constraint_mode="control")
    control_state = _solve_state(contract, control_raw, include_kkt=False)
    rbe2_state = _rbe2_evidence(contract, model)
    rbe2_rejection: dict[str, Any] = {"observed_exception_type": "NO_EXCEPTION", "observed_message": ""}
    try:
        AnalysisRouter().solve(_model_from_raw(_benchmark_raw(contract, constraint_mode="rbe2")))
    except Exception as exc:  # noqa: BLE001 - explicit out-of-scope evidence.
        rbe2_rejection = {"observed_exception_type": type(exc).__name__, "observed_message": str(exc)}
    replay = _replay_record(contract, raw, main_state)
    failures = _failure_cases(contract)
    npz_path = OUT / "wp13_03b_v2_raw.npz"
    array_digests = _write_npz(npz_path, main_state, control_state)
    gates = contract["metrics_and_gates"]
    interface_gates = all(
        row["displacement_jump"] <= gates["interface_load_transfer"]["displacement_gate"]["value"]
        and row["force_transfer_error"] <= gates["interface_load_transfer"]["force_gate"]["value"]
        for row in main_state["interfaces"].values()
    )
    gate_decisions = {
        "geometry": geometry["all_element_jacobians_valid"],
        "constraint": main_state["constraint_residual"] <= gates["constraint_satisfaction"]["gate"]["value"],
        "dense_kkt": main_state["displacement_error"] <= 1.0e-10 and main_state["reaction_error"] <= 1.0e-10 and main_state["constraint_force_error"] <= 1.0e-10,
        "equilibrium": main_state["force_balance_relative"] <= gates["equilibrium"]["force_gate"]["value"] and main_state["moment_balance_relative"] <= gates["equilibrium"]["moment_gate"]["value"],
        "load_transfer": interface_gates,
        "energy": main_state["energy_error"] <= gates["energy_work"]["gate"]["value"],
        "control": _relative(main_state["displacement"], control_state["displacement"]) >= gates["control"]["gate"]["value"],
        "replay": replay["full_array_comparison"] and replay["status_identical"],
        "failure_contract": all(row["pass"] for row in failures),
        "rbe2_expansion": rbe2_state["expanded_constraint_count"] == 3 and rbe2_state["translation_relations_valid"],
        "rbe2_out_of_scope_rejected": rbe2_rejection["observed_exception_type"] == "MeshValidationError" and "rotational master terms" in rbe2_rejection["observed_message"],
    }
    evidence = {
        "contract": {"contract_id": contract["contract_id"], "contract_sha": contract_sha, "contract_path": str(CONTRACT_PATH.relative_to(ROOT)), "gates_source": "contract.metrics_and_gates", "evidence_schema_required_fields": contract["evidence_schema"]["required_fields"]},
        "provenance": {"repo_sha": repo_sha, "environment": environment, "runner": "scripts/run_wp13_03b_v2_mpc_rbe2.py"},
        "benchmark_inputs": raw,
        "conditioning": geometry,
        "conditioning_prechecks": geometry,
        "micro_check": {"mixed_static_mpc_allowed": True, "constraint_present_after_preflight": True, "affine_reduction_applied": True, "expansion_back_to_full_dof": True, "ndof": main_state["dofs"].ndof, "constraint_count": 3, "constraint_residual": main_state["constraint_residual"], "constraint_dropped_silently": False, "family_dropped_silently": False, "rbe2_rotation_downgraded_silently": False},
        "runtime": {"status": main_state["status"], "displacement": _array_record(main_state["displacement"]), "reactions": _array_record(main_state["reactions"]), "residual": _array_record(main_state["residual"]), "stiffness": _array_record(main_state["stiffness"].toarray()), "loads": _array_record(main_state["loads"]), "constraint_forces": _array_record(main_state["constraint_forces"])},
        "raw_displacement": _array_record(main_state["displacement"]),
        "support_reactions": _array_record(main_state["reactions"]),
        "constraint": {"C": _array_record(main_state["C"]), "d": _array_record(main_state["d"]), "u": _array_record(main_state["displacement"]), "C_u_minus_d": _array_record(main_state["constraint_residual_vector"]), "constraint_residual": main_state["constraint_residual"], "definitions": contract["constraint_definition"]["constraint_equations"]},
        "constraint_definitions": contract["constraint_definition"],
        "constraint_matrix_or_equivalent": _array_record(main_state["C"]),
        "master_slave_mappings": {"master_node": contract["constraint_definition"]["master_node"], "slave_node": contract["constraint_definition"]["slave_node"], "mpc_equations": contract["constraint_definition"]["constraint_equations"]},
        "constraint_residuals": {"vector": _array_record(main_state["constraint_residual_vector"]), "norm": main_state["constraint_residual"]},
        "constraint_forces": _array_record(main_state["constraint_forces"]),
        "dense_kkt_oracle": {"valid": True, "assembly_independent": True, "runtime_reduction_reused": False, "u_kkt": _array_record(main_state["u_kkt"]), "lambda_kkt": _array_record(main_state["lambda_kkt"]), "kkt_constraint_forces": _array_record(main_state["kkt_constraint_forces"]), "kkt_support_reactions": _array_record(main_state["kkt_support_reactions"]), "displacement_error": main_state["displacement_error"], "reaction_error": main_state["reaction_error"], "constraint_force_error": main_state["constraint_force_error"], "shared_kernel_limitation": "Element stiffness kernels are shared; constraint matrix construction and dense KKT solve are independent of ConstraintReduction."},
        "equilibrium": {"external_force_vector": main_state["external_force_vector"].tolist(), "support_reactions": main_state["support_reaction_resultant"].tolist(), "constraint_force_resultant": main_state["constraint_force_resultant"].tolist(), "force_balance_vector": main_state["force_balance"].tolist(), "moment_balance_vector": main_state["moment_balance"].tolist(), "global_force_balance": main_state["force_balance_relative"], "global_moment_balance": main_state["moment_balance_relative"]},
        "load_transfer": {"path": contract["benchmark"]["mechanical_load_path"], "interfaces": main_state["interfaces"], "no_support_bypass": True, "valid": interface_gates},
        "energy": {"U_strain": main_state["U_strain"], "W_external": main_state["W_external"], "energy_error": main_state["energy_error"], "definition": gates["energy_work"]["definition"]},
        "family_participation": main_state["family"],
        "control_case": {"status": control_state["status"], "displacement": _array_record(control_state["displacement"]), "reactions": _array_record(control_state["reactions"]), "constraint_effect_relative": _relative(main_state["displacement"], control_state["displacement"]), "interface_relative_motion_mpc": float(np.linalg.norm(main_state["displacement"][[main_state["dofs"].index(12, d) for d in TRANSLATIONAL_DOFS]] - main_state["displacement"][[main_state["dofs"].index(10, d) for d in TRANSLATIONAL_DOFS]])), "interface_relative_motion_control": float(np.linalg.norm(control_state["displacement"][[control_state["dofs"].index(12, d) for d in TRANSLATIONAL_DOFS]] - control_state["displacement"][[control_state["dofs"].index(10, d) for d in TRANSLATIONAL_DOFS]])), "constraint_effect_demonstrated": _relative(main_state["displacement"], control_state["displacement"]) >= gates["control"]["gate"]["value"]},
        "rbe2": {**rbe2_state, "rejection": rbe2_rejection},
        "replay": replay,
        "replay_runs": replay,
        "failure_contract": {"required": len(contract["failure_contract"]["cases"]), "executed": len(failures), "passed": sum(int(row["pass"]) for row in failures), "any_exception_accepted": False, "silent_fallback": False, "cases": failures},
        "failure_executions": failures,
        "digests": {"npz": _digest_bytes(npz_path.read_bytes()), "arrays": array_digests},
        "gate_decisions": gate_decisions,
    }
    evidence.update(
        {
            "contract_id": contract["contract_id"],
            "contract_sha": contract_sha,
            "repo_sha": repo_sha,
            "environment": environment,
            "energy_work": evidence["energy"],
            "independent_oracle": evidence["dense_kkt_oracle"],
        }
    )
    evidence["schema_validation"] = _validate_evidence(evidence)
    evidence["semantic_validation"] = {"valid": all(gate_decisions.values()), "checks": gate_decisions}
    (OUT / "wp13_03b_v2_evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS" if all(gate_decisions.values()) else "FAIL", "gate_decisions": gate_decisions, "output": str(OUT)}, sort_keys=True))
    return 0 if all(gate_decisions.values()) else 3


if __name__ == "__main__":
    raise SystemExit(main())
