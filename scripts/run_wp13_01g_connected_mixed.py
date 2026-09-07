"""Execute the predeclared WP13-01G connected mixed PETSc/MPI campaign."""

from __future__ import annotations

# ruff: noqa: E402

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from run_wp13_01c_runtime import (
    _fixed_indices,
    _petsc_run,
    _serial_run,
    _staged_model,
)
from solveur.core.model import FiniteElementModel
from solveur.large.generic_distributed import GenericDistributedModel, partition_generic_model
from solveur.mesh.mixed_validation import mixed_linear_static_scope_errors, mixed_solid_faces


CONTRACT_ID = "WP13-01G-CONNECTED-MIXED-PETSC-001"
CASES = {"control": 1, "stage-a": 3332, "stage-b": 9999, "stage-c": 19999}
FAMILIES = ("TET4", "WEDGE6", "HEX8")


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _element_graph(model: FiniteElementModel) -> tuple[dict[str, Any], dict[int, int]]:
    faces = mixed_solid_faces(model)
    by_nodes: dict[frozenset[int], list[Any]] = defaultdict(list)
    for face in faces:
        by_nodes[frozenset(face.nodes)].append(face)
    parent = list(range(len(model.elements)))

    def find(item: int) -> int:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left: int, right: int) -> None:
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    interface_records: list[dict[str, Any]] = []
    family_pairs: dict[tuple[str, str], int] = defaultdict(int)
    for node_set, entries in by_nodes.items():
        if len(entries) != 2:
            continue
        first, second = entries
        union(first.element_index, second.element_index)
        pair = tuple(sorted((str(first.element_type), str(second.element_type))))
        if pair[0] != pair[1]:
            family_pairs[pair] += 1
            interface_records.append(
                {
                    "families": list(pair),
                    "nodes": sorted(int(node) for node in node_set),
                    "element_indices": [int(first.element_index), int(second.element_index)],
                }
            )
    component_ids = {index: find(index) for index in range(len(model.elements))}
    family_graph = {family: set() for family in FAMILIES}
    for left, right in family_pairs:
        family_graph[left].add(right)
        family_graph[right].add(left)
    families_for_nodes: dict[int, set[str]] = defaultdict(set)
    for index, element in enumerate(model.elements):
        for node in element.nodes:
            families_for_nodes[int(node)].add(str(element.type).upper())
    load_families = sorted(
        {family for load in model.loads for family in families_for_nodes.get(int(load.node), set())}
    )
    fixed_nodes = {int(condition.node) for condition in model.fixed_dofs}
    fixed_families = sorted({family for node in fixed_nodes for family in families_for_nodes.get(node, set())})
    return (
        {
            "connected_components": len(set(component_ids.values())),
            "element_counts": {
                family: sum(str(element.type).upper() == family for element in model.elements)
                for family in FAMILIES
            },
            "interface_counts": {
                "TET4_WEDGE6": int(family_pairs.get(("TET4", "WEDGE6"), 0)),
                "WEDGE6_HEX8": int(family_pairs.get(("HEX8", "WEDGE6"), 0)),
            },
            "interface_records_sample": interface_records[:8],
            "family_graph": {family: sorted(neighbors) for family, neighbors in family_graph.items()},
            "load_families": load_families,
            "fixed_families": fixed_families,
            "mechanical_load_path": "TET4 -> WEDGE6 -> HEX8 through shared conforming faces"
            if len(set(component_ids.values())) == 1
            and {"TET4", "WEDGE6", "HEX8"}.issubset(set(load_families) | set(fixed_families) | set(family_graph))
            else "INCOMPLETE",
            "scope_errors": mixed_linear_static_scope_errors(model),
        },
        component_ids,
    )


def _partition_metadata(model: FiniteElementModel, ranks: int, component_ids: dict[int, int]) -> dict[str, Any]:
    generic = GenericDistributedModel.from_finite_element_model(model)
    partitions = partition_generic_model(generic, ranks)
    owner = {element.element_id: partition.rank for partition in partitions for element in partition.elements}
    faces = mixed_solid_faces(model)
    by_nodes: dict[frozenset[int], list[Any]] = defaultdict(list)
    for face in faces:
        by_nodes[frozenset(face.nodes)].append(face)
    cross_rank: dict[str, int] = {"TET4_WEDGE6": 0, "WEDGE6_HEX8": 0}
    total: dict[str, int] = {"TET4_WEDGE6": 0, "WEDGE6_HEX8": 0}
    for node_set, entries in by_nodes.items():
        if len(entries) != 2:
            continue
        first, second = entries
        pair = tuple(sorted((str(first.element_type), str(second.element_type))))
        key = {("TET4", "WEDGE6"): "TET4_WEDGE6", ("HEX8", "WEDGE6"): "WEDGE6_HEX8"}.get(pair)
        if key is None:
            continue
        total[key] += 1
        if owner[first.element_index] != owner[second.element_index]:
            cross_rank[key] += 1
    records = [
        {
            "rank": partition.rank,
            "owned_elements": list(partition.owned_element_ids),
            "families": partition.element_counts,
            "owned_nodes": int(partition.owned_node_ids.size),
            "ghost_nodes": int(partition.ghost_node_ids.size),
            "interface_nodes": int(partition.interface_node_ids.size),
            "neighbors": list(partition.neighboring_ranks),
        }
        for partition in partitions
    ]
    return {
        "rank_count": int(ranks),
        "partition_digest": _digest(records),
        "local_records": records,
        "cross_rank_interfaces": cross_rank,
        "total_family_interfaces": total,
        "element_components": len(set(component_ids.values())),
    }


def _state_from_result(result: dict[str, Any], partition: dict[str, Any]) -> dict[str, Any]:
    return {
        "model_digest": result["model_digest"],
        "partition_digest": partition["partition_digest"],
        "displacement": np.asarray(result["displacement"], dtype=np.float64),
        "reactions": np.asarray(result["reaction_vector"], dtype=np.float64),
        "residual": np.asarray(result["residual"], dtype=np.float64),
        "energy": float(result["energy"]),
        "iterations": result["iterations"],
    }


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {key: value for key, value in state.items() if not isinstance(value, np.ndarray)}
    np.savez_compressed(
        path,
        displacement=state["displacement"],
        reactions=state["reactions"],
        residual=state["residual"],
        metadata=json.dumps(metadata, sort_keys=True),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=tuple(CASES), required=True)
    parser.add_argument("--backend", choices=("serial", "petsc"), required=True)
    parser.add_argument("--pc-type", default="lu")
    parser.add_argument("--ksp-type", default="auto")
    parser.add_argument("--residual-refinement-steps", type=int, default=2)
    parser.add_argument("--include-vectors", action="store_true")
    parser.add_argument("--state-out", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    model = _staged_model(CASES[args.case])
    connectivity, component_ids = _element_graph(model)
    if connectivity["connected_components"] != 1 or connectivity["scope_errors"]:
        raise SystemExit(json.dumps({"status": "FAIL", "connectivity": connectivity}, indent=2))
    if args.backend == "serial":
        if args.case != "control":
            raise SystemExit("serial execution is defined only for the 33-DOF control")
        result = _serial_run(model)
        partition = _partition_metadata(model, 1, component_ids)
    else:
        from mpi4py import MPI

        ranks = MPI.COMM_WORLD.Get_size()
        partition = _partition_metadata(model, ranks, component_ids)
        result = _petsc_run(
            model,
            args.pc_type,
            args.ksp_type,
            args.residual_refinement_steps,
            args.include_vectors or model.dof_manager().ndof <= 1000,
        )
        if result is None:
            return 0
    result["connectivity"] = connectivity
    result["partition"] = partition
    result["contract_id"] = CONTRACT_ID
    result["case"] = args.case
    result["backend"] = args.backend
    result["rank_count"] = int(partition["rank_count"])
    result["gates"] = {
        "connected_components": connectivity["connected_components"] == 1,
        "family_presence": all(connectivity["element_counts"][family] > 0 for family in FAMILIES),
        "tet4_wedge6_interface": connectivity["interface_counts"]["TET4_WEDGE6"] > 0,
        "wedge6_hex8_interface": connectivity["interface_counts"]["WEDGE6_HEX8"] > 0,
        "free_residual": result["free_residual_relative"] <= 1.0e-10,
        "equilibrium_force": result["equilibrium_relative"] <= 1.0e-10,
        "equilibrium_component": result["equilibrium_relative"] <= 1.0e-10,
        "energy": result["energy_identity_relative"] <= 1.0e-10,
        "reallocations": result.get("reallocations", 0) == 0,
        "structural_global_gather": result.get("global_gather_present") is False,
    }
    if args.state_out and result.get("displacement") is not None:
        _save_state(args.state_out, _state_from_result(result, partition))
        if model.dof_manager().ndof > 1000:
            for field in ("displacement", "reaction_vector", "residual", "loads"):
                result[field] = None
    payload = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "case": args.case,
        "backend": args.backend,
        "segments": CASES[args.case],
        "result": result,
    }
    encoded = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
