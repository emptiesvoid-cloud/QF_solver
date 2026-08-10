"""HDF5/NPZ I/O for large-scale TET4 models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from solveur.core.errors import InfrastructureError, InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.io.json_reader import JsonModelReader
from solveur.large.dofs import component_from_dof
from solveur.large.materials import create_large_material
from solveur.large.model import LargeModel


def load_large_model(path: str | Path) -> LargeModel:
    """Load a large-scale model from HDF5 or NPZ."""
    source = Path(path)
    if source.suffix.lower() in {".h5", ".hdf5"}:
        return _load_hdf5(source)
    if source.suffix.lower() == ".npz":
        return _load_npz(source)
    raise InputValidationError(f"Unsupported large model format {source.suffix!r}; expected .h5, .hdf5 or .npz.")


def save_large_model(model: LargeModel, path: str | Path) -> Path:
    """Save a large-scale model to HDF5 or NPZ."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.suffix.lower() in {".h5", ".hdf5"}:
        _save_hdf5(model, target)
    elif target.suffix.lower() == ".npz":
        _save_npz(model, target)
    else:
        raise InputValidationError(f"Unsupported large model format {target.suffix!r}; expected .h5, .hdf5 or .npz.")
    return target


def convert_model_to_large(input_path: str | Path, output_path: str | Path) -> LargeModel:
    """Convert a standard JSON model to large-scale HDF5/NPZ format."""
    model = JsonModelReader().read(input_path)
    large = from_finite_element_model(model)
    save_large_model(large, output_path)
    return large


def from_finite_element_model(model: FiniteElementModel) -> LargeModel:
    """Build a LargeModel from the existing in-memory model after strict scope checks."""
    _validate_large_scope(model)
    material_names = tuple(sorted(model.materials))
    material_index = {name: index for index, name in enumerate(material_names)}
    tet4 = np.asarray([element.nodes for element in model.elements], dtype=np.int64)
    material_ids = np.asarray([material_index[element.material] for element in model.elements], dtype=np.int64)
    fixed_nodes: list[int] = []
    fixed_components: list[int] = []
    for condition in model.fixed_dofs:
        for dof in condition.dofs:
            fixed_nodes.append(int(condition.node))
            fixed_components.append(component_from_dof(dof))
    load_nodes = [int(load.node) for load in model.loads]
    load_components = [component_from_dof(load.dof) for load in model.loads]
    load_values = [float(load.value) for load in model.loads]
    return LargeModel(
        nodes=np.asarray(model.nodes, dtype=float),
        tet4=tet4,
        material_ids=material_ids,
        materials=model.materials,
        material_names=material_names,
        fixed_nodes=np.asarray(fixed_nodes, dtype=np.int64),
        fixed_components=np.asarray(fixed_components, dtype=np.int8),
        load_nodes=np.asarray(load_nodes, dtype=np.int64),
        load_components=np.asarray(load_components, dtype=np.int8),
        load_values=np.asarray(load_values, dtype=float),
        analysis={"type": model.analysis.type, "method": model.analysis.method, "parameters": model.analysis.parameters},
        schema_version=model.schema_version,
        units=model.units,
        verification_profile=model.verification_profile,
    )


def _validate_large_scope(model: FiniteElementModel) -> None:
    if model.analysis.type != "linear_static":
        raise InputValidationError("Large-scale v1 supports only linear_static analysis.")
    if model.distributed_loads:
        raise InputValidationError(
            "Large-scale v1 does not support distributed loads; conversion would lose load data."
        )
    for index, element in enumerate(model.elements):
        if element.type != "TET4":
            raise InputValidationError(
                f"Large-scale v1 supports only TET4 elements; element {index} is {element.type}."
            )
        material = model.materials.get(element.material, {})
        try:
            create_large_material(material)
        except (KeyError, TypeError, ValueError) as exc:
            raise InputValidationError(
                f"Large-scale material {element.material!r} is invalid or unsupported: {exc}"
            ) from exc


def _save_hdf5(model: LargeModel, path: Path) -> None:
    h5py = _h5py()
    with h5py.File(path, "w") as handle:
        handle.create_dataset("nodes", data=model.nodes, chunks=True)
        handle.create_dataset("tet4", data=model.tet4, chunks=True)
        handle.create_dataset("material_ids", data=model.material_ids, chunks=True)
        handle.create_dataset("fixed_nodes", data=model.fixed_nodes, chunks=True)
        handle.create_dataset("fixed_dofs", data=model.fixed_components, chunks=True)
        handle.create_dataset("load_nodes", data=model.load_nodes, chunks=True)
        handle.create_dataset("load_dofs", data=model.load_components, chunks=True)
        handle.create_dataset("load_values", data=model.load_values, chunks=True)
        handle.attrs["metadata_json"] = json.dumps(_metadata(model))


def _load_hdf5(path: Path) -> LargeModel:
    h5py = _h5py()
    try:
        with h5py.File(path, "r") as handle:
            metadata = json.loads(handle.attrs.get("metadata_json", "{}"))
            return LargeModel(
                nodes=np.asarray(handle["nodes"], dtype=float),
                tet4=np.asarray(handle["tet4"], dtype=np.int64),
                material_ids=np.asarray(handle["material_ids"], dtype=np.int64),
                materials=metadata["materials"],
                material_names=tuple(metadata["material_names"]),
                fixed_nodes=np.asarray(handle["fixed_nodes"], dtype=np.int64),
                fixed_components=np.asarray(handle["fixed_dofs"], dtype=np.int8),
                load_nodes=np.asarray(handle["load_nodes"], dtype=np.int64),
                load_components=np.asarray(handle["load_dofs"], dtype=np.int8),
                load_values=np.asarray(handle["load_values"], dtype=float),
                analysis=metadata.get("analysis", {"type": "linear_static", "method": "cg"}),
                schema_version=int(metadata.get("schema_version", 1)),
                units=dict(metadata.get("units", {"system": "SI"})),
                verification_profile=str(metadata.get("verification_profile", "engineering")),
            )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"Invalid or corrupted HDF5 large model {path}: {exc}") from exc


def _save_npz(model: LargeModel, path: Path) -> None:
    np.savez_compressed(
        path,
        nodes=model.nodes,
        tet4=model.tet4,
        material_ids=model.material_ids,
        fixed_nodes=model.fixed_nodes,
        fixed_dofs=model.fixed_components,
        load_nodes=model.load_nodes,
        load_dofs=model.load_components,
        load_values=model.load_values,
        metadata_json=np.asarray(json.dumps(_metadata(model))),
    )


def _load_npz(path: Path) -> LargeModel:
    try:
        with np.load(path, allow_pickle=False) as data:
            metadata = json.loads(str(data["metadata_json"].item()))
            return LargeModel(
                nodes=data["nodes"],
                tet4=data["tet4"],
                material_ids=data["material_ids"],
                materials=metadata["materials"],
                material_names=tuple(metadata["material_names"]),
                fixed_nodes=data["fixed_nodes"],
                fixed_components=data["fixed_dofs"],
                load_nodes=data["load_nodes"],
                load_components=data["load_dofs"],
                load_values=data["load_values"],
                analysis=metadata.get("analysis", {"type": "linear_static", "method": "cg"}),
                schema_version=int(metadata.get("schema_version", 1)),
                units=dict(metadata.get("units", {"system": "SI"})),
                verification_profile=str(metadata.get("verification_profile", "engineering")),
            )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"Invalid or corrupted NPZ large model {path}: {exc}") from exc


def _metadata(model: LargeModel) -> dict[str, Any]:
    return {
        "schema_version": model.schema_version,
        "units": model.units,
        "verification_profile": model.verification_profile,
        "analysis": model.analysis,
        "materials": model.materials,
        "material_names": list(model.material_names),
    }


def _h5py() -> object:
    try:
        import h5py
    except ImportError as exc:
        raise InfrastructureError("HDF5 large-model support requires optional dependency h5py.") from exc
    return h5py
