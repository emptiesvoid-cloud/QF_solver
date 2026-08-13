"""Checkpointed, block-wise post-processing for large linear TET4 models."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import numpy as np

from solveur.core.errors import InfrastructureError, InputValidationError
from solveur.io.manifest import sha256, utc_timestamp, write_json_file
from solveur.large.evidence import write_large_manifest
from solveur.large.materials import create_large_material
from solveur.large.tet4_batch import tet4_response_batch

_CHECKPOINT_SCHEMA = 1
_RESULT_SCHEMA = 1


def postprocess_large_tet4(
    model_path: str | Path,
    displacement_path: str | Path,
    output_dir: str | Path,
    *,
    chunk_size: int = 65_536,
    resume: bool = False,
    overwrite: bool = False,
    max_chunks: int | None = None,
) -> dict[str, Any]:
    """Recover TET4 fields into HDF5 without loading the complete result arrays."""
    if chunk_size <= 0:
        raise InputValidationError("Large post-processing chunk_size must be positive.")
    if max_chunks is not None and max_chunks <= 0:
        raise InputValidationError("max_chunks must be positive when provided.")
    if resume and overwrite:
        raise InputValidationError("resume and overwrite are mutually exclusive.")
    model_source = Path(model_path)
    displacement_source = Path(displacement_path)
    if model_source.suffix.lower() not in {".h5", ".hdf5"}:
        raise InputValidationError("Scalable post-processing currently requires an HDF5 large model.")
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    result_path = root / "element_results.h5"
    checkpoint_path = root / "postprocess_checkpoint.json"
    summary_path = root / "postprocess_summary.json"
    if overwrite:
        for path in (result_path, checkpoint_path, summary_path, root / "evidence_manifest.json"):
            path.unlink(missing_ok=True)
    elif not resume and any(path.exists() for path in (result_path, checkpoint_path, summary_path)):
        raise InputValidationError("Post-processing outputs already exist; use resume=True or overwrite=True.")
    fingerprints = {"model_sha256": sha256(model_source), "displacement_sha256": sha256(displacement_source)}
    h5py = _h5py()
    started = time.perf_counter()
    with h5py.File(model_source, "r") as model, _DisplacementReader(displacement_source) as displacement:
        metadata = _model_metadata(model)
        node_count = int(model["nodes"].shape[0])
        element_count = int(model["tet4"].shape[0])
        if element_count <= 0:
            raise InputValidationError("Large post-processing requires at least one TET4 element.")
        displacement.validate(node_count)
        materials = _elasticity_matrices(metadata)
        state = _load_or_create_state(
            checkpoint_path,
            result_path,
            fingerprints,
            element_count,
            chunk_size,
            resume,
        )
        initial_processed = int(state["processed_count"])
        mode = "r+" if resume else "w"
        with h5py.File(result_path, mode) as results:
            if not resume:
                _create_result_datasets(results, element_count, chunk_size, fingerprints)
                _write_checkpoint(checkpoint_path, state)
            else:
                _validate_result_file(results, element_count, fingerprints)
            processed_chunks = 0
            while int(state["next_element"]) < element_count:
                start = int(state["next_element"])
                stop = min(start + chunk_size, element_count)
                response = _process_chunk(model, displacement, materials, start, stop)
                for name in ("volume", "strain", "stress", "von_mises", "strain_energy"):
                    results[name][start:stop] = response[name]
                results.flush()
                _update_state(state, response, stop)
                _write_checkpoint(checkpoint_path, state)
                processed_chunks += 1
                if max_chunks is not None and processed_chunks >= max_chunks:
                    break
    complete = int(state["next_element"]) == int(state["element_count"])
    summary = _summary(
        state,
        fingerprints,
        result_path,
        time.perf_counter() - started,
        complete,
        int(state["processed_count"]) - initial_processed,
    )
    write_json_file(summary_path, summary)
    if complete:
        manifest = write_large_manifest(root, {"kind": "large_tet4_postprocess", "status": "PASS"})
        summary["evidence_manifest"] = str(manifest)
    return summary


class _DisplacementReader:
    def __init__(self, path: Path):
        self.path = path
        self._handle: Any | None = None
        self._values: Any | None = None
        self.shape: tuple[int, int] = (0, 0)

    def __enter__(self) -> _DisplacementReader:
        suffix = self.path.suffix.lower()
        if suffix == ".bin":
            metadata_path = self.path.with_name("displacements_metadata.json")
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                self.shape = tuple(int(value) for value in metadata["shape"])  # type: ignore[assignment]
                dtype = np.dtype("<f8" if metadata.get("byte_order", "little") == "little" else ">f8")
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise InputValidationError(f"Invalid distributed displacement metadata: {exc}") from exc
            if self.path.stat().st_size != int(np.prod(self.shape)) * dtype.itemsize:
                raise InputValidationError("Distributed displacement file size does not match its metadata.")
            self._values = np.memmap(self.path, mode="r", dtype=dtype, shape=self.shape)
        elif suffix in {".h5", ".hdf5"}:
            self._handle = _h5py().File(self.path, "r")
            if "displacements" not in self._handle:
                raise InputValidationError("HDF5 displacement file has no 'displacements' dataset.")
            self._values = self._handle["displacements"]
            self.shape = tuple(int(value) for value in self._values.shape)
        else:
            raise InputValidationError("Large post-processing supports .bin and HDF5 displacements.")
        return self

    def __exit__(self, *_: object) -> None:
        if self._handle is not None:
            self._handle.close()

    def validate(self, node_count: int) -> None:
        if self.shape != (node_count, 3):
            raise InputValidationError(
                f"Displacement shape {self.shape} is incompatible with expected {(node_count, 3)}."
            )

    def read(self, node_ids: np.ndarray) -> np.ndarray:
        if self._values is None:
            raise RuntimeError("Displacement reader is not open.")
        return np.asarray(self._values[node_ids], dtype=float)


def _process_chunk(
    model: Any,
    displacement: _DisplacementReader,
    materials: list[np.ndarray],
    start: int,
    stop: int,
) -> dict[str, np.ndarray]:
    connectivity = np.asarray(model["tet4"][start:stop], dtype=np.int64)
    material_ids = np.asarray(model["material_ids"][start:stop], dtype=np.int64)
    unique_nodes, inverse = np.unique(connectivity, return_inverse=True)
    coords = np.asarray(model["nodes"][unique_nodes], dtype=float)[inverse].reshape((-1, 4, 3))
    local_u = displacement.read(unique_nodes)[inverse].reshape((-1, 12))
    count = stop - start
    response = {
        "volume": np.empty(count, dtype=float),
        "strain": np.empty((count, 6), dtype=float),
        "stress": np.empty((count, 6), dtype=float),
        "von_mises": np.empty(count, dtype=float),
        "strain_energy": np.empty(count, dtype=float),
    }
    for material_id in np.unique(material_ids):
        index = int(material_id)
        if index < 0 or index >= len(materials):
            raise InputValidationError(f"Unknown material id {index} in elements {start}:{stop}.")
        selected = material_ids == index
        values = tet4_response_batch(coords[selected], local_u[selected], materials[index])
        for name, array in response.items():
            array[selected] = values[name]
    return response


def _elasticity_matrices(metadata: dict[str, Any]) -> list[np.ndarray]:
    matrices = []
    for name in metadata.get("material_names", []):
        data = dict(metadata.get("materials", {}).get(name, {}))
        try:
            matrices.append(create_large_material(data).elasticity_matrix)
        except (KeyError, TypeError, ValueError) as exc:
            raise InputValidationError(
                f"Large post-processing does not support material {name!r}: {exc}"
            ) from exc
    if not matrices:
        raise InputValidationError("Large model metadata contains no supported material.")
    return matrices


def _model_metadata(model: Any) -> dict[str, Any]:
    try:
        return json.loads(model.attrs["metadata_json"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"Invalid large-model metadata: {exc}") from exc


def _load_or_create_state(
    path: Path,
    result_path: Path,
    fingerprints: dict[str, str],
    element_count: int,
    chunk_size: int,
    resume: bool,
) -> dict[str, Any]:
    if resume:
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise InputValidationError(f"Invalid large post-processing checkpoint: {exc}") from exc
        expected = {
            "checkpoint_schema_version": _CHECKPOINT_SCHEMA,
            "element_count": element_count,
            "chunk_size": chunk_size,
            **fingerprints,
        }
        if any(state.get(key) != value for key, value in expected.items()) or not result_path.is_file():
            raise InputValidationError("Checkpoint does not match the model, displacement field or chunk size.")
        if not 0 <= int(state.get("next_element", -1)) <= element_count:
            raise InputValidationError("Checkpoint next_element is outside the model range.")
        return state
    return {
        "checkpoint_schema_version": _CHECKPOINT_SCHEMA,
        "status": "RUNNING",
        "created_at": utc_timestamp(),
        "updated_at": utc_timestamp(),
        "element_count": element_count,
        "chunk_size": chunk_size,
        "next_element": 0,
        "processed_count": 0,
        "von_mises_min": None,
        "von_mises_max": None,
        "von_mises_sum": 0.0,
        "strain_energy_sum": 0.0,
        **fingerprints,
    }


def _create_result_datasets(
    results: Any, element_count: int, chunk_size: int, fingerprints: dict[str, str]
) -> None:
    chunk = min(chunk_size, element_count)
    results.create_dataset("volume", shape=(element_count,), dtype="f8", chunks=(chunk,))
    results.create_dataset("strain", shape=(element_count, 6), dtype="f8", chunks=(chunk, 6))
    results.create_dataset("stress", shape=(element_count, 6), dtype="f8", chunks=(chunk, 6))
    results.create_dataset("von_mises", shape=(element_count,), dtype="f8", chunks=(chunk,))
    results.create_dataset("strain_energy", shape=(element_count,), dtype="f8", chunks=(chunk,))
    results.attrs["result_schema_version"] = _RESULT_SCHEMA
    for key, value in fingerprints.items():
        results.attrs[key] = value
    results.attrs["voigt_order"] = "XX,YY,ZZ,XY,YZ,XZ"


def _validate_result_file(results: Any, element_count: int, fingerprints: dict[str, str]) -> None:
    required = {"volume": (element_count,), "strain": (element_count, 6), "stress": (element_count, 6),
                "von_mises": (element_count,), "strain_energy": (element_count,)}
    if any(name not in results or tuple(results[name].shape) != shape for name, shape in required.items()):
        raise InputValidationError("Checkpoint result HDF5 datasets are missing or have invalid shapes.")
    if any(results.attrs.get(key) != value for key, value in fingerprints.items()):
        raise InputValidationError("Checkpoint result HDF5 fingerprints do not match the requested inputs.")


def _update_state(state: dict[str, Any], response: dict[str, np.ndarray], stop: int) -> None:
    von_mises = response["von_mises"]
    current_min = float(np.min(von_mises))
    current_max = float(np.max(von_mises))
    state["next_element"] = int(stop)
    state["processed_count"] = int(state["processed_count"]) + int(von_mises.size)
    state["von_mises_min"] = current_min if state["von_mises_min"] is None else min(state["von_mises_min"], current_min)
    state["von_mises_max"] = current_max if state["von_mises_max"] is None else max(state["von_mises_max"], current_max)
    state["von_mises_sum"] = float(state["von_mises_sum"]) + float(np.sum(von_mises))
    state["strain_energy_sum"] = float(state["strain_energy_sum"]) + float(np.sum(response["strain_energy"]))
    state["updated_at"] = utc_timestamp()
    state["status"] = "PASS" if stop == int(state["element_count"]) else "RUNNING"


def _summary(
    state: dict[str, Any],
    fingerprints: dict[str, str],
    result_path: Path,
    elapsed: float,
    complete: bool,
    processed_this_run: int,
) -> dict[str, Any]:
    processed = int(state["processed_count"])
    return {
        "postprocess_schema_version": _RESULT_SCHEMA,
        "status": "PASS" if complete else "CHECKPOINTED",
        "element_count": int(state["element_count"]),
        "processed_element_count": processed,
        "next_element": int(state["next_element"]),
        "chunk_size": int(state["chunk_size"]),
        "elapsed_seconds_this_run": float(elapsed),
        "processed_elements_this_run": processed_this_run,
        "throughput_elements_per_second": processed_this_run / elapsed if elapsed > 0.0 else None,
        "von_mises_min": state["von_mises_min"],
        "von_mises_max": state["von_mises_max"],
        "von_mises_mean": float(state["von_mises_sum"]) / processed if processed else None,
        "strain_energy_sum": float(state["strain_energy_sum"]),
        "result_file": str(result_path),
        "checkpoint_file": str(result_path.with_name("postprocess_checkpoint.json")),
        **fingerprints,
    }


def _write_checkpoint(path: Path, state: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def _h5py() -> Any:
    try:
        import h5py
    except ImportError as exc:
        raise InfrastructureError("Large post-processing requires h5py.") from exc
    return h5py
