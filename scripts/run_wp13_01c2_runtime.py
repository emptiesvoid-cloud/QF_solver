"""Execute the separately predeclared WP13-01F mixed PETSc/MPI runtime campaign."""

from __future__ import annotations

# ruff: noqa: E402

import argparse
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

from run_wp11_mixed_large import _make_model
from run_wp13_01c_runtime import _petsc_run, _serial_run
from solveur.core.model import FiniteElementModel
from solveur.large.generic_distributed import GenericDistributedModel, partition_generic_model


CONTRACT_ID = "WP13-01F-MIXED-PETSC-RUNTIME-002"
CHAIN_COUNTS = {"control": 2, "stage-a": 3031, "stage-b": 9091, "stage-c": 30303}
FAMILIES = ("TET4", "WEDGE6", "HEX8")


def _family_major_model(chains: int) -> FiniteElementModel:
    """Build the frozen WP11 unit-scale bundle in declared family-major order."""

    source, _ = _make_model(chains)
    rows = [
        {"type": item.type, "nodes": list(item.nodes), "material": item.material}
        for family in FAMILIES
        for item in source.elements
        if item.type == family
    ]
    return FiniteElementModel.from_raw(
        nodes=source.nodes.tolist(),
        elements=rows,
        materials={name: dict(data) for name, data in source.materials.items()},
        fixed_dofs=[{"node": item.node, "dofs": list(item.dofs)} for item in source.fixed_dofs],
        loads=[{"node": item.node, "dof": item.dof, "value": item.value} for item in source.loads],
        analysis={"type": "linear_static", "method": "direct"},
        units=dict(source.units),
        verification_profile=source.verification_profile,
    )


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _partition_metadata(model: FiniteElementModel, ranks: int) -> dict[str, Any]:
    generic = GenericDistributedModel.from_finite_element_model(model)
    partitions = partition_generic_model(generic, ranks)
    owner = {element.element_id: partition.rank for partition in partitions for element in partition.elements}
    chains = len(model.elements) // 3
    tet_wedge = sum(owner[index] != owner[chains + index] for index in range(chains)) / chains
    wedge_hex = sum(owner[chains + index] != owner[2 * chains + index] for index in range(chains)) / chains
    records = [
        {"rank": partition.rank, "elements": list(partition.owned_element_ids), "families": partition.element_counts}
        for partition in partitions
    ]
    return {
        "digest": _digest(records),
        "rank_count": ranks,
        "local_family_counts": [record["families"] for record in records],
        "cross_rank_interface_fraction": {"tet4_wedge6": tet_wedge, "wedge6_hex8": wedge_hex},
        "ghost_nodes": [int(partition.ghost_node_ids.size) for partition in partitions],
    }


def _component_equilibrium(result: dict[str, Any]) -> float:
    external = np.asarray(result["external_load_resultant"], dtype=float)
    reaction = np.asarray(result["reaction_resultant"], dtype=float)
    return float(np.max(np.abs(external + reaction)) / max(float(np.linalg.norm(external)), 1.0))


def _normalized_digest(vector: np.ndarray) -> str:
    scale = max(float(np.linalg.norm(vector, ord=np.inf)), 1.0e-30)
    values = np.round(vector / scale, decimals=12)
    return hashlib.sha256(np.asarray(values, dtype=np.float64).tobytes(order="C")).hexdigest()


def _vector_state(result: dict[str, Any], partition: dict[str, Any]) -> dict[str, Any]:
    displacement = np.asarray(result.pop("displacement"), dtype=float)
    reactions = np.asarray(result.pop("reaction_vector"), dtype=float)
    residual = np.asarray(result.pop("residual"), dtype=float)
    result.pop("loads")
    return {
        "model_digest": result["model_digest"],
        "partition_digest": partition["digest"],
        "displacement": displacement,
        "reactions": reactions,
        "residual": residual,
        "energy": float(result["energy"]),
        "iterations": int(result["iterations"]),
        "normalized_physics_digest": _digest(
            {
                "displacement": _normalized_digest(displacement),
                "reactions": _normalized_digest(reactions),
                "residual": _normalized_digest(residual),
                "energy": float(result["energy"]),
            }
        ),
    }


def _relative(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right) / max(float(np.linalg.norm(right)), 1.0))


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        displacement=state["displacement"],
        reactions=state["reactions"],
        residual=state["residual"],
        metadata=json.dumps({key: value for key, value in state.items() if not isinstance(value, np.ndarray)}, sort_keys=True),
    )


def _compare_state(path: Path, state: dict[str, Any]) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as reference:
        metadata = json.loads(str(reference["metadata"]))
        displacement = _relative(state["displacement"], reference["displacement"])
        reactions = _relative(state["reactions"], reference["reactions"])
        residual = _relative(state["residual"], reference["residual"])
        energy = abs(state["energy"] - float(metadata["energy"])) / max(abs(float(metadata["energy"])), 1.0)
        return {
            "same_model_digest": state["model_digest"] == metadata["model_digest"],
            "same_partition_digest": state["partition_digest"] == metadata["partition_digest"],
            "iteration_difference": abs(state["iterations"] - int(metadata["iterations"])),
            "displacement_relative_l2": displacement,
            "reaction_relative_l2": reactions,
            "residual_relative_difference": residual,
            "energy_relative_difference": energy,
            "normalized_digest_equal": state["normalized_physics_digest"] == metadata["normalized_physics_digest"],
            "status": "PASS" if all(
                (
                    state["model_digest"] == metadata["model_digest"],
                    state["partition_digest"] == metadata["partition_digest"],
                    state["iterations"] == int(metadata["iterations"]),
                    displacement <= 1.0e-12,
                    reactions <= 1.0e-12,
                    residual <= 1.0e-12,
                    energy <= 1.0e-12,
                )
            ) else "FAIL"
        }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=tuple(CHAIN_COUNTS), required=True)
    parser.add_argument("--backend", choices=("serial", "petsc"), required=True)
    parser.add_argument("--pc-type", default="lu")
    parser.add_argument("--state-out", type=Path)
    parser.add_argument("--compare-state", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    model = _family_major_model(CHAIN_COUNTS[args.case])
    if args.backend == "serial":
        if args.case != "control":
            raise SystemExit("serial execution is restricted to the 66-DOF control")
        result = _serial_run(model)
        partition = _partition_metadata(model, 1)
    else:
        from mpi4py import MPI

        ranks = MPI.COMM_WORLD.Get_size()
        partition = _partition_metadata(model, ranks)
        result = _petsc_run(model, args.pc_type, "auto", 2, bool(args.state_out or args.compare_state))
        if result is None:
            return 0
    result["e_component"] = _component_equilibrium(result)
    result["partition"] = partition
    result["gates"] = {
        "free_residual": result["free_residual_relative"] <= 1.0e-10,
        "e_force": result["equilibrium_relative"] <= 1.0e-10,
        "e_component": result["e_component"] <= 1.0e-10,
        "energy": result["energy_identity_relative"] <= 1.0e-10,
    }
    if args.backend == "petsc" and (args.state_out or args.compare_state):
        state = _vector_state(result, partition)
        if args.state_out:
            _save_state(args.state_out, state)
        if args.compare_state:
            result["replay_comparison"] = _compare_state(args.compare_state, state)
    payload = {"schema_version": 1, "contract_id": CONTRACT_ID, "case": args.case, "backend": args.backend, "result": result}
    encoded = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
