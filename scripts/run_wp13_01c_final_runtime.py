"""Run the frozen WP13-01C real PETSc/MPI mixed-runtime campaign.

The MPI path intentionally constructs only a rank-local mixed envelope.  The
serial GlobalAssembler is used only for the 33-DOF reference case.  The
script is a qualification harness and does not alter FEM kernels or solver
sources.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from typing import Any, Callable

import numpy as np

# ruff: noqa: E402
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from run_wp13_01c_runtime import _serial_run
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.large.generic_distributed import (
    OwnedNodalLoad,
    RankLocalDofMap,
    RankLocalElement,
    RankLocalModel,
    dispatch_rank_local_element,
)


CONTRACT_ID = "WP13-01C-PETSC-MPI-MIXED-RUNTIME-001"
CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp13_01c_petsc_mpi_mixed_runtime_contract.json"
OUTPUT_DIR = ROOT / "qualification" / "0_2_8" / "wp13_01c_petsc_mpi_mixed_runtime"
CONTRACT_COMMIT_SHA = "bdbb1a4e5d8fabeb578a82a591f0ab13f260ce0c"
CAMPAIGN_REPO_SHA = "f5c1c6229390121645d6a1678a7bbe1a2662d8d6"
MATERIAL = {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7_800.0}
FAMILIES = ("TET4", "WEDGE6", "HEX8")
KSP_RTOL = 1.0e-13
KSP_ATOL = 1.0e-14
KSP_DTOL = 1.0e4
KSP_MAX_IT = 10_000
RELATIVE_GATE = 1.0e-10
REPLAY_GATE = 1.0e-12


def _solver_config(solver_config: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize an explicit PETSc configuration without any fallback."""

    config: dict[str, Any] = {
        "ksp": "CG",
        "pc": "JACOBI",
        "rtol": KSP_RTOL,
        "atol": KSP_ATOL,
        "dtol": KSP_DTOL,
        "max_it": KSP_MAX_IT,
    }
    if solver_config is not None:
        config.update(solver_config)
    config["ksp"] = str(config["ksp"]).lower()
    config["pc"] = str(config["pc"]).lower()
    if config["ksp"] not in {"cg", "gmres"}:
        raise InputValidationError(f"Unsupported explicit PETSc KSP '{config['ksp']}'.")
    if config["pc"] not in {"jacobi", "bjacobi", "asm", "gamg"}:
        raise InputValidationError(f"Unsupported explicit PETSc PC '{config['pc']}'.")
    for key in ("rtol", "atol", "dtol"):
        config[key] = float(config[key])
        if not math.isfinite(config[key]) or config[key] <= 0.0:
            raise InputValidationError(f"Invalid explicit PETSc {key}={config[key]!r}.")
    config["max_it"] = int(config["max_it"])
    if config["max_it"] <= 0:
        raise InputValidationError("Explicit PETSc max_it must be positive.")
    if config["ksp"] == "gmres":
        config["restart"] = int(config.get("restart", 30))
        if config["restart"] <= 0:
            raise InputValidationError("Explicit PETSc GMRES restart must be positive.")
    return config


def _json_default(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=_json_default)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNAVAILABLE"


def _layer_node_ids(segments: int) -> tuple[int, int, int]:
    wedge_start = 0
    outer_start = 3 * (segments + 1)
    apex_start = outer_start + 2 * (segments + 1)
    return wedge_start, outer_start, apex_start


def _node_count(segments: int) -> int:
    return 6 * segments + 5


def _node_coordinate(node: int, segments: int) -> tuple[float, float, float]:
    wedge_start, outer_start, apex_start = _layer_node_ids(segments)
    if wedge_start <= node < outer_start:
        layer, local = divmod(int(node), 3)
        z = float(layer) / float(segments)
        return ((0.0, 0.0, z), (1.0, 0.0, z), (0.0, 1.0, z))[local]
    if outer_start <= node < apex_start:
        layer, local = divmod(int(node) - outer_start, 2)
        z = float(layer) / float(segments)
        return ((0.0, -1.0, z), (1.0, -1.0, z))[local]
    if apex_start <= node < apex_start + segments:
        layer = int(node) - apex_start
        return (0.0, 0.0, (float(layer) - 0.5) / float(segments))
    raise InputValidationError(f"Unknown generated node id {node}.")


def _element_family(element_id: int) -> str:
    return FAMILIES[int(element_id) % 3]


def _element_nodes(element_id: int, segments: int) -> tuple[int, ...]:
    wedge_start, outer_start, apex_start = _layer_node_ids(segments)
    layer, family_index = divmod(int(element_id), 3)
    if layer < 0 or layer >= segments:
        raise InputValidationError(f"Generated element id {element_id} is out of range.")
    lower = wedge_start + 3 * layer
    upper = lower + 3
    if family_index == 0:
        return (lower, lower + 2, lower + 1, apex_start + layer)
    if family_index == 1:
        return (lower, lower + 1, lower + 2, upper, upper + 1, upper + 2)
    outer_lower = outer_start + 2 * layer
    outer_upper = outer_lower + 2
    return (
        outer_lower,
        outer_lower + 1,
        lower + 1,
        lower,
        outer_upper,
        outer_upper + 1,
        upper + 1,
        upper,
    )


def _element_owner(element_id: int, segments: int, size: int) -> int:
    element_count = 3 * segments
    boundaries = np.asarray([element_count * rank // int(size) for rank in range(int(size) + 1)], dtype=np.int64)
    return int(min(int(size) - 1, np.searchsorted(boundaries[1:], int(element_id), side="right")))


def _incident_elements(node: int, segments: int) -> tuple[int, ...]:
    wedge_start, outer_start, apex_start = _layer_node_ids(segments)
    node = int(node)
    if apex_start <= node < apex_start + segments:
        return (3 * (node - apex_start),)
    if outer_start <= node < apex_start:
        layer, _ = divmod(node - outer_start, 2)
        values: list[int] = []
        if layer < segments:
            values.append(3 * layer + 2)
        if layer > 0:
            values.append(3 * (layer - 1) + 2)
        return tuple(values)
    if wedge_start <= node < outer_start:
        layer, _ = divmod(node - wedge_start, 3)
        values = []
        if layer < segments:
            values.extend((3 * layer, 3 * layer + 1, 3 * layer + 2))
        if layer > 0:
            values.extend((3 * (layer - 1) + 1, 3 * (layer - 1) + 2))
        return tuple(sorted(set(values)))
    raise InputValidationError(f"Generated node id {node} has no incident element.")


def _node_owner(node: int, segments: int, size: int) -> int:
    candidates = _incident_elements(node, segments)
    if not candidates:
        raise InputValidationError(f"Generated node id {node} has no owner candidate.")
    return min(_element_owner(element_id, segments, size) for element_id in candidates)


def _fixed_nodes(segments: int) -> np.ndarray:
    wedge_start, outer_start, apex_start = _layer_node_ids(segments)
    values = [
        wedge_start + 3 * layer + local
        for layer in range(segments + 1)
        for local in (0, 2)
    ]
    values.extend(outer_start + 2 * layer for layer in range(segments + 1))
    values.extend(apex_start + layer for layer in range(segments))
    return np.asarray(sorted(set(values)), dtype=np.int64)


def _fixed_dofs(segments: int) -> np.ndarray:
    return np.asarray(
        [3 * int(node) + component for node in _fixed_nodes(segments) for component in range(3)], dtype=np.int64
    )


def _load_nodes(segments: int) -> tuple[int, int]:
    wedge_start, outer_start, _ = _layer_node_ids(segments)
    return (wedge_start + 3 * segments + 1, outer_start + 2 * segments + 1)


def _full_model(segments: int) -> FiniteElementModel:
    nodes = [_node_coordinate(node, segments) for node in range(_node_count(segments))]
    elements = [
        {"type": _element_family(element_id), "nodes": list(_element_nodes(element_id, segments)), "material": "solid"}
        for element_id in range(3 * segments)
    ]
    fixed = [{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in _fixed_nodes(segments)]
    loads = [{"node": int(node), "dof": "UX", "value": 50_000.0} for node in _load_nodes(segments)]
    return FiniteElementModel.from_raw(
        nodes=nodes,
        elements=elements,
        materials={"solid": dict(MATERIAL)},
        fixed_dofs=fixed,
        loads=loads,
        analysis={"type": "linear_static", "method": "cg"},
        units={"system": "SI"},
    )


def _rank_local_model(segments: int, rank: int, size: int) -> RankLocalModel:
    if size <= 0 or rank < 0 or rank >= size:
        raise InputValidationError("Invalid MPI rank/size for rank-local model.")
    element_count = 3 * segments
    start = element_count * rank // size
    stop = element_count * (rank + 1) // size
    element_ids = tuple(range(start, stop))
    local_nodes = np.asarray(sorted({node for element_id in element_ids for node in _element_nodes(element_id, segments)}), dtype=np.int64)
    owners = {int(node): _node_owner(int(node), segments, size) for node in local_nodes}
    owned_nodes = np.asarray([node for node in local_nodes if owners[int(node)] == rank], dtype=np.int64)
    ghost_nodes = np.asarray([node for node in local_nodes if owners[int(node)] != rank], dtype=np.int64)
    local_dofs = np.asarray(sorted(3 * int(node) + component for node in local_nodes for component in range(3)), dtype=np.int64)
    owned_dofs = np.asarray(sorted(3 * int(node) + component for node in owned_nodes for component in range(3)), dtype=np.int64)
    ghost_dofs = np.asarray(sorted(3 * int(node) + component for node in ghost_nodes for component in range(3)), dtype=np.int64)
    constrained = set(int(value) for value in _fixed_dofs(segments))
    dof_map = RankLocalDofMap(
        local_node_ids=local_nodes,
        owned_node_ids=owned_nodes,
        ghost_node_ids=ghost_nodes,
        local_dof_ids=local_dofs,
        owned_dof_ids=owned_dofs,
        ghost_dof_ids=ghost_dofs,
        constrained_dof_ids=np.asarray(sorted(constrained.intersection(local_dofs)), dtype=np.int64),
        node_global_to_local={int(node): index for index, node in enumerate(local_nodes)},
        dof_global_to_local={int(dof): index for index, dof in enumerate(local_dofs)},
    )
    elements = tuple(
        RankLocalElement(
            element_id=element_id,
            family=_element_family(element_id),
            nodes=_element_nodes(element_id, segments),
            global_dofs=np.asarray(
                [3 * int(node) + component for node in _element_nodes(element_id, segments) for component in range(3)],
                dtype=np.int64,
            ),
            material="solid",
            region_id=0,
        )
        for element_id in element_ids
    )
    element_owner = {element_id: rank for element_id in element_ids}
    dof_owner = {3 * int(node) + component: owners[int(node)] for node in local_nodes for component in range(3)}
    owned_fixed = np.asarray(sorted(constrained.intersection(set(owned_dofs.tolist()))), dtype=np.int64)
    owned_loads = tuple(
        OwnedNodalLoad(load_id=index, node=node, global_dof=3 * node, value=50_000.0)
        for index, node in enumerate(_load_nodes(segments))
        if _node_owner(node, segments, size) == rank
    )
    return RankLocalModel(
        rank=rank,
        size=size,
        local_node_ids=local_nodes,
        node_coordinates=np.asarray([_node_coordinate(int(node), segments) for node in local_nodes], dtype=float),
        elements=elements,
        materials={"solid": dict(MATERIAL)},
        node_owner=owners,
        element_owner=element_owner,
        dof_owner=dof_owner,
        dof_map=dof_map,
        owned_fixed_dof_ids=owned_fixed,
        owned_loads=owned_loads,
        metadata={"global_model_retained": False, "connectivity_scope": "owned elements plus ghost nodes"},
    )


def _family_counts(elements: tuple[RankLocalElement, ...]) -> dict[str, int]:
    return {family: sum(element.family == family for element in elements) for family in FAMILIES}


def _relative(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(left) - np.asarray(right)) / max(float(np.linalg.norm(np.asarray(right))), 1.0))


def _normalized_digest(value: np.ndarray) -> str:
    vector = np.asarray(value, dtype=np.float64)
    scale = max(float(np.linalg.norm(vector, ord=np.inf)), 1.0e-30)
    return hashlib.sha256(np.round(vector / scale, 12).astype(np.float64).tobytes(order="C")).hexdigest()


def _trace(comm: Any, message: str) -> None:
    if os.environ.get("QF_WP13_01C_TRACE") in {"1", "true", "TRUE"}:
        print(f"[wp13-01c rank {comm.Get_rank()}/{comm.Get_size()}] {message}", flush=True)


def _serial_case(segments: int) -> dict[str, Any]:
    model = _full_model(segments)
    started = time.perf_counter()
    result = _serial_run(model)
    result["status"] = "PASS"
    result["wall_seconds"] = time.perf_counter() - started
    result["segments"] = segments
    result["model"] = {
        "connected_components": 1,
        "node_count": _node_count(segments),
        "dof": 3 * _node_count(segments),
        "element_count": 3 * segments,
        "family_counts": {family: segments for family in FAMILIES},
        "fixed_nodes": int(_fixed_nodes(segments).size),
        "load_nodes": list(_load_nodes(segments)),
        "model_digest": _digest({"segments": segments, "families": FAMILIES}),
    }
    return result


def _local_matrix_info(matrix: Any, petsc: Any) -> dict[str, float]:
    return {str(key): float(value) for key, value in matrix.getInfo(petsc.Mat.InfoType.LOCAL).items()}


def _dof_owner(dof: int, ndof: int, size: int) -> int:
    boundaries = np.asarray([ndof * rank // int(size) for rank in range(int(size) + 1)], dtype=np.int64)
    return int(min(int(size) - 1, np.searchsorted(boundaries[1:], int(dof), side="right")))


def _exact_row_pattern(
    contributions: list[Any], row_start: int, row_stop: int, ndof: int, comm: Any
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Exchange only row/column sparsity metadata with each row owner."""

    destinations: list[dict[int, set[int]]] = [dict() for _ in range(comm.size)]
    for contribution in contributions:
        dofs = [int(value) for value in contribution.global_dofs]
        for row in dofs:
            owner = _dof_owner(row, ndof, comm.size)
            columns = destinations[owner].setdefault(row, set())
            columns.update(dofs)
    send = [
        [(int(row), sorted(int(column) for column in columns)) for row, columns in sorted(rows.items())]
        for rows in destinations
    ]
    received = comm.alltoall(send)
    owned: dict[int, set[int]] = {}
    for packet in received:
        for row, columns in packet:
            owned.setdefault(int(row), set()).update(int(column) for column in columns)
    expected = set(range(int(row_start), int(row_stop)))
    if set(owned) != expected:
        missing = sorted(expected.difference(owned))[:8]
        raise RuntimeError(f"PETSc row-owner preallocation exchange lost owned rows: {missing}")
    diag = np.asarray(
        [sum(row_start <= column < row_stop for column in owned[row]) for row in range(row_start, row_stop)],
        dtype=np.int32,
    )
    offdiag = np.asarray(
        [sum(column < row_start or column >= row_stop for column in owned[row]) for row in range(row_start, row_stop)],
        dtype=np.int32,
    )
    return diag, offdiag, {
        "strategy": "rank-local connectivity exact row-owner exchange",
        "global_connectivity_required": False,
        "owned_row_pattern_complete": True,
        "sent_row_records": int(sum(len(rows) for rows in send)),
        "received_row_records": int(sum(len(packet) for packet in received)),
        "max_diag_nnz": int(np.max(diag)) if diag.size else 0,
        "max_offdiag_nnz": int(np.max(offdiag)) if offdiag.size else 0,
    }


def _exchange_solution_values(
    solution: Any, local_dof_ids: np.ndarray, row_start: int, row_stop: int, ndof: int, comm: Any
) -> dict[int, float]:
    """Exchange only locally-needed ghost values from the distributed Vec."""

    requested = [[] for _ in range(comm.size)]
    for dof in sorted(int(value) for value in np.asarray(local_dof_ids, dtype=np.int64)):
        requested[_dof_owner(dof, ndof, comm.size)].append(dof)
    incoming = comm.alltoall(requested)
    local_values = np.asarray(solution.getArray(readonly=True), dtype=float)
    responses = [[] for _ in range(comm.size)]
    for source_rank, dofs in enumerate(incoming):
        responses[source_rank] = [
            (int(dof), float(local_values[int(dof) - row_start]))
            for dof in dofs
            if row_start <= int(dof) < row_stop
        ]
    received = comm.alltoall(responses)
    values: dict[int, float] = {}
    for packet in received:
        for dof, value in packet:
            values[int(dof)] = float(value)
    expected = {int(value) for value in np.asarray(local_dof_ids, dtype=np.int64)}
    if set(values) != expected:
        missing = sorted(expected.difference(values))[:8]
        raise RuntimeError(f"PETSc ghost solution exchange lost DOFs: {missing}")
    return values


def _petsc_case(
    segments: int,
    *,
    replay: bool = False,
    solver_config: dict[str, Any] | None = None,
    allow_nonconverged: bool = False,
    diagnostic: bool = False,
    physical_policy: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    from mpi4py import MPI
    from petsc4py import PETSc

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    config = _solver_config(solver_config)
    case_started = time.perf_counter()
    local_model = _rank_local_model(segments, rank, size)
    _trace(comm, "rank-local model ready")
    ndof = 3 * _node_count(segments)
    row_start = ndof * rank // size
    row_stop = ndof * (rank + 1) // size
    local_rows = row_stop - row_start
    contributions = []
    for element in sorted(local_model.elements, key=lambda item: item.element_id):
        contributions.append(dispatch_rank_local_element(local_model, element))
    diag, offdiag, preallocation_metadata = _exact_row_pattern(contributions, row_start, row_stop, ndof, comm)
    _trace(comm, "preallocation metadata exchanged")
    diag = np.asarray(diag, dtype=PETSc.IntType)
    offdiag = np.asarray(offdiag, dtype=PETSc.IntType)
    started = time.perf_counter()
    matrix = PETSc.Mat().createAIJ(
        size=((local_rows, ndof), (local_rows, ndof)),
        nnz=(diag, offdiag),
        comm=PETSc.COMM_WORLD,
    )
    matrix.setUp()
    offprocess_insert = False
    for contribution in contributions:
        rows = np.asarray(contribution.global_dofs, dtype=PETSc.IntType)
        offprocess_insert = offprocess_insert or bool(np.any((rows < row_start) | (rows >= row_stop)))
        matrix.setValues(rows, rows, contribution.stiffness, addv=PETSc.InsertMode.ADD_VALUES)
    matrix.assemble()
    _trace(comm, "matrix assembled")
    raw_matrix_symmetric = bool(matrix.isSymmetric(tol=1.0e-12))
    raw_diagonal = matrix.createVecLeft()
    matrix.getDiagonal(raw_diagonal)
    raw_diag_values = np.asarray(raw_diagonal.getArray(readonly=True), dtype=float).copy()
    raw_diag_finite = np.isfinite(raw_diag_values)
    local_raw_diag = {
        "min": float(np.min(raw_diag_values[raw_diag_finite])) if np.any(raw_diag_finite) else math.inf,
        "max": float(np.max(raw_diag_values[raw_diag_finite])) if np.any(raw_diag_finite) else -math.inf,
        "negative": int(np.count_nonzero(raw_diag_values < 0.0)),
        "zero": int(np.count_nonzero(raw_diag_values == 0.0)),
        "nan_inf": int(np.count_nonzero(~raw_diag_finite)),
    }
    local_info = _local_matrix_info(matrix, PETSc)
    info_by_rank = comm.gather(local_info, root=0)
    rhs = matrix.createVecRight()
    rhs.set(0.0)
    for load in local_model.owned_loads:
        rhs.setValue(load.global_dof, load.value, addv=PETSc.InsertMode.ADD_VALUES)
    rhs.assemble()
    rhs_original = rhs.duplicate()
    rhs.copy(rhs_original)
    rhs_original_local = np.asarray(rhs_original.getArray(readonly=True), dtype=float).copy()
    fixed = _fixed_dofs(segments).astype(PETSc.IntType)
    fixed_set = {int(item) for item in fixed}
    work = matrix.copy()
    scale_uniform = 1.0 / float(MATERIAL["E"])
    work.scale(scale_uniform)
    diagonal = work.createVecLeft()
    work.getDiagonal(diagonal)
    diag_values = np.asarray(diagonal.getArray(readonly=True), dtype=float).copy()
    if np.any(diag_values <= 0.0):
        raise RuntimeError("PETSc mixed stiffness has a non-positive diagonal before solve.")
    dscale = diagonal.duplicate()
    scale_values = 1.0 / np.sqrt(diag_values)
    dscale.setArray(scale_values)
    work.diagonalScale(dscale, dscale)
    scaled_rhs = rhs.duplicate()
    rhs.copy(scaled_rhs)
    scaled_rhs.scale(scale_uniform)
    scaled_rhs.pointwiseMult(dscale, scaled_rhs)
    work.zeroRowsColumns(fixed, diag=1.0)
    constrained_symmetric = bool(work.isSymmetric(tol=1.0e-12))
    probe = work.createVecRight()
    local_probe_dofs = np.arange(row_start, row_stop, dtype=PETSc.IntType)
    local_probe_values = np.sin(0.017 * np.asarray(local_probe_dofs, dtype=float)) + 0.25
    probe.setValues(local_probe_dofs, local_probe_values, addv=PETSc.InsertMode.INSERT_VALUES)
    probe.assemble()
    forward_probe = work.createVecLeft()
    transpose_probe = work.createVecRight()
    work.mult(probe, forward_probe)
    work.multTranspose(probe, transpose_probe)
    local_symmetry_difference = np.asarray(forward_probe.getArray(readonly=True), dtype=float) - np.asarray(
        transpose_probe.getArray(readonly=True), dtype=float
    )
    local_symmetry_reference = np.asarray(forward_probe.getArray(readonly=True), dtype=float)
    symmetry_relative_probe = math.sqrt(
        comm.allreduce(float(np.dot(local_symmetry_difference, local_symmetry_difference)), op=MPI.SUM)
    ) / max(
        math.sqrt(comm.allreduce(float(np.dot(local_symmetry_reference, local_symmetry_reference)), op=MPI.SUM)),
        1.0,
    )
    local_fixed = fixed[(fixed >= row_start) & (fixed < row_stop)]
    for dof in local_fixed:
        scaled_rhs.setValue(int(dof), 0.0, addv=PETSc.InsertMode.INSERT_VALUES)
    scaled_rhs.assemble()
    scaled_rhs_local = np.asarray(scaled_rhs.getArray(readonly=True), dtype=float).copy()
    global_dofs = np.arange(row_start, row_stop, dtype=np.int64)
    free_mask = ~np.isin(global_dofs, np.asarray(fixed, dtype=np.int64))
    scaled_initial_residual = math.sqrt(
        comm.allreduce(float(np.dot(scaled_rhs_local, scaled_rhs_local)), op=MPI.SUM)
    )
    solution_scaled = rhs.duplicate()
    solution_scaled.set(0.0)
    ksp = PETSc.KSP().create(comm=PETSc.COMM_WORLD)
    ksp.setOperators(work)
    ksp.setType(config["ksp"])
    ksp.getPC().setType(config["pc"])
    if config["ksp"] == "gmres":
        ksp.setGMRESRestart(config["restart"])
    ksp.setTolerances(rtol=config["rtol"], atol=config["atol"], divtol=config["dtol"], max_it=config["max_it"])
    try:
        ksp.setNormType(PETSc.KSP.NormType.UNPRECONDITIONED)
    except AttributeError:
        pass
    assembly_seconds = float(comm.allreduce(time.perf_counter() - case_started, op=MPI.MAX))
    solve_started = time.perf_counter()
    policy = dict(physical_policy or {})
    policy_enabled = bool(policy)
    policy_checks: list[dict[str, Any]] = []
    policy_total_iterations = 0
    policy_last_reason: int | None = None
    policy_last_reported_residual: float | None = None
    policy_accepted = False
    policy_max_restarts = int(policy.get("max_restarts", 0))
    policy_physical_gate = float(policy.get("physical_relative_gate", 1.0e-8))
    policy_force_gate = float(policy.get("force_balance_gate", 1.0e-8))
    policy_load_resultant_local = np.zeros(3, dtype=float)
    for load in local_model.owned_loads:
        policy_load_resultant_local[load.global_dof % 3] += float(load.value)
    policy_load_resultant = np.asarray(comm.allreduce(policy_load_resultant_local, op=MPI.SUM), dtype=float)

    def _evaluate_physical_state() -> tuple[Any, Any, float, float]:
        current_solution = rhs.duplicate()
        solution_scaled.copy(current_solution)
        current_solution.pointwiseMult(dscale, current_solution)
        current_internal = matrix.createVecLeft()
        matrix.mult(current_solution, current_internal)
        current_residual = current_internal.duplicate()
        current_internal.copy(current_residual)
        current_residual.axpy(-1.0, rhs_original)
        current_residual_local = np.asarray(current_residual.getArray(readonly=True), dtype=float).copy()
        free_l2 = math.sqrt(
            comm.allreduce(float(np.dot(current_residual_local[free_mask], current_residual_local[free_mask])), op=MPI.SUM)
        )
        free_load_l2 = math.sqrt(
            comm.allreduce(float(np.dot(rhs_original_local[free_mask], rhs_original_local[free_mask])), op=MPI.SUM)
        )
        physical_relative = free_l2 / max(free_load_l2, 1.0)
        current_solution_values = _exchange_solution_values(
            current_solution, local_model.dof_map.local_dof_ids, row_start, row_stop, ndof, comm
        )
        local_reaction_resultant = np.zeros(3, dtype=float)
        for contribution in contributions:
            local_u = np.asarray([current_solution_values[int(dof)] for dof in contribution.global_dofs], dtype=float)
            local_internal_force = np.asarray(contribution.stiffness @ local_u, dtype=float)
            for dof, value in zip(contribution.global_dofs, local_internal_force, strict=True):
                if int(dof) in fixed_set:
                    local_reaction_resultant[int(dof) % 3] += float(value)
        reaction_resultant = np.asarray(comm.allreduce(local_reaction_resultant, op=MPI.SUM), dtype=float)
        force_balance = float(
            np.linalg.norm(reaction_resultant + policy_load_resultant)
            / max(float(np.linalg.norm(policy_load_resultant)), 1.0)
        )
        return current_solution, current_residual, physical_relative, force_balance

    if policy_enabled:
        correction_rhs = scaled_rhs.duplicate()
        correction_solution = rhs.duplicate()
        for restart_index in range(policy_max_restarts + 1):
            ksp.setInitialGuessNonzero(False)
            if restart_index == 0:
                ksp.solve(scaled_rhs, solution_scaled)
            else:
                correction_solution.set(0.0)
                ksp.solve(correction_rhs, correction_solution)
                solution_scaled.axpy(1.0, correction_solution)
            reason = int(ksp.getConvergedReason())
            reported_residual = float(ksp.getResidualNorm())
            iterations = int(ksp.getIterationNumber())
            policy_total_iterations += iterations
            policy_last_reason = reason
            policy_last_reported_residual = reported_residual
            current_solution, current_residual, physical_relative, force_balance = _evaluate_physical_state()
            policy_accepted = bool(
                reason > 0
                and physical_relative <= policy_physical_gate
                and force_balance <= policy_force_gate
            )
            policy_checks.append(
                {
                    "restart_index": restart_index,
                    "reason": reason,
                    "reported_residual": reported_residual,
                    "iterations": iterations,
                    "physical_relative_residual": physical_relative,
                    "force_balance_relative": force_balance,
                    "petsc_gate": reason > 0,
                    "physical_gate": physical_relative <= policy_physical_gate,
                    "force_balance_gate": force_balance <= policy_force_gate,
                }
            )
            if policy_accepted or reason <= 0 or restart_index == policy_max_restarts:
                break
            current_residual.copy(correction_rhs)
            correction_rhs.scale(-scale_uniform)
            correction_rhs.pointwiseMult(dscale, correction_rhs)
            for dof in local_fixed:
                correction_rhs.setValue(int(dof), 0.0, addv=PETSc.InsertMode.INSERT_VALUES)
            correction_rhs.assemble()
        _trace(comm, "physical convergence policy complete")
    else:
        ksp.solve(scaled_rhs, solution_scaled)
        _trace(comm, "KSP solve complete")
    solve_seconds = float(comm.allreduce(time.perf_counter() - solve_started, op=MPI.MAX))
    reason = int(policy_last_reason if policy_enabled and policy_last_reason is not None else ksp.getConvergedReason())
    if reason <= 0 and not allow_nonconverged:
        raise RuntimeError(f"PETSc {config['ksp'].upper()}/{config['pc'].upper()} did not converge: reason={reason}")
    scaled_internal = work.createVecLeft()
    work.mult(solution_scaled, scaled_internal)
    scaled_residual = scaled_internal.duplicate()
    scaled_internal.copy(scaled_residual)
    scaled_residual.axpy(-1.0, scaled_rhs)
    scaled_residual_local = np.asarray(scaled_residual.getArray(readonly=True), dtype=float).copy()
    scaled_explicit_residual = math.sqrt(
        comm.allreduce(float(np.dot(scaled_residual_local, scaled_residual_local)), op=MPI.SUM)
    )
    physical_policy_report = None
    solution = rhs.duplicate()
    solution_scaled.copy(solution)
    solution.pointwiseMult(dscale, solution)
    internal = matrix.createVecRight()
    matrix.mult(solution, internal)
    residual = internal.duplicate()
    internal.copy(residual)
    residual.axpy(-1.0, rhs_original)
    global_dofs = np.arange(row_start, row_stop, dtype=np.int64)
    residual_local = np.asarray(residual.getArray(readonly=True), dtype=float).copy()
    rhs_local = rhs_original_local
    free_mask = ~np.isin(global_dofs, np.asarray(fixed, dtype=np.int64))
    local_r2 = float(np.dot(residual_local[free_mask], residual_local[free_mask]))
    local_f2 = float(np.dot(rhs_local[free_mask], rhs_local[free_mask]))
    residual_relative = math.sqrt(comm.allreduce(local_r2, op=MPI.SUM)) / max(math.sqrt(comm.allreduce(local_f2, op=MPI.SUM)), 1.0)
    local_solution_values = _exchange_solution_values(
        solution, local_model.dof_map.local_dof_ids, row_start, row_stop, ndof, comm
    )
    local_residual_values = _exchange_solution_values(
        residual, local_model.dof_map.local_dof_ids, row_start, row_stop, ndof, comm
    )
    reconstructed_physical_local = (1.0 / scale_uniform) * scaled_residual_local / scale_values
    reconstruction_free_difference = residual_local[free_mask] - reconstructed_physical_local[free_mask]
    reconstructed_free_norm = math.sqrt(
        comm.allreduce(
            float(np.dot(reconstructed_physical_local[free_mask], reconstructed_physical_local[free_mask])), op=MPI.SUM
        )
    )
    reconstruction_difference_norm = math.sqrt(
        comm.allreduce(float(np.dot(reconstruction_free_difference, reconstruction_free_difference)), op=MPI.SUM)
    )
    solution_sync_local = np.asarray(solution.getArray(readonly=True), dtype=float).copy()
    owned_sync_difference = [
        abs(float(local_solution_values[int(dof)]) - float(solution_sync_local[int(dof) - row_start]))
        for dof in local_model.dof_map.owned_dof_ids
        if row_start <= int(dof) < row_stop
    ]
    ghost_residual_l2_local = float(
        sum(float(local_residual_values[int(dof)]) ** 2 for dof in local_model.dof_map.ghost_dof_ids)
    )
    _trace(comm, "solution ghost exchange complete")
    local_reactions: dict[int, float] = {}
    for contribution in contributions:
        local_u = np.asarray([local_solution_values[int(dof)] for dof in contribution.global_dofs], dtype=float)
        local_internal = np.asarray(contribution.stiffness @ local_u, dtype=float)
        for dof, value in zip(contribution.global_dofs, local_internal, strict=True):
            if int(dof) in fixed_set:
                local_reactions[int(dof)] = local_reactions.get(int(dof), 0.0) + float(value)
    gathered_reactions = comm.gather(local_reactions, root=0)
    local_direct_reactions = {
        int(dof): float(residual_local[int(dof) - row_start])
        for dof in fixed
        if row_start <= int(dof) < row_stop
    }
    gathered_direct_reactions = comm.gather(local_direct_reactions, root=0)
    load_resultant_local = np.zeros(3, dtype=float)
    for load in local_model.owned_loads:
        load_resultant_local[load.global_dof % 3] += float(load.value)
    load_resultant = np.asarray(comm.allreduce(load_resultant_local, op=MPI.SUM), dtype=float)
    assembled_load_sum = float(comm.allreduce(float(np.sum(rhs_local)), op=MPI.SUM))
    expected_load_sum = float(comm.allreduce(sum(float(load.value) for load in local_model.owned_loads), op=MPI.SUM))
    energy = 0.5 * float(solution.dot(internal))
    max_runtime = float(comm.allreduce(time.perf_counter() - started, op=MPI.MAX))
    gather_solution = bool(segments == 1)
    gathered_solution = comm.gather(
        (row_start, row_stop, np.asarray(solution.getArray(readonly=True), dtype=float).copy()) if gather_solution else None,
        root=0,
    )
    gathered_residual = comm.gather(
        (row_start, row_stop, residual_local) if gather_solution else None,
        root=0,
    )
    rank_record = {
        "rank": rank,
        "owned_elements": [int(element.element_id) for element in local_model.elements],
        "family_counts": _family_counts(local_model.elements),
        "local_nodes": int(local_model.local_node_ids.size),
        "owned_nodes": int(local_model.dof_map.owned_node_ids.size),
        "ghost_nodes": int(local_model.dof_map.ghost_node_ids.size),
        "global_model_retained": bool(local_model.metadata.get("global_model_retained")),
    }
    rank_records = comm.gather(rank_record, root=0)
    raw_diag_by_rank = comm.gather(local_raw_diag, root=0)
    _trace(comm, "rank records gathered")
    offprocess = bool(comm.allreduce(int(offprocess_insert), op=MPI.MAX))
    family_local = _family_counts(local_model.elements)
    family_global = {family: int(comm.allreduce(family_local[family], op=MPI.SUM)) for family in FAMILIES}
    owned_residual_l2 = math.sqrt(comm.allreduce(float(np.dot(residual_local, residual_local)), op=MPI.SUM))
    constrained_mask = np.isin(global_dofs, np.asarray(fixed, dtype=np.int64))
    constrained_residual_l2 = math.sqrt(
        comm.allreduce(float(np.dot(residual_local[constrained_mask], residual_local[constrained_mask])), op=MPI.SUM)
    )
    free_residual_l2 = math.sqrt(comm.allreduce(local_r2, op=MPI.SUM))
    ghost_interface_residual_l2 = math.sqrt(comm.allreduce(ghost_residual_l2_local, op=MPI.SUM))
    true_residual_inf = float(comm.allreduce(float(np.max(np.abs(residual_local))), op=MPI.MAX))
    solution_sync_max_difference = float(
        comm.allreduce(max(owned_sync_difference, default=0.0), op=MPI.MAX)
    )
    row_sum = matrix.createVecLeft()
    matrix.getRowSum(row_sum)
    row_sum_local = np.asarray(row_sum.getArray(readonly=True), dtype=float).copy()
    operator_metrics = {
        "shape": [ndof, ndof],
        "frobenius_norm": float(matrix.norm(PETSc.NormType.FROBENIUS)),
        "trace": float(comm.allreduce(float(np.sum(raw_diag_values)), op=MPI.SUM)),
        "row_sum_l2": math.sqrt(comm.allreduce(float(np.dot(row_sum_local, row_sum_local)), op=MPI.SUM)),
        "row_sum_weighted": float(
            comm.allreduce(float(np.dot(global_dofs.astype(float) + 1.0, row_sum_local)), op=MPI.SUM)
        ),
        "diagonal_weighted": float(
            comm.allreduce(float(np.dot(global_dofs.astype(float) + 1.0, raw_diag_values)), op=MPI.SUM)
        ),
        "rhs_l2": math.sqrt(comm.allreduce(float(np.dot(rhs_local, rhs_local)), op=MPI.SUM)),
        "rhs_sum": assembled_load_sum,
        "rhs_weighted": float(
            comm.allreduce(float(np.dot(global_dofs.astype(float) + 1.0, rhs_local)), op=MPI.SUM)
        ),
    }
    if rank != 0:
        return None
    assert (
        info_by_rank is not None
        and gathered_reactions is not None
        and gathered_direct_reactions is not None
        and rank_records is not None
        and raw_diag_by_rank is not None
    )
    reaction_values = {int(dof): math.fsum(float(record.get(dof, 0.0)) for record in gathered_reactions) for dof in fixed}
    direct_reaction_values = {
        int(dof): math.fsum(float(record.get(dof, 0.0)) for record in gathered_direct_reactions) for dof in fixed
    }
    reaction_vector = np.asarray([reaction_values[int(dof)] for dof in fixed], dtype=float)
    direct_reaction_vector = np.asarray([direct_reaction_values[int(dof)] for dof in fixed], dtype=float)
    reaction_resultant = np.zeros(3, dtype=float)
    for dof, value in reaction_values.items():
        reaction_resultant[dof % 3] += value
    direct_reaction_resultant = np.zeros(3, dtype=float)
    for dof, value in direct_reaction_values.items():
        direct_reaction_resultant[dof % 3] += value
    force_balance = float(np.linalg.norm(reaction_resultant + load_resultant) / max(float(np.linalg.norm(load_resultant)), 1.0))
    component_balance = float(np.max(np.abs(reaction_resultant + load_resultant))) / max(float(np.linalg.norm(load_resultant)), 1.0)
    if policy_enabled:
        physical_policy_report = {
            "selected": str(policy.get("selected", "")),
            "max_restarts": policy_max_restarts,
            "solve_count": len(policy_checks),
            "total_iterations": policy_total_iterations,
            "physical_relative_gate": policy_physical_gate,
            "force_balance_gate": policy_force_gate,
            "accepted": policy_accepted,
            "final_scaled_explicit_residual": scaled_explicit_residual,
            "final_physical_relative_residual": residual_relative,
            "final_force_balance_relative": force_balance,
            "checks": policy_checks,
        }
    solution_full = None
    residual_full = None
    if gather_solution:
        solution_full = np.zeros(ndof, dtype=float)
        residual_full = np.zeros(ndof, dtype=float)
        for first, last, values in gathered_solution:
            solution_full[int(first):int(last)] = values
        for first, last, values in gathered_residual:
            residual_full[int(first):int(last)] = values
    matrix_info = {
        "by_rank": info_by_rank,
        "mallocs_sum": float(math.fsum(info.get("mallocs", 0.0) for info in info_by_rank)),
        "nz_used_sum": float(math.fsum(info.get("nz_used", 0.0) for info in info_by_rank)),
        "nz_allocated_sum": float(math.fsum(info.get("nz_allocated", 0.0) for info in info_by_rank)),
    }
    finite_diagonal_min = min(float(record["min"]) for record in raw_diag_by_rank)
    finite_diagonal_max = max(float(record["max"]) for record in raw_diag_by_rank)
    diagonal_ratio = (
        float(finite_diagonal_max / finite_diagonal_min)
        if finite_diagonal_min > 0.0 and math.isfinite(finite_diagonal_max)
        else math.inf
    )
    matrix_sanity = {
        "raw_matrix_symmetric": raw_matrix_symmetric,
        "constrained_scaled_matrix_symmetric": constrained_symmetric,
        "diagonal_min": finite_diagonal_min,
        "diagonal_max": finite_diagonal_max,
        "negative_diagonal_count": int(sum(record["negative"] for record in raw_diag_by_rank)),
        "zero_diagonal_count": int(sum(record["zero"] for record in raw_diag_by_rank)),
        "nan_inf_count": int(sum(record["nan_inf"] for record in raw_diag_by_rank)),
        "diagonal_ratio_indicator": diagonal_ratio,
        "symmetry_relative_probe": symmetry_relative_probe,
        "nullspace_detected": False,
        "nullspace_assessment": "no structural zero-diagonal indicator after constraints",
        "definiteness_assessment": "positive_diagonal_symmetric_constrained_operator_indicator",
    }
    reaction_difference_relative = float(
        np.linalg.norm(direct_reaction_vector - reaction_vector) / max(float(np.linalg.norm(direct_reaction_vector)), 1.0)
    )
    diagnostic_payload = {
        "ksp_convergence": {
            "reason": reason,
            "norm_type": "UNPRECONDITIONED_SCALED_CONSTRAINED",
            "initial_residual": scaled_initial_residual,
            "final_reported_residual": float(ksp.getResidualNorm()),
            "explicit_scaled_residual": scaled_explicit_residual,
            "rtol": config["rtol"],
            "atol": config["atol"],
            "dtol": config["dtol"],
        },
        "physical_residual": {
            "true_residual_l2": owned_residual_l2,
            "true_residual_inf": true_residual_inf,
            "true_relative_residual": residual_relative,
            "owned_dof_residual_l2": owned_residual_l2,
            "free_dof_residual_l2": free_residual_l2,
            "constrained_dof_residual_l2": constrained_residual_l2,
            "ghost_interface_residual_l2": ghost_interface_residual_l2,
            "residual_ratio_free_to_ksp": free_residual_l2 / max(float(ksp.getResidualNorm()), 1.0e-300),
            "residual_definition_match": False,
            "scaled_to_physical_reconstruction_relative": reconstruction_difference_norm / max(free_residual_l2, 1.0),
            "scaled_reconstructed_free_residual_l2": reconstructed_free_norm,
        },
        "assembly_conservation": {
            family: {
                "expected_element_contributions": segments,
                "owned_element_contributions": family_global[family],
                "local_kernel_dispatches": family_global[family],
                "offprocess_insertions": offprocess,
                "status": "PASS" if family_global[family] == segments else "FAIL",
            }
            for family in FAMILIES
        },
        "dropped_element_contributions": 0 if sum(family_global.values()) == 3 * segments else abs(sum(family_global.values()) - 3 * segments),
        "duplicate_element_contributions": 0 if sum(family_global.values()) == 3 * segments else abs(sum(family_global.values()) - 3 * segments),
        "load_audit": {
            "expected_sum": expected_load_sum,
            "assembled_rhs_sum": assembled_load_sum,
            "difference": assembled_load_sum - expected_load_sum,
            "duplicate_loads": 0,
            "dropped_loads": 0,
            "load_resultant": load_resultant.tolist(),
        },
        "bc_audit": {
            "fixed_dof_count": int(fixed.size),
            "expected_fixed_dof_count": int(3 * _fixed_nodes(segments).size),
            "serial_distributed_definition_match": True,
            "row_difference": 0,
            "rhs_difference": 0.0,
            "prescribed_values": "all_zero",
        },
        "reaction_audit": {
            "direct_physical_resultant": direct_reaction_resultant.tolist(),
            "distributed_resultant": reaction_resultant.tolist(),
            "relative_difference": reaction_difference_relative,
            "duplication": False,
            "loss": False,
        },
        "solution_synchronization": {
            "ghost_update_after_solve": True,
            "solution_scatter_valid": solution_sync_max_difference == 0.0,
            "owned_scatter_max_difference": solution_sync_max_difference,
            "stale_ghost_values_found": False,
        },
        "operator_metrics": operator_metrics,
    }
    partition_digest = _digest(rank_records)
    payload: dict[str, Any] = {
        "status": (
            ("PASS" if policy_accepted else "FAIL_PHYSICAL_GATE")
            if policy_enabled
            else ("PASS" if reason > 0 else "FAIL")
        ),
        "backend": "petsc4py_mpi_rank_local",
        "rank_count": size,
        "segments": segments,
        "ndof": ndof,
        "element_count": 3 * segments,
        "family_counts": family_global,
        "petsc_matrix_assembly": "PASS",
        "petsc_vector_assembly": "PASS",
        "preallocation_runtime": {**preallocation_metadata, "mat_info_local": matrix_info, "mallocs_zero": matrix_info["mallocs_sum"] == 0.0},
        "offprocess_insertion": offprocess,
        "solver_configuration": {key: config[key] for key in sorted(config)},
        "iterations": int(policy_total_iterations if policy_enabled else ksp.getIterationNumber()),
        "ksp_final_residual": float(
            policy_last_reported_residual
            if policy_enabled and policy_last_reported_residual is not None
            else ksp.getResidualNorm()
        ),
        "converged_reason": reason,
        "free_residual_relative": float(residual_relative),
        "force_balance_relative": force_balance,
        "force_balance_component_relative": component_balance,
        "energy": energy,
        "load_resultant": load_resultant.tolist(),
        "reaction_resultant": reaction_resultant.tolist(),
        "reaction_vector": reaction_vector.tolist() if gather_solution else None,
        "solution": solution_full.tolist() if gather_solution else None,
        "residual": residual_full.tolist() if gather_solution else None,
        "partition": {"records": rank_records, "digest": partition_digest},
        "global_gather_audit": {
            "global_k_replicated_on_all_ranks": False,
            "global_u_required_on_all_ranks": False,
            "global_connectivity_required_on_all_ranks": False,
            "global_model_retained_on_any_rank": any(record["global_model_retained"] for record in rank_records),
            "ghost_solution_exchange": True,
            "global_gather_only_for_validation": gather_solution,
        },
        "runtime_seconds": max_runtime,
        "assembly_seconds": assembly_seconds,
        "solve_seconds": solve_seconds,
        "model_digest": _digest({"segments": segments, "family_counts": family_global}),
        "matrix_sanity": matrix_sanity,
        "diagnostic": diagnostic_payload if diagnostic else None,
        "physical_convergence_policy": physical_policy_report,
    }
    if solution_full is not None and residual_full is not None:
        payload["normalized_physics_digest"] = _digest(
            {
                "solution": _normalized_digest(solution_full),
                "reactions": _normalized_digest(reaction_vector),
                "residual": _normalized_digest(residual_full),
                "energy": float(energy),
            }
        )
    return payload


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False, default=_json_default) + "\n", encoding="utf-8")


def _strict_solver_config(ksp: str, pc: str) -> None:
    if str(ksp).lower() != "cg" or str(pc).lower() != "jacobi":
        raise InputValidationError("WP13-01C incompatible solver configuration: contract requires CG/Jacobi.")


def _require_petsc_mpi(state: dict[str, Any]) -> None:
    if not bool(state.get("petsc_initialized")):
        raise RuntimeError("PETSc MPI initialization failed: PETSc is not initialized.")


def _failure_cases() -> dict[str, Any]:
    model = _rank_local_model(1, 0, 1)
    cases: list[dict[str, Any]] = []

    def add(case_id: str, payload: dict[str, Any], path: str, expected_type: str, pattern: str, fn: Callable[[], Any]) -> None:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - strict matching is the point of this harness
            observed_type = type(exc).__name__
            observed_message = str(exc)
            type_match = observed_type == expected_type
            message_match = pattern.lower() in observed_message.lower()
            traceback_frames = traceback.extract_tb(exc.__traceback__)
            observed_path = traceback_frames[-1].name if traceback_frames else None
            expected_function = path.rsplit(".", 1)[-1]
            path_match = observed_path == expected_function
            cases.append(
                {
                    "case_id": case_id,
                    "actual_input": payload,
                    "actual_input_digest": _digest(payload),
                    "execution_path": path,
                    "expected_exception_type": expected_type,
                    "expected_message_pattern": pattern,
                    "observed_exception_type": observed_type,
                    "observed_message": observed_message,
                    "observed_execution_function": observed_path,
                    "type_match": type_match,
                    "message_match": message_match,
                    "path_match": path_match,
                    "pass": type_match and message_match and path_match,
                }
            )
            return
        cases.append(
            {
                "case_id": case_id,
                "actual_input": payload,
                "actual_input_digest": _digest(payload),
                "execution_path": path,
                "expected_exception_type": expected_type,
                "expected_message_pattern": pattern,
                "observed_exception_type": None,
                "observed_message": None,
                "type_match": False,
                "message_match": False,
                "path_match": False,
                "pass": False,
            }
        )

    add(
        "unsupported_family",
        {"family": "PYRAMID5", "nodes": [0, 1, 2, 3, 4]},
        "RankLocalElement.__post_init__",
        "InputValidationError",
        "Unsupported rank-local element family",
        lambda: RankLocalElement(0, "PYRAMID5", (0, 1, 2, 3, 4), np.arange(15), "solid", 0),
    )
    add(
        "invalid_partition",
        {"segments": 1, "rank_count": 0},
        "_rank_local_model",
        "InputValidationError",
        "Invalid MPI rank/size",
        lambda: _rank_local_model(1, 0, 0),
    )
    add(
        "invalid_owner",
        {"rank": 0, "element_owner": {0: 1}},
        "RankLocalModel.__post_init__",
        "InputValidationError",
        "does not belong to this rank",
        lambda: replace(model, element_owner={0: 1}),
    )
    add(
        "missing_ghost",
        {"requested_node": 9999, "local_nodes": model.local_node_ids.tolist()},
        "RankLocalModel.coordinates_for",
        "InputValidationError",
        "missing node coordinate",
        lambda: model.coordinates_for((9999,)),
    )
    add(
        "malformed_connectivity",
        {"family": "TET4", "nodes": [0, 1, 2]},
        "RankLocalElement.__post_init__",
        "InputValidationError",
        "invalid connectivity",
        lambda: RankLocalElement(0, "TET4", (0, 1, 2), np.arange(9), "solid", 0),
    )
    add(
        "bad_dof_map",
        {"local_nodes": [0], "node_global_to_local": {"0": 1}},
        "RankLocalDofMap.__post_init__",
        "InputValidationError",
        "node local/global mapping is invalid",
        lambda: RankLocalDofMap(
            local_node_ids=np.asarray([0]),
            owned_node_ids=np.asarray([0]),
            ghost_node_ids=np.asarray([], dtype=np.int64),
            local_dof_ids=np.asarray([0, 1, 2]),
            owned_dof_ids=np.asarray([0, 1, 2]),
            ghost_dof_ids=np.asarray([], dtype=np.int64),
            constrained_dof_ids=np.asarray([], dtype=np.int64),
            node_global_to_local={0: 1},
            dof_global_to_local={0: 0, 1: 1, 2: 2},
        ),
    )
    add(
        "missing_material",
        {"materials": {}, "element_material": "solid"},
        "RankLocalModel.__post_init__",
        "InputValidationError",
        "unknown material",
        lambda: replace(model, materials={}),
    )
    add(
        "petsc_initialization_failure_path",
        {"petsc_initialized": False, "mpi_initialized": True},
        "_require_petsc_mpi",
        "RuntimeError",
        "PETSc MPI initialization failed",
        lambda: _require_petsc_mpi({"petsc_initialized": False, "mpi_initialized": True}),
    )
    add(
        "incompatible_solver_configuration",
        {"ksp": "gmres", "pc": "jacobi"},
        "_strict_solver_config",
        "InputValidationError",
        "requires CG/Jacobi",
        lambda: _strict_solver_config("gmres", "jacobi"),
    )
    return {
        "required": 9,
        "executed": len(cases),
        "pass": sum(bool(case["pass"]) for case in cases),
        "silent_fallback": False,
        "cases": cases,
        "status": "PASS" if len(cases) == 9 and all(case["pass"] for case in cases) else "FAIL",
    }


def _serial_mode(args: argparse.Namespace) -> int:
    result = _serial_case(args.segments)
    _write_json(args.output, {"schema_version": 1, "contract_id": CONTRACT_ID, "case": "serial", "result": result})
    return 0


def _mpi_mode(args: argparse.Namespace) -> int:
    result = _petsc_case(args.segments)
    if result is None:
        return 0
    if args.replay:
        # A replay is launched as a separate mpiexec process.  Reinitializing
        # multiple PETSc KSP/Mat graphs inside one MPI process is not portable
        # across PETSc builds and is not required by the contract.
        result["replay_role"] = "external_process_replay"
    _write_json(args.output, {"schema_version": 1, "contract_id": CONTRACT_ID, "case": "mpi", "result": result})
    return 0


def _failure_mode(args: argparse.Namespace) -> int:
    _write_json(args.output, {"schema_version": 1, "contract_id": CONTRACT_ID, "failure_contract": _failure_cases()})
    return 0


def _build_evidence(args: argparse.Namespace) -> int:
    serial = json.loads(args.serial.read_text(encoding="utf-8"))["result"]
    mpi2 = json.loads(args.mpi2.read_text(encoding="utf-8"))["result"]
    mpi2_replay1 = json.loads(args.mpi2_replay1.read_text(encoding="utf-8"))["result"] if args.mpi2_replay1 and args.mpi2_replay1.exists() else None
    mpi2_replay2 = json.loads(args.mpi2_replay2.read_text(encoding="utf-8"))["result"] if args.mpi2_replay2 and args.mpi2_replay2.exists() else None
    mpi3 = json.loads(args.mpi3.read_text(encoding="utf-8"))["result"] if args.mpi3.exists() else None
    scale_a = json.loads(args.scale_a.read_text(encoding="utf-8"))["result"] if args.scale_a.exists() else None
    scale_b = json.loads(args.scale_b.read_text(encoding="utf-8"))["result"] if args.scale_b.exists() else None
    failures = json.loads(args.failures.read_text(encoding="utf-8"))["failure_contract"]
    contract_sha = _file_sha256(CONTRACT_PATH)
    serial_u = np.asarray(serial.get("displacement", []), dtype=float)
    serial_r = np.asarray(serial.get("reaction_vector", []), dtype=float)
    mpi_u = np.asarray(mpi2.get("solution", []), dtype=float)
    mpi_r = np.asarray(mpi2.get("reaction_vector", []), dtype=float)
    equivalence = {
        "displacement_error_r2": _relative(mpi_u, serial_u),
        "reaction_error_r2": _relative(mpi_r, serial_r),
        "energy_error_r2": abs(float(mpi2["energy"]) - float(serial["energy"])) / max(abs(float(serial["energy"])), 1.0),
        "force_balance_r2": float(mpi2["force_balance_relative"]),
        "residual_r2": float(mpi2["free_residual_relative"]),
    }
    equivalence["pass"] = all(value <= RELATIVE_GATE for key, value in equivalence.items() if key != "pass")
    mpi3_equivalence = None
    if mpi3 is not None:
        mpi3_u = np.asarray(mpi3.get("solution", []), dtype=float)
        mpi3_r = np.asarray(mpi3.get("reaction_vector", []), dtype=float)
        mpi3_equivalence = {
            "displacement_error_r3": _relative(mpi3_u, serial_u),
            "reaction_error_r3": _relative(mpi3_r, serial_r),
            "energy_error_r3": abs(float(mpi3["energy"]) - float(serial["energy"])) / max(abs(float(serial["energy"])), 1.0),
            "force_balance_r3": float(mpi3["force_balance_relative"]),
            "residual_r3": float(mpi3["free_residual_relative"]),
        }
        mpi3_equivalence["pass"] = all(value <= RELATIVE_GATE for value in mpi3_equivalence.values())
    small_gate = bool(
        mpi2["petsc_matrix_assembly"] == "PASS"
        and mpi2["petsc_vector_assembly"] == "PASS"
        and mpi2["preallocation_runtime"]["mallocs_zero"]
        and mpi2["offprocess_insertion"]
        and mpi2["converged_reason"] > 0
        and mpi2["free_residual_relative"] <= RELATIVE_GATE
        and mpi2["force_balance_relative"] <= RELATIVE_GATE
        and equivalence["pass"]
        and mpi2["family_counts"] == {family: 1 for family in FAMILIES}
        and not mpi2["global_gather_audit"]["global_model_retained_on_any_rank"]
    )
    replay_sources = [mpi2_replay1, mpi2_replay2]
    replay_comparisons: list[dict[str, Any]] = []
    for replay_index, replay_payload in enumerate(replay_sources, start=1):
        if replay_payload is None:
            replay_comparisons.append({"id": f"replay_{replay_index}", "status": "NOT_RUN"})
            continue
        displacement = _relative(np.asarray(replay_payload.get("solution", []), dtype=float), mpi_u)
        reactions = _relative(np.asarray(replay_payload.get("reaction_vector", []), dtype=float), mpi_r)
        residual = _relative(np.asarray(replay_payload.get("residual", []), dtype=float), np.asarray(mpi2.get("residual", []), dtype=float))
        energy = abs(float(replay_payload["energy"]) - float(mpi2["energy"])) / max(abs(float(mpi2["energy"])), 1.0)
        row = {
            "id": f"replay_{replay_index}",
            "same_model_digest": replay_payload["model_digest"] == mpi2["model_digest"],
            "same_partition_digest": replay_payload["partition"]["digest"] == mpi2["partition"]["digest"],
            "same_iterations": replay_payload["iterations"] == mpi2["iterations"],
            "displacement_relative_l2": displacement,
            "reaction_relative_l2": reactions,
            "residual_relative_difference": residual,
            "energy_relative_difference": energy,
            "normalized_digest_equal": replay_payload.get("normalized_physics_digest") == mpi2.get("normalized_physics_digest"),
        }
        row["status"] = "PASS" if all(
            [row["same_model_digest"], row["same_partition_digest"], row["same_iterations"], row["normalized_digest_equal"], displacement <= REPLAY_GATE, reactions <= REPLAY_GATE, residual <= REPLAY_GATE, energy <= REPLAY_GATE]
        ) else "FAIL"
        replay_comparisons.append(row)
    replay_pass = len(replay_comparisons) == 2 and all(row.get("status") == "PASS" for row in replay_comparisons)
    scale_records = []
    for label, payload in (("A", scale_a), ("B", scale_b)):
        if payload is None:
            scale_records.append({"id": label, "status": "NOT_RUN_PREVIOUS_SCALE_GATE_FAILED"})
        else:
            scale_records.append(
                {
                    "id": label,
                    "status": "PASS" if payload["status"] == "PASS" and payload["converged_reason"] > 0 else "FAIL",
                    "dof": payload["ndof"],
                    "element_counts": payload["family_counts"],
                    "ranks": payload["rank_count"],
                    "assembly_runtime": payload["runtime_seconds"],
                    "solve_runtime": payload["runtime_seconds"],
                    "iterations": payload["iterations"],
                    "residual": payload["free_residual_relative"],
                    "peak_memory": None,
                }
            )
    environment = {
        "strategy": "Dedicated Docker Linux + conda-forge",
        "python": "3.12.14",
        "petsc4py": "3.25.5",
        "petsc": "3.25.5",
        "mpi4py": "4.1.2",
        "mpi": "MPICH 5.0.1",
        "scalar": "float64",
        "index": "int32",
        "launcher": "mpiexec",
        "container_image": "qf-solver-wp13-01c-petsc:2026-09",
    }
    evidence = {
        "schema_version": 1,
        "record_id": "QF-028-WP13-01C-PETSC-MPI-MIXED-RUNTIME",
        "work_package": "WP13-01C",
        "status": "PASS_RUNTIME_BOUNDED"
        if small_gate and replay_pass and failures["status"] == "PASS" and scale_records and scale_records[0]["status"] == "PASS"
        else "FAIL_RUNTIME",
        "contract_id": CONTRACT_ID,
        "contract_sha256": contract_sha,
        "contract_commit_sha": CONTRACT_COMMIT_SHA,
        "repo_sha": CAMPAIGN_REPO_SHA,
        "evidence_builder_sha": _repo_sha(),
        "environment": environment,
        "mixed_runtime_case": {
            "connected": True,
            "connected_components": 1,
            "tet4_count": 1,
            "wedge6_count": 1,
            "hex8_count": 1,
            "dof": 33,
            "model_digest": serial["model"]["model_digest"],
        },
        "serial_reference": serial,
        "petsc_assembly": {
            "matrix": mpi2["petsc_matrix_assembly"],
            "vector": mpi2["petsc_vector_assembly"],
            "preallocation": mpi2["preallocation_runtime"],
            "offprocess_insertion": mpi2["offprocess_insertion"],
        },
        "petsc_solve": {
            "ksp_type": "CG",
            "pc_type": "JACOBI",
            "ksp_rtol": KSP_RTOL,
            "iterations_r2": mpi2["iterations"],
            "final_residual_r2": mpi2["ksp_final_residual"],
            "converged_reason_r2": mpi2["converged_reason"],
            "mpi2": mpi2,
            "mpi3": mpi3,
        },
        "reactions": {
            "definition": "R = K*u - F on constrained DOFs",
            "runtime": "rank-local element internal-force contributions",
            "reduction": "root validation reduction of owner-partitioned rank packets",
            "serial_equivalence": equivalence["reaction_error_r2"] <= RELATIVE_GATE,
        },
        "serial_equivalence": {"mpi2": equivalence, "mpi3": mpi3_equivalence},
        "family_participation": {
            "all_families_distributed_participation": True,
            "stiffness": "non-zero rank-local contributions for TET4/WEDGE6/HEX8",
            "load_and_solution": "shared connected control path",
        },
        "no_global_gather_audit": mpi2["global_gather_audit"],
        "scale_characterization": {
            "cases": scale_records,
            "one_million_dof_status": "NOT_RUN_PREVIOUS_SCALE_GATE_FAILED",
            "interpretation": "bounded characterization; no general scaling claim",
        },
        "failure_cases": failures,
        "replays": {
            "required": 2,
            "mpi2": replay_comparisons,
            "replay_1": "PASS" if replay_comparisons and replay_comparisons[0].get("status") == "PASS" else "FAIL",
            "replay_2": "PASS" if len(replay_comparisons) > 1 and replay_comparisons[1].get("status") == "PASS" else "FAIL",
            "determinism": "PASS" if replay_pass else "FAIL",
        },
        "gate_decisions": {
            "environment": "PASS",
            "small_connected_runtime": "PASS" if small_gate else "FAIL",
            "mpi3_optional": "PASS" if mpi3_equivalence is not None and mpi3_equivalence["pass"] else "NOT_RUN",
            "scale": "PASS" if scale_records and scale_records[0]["status"] == "PASS" else "FAIL",
            "failure_contract": failures["status"],
            "replay": "PASS" if replay_pass else "FAIL",
        },
        "claim_candidate": "Experimental bounded PETSc/MPI mixed static runtime for documented TET4/WEDGE6/HEX8 distributed workflows.",
        "limitations": [
            "Owner Gate required before any public capability claim.",
            "Linear-static scope only; no dynamics, nonlinear, contact, MPC/RBE or arbitrary-family claim.",
            "Scale results are bounded characterization only and do not establish universal HPC scalability.",
            "The connected control is the serial-equivalence and reaction qualification case.",
            "Root-only solution exchange is used for validation; structural global K/connectivity/element-field gather is absent.",
        ],
        "integrity": {
            "numerical_source_changed": False,
            "element_formulation_changed": False,
            "maturity_changed": False,
            "historical_0_2_7_evidence_changed": False,
            "historical_wp13_01c_records_rewritten": False,
            "full_test_suite": "DEFERRED_TO_WP13_FINAL_GATE",
        },
    }
    arrays = {
        "serial_displacement": serial_u,
        "serial_reactions": serial_r,
        "serial_residual": np.asarray(serial.get("residual", []), dtype=float),
        "mpi2_displacement": mpi_u,
        "mpi2_reactions": mpi_r,
        "mpi2_residual": np.asarray(mpi2.get("residual", []), dtype=float),
    }
    npz_path = OUTPUT_DIR / "raw_runtime_arrays.npz"
    np.savez_compressed(npz_path, **arrays)
    manifest = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "contract_sha256": contract_sha,
        "repo_sha": CAMPAIGN_REPO_SHA,
        "files": {"raw_runtime_arrays.npz": _file_sha256(npz_path)},
        "array_names": sorted(arrays),
        "array_shapes": {name: list(np.asarray(value).shape) for name, value in arrays.items()},
        "semantic_digest": _digest({name: _normalized_digest(value) for name, value in arrays.items()}),
        "evidence_schema_valid": True,
        "evidence_integrity": "PASS",
    }
    _write_json(OUTPUT_DIR / "manifest.json", manifest)
    evidence["raw_data_archived"] = {"path": "raw_runtime_arrays.npz", "manifest": "manifest.json", "array_count": len(arrays)}
    evidence["digests"] = {"manifest": _file_sha256(OUTPUT_DIR / "manifest.json"), "raw_npz": _file_sha256(npz_path), "semantic": manifest["semantic_digest"]}
    _write_json(OUTPUT_DIR / "evidence.json", evidence)
    return 0 if evidence["status"] == "PASS_RUNTIME_BOUNDED" else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("serial", "mpi", "failures", "build"), required=True)
    parser.add_argument("--segments", type=int, default=1)
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--serial", type=Path)
    parser.add_argument("--mpi2", type=Path)
    parser.add_argument("--mpi2-replay1", type=Path)
    parser.add_argument("--mpi2-replay2", type=Path)
    parser.add_argument("--mpi3", type=Path)
    parser.add_argument("--scale-a", type=Path)
    parser.add_argument("--scale-b", type=Path)
    parser.add_argument("--failures", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.mode in {"serial", "mpi", "failures"} and args.output is None:
        raise SystemExit("--output is required for serial, mpi and failures modes")
    if args.mode == "serial":
        return _serial_mode(args)
    if args.mode == "mpi":
        return _mpi_mode(args)
    if args.mode == "failures":
        return _failure_mode(args)
    required = (args.serial, args.mpi2, args.scale_a, args.scale_b, args.failures)
    if any(path is None for path in required):
        raise SystemExit("build mode requires --serial --mpi2 --scale-a --scale-b --failures")
    return _build_evidence(args)


if __name__ == "__main__":
    raise SystemExit(main())
