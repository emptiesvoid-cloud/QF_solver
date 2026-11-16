"""A small TET10 modal route smoke compared with a dense same-operator eigensolve."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import platform
import tempfile
from importlib import metadata
from pathlib import Path
from typing import Any

import numpy as np
import scipy
from scipy.linalg import eigh
import threadpoolctl

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
import sys

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from solveur.api import solve_model  # noqa: E402
from solveur.core.assembly.assembler import GlobalAssembler  # noqa: E402
from solveur.core.model import FiniteElementModel  # noqa: E402

CONTRACT_PATH = ROOT / "research/j10_modal/contracts/tet10_modal_route_smoke_contract.json"
NODEID = "tests/verification/test_j10_tet10_modal_smoke.py::test_j10_tet10_modal_route_smoke"
MODE_COUNT = 4

NODES = np.asarray(
    [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.5, 0.0, 0.0],
        [0.5, 0.5, 0.0],
        [0.0, 0.5, 0.0],
        [0.0, 0.0, 0.5],
        [0.5, 0.0, 0.5],
        [0.0, 0.5, 0.5],
    ],
    dtype=np.float64,
)
CONNECTIVITY = np.arange(10, dtype=np.int64)
FIXED_NODES = np.asarray((0, 2, 3, 6, 7, 9), dtype=np.int64)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256(path.read_bytes())


def _canonical_sha256(path: Path) -> str:
    return _sha256(path.read_bytes().replace(b"\r\n", b"\n"))


def _atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _atomic_json(path: Path, payload: dict[str, Any]) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    _atomic_bytes(path, encoded)
    return _sha256(encoded)


def _attempt_output_dir() -> tuple[Path, dict[str, Any]]:
    if os.environ.get("QF_DEVELOPMENT_AUTONOMOUS") != "1":
        raise RuntimeError("J10 modal outputs require the registered development launcher")
    temp = Path(os.environ["TMP"]).resolve(strict=True)
    attempt_dir = temp.parent
    run_path = attempt_dir / "run.json"
    if not run_path.is_file():
        raise RuntimeError("The development runner attempt record is missing")
    run = json.loads(run_path.read_text(encoding="utf-8"))
    if run.get("state") != "RUNNING" or run.get("worktree_id") != "j10" or run.get("target") != [NODEID]:
        raise RuntimeError("The development runner does not identify this exact J10 modal node")
    expected = (ROOT / ".codex/development-runs/worktrees/j10").resolve()
    try:
        attempt_dir.resolve().relative_to(expected)
    except ValueError as exc:
        raise RuntimeError("The J10 modal output directory is outside its registered attempt namespace") from exc
    output = attempt_dir / "output" / "j10_tet10_modal_smoke"
    output.mkdir(parents=True, exist_ok=False)
    return output, run


def _model() -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=NODES.tolist(),
        elements=[{"type": "TET10", "nodes": CONNECTIVITY.tolist(), "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 70.0e9, "nu": 0.30, "density": 2700.0}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in FIXED_NODES],
        analysis={
            "type": "modal",
            "method": "eigsh",
            "modes": MODE_COUNT,
            "arpack_tolerance": 1.0e-11,
            "modal_validation_policy": "strict",
        },
        units={"length": "m", "force": "N", "time": "s", "mass": "kg"},
        verification_profile="quick",
    )


def run_modal_route_smoke() -> dict[str, Any]:
    output_dir, run = _attempt_output_dir()
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    contract_sha = _canonical_sha256(CONTRACT_PATH)
    for item in contract["source_identity"]:
        if _canonical_sha256(ROOT / item["path"]) != item["canonical_sha256"]:
            raise RuntimeError(f"TET10 modal smoke source differs from the frozen contract: {item['path']}")

    model = _model()
    assembler = GlobalAssembler()
    dofs = model.dof_manager()
    stiffness, mass, _stiffness_diag, _mass_diag = assembler.assemble_stiffness_and_mass(model, dofs)
    fixed = assembler.fixed_indices(model, dofs)
    free = np.setdiff1d(np.arange(dofs.ndof, dtype=np.int64), fixed)
    kff = stiffness[free, :][:, free].toarray()
    mff = mass[free, :][:, free].toarray()
    if len(free) != 12:
        raise RuntimeError("TET10 modal smoke free-DOF count differs from its frozen one-element model")
    reference_values, reference_vectors = eigh(kff, mff, subset_by_index=(0, MODE_COUNT - 1), check_finite=True)
    reference_frequencies = np.sqrt(reference_values) / (2.0 * np.pi)

    result = solve_model(model, enforce_policy=False)
    raw_frequencies = getattr(result, "frequencies_hz", None)
    qf_frequencies = np.asarray(raw_frequencies if raw_frequencies is not None else [], dtype=np.float64)
    raw_modes = getattr(result, "modes", None)
    qf_modes = np.asarray(raw_modes if raw_modes is not None else np.empty((0, len(free))), dtype=np.float64)
    frequency_payload_valid = bool(
        qf_frequencies.ndim == 1
        and qf_frequencies.size > 0
        and np.isfinite(qf_frequencies).all()
        and np.all(qf_frequencies > 0.0)
    )
    mode_payload_valid = bool(qf_modes.ndim == 2 and qf_modes.size > 0 and np.isfinite(qf_modes).all())
    modal_validation = (result.solver or {}).get("modal_residual_validation", {})
    route_status = str(result.numerical_status)
    if route_status not in {"PASS", "INCONCLUSIVE", "FAIL"}:
        raise RuntimeError(f"Unexpected modal route status {route_status!r}")
    if route_status == "PASS" and (
        not frequency_payload_valid
        or qf_frequencies.shape != (MODE_COUNT,)
        or not mode_payload_valid
        or len(free) not in qf_modes.shape
        or MODE_COUNT not in qf_modes.shape
    ):
        raise RuntimeError("The modal route reported PASS without four finite frequencies and mode vectors")
    if not frequency_payload_valid:
        # Preserve the route status and shape diagnostics without serializing invalid numeric values.
        qf_frequencies = np.empty((0,), dtype=np.float64)
    if not mode_payload_valid:
        qf_modes = np.empty((0, len(free)), dtype=np.float64)
    compared_mode_count = min(len(qf_frequencies), len(reference_frequencies))
    frequency_relative_errors = (
        np.abs(qf_frequencies[:compared_mode_count] - reference_frequencies[:compared_mode_count])
        / reference_frequencies[:compared_mode_count]
    )

    result_payload = {
        "schema": "qf-j10-tet10-modal-smoke-result-v1",
        "classification": "DEVELOPMENT_ROUTE_SMOKE_NOT_QUALIFICATION",
        "execution_status": "COMPLETED_EXPLORATORY",
        "nodeid": NODEID,
        "source_head": run["identity"]["head"],
        "source_fingerprint": run["source_fingerprint"],
        "contract_sha256": contract_sha,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "matplotlib": metadata.version("matplotlib"),
            "threadpools": [
                {key: item.get(key) for key in ("user_api", "internal_api", "version", "num_threads")}
                for item in threadpoolctl.threadpool_info()
            ],
        },
        "model": {
            "family": "one TET10 tetrahedron",
            "geometry_m": "unit right tetrahedron",
            "element_count": 1,
            "node_count": 10,
            "free_dof_count": int(len(free)),
            "fixed_face_nodes": FIXED_NODES.tolist(),
            "material": {"young_modulus_pa": 70.0e9, "poisson_ratio": 0.30, "density_kg_m3": 2700.0},
            "units": "SI",
            "requested_modes": MODE_COUNT,
        },
        "route": {
            "method": "QF Solver modal eigsh route with strict modal residual validation policy",
            "numerical_status": route_status,
            "modal_residual_validation": modal_validation,
            "frequencies_hz": qf_frequencies.tolist(),
            "returned_frequency_count": int(len(qf_frequencies)),
            "frequency_payload_valid": frequency_payload_valid,
            "returned_mode_shape": list(qf_modes.shape),
            "mode_payload_valid": mode_payload_valid,
        },
        "reference": {
            "type": "dense scipy.linalg.eigh generalized eigenproblem on the same QF-assembled Kff and Mff",
            "frequencies_hz": reference_frequencies.tolist(),
            "relative_frequency_differences": frequency_relative_errors.tolist(),
            "mode_count_compared": int(compared_mode_count),
            "maximum_relative_frequency_difference": (
                float(np.max(frequency_relative_errors)) if frequency_relative_errors.size else None
            ),
            "validates": "the modal route/eigenpair output for this 12-DOF one-element system against a separate dense eigensolver",
            "does_not_validate": "TET10 spatial accuracy, the J9 cantilever response, continuum frequency accuracy, or a modal transient route",
        },
        "criteria": {
            "formal_acceptance_thresholds": "none",
            "completion_invariants": "four finite positive frequencies, finite mode vectors, 12 free DOFs, solver validation status recorded without promoting INCONCLUSIVE",
        },
        "interpretation": "This is a deliberately small route smoke with a same-operator numerical cross-check. It does not retry or replace the historical J9 full-basis failure at 108 free DOFs.",
    }
    arrays = {
        "nodes_m": NODES,
        "connectivity_tet10": CONNECTIVITY,
        "free_dof_indices": free,
        "stiffness_free_n_per_m": kff,
        "mass_free_kg": mff,
        "qf_frequencies_hz": qf_frequencies,
        "qf_modes": qf_modes,
        "dense_reference_frequencies_hz": reference_frequencies,
        "dense_reference_modes": reference_vectors,
    }
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **arrays)
    state_path = output_dir / "tet10_modal_smoke_state.npz"
    state_bytes = buffer.getvalue()
    _atomic_bytes(state_path, state_bytes)
    result_payload["state_npz"] = {"path": state_path.name, "sha256": _sha256(state_bytes)}
    csv_path = output_dir / "tet10_modal_smoke_frequencies.csv"
    with tempfile.NamedTemporaryFile(mode="w", dir=output_dir, prefix=csv_path.name + ".", suffix=".tmp", delete=False, newline="", encoding="utf-8") as stream:
        temporary_csv = Path(stream.name)
        writer = csv.DictWriter(stream, fieldnames=["mode", "qf_frequency_hz", "dense_same_operator_frequency_hz", "relative_difference"])
        writer.writeheader()
        writer.writerows({
            "mode": index + 1,
            "qf_frequency_hz": float(qf_frequencies[index]),
            "dense_same_operator_frequency_hz": float(reference_frequencies[index]),
            "relative_difference": float(frequency_relative_errors[index]),
        } for index in range(compared_mode_count))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary_csv, csv_path)
    result_payload["frequencies_csv"] = {"path": csv_path.name, "sha256": _file_sha256(csv_path)}
    result_sha = _atomic_json(output_dir / "result.json", result_payload)
    _atomic_json(output_dir / "result.sha256.json", {"sha256": result_sha})
    return result_payload
